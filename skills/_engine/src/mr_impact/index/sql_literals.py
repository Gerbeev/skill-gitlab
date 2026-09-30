from __future__ import annotations

import re

from mr_impact.models import Edge

_MEMBER_IN_TEXT = re.compile(r"\b(\w+)\s*\.\s*(\w+)\b")

_SKIP_PACKAGES = frozenset({"sys", "dbms_output", "system"})


def _scan_fragment(fragment: str, rel_path: str, line: int, seen: set[str], confidence: str) -> list[Edge]:
    edges: list[Edge] = []
    for match in _MEMBER_IN_TEXT.finditer(fragment):
        pkg, member = match.group(1), match.group(2)
        if pkg.lower() in _SKIP_PACKAGES:
            continue
        target = f"{pkg}.{member}"
        key = f"sql_literal:{target}:{line}"
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            Edge(
                target,
                "sql_call",
                confidence,
                f"pkg.member literal in {rel_path}",
                line,
                line,
            )
        )
    return edges


def sql_call_edges_from_literals(
    rel_path: str,
    text: str,
    *,
    seen: set[str],
    confidence: str = "medium",
) -> list[Edge]:
    edges: list[Edge] = []
    for match in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text):
        line = text[: match.start()].count("\n") + 1
        edges.extend(_scan_fragment(match.group(1), rel_path, line, seen, confidence))
    for match in re.finditer(r"'([^'\\]*(?:\\.[^'\\]*)*)'", text):
        line = text[: match.start()].count("\n") + 1
        edges.extend(_scan_fragment(match.group(1), rel_path, line, seen, confidence))
    for match in re.finditer(r'@"((?:[^"]|"")*)"', text):
        line = text[: match.start()].count("\n") + 1
        content = match.group(1).replace('""', '"')
        edges.extend(_scan_fragment(content, rel_path, line, seen, confidence))
    return edges
