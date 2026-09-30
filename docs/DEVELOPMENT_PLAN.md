# MR Impact development plan

Living implementation checklist against [engine-contract.md](reference/engine-contract.md). Update checkboxes as work lands.

## How we execute

Work proceeds **one plan item at a time**. Before each item, the implementer states the intended change in chat; proceed only after **ok** or **1** (or after incorporating feedback).

## Current status

| Area | Status |
| --- | --- |
| Index + graph | Shipped (`create-index`, `create-graph`) |
| Analyze Issue | Shipped (baseline) |
| Analyze MR | MVP + `test_analyze_mr.py` |
| Update Issue | Preview + nearest QA paths ([nearest-runtime-impact-paths.md](reference/nearest-runtime-impact-paths.md)) |
| CI | `.github/workflows/engine.yml` |

## Phase 0 — Contract

- [x] Canonical CLI and artifacts: [reference/engine-contract.md](reference/engine-contract.md)
- [x] Align root [README.md](../README.md) and [V1_SCOPE.md](reference/V1_SCOPE.md) with the contract (five skills, split index/graph commands)
- [x] Align [GLOSSARY.md](reference/GLOSSARY.md) and key [TASK_STATEMENT.md](reference/TASK_STATEMENT.md) sections with the contract

## Phase 1 — `analyze-mr`

- [x] Contract document
- [x] `mr_impact/git/` — parse `--revision`, list changed files
- [x] `changed-symbols.json` from index for changed paths (+ JIL sources)
- [x] Bounded impact graph → `impact-graph.json`
- [x] Runtime/QA hints (JIL/script paths) → `runtime-impact.json`, `test-impact.json`
- [x] Markdown `01`–`04` + `mr-context.json`
- [x] CLI `analyze-mr`
- [x] Integration test on `tests/fixtures/mini-repo`
- [x] Re-index changed files when index is stale (`reindex_changed_paths` in `analyze-mr`)
- [x] Symbol↔diff line mapping (`changed_line_ranges`, `symbols_touched_by_diff`)

## Phase 2 — `update-issue`

- [x] `update-issue --run-dir` → `05-issue-update.md`
- [x] Test: chain after `analyze-mr`
- [x] Structured `issue-update.json`

## Phase 2b — Nearest runtime impact paths (critical)

Spec: [reference/nearest-runtime-impact-paths.md](reference/nearest-runtime-impact-paths.md).

- [x] Diff-accurate seeds → upstream traversal (SQL/PL/SQL → app → JIL), not broad string BFS
- [x] `runtime-impact.json` `primary_qa_targets` + `path[]` (job + box)
- [x] `04-test-plan.md` / `03-impact-analysis.md` driven by primary targets only
- [x] `update-issue`: `## QA / runtime (nearest paths)` + `issue-update.json` schema v2
- [x] Engine tests: SQL file change → `PAYMENT_SQL_EOD` chain (fixture repo)

## Phase 3 — Index quality

- [x] Targeted re-index of changed files inside `analyze-mr` (`reindex_changed_paths`)
- [x] C#: dedicated adapter (csproj refs + tree-sitter or regex fallback) + tests
- [x] SQL: `CALL`/`EXEC` and `pkg.member(` → `sql_call` edges + tests
- [x] JIL: `condition` / `depends` job edges + fixture tests
- [x] PL/SQL routine symbols with line spans; `sql_call` from string literals; upstream `calls` edges for nearest paths

## Phase 4 — Analyze Issue

- [x] `issue-intent.json`
- [x] Shared graph traversal (`impact_from_seeds` / `anchored_paths`; document in contract)

## Phase 5 — Boundary catalog

- [x] Surface catalog entries in `03-impact-analysis.md` + `boundary-hints.json`

## Phase 6 — Infrastructure

- [x] GitHub Actions: `.github/workflows/engine.yml` (`unittest`, `validate_skills.py --strict`, `test_render_skills.py`)
- [x] CI smoke: `setup.py` + `--status` assertions in `.github/workflows/engine.yml`

## Phase 7 — Skills polish

- [x] `workflow-discipline.md`: five skills (wording)
- [x] `references/run-cleanup.md` + step files; `setup_check` index/MR prerequisites

## Execution order

```text
Phase 0 (docs) → Phase 1 follow-ups → Phase 2 optional JSON
              → Phases 3–5 by stack priority
              → Phase 6 smoke, Phase 7 polish
```

## Out of scope (V1)

Org-wide index, vector search, autonomous GitLab writes, full PL/SQL semantics, MR vs Issue correctness grading.
