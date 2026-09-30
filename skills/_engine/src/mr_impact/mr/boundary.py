from __future__ import annotations

import json
from pathlib import Path

from mr_impact.paths import analysis_layout


def load_boundary_catalog(project_root: Path) -> dict | None:
    path = analysis_layout(project_root).boundary_catalog_json
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _entity_tokens(entity: dict) -> set[str]:
    tokens: set[str] = set()
    entity_id = str(entity.get("id", ""))
    kind = str(entity.get("kind", ""))

    if entity_id:
        tokens.add(entity_id)
        if "/" in entity_id:
            tail = entity_id.rsplit("/", 1)[-1]
            tokens.add(tail)
            if kind == "autosys_job":
                tokens.add(tail.upper())

    summary = str(entity.get("summary", ""))
    for word in summary.split():
        if len(word) >= 4 and word.isalnum():
            tokens.add(word)

    return {t for t in tokens if t}


def _collect_anchors(
    *,
    changed_paths: set[str],
    symbols: list[dict],
    runtime_targets: list[dict],
) -> dict[str, set[str]]:
    by_reason: dict[str, set[str]] = {
        "changed_path": set(),
        "symbol": set(),
        "runtime_target": set(),
    }

    for path in changed_paths:
        normalized = path.replace("\\", "/")
        by_reason["changed_path"].add(normalized)
        by_reason["changed_path"].add(Path(normalized).name)

    for sym in symbols:
        name = str(sym.get("name", ""))
        if name:
            by_reason["symbol"].add(name)
            by_reason["symbol"].add(name.upper())

    for target in runtime_targets:
        job = str(target.get("job_or_process", ""))
        if job and job != "(job unknown)":
            by_reason["runtime_target"].add(job)
            by_reason["runtime_target"].add(job.upper())

    return by_reason


def _matches_entity(entity: dict, anchors: dict[str, set[str]]) -> tuple[str, str] | None:
    tokens = _entity_tokens(entity)
    if not tokens:
        return None

    for reason, values in anchors.items():
        for value in values:
            upper = value.upper()
            for token in tokens:
                if token == value or token.upper() == upper:
                    return value, reason
                if len(token) >= 5 and len(value) >= 5 and token.upper() in upper:
                    return value, reason
    return None


def match_boundary_hints(
    catalog: dict | None,
    *,
    changed_paths: set[str],
    symbols: list[dict],
    runtime_targets: list[dict],
) -> dict:
    if not catalog:
        return {
            "schema_version": 1,
            "catalog_present": False,
            "catalog_version": None,
            "hints": [],
        }

    entities = catalog.get("entities")
    if not isinstance(entities, list):
        return {
            "schema_version": 1,
            "catalog_present": True,
            "catalog_version": catalog.get("version"),
            "hints": [],
            "error": "invalid catalog: entities must be a list",
        }

    anchors = _collect_anchors(
        changed_paths=changed_paths,
        symbols=symbols,
        runtime_targets=runtime_targets,
    )
    hints: list[dict] = []
    matched_ids: set[str] = set()

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_id = str(entity.get("id", ""))
        hit = _matches_entity(entity, anchors)
        if hit is None or entity_id in matched_ids:
            continue
        matched_ids.add(entity_id)
        matched_on, match_reason = hit
        hints.append(
            {
                "entity_id": entity_id,
                "kind": entity.get("kind"),
                "summary": entity.get("summary"),
                "matched_on": matched_on,
                "match_reason": match_reason,
                "repos": entity.get("repos", []),
            }
        )

    return {
        "schema_version": 1,
        "catalog_present": True,
        "catalog_version": catalog.get("version"),
        "hint_count": len(hints),
        "hints": hints,
    }


def format_boundary_markdown(hints_payload: dict) -> list[str]:
    if not hints_payload.get("catalog_present"):
        return []
    lines = ["", "## Boundary catalog hints", ""]
    hints = hints_payload.get("hints") or []
    if not hints:
        lines.append("_Catalog loaded; no entities matched this MR context._")
        return lines

    for hint in hints[:20]:
        repos = hint.get("repos") or []
        repo_paths = ", ".join(
            f"`{r.get('path')}` ({r.get('role', '?')})" for r in repos if isinstance(r, dict)
        )
        lines.append(
            f"- **{hint.get('entity_id')}** ({hint.get('kind')}): {hint.get('summary', '')} "
            f"— matched `{hint.get('matched_on')}` via {hint.get('match_reason')}"
        )
        if repo_paths:
            lines.append(f"  - Cross-repo: {repo_paths}")
    if len(hints) > 20:
        lines.append(f"- … and {len(hints) - 20} more (see `boundary-hints.json`)")
    return lines
