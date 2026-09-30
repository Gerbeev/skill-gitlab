from __future__ import annotations

from pathlib import Path

from mr_impact.index.adapters.base import Adapter
from mr_impact.models import Edge, Symbol
from mr_impact.readers import claims, read as reader_read


class ReadersBridgeAdapter(Adapter):
    name = "readers"
    priority = 30

    def matches(self, rel_path: str) -> bool:
        return claims(Path(rel_path)) is not None

    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        defines, calls, unresolved = reader_read(rel_path, text)
        symbols: list[Symbol] = []
        edges: list[Edge] = []

        for name, start, end in defines:
            kind = "definition"
            symbols.append(Symbol(name, kind, start, end))

        confidence_map = {
            "import": "high",
            "typed": "high",
            "name": "medium",
            "attribute": "low",
        }
        for name, kind, start, end in calls:
            conf = confidence_map.get(kind, "low")
            edges.append(
                Edge(
                    name,
                    kind,
                    conf,
                    f"{rel_path}",
                    start,
                    end,
                )
            )

        notes = [f"unresolved: {u}" for u in unresolved] if unresolved else []
        return symbols, edges, notes
