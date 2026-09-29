# MVP Task Statement — Analysis and Improvements

This document analyzes [TASK_STATEMENT.md](TASK_STATEMENT.md), compares it with the reference implementations under `examples/`, and records **recommended clarifications and simplifications** for the MVP. Repository content is **English only**; this analysis informed updates to [V1_SCOPE.md](V1_SCOPE.md).

## Executive summary

The task statement is strong on **product intent**, **evidence discipline**, and **separation of AI vs deterministic work**. For an MVP, the main risk is **scope collision**: sections 3–4 and 14 describe organization-scale boundary indexing and cross-repo MR expansion, while §11 lists an organization-wide graph as a non-goal for the first version. **[V1_SCOPE.md](V1_SCOPE.md) resolves that tension** by keeping the full spec intact and binding delivery to single-repo DEEP indexing plus an optional read-only catalog stub.

Recommended engineering patterns:

| Source | Take for this repo |
| --- | --- |
| **BMAD Method** (`examples/BMAD-METHOD`) | Thin `SKILL.md` → single CLI/renderer → halt on failure; workflow content lives outside the skill surface |
| **iFlow** (`examples/iFlow`) | Python `ast` floor; optional tree-sitter; confidence + `unknown` reporting; index as cache tied to Git freshness |

---

## TASK_STATEMENT strengths (keep as-is)

1. **Four skills, one engine** — clear product surface and test strategy.
2. **Analyze Issue** — two artifacts only; template is the sole Issue schema (`GITLAB_ISSUE_TEMPLATE.md`).
3. **Analyze MR** — explicit ban on grading the developer against the Issue; neutral traceability only.
4. **Runtime/QA focus** — impact must reach jobs/processes, not only files (differentiator for enterprise estates).
5. **Evidence model** — detector, confidence, paths; aligns with iFlow trust levels.
6. **Security** — untrusted Issue/MR/docs; no command execution from content.

---

## Gaps and contradictions (addressed in V1_SCOPE)

| Topic | In TASK_STATEMENT | MVP resolution |
| --- | --- | --- |
| Org boundary catalog | Required in §3, §4, §13–14 | V1: optional local JSON stub; no automated org indexer |
| Cross-repo deep scan | Described as core strategy | V1: report external candidates only; no automatic deep-index of other repos |
| `MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md` | Referenced | Keep as **target architecture**; V1 implements **single-repo** subset + extension points (`catalog.py`, `expansion.py`) |
| `V1_SCOPE.md` | Linked in delivery note | **Created**; TASK_STATEMENT delivery note updated to point here |
| Package layout `src/mr_impact/...` | §7 | Actual layout: `skills/_engine/src/mr_impact/` — spec should not imply a second root |
| `issue-intent.json` | §12 artifacts list | Clarify: optional machine artifact for `/analyze-issue`; not a third user-facing file |

---

## Simplifications for MVP

### 1. Indexing adapters — staged rollout

**V1 adapter priority (confirmed):**

1. **C#**
2. **Oracle SQL / PL/SQL**
3. **JIL** (AutoSys)
4. **Scala**, **Java**
5. Python (`ast`), generic, scripts, YAML/config

**Defer:** full PL/SQL semantic graph, exhaustive DI/reflection, generated-code deep parsing.

**iFlow borrow:** `examples/iFlow/framework/readers/python_ast.py` and `treesitter.py` — use the same dependency list pattern (`requirements.txt` + optional `_lib` install) so CI and laptops without grammars still get honest “unread” status.

### 2. Graph edges — V1 required vs optional

**V1 required edge types:** `IMPORTS`, `CALLS` (where resolved), `REFERENCES`, `TESTED_BY`, `CONFIGURES`, `SCRIPT_INVOKES` / `JOB_LAUNCHES` (operational adapters).

**V1 optional / best-effort:** `INHERITS`, `IMPLEMENTS`, DB/event/API edges — emit only when adapter confidence ≥ threshold; otherwise omit or mark `UNRESOLVED`.

### 3. Analyze MR phases — merge reporting burden

Ten phases are correct logically; for MVP **one engine pipeline** can emit the same content with **four human reports** (already listed). Avoid requiring the agent to run ten separate “phase skills.”

**Simplify agent instructions:** “Run `mr-impact analyze-mr` once; then summarize if needed.”

### 4. Analyze Issue — deterministic pre-pass (optional V1.1)

Not required for first Copilot-only flow, but low-cost win:

- Engine scans input folder file list and template section headings.
- Skill/LLM fills narrative sections and AC quality.

Keeps template drift impossible without parsing the template file.

### 5. Artifacts and output directory

**V1 convention (confirmed):**

| Kind | Location |
| --- | --- |
| Persistent index | `.repository-analysis/index/`, `.repository-analysis/graph/` |
| Per-run Issue/MR/update outputs | `.repository-analysis/run/` (gitignored, **cleaned before/after runs** unless user keeps) |
| Optional boundary catalog | `.repository-analysis/catalog/boundary-catalog.json` (seed from [boundary-catalog.example.json](boundary-catalog.example.json)) |

Document in CLI help and each `SKILL.md`.

### 6. Validation gate (iFlow-inspired)

iFlow `check.py` validates artifact shape against templates. For MVP, add **engine subcommand or test module** `validate-artifacts` that checks:

- required files exist;
- JSON schemas minimal (required keys);
- `01-generated-issue.md` sections match template headings (order-sensitive).

Skills should mention: “If validation fails, halt and fix deterministically before rewriting prose.”

---

## BMAD Method — applicable skills and patterns

BMAD ships many skills; only a subset maps to this product.

| BMAD skill | Relevance | Pattern to adopt |
| --- | --- | --- |
| `bmad-build`, `bmad-code-review` | High | `SKILL.md` runs **one** `render_skill.py` / CLI command; on failure **HALT**; workflow in separate `workflow.md` |
| `bmad-project-context` | Medium | Activation steps, `references/` for long instructions; skill stays short |
| `bmad` (router) | Low for V1 | Optional later: meta-skill listing four commands — **not** required if Copilot exposes slash commands |
| `bmad-qa-generate-e2e-tests` | Medium (ideas) | Concrete validation scenarios — align with §4 Phase 9 wording |
| `bmad-spec`, `bmad-prd` | Low | Different domain (greenfield product docs), not MR impact |

**Recommended V1 skill shape** (BMAD-like, without `_bmad` templating in MVP):

```markdown
---
name: analyze-mr
description: Analyze a Merge Request using the shared mr-impact engine...
---

Run once from the repository root (replace paths):

python _mr-impact/scripts/run_engine.py --project-root . -- analyze-mr [args]

- On non-zero exit: show stderr and STOP. Do not guess graph results.
- On success: present paths to 01–04 markdown reports and offer to open runtime-impact.json.
```

Stage 2 work: implement four `SKILL.md` files **strictly** from this pattern + TASK_STATEMENT §15.

---

## iFlow — parsing and estate model

| iFlow concept | Application here |
| --- | --- |
| `python_ast.read()` | Baseline Python adapter; local type bindings; line spans for MR hunk mapping |
| `treesitter` reader | Optional multi-language; extension → grammar table; degrade to “unread” |
| Trust: `derived` vs `matched` | Map to engine `confidence` + `detector` fields |
| `estate.py freshness` | Index manifest: Git commit, file hashes, adapter versions |
| `unknown` / `corrections` | Surface in `03-impact-analysis.md` and JSON as `UNRESOLVED` nodes |
| On-demand vs persisted | TASK_STATEMENT chooses **persisted SQLite** for MR speed — keep iFlow’s invalidation rules in `index-manifest.json` |

**Libraries (from iFlow `readers/requirements.txt`):** vendored under `skills/_engine/src/mr_impact/readers/`; pin list in `readers/requirements.txt` when the engine adapters layer is implemented.

---

## Architecture improvements (engine + docs)

1. **Single entry CLI** — `mr-impact` with subcommands matching four skills; skills must not fork alternate orchestration.
2. **Adapter registry** — explicit registration in `adapters.py`; generic last; feature flags for heavy grammars.
3. **Expansion module** — keep `expansion.py` API but V1 implements **in-repo** traversal only; cross-repo = read catalog edges without remote clone.
4. **Template module** — `template.py` parses `GITLAB_ISSUE_TEMPLATE.md` headings and HTML comments for AI contract text.
5. **Safety** — `safety.py` rejects path traversal and unsafe paths from Issue content (already aligned with TASK_STATEMENT §10).
6. **Docs triad:**
   - TASK_STATEMENT = north star
   - V1_SCOPE = sprint boundary
   - MVP_TASK_IMPROVEMENTS = this file (design rationale)

---

## Proposed TASK_STATEMENT edits (applied)

1. Delivery note: clarify that **V1_SCOPE** is authoritative for MVP; full spec describes end state.
2. §11 Non-Goals: add bullet “automatic cross-repo deep indexing (V1)” to align with §3–4 narrative.
3. §7 Repository structure: point to `skills/_engine/` instead of ambiguous `src/mr_impact` at repo root.
4. §12: mark `issue-intent.json` as optional; add default output directory note.

---

## Product decisions (recorded)

| Topic | Decision |
| --- | --- |
| Issue template | `.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md` (skill root); `docs/` mirror for readability |
| Adapter priority | C# → Oracle SQL/PL/SQL → JIL → Scala/Java → rest |
| Boundary catalog | Example JSON in repo; runtime file `.repository-analysis/catalog/boundary-catalog.json`; read-only hints in V1 |
| Run outputs | `.repository-analysis/run/`, ephemeral cleanup |
| Copilot skills path | `.github/skills/` |
| GitLab | Optional reads + opt-in writes via `GITLAB_TOKEN` or GitLab MCP ([gitlab-integration.md](gitlab-integration.md)) |

---

## Stage 2 preview (skills implementation)

Per user plan, next phase:

1. Copy BMAD **thin SKILL** pattern only (no `_bmad` install requirement).
2. Wire each skill to `skills/_engine` CLI with documented arguments matching §15 examples.
3. Add `references/` per skill only if `SKILL.md` exceeds ~120 lines (e.g. analyze-mr phase checklist).
4. Integration test: skill text contains required halt/run commands; engine tests cover behavior.

No skill should embed indexing algorithms or Issue section lists duplicated from `GITLAB_ISSUE_TEMPLATE.md`.
