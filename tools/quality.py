#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Run the same checks as .github/workflows/engine.yml, in order.

Usage (from repository root):
  python tools/quality.py

Requires Python 3.11+. Does not use uv.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METHOD_REQ = ROOT / "skills" / "mr-impact-method" / "scripts" / "requirements.txt"
SETUP = ROOT / "skills" / "mr-impact-method" / "scripts" / "setup.py"
ENGINE_DIR = ROOT / "skills" / "_engine"
VALIDATE = ROOT / "tools" / "validate_skills.py"
VALIDATE_REFS = ROOT / "tools" / "validate_file_refs.py"
FIND_ORPHAN_REFS = ROOT / "tools" / "find_orphan_skill_references.py"
RENDER_TESTS = ROOT / "skills" / "mr-impact-method" / "scripts" / "tests" / "test_render_skills.py"


def _run(label: str, argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    where = f" (cwd={cwd.relative_to(ROOT)})" if cwd and cwd != ROOT else ""
    print(f"\n--- {label}{where} ---", flush=True)
    print(" ".join(argv), flush=True)
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(argv, cwd=cwd or ROOT, env=merged)
    if result.returncode != 0:
        print(f"quality: failed at: {label}", file=sys.stderr)
    return result.returncode


def _verify_setup_status() -> int:
    print("\n--- Verify setup status ---", flush=True)
    out = subprocess.check_output(
        [sys.executable, str(SETUP), "--project-root", str(ROOT), "--status"],
        text=True,
        cwd=ROOT,
    )
    status = json.loads(out)
    assert status.get("engine_bundled"), status
    assert status.get("config_exists"), status
    expected = set(status.get("expected_skills") or [])
    installed = set(status.get("github_skills") or [])
    missing = expected - installed
    assert not missing, f"missing .github/skills: {sorted(missing)} ({status})"
    extra = status.get("extra_github_skills") or []
    assert not extra, f"unexpected .github/skills: {extra}"
    print("setup smoke ok:", len(installed), "skills", flush=True)
    return 0


def main() -> int:
    if sys.version_info < (3, 11):
        print("quality: Python 3.11+ required", file=sys.stderr)
        return 1

    code = _run(
        "Install method dependencies",
        [sys.executable, "-m", "pip", "install", "-r", str(METHOD_REQ)],
    )
    if code:
        return code

    code = _run(
        "Setup (bundle engine and sync skills)",
        [sys.executable, str(SETUP), "--project-root", str(ROOT)],
    )
    if code:
        return code

    try:
        _verify_setup_status()
    except (subprocess.CalledProcessError, AssertionError) as exc:
        print(f"quality: setup status check failed: {exc}", file=sys.stderr)
        return 1

    code = _run(
        "Engine unit tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ENGINE_DIR,
        env={"PYTHONPATH": str(ENGINE_DIR / "src")},
    )
    if code:
        return code

    code = _run("Validate Copilot skills", [sys.executable, str(VALIDATE), "--strict"])
    if code:
        return code

    code = _run(
        "Validate skill file references",
        [sys.executable, str(VALIDATE_REFS), "--strict"],
    )
    if code:
        return code

    if FIND_ORPHAN_REFS.is_file():
        code = _run(
            "Orphan skill reference check",
            [sys.executable, str(FIND_ORPHAN_REFS), "--strict"],
        )
        if code:
            return code

    code = _run("Render skill tests", [sys.executable, str(RENDER_TESTS)])
    if code:
        return code

    tools_tests = ROOT / "tools" / "tests"
    if tools_tests.is_dir():
        code = _run(
            "Tools unit tests",
            [sys.executable, "-m", "unittest", "discover", "-s", str(tools_tests), "-v"],
        )
        if code:
            return code

    setup_check_tests = ROOT / "skills" / "mr-impact-method" / "scripts" / "tests" / "test_setup_check.py"
    if setup_check_tests.is_file():
        code = _run("Setup check tests", [sys.executable, str(setup_check_tests)])
        if code:
            return code

    print("\nquality: all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
