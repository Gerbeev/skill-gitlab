# Engine contract (canonical)

This file is the **source of truth** for CLI commands and run artifacts. Skills and `run_engine.py` must match it. Product narrative lives in [TASK_STATEMENT.md](TASK_STATEMENT.md); delivery phases in [../DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md).

## CLI (`python -m mr_impact`)

All commands use the **Git repository root** as the current working directory unless noted.

| Command | Status | Purpose |
| --- | --- | --- |
| `create-index` | implemented | Build `.repository-analysis/index/` (SQLite + JSON manifests) |
| `create-graph` | implemented | Export `.repository-analysis/graph/` from index |
| `analyze-issue` | implemented | Issue prep: `00-issue-analysis.md`, `01-generated-issue.md` |
| `analyze-mr` | implemented | MR impact from Git revision + index; if index `git_head` ≠ repo HEAD, re-indexes MR changed paths only |
| `update-issue` | implemented | Preview `05-issue-update.md` from MR run artifacts; **nearest QA paths** per [nearest-runtime-impact-paths.md](nearest-runtime-impact-paths.md) |
| `validate-artifacts` | implemented | Deterministic check of run-dir outputs (no GitLab) |
| `index-repository` | deprecated | Runs `create-index` then `create-graph` |

### Flags

| Command | Flags |
| --- | --- |
| `create-index`, `create-graph` | `--analysis-root` (optional) |
| `analyze-issue` | `--input-dir`, `--template`, `--run-dir` (required) |
| `analyze-mr` | `--revision` (required, `base..head`), `--run-dir` (required), `--issue-dir` (optional), `--analysis-root` (optional) |
| `update-issue` | `--run-dir` (required) |
| `validate-artifacts` | `--profile` (`issue-run` \| `mr-run` \| `update-run`), `--run-dir` (required), `--template` (required for `issue-run` when checking template sections) |

Default run directory: `.repository-analysis/run` (gitignored).

Skills run `validate-artifacts` after a successful engine command and **HALT** on non-zero exit before presenting results.

## Persistent analysis tree

| Path | Role |
| --- | --- |
| `.repository-analysis/index/repository-index.sqlite` | Structural index |
| `.repository-analysis/index/index-manifest.json` | Index metadata |
| `.repository-analysis/graph/dependency-graph.json` | Exported graph |
| `.repository-analysis/catalog/boundary-catalog.json` | Optional cross-repo hints (read-only) |

## Per-run artifacts (`--run-dir`)

### Analyze Issue

| File | Producer |
| --- | --- |
| `00-issue-analysis.md` | engine |
| `01-generated-issue.md` | engine |
| `issue-intent.json` | engine (gaps, anchors, bounded dependency paths) |

### Analyze MR

`changed-symbols.json` includes `changed_line_ranges` (head-side hunks), `symbols_touched_by_diff` (line overlap + linked JIL jobs), and `symbols_in_changed_files` (same set as `symbols_touched_by_diff`).

| File | Producer |
| --- | --- |
| `mr-context.json` | engine |
| `changed-symbols.json` | engine |
| `impact-graph.json` | engine |
| `runtime-impact.json` | engine |
| `test-impact.json` | engine |
| `01-mr-analysis.md` | engine |
| `02-change-context.md` | engine |
| `03-impact-analysis.md` | engine |
| `04-test-plan.md` | engine |
| `boundary-hints.json` | engine (optional; empty when no catalog) |

### Update Issue

Requires a completed **Analyze MR** run in the same `--run-dir` (at minimum `01-mr-analysis.md`).

| File | Producer |
| --- | --- |
| `05-issue-update.md` | engine |
| `issue-update.json` | engine (structured preview; `gitlab_apply` always false) |

**QA dependency chains:** The preview surfaces **nearest** runtime paths (diff seed → database/app layers → primary AutoSys **job** and **box**). See [nearest-runtime-impact-paths.md](nearest-runtime-impact-paths.md).

`runtime-impact.json` uses `schema_version` **2** when MR analysis emits `primary_qa_targets`. `issue-update.json` uses `schema_version` **2** when those targets are present; it always includes `nearest_paths_markdown` in the payload for markdown assembly.

GitLab writes are **never** performed by the engine; skills apply via MCP/token after user confirmation.

## Copilot skills (five)

Synced to `.github/skills/` by `skills/mr-impact-method/scripts/setup.py`:

1. `analyze-issue`
2. `create-index`
3. `create-graph`
4. `analyze-mr`
5. `update-issue`

`index-repository` is not a separate skill; use `create-index` then `create-graph`.

## Revision format

`--revision` must be a two-dot range: `base..head` (examples: `HEAD~1..HEAD`, `main..HEAD`). Both ends are resolved with `git rev-parse`.

## Graph traversal (engine)

| Entry | Used by | Seeds |
| --- | --- | --- |
| `anchored_paths` | `analyze-issue` | Issue/job/path anchors from input text |
| `impact_from_seeds` | `analyze-mr` | Changed paths, touched symbols, linked JIL jobs |

Both apply bounded BFS with the same limits in `graph/query.py`.

**Nearest paths (planned):** MR analysis must compute **upstream** paths from diff-accurate seeds to primary AutoSys jobs/boxes for QA; see [nearest-runtime-impact-paths.md](nearest-runtime-impact-paths.md). Raw `impact-graph.json` edge lists are not sufficient for Issue update or test planning.
