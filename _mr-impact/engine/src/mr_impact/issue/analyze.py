from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from mr_impact.graph.query import anchored_paths
from mr_impact.index.scanner import git_head

INPUT_EXTENSIONS = {".md", ".txt", ".rst", ".adoc", ".json", ".yaml", ".yml"}

JOB_ANCHOR = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")
PATH_ANCHOR = re.compile(
    r"(?:[\w.-]+/)+[\w.-]+\.(?:py|cs|sql|jil|scala|java|kt|xml|yaml|yml|md|ps1|sh)",
    re.I,
)


def _collect_inputs(input_dir: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    if input_dir.is_file():
        try:
            return [(input_dir.name, input_dir.read_text(encoding="utf-8", errors="replace"))]
        except OSError:
            return []
    if not input_dir.is_dir():
        return []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in INPUT_EXTENSIONS and path.name not in ("README", "NOTES"):
            continue
        try:
            rel = path.relative_to(input_dir).as_posix()
            files.append((rel, path.read_text(encoding="utf-8", errors="replace")))
        except (OSError, ValueError):
            continue
    return files


def _extract_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for match in JOB_ANCHOR.finditer(text):
        token = match.group(0)
        if token not in {"TRUE", "FALSE", "NULL", "HTTP", "HTTPS", "JSON", "YAML", "SQL"}:
            anchors.add(token)
    for match in PATH_ANCHOR.finditer(text):
        anchors.add(match.group(0))
    return anchors


def _section_gaps(template: str, combined_input: str) -> list[str]:
    gaps: list[str] = []
    if "Problem" in template and "problem" not in combined_input.lower():
        gaps.append("Input does not clearly state the problem / current state.")
    if "Acceptance" in template and "acceptance" not in combined_input.lower():
        if not re.search(r"\bAC\d+\b", combined_input, re.I) and "criteria" not in combined_input.lower():
            gaps.append("No explicit acceptance criteria found in input material.")
    if len(combined_input.strip()) < 80:
        gaps.append("Input material is very short; analysis may be incomplete.")
    return gaps


def run_analyze_issue(
    project_root: Path,
    *,
    input_dir: Path,
    template_path: Path,
    run_dir: Path,
) -> dict:
    project_root = project_root.resolve()
    input_dir = input_dir.resolve()
    template_path = template_path.resolve()
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    if not template_path.is_file():
        raise FileNotFoundError(f"template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8", errors="replace")
    inputs = _collect_inputs(input_dir)
    if not inputs:
        raise ValueError(f"no input files under {input_dir}")

    combined = "\n\n".join(f"### {name}\n\n{body}" for name, body in inputs)
    anchors = _extract_anchors(combined)
    gaps = _section_gaps(template, combined)
    head = git_head(project_root)
    paths = anchored_paths(project_root, anchors)

    indexed = (project_root / ".repository-analysis" / "index" / "repository-index.sqlite").is_file()
    graph_json = (project_root / ".repository-analysis" / "graph" / "dependency-graph.json").is_file()

    now = datetime.now(timezone.utc).isoformat()
    analysis_path = run_dir / "00-issue-analysis.md"
    generated_path = run_dir / "01-generated-issue.md"

    analysis_lines = [
        "# Issue analysis",
        "",
        f"- **Generated:** {now}",
        f"- **Input directory:** `{input_dir}`",
        f"- **Repository HEAD:** `{head or 'unknown'}`",
        f"- **Index present:** {indexed}",
        f"- **Graph JSON present:** {graph_json}",
        "",
        "## Input scope",
        "",
    ]
    for name, _ in inputs:
        analysis_lines.append(f"- `{name}`")
    analysis_lines.extend(["", "## Gaps and ambiguities", ""])
    if gaps:
        for gap in gaps:
            analysis_lines.append(f"- {gap}")
    else:
        analysis_lines.append("- None flagged by deterministic scan (review still required).")
    analysis_lines.extend(["", "## Anchors (deterministic)", ""])
    if anchors:
        for anchor in sorted(anchors)[:100]:
            analysis_lines.append(f"- `{anchor}`")
    else:
        analysis_lines.append("- No job names or file paths detected in input.")
    analysis_lines.extend(["", "## Dependency paths (anchored, bounded)", ""])
    if not indexed and not graph_json:
        analysis_lines.append(
            "- No repository index/graph. Run `/create_index` (and `/create_graph` if needed) "
            "for path evidence, or list dependencies explicitly in the Issue only."
        )
    elif not paths:
        analysis_lines.append("- No graph edges matched anchors from input (names may not be indexed).")
    else:
        for edge in paths[:50]:
            analysis_lines.append(
                f"- `{edge.get('from_file')}` → `{edge.get('target')}` "
                f"({edge.get('type')}, {edge.get('confidence')})"
            )
        if len(paths) > 50:
            analysis_lines.append(f"- … and {len(paths) - 50} more edges (truncated).")
    analysis_lines.extend(
        [
            "",
            "## AI inference",
            "",
            "- This section was produced by the **engine** (deterministic). "
            "The agent must not promote items here to Acceptance Criteria without user evidence.",
            "",
            "## Open questions",
            "",
            "- Review gaps above and resolve before implementation.",
            "",
        ]
    )
    analysis_path.write_text("\n".join(analysis_lines), encoding="utf-8")

    generated_lines = [
        "# Generated Issue (draft)",
        "",
        "<!-- Filled from template structure; explicit requirements only from input. -->",
        "",
        template,
        "",
        "---",
        "",
        "## Source material summary (engine)",
        "",
        "The following input was available when this draft was generated:",
        "",
    ]
    for name, body in inputs:
        preview = body.strip().replace("\r\n", "\n")
        if len(preview) > 1200:
            preview = preview[:1200] + "\n\n… (truncated)"
        generated_lines.append(f"### {name}")
        generated_lines.append("")
        generated_lines.append(preview)
        generated_lines.append("")

    generated_path.write_text("\n".join(generated_lines), encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "analysis": str(analysis_path),
        "generated": str(generated_path),
        "input_files": len(inputs),
        "anchors": len(anchors),
        "graph_edges": len(paths),
    }
