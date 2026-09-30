"""Map tree-sitter reader call tuples to index edges (shared by C# and readers bridge)."""

from __future__ import annotations

from mr_impact.models import Edge

READER_CALL_CONFIDENCE: dict[str, str] = {
    "import": "high",
    "typed": "high",
    "name": "medium",
    "attribute": "low",
}


def edges_from_reader_calls(
    rel_path: str,
    calls: list[tuple[str, str, int, int]],
    *,
    import_edge_type: str,
) -> list[Edge]:
    """Build call/import edges from ``reader_read`` call tuples ``(name, kind, start, end)``."""
    edges: list[Edge] = []
    for name, kind, start, end in calls:
        conf = READER_CALL_CONFIDENCE.get(kind, "low")
        edge_type = import_edge_type if kind == "import" else "calls"
        edges.append(Edge(name, edge_type, conf, rel_path, start, end))
    return edges
