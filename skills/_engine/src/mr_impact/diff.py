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
                hunk.new_lines.append(hunk.new_start + new_seen)
                hunk.payload.append(("+", line[1:]))
                new_seen += 1
            elif line.startswith("-"):
                hunk.removed.append(line[1:])
                hunk.old_lines.append(hunk.old_start + old_seen)
                hunk.payload.append(("-", line[1:]))
                old_seen += 1
            elif line.startswith(" "):
                hunk.payload.append((" ", line[1:]))
                old_seen += 1
                new_seen += 1
            elif line.startswith("\\ No newline"):
                if not hunk.payload:
                    raise EngineError("Newline marker has no preceding payload")
                kind = hunk.payload[-1][0]
                hunk.old_no_newline |= kind in {"-", " "}
                hunk.new_no_newline |= kind in {"+", " "}
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
                hits = [i for i, hunk in enumerate(change.hunks)
                        if any(symbol["start_line"] <= line <= symbol["end_line"]
                               for line in (hunk.old_lines if side == "base" else hunk.new_lines))]
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


def validate_patch(changes, old_files, new_files, read_old, read_new):
    """Verify complete textual transformations without running a patch program.

    A patch can cover a subset of files, but each included file must match its
    complete base/head transformation. Without a base, old-side claims remain
    explicitly unverified; head context and deletion absence are still checked.
    """
    seen_old, seen_new = set(), set()
    for change in changes:
        old, new = change.old_path, change.new_path
        if old in seen_old or new in seen_new:
            raise EngineError("Duplicate file change in patch")
        if old:
            seen_old.add(old)
        if new:
            seen_new.add(new)
        if change.binary:
            raise EngineError("External binary patch verification is unsupported; use a Git range")
        if new and new not in new_files:
            raise EngineError("Patch head file is absent from the selected revision")
        if not new and old in new_files:
            raise EngineError("Patch deletion is inconsistent with the selected head")
        if old and new and old != new and old in new_files:
            raise EngineError("Patch rename source still exists at the selected head")
        head_text = read_new(new) if new else ""
        head_lines = head_text.splitlines()
        base_lines = None
        if old_files is not None:
            if old and old not in old_files:
                raise EngineError("Patch base file is absent from the selected revision")
            if not old and new in old_files:
                raise EngineError("Patch addition already exists at the selected base")
            base_text = read_old(old) if old else ""
            base_lines = base_text.splitlines()
        cursor, result = 0, []
        previous_new_end = 0
        for hunk in change.hunks:
            old_start = hunk.old_start - 1 if hunk.old_count else hunk.old_start
            new_start = hunk.new_start - 1 if hunk.new_count else hunk.new_start
            old_payload = [text for kind, text in hunk.payload if kind != "+"]
            new_payload = [text for kind, text in hunk.payload if kind != "-"]
            if old_start < cursor or new_start < previous_new_end or new_start < 0 or old_start < 0:
                raise EngineError("Patch hunks overlap or have invalid positions")
            if head_lines[new_start:new_start + hunk.new_count] != new_payload or new_start > len(head_lines):
                raise EngineError("Patch new content or context does not match the selected head")
            if hunk.new_count and new_start + hunk.new_count == len(head_lines):
                if hunk.new_no_newline != bool(head_text and not head_text.endswith(("\n", "\r"))):
                    raise EngineError("Patch head newline marker does not match the selected revision")
            elif hunk.new_no_newline:
                raise EngineError("Patch head newline marker is not at end of file")
            if base_lines is not None:
                if hunk.old_count and old_start + hunk.old_count == len(base_lines):
                    if hunk.old_no_newline != bool(base_text and not base_text.endswith(("\n", "\r"))):
                        raise EngineError("Patch base newline marker does not match the selected revision")
                elif hunk.old_no_newline:
                    raise EngineError("Patch base newline marker is not at end of file")
                if old_start > len(base_lines) or base_lines[old_start:old_start + hunk.old_count] != old_payload:
                    raise EngineError("Patch old content or context does not match the selected base")
                result.extend(base_lines[cursor:old_start])
                if len(result) != new_start:
                    raise EngineError("Patch old/new positions are inconsistent")
                result.extend(new_payload)
            cursor = old_start + hunk.old_count
            previous_new_end = new_start + hunk.new_count
        if base_lines is not None:
            result.extend(base_lines[cursor:])
            if result != head_lines:
                raise EngineError("Patch does not describe the complete selected file transformation")
