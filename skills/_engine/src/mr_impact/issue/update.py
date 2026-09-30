from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_SECTION_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("observed_implementation", "01-mr-analysis.md", "MR analysis"),
    ("impact_summary", "03-impact-analysis.md", "Impact analysis"),
    ("validation_runtime", "04-test-plan.md", "Test plan"),
    ("change_vs_issue_intent", "02-change-context.md", "Change context"),
)

_EXCERPT_LIMIT = 2000


def _format_nearest_paths_markdown(primary: list[dict], unresolved: list[dict]) -> str:
    lines: list[str] = []
    if primary:
        for item in primary:
            job = item.get("job", "?")
            lines.append(f"### {job}")
            if item.get("box"):
                lines.append(f"- **Box:** `{item['box']}`")
            path_nodes = " → ".join(h.get("node", "?") for h in item.get("path", []))
            lines.append(f"- **Path:** {path_nodes}")
            for run in item.get("recommended_run", []):
                lines.append(f"- **Run:** {run}")
            for verify in item.get("recommended_verify", []):
                lines.append(f"- **Verify:** {verify}")
            lines.append("")
    else:
        lines.append("_No primary AutoSys job path in runtime-impact.json._")
        lines.append("")
    if unresolved:
        lines.append("#### Unresolved")
        lines.append("")
        for item in unresolved[:5]:
            seed = item.get("seed", {})
            label = seed.get("name") or seed.get("path") or "?"
            lines.append(f"- `{label}`: {item.get('reason', 'unresolved')}")
        lines.append("")
    return "\n".join(lines).strip()


def run_update_issue(project_root: Path, *, run_dir: Path) -> dict:
    """Build local Issue update preview from MR run artifacts."""
    project_root = project_root.resolve()
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")

    mr_analysis = run_dir / "01-mr-analysis.md"
    if not mr_analysis.is_file():
        raise FileNotFoundError(
            f"MR analysis missing: {mr_analysis} — run analyze-mr first"
        )

    now = datetime.now(timezone.utc).isoformat()
    payload = build_issue_update_payload(run_dir, generated_at=now)

    sections: list[str] = [
        "# Issue update (preview)",
        "",
        f"- **Generated:** {now}",
        "- **GitLab apply:** not performed by engine; user must confirm in skill.",
        "",
        "## Observed implementation context",
        "",
        payload["sections"]["observed_implementation"]["excerpt"],
        "",
        "## Impact summary",
        "",
        payload["sections"]["impact_summary"]["excerpt"],
        "",
        "## QA / runtime (nearest paths)",
        "",
        payload.get("nearest_paths_markdown", "_No runtime-impact.json._"),
        "",
        "## Validation / runtime",
        "",
        payload["sections"]["validation_runtime"]["excerpt"],
        "",
        "## Change vs Issue intent",
        "",
        payload["sections"]["change_vs_issue_intent"]["excerpt"],
        "",
        "## Limitations",
        "",
    ]
    for item in payload["limitations"]:
        sections.append(f"- {item}")
    sections.append("")

    md_out = run_dir / "05-issue-update.md"
    md_out.write_text("\n".join(sections), encoding="utf-8")
    json_out = run_dir / "issue-update.json"
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "preview": str(md_out),
        "issue_update_json": str(json_out),
    }


def build_issue_update_payload(run_dir: Path, *, generated_at: str) -> dict:
    sections: dict[str, dict] = {}
    artifacts_present: dict[str, bool] = {}

    for key, filename, label in _SECTION_SOURCES:
        path = run_dir / filename
        artifacts_present[filename] = path.is_file()
        sections[key] = _section_record(path, label)

    changed = _load_json(run_dir / "changed-symbols.json")
    runtime = _load_json(run_dir / "runtime-impact.json")
    boundary = _load_json(run_dir / "boundary-hints.json")
    mr_context = _load_json(run_dir / "mr-context.json")

    runtime_targets = runtime.get("targets", []) if isinstance(runtime, dict) else []
    primary_qa = runtime.get("primary_qa_targets", []) if isinstance(runtime, dict) else []
    unresolved = runtime.get("unresolved", []) if isinstance(runtime, dict) else []
    boundary_hints = boundary.get("hints", []) if isinstance(boundary, dict) else []
    schema_version = 2 if primary_qa or (runtime and runtime.get("schema_version") == 2) else 1

    return {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "gitlab_apply": False,
        "nearest_paths_markdown": _format_nearest_paths_markdown(primary_qa, unresolved),
        "artifacts_present": {
            **artifacts_present,
            "mr-context.json": (run_dir / "mr-context.json").is_file(),
            "changed-symbols.json": (run_dir / "changed-symbols.json").is_file(),
            "runtime-impact.json": (run_dir / "runtime-impact.json").is_file(),
            "boundary-hints.json": (run_dir / "boundary-hints.json").is_file(),
        },
        "sections": sections,
        "mr_summary": {
            "revision": changed.get("revision") if changed else None,
            "base_sha": changed.get("base_sha") if changed else None,
            "head_sha": changed.get("head_sha") if changed else None,
            "changed_file_count": len(changed.get("changed_files", [])) if changed else None,
            "symbols_touched_count": len(changed.get("symbols_touched_by_diff", [])) if changed else None,
            "runtime_target_count": len(runtime_targets),
            "primary_qa_target_count": len(primary_qa),
            "boundary_hint_count": boundary.get("hint_count", len(boundary_hints)) if boundary else 0,
            "index_stale": changed.get("index_stale") if changed else None,
            "index_partial_refresh": changed.get("index_partial_refresh") if changed else None,
        },
        "mr_context": mr_context,
        "runtime_targets": runtime_targets,
        "primary_qa_targets": primary_qa,
        "unresolved": unresolved,
        "boundary_hints": boundary_hints,
        "limitations": [
            "Preview assembled from local run artifacts only.",
            "No pass/fail verdict vs Issue acceptance criteria.",
            "GitLab write not performed by engine.",
        ],
    }


def _section_record(path: Path, label: str) -> dict:
    if not path.is_file():
        return {
            "source": path.name,
            "present": False,
            "excerpt": f"_Missing `{path.name}` ({label})._",
        }
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    truncated = len(text) > _EXCERPT_LIMIT
    excerpt = text if not truncated else text[:_EXCERPT_LIMIT] + "\n\n… (truncated)"
    return {
        "source": path.name,
        "present": True,
        "truncated": truncated,
        "excerpt": excerpt,
    }


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
