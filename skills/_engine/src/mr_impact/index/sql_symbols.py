from __future__ import annotations

import re

from mr_impact.models import Symbol

_PACKAGE_BODY = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY\s+((?:\"[^\"]+\"|\w+))",
    re.I,
)
_PLSQL_ROUTINE = re.compile(r"\b(PROCEDURE|FUNCTION)\s+(\w+)\b", re.I)
_END_ROUTINE = re.compile(r"\bEND\s+(\w+)\s*;", re.I)


def _clean_pkg(raw: str) -> str:
    return raw.replace('"', "").strip()


def plsql_routine_symbols(text: str) -> list[Symbol]:
    """Package-body PROCEDURE/FUNCTION symbols with line spans (for diff overlap)."""
    symbols: list[Symbol] = []
    current_pkg: str | None = None
    lines = text.splitlines()
    open_routine: tuple[str, str, int] | None = None  # kind, name, start_line

    for idx, line in enumerate(lines, start=1):
        pkg_match = _PACKAGE_BODY.search(line)
        if pkg_match:
            current_pkg = _clean_pkg(pkg_match.group(1))
            open_routine = None
            continue

        if open_routine is None:
            routine_match = _PLSQL_ROUTINE.search(line)
            if routine_match and current_pkg:
                kind, name = routine_match.group(1).lower(), routine_match.group(2)
                open_routine = (kind, name, idx)
            continue

        end_match = _END_ROUTINE.search(line)
        if end_match and end_match.group(1).lower() == open_routine[1].lower():
            kind, name, start = open_routine
            sym_name = f"{current_pkg}.{name}" if current_pkg else name
            sym_kind = f"oracle_{kind}"
            symbols.append(Symbol(sym_name, sym_kind, start, idx))
            open_routine = None

    return symbols
