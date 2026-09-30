"""Markdown reports for analyze-mr (01–04 under run-dir)."""

from __future__ import annotations

from pathlib import Path

from mr_impact.mr.boundary import format_boundary_markdown
from mr_impact.mr.run_context import MrRunContext


def issue_snippet(issue_dir: Path | None) -> str | None:
    if issue_dir is None or not issue_dir.is_dir():
        return None
    for name in ("01-generated-issue.md", "00-issue-analysis.md"):
        candidate = issue_dir / name
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace").strip()
            return text[:4000] + ("…" if len(text) > 4000 else "")
    return None


def index_stale_note(
    *,
    index_stale: bool,
    indexed_head: str,
    repo_head: str | None,
    partial_refresh: dict | None,
) -> str:
    if index_stale:
        return (
            f"\n\n> **Index stale:** index at `{indexed_head[:12]}`, "
            f"repo HEAD `{repo_head[:12] if repo_head else 'unknown'}`. "
            "Run `/create-index` for a full refresh.\n"
        )
    if partial_refresh:
        return (
            "\n\n> **Index:** MR changed paths were re-indexed at current HEAD "
            f"({len(partial_refresh.get('refreshed_paths', []))} paths). "
            "Full-repo index may still be older elsewhere.\n"
        )
    return ""


def render_mr_analysis(ctx: MrRunContext) -> str:
    stale_note = index_stale_note(
        index_stale=ctx.index_stale,
        indexed_head=ctx.indexed_head,
        repo_head=ctx.repo_head,
        partial_refresh=ctx.partial_refresh,
    )
    changed_lines = [f"- `{c.status}` `{c.path}`" for c in ctx.changed] or ["- (none)"]
    symbol_lines = [
        f"- `{sym['path']}`:`{sym['name']}` ({sym.get('diff_match', '?')}, "
        f"L{sym['line_start']}-L{sym['line_end']})"
        for sym in ctx.symbols[:30]
    ]
    if len(ctx.symbols) > 30:
        symbol_lines.append(f"- … and {len(ctx.symbols) - 30} more")
    lines = [
        "# MR analysis",
        "",
        f"- **Generated:** {ctx.now}",
        f"- **Revision:** `{ctx.revision}`",
        f"- **Base / head:** `{ctx.base_sha[:12]}` / `{ctx.head_sha[:12]}`",
        f"- **Changed files:** {len(ctx.changed)}",
        f"- **Symbols touched by diff:** {len(ctx.symbols)}",
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
    return "\n".join(lines)


def render_change_context(ctx: MrRunContext) -> str:
    issue_text = issue_snippet(ctx.issue_dir)
    lines = [
        "# Change context",
        "",
        f"- **Generated:** {ctx.now}",
        "",
        "## Issue context",
        "",
    ]
    if issue_text:
        lines.append(issue_text)
    else:
        lines.append("_No Issue artifacts supplied (`--issue-dir` optional)._")
    return "\n".join(lines) + "\n"


def render_impact_analysis(ctx: MrRunContext) -> str:
    lines = [
        "# Impact analysis",
        "",
        f"- **Primary QA targets:** {len(ctx.primary_qa)}",
        f"- **Bounded graph edges (diagnostic):** {len(ctx.impact_edges)}",
        "",
        "## Nearest runtime paths",
        "",
    ]
    if ctx.primary_qa:
        for item in ctx.primary_qa:
            job = item.get("job", "?")
            box = item.get("box")
            path_nodes = " → ".join(h.get("node", "?") for h in item.get("path", []))
            lines.append(f"### {job}")
            if box:
                lines.append(f"- **Box:** `{box}`")
            lines.append(f"- **Path:** {path_nodes}")
            lines.append(f"- **Confidence:** {item.get('confidence')}")
            lines.append("")
    else:
        lines.append("_No primary AutoSys job resolved; see unresolved in runtime-impact.json._")
        lines.append("")
    if ctx.unresolved:
        lines.append("## Unresolved seeds")
        lines.append("")
        for item in ctx.unresolved[:10]:
            seed = item.get("seed", {})
            lines.append(
                f"- `{seed.get('path', '?')}` / `{seed.get('name', '')}` — {item.get('reason')}"
            )
        lines.append("")
    lines.extend(["## Graph (diagnostic, truncated)", ""])
    for edge in ctx.impact_edges[:20]:
        lines.append(
            f"- `{edge.get('from_file')}` → `{edge.get('target')}` "
            f"({edge.get('type')}, {edge.get('confidence')})"
        )
    if len(ctx.impact_edges) > 20:
        lines.append(f"- … and {len(ctx.impact_edges) - 20} more")
    lines.extend(format_boundary_markdown(ctx.boundary_hints))
    return "\n".join(lines) + "\n"


def render_test_plan(ctx: MrRunContext) -> str:
    lines = [
        "# Test / runtime plan",
        "",
        "Primary AutoSys jobs from nearest indexed paths (not full batch inventory).",
        "",
    ]
    if ctx.primary_qa:
        for item in ctx.primary_qa:
            job = item.get("job", "?")
            lines.extend([f"## {job}", ""])
            if item.get("box"):
                lines.append(f"- **Box:** `{item['box']}`")
            for run in item.get("recommended_run", []):
                lines.append(f"- **Run:** {run}")
            for verify in item.get("recommended_verify", []):
                lines.append(f"- **Verify:** {verify}")
            path_nodes = " → ".join(h.get("node", "?") for h in item.get("path", []))
            lines.extend([f"- **Path:** {path_nodes}", ""])
    elif ctx.runtime:
        for target in ctx.runtime:
            lines.extend(
                [
                    f"## {target['job_or_process']}",
                    "",
                    f"- **Why:** {target['why_affected']}",
                    f"- **Run:** {target['suggested_run']}",
                    f"- **Verify:** {target['suggested_verify']}",
                    f"- **Path:** {target['dependency_path']}",
                    "",
                ]
            )
    else:
        lines.append("_No runtime targets inferred from index; extend index or check changed paths._")
    return "\n".join(lines) + "\n"


def write_mr_markdown_reports(run_dir: Path, ctx: MrRunContext) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "01-mr-analysis.md").write_text(render_mr_analysis(ctx), encoding="utf-8")
    (run_dir / "02-change-context.md").write_text(render_change_context(ctx), encoding="utf-8")
    (run_dir / "03-impact-analysis.md").write_text(render_impact_analysis(ctx), encoding="utf-8")
    (run_dir / "04-test-plan.md").write_text(render_test_plan(ctx), encoding="utf-8")
