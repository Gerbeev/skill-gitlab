#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Deterministic validator for MR Impact Copilot skills.

Adapted from BMAD tools/validate_skills.py (SKILL-01–08, PATH-02, SEQ-02, TPL-01, WORKFLOW-01–02).
Inference pass: tools/skill-validator.md.

Usage:
  python tools/validate_skills.py
  python tools/validate_skills.py skills/analyze-issue
  python tools/validate_skills.py --strict
  python tools/validate_skills.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib

sys.dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.join(PROJECT_ROOT, "skills")

COPILOT_SKILLS = (
    "analyze-issue",
    "create-index",
    "create-graph",
    "analyze-mr",
    "update-issue",
)

NAME_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_REGEX_DISPLAY = r"/^[a-z0-9]+(?:-[a-z0-9]+)*$/"
TIME_ESTIMATE_PATTERNS = [
    re.compile(r"takes?\s+\d+\s*min", re.I),
    re.compile(r"~\s*\d+\s*min", re.I),
    re.compile(r"estimated\s+time", re.I),
    re.compile(r"\bETA\b"),
]
TEMPLATE_FILENAME_REGEX = re.compile(r"template", re.I)
COMPILE_TIME_SUB_REGEX = re.compile(r"\{\{-?\s*(?:config|workflow)\.[^}]*\}\}")
INSTALLED_PATH_RE = re.compile(r"installed_path", re.I)
USE_WHEN_RE = re.compile(r"use\s+when\b", re.I)
USE_IF_RE = re.compile(r"use\s+if\b", re.I)
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".pytest_cache", "_engine"}
SCAN_EXTENSIONS = {".md", ".yaml", ".yml"}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
WORKFLOW_DISCIPLINE_RE = re.compile(r"workflow-discipline\.md", re.I)


def _relpath(to_path: str, start: str) -> str:
    rel = os.path.relpath(to_path, start).replace(os.sep, "/")
    return "" if rel == "." else rel


def _finding(
    rule: str,
    title: str,
    severity: str,
    file: str,
    detail: str,
    fix: str,
    line: int | None = None,
) -> dict:
    item = {
        "rule": rule,
        "title": title,
        "severity": severity,
        "file": file,
        "detail": detail,
        "fix": fix,
    }
    if line is not None:
        item["line"] = line
    return item


def _frontmatter_block(content: str) -> str | None:
    trimmed = content.lstrip()
    if not trimmed.startswith("---"):
        return None
    end_index = trimmed.find(f"{os.linesep}---{os.linesep}", 3)
    if end_index == -1:
        if trimmed.endswith(f"{os.linesep}---"):
            end_index = len(trimmed) - len(os.linesep) - 3
        else:
            return None
    return trimmed[3:end_index].strip()


def parse_frontmatter_multiline(content: str) -> dict[str, str] | None:
    fm_block = _frontmatter_block(content)
    if fm_block is None:
        return None
    if fm_block == "":
        return {}
    result: dict[str, str] = {}
    current_key: str | None = None
    current_value = ""
    for line in fm_block.split(os.linesep):
        colon_index = line.find(":")
        if colon_index > 0 and line[:1] not in (" ", "\t"):
            if current_key is not None:
                result[current_key] = current_value.strip().strip("'\"")
            current_key = line[:colon_index].strip()
            current_value = line[colon_index + 1 :]
        elif current_key is not None:
            if line.lstrip().startswith("#"):
                continue
            current_value += "\n" + line
    if current_key is not None:
        result[current_key] = current_value.strip().strip("'\"")
    return result


def safe_read_file(file_path: str, findings: list[dict], rel_file: str | None) -> str | None:
    try:
        with open(file_path, encoding="utf-8", errors="replace", newline="") as handle:
            return handle.read()
    except OSError as error:
        findings.append(
            _finding(
                "READ-ERR",
                "File Read Error",
                "MEDIUM",
                rel_file or os.path.basename(file_path),
                f"Cannot read file: {error}",
                "Check file permissions and ensure the file exists.",
            )
        )
        return None


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\r\n]", "", match.group(0))


def strip_code_blocks(content: str) -> str:
    return re.sub(r"```.*?```", _blank, content, flags=re.DOTALL)


def default_skill_dirs() -> list[str]:
    dirs: list[str] = []
    for name in COPILOT_SKILLS:
        path = os.path.join(SKILLS_ROOT, name)
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            dirs.append(path)
    return dirs


def collect_skill_files(skill_dir: str, findings: list[dict]) -> list[str]:
    files: list[str] = []

    def walk(current_dir: str) -> None:
        try:
            with os.scandir(current_dir) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as error:
            findings.append(
                _finding(
                    "READ-ERR",
                    "File Read Error",
                    "MEDIUM",
                    _relpath(current_dir, skill_dir),
                    f"Cannot read directory: {error}",
                    "Check permissions.",
                )
            )
            return
        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            if entry.is_dir(follow_symlinks=False):
                walk(entry.path)
            elif entry.is_file(follow_symlinks=False):
                files.append(entry.path)

    walk(skill_dir)
    return files


def validate_skill(skill_dir: str) -> list[dict]:
    findings: list[dict] = []
    dir_name = os.path.basename(skill_dir)
    skill_md_path = os.path.join(skill_dir, "SKILL.md")
    all_files = collect_skill_files(skill_dir, findings)

    if not os.path.exists(skill_md_path):
        findings.append(
            _finding(
                "SKILL-01",
                "SKILL.md Must Exist",
                "CRITICAL",
                "SKILL.md",
                "SKILL.md not found in skill directory.",
                "Create SKILL.md as the skill entrypoint.",
            )
        )
        return findings

    skill_content = safe_read_file(skill_md_path, findings, "SKILL.md")
    if skill_content is None:
        return findings
    skill_fm = parse_frontmatter_multiline(skill_content)

    if not skill_fm or "name" not in skill_fm:
        findings.append(
            _finding(
                "SKILL-02",
                "SKILL.md Must Have name in Frontmatter",
                "CRITICAL",
                "SKILL.md",
                "Frontmatter is missing the `name` field.",
                "Add `name: <skill-name>` to the frontmatter.",
            )
        )
    elif skill_fm["name"] != dir_name:
        findings.append(
            _finding(
                "SKILL-05",
                "name Must Match Directory Name",
                "HIGH",
                "SKILL.md",
                f'name "{skill_fm.get("name")}" does not match directory "{dir_name}".',
                f'Change name to "{dir_name}".',
            )
        )

    name = skill_fm.get("name") if skill_fm else None
    if name and not NAME_REGEX.search(name):
        findings.append(
            _finding(
                "SKILL-04",
                "name Format",
                "HIGH",
                "SKILL.md",
                f'name "{name}" does not match pattern: {NAME_REGEX_DISPLAY}',
                "Use lowercase letters, numbers, and hyphens only.",
            )
        )

    description = skill_fm.get("description") if skill_fm else None
    if not skill_fm or "description" not in skill_fm:
        findings.append(
            _finding(
                "SKILL-03",
                "SKILL.md Must Have description in Frontmatter",
                "CRITICAL",
                "SKILL.md",
                "Frontmatter is missing the `description` field.",
                "Add a description with a Use when clause.",
            )
        )
    elif description and not USE_WHEN_RE.search(description) and not USE_IF_RE.search(description):
        findings.append(
            _finding(
                "SKILL-06",
                "description Quality",
                "MEDIUM",
                "SKILL.md",
                'description does not contain "Use when" or "Use if".',
                'Add when to invoke this skill.',
            )
        )

    if "render_skill.py" not in skill_content:
        findings.append(
            _finding(
                "SKILL-08",
                "Rendered skill dispatch",
                "HIGH",
                "SKILL.md",
                "SKILL.md does not reference render_skill.py.",
                "Add the standard python render_skill.py dispatch block.",
            )
        )

    trimmed = skill_content.lstrip()
    body_start = -1
    if trimmed.startswith("---"):
        end_idx = trimmed.find(f"{os.linesep}---{os.linesep}", 3)
        if end_idx != -1:
            body_start = end_idx + len(os.linesep) + 3
        elif trimmed.endswith(f"{os.linesep}---"):
            body_start = len(trimmed)
    else:
        body_start = 0
    body = trimmed[body_start:].strip() if body_start >= 0 else ""
    if body == "":
        findings.append(
            _finding(
                "SKILL-07",
                "SKILL.md Must Have Body Content",
                "HIGH",
                "SKILL.md",
                "SKILL.md has no content after frontmatter.",
                "Add the render_skill dispatch block after the closing ---.",
            )
        )

    workflow_path = os.path.join(skill_dir, "workflow.md")
    workflow_content = safe_read_file(workflow_path, findings, "workflow.md")
    if workflow_content is None:
        findings.append(
            _finding(
                "WORKFLOW-01",
                "workflow.md required",
                "CRITICAL",
                "workflow.md",
                "workflow.md is missing.",
                "Add workflow.md with On Activation and FIRST STEP.",
            )
        )
    elif workflow_content and not WORKFLOW_DISCIPLINE_RE.search(workflow_content):
        findings.append(
            _finding(
                "WORKFLOW-01",
                "workflow.md links discipline",
                "HIGH",
                "workflow.md",
                "workflow.md does not reference references/workflow-discipline.md.",
                'Add rendered("references/workflow-discipline.md") in On Activation.',
            )
        )

    discipline = os.path.join(skill_dir, "references", "workflow-discipline.md")
    if not os.path.isfile(discipline):
        findings.append(
            _finding(
                "WORKFLOW-02",
                "Shared discipline file",
                "HIGH",
                "references/workflow-discipline.md",
                "Missing shared workflow discipline reference (run setup or copy from mr-impact-method).",
                "Run python skills/mr-impact-method/scripts/setup.py --project-root .",
            )
        )

    for file_path in all_files:
        ext = os.path.splitext(file_path)[1]
        if ext not in SCAN_EXTENSIONS:
            continue
        rel_file = _relpath(file_path, skill_dir)
        content = safe_read_file(file_path, findings, rel_file)
        if content is None:
            continue
        stripped = strip_code_blocks(content)
        for i, line in enumerate(stripped.split(os.linesep)):
            if INSTALLED_PATH_RE.search(line):
                findings.append(
                    _finding(
                        "PATH-02",
                        "No installed_path Variable",
                        "HIGH",
                        rel_file,
                        "`installed_path` reference found.",
                        "Remove installed_path usage.",
                        line=i + 1,
                    )
                )
            for pattern in TIME_ESTIMATE_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        _finding(
                            "SEQ-02",
                            "No Time Estimates",
                            "LOW",
                            rel_file,
                            f'Time estimate pattern: "{line.strip()}"',
                            "Remove time estimates.",
                            line=i + 1,
                        )
                    )
                    break

        base = os.path.basename(file_path)
        if ext == ".md" and TEMPLATE_FILENAME_REGEX.search(base):
            for i, line in enumerate(content.split(os.linesep)):
                match = COMPILE_TIME_SUB_REGEX.search(line)
                if match:
                    findings.append(
                        _finding(
                            "TPL-01",
                            "No render-time expressions in templates",
                            "HIGH",
                            rel_file,
                            f"Template contains `{match.group(0)}`.",
                            "Use single-curly placeholders for LLM runtime.",
                            line=i + 1,
                        )
                    )

    return findings


def run(
    project_root: str,
    skill_dir: str | None = None,
    strict: bool = False,
    json_output: bool = False,
) -> int:
    if skill_dir is not None:
        target = os.path.abspath(skill_dir)
        if not os.path.isdir(target):
            print(f'Error: "{skill_dir}" is not a directory.', file=sys.stderr)
            return 2
        skill_dirs = [target]
    else:
        skill_dirs = default_skill_dirs()

    if not skill_dirs:
        print("No Copilot skill directories found.", file=sys.stderr)
        return 2

    results = [{"skillDir": d, "findings": validate_skill(d)} for d in skill_dirs]
    all_findings = []
    for result in results:
        rel = _relpath(result["skillDir"], project_root)
        for f in result["findings"]:
            all_findings.append({**f, "skill": rel})

    has_high_plus = any(f["severity"] in ("CRITICAL", "HIGH") for f in all_findings)

    if json_output:
        print(json.dumps(all_findings, indent=2, ensure_ascii=False))
    else:
        print(f"\nValidating MR Impact skills under {SKILLS_ROOT}\n")
        for result in results:
            rel = _relpath(result["skillDir"], project_root)
            if not result["findings"]:
                print(f"  OK  {rel}")
                continue
            print(f"\n{rel}")
            for f in result["findings"]:
                loc = f" (line {f['line']})" if f.get("line") else ""
                print(f"  [{f['severity']}] {f['rule']} — {f['detail']} ({f['file']}{loc})")
        print(f"\n{len(skill_dirs)} skills, {len(all_findings)} findings")
        if strict and has_high_plus:
            print("[STRICT] HIGH+ findings — failing.")
        elif not all_findings:
            print("All skills passed.")

    return 1 if strict and has_high_plus else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate MR Impact Copilot skills.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("skill_dir", nargs="?", default=None)
    args = parser.parse_args(argv)
    return run(PROJECT_ROOT, skill_dir=args.skill_dir, strict=args.strict, json_output=args.json_output)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
