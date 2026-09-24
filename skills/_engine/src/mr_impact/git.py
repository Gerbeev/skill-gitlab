"""Read-only Git plumbing with argument arrays and a fixed command allowlist."""

import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .safety import EngineError, contained, safe_relative

ALLOWED = {"rev-parse", "ls-tree", "diff", "cat-file", "status", "ls-files", "diff-tree"}


def git(root: Path, *args: str, max_bytes: int = 64_000_000, input_bytes: bytes | None = None) -> bytes:
    if not args or args[0] not in ALLOWED:
        raise EngineError("Git operation is not allowlisted")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0",
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            result = subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
                 "-c", "core.quotePath=false", "-C", str(root), *args],
                stdout=output, stderr=errors, input=input_bytes, env=env, timeout=120, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EngineError("Git unavailable or read operation timed out") from exc
        if result.returncode:
            raise EngineError(f"Git {args[0]} failed; verify repository and revision")
        size = output.seek(0, os.SEEK_END)
        if size > max_bytes:
            raise EngineError("Git output exceeds configured resource limit")
        output.seek(0)
        return output.read(size)


def resolve(root: Path, ref: str) -> str:
    if ref.startswith("-") or "\x00" in ref or len(ref) > 512:
        raise EngineError("Invalid Git revision")
    return git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()


def repository_id(root: Path) -> str:
    from .identity import settings
    explicit = settings(root).get("repository_id")
    if explicit:
        return explicit
    label = re.sub(r"[^a-zA-Z0-9_-]", "-", root.resolve().name)[:40] or "repository"
    return label + "-" + hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]


def snapshot(root: Path, ref: str = "HEAD", worktree: bool = False, accepts=None, max_file_bytes=None):
    commit = resolve(root, ref)
    entries = {}
    for entry in git(root, "ls-tree", "-rlz", commit).split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid, size = meta.decode().split()
        path = safe_relative(raw_path.decode("utf-8", errors="strict"))
        if kind == "blob" and mode != "120000":
            entries[path] = (oid, int(size), False)
    if worktree:
        if commit != resolve(root, "HEAD"):
            raise EngineError("Worktree indexing requires the HEAD revision")
        dirty = set(git(root, "diff", "--name-only", "-z", "--no-ext-diff", "--no-textconv", commit, "--").decode().split("\0"))
        dirty.update(git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0"))
        for path in sorted(dirty - {""}):
            if accepts is not None and not accepts(path):
                entries.pop(path, None)
                continue
            full = contained(root, path)
            if not full.is_file() or full.is_symlink():
                entries.pop(path, None)
                continue
            if max_file_bytes is not None and full.stat().st_size > max_file_bytes:
                stat = full.stat()
                entries[path] = (f"oversized:{stat.st_size}:{stat.st_mtime_ns}", stat.st_size, True)
                continue
            # Hash in chunks, never load a large dirty file into memory.
            digest = hashlib.sha256()
            with full.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    digest.update(chunk)
            entries[path] = ("worktree:" + digest.hexdigest(), full.stat().st_size, True)
    return commit, entries


def content(root: Path, path: str, entry, max_bytes: int) -> str:
    oid, size, dirty = entry
    if size > max_bytes:
        raise EngineError("File exceeds configured byte limit")
    if dirty:
        from .safety import read_text
        return read_text(contained(root, path), max_bytes)
    data = git(root, "cat-file", "blob", oid, max_bytes=max_bytes)
    if b"\0" in data:
        raise EngineError("Binary file skipped")
    return data.decode("utf-8-sig", errors="replace")


def batch_blobs(root: Path, items: list[tuple[str, tuple]], max_file_bytes: int):
    """Read a bounded batch with one Git process; keys are validated Git object IDs."""
    committed = [(path, entry) for path, entry in items if not entry[2] and entry[1] <= max_file_bytes]
    if not committed:
        return {}
    identities = [entry[0] for _, entry in committed]
    if any(not re.fullmatch(r"[0-9a-f]{40,64}", oid) for oid in identities):
        raise EngineError("Invalid blob identity")
    budget = sum(entry[1] for _, entry in committed) + 128 * len(committed)
    data = git(root, "cat-file", "--batch", max_bytes=budget,
               input_bytes=("\n".join(identities) + "\n").encode("ascii"))
    results, offset = {}, 0
    for path, entry in committed:
        end = data.find(b"\n", offset)
        header = data[offset:end].decode("ascii").split()
        if len(header) != 3 or header[0] != entry[0] or header[1] != "blob" or int(header[2]) != entry[1]:
            raise EngineError("Unexpected Git batch response")
        start, length = end + 1, int(header[2])
        payload = data[start:start + length]
        if len(payload) != length or data[start + length:start + length + 1] != b"\n":
            raise EngineError("Incomplete Git batch response")
        results[path] = payload
        offset = start + length + 1
    return results
