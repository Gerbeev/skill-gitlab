#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Run the shared mr_impact CLI via uv."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from config_utils import ConfigError, load_central_config
except ImportError:
    load_central_config = None  # type: ignore


def engine_root(project_root: Path) -> Path:
    if load_central_config is not None:
        try:
            cfg = load_central_config(project_root)
            raw = cfg.get("core", {}).get("engine_project")
            if isinstance(raw, str) and raw.strip():
                return Path(raw.replace("{project-root}", project_root.as_posix()))
        except ConfigError:
            pass
    return project_root / "skills" / "_engine"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run python -m mr_impact with forwarded args.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("engine_args", nargs=argparse.REMAINDER, help="Arguments after -- for mr_impact")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    forwarded = list(args.engine_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    engine = engine_root(project_root)
    cmd = [
        "uv",
        "run",
        "--project",
        str(engine),
        "python",
        "-m",
        "mr_impact",
        *forwarded,
    ]
    completed = subprocess.run(cmd, cwd=str(project_root))
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
