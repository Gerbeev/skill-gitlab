from __future__ import annotations

import re
from pathlib import Path

from mr_impact.artifacts.contract import validate_mr_json_file
from mr_impact.json_io import load_json, load_json_dict

_TEMPLATE_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

ISSUE_RUN_FILES = (
    "00-issue-analysis.md",
    "01-generated-issue.md",
    "issue-intent.json",
)

MR_RUN_FILES = (
    "mr-context.json",
    "changed-symbols.json",
    "impact-graph.json",
    "runtime-impact.json",
    "test-impact.json",
    "01-mr-analysis.md",
    "02-change-context.md",
    "03-impact-analysis.md",
    "04-test-plan.md",
    "boundary-hints.json",
)

UPDATE_RUN_FILES = (
    "01-mr-analysis.md",
    "05-issue-update.md",
    "issue-update.json",
)

ISSUE_INTENT_KEYS = frozenset(
    {
        "schema_version",
        "generated_at",
        "input_files",
        "gaps",
        "anchors",
    }
)

ISSUE_UPDATE_KEYS = frozenset({"schema_version", "generated_at", "gitlab_apply", "sections"})


def _template_headings(template_text: str) -> list[str]:
    headings: list[str] = []
    for match in _TEMPLATE_HEADING.finditer(template_text):
        title = match.group(1).strip()
        if title.lower() == "issue":
            continue
        headings.append(title)
    return headings


def _missing_files(run_dir: Path, names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not (run_dir / name).is_file()]


def validate_issue_run(
    run_dir: Path,
    *,
    template_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    run_dir = run_dir.resolve()
    missing = _missing_files(run_dir, ISSUE_RUN_FILES)
    for name in missing:
        errors.append(f"missing file: {name}")

    intent = load_json_dict(run_dir / "issue-intent.json")
    if intent is not None:
        for key in ISSUE_INTENT_KEYS:
            if key not in intent:
                errors.append(f"issue-intent.json missing key: {key}")
    elif (run_dir / "issue-intent.json").is_file():
        errors.append("issue-intent.json is not valid JSON object")

    if template_path is not None and template_path.is_file():
        generated = run_dir / "01-generated-issue.md"
        if generated.is_file():
            template_text = template_path.read_text(encoding="utf-8", errors="replace")
            body = generated.read_text(encoding="utf-8", errors="replace")
            for heading in _template_headings(template_text):
                needle = f"## {heading}"
                if needle not in body:
                    errors.append(f"01-generated-issue.md missing template section: {heading}")
    return errors


def validate_mr_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    run_dir = run_dir.resolve()
    for name in _missing_files(run_dir, MR_RUN_FILES):
        errors.append(f"missing file: {name}")

    for json_name in (
        "mr-context.json",
        "changed-symbols.json",
        "impact-graph.json",
        "runtime-impact.json",
        "test-impact.json",
        "boundary-hints.json",
    ):
        path = run_dir / json_name
        if not path.is_file():
            continue
        payload = load_json(path)
        if payload is None:
            errors.append(f"{json_name} is not valid JSON")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{json_name} must be a JSON object")
            continue
        errors.extend(validate_mr_json_file(json_name, payload))
    return errors


def validate_update_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    run_dir = run_dir.resolve()
    for name in _missing_files(run_dir, UPDATE_RUN_FILES):
        errors.append(f"missing file: {name}")

    payload = load_json_dict(run_dir / "issue-update.json")
    if payload is not None:
        for key in ISSUE_UPDATE_KEYS:
            if key not in payload:
                errors.append(f"issue-update.json missing key: {key}")
        if payload.get("gitlab_apply") is not False:
            errors.append("issue-update.json must have gitlab_apply: false from engine")
    elif (run_dir / "issue-update.json").is_file():
        errors.append("issue-update.json is not valid JSON object")
    return errors


def validate_profile(
    profile: str,
    run_dir: Path,
    *,
    template_path: Path | None = None,
) -> list[str]:
    if profile == "issue-run":
        return validate_issue_run(run_dir, template_path=template_path)
    if profile == "mr-run":
        return validate_mr_run(run_dir)
    if profile == "update-run":
        return validate_update_run(run_dir)
    raise ValueError(
        f"unknown profile '{profile}'; use issue-run, mr-run, or update-run"
    )
