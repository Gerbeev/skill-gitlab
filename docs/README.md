# Documentation

**Install and usage:** root **[README.md](../README.md)** (setup, staged workflow, prompts, outputs).

## Index

| Document | Purpose |
| --- | --- |
| [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) | Roadmap — phases and delivery status |
| [reference/engine-contract.md](reference/engine-contract.md) | **Canonical CLI** and run artifacts (skills must match) |
| [reference/GLOSSARY.md](reference/GLOSSARY.md) | Terms: skills, engine, indexing, artifacts |
| [reference/analysis-inputs.md](reference/analysis-inputs.md) | Which index/graph files downstream skills read |
| [reference/issue-anchored-graph-traversal.md](reference/issue-anchored-graph-traversal.md) | Anchored graph walks (Issue and MR) |
| [reference/TASK_STATEMENT.md](reference/TASK_STATEMENT.md) | Full product specification |
| [reference/V1_SCOPE.md](reference/V1_SCOPE.md) | **MVP delivery boundary** |
| [reference/MVP_TASK_IMPROVEMENTS.md](reference/MVP_TASK_IMPROVEMENTS.md) | Design rationale (BMAD patterns, V1 simplifications) |
| [reference/python-setup.md](reference/python-setup.md) | Python 3.11+ without `uv` |
| [reference/gitlab-integration.md](reference/gitlab-integration.md) | GitLab token + MCP (read / opt-in write) |
| [reference/boundary-catalog.example.json](reference/boundary-catalog.example.json) | Optional cross-repo boundary catalog seed |

**Issue template (canonical):** `.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md` (synced from `skills/analyze-issue/` by setup).

Reference example (not shipped as product code): **`examples/BMAD-METHOD`** — thin Copilot `SKILL.md` → `render_skill` → workflow steps.

Local CI mirror: `python tools/quality.py` (from repo root). Optional skill review: [tools/skill-validator.md](../tools/skill-validator.md).

Agent routing / blockers (not loaded on every run): [skills/mr-impact-method/help/](../skills/mr-impact-method/help/).

## Layout

Authoring skills: **[skills/README.md](../skills/README.md)**.

```text
skills/                   # Skill sources (edit here)
.github/skills/           # Copilot entry (five folders; synced by setup)
skills/mr-impact-method/  # setup.py, render_skill, run_engine
skills/_engine/           # mr_impact Python package
_mr-impact/               # Runtime after setup (gitignored; run setup.py)
.repository-analysis/     # index, graph, catalog, ephemeral run/
```

## Ephemeral run output

Per-run artifacts go to `.repository-analysis/run/` (gitignored). Unless the user asks to keep files, delete that folder before a new skill run and after presenting results. Persistent index and graph under `.repository-analysis/index/` and `.repository-analysis/graph/` are not deleted between runs.

## GitLab (optional)

Set `GITLAB_TOKEN` (and `GITLAB_HOST` if not gitlab.com). Prefer GitLab MCP in Copilot when available. Details and prompt hints: [reference/gitlab-integration.md](reference/gitlab-integration.md).
