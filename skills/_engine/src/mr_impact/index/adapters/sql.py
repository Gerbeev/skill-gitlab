from __future__ import annotations

import re

from mr_impact.index.adapters.base import Adapter
from mr_impact.index.sql_literals import sql_call_edges_from_literals
from mr_impact.index.sql_symbols import plsql_routine_symbols
from mr_impact.models import Edge, Symbol

_CREATE = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?"
    r"(PROCEDURE|FUNCTION|PACKAGE(?:\s+BODY)?|TRIGGER|TABLE|VIEW|TYPE)\s+"
    r"((?:\"[^\"]+\"|\w+)(?:\s*\.\s*(?:\"[^\"]+\"|\w+))*)",
    re.I,
)
_FROM_JOIN = re.compile(r"\b(?:FROM|JOIN)\s+((?:\"[^\"]+\"|\w+)(?:\s*\.\s*(?:\"[^\"]+\"|\w+))*)", re.I)
_CALL_EXEC = re.compile(
    r"\b(?:CALL|EXEC(?:UTE)?)\s+((?:\"[^\"]+\"|\w+)(?:\s*\.\s*(?:\"[^\"]+\"|\w+))*)",
    re.I,
)
_PKG_MEMBER_CALL = re.compile(
    r"\b((?:\"[^\"]+\"|\w+)\s*\.\s*(?:\"[^\"]+\"|\w+))\s*(?:\(|;)",
    re.I,
)

_SQL_SKIP_TARGETS = frozenset({"DUAL", "SYS", "DBMS_OUTPUT", "UTL_FILE", "SQL", "IMMEDIATE"})


def _normalize_sql_name(raw: str) -> str:
    return raw.replace('"', "").replace(" ", "")


def _add_sql_edge(
    edges: list[Edge],
    seen: set[str],
    target: str,
    edge_type: str,
    confidence: str,
    evidence: str,
    line: int,
) -> None:
    name = _normalize_sql_name(target)
    if not name:
        return
    base = name.split(".")[-1].upper()
    if base in _SQL_SKIP_TARGETS:
        return
    key = f"{edge_type}:{name}:{line}"
    if key in seen:
        return
    seen.add(key)
    edges.append(Edge(name, edge_type, confidence, evidence, line, line))


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

        symbols.extend(plsql_routine_symbols(text))

        for match in _FROM_JOIN.finditer(text):
            line = text[: match.start()].count("\n") + 1
            _add_sql_edge(
                edges,
                seen,
                match.group(1),
                "sql_reference",
                "low",
                f"FROM/JOIN in {rel_path}",
                line,
            )

        for match in _CALL_EXEC.finditer(text):
            line = text[: match.start()].count("\n") + 1
            _add_sql_edge(
                edges,
                seen,
                match.group(1),
                "sql_call",
                "medium",
                f"CALL/EXEC in {rel_path}",
                line,
            )

        for match in _PKG_MEMBER_CALL.finditer(text):
            line = text[: match.start()].count("\n") + 1
            _add_sql_edge(
                edges,
                seen,
                match.group(1),
                "sql_call",
                "medium",
                f"package member call in {rel_path}",
                line,
            )

        edges.extend(sql_call_edges_from_literals(rel_path, text, seen=seen))

        return symbols, edges, []
