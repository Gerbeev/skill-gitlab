#!/usr/bin/env python3
"""Run the shared mr_impact CLI using the current Python (no uv required)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from config_utils import ConfigError, load_central_config
except ImportError:
    load_central_config = None


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
    src = engine / "src"
    env = os.environ.copy()
    if src.is_dir():
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([str(src), prev]) if prev else str(src)
    cmd = [sys.executable, "-m", "mr_impact", *forwarded]
    completed = subprocess.run(cmd, cwd=str(project_root), env=env)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
