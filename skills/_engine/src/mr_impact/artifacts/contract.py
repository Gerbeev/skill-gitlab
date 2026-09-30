"""Structural checks for run-dir JSON (stdlib only; mirrors engine-contract.md)."""

from __future__ import annotations

from typing import Any


def _require_dict(data: Any, label: str) -> list[str]:
    if not isinstance(data, dict):
        return [f"{label} must be a JSON object"]
    return []


def _require_keys(data: dict, label: str, keys: frozenset[str]) -> list[str]:
    return [f"{label} missing key: {key}" for key in keys if key not in data]


def validate_changed_symbols(data: dict) -> list[str]:
    errors = _require_keys(
        data,
        "changed-symbols.json",
        frozenset(
            {
                "schema_version",
                "revision",
                "base_sha",
                "head_sha",
                "changed_files",
                "symbols_touched_by_diff",
            }
        ),
    )
    if errors:
        return errors
    if not isinstance(data.get("changed_files"), list):
        errors.append("changed-symbols.json: changed_files must be a list")
    if not isinstance(data.get("symbols_touched_by_diff"), list):
        errors.append("changed-symbols.json: symbols_touched_by_diff must be a list")
    return errors


def validate_impact_graph(data: dict) -> list[str]:
    errors = _require_keys(data, "impact-graph.json", frozenset({"schema_version", "edges"}))
    if errors:
        return errors
    if not isinstance(data.get("edges"), list):
        errors.append("impact-graph.json: edges must be a list")
    return errors


def validate_runtime_impact(data: dict) -> list[str]:
    errors = _require_keys(data, "runtime-impact.json", frozenset({"schema_version"}))
    if errors:
        return errors
    version = data.get("schema_version")
    if version == 2:
        errors.extend(_require_keys(data, "runtime-impact.json", frozenset({"primary_qa_targets", "targets"})))
        if not isinstance(data.get("primary_qa_targets"), list):
            errors.append("runtime-impact.json: primary_qa_targets must be a list")
        if not isinstance(data.get("targets"), list):
            errors.append("runtime-impact.json: targets must be a list")
    elif not isinstance(data.get("targets"), list):
        errors.append("runtime-impact.json: targets must be a list when schema_version is not 2")
    return errors


def validate_test_impact(data: dict) -> list[str]:
    errors = _require_keys(data, "test-impact.json", frozenset({"schema_version", "scenarios"}))
    if errors:
        return errors
    if not isinstance(data.get("scenarios"), list):
        errors.append("test-impact.json: scenarios must be a list")
    return errors


def validate_mr_context(data: dict) -> list[str]:
    return _require_keys(
        data,
        "mr-context.json",
        frozenset({"schema_version", "generated_at", "revision"}),
    )


def validate_boundary_hints(data: dict) -> list[str]:
    errors = _require_keys(data, "boundary-hints.json", frozenset({"hint_count", "hints"}))
    if errors:
        return errors
    if not isinstance(data.get("hints"), list):
        errors.append("boundary-hints.json: hints must be a list")
    return errors


MR_JSON_VALIDATORS: tuple[tuple[str, Any], ...] = (
    ("mr-context.json", validate_mr_context),
    ("changed-symbols.json", validate_changed_symbols),
    ("impact-graph.json", validate_impact_graph),
    ("runtime-impact.json", validate_runtime_impact),
    ("test-impact.json", validate_test_impact),
    ("boundary-hints.json", validate_boundary_hints),
)


def validate_mr_json_file(filename: str, data: dict) -> list[str]:
    for name, validator in MR_JSON_VALIDATORS:
        if name == filename:
            return validator(data)
    return []
