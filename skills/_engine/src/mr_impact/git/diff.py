from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class ChangedFile:
    status: str
    path: str


@dataclass(frozen=True)
class LineRange:
    """Inclusive line range on the **head** revision of the file."""

    start: int
    end: int

    def overlaps(self, start: int, end: int) -> bool:
        return self.start <= end and self.end >= start


def list_changed_files(repo: Path, base_sha: str, head_sha: str) -> list[ChangedFile]:
    """Files that differ between two commits (git diff --name-status)."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "diff",
                "--name-status",
                f"{base_sha}..{head_sha}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise FileNotFoundError(f"git not available: {error}") from error
    if out.returncode != 0:
        raise ValueError(f"git diff failed: {out.stderr.strip() or out.stdout.strip()}")

    changed: list[ChangedFile] = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        path = parts[-1].strip()
        if status.startswith("R") and len(parts) >= 3:
            path = parts[2].strip()
        changed.append(ChangedFile(status=status, path=path.replace("\\", "/")))
    return changed


def changed_line_ranges(repo: Path, base_sha: str, head_sha: str) -> dict[str, list[LineRange]]:
    """Map repository-relative paths to line ranges touched on the head side."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "diff",
                "-U0",
                f"{base_sha}..{head_sha}",
                "--",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise FileNotFoundError(f"git not available: {error}") from error
    if out.returncode != 0:
        raise ValueError(f"git diff failed: {out.stderr.strip() or out.stdout.strip()}")

    ranges: dict[str, list[LineRange]] = {}
    current: str | None = None

    for line in out.stdout.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            if path == "/dev/null":
                current = None
            else:
                current = path.replace("\\", "/")
            continue
        if current is None:
            continue
        match = _HUNK.match(line)
        if not match:
            continue
        new_start = int(match.group(3))
        new_count = int(match.group(4) or "1")
        if new_count <= 0:
            continue
        end = new_start + new_count - 1
        ranges.setdefault(current, []).append(LineRange(new_start, end))

    return ranges


def serialize_line_ranges(ranges: dict[str, list[LineRange]]) -> dict[str, list[dict[str, int]]]:
    """JSON-friendly changed line ranges (merged per file)."""
    return _serialize_ranges(ranges)


def _serialize_ranges(ranges: dict[str, list[LineRange]]) -> dict[str, list[dict[str, int]]]:
    return {
        path: [{"start": r.start, "end": r.end} for r in merged]
        for path, merged in {p: _merge_ranges(rs) for p, rs in ranges.items()}.items()
    }


def _merge_ranges(ranges: list[LineRange]) -> list[LineRange]:
    if not ranges:
        return []
    ordered = sorted(ranges, key=lambda r: r.start)
    merged: list[LineRange] = [ordered[0]]
    for current in ordered[1:]:
        last = merged[-1]
        if current.start <= last.end + 1:
            merged[-1] = LineRange(last.start, max(last.end, current.end))
        else:
            merged.append(current)
    return merged


def symbols_touched_by_diff(
    symbols: list[dict],
    *,
    changed_paths: set[str],
    linked_paths: set[str],
    line_ranges: dict[str, list[LineRange]],
) -> list[dict]:
    """Keep symbols that overlap diff hunks, or live in linked (unchanged) JIL files."""
    normalized_changed = {p.replace("\\", "/") for p in changed_paths}
    normalized_linked = {p.replace("\\", "/") for p in linked_paths}
    touched: list[dict] = []

    for sym in symbols:
        path = str(sym.get("path", "")).replace("\\", "/")
        line_start = int(sym.get("line_start", 0))
        line_end = int(sym.get("line_end", line_start))

        if path in normalized_linked and path not in normalized_changed:
            touched.append({**sym, "diff_match": "linked_file"})
            continue
        if path not in normalized_changed:
            continue

        file_ranges = line_ranges.get(path) or []
        if not file_ranges:
            touched.append({**sym, "diff_match": "file"})
            continue

        if any(r.overlaps(line_start, line_end) for r in file_ranges):
            touched.append({**sym, "diff_match": "line"})
    return touched
