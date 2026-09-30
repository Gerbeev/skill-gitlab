"""JSON artifacts for analyze-mr (run-dir contract)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mr_impact.json_io import write_json
from mr_impact.mr.run_context import MrRunContext


@dataclass(frozen=True, slots=True)
class MrJsonArtifacts:
    changed_symbols: dict
    impact_graph: dict
    runtime_impact: dict
    test_impact: dict
    boundary_hints: dict
    mr_context: dict


def build_changed_symbols(ctx: MrRunContext) -> dict:
    return {
        "schema_version": 1,
        "revision": ctx.revision,
        "base_sha": ctx.base_sha,
        "head_sha": ctx.head_sha,
        "changed_files": [{"status": c.status, "path": c.path} for c in ctx.changed],
        "changed_line_ranges": ctx.serialized_line_ranges,
        "symbols_touched_by_diff": ctx.symbols,
        "symbols_in_changed_files": ctx.symbols,
        "index_git_head": ctx.indexed_head,
        "repository_git_head": ctx.repo_head,
        "index_stale": ctx.index_stale,
        "index_partial_refresh": ctx.partial_refresh is not None,
        "mr_refreshed_paths": (ctx.partial_refresh or {}).get("refreshed_paths", []),
    }


def build_impact_graph(ctx: MrRunContext) -> dict:
    return {
        "schema_version": 1,
        "seed_count": len(ctx.seeds),
        "edge_count": len(ctx.impact_edges),
        "edges": ctx.impact_edges,
    }


def build_runtime_impact(ctx: MrRunContext) -> dict:
    return {
        "schema_version": 2,
        "primary_qa_targets": ctx.primary_qa,
        "unresolved": ctx.unresolved,
        "targets": ctx.runtime,
        "unresolved_note": None
        if ctx.runtime
        else "No nearest AutoSys job path from MR seeds in index.",
    }


def build_test_impact(ctx: MrRunContext) -> dict:
    scenarios = [
        {
            "scenario": t["job_or_process"],
            "reason": t["why_affected"],
            "verify": t["suggested_verify"],
            "confidence": t["confidence"],
        }
        for t in ctx.runtime
    ]
    return {"schema_version": 1, "scenarios": scenarios}


def build_mr_context(ctx: MrRunContext) -> dict:
    payload = {
        "schema_version": 1,
        "generated_at": ctx.now,
        "revision": ctx.revision,
        "base_sha": ctx.base_sha,
        "head_sha": ctx.head_sha,
        "changed_file_count": len(ctx.changed),
        "index_present": True,
        "graph_json_present": ctx.graph_json_present,
        "boundary_catalog_present": ctx.boundary_catalog_present,
        "boundary_hint_count": ctx.boundary_hints.get("hint_count", 0),
        "issue_dir": str(ctx.issue_dir) if ctx.issue_dir else None,
        "index_partial_refresh": ctx.partial_refresh is not None,
    }
    if ctx.partial_refresh:
        payload["mr_refreshed_paths"] = ctx.partial_refresh.get("refreshed_paths", [])
    return payload


def build_mr_json_artifacts(ctx: MrRunContext) -> MrJsonArtifacts:
    return MrJsonArtifacts(
        changed_symbols=build_changed_symbols(ctx),
        impact_graph=build_impact_graph(ctx),
        runtime_impact=build_runtime_impact(ctx),
        test_impact=build_test_impact(ctx),
        boundary_hints=ctx.boundary_hints,
        mr_context=build_mr_context(ctx),
    )


def write_mr_json_artifacts(run_dir: Path, artifacts: MrJsonArtifacts) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "changed-symbols.json", artifacts.changed_symbols)
    write_json(run_dir / "impact-graph.json", artifacts.impact_graph)
    write_json(run_dir / "runtime-impact.json", artifacts.runtime_impact)
    write_json(run_dir / "test-impact.json", artifacts.test_impact)
    write_json(run_dir / "boundary-hints.json", artifacts.boundary_hints)
    write_json(run_dir / "mr-context.json", artifacts.mr_context)
