#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Report ``skills/*/references/*.md`` files not referenced from skill sources.

Scans only ``skills/`` (not ``.github/skills/``). Markdown skill content is not modified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
SKIP_PARTS = frozenset({"_engine", "mr-impact-method", "node_modules", ".git"})


def _collect_reference_files() -> list[Path]:
    refs: list[Path] = []
    for skill_dir in SKILLS.iterdir():
        if not skill_dir.is_dir() or skill_dir.name in SKIP_PARTS:
            continue
        ref_dir = skill_dir / "references"
        if not ref_dir.is_dir():
            continue
        for path in ref_dir.glob("*.md"):
            refs.append(path)
    method_refs = SKILLS / "mr-impact-method" / "references"
    if method_refs.is_dir():
        refs.extend(method_refs.glob("*.md"))
    return sorted(refs)


def _corpus_text() -> str:
    chunks: list[str] = []
    for path in SKILLS.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix not in {".md", ".toml"}:
            continue
        if path.suffix == ".toml":
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            continue
        if path.suffix != ".md":
            continue
        if path.name in {"SKILL.md", "README.md"} or path.name.startswith("step-") or path.name == "workflow.md":
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            continue
        if path.parent.name == "help":
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def find_orphans() -> list[str]:
    corpus = _corpus_text()
    orphans: list[str] = []
    for path in _collect_reference_files():
        rel = path.relative_to(SKILLS).as_posix()
        name = path.name
        stem = path.stem
        if name in corpus or stem in corpus or rel in corpus:
            continue
        orphans.append(rel)
    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 when orphans exist")
    args = parser.parse_args()
    orphans = find_orphans()
    if orphans:
        sys.stdout.write("Orphan skill reference files (not cited in skills/ sources):\n")
        for item in orphans:
            sys.stdout.write(f"  {item}\n")
        if args.strict:
            return 1
    else:
        sys.stdout.write("No orphan skill reference files under skills/.\n")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
