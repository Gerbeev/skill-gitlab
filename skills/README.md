# MR Impact Copilot skills (source)

Copilot loads **`.github/skills/`** (five folders). Edit skills here, then re-run setup — never hand-edit `.github/skills/` except to verify sync.

| Path | Role |
| --- | --- |
| `analyze-issue`, `create-index`, `create-graph`, `analyze-mr`, `update-issue` | Slash-command skills |
| `mr-impact-method/` | Setup, `render_skill.py`, `run_engine.py`, shared `references/` (not a slash command) |
| `_engine/` | Python `mr_impact` package (not a skill) |

Canonical CLI and run artifacts: [docs/reference/engine-contract.md](../docs/reference/engine-contract.md).

---

## Writing prompts (read before editing)

Skill text is read **in full on every agent run**. Length and ambiguity cost every time; rare edge cases cost only when they happen.

- Keep **`SKILL.md` thin** — one `render_skill.py` invocation, setup fallback, HALT rules. No workflow steps in `SKILL.md`.
- Put procedure in **`workflow.md`** and **`step-*.md`**. Put long or optional context in **`references/`** and load it from a step (just-in-time).
- Do **not** duplicate engine behavior (graph rules, adapter lists, Issue section names). Point at the engine, [engine-contract](../docs/reference/engine-contract.md), or `GITLAB_ISSUE_TEMPLATE.md`.
- **`description`** in frontmatter must include **Use when** (and optional **Skip when** for false triggers). Match the directory name in `name:`.
- No time estimates (`~5 min`, `ETA`) in skill Markdown — the validator flags them.

Automated tests cover **deterministic** behavior (render, CLI, artifacts). Do not add tests that assert LLM prose.

---

## Layout of one skill

```text
skills/<skill-name>/
├── SKILL.md              # Entry: render only
├── workflow.md           # Jinja: activation + FIRST STEP → rendered snapshot
├── customize.toml        # Defaults; override in _mr-impact/custom/<skill-name>.toml
├── step-01-….md          # RULES → INSTRUCTIONS → CHECKPOINT → NEXT
├── references/           # Skill-specific + copies synced from mr-impact-method
└── bmod.toml             # Listed in mr-impact-method/bmod.toml
```

**Step files**

- Use `{{ rendered("step-02-….md") }}` in **NEXT** (sources only; rendered paths in the running workflow).
- Optional YAML frontmatter on steps for runtime variables the agent sets (e.g. `revision`).
- **CHECKPOINT** = HALT until the user confirms or supplies input.

**Shared discipline** (copied into each skill by setup): `references/workflow-discipline.md`. `workflow.md` must include `{{ rendered("references/workflow-discipline.md") }}` in On Activation.

**Present step** should call `references/validate-present.md` and honor `{{ workflow.on_complete }}` from `customize.toml`.

---

## Customization (per project)

Shipped defaults live in each skill’s `customize.toml`. Project overrides:

```text
_mr-impact/custom/<skill-name>.toml   # [workflow] table — same keys as customize.toml
```

- Scalars (e.g. `on_complete`) **override**.
- Arrays (`persistent_facts`, `activation_steps_*`) **append**.
- Use `file:{project-root}/path` in `persistent_facts` to inject standards docs without forking the skill.

---

## Change workflow

From repository root, **one command** (same as CI):

```bash
python tools/quality.py
```

Or step by step:

```bash
python -m pip install -r skills/mr-impact-method/scripts/requirements.txt
python skills/mr-impact-method/scripts/setup.py --project-root .
python tools/validate_skills.py --strict
python skills/mr-impact-method/scripts/tests/test_render_skills.py
```

**Order of work for a new capability**

1. Update [engine-contract.md](../docs/reference/engine-contract.md) and implement in `skills/_engine/`.
2. Add or adjust `step-*-run-engine.md` (exact `run_engine.py` line).
3. Adjust `workflow.md` / present step / `references/` only as needed for the agent.
4. Run setup + validators above.

CI runs `python tools/quality.py` ([engine.yml](../.github/workflows/engine.yml)).

For large skill edits, optional second pass: [tools/skill-validator.md](../tools/skill-validator.md) (path/step rules after `validate_skills.py`).

---

## Pipeline (typical)

Canonical full-change order (table and alternate entry points): [mr-impact-method/references/module.md](mr-impact-method/references/module.md). Step-by-step prompts: root [README.md](../README.md#usage-by-stage-workflow).

1. `/analyze-issue` → 2. `/create_index` → 3. `/create_graph` (optional) → 4. `/analyze-mr` → 5. `/update-issue`

---

## Further reading

- [workflow-discipline.md](mr-impact-method/references/workflow-discipline.md) — execution rules for agents
- [analysis-inputs.md](mr-impact-method/references/analysis-inputs.md) — index vs graph consumption
- [run-cleanup.md](mr-impact-method/references/run-cleanup.md) — ephemeral `run/` directory
- BMAD reference pattern: `examples/BMAD-METHOD/skills/bmad-code-review/` (thin `SKILL.md`, rendered workflow)
- On-demand agent help: `mr-impact-method/help/` (slash commands, artifacts, blockers)
