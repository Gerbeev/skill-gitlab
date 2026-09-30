# Workflow discipline (MR Impact)

This file is shared across all four Copilot skills. Follow it for the whole run.

## Step-file architecture

- **Micro-files:** Each step is self-contained; follow it exactly.
- **Just-in-time loading:** Read only the current step file (plus paths it names).
- **Sequential:** Complete steps in order; do not skip or merge steps.
- **Checkpoints:** At `### CHECKPOINT`, HALT until the user confirms or supplies missing input.

## Step processing rules

1. **Read completely** — entire step file before acting.
2. **Follow sequence** — RULES → INSTRUCTIONS → CHECKPOINT → NEXT.
3. **Load next** — when directed, read the next snapshot path fully before continuing.

## Critical rules

- **Never** load multiple step files at once unless a step explicitly lists several reads.
- **Never** run workflow sources from `skills/` or `.github/skills/` directly; only rendered snapshots under `_mr-impact/render/`.
- **Never** fabricate engine outputs; non-zero `run_engine.py` exit means HALT.
- **Always** use absolute snapshot paths from `rendered("…")` or stdout from `render_skill.py`.

## Human-facing output

- Lead with a short summary; put long reports in files under `.repository-analysis/`.
- On present steps, follow `references/validate-present.md`.
