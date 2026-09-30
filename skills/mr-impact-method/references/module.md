# MR Impact method module

Hub for Copilot skills (not a slash command). **How to author or change skills:** [skills/README.md](../../README.md).

Narrative prompts and examples: root [README.md](../../../README.md#usage-by-stage-workflow).

## Full change pipeline (canonical order)

Use this sequence for a feature from requirements through MR to Issue update. Each step can also be run alone.

| Step | Copilot command | Needs | Primary output |
| --- | --- | --- | --- |
| 1 | `/analyze-issue` | Input folder or GitLab Issue text; index **optional** (richer anchors if index/graph exist) | `.repository-analysis/run/` — `00-issue-analysis.md`, `01-generated-issue.md`, `issue-intent.json` |
| 2 | `/create-index` | Git repo at project root | `.repository-analysis/index/` |
| 3 | `/create-graph` | Index SQLite from step 2 | `.repository-analysis/graph/` (optional; recommended for graph traversal) |
| 4 | `/analyze-mr` | **Index required**; graph optional; Issue files in `run/` optional | `run/` — MR reports + JSON per [engine-contract](../../../docs/reference/engine-contract.md) |
| 5 | `/update-issue` | MR artifacts in `run/` | `05-issue-update.md`, `issue-update.json` — **nearest QA/runtime chains** per [nearest-runtime-impact-paths.md](../../../docs/reference/nearest-runtime-impact-paths.md) (GitLab apply opt-in) |

After review, clean ephemeral `run/` unless the user keeps artifacts ([run-cleanup.md](run-cleanup.md)).

## Other entry points

| Goal | Commands |
| --- | --- |
| Requirements / Issue only | `/analyze-issue` alone (no index) |
| Refresh structural model | `/create-index` → optional `/create-graph` |
| MR impact only | `/create-index` if missing, then `/analyze-mr` (optional Issue context from `run/` or GitLab) |

Downstream skills read **whatever exists** in `index/` and `graph/` ([analysis-inputs.md](analysis-inputs.md)).

## Agent help (on demand)

| Doc | When to load |
| --- | --- |
| [help/slash-commands.md](help/slash-commands.md) | User unsure which slash command or pipeline order |
| [help/analysis-artifacts.md](help/analysis-artifacts.md) | Questions about `index/`, `graph/`, or `run/` |
| [help/common-blockers.md](help/common-blockers.md) | Setup, missing index/MR artifacts, engine HALT |

## Setup

```bash
python tools/quality.py
```
