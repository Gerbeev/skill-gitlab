from __future__ import annotations

import os
import subprocess
from pathlib import Path

from mr_impact.paths import ANALYSIS_DIR_NAME

SKIP_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    ANALYSIS_DIR_NAME,
    "_mr-impact",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
}

DEFAULT_MAX_BYTES = 2 * 1024 * 1024

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".eot",
    ".pdf",
    ".zip",
    ".jar",
    ".dll",
    ".exe",
    ".bin",
    ".pyc",
    ".class",
    ".lock",
}


def git_head(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def list_repo_files(repo: Path, include_globs: list[str] | None = None) -> list[str]:
    """Return repository-relative file paths to index."""
    tracked = _git_ls_files(repo)
    if tracked is not None:
        paths = tracked
    else:
        paths = _walk_files(repo)

    cleaned: list[str] = []
    for rel in paths:
        if _skip_path(rel):
            continue
        if Path(rel).suffix.lower() in SKIP_EXTENSIONS:
            continue
        if include_globs and not _matches_any(rel, include_globs):
            continue
        abs_path = repo / rel
        if not abs_path.is_file():
            continue
        try:
            if abs_path.stat().st_size > DEFAULT_MAX_BYTES:
                continue
        except OSError:
            continue
        cleaned.append(rel.replace("\\", "/"))
    cleaned.sort()
    return cleaned


def file_hash(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_ls_files(repo: Path) -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    raw = out.stdout.split(b"\0")
    return [p.decode("utf-8", "replace") for p in raw if p]


def _walk_files(repo: Path) -> list[str]:
    found: list[str] = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        rel_root = Path(root).relative_to(repo)
        for name in files:
            rel = (rel_root / name).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            found.append(rel)
    return found


def _skip_path(rel: str) -> bool:
    parts = Path(rel).parts
    return any(part in SKIP_DIR_NAMES for part in parts)


def _matches_any(rel: str, globs: list[str]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(rel, pattern) for pattern in globs)
