"""Versioned, technology-neutral records shared by all operations."""

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any

SCHEMA_VERSION = 1
ADAPTER_VERSION = "1"


class Confidence(IntEnum):
    CANDIDATE = 30
    PROBABLE = 60
    STRONG = 90
    EXACT = 100


@dataclass(frozen=True)
class Evidence:
    file: str
    start_line: int
    end_line: int
    detector: str
    confidence: int = Confidence.STRONG
    revision: str = ""

    def __post_init__(self):
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("Invalid evidence line range")
        if not 0 <= self.confidence <= 100:
            raise ValueError("Invalid evidence confidence")


@dataclass
class Node:
    key: str
    type: str
    name: str
    evidence: Evidence
    boundary: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Symbol:
    id: str
    file: str
    qualified_name: str
    type: str
    start_line: int
    end_line: int
    language: str
    signature: str = ""
    confidence: int = Confidence.STRONG


@dataclass
class Edge:
    source: str
    target: str
    type: str
    evidence: Evidence


@dataclass
class ParsedFile:
    nodes: list[Node] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FileRecord:
    path: str
    identity: str
    size: int
    language: str


@dataclass
class RepositoryState:
    repository_id: str
    root: str
    commit: str
    mode: str
    fingerprint: str
    config: dict[str, Any]
    schema_version: int = SCHEMA_VERSION
    adapter_version: str = ADAPTER_VERSION


@dataclass
class BoundaryEntity:
    entity: str
    type: str
    role: str
    source: str
    confidence: int
    evidence: dict[str, Any]


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


@dataclass
class Change:
    old_path: str | None
    new_path: str | None
    status: str
    hunks: list[Hunk] = field(default_factory=list)
    binary: bool = False


@dataclass
class Limits:
    max_depth: int = 8
    max_nodes: int = 1000
    max_edges: int = 4000
    confidence: int = 30
    edge_types: tuple[str, ...] = ()
    max_candidates: int = 20
    cross_depth: int = 2

    def __post_init__(self):
        if not (0 <= self.max_depth <= 100 and 1 <= self.max_nodes <= 100000
                and 1 <= self.max_edges <= 1000000 and 0 <= self.confidence <= 100
                and 0 <= self.max_candidates <= 1000 and 0 <= self.cross_depth <= 10):
            raise ValueError("Invalid traversal limits")


@dataclass
class RuntimeTarget:
    target: str
    type: str
    repository: str
    impact: str
    reason: str
    path: list[dict[str, Any]]
    confidence: int
    execute: str
    verify: list[str]
    entity: str = ""


@dataclass
class ReportInput:
    repository: str
    base: str | None
    head: str
    changes: list[Change]
    warnings: list[str] = field(default_factory=list)


def record(value):
    return asdict(value)
