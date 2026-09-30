from __future__ import annotations

import re

from mr_impact.index.adapters.base import Adapter
from mr_impact.models import Edge, Symbol

_JOB_HEAD = re.compile(r"^\s*insert_job\s*:\s*(\S+)", re.I | re.M)
_JOB_TYPE = re.compile(r"^\s*job_type\s*:\s*(\S+)", re.I | re.M)
_BOX_NAME = re.compile(r"^\s*box_name\s*:\s*(\S+)", re.I | re.M)
_COMMAND = re.compile(r"^\s*command\s*:\s*(.+)$", re.I | re.M)
_MEMBER = re.compile(r"^\s*member\s*:\s*(\S+)", re.I | re.M)
_CONDITION_LINE = re.compile(r"^\s*condition\s*:\s*(.+)$", re.I | re.M)
_DEPENDS_LINE = re.compile(r"^\s*depend(?:s|ency|encies)\s*:\s*(.+)$", re.I | re.M)
_STATUS_JOB_REF = re.compile(r"\b[sfndt]\(\s*([^)]+?)\s*\)", re.I)
_PATH_IN_TEXT = re.compile(
    r"""([\w.-]+(?:/[\w.-]+)+\.(?:py|pl|sh|ps1|bat|cmd|sql|jil|scala|java|cs|jar|exe))""",
    re.I,
)

_CONDITION_SKIP = frozenset(
    {
        "AND",
        "OR",
        "NOT",
        "TRUE",
        "FALSE",
        "CMD",
        "BOX",
        "SQL",
        "SV",
        "S",
        "F",
        "D",
        "T",
        "N",
    }
)


def _job_refs_in_expression(expr: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in _STATUS_JOB_REF.finditer(expr):
        name = match.group(1).strip().strip("'\"")
        if name and name not in seen:
            seen.add(name)
            refs.append(name)
    for token in re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", expr):
        if token in _CONDITION_SKIP or token in seen:
            continue
        seen.add(token)
        refs.append(token)
    return refs


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

        for match in _CONDITION_LINE.finditer(text):
            expr = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            for job in _job_refs_in_expression(expr):
                edges.append(
                    Edge(
                        job,
                        "condition_dependency",
                        "high",
                        f"condition in {rel_path}",
                        line,
                        line,
                    )
                )

        for match in _DEPENDS_LINE.finditer(text):
            expr = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            for part in re.split(r"[,;&|]+", expr):
                job = part.strip().strip("'\"")
                if job and re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", job):
                    edges.append(
                        Edge(
                            job,
                            "depends_on",
                            "high",
                            f"depends in {rel_path}",
                            line,
                            line,
                        )
                    )

        if not symbols and not edges:
            notes.append("no JIL jobs parsed (format may differ)")
        return symbols, edges, notes
