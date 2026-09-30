from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mr_impact.git.diff import (
    changed_line_ranges,
    list_changed_files,
    serialize_line_ranges,
    symbols_touched_by_diff,
)
from mr_impact.git.revision import parse_revision_range, resolve_ref
from mr_impact.graph.query import impact_from_seeds
from mr_impact.index.pipeline import analysis_paths, reindex_changed_paths
from mr_impact.index.scanner import git_head
from mr_impact.index.store import IndexStore
from mr_impact.mr.boundary import (
    format_boundary_markdown,
    load_boundary_catalog,
    match_boundary_hints,
)


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _issue_snippet(issue_dir: Path | None) -> str | None:
    if issue_dir is None or not issue_dir.is_dir():
        return None
    for name in ("01-generated-issue.md", "00-issue-analysis.md"):
        candidate = issue_dir / name
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace").strip()
            return text[:4000] + ("…" if len(text) > 4000 else "")
    return None


def _runtime_targets(changed_paths: set[str], edges: list[dict], symbols: list[dict]) -> list[dict]:
    """Jobs/processes that reference changed script paths (JIL script_path edges)."""
    normalized = {p.replace("\\", "/") for p in changed_paths}
    targets: list[dict] = []
    jobs_by_file: dict[str, list[str]] = {}
    for sym in symbols:
        if sym.get("kind") == "autosys_job":
            jobs_by_file.setdefault(sym["path"], []).append(sym["name"])

    for edge in edges:
        if edge.get("type") != "script_path":
            continue
        target = str(edge.get("target", "")).replace("\\", "/")
        if not any(target == cp or target.endswith("/" + cp) or cp.endswith(target) for cp in normalized):
            continue
        from_file = str(edge.get("from_file", ""))
        job_names = jobs_by_file.get(from_file, [])
        for job in job_names or ["(job unknown)"]:
            targets.append(
                {
                    "job_or_process": job,
                    "why_affected": f"command references changed path `{target}`",
                    "suggested_run": f"Verify AutoSys job `{job}` after deploy",
                    "suggested_verify": f"Confirm `{target}` behavior in lower environment",
                    "dependency_path": f"{from_file} → {target}",
                    "confidence": edge.get("confidence", "medium"),
                }
            )
    return targets


def run_analyze_mr(
    project_root: Path,
    *,
    revision: str,
    run_dir: Path,
    issue_dir: Path | None = None,
    analysis_root: Path | None = None,
) -> dict:
    project_root = project_root.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    if issue_dir is not None:
        issue_dir = issue_dir.resolve()

    index_dir, graph_dir = analysis_paths(project_root, analysis_root)
    db_path = index_dir / "repository-index.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(
            f"index missing: {db_path} — run create-index before analyze-mr"
        )

    base_ref, head_ref = parse_revision_range(revision)
    base_sha = resolve_ref(project_root, base_ref)
    head_sha = resolve_ref(project_root, head_ref)
    changed = list_changed_files(project_root, base_sha, head_sha)
    changed_paths = {c.path for c in changed}
    diff_line_ranges = changed_line_ranges(project_root, base_sha, head_sha)

    repo_head = git_head(project_root)
    store = IndexStore(db_path)
    indexed_head = store.get_meta("git_head") or ""
    store.close()

    partial_refresh: dict | None = None
    index_was_stale = bool(indexed_head and repo_head and indexed_head != repo_head)
    if index_was_stale and changed:
        partial_refresh = reindex_changed_paths(project_root, changed, analysis_root=analysis_root)
        indexed_head = partial_refresh.get("git_head") or indexed_head

    store = IndexStore(db_path)
    all_edges = store.iter_graph_edges()
    normalized_changed = {p.replace("\\", "/") for p in changed_paths}
    jil_sources: set[str] = set()
    for edge in all_edges:
        if edge.get("type") != "script_path":
            continue
        target = str(edge.get("target", "")).replace("\\", "/")
        if any(
            target == cp or target.endswith("/" + cp) or cp.endswith("/" + target) or cp == target
            for cp in normalized_changed
        ):
            jil_sources.add(str(edge.get("from_file", "")))
    symbol_paths = changed_paths | jil_sources
    symbols_all = store.symbols_for_paths(symbol_paths)
    symbols = symbols_touched_by_diff(
        symbols_all,
        changed_paths=changed_paths,
        linked_paths=jil_sources,
        line_ranges=diff_line_ranges,
    )
    store.close()

    seeds: set[str] = set()
    for path in changed_paths:
        seeds.add(path)
        seeds.add(Path(path).name)
    for sym in symbols:
        seeds.add(sym["name"])

    impact_edges = impact_from_seeds(project_root, seeds)
    runtime = _runtime_targets(changed_paths, all_edges, symbols)
    boundary = load_boundary_catalog(project_root)
    boundary_hints = match_boundary_hints(
        boundary,
        changed_paths=changed_paths,
        symbols=symbols,
        runtime_targets=runtime,
    )
    now = datetime.now(timezone.utc).isoformat()
    if repo_head is None:
        repo_head = git_head(project_root)

    index_stale = bool(indexed_head and repo_head and indexed_head != repo_head)
    changed_symbols_payload = {
        "schema_version": 1,
        "revision": revision,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_files": [{"status": c.status, "path": c.path} for c in changed],
        "changed_line_ranges": serialize_line_ranges(diff_line_ranges),
        "symbols_touched_by_diff": symbols,
        "symbols_in_changed_files": symbols,
        "index_git_head": indexed_head,
        "repository_git_head": repo_head,
        "index_stale": index_stale,
        "index_partial_refresh": partial_refresh is not None,
        "mr_refreshed_paths": (partial_refresh or {}).get("refreshed_paths", []),
    }
    _write_json(run_dir / "changed-symbols.json", changed_symbols_payload)

    impact_graph_payload = {
        "schema_version": 1,
        "seed_count": len(seeds),
        "edge_count": len(impact_edges),
        "edges": impact_edges,
    }
    _write_json(run_dir / "impact-graph.json", impact_graph_payload)

    runtime_payload = {
        "schema_version": 1,
        "targets": runtime,
        "unresolved_note": None if runtime else "No JIL script_path links to changed files in index.",
    }
    _write_json(run_dir / "runtime-impact.json", runtime_payload)

    test_impact = [
        {
            "scenario": t["job_or_process"],
            "reason": t["why_affected"],
            "verify": t["suggested_verify"],
            "confidence": t["confidence"],
        }
        for t in runtime
    ]
    _write_json(run_dir / "test-impact.json", {"schema_version": 1, "scenarios": test_impact})
    _write_json(run_dir / "boundary-hints.json", boundary_hints)

    mr_context = {
        "schema_version": 1,
        "generated_at": now,
        "revision": revision,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_file_count": len(changed),
        "index_present": True,
        "graph_json_present": (graph_dir / "dependency-graph.json").is_file(),
        "boundary_catalog_present": boundary is not None,
        "boundary_hint_count": boundary_hints.get("hint_count", 0),
        "issue_dir": str(issue_dir) if issue_dir else None,
        "index_partial_refresh": partial_refresh is not None,
    }
    if partial_refresh:
        mr_context["mr_refreshed_paths"] = partial_refresh.get("refreshed_paths", [])
    _write_json(run_dir / "mr-context.json", mr_context)

    stale_note = ""
    if index_stale:
        stale_note = (
            f"\n\n> **Index stale:** index at `{indexed_head[:12]}`, "
            f"repo HEAD `{repo_head[:12] if repo_head else 'unknown'}`. "
            "Run `/create_index` for a full refresh.\n"
        )
    elif partial_refresh:
        stale_note = (
            "\n\n> **Index:** MR changed paths were re-indexed at current HEAD "
            f"({len(partial_refresh.get('refreshed_paths', []))} paths). "
            "Full-repo index may still be older elsewhere.\n"
        )

    changed_lines = [f"- `{c.status}` `{c.path}`" for c in changed] or ["- (none)"]
    symbol_lines = [
        f"- `{sym['path']}`:`{sym['name']}` ({sym.get('diff_match', '?')}, L{sym['line_start']}-L{sym['line_end']})"
        for sym in symbols[:30]
    ]
    if len(symbols) > 30:
        symbol_lines.append(f"- … and {len(symbols) - 30} more")
    analysis_body = [
        "# MR analysis",
        "",
        f"- **Generated:** {now}",
        f"- **Revision:** `{revision}`",
        f"- **Base / head:** `{base_sha[:12]}` / `{head_sha[:12]}`",
        f"- **Changed files:** {len(changed)}",
        f"- **Symbols touched by diff:** {len(symbols)}",
        stale_note,
        "",
        "## Changed paths",
        "",
        *changed_lines,
        "",
        "## Symbols touched (line-aware)",
        "",
        *(symbol_lines or ["- (none)"]),
        "",
    ]
    (run_dir / "01-mr-analysis.md").write_text("\n".join(analysis_body), encoding="utf-8")

    issue_text = _issue_snippet(issue_dir)
    issue_lines = [
        "# Change context",
        "",
        f"- **Generated:** {now}",
        "",
        "## Issue context",
        "",
    ]
    if issue_text:
        issue_lines.append(issue_text)
    else:
        issue_lines.append("_No Issue artifacts supplied (`--issue-dir` optional)._")
    (run_dir / "02-change-context.md").write_text("\n".join(issue_lines) + "\n", encoding="utf-8")

    impact_lines = [
        "# Impact analysis",
        "",
        f"- **Bounded edges:** {len(impact_edges)}",
        "",
        "## Graph (truncated)",
        "",
    ]
    for edge in impact_edges[:40]:
        impact_lines.append(
            f"- `{edge.get('from_file')}` → `{edge.get('target')}` "
            f"({edge.get('type')}, {edge.get('confidence')})"
        )
    if len(impact_edges) > 40:
        impact_lines.append(f"- … and {len(impact_edges) - 40} more")
    impact_lines.extend(format_boundary_markdown(boundary_hints))
    (run_dir / "03-impact-analysis.md").write_text("\n".join(impact_lines) + "\n", encoding="utf-8")

    plan_lines = [
        "# Test / runtime plan",
        "",
        "Concrete targets from indexed JIL/script links (not generic boilerplate).",
        "",
    ]
    if runtime:
        for t in runtime:
            plan_lines.extend(
                [
                    f"## {t['job_or_process']}",
                    "",
                    f"- **Why:** {t['why_affected']}",
                    f"- **Run:** {t['suggested_run']}",
                    f"- **Verify:** {t['suggested_verify']}",
                    f"- **Path:** {t['dependency_path']}",
                    "",
                ]
            )
    else:
        plan_lines.append("_No runtime targets inferred from index; extend index or check changed paths._")
    (run_dir / "04-test-plan.md").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "changed_files": len(changed),
        "impact_edges": len(impact_edges),
        "runtime_targets": len(runtime),
        "index_partial_refresh": partial_refresh is not None,
        "index_stale": index_stale,
        "boundary_hint_count": boundary_hints.get("hint_count", 0),
    }
