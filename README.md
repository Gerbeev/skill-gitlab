# MR Impact Copilot Skills

Four VS Code Copilot skills (`/analyze-issue`, `/index-repository`, `/analyze-mr`, `/update-issue`). BMAD-style structure per skill; shared `render_skill.py` lives under `skills/mr-impact-method/` (module, not a fifth skill).

**Setup once:**

```bash
uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root .
```

**Start here:** [docs/README.md](docs/README.md) — Copilot prompts, inputs/outputs, GitLab token/MCP. Skill catalog: [skills/README.md](skills/README.md).

**Specification:** [docs/reference/TASK_STATEMENT.md](docs/reference/TASK_STATEMENT.md) · **MVP scope:** [docs/reference/V1_SCOPE.md](docs/reference/V1_SCOPE.md)
