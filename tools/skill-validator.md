# Skill validator — inference pass (MR Impact)

Optional second pass after deterministic checks. Adapted from BMAD `tools/skill-validator.md` for this repository’s **rendered** Copilot skills under `skills/`.

## First pass — deterministic (required)

```bash
python tools/validate_skills.py --strict
# or one skill:
python tools/validate_skills.py --json skills/analyze-mr
```

**Deterministic rules:** SKILL-01–08, WORKFLOW-01–02, PATH-02, SEQ-02, TPL-01 (see `tools/validate_skills.py`).

If `--json` reports zero findings for a rule, treat that rule as satisfied. Re-check any rule that still has findings; SKILL-06 (description quality) may still benefit from human judgment.

## When to run the inference pass

- Before merging large skill refactors (new steps, moved `references/`).
- When adding cross-links between steps and `workflow.md`.
- Not required on every commit if `python tools/quality.py` already passes.

## How to use this document

1. Pick a skill directory (`skills/<name>/`, one of the five Copilot skills).
2. Run the deterministic first pass and note remaining findings.
3. Read every file in that directory (recursive).
4. Apply the **judgment rules** below.
5. Report findings in the template at the end. If none, the skill passes.

---

## Definitions

- **Skill directory:** folder with `SKILL.md` (not `mr-impact-method/` or `_engine/`).
- **Rendered skill:** agent runs `render_skill.py` first; workflow steps execute from **`_mr-impact/render/<skill>/…`** snapshots, not from `skills/` directly.
- **Internal reference:** path from one file in the skill to another file in the **same** skill (before render).
- **External reference:** path to repo files (`docs/`, `.repository-analysis/`, engine outputs) — use `{project-root}/…` or `file:{project-root}/…` in `customize.toml`.
- **Originating file:** file containing the reference; resolve relative paths from its directory.

**Layout here:** flat `step-NN-*.md` beside `workflow.md` (not `steps/` subdirectory). In sources, `{{ rendered("step-02-….md") }}` in **NEXT**; in the running workflow, follow **absolute snapshot paths** printed by render.

---

## Judgment rule catalog

### PATH-01 — Internal references are relative to the originating file

- **Severity:** CRITICAL  
- **Rule:** Links or “read `foo.md`” targets inside the skill use `./`, `../`, or a bare sibling name — not absolute paths or `{project-root}` for in-skill files.  
- **Wrong:** `{project-root}/skills/analyze-mr/step-02-run-engine.md` in a step file.  
- **Right:** `references/analysis-inputs.md` from a step in the same skill; `{{ rendered("step-02-run-engine.md") }}` in **NEXT**.

### PATH-03 — External references use `{project-root}` or config

- **Severity:** HIGH  
- **Rule:** Paths outside the skill start with `{project-root}/` or come from `file:{project-root}/…` in `persistent_facts`.  
- **Wrong:** `C:\repo\docs/...`, `../../docs` from a step without clarifying project root.  
- **Right:** `{project-root}/.repository-analysis/run/`, `{project-root}/docs/reference/engine-contract.md`.

### PATH-04 — Avoid intra-skill path variables

- **Severity:** MEDIUM  
- **Rule:** Do not assign `./step-03.md` to a variable in frontmatter if used once or twice; use inline paths or `rendered()`.  
- **Exception:** runtime temps outside the repo (BMAD-style `{diff_file}`) — rare in MR Impact; prefer explicit run-dir paths under `.repository-analysis/run/`.

### PATH-05 — No paths into another skill’s tree

- **Severity:** HIGH  
- **Rule:** Do not reference `skills/other-skill/step-….md`. Invoke the other slash command in prose or duplicate shared text into `mr-impact-method/references/` and sync via setup.

### STEP-04 — CHECKPOINT halts

- **Severity:** HIGH  
- **Rule:** Sections with `### CHECKPOINT` must require HALT until user input (revision, confirmation, apply GitLab).  
- **Fix:** Add explicit “HALT and wait” if missing.

### STEP-05 — No forward loading

- **Severity:** HIGH  
- **Rule:** Do not instruct reading step N+1 before the current step completes, except in **NEXT** or conditional branches.

### SEQ-01 — No skip / reorder optimization

- **Severity:** HIGH  
- **Rule:** No “skip to step 3” or “you may skip checkpoints” except negated (“do NOT skip”). Conditional routing (if index missing → tell user `/create_index`) is allowed.

### REF-01 — Rendered vs runtime placeholders

- **Severity:** HIGH  
- **Rule:** In **sources**, `{{ rendered("…") }}` and `{{ workflow.on_complete }}` are render-time. In **GITLAB_ISSUE_TEMPLATE.md** and generated artifacts, use single-brace placeholders the LLM fills — do not mix `{{ config.* }}` into Issue templates (TPL-01).

### REF-02 — Engine commands are literal in step files

- **Severity:** HIGH  
- **Rule:** `run_engine.py` / `python -m mr_impact` lines in `step-*-run-engine.md` must match [engine-contract.md](../docs/reference/engine-contract.md). No alternate flags invented in prose.

### REF-03 — Invoke other skills by name

- **Severity:** MEDIUM  
- **Rule:** Prefer “run `/create_index`” over hardcoding another skill’s internal step paths.

---

## MR Impact specifics

| Topic | Expectation |
| --- | --- |
| `SKILL.md` | Only `render_skill.py` + setup fallback + HALT; see `skills/README.md`. |
| `workflow.md` | Includes `{{ rendered("references/workflow-discipline.md") }}` in On Activation. |
| Engine failures | Non-zero `run_engine.py` → HALT; never invent `01-mr-analysis.md` content. |
| GitLab writes | Only `/update-issue` after explicit user confirmation. |
| Overrides | `_mr-impact/custom/<skill-name>.toml`, not forks under `.github/skills/`. |

---

## Findings report template

```markdown
## Skill validation: <skill-name>

**Deterministic:** `python tools/validate_skills.py --json skills/<skill-name>` → <N> findings

| Rule | Severity | File | Line | Issue | Suggested fix |
| --- | --- | --- | --- | --- | --- |
| PATH-01 | CRITICAL | step-01….md | 12 | … | … |

**Verdict:** PASS / FAIL (list blocking CRITICAL/HIGH)
```

---

## Related

- Authoring: [skills/README.md](../skills/README.md)
- CI: `python tools/quality.py`
- BMAD full catalog: `examples/BMAD-METHOD/tools/skill-validator.md` (reference only)
