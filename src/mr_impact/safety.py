"""Bounded I/O and redaction; repository strings are never executable commands."""

import json
import os
import re
from pathlib import Path, PurePosixPath


class EngineError(Exception):
    """An actionable input or system failure, safe to show in the CLI."""


def validate_output(path: Path):
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise EngineError("Refusing output through a symlink or junction")


def safe_relative(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or ":" in value or "\x00" in value:
        raise EngineError("Unsafe repository-relative path")
    return str(path)


def contained(root: Path, relative: str) -> Path:
    path = root / safe_relative(relative)
    if not path.resolve().is_relative_to(root.resolve()):
        raise EngineError("Path escapes selected scope")
    return path


def read_text(path: Path, limit: int = 2_000_000) -> str:
    if path.is_symlink() or not path.is_file():
        raise EngineError("Input must be a regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise EngineError("Input exceeds configured byte limit")
    if b"\x00" in data:
        raise EngineError("Binary input is not supported as text")
    return data.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def redact(text: str) -> str:
    text = re.sub(r"(?i)\b(password|token|secret|api[_-]?key)\b([\s\"']*[:=][\s\"']*)([^\s,;\"']+)",
                  r"\1\2[REDACTED]", text)
    text = re.sub(r"\b(?:glpat-|ghp_|github_pat_)[A-Za-z0-9_-]+", "[REDACTED]", text)
    text = re.sub(r"(https?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", text)
    return text


def write_text(path: Path, content: str):
    validate_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise EngineError("Refusing symlink output")
    # Exclusive temporary creation prevents following a pre-existing link.
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".mr-impact-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(redact(content))
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path: Path, value):
    write_text(path, json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def read_json(path: Path, limit: int = 20_000_000):
    return json.loads(read_text(path, limit))
