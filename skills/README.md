# Skills

**Four Copilot skills** (only these are synced to `.github/skills/`):

| Skill | Directory |
| --- | --- |
| `/analyze-issue` | `analyze-issue/` |
| `/index-repository` | `index-repository/` |
| `/analyze-mr` | `analyze-mr/` |
| `/update-issue` | `update-issue/` |

BMAD-style package per skill: `SKILL.md`, `customize.toml`, `workflow.md`, `step-*.md`, optional `references/`. Shared hub scripts (from BMAD `render_skill` pattern) live in **`mr-impact-method/`** — not a fifth slash command.

```bash
uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root .
```

Engine (in progress): `skills/_engine/` — see [skills/_engine/README.md](_engine/README.md).
