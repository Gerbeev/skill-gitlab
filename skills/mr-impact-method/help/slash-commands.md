# Which slash command to use

Load this when the user is unsure which MR Impact skill fits, or asks for the recommended pipeline order.

## Canonical pipeline (full change)

1. `/analyze-issue` — requirements → Issue draft under `.repository-analysis/run/`
2. `/create_index` — structural index (required before MR impact analysis)
3. `/create_graph` — optional JSON graph for traversal
4. `/analyze-mr` — MR/branch impact + runtime/QA scope
5. `/update-issue` — preview Issue update from MR artifacts (GitLab apply opt-in)

## Run alone

| Goal | Command |
| --- | --- |
| Issue draft only | `/analyze-issue` (index optional) |
| Refresh model | `/create_index` → optional `/create_graph` |
| MR impact only | `/create_index` if missing, then `/analyze-mr` |

Downstream skills use **only artifacts that exist** under `.repository-analysis/index/` and `graph/` — see `references/analysis-inputs.md` in any skill.
