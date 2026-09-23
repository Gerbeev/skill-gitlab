# Audit bug tracker

All 11 confirmed audit bugs are fixed in the working tree: five P1 and six P2.
Original reproduction evidence is preserved; each card records expected/actual
behavior, impact, implementation, and regression acceptance.

These are local engineering reports suitable for an issue tracker. They were not
published to Anthropic, OpenAI, GitLab, or another external service and do not claim
to reproduce a private vendor tracker format.

| ID | Priority | Severity | Title | Status |
|---|---|---|---|---|
| [BUG-001](BUG-001.md) | P1 | Major | Multiple placeholders on one line overwrite independent values | Fixed |
| [BUG-002](BUG-002.md) | P2 | Major | Optional-field instructions are ignored by standalone extraction | Fixed |
| [BUG-003](BUG-003.md) | P1 | Major | Neutral placeholder names bypass the acceptance-criteria guard | Fixed |
| [BUG-004](BUG-004.md) | P1 | Major | Unified-patch context marks unchanged functions as changed | Fixed |
| [BUG-005](BUG-005.md) | P2 | Major | Multiline Python signature changes are missed | Fixed |
| [BUG-006](BUG-006.md) | P1 | Critical | Fabricated deletion patches are accepted against unchanged revisions | Fixed |
| [BUG-007](BUG-007.md) | P2 | Major | A weak first path hides stronger graph evidence | Fixed |
| [BUG-008](BUG-008.md) | P1 | Major | Relative Python imports lose the actual caller | Fixed |
| [BUG-009](BUG-009.md) | P2 | Major | Standalone boundary definitions are omitted from the catalog | Fixed |
| [BUG-010](BUG-010.md) | P2 | Moderate | Redaction after serialization produces invalid JSON | Fixed |
| [BUG-011](BUG-011.md) | P2 | Moderate | Commit analysis fails on an initial commit | Fixed |

## Verification

```text
python skills/_engine/scripts/audit-repro.py
python -m unittest discover -s skills/_engine/tests -t skills/_engine -v
```

The probe exits 0 when no original bug is reproduced, and 1 if a regression appears.
Fixtures are created in temporary directories; analyzed business code is not executed.

- [Original observations: 11 reproduced](audit-results-before.json)
- [Current observations: zero reproduced](audit-results.json)
- [Requirements assessment](../REQUIREMENTS_AUDIT.md)
- [Improvements and remaining capability boundaries](../IMPROVEMENT_INSTRUCTIONS.md)

The register covers confirmed audit findings; passing it does not establish complete
semantic resolution, organization-scale performance, or live Copilot discovery.
