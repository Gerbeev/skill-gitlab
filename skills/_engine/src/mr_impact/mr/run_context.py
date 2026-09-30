"""Shared inputs for MR JSON payloads and markdown reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mr_impact.git.diff import ChangedFile


@dataclass(frozen=True, slots=True)
class MrRunContext:
    now: str
    revision: str
    base_sha: str
    head_sha: str
    changed: list[ChangedFile]
    symbols: list[dict]
    indexed_head: str
    repo_head: str | None
    index_stale: bool
    partial_refresh: dict | None
    issue_dir: Path | None
    graph_json_present: bool
    boundary_catalog_present: bool
    seeds: set[str]
    impact_edges: list[dict]
    primary_qa: list[dict]
    runtime: list[dict]
    unresolved: list[dict]
    boundary_hints: dict
    serialized_line_ranges: dict[str, list[dict]]
