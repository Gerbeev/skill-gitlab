#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Install _mr-impact runtime and sync Copilot skills to .github/skills/."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path

sys.dont_write_bytecode = True

COPILOT_SKILLS = (
    "analyze-issue",
    "create-index",
    "create-graph",
    "analyze-mr",
    "update-issue",
)
SCRIPT_NAMES = (
    "config_utils.py",
    "render_skill.py",
    "resolve_config.py",
    "run_engine.py",
    "setup.py",
    "setup_check.py",
)
SHARED_REFERENCES = (
    "references/workflow-discipline.md",
    "references/validate-present.md",
    "references/analysis-inputs.md",
    "references/run-cleanup.md",
)


def method_root(script_file: Path) -> Path:
    return script_file.resolve().parent.parent


def write_config(project_root: Path, template: Path) -> Path:
    text = template.read_text(encoding="utf-8")
    text = text.replace("{directory_name}", project_root.name).replace(
        "{project-root}", project_root.as_posix()
    )
    dest = project_root / "_mr-impact" / "config.toml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


ENGINE_IGNORE = shutil.ignore_patterns(
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "*.egg-info",
)


def resolve_engine_source(project_root: Path, method_dir: Path) -> Path | None:
    for candidate in (project_root / "skills" / "_engine", method_dir.parent / "_engine"):
        if (candidate / "src" / "mr_impact").is_dir():
            return candidate
    return None


def copy_engine(project_root: Path, method_dir: Path) -> str | None:
    source = resolve_engine_source(project_root, method_dir)
    if source is None:
        return None
    dest = project_root / "_mr-impact" / "engine"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=ENGINE_IGNORE)
    return str(dest)


def copy_scripts(method_dir: Path, project_root: Path) -> list[str]:
    src = method_dir / "scripts"
    dest = project_root / "_mr-impact" / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in SCRIPT_NAMES:
        source = src / name
        if source.is_file():
            shutil.copy2(source, dest / name)
            copied.append(name)
    return copied


def install_shared_references(method_dir: Path, skills_dir: Path, skill_names: list[str]) -> None:
    for skill_name in skill_names:
        for rel in SHARED_REFERENCES:
            source = method_dir / rel
            if not source.is_file():
                continue
            dest = skills_dir / skill_name / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)


def sync_skill(skill_name: str, skills_dir: Path, github_skills: Path) -> str:
    source = skills_dir / skill_name
    target = github_skills / skill_name
    if not source.is_dir():
        return f"missing source {source}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("bmod.toml", "__pycache__", "*.pyc", ".pytest_cache"),
    )
    return f"synced {skill_name}"


def load_copilot_skills(skills_dir: Path) -> list[str]:
    manifest = skills_dir / "mr-impact-method" / "bmod.toml"
    if not manifest.is_file():
        return list(COPILOT_SKILLS)
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    listed = data.get("bmod", {}).get("skills")
    if isinstance(listed, list) and all(isinstance(x, str) for x in listed):
        return listed
    return list(COPILOT_SKILLS)


def prune_github_skills(github_skills: Path, allowed: set[str]) -> list[str]:
    removed = []
    if not github_skills.is_dir():
        return removed
    for child in github_skills.iterdir():
        if child.is_dir() and child.name not in allowed:
            shutil.rmtree(child)
            removed.append(child.name)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    method_dir = method_root(Path(__file__))
    project_root = Path(args.project_root).resolve() if args.project_root else method_dir.parent.parent
    skills_dir = project_root / "skills"
    github_skills = project_root / ".github" / "skills"
    runtime = project_root / "_mr-impact"
    template = method_dir / "assets" / "config.template.toml"
    allowed = set(load_copilot_skills(skills_dir))

    if args.status:
        installed = [p.name for p in github_skills.iterdir() if p.is_dir()] if github_skills.is_dir() else []
        payload = {
            "project_root": str(project_root),
            "runtime_exists": runtime.is_dir(),
            "config_exists": (runtime / "config.toml").is_file(),
            "engine_bundled": (runtime / "engine" / "src" / "mr_impact").is_dir(),
            "github_skills": installed,
            "expected_skills": sorted(allowed),
            "extra_github_skills": sorted(set(installed) - allowed),
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0

    if not template.is_file():
        sys.stderr.write(f"error: missing template {template}\n")
        return 1

    write_config(project_root, template)
    engine_dest = copy_engine(project_root, method_dir)
    copied = copy_scripts(method_dir, project_root)
    skill_list = sorted(allowed)
    install_shared_references(method_dir, skills_dir, skill_list)
    github_skills.mkdir(parents=True, exist_ok=True)
    removed = prune_github_skills(github_skills, allowed)
    actions = [sync_skill(name, skills_dir, github_skills) for name in skill_list]
    (runtime / "custom").mkdir(parents=True, exist_ok=True)
    (project_root / ".repository-analysis" / "catalog").mkdir(parents=True, exist_ok=True)
    example = project_root / "docs" / "reference" / "boundary-catalog.example.json"
    catalog = project_root / ".repository-analysis" / "catalog" / "boundary-catalog.json"
    if example.is_file() and not catalog.is_file():
        shutil.copy2(example, catalog)

    sys.stdout.write(
        json.dumps(
            {
                "status": "ok",
                "config": str(runtime / "config.toml"),
                "engine_bundled": engine_dest,
                "scripts_copied": copied,
                "sync": actions,
                "removed_from_github_skills": removed,
            },
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
