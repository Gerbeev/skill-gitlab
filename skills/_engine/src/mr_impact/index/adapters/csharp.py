from __future__ import annotations

import re
from pathlib import Path

from mr_impact.index.adapters.base import Adapter
from mr_impact.index.sql_literals import sql_call_edges_from_literals
from mr_impact.models import Edge, Symbol
from mr_impact.readers import claims, read as reader_read

_PACKAGE_REF = re.compile(r"<PackageReference\s+Include=\"([^\"]+)\"", re.I)
_PROJECT_REF = re.compile(r"<ProjectReference\s+Include=\"([^\"]+)\"", re.I)
_USING = re.compile(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;", re.M)
_NAMESPACE = re.compile(r"^\s*namespace\s+([\w.]+)\s*;?", re.M)
_TYPE_DECL = re.compile(
    r"\b(?:public|private|internal|protected)?\s*(?:partial\s+)?"
    r"(class|interface|record|struct|enum)\s+(\w+)",
    re.I,
)
_METHOD_DECL = re.compile(
    r"\b(?:public|private|internal|protected)?\s*(?:static\s+)?(?:async\s+)?"
    r"[\w<>,\[\]?]+\s+(\w+)\s*\([^;{}]*\)\s*(?:=>|{)",
    re.M,
)

_CALL_CONFIDENCE = {
    "import": "high",
    "typed": "high",
    "name": "medium",
    "attribute": "low",
}


class CSharpAdapter(Adapter):
    name = "csharp"
    priority = 18

    def matches(self, rel_path: str) -> bool:
        lower = rel_path.lower()
        return lower.endswith(".cs") or lower.endswith(".csproj")

    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        lower = rel_path.lower()
        if lower.endswith(".csproj"):
            return self._analyze_csproj(rel_path, text)
        return self._analyze_cs(rel_path, text)

    def _analyze_csproj(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        symbols: list[Symbol] = []
        edges: list[Edge] = []
        stem = Path(rel_path).stem
        symbols.append(Symbol(stem, "csharp_project", 1, 1))

        for match in _PACKAGE_REF.finditer(text):
            line = text[: match.start()].count("\n") + 1
            edges.append(
                Edge(
                    match.group(1),
                    "package_reference",
                    "high",
                    f"PackageReference in {rel_path}",
                    line,
                    line,
                )
            )

        for match in _PROJECT_REF.finditer(text):
            line = text[: match.start()].count("\n") + 1
            target = match.group(1).replace("\\", "/")
            edges.append(
                Edge(
                    target,
                    "project_reference",
                    "high",
                    f"ProjectReference in {rel_path}",
                    line,
                    line,
                )
            )

        return symbols, edges, []

    def _analyze_cs(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        if claims(Path(rel_path)) is not None:
            return self._analyze_cs_treesitter(rel_path, text)
        return self._analyze_cs_regex(rel_path, text)

    def _analyze_cs_treesitter(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        defines, calls, unresolved = reader_read(rel_path, text)
        symbols: list[Symbol] = []
        edges: list[Edge] = []

        for name, start, end in defines:
            symbols.append(Symbol(name, "csharp_definition", start, end))

        seen_sql: set[str] = set()
        for name, kind, start, end in calls:
            if kind == "import":
                edge_type = "csharp_using"
            else:
                edge_type = "calls"
            conf = _CALL_CONFIDENCE.get(kind, "low")
            edges.append(Edge(name, edge_type, conf, rel_path, start, end))
        edges.extend(sql_call_edges_from_literals(rel_path, text, seen=seen_sql))

        notes = [f"unresolved: {u}" for u in unresolved] if unresolved else []
        notes.append("reader: tree-sitter")
        return symbols, edges, notes

    def _analyze_cs_regex(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        symbols: list[Symbol] = []
        edges: list[Edge] = []
        seen_sym: set[str] = set()

        for match in _NAMESPACE.finditer(text):
            name = match.group(1)
            line = text[: match.start()].count("\n") + 1
            key = f"ns:{name}"
            if key not in seen_sym:
                seen_sym.add(key)
                symbols.append(Symbol(name, "csharp_namespace", line, line))

        for match in _TYPE_DECL.finditer(text):
            kind, name = match.group(1).lower(), match.group(2)
            line = text[: match.start()].count("\n") + 1
            key = f"type:{name}"
            if key not in seen_sym:
                seen_sym.add(key)
                symbols.append(Symbol(name, f"csharp_{kind}", line, line))

        for match in _METHOD_DECL.finditer(text):
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            line = text[: match.start()].count("\n") + 1
            key = f"method:{name}"
            if key not in seen_sym:
                seen_sym.add(key)
                symbols.append(Symbol(name, "csharp_method", line, line))

        for match in _USING.finditer(text):
            ns = match.group(1)
            line = text[: match.start()].count("\n") + 1
            edges.append(
                Edge(
                    ns,
                    "csharp_using",
                    "high",
                    f"using in {rel_path}",
                    line,
                    line,
                )
            )

        seen_sql: set[str] = set()
        edges.extend(sql_call_edges_from_literals(rel_path, text, seen=seen_sql))

        notes = ["reader: regex-fallback (install tree-sitter-c-sharp for richer C# edges)"]
        return symbols, edges, notes
