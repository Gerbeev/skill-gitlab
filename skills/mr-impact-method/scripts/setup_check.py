#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Report setup gaps before rendering a skill (must never fail the render)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

USES_INDEX = frozenset({"analyze-issue", "analyze-mr"})
REQUIRES_INDEX = frozenset({"analyze-mr"})
USES_GRAPH = frozenset({"analyze-mr"})
RUN_DIR = ".repository-analysis/run"
MR_MARKER = "01-mr-analysis.md"


def _import_jinja2() -> bool:
    try:
        import jinja2  # noqa: F401
    except ImportError:
        return False
    return True


def _index_sqlite(project_root: Path) -> Path:
    return project_root / ".repository-analysis" / "index" / "repository-index.sqlite"


def _graph_manifest(project_root: Path) -> Path:
    return project_root / ".repository-analysis" / "graph" / "graph-manifest.json"


def owed(skill_dir: Path, project_root: Path | None) -> list[str]:
    notes: list[str] = []
    skill_name = skill_dir.name

    if project_root is None:
        return notes

    runtime = project_root / "_mr-impact"
    render_script = runtime / "scripts" / "render_skill.py"
    if not runtime.is_dir() or not render_script.is_file():
        setup = project_root / "skills" / "mr-impact-method" / "scripts" / "setup.py"
        notes.append(
            "needs the MR Impact runtime under `_mr-impact/`. "
            f'Offer to run: python "{setup}" --project-root "{project_root}"'
        )

    engine_pkg = project_root / "_mr-impact" / "engine" / "src" / "mr_impact"
    dev_pkg = project_root / "skills" / "_engine" / "src" / "mr_impact"
    if not engine_pkg.is_dir() and not dev_pkg.is_dir():
        notes.append(
            "needs the Python engine under `_mr-impact/engine/` (or `skills/_engine/`). "
            "Re-run setup.py from a checkout that includes `skills/_engine`."
        )

    if not _import_jinja2():
        req = project_root / "skills" / "mr-impact-method" / "scripts" / "requirements.txt"
        notes.append(
            "needs the `jinja2` package for render_skill. "
            f'Offer: python -m pip install -r "{req}"'
        )

    sqlite = _index_sqlite(project_root)
    if skill_name == "create-graph" and not sqlite.is_file():
        notes.append(
            "needs `index/repository-index.sqlite`. Offer `/create-index` (create-index skill) first."
        )

    if skill_name in USES_INDEX and skill_name not in REQUIRES_INDEX and not sqlite.is_file():
        notes.append(
            "works best after `/create-index` — `.repository-analysis/index/` is missing. "
            "Offer create-index; proceed with Issue text only if the user accepts."
        )

    if skill_name in REQUIRES_INDEX and not sqlite.is_file():
        notes.append(
            "requires `index/repository-index.sqlite` — `analyze-mr` exits with an error without create-index."
        )

    if skill_name in USES_GRAPH and sqlite.is_file() and not _graph_manifest(project_root).is_file():
        notes.append(
            "has index but no `graph/graph-manifest.json`. For JSON export offer `/create-graph`; "
            "analyze-mr still uses index SQLite when graph JSON is absent."
        )

    run_dir = project_root / RUN_DIR
    mr_analysis = run_dir / MR_MARKER
    if skill_name == "update-issue" and not mr_analysis.is_file():
        notes.append(
            f"needs `{RUN_DIR}/{MR_MARKER}` from analyze-mr before update-issue can run."
        )

    discipline = skill_dir / "references" / "workflow-discipline.md"
    if not discipline.is_file():
        notes.append(
            "is missing `references/workflow-discipline.md` beside the skill. "
            "Offer to run setup.py --project-root to refresh shared references."
        )

    return notes


def report(skill_dir: Path, project_root: Path | None) -> None:
    try:
        notes = owed(skill_dir, project_root)
    except Exception:
        return
    for note in notes:
        sys.stderr.write(f"setup: before continuing, tell the user that `{skill_dir.name}` {note}\n")


if __name__ == "__main__":
    raise SystemExit(0)
