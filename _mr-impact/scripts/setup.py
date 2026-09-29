#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Install _mr-impact runtime and sync the four Copilot skills to .github/skills/."""

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
    "index-repository",
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
    copied = copy_scripts(method_dir, project_root)
    github_skills.mkdir(parents=True, exist_ok=True)
    removed = prune_github_skills(github_skills, allowed)
    actions = [sync_skill(name, skills_dir, github_skills) for name in sorted(allowed)]
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
