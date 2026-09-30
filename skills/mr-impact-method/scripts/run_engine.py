#!/usr/bin/env python3
"""Run the shared mr_impact CLI using the current Python (no uv required)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from engine_paths import resolve_runtime_engine_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Run python -m mr_impact with forwarded args.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("engine_args", nargs=argparse.REMAINDER, help="Arguments after -- for mr_impact")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    forwarded = list(args.engine_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    engine = resolve_runtime_engine_root(project_root)
    src = engine / "src"
    if not (src / "mr_impact").is_dir():
        sys.stderr.write(
            "error: mr_impact engine not found. Expected one of:\n"
            f"  {project_root / '_mr-impact' / 'engine'}\n"
            f"  {project_root / 'skills' / '_engine'}\n"
            "Re-run: python skills/mr-impact-method/scripts/setup.py --project-root <repo>\n"
        )
        return 1
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(src), prev]) if prev else str(src)
    cmd = [sys.executable, "-m", "mr_impact", *forwarded]
    completed = subprocess.run(cmd, cwd=str(project_root), env=env)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
