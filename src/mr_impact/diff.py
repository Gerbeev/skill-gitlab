"""Deterministic unified-diff extraction and before/after symbol mapping."""

import ast
import re

from .models import Change, Hunk
from .safety import EngineError, safe_relative


def patch_path(value: str, prefix=True):
    value = value.split("\t", 1)[0].strip()
    if value == "/dev/null":
        return None
    if value.startswith('"'):
        try:
            value = ast.literal_eval(value)
            # Git's quoted names use UTF-8 bytes represented as octal escapes.
            try:
                value = value.encode("latin1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        except (SyntaxError, ValueError) as exc:
            raise EngineError("Invalid quoted diff path") from exc
    if prefix and value.startswith(("a/", "b/")):
        value = value[2:]
    return safe_relative(value)


def parse_diff(text: str) -> list[Change]:
    changes, current, hunk = [], None, None
    old_seen = new_seen = 0

    def validate_hunk():
        if hunk and (old_seen != hunk.old_count or new_seen != hunk.new_count):
            raise EngineError("Malformed unified diff: hunk counts do not match payload")

    for line in text.splitlines():
        if line.startswith("diff --git "):
            validate_hunk()
            hunk = None
            current = Change(None, None, "modified")
            changes.append(current)
            # Standard paths can be recovered even for mode-only or binary changes.
            value = line[len("diff --git "):]
            if value.startswith('"'):
                tokens = re.findall(r'"(?:\\.|[^"\\])*"|\S+', value)
                if len(tokens) == 2:
                    current.old_path, current.new_path = map(patch_path, tokens)
            elif " b/" in value:
                left, right = value.split(" b/", 1)
                current.old_path, current.new_path = patch_path(left), patch_path("b/" + right)
            continue
        # Ordinary unified patches may omit diff --git headers.
        if line.startswith("--- ") and (hunk is None or old_seen == hunk.old_count and new_seen == hunk.new_count):
            validate_hunk()
            hunk = None
            if current is None or current.hunks:
                current = Change(None, None, "modified")
                changes.append(current)
            current.old_path = patch_path(line[4:])
            continue
        if current is None:
            continue
        if line.startswith("+++ ") and hunk is None:
            current.new_path = patch_path(line[4:])
        elif line.startswith("rename from "):
            current.old_path, current.status = patch_path(line[12:], False), "renamed"
        elif line.startswith("rename to "):
            current.new_path = patch_path(line[10:], False)
        elif line.startswith("new file mode "):
            current.old_path, current.status = None, "added"
        elif line.startswith("deleted file mode "):
            current.new_path, current.status = None, "deleted"
        elif line.startswith(("Binary files ", "GIT binary patch")):
            current.binary = True
        elif line.startswith("@@ "):
            validate_hunk()
            match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                raise EngineError("Invalid hunk header")
            hunk = Hunk(int(match[1]), int(match[2] or 1), int(match[3]), int(match[4] or 1))
            current.hunks.append(hunk)
            old_seen = new_seen = 0
        elif hunk:
            if line.startswith("+"):
                hunk.added.append(line[1:])
                new_seen += 1
            elif line.startswith("-"):
                hunk.removed.append(line[1:])
                old_seen += 1
            elif line.startswith(" "):
                old_seen += 1
                new_seen += 1
            elif line.startswith("\\ No newline"):
                pass
            elif old_seen != hunk.old_count or new_seen != hunk.new_count:
                raise EngineError("Malformed diff payload")
    validate_hunk()
    for change in changes:
        if not change.old_path and not change.new_path:
            raise EngineError("Diff change has no safe file path")
        if change.old_path is None:
            change.status = "added"
        elif change.new_path is None:
            change.status = "deleted"
    if text.strip() and not changes:
        raise EngineError("No supported unified diff found")
    return changes


def overlap(start, count, symbol):
    # A zero-width edit is anchored at its preceding line.
    return symbol["start_line"] <= start + max(count, 1) - 1 and symbol["end_line"] >= max(start, 1)


def map_symbols(changes, head_store, base_store=None):
    mappings = []
    for change in changes:
        old = base_store.symbols(change.old_path) if base_store and change.old_path else []
        new = head_store.symbols(change.new_path) if change.new_path else []
        old_names = {s["qualified_name"]: s for s in old}
        new_names = {s["qualified_name"]: s for s in new}
        for side, symbols in (("base", old), ("head", new)):
            for symbol in symbols:
                hits = [i for i, hunk in enumerate(change.hunks) if overlap(
                    hunk.old_start if side == "base" else hunk.new_start,
                    hunk.old_count if side == "base" else hunk.new_count, symbol)]
                if not hits:
                    continue
                counterpart = (new_names if side == "base" else old_names).get(symbol["qualified_name"])
                kind = "changed"
                if base_store and counterpart is None:
                    kind = "removed" if side == "base" else "added"
                elif counterpart and counterpart["signature"] != symbol["signature"]:
                    kind = "signature_changed"
                mappings.append({"side": side, "change": kind, "symbol": symbol,
                                 "hunks": hits, "evidence": {"file": symbol["file"],
                                 "start_line": symbol["start_line"], "end_line": symbol["end_line"],
                                 "detector": "diff-range-overlap", "confidence": symbol["confidence"]}})
    return mappings
