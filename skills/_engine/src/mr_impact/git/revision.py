from __future__ import annotations

import subprocess
from pathlib import Path


def parse_revision_range(revision: str) -> tuple[str, str]:
    """Split `base..head` into two ref strings (not yet resolved to SHA)."""
    text = revision.strip()
    if ".." not in text:
        raise ValueError(f"revision must be a two-dot range (base..head), got: {revision!r}")
    base, head = text.split("..", 1)
    base, head = base.strip(), head.strip()
    if not base or not head:
        raise ValueError(f"invalid revision range: {revision!r}")
    return base, head


def resolve_ref(repo: Path, ref: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", ref],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise FileNotFoundError(f"git not available: {error}") from error
    if out.returncode != 0:
        raise ValueError(f"cannot resolve ref {ref!r}: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout.strip()
