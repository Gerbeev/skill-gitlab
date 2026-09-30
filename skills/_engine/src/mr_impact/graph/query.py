from __future__ import annotations

import json
import sqlite3
from collections import deque
from pathlib import Path


def _load_edges_sqlite(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT path, target, edge_type, confidence, evidence, line_start, line_end FROM edges"
    ).fetchall()
    conn.close()
    return [
        {
            "from_file": r[0],
            "target": r[1],
            "type": r[2],
            "confidence": r[3],
            "evidence": r[4],
            "line_start": r[5],
            "line_end": r[6],
        }
        for r in rows
    ]


def _load_edges_json(graph_path: Path) -> list[dict]:
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = data.get("edges") or []
    normalized = []
    for edge in edges:
        if "from_file" in edge:
            normalized.append(edge)
        elif "from" in edge:
            normalized.append({**edge, "from_file": edge.get("from")})
    return normalized


def anchored_paths(
    project_root: Path,
    anchors: set[str],
    *,
    max_depth: int = 10,
    max_nodes: int = 200,
) -> list[dict]:
    """Bounded BFS from anchor names across indexed edges (sqlite or graph json)."""
    if not anchors:
        return []

    root = project_root / ".repository-analysis"
    db = root / "index" / "repository-index.sqlite"
    graph = root / "graph" / "dependency-graph.json"

    edges: list[dict] = []
    if db.is_file():
        edges = _load_edges_sqlite(db)
    elif graph.is_file():
        edges = _load_edges_json(graph)
    else:
        return []

    anchor_lower = {a.lower() for a in anchors}
    # seed: edges where target or from_file matches anchor
    queue: deque[tuple[str, int, list[dict]]] = deque()
    seen: set[str] = set()
    results: list[dict] = []

    for edge in edges:
        target = str(edge.get("target", ""))
        source = str(edge.get("from_file", ""))
        if target.lower() in anchor_lower or any(a in source.lower() for a in anchor_lower):
            key = f"{source}|{target}|{edge.get('type')}"
            if key not in seen:
                seen.add(key)
                queue.append((target, 1, [edge]))
                results.append(edge)

    while queue and len(results) < max_nodes:
        node, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in edges:
            if str(edge.get("target", "")).lower() != node.lower() and node not in str(
                edge.get("from_file", "")
            ):
                continue
            nxt = str(edge.get("target", ""))
            key = "|".join(f"{e.get('from_file')}->{e.get('target')}" for e in path + [edge])
            if key in seen:
                continue
            seen.add(key)
            results.append(edge)
            if len(results) >= max_nodes:
                break
            queue.append((nxt, depth + 1, path + [edge]))

    return results[:max_nodes]


def impact_from_seeds(
    project_root: Path,
    seeds: set[str],
    *,
    max_depth: int = 10,
    max_nodes: int = 200,
) -> list[dict]:
    """Bounded traversal from changed paths, symbols, or graph targets."""
    return anchored_paths(project_root, seeds, max_depth=max_depth, max_nodes=max_nodes)
