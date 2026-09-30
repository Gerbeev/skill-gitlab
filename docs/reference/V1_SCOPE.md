# V1 Scope (MVP)

This document defines what the **first shippable version** of the repository must implement. [TASK_STATEMENT.md](TASK_STATEMENT.md) remains the long-term product specification; when the two differ, **V1 wins for delivery planning**. **CLI commands and run artifacts** are canonical in [engine-contract.md](engine-contract.md).

## V1 product surface

**Five** Copilot project skills under `.github/skills/`, each a thin wrapper over one shared engine (`mr_impact`):

| Skill | Engine command | Required V1 behavior |
| --- | --- | --- |
| `/analyze-issue` | `analyze-issue` | `00-issue-analysis.md` + `01-generated-issue.md` from scoped input + skill-root template |
| `/create-index` | `create-index` | **DEEP** structural index → `.repository-analysis/index/` only |
| `/create-graph` | `create-graph` | Export graph JSON from index SQLite → `.repository-analysis/graph/` |
| `/analyze-mr` | `analyze-mr` | Deterministic diff → symbols → bounded graph → runtime/QA hints → reports + JSON |
| `/update-issue` | `update-issue` | Local preview `05-issue-update.md`; GitLab apply **opt-in** (token or MCP) |

**Not a skill:** `index-repository` CLI (deprecated) runs `create-index` then `create-graph` in one process.

### Engine delivery status (this repo)

| Command | Shipped in `skills/_engine` |
| --- | --- |
| `create-index`, `create-graph` | Yes |
| `analyze-issue` | Yes (baseline) |
| `analyze-mr` | Yes (MVP; see [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) for follow-ups) |
| `update-issue` | Yes (markdown preview) |

## Ephemeral vs persistent storage

| Path | Lifecycle |
| --- | --- |
| `.repository-analysis/run/` | **Per-run outputs** (Issue + MR + update previews). **Gitignored.** Cleared before each new skill run and after the user finishes reviewing, unless they ask to keep artifacts. |
| `.repository-analysis/index/`, `graph/` | **Persistent** repository index; reused across MR runs. |
| `.repository-analysis/catalog/boundary-catalog.json` | **Optional**, curated; not deleted with run cleanup. |

Default CLI flag: `--run-dir .repository-analysis/run`.

## Issue template location

The authoritative template for `/analyze-issue` ships with the skill:

```text
.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md
```

## V1 in scope

### Shared engine

- Single Python package under `skills/_engine/` (`mr_impact`) with CLI entry point.
- Deterministic responsibilities: Git diff/range, file scan, adapter-based symbol/edge extraction, SQLite persistence under `.repository-analysis/`.
- Evidence and confidence on graph edges and runtime links; unresolved items must be explicit.
- Tests against fixture repositories in `skills/_engine/tests/fixtures/`.

### Indexing (DEEP only)

- **One repository at a time** (where the agent runs `/create-index`).
- Incremental refresh when Git HEAD / file hashes change (`create-index`).

**Adapter priority (V1 implementation order):**

1. **C#** (.NET projects, types, references — tree-sitter-c-sharp when installed)
2. **Oracle SQL / PL/SQL** (objects, references — regex/lexer-level minimum; full semantic optional later)
3. **JIL** (AutoSys jobs, commands, script paths, box/parent links)
4. **Scala**, **Java** (tree-sitter when installed)
5. **Generic** + **Python** (`ast`) and operational configs (shell, PowerShell, Databricks YAML, CI files)

Missing optional grammars must not fail indexing; report unread languages honestly.

### Boundary catalog (V1)

**Recommended approach:**

- Ship example: [boundary-catalog.example.json](boundary-catalog.example.json)
- Runtime path: `.repository-analysis/catalog/boundary-catalog.json` (copy or generate offline; setup may seed from example)
- **Read-only** during `/analyze-mr`: map local boundary entities (tables, jobs, APIs) to **candidate repository names** and paths
- **No** automatic clone or deep-index of other repos in V1

This replaces a heavy org-wide indexer for MVP while matching TASK_STATEMENT cross-repo *hints*.

### Analyze Issue

- Template-driven generation from `{skill-root}/GITLAB_ISSUE_TEMPLATE.md`.
- Optional GitLab fetch: MCP preferred, else `GITLAB_TOKEN` REST ([gitlab-integration.md](gitlab-integration.md)).
- Optional **anchored** graph context when an index exists: bounded paths from Issue-named jobs/symbols only ([issue-anchored-graph-traversal.md](issue-anchored-graph-traversal.md)).

### Analyze MR

Phases per TASK_STATEMENT §4 with bounded graph traversal and in-repo runtime discovery (JIL, scripts, launchers). Outputs per [engine-contract.md](engine-contract.md).

Optional: read `boundary-catalog.json`; optional GitLab MR metadata via MCP/token.

### Update Issue

- Always local preview first (`05-issue-update.md`).
- Preview must carry **nearest** QA dependency chains (primary AutoSys job + box) from MR analysis — see [nearest-runtime-impact-paths.md](nearest-runtime-impact-paths.md).
- GitLab write only with explicit user confirmation via MCP or token ([gitlab-integration.md](gitlab-integration.md)).

### Skill packages (BMAD-shaped)

- **Copilot:** exactly **five** folders under `.github/skills/` (synced by `skills/mr-impact-method/scripts/setup.py`).
- **Source:** `skills/<name>/` — `SKILL.md`, `customize.toml`, `workflow.md`, `step-*.md`, `references/`.
- **Module (not a skill):** `skills/mr-impact-method/scripts/` — `render_skill.py`, `setup.py`, `run_engine.py` (BMAD `bmad/` pattern).
- **Runtime:** `_mr-impact/`; rendered workflows under `_mr-impact/render/` (gitignored).
- **Patterns:** thin `SKILL.md` + render; `analyze-mr` steps from `bmad-code-review`.

## V1 explicitly out of scope

- Automated org-wide boundary index build across thousands of repos
- Automatic cross-repository **deep** indexing during `/analyze-mr`
- Vector search
- Autonomous GitLab writes without user confirmation
- MR correctness grading vs Issue
- Exhaustive PL/SQL semantic analysis (beyond V1 lexer/reference extraction)

## V1 quality bar

1. `create-index` reuses unchanged index data (content-hash skip).
2. `/analyze-mr` and `/update-issue` produce **nearest** actionable runtime/QA targets (job + box on an evidence path from diff seeds through DB/app layers), not exhaustive batch job lists — see [nearest-runtime-impact-paths.md](nearest-runtime-impact-paths.md). Full stack chains are **in progress** (Phase 2b in [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md)).
3. `/analyze-issue` does not invent ACs; gaps in `00-issue-analysis.md`.
4. Run folder cleanup behavior documented and gitignored.
5. All **five** skills invoke the same engine via `run_engine.py`.

## Document map

| Document | Role |
| --- | --- |
| [TASK_STATEMENT.md](TASK_STATEMENT.md) | Full product specification |
| [engine-contract.md](engine-contract.md) | Canonical CLI and artifacts |
| [../DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md) | Phased implementation checklist |
| **V1_SCOPE.md** (this file) | MVP delivery boundary |
| [GLOSSARY.md](GLOSSARY.md) | Definitions of skills, engine, render_skill, artifacts |
| [MVP_TASK_IMPROVEMENTS.md](MVP_TASK_IMPROVEMENTS.md) | Rationale and patterns |
| [gitlab-integration.md](gitlab-integration.md) | Token + MCP |
| [../README.md](../README.md) | Copilot usage examples |
