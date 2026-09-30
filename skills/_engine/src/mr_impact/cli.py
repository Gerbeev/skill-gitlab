from __future__ import annotations

import sys
from pathlib import Path

from mr_impact.cli_dispatch import run_cli


def main(argv: list[str] | None = None) -> int:
    return run_cli(argv, Path.cwd())


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
