#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Report whether _mr-impact is installed before rendering a skill."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True


def report(skill_dir: Path, project_root: Path) -> None:
    runtime = project_root / "_mr-impact"
    render = project_root / "_mr-impact" / "scripts" / "render_skill.py"
    if runtime.is_dir() and render.is_file():
        return
    sys.stdout.write(
        "NOTE: MR Impact runtime is not installed. "
        f"Run: uv run --no-cache \"{skill_dir / 'scripts' / 'setup.py'}\" "
        f"--project-root \"{project_root}\" --skill \"{skill_dir.parent / 'mr-impact'}\"\n"
    )


if __name__ == "__main__":
    raise SystemExit(0)
