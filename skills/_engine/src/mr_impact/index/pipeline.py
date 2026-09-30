from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mr_impact.index.adapters import DEFAULT_ADAPTERS
from mr_impact.index.adapters.base import Adapter
from mr_impact.index.scanner import file_hash, git_head, list_repo_files
from mr_impact.index.store import IndexStore
from mr_impact.models import FileIndexResult
from mr_impact.readers import claims, derivation, readable, who


def language_for(rel_path: str) -> str:
    path = Path(rel_path)
    if claims(path) is not None:
        reader = claims(path)
        return getattr(reader, "NAME", "code")
    lower = rel_path.lower()
    if lower.endswith(".jil"):
        return "jil"
    if lower.endswith((".sql", ".pls", ".pck", ".pkb", ".pks")):
        return "sql"
    if lower.endswith(".cs"):
        return "csharp"
    if lower.endswith((".scala", ".sc")):
        return "scala"
    if lower.endswith(".java"):
        return "java"
    return path.suffix.lstrip(".") or "unknown"


def select_adapter(adapters: list[Adapter], rel_path: str) -> Adapter:
    ordered = sorted(adapters, key=lambda a: a.priority)
    for adapter in ordered:
        if adapter.name == "generic":
            continue
        if adapter.matches(rel_path):
            return adapter
    return ordered[-1]


def analysis_paths(project_root: Path, analysis_root: Path | None = None) -> tuple[Path, Path]:
    root = analysis_root or (project_root / ".repository-analysis")
    return root / "index", root / "graph"


def run_create_index(
    project_root: Path,
    *,
    analysis_root: Path | None = None,
) -> dict:
    """Scan repository and write only `.repository-analysis/index/` artifacts."""
    project_root = project_root.resolve()
    index_dir, _ = analysis_paths(project_root, analysis_root)
    index_dir.mkdir(parents=True, exist_ok=True)

    db_path = index_dir / "repository-index.sqlite"
    store = IndexStore(db_path)
    head = git_head(project_root)
    indexed_at = datetime.now(timezone.utc).isoformat()
    rel_files = list_repo_files(project_root)

    unread = 0
    skipped = 0
    parsed = 0

    for rel in rel_files:
        abs_path = project_root / rel
        try:
            digest = file_hash(abs_path)
            size = abs_path.stat().st_size
        except OSError:
            continue

        if store.file_hash(rel) == digest:
            skipped += 1
            continue

        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unread += 1
            continue

        adapter = select_adapter(DEFAULT_ADAPTERS, rel)
        if not readable(abs_path) and adapter.name == "generic":
            unread += 1

        symbols, edges, notes = adapter.analyze(rel, text)
        result = FileIndexResult(
            rel_path=rel,
            language=language_for(rel),
            adapter=adapter.name,
            content_hash=digest,
            symbols=symbols,
            edges=edges,
            notes=notes,
        )
        store.replace_file(result, size, indexed_at)
        parsed += 1

    store.remove_paths_not_in(set(rel_files))
    store.set_meta("git_head", head or "")
    store.set_meta("indexed_at", indexed_at)
    store.set_meta("mode", "deep")
    store.set_meta("reader_derivation", derivation())
    store.commit()

    summary = store.export_summary()
    summary["git_head"] = head
    summary["indexed_at"] = indexed_at
    summary["mode"] = "deep"
    summary["artifact"] = "index"
    summary["files_scanned"] = len(rel_files)
    summary["files_parsed_this_run"] = parsed
    summary["files_unchanged_skipped"] = skipped
    summary["files_unread_or_generic_only"] = unread
    summary["readers"] = who()

    _write_json(index_dir / "repository-index.json", summary)
    _write_json(
        index_dir / "index-manifest.json",
        {
            "schema_version": 1,
            "git_head": head,
            "indexed_at": indexed_at,
            "mode": "deep",
            "reader_derivation": derivation(),
            "paths": {
                "sqlite": "repository-index.sqlite",
                "summary": "repository-index.json",
            },
            "stats": store.stats(),
        },
    )

    store.close()
    return summary


def run_create_graph(
    project_root: Path,
    *,
    analysis_root: Path | None = None,
) -> dict:
    """Export `.repository-analysis/graph/` from existing index SQLite."""
    project_root = project_root.resolve()
    index_dir, graph_dir = analysis_paths(project_root, analysis_root)
    graph_dir.mkdir(parents=True, exist_ok=True)
    db_path = index_dir / "repository-index.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(
            f"index missing: {db_path} — run create-index before create-graph"
        )

    store = IndexStore(db_path)
    head = store.get_meta("git_head") or git_head(project_root)
    indexed_at = store.get_meta("indexed_at") or datetime.now(timezone.utc).isoformat()
    built_at = datetime.now(timezone.utc).isoformat()

    graph = {
        "schema_version": 1,
        "git_head": head,
        "indexed_at": indexed_at,
        "built_at": built_at,
        "source_sqlite": "index/repository-index.sqlite",
        "nodes": store.iter_graph_nodes(),
        "edges": store.iter_graph_edges(),
    }
    _write_json(graph_dir / "dependency-graph.json", graph)
    manifest = {
        "schema_version": 1,
        "git_head": head,
        "indexed_at": indexed_at,
        "built_at": built_at,
        "edge_count": len(graph["edges"]),
        "node_count": len(graph["nodes"]),
        "source_index_manifest": "index/index-manifest.json",
    }
    _write_json(graph_dir / "graph-manifest.json", manifest)

    store.close()
    return {
        "artifact": "graph",
        "git_head": head,
        "indexed_at": indexed_at,
        "built_at": built_at,
        "edge_count": manifest["edge_count"],
        "node_count": manifest["node_count"],
    }


def run_deep_index(
    project_root: Path,
    *,
    analysis_root: Path | None = None,
) -> dict:
    """Legacy: index then graph (prefer separate CLI commands)."""
    summary = run_create_index(project_root, analysis_root=analysis_root)
    graph = run_create_graph(project_root, analysis_root=analysis_root)
    summary["graph"] = graph
    return summary


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
