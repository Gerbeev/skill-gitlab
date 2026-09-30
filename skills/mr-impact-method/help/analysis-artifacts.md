# Analysis artifact layout

## Persistent (keep between runs)

| Path | Role |
| --- | --- |
| `.repository-analysis/index/repository-index.sqlite` | Structural index |
| `.repository-analysis/index/index-manifest.json` | Index metadata (`git_head`, counts) |
| `.repository-analysis/graph/dependency-graph.json` | Exported graph |
| `.repository-analysis/graph/graph-manifest.json` | Graph metadata |
| `.repository-analysis/catalog/boundary-catalog.json` | Optional cross-repo hints |

Do **not** delete `index/` or `graph/` during routine `run/` cleanup.

## Ephemeral per run (`.repository-analysis/run/`)

Gitignored. Typical contents:

- **Issue:** `00-issue-analysis.md`, `01-generated-issue.md`, `issue-intent.json`
- **MR:** `01-mr-analysis.md` … `04-test-plan.md`, JSON (`mr-context.json`, `impact-graph.json`, …)
- **Update:** `05-issue-update.md`, `issue-update.json` (should promote **nearest QA paths** from MR `runtime-impact.json` — see [nearest-runtime-impact-paths.md](../../../docs/reference/nearest-runtime-impact-paths.md))

Unless the user asks to keep files, delete `run/` before a new skill run and after presenting results (`references/run-cleanup.md`).

## Evidence discipline

- Engine outputs are produced only by `run_engine.py` / `python -m mr_impact`.
- After a successful engine run, validate with `validate-artifacts` (see engine contract) before presenting or editing prose.
- GitLab writes happen only in `/update-issue` after explicit user confirmation.
