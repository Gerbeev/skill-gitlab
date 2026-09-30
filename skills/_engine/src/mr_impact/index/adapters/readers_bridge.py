from __future__ import annotations

from pathlib import Path

from mr_impact.index.adapters.base import Adapter
from mr_impact.index.adapters.reader_calls import edges_from_reader_calls
from mr_impact.index.sql_literals import sql_call_edges_from_literals
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

        seen_sql: set[str] = set()
        edges.extend(edges_from_reader_calls(rel_path, calls, import_edge_type="import"))
        edges.extend(sql_call_edges_from_literals(rel_path, text, seen=seen_sql))

        notes = [f"unresolved: {u}" for u in unresolved] if unresolved else []
        return symbols, edges, notes
