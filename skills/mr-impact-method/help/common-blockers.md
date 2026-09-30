# Common blockers

## Setup / render

| Symptom | Fix |
| --- | --- |
| `render_skill.py` not found | Run `python skills/mr-impact-method/scripts/setup.py --project-root .` |
| Missing `jinja2` | `pip install -r skills/mr-impact-method/scripts/requirements.txt` |
| Agent reads `skills/…/step-*.md` directly | **HALT** — only follow rendered paths under `_mr-impact/render/` |

## Missing prerequisites

| Skill | Blocker | Action |
| --- | --- | --- |
| `create-graph` | No `index/repository-index.sqlite` | Run `/create_index` first |
| `analyze-mr` | No index SQLite | Run `/create_index` (engine errors without it) |
| `analyze-mr` | No graph JSON | Optional — offer `/create_graph`; index-only still works |
| `update-issue` | No `run/01-mr-analysis.md` | Run `/analyze-mr` first |

`setup_check` prints hints on stderr when `render_skill.py` starts — relay them to the user.

## Engine failures

- Non-zero `run_engine.py` exit → **HALT**. Do not invent markdown reports or JSON.
- After exit code 0, run `validate-artifacts` for the profile (`issue-run`, `mr-run`, `update-run`). If validation fails, fix the engine run or inputs — do not patch artifacts by hand to pass review.

## GitLab

- Reads: MCP or `GITLAB_TOKEN` per `docs/reference/gitlab-integration.md`.
- Writes: only after explicit user confirmation in `/update-issue`.
