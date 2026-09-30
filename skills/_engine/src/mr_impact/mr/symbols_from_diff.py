"""Resolve MR diff symbols from the repository index (reindex, JIL links, filters)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mr_impact.git.diff import ChangedFile, LineRange, symbols_touched_by_diff
from mr_impact.graph.nearest_runtime import jobs_for_jil_script
from mr_impact.index.pipeline import reindex_changed_paths
from mr_impact.index.scanner import git_head
from mr_impact.index.store import IndexStore


@dataclass(frozen=True, slots=True)
class MrSymbolContext:
    indexed_head: str
    partial_refresh: dict | None
    all_edges: list[dict]
    all_symbols: list[dict]
    symbols: list[dict]
    jil_sources: set[str]


def _normalize_paths(paths: set[str]) -> set[str]:
    return {p.replace("\\", "/") for p in paths}


def jil_sources_for_changed_paths(changed_paths: set[str], edges: list[dict]) -> set[str]:
    """JIL files whose script_path targets overlap MR changed paths."""
    normalized = _normalize_paths(changed_paths)
    sources: set[str] = set()
    for edge in edges:
        if edge.get("type") != "script_path":
            continue
        target = str(edge.get("target", "")).replace("\\", "/")
        if any(
            target == cp or target.endswith("/" + cp) or cp.endswith("/" + target) or cp == target
            for cp in normalized
        ):
            sources.add(str(edge.get("from_file", "")))
    return sources


def filter_linked_job_symbols(
    symbols: list[dict],
    changed_paths: set[str],
    edges: list[dict],
) -> list[dict]:
    """Drop linked JIL jobs that are not tied to changed script/SQL paths."""
    normalized_changed = _normalize_paths(changed_paths)
    kept: list[dict] = []
    for sym in symbols:
        if sym.get("diff_match") != "linked_file" or sym.get("kind") != "autosys_job":
            kept.append(sym)
            continue
        jil = str(sym.get("path", "")).replace("\\", "/")
        job = str(sym.get("name", ""))
        script_hint: str | None = None
        for cp in normalized_changed:
            for edge in edges:
                if edge.get("from_file") != jil or edge.get("type") != "script_path":
                    continue
                target = str(edge.get("target", "")).replace("\\", "/")
                if target == cp or target.endswith("/" + cp) or cp.endswith("/" + target):
                    script_hint = cp
                    break
            if script_hint:
                break
        if not script_hint:
            continue
        matching_jobs = jobs_for_jil_script(edges, symbols, jil, script_hint)
        if job in matching_jobs:
            kept.append(sym)
    return kept


def impact_seeds_from_diff(changed_paths: set[str], symbols: list[dict]) -> set[str]:
    seeds: set[str] = set()
    for path in changed_paths:
        seeds.add(path)
        seeds.add(Path(path).name)
    for sym in symbols:
        seeds.add(sym["name"])
    return seeds


def prepare_mr_symbol_context(
    project_root: Path,
    db_path: Path,
    *,
    changed: list[ChangedFile],
    changed_paths: set[str],
    diff_line_ranges: dict[str, list[LineRange]],
    analysis_root: Path | None,
    repo_head: str | None,
) -> MrSymbolContext:
    """Refresh stale index paths when needed, then load diff-accurate symbols."""
    if repo_head is None:
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
    all_symbols = store.all_symbols()
    jil_sources = jil_sources_for_changed_paths(changed_paths, all_edges)
    symbol_paths = changed_paths | jil_sources
    symbols_all = store.symbols_for_paths(symbol_paths)
    symbols = symbols_touched_by_diff(
        symbols_all,
        changed_paths=changed_paths,
        linked_paths=jil_sources,
        line_ranges=diff_line_ranges,
    )
    symbols = filter_linked_job_symbols(symbols, changed_paths, all_edges)
    store.close()

    return MrSymbolContext(
        indexed_head=indexed_head,
        partial_refresh=partial_refresh,
        all_edges=all_edges,
        all_symbols=all_symbols,
        symbols=symbols,
        jil_sources=jil_sources,
    )
