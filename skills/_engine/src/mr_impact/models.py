from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class Edge:
    target: str
    edge_type: str
    confidence: str
    evidence: str
    line_start: int
    line_end: int


@dataclass
class FileIndexResult:
    rel_path: str
    language: str
    adapter: str
    content_hash: str
    symbols: list[Symbol] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
