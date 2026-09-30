from __future__ import annotations

import re

from mr_impact.index.adapters.base import Adapter
from mr_impact.models import Edge, Symbol

_CREATE = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?"
    r"(PROCEDURE|FUNCTION|PACKAGE(?:\s+BODY)?|TRIGGER|TABLE|VIEW|TYPE)\s+"
    r"((?:\"[^\"]+\"|\w+)(?:\s*\.\s*(?:\"[^\"]+\"|\w+))*)",
    re.I,
)
_FROM_JOIN = re.compile(r"\b(?:FROM|JOIN)\s+((?:\"[^\"]+\"|\w+)(?:\s*\.\s*(?:\"[^\"]+\"|\w+))*)", re.I)


class SqlAdapter(Adapter):
    name = "sql"
    priority = 20

    _EXT = {".sql", ".pls", ".plb", ".pck", ".pkb", ".pks", ".ddl"}

    def matches(self, rel_path: str) -> bool:
        lower = rel_path.lower()
        return any(lower.endswith(ext) for ext in self._EXT) or "/sql/" in lower

    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        symbols: list[Symbol] = []
        edges: list[Edge] = []
        seen: set[str] = set()

        for match in _CREATE.finditer(text):
            kind = match.group(1).upper()
            name = match.group(2).replace('"', "").replace(" ", "")
            line = text[: match.start()].count("\n") + 1
            sym_kind = f"oracle_{kind.lower().replace(' ', '_')}"
            symbols.append(Symbol(name, sym_kind, line, line))

        for match in _FROM_JOIN.finditer(text):
            name = match.group(1).replace('"', "").replace(" ", "")
            line = text[: match.start()].count("\n") + 1
            key = f"{name}:{line}"
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                Edge(
                    name,
                    "sql_reference",
                    "low",
                    f"FROM/JOIN in {rel_path}",
                    line,
                    line,
                )
            )

        return symbols, edges, []
