# Run directory cleanup (`.repository-analysis/run/`)

Per-run outputs are **gitignored**. Persistent analysis lives in `index/`, `graph/`, and `catalog/` — **never delete those** during skill cleanup.

## When to clean

| Situation | Action |
| --- | --- |
| New Issue analysis from scratch | Remove all files under `run/` (or the whole folder) unless the user asked to keep artifacts. |
| New MR analysis | Remove **MR/update** outputs only (see below). **Keep** Issue artifacts if you still need them for `--issue-dir`. |
| Update Issue | **Do not** clean `run/` — MR outputs are required. |
| User finished reviewing | Offer to delete `run/` contents; keep if they want an audit trail. |

## MR / update outputs (safe to delete before a new `analyze-mr`)

- `01-mr-analysis.md` … `04-test-plan.md`
- `05-issue-update.md`, `issue-update.json`
- `mr-context.json`, `changed-symbols.json`, `impact-graph.json`, `runtime-impact.json`, `test-impact.json`, `boundary-hints.json`

## Issue outputs (keep when chaining into MR)

- `00-issue-analysis.md`, `01-generated-issue.md`, `issue-intent.json`
- `gitlab-input/` (if used)

Optional JSON files are **never required** for a skill to start; the engine creates them when applicable.
