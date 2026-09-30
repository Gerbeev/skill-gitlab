# Step 1: Verify Inputs

## RULES

- **Do not** clean `.repository-analysis/run/` — this skill reads existing MR outputs.
- Follow `references/run-cleanup.md` only **after** the user finishes review (optional delete).

## INSTRUCTIONS

Confirm `{project-root}/.repository-analysis/run/` contains:

| Required | Optional (Issue / structured) |
| --- | --- |
| `01-mr-analysis.md` (minimum) | `00-issue-analysis.md`, `01-generated-issue.md`, `issue-intent.json` |
| MR JSON from `analyze-mr` | `boundary-hints.json` (empty hints OK) |

HALT if `01-mr-analysis.md` is missing (run `/analyze-mr` first).

## NEXT

`{{ rendered("step-02-run-engine.md") }}`
