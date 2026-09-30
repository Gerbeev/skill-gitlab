from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from mr_impact.models import Edge, Symbol


class Adapter(ABC):
    name: str
    priority: int = 100

    @abstractmethod
    def matches(self, rel_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, rel_path: str, text: str) -> tuple[list[Symbol], list[Edge], list[str]]:
        raise NotImplementedError


def pick_adapter(adapters: list[Adapter], rel_path: str, text: str) -> Adapter | None:
    ordered = sorted(adapters, key=lambda a: a.priority)
    for adapter in ordered:
        if adapter.matches(rel_path):
            return adapter
    # Generic fallback always matches
    for adapter in ordered:
        if adapter.name == "generic":
            return adapter
    return None
