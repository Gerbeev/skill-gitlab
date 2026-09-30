from __future__ import annotations

import re

from mr_impact.index.adapters.base import Adapter
from mr_impact.models import Edge, Symbol

_JOB_HEAD = re.compile(r"^\s*insert_job\s*:\s*(\S+)", re.I | re.M)
_JOB_TYPE = re.compile(r"^\s*job_type\s*:\s*(\S+)", re.I | re.M)
_BOX_NAME = re.compile(r"^\s*box_name\s*:\s*(\S+)", re.I | re.M)
_COMMAND = re.compile(r"^\s*command\s*:\s*(.+)$", re.I | re.M)
_MEMBER = re.compile(r"^\s*member\s*:\s*(\S+)", re.I | re.M)
_CONDITION = re.compile(r"\b(\w+)\s*[=<>!]", re.I)
_PATH_IN_TEXT = re.compile(
    r"""([\w.-]+(?:/[\w.-]+)+\.(?:py|pl|sh|ps1|bat|cmd|sql|jil|scala|java|cs|jar|exe))""",
    re.I,
)


class JilAdapter(Adapter):
    name = "jil"
    priority = 10

    def matches(self, rel_path: str) -> bool:
        path = rel_path.lower()
        return path.endswith(".jil") or "/jil/" in path or path.endswith(".job")

    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        symbols: list[Symbol] = []
        edges: list[Edge] = []
        notes: list[str] = []

        for match in _JOB_HEAD.finditer(text):
            job = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            symbols.append(Symbol(job, "autosys_job", line, line))

        for match in _JOB_TYPE.finditer(text):
            jtype = match.group(1).strip().upper()
            line = text[: match.start()].count("\n") + 1
            if jtype == "BOX":
                symbols.append(Symbol(f"box@{rel_path}:{line}", "autosys_box", line, line))

        for match in _BOX_NAME.finditer(text):
            box = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            edges.append(
                Edge(
                    box,
                    "box_parent",
                    "high",
                    f"box_name in {rel_path}",
                    line,
                    line,
                )
            )

        for match in _MEMBER.finditer(text):
            member = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            edges.append(
                Edge(
                    member,
                    "box_member",
                    "high",
                    f"member in {rel_path}",
                    line,
                    line,
                )
            )

        for match in _COMMAND.finditer(text):
            cmd = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            for path_match in _PATH_IN_TEXT.finditer(cmd):
                target = path_match.group(1).strip("'\"")
                edges.append(
                    Edge(
                        target,
                        "script_path",
                        "medium",
                        f"command in {rel_path}",
                        line,
                        line,
                    )
                )
            for token in re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", cmd):
                if token not in {"CMD", "BOX", "SQL", "TRUE", "FALSE"}:
                    edges.append(
                        Edge(
                            token,
                            "job_reference",
                            "low",
                            f"token in command ({rel_path})",
                            line,
                            line,
                        )
                    )

        if not symbols and not edges:
            notes.append("no JIL jobs parsed (format may differ)")
        return symbols, edges, notes
