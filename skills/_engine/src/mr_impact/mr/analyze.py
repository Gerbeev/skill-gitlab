from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mr_impact.git.diff import (
    changed_line_ranges,
    list_changed_files,
    serialize_line_ranges,
)
from mr_impact.git.revision import parse_revision_range, resolve_ref
from mr_impact.graph.nearest_runtime import compute_primary_qa_targets
from mr_impact.graph.query import impact_from_seeds
from mr_impact.index.scanner import git_head
from mr_impact.mr.boundary import load_boundary_catalog, match_boundary_hints
from mr_impact.mr.payloads import build_mr_json_artifacts, write_mr_json_artifacts
from mr_impact.mr.reports import write_mr_markdown_reports
from mr_impact.mr.run_context import MrRunContext
from mr_impact.mr.symbols_from_diff import impact_seeds_from_diff, prepare_mr_symbol_context
from mr_impact.paths import require_index_sqlite


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

    db_path, layout = require_index_sqlite(project_root, analysis_root)

    base_ref, head_ref = parse_revision_range(revision)
    base_sha = resolve_ref(project_root, base_ref)
    head_sha = resolve_ref(project_root, head_ref)
    changed = list_changed_files(project_root, base_sha, head_sha)
    changed_paths = {c.path for c in changed}
    diff_line_ranges = changed_line_ranges(project_root, base_sha, head_sha)

    repo_head = git_head(project_root)
    symbol_ctx = prepare_mr_symbol_context(
        project_root,
        db_path,
        changed=changed,
        changed_paths=changed_paths,
        diff_line_ranges=diff_line_ranges,
        analysis_root=analysis_root,
        repo_head=repo_head,
    )
    indexed_head = symbol_ctx.indexed_head
    partial_refresh = symbol_ctx.partial_refresh
    all_edges = symbol_ctx.all_edges
    all_symbols = symbol_ctx.all_symbols
    symbols = symbol_ctx.symbols

    seeds = impact_seeds_from_diff(changed_paths, symbols)

    impact_edges = impact_from_seeds(project_root, seeds)
    primary_qa, runtime, unresolved = compute_primary_qa_targets(
        all_edges,
        all_symbols,
        symbols,
        changed_paths,
    )
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

    ctx = MrRunContext(
        now=now,
        revision=revision,
        base_sha=base_sha,
        head_sha=head_sha,
        changed=changed,
        symbols=symbols,
        indexed_head=indexed_head,
        repo_head=repo_head,
        index_stale=index_stale,
        partial_refresh=partial_refresh,
        issue_dir=issue_dir,
        graph_json_present=layout.graph_json_present,
        boundary_catalog_present=boundary is not None,
        seeds=seeds,
        impact_edges=impact_edges,
        primary_qa=primary_qa,
        runtime=runtime,
        unresolved=unresolved,
        boundary_hints=boundary_hints,
        serialized_line_ranges=serialize_line_ranges(diff_line_ranges),
    )

    write_mr_json_artifacts(run_dir, build_mr_json_artifacts(ctx))
    write_mr_markdown_reports(run_dir, ctx)

    return {
        "run_dir": str(run_dir),
        "changed_files": len(changed),
        "impact_edges": len(impact_edges),
        "runtime_targets": len(runtime),
        "primary_qa_targets": len(primary_qa),
        "index_partial_refresh": partial_refresh is not None,
        "index_stale": index_stale,
        "boundary_hint_count": boundary_hints.get("hint_count", 0),
    }
