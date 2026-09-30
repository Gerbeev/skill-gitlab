from __future__ import annotations

import re

from mr_impact.index.adapters.base import Adapter
from mr_impact.models import Edge, Symbol

_PATH = re.compile(
    r"""(?P<path>(?:\./|\../|[A-Za-z]:\\|[/"'])?[\w./\\-]+\.(?:py|cs|sql|jil|scala|java|kt|xml|yaml|yml|json|ps1|sh|bat|cmd))""",
    re.I,
)
_JOB_TOKEN = re.compile(r"\bAUTOSYS[_A-Z0-9]{3,}\b")
_PACKAGE_REF = re.compile(r"<(?:PackageReference|ProjectReference)\s+Include=\"([^\"]+)\"", re.I)


class GenericAdapter(Adapter):
    name = "generic"
    priority = 1000

    def matches(self, rel_path: str) -> bool:
        return True

    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        symbols: list[Symbol] = []
        edges: list[Edge] = []
        lower = rel_path.lower()

        if lower.endswith(".csproj") or lower.endswith(".fsproj"):
            for match in _PACKAGE_REF.finditer(text):
                pkg = match.group(1)
                line = text[: match.start()].count("\n") + 1
                edges.append(Edge(pkg, "package_reference", "medium", rel_path, line, line))

        if not lower.endswith(".md"):
            for match in _PATH.finditer(text):
                target = match.group("path").strip("'\"")
                line = text[: match.start()].count("\n") + 1
                edges.append(
                    Edge(
                        target,
                        "path_literal",
                        "low",
                        f"literal path in {rel_path}",
                        line,
                        line,
                    )
                )

        for match in _JOB_TOKEN.finditer(text):
            line = text[: match.start()].count("\n") + 1
            edges.append(
                Edge(
                    match.group(0),
                    "autosys_mention",
                    "low",
                    f"mention in {rel_path}",
                    line,
                    line,
                )
            )

        if lower.endswith((".yaml", ".yml", ".xml", ".config", ".props", ".toml")):
            from pathlib import Path

            symbols.append(Symbol(Path(rel_path).stem, "config_file", 1, 1))

        return symbols, edges, []
