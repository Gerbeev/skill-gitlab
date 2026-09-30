# MR Impact method module

Hub for Copilot skills (not a slash command).

## Recommended pipeline

| Order | Skill | Output |
| --- | --- | --- |
| 1 | `create-index` | `.repository-analysis/index/` |
| 2 | `create-graph` | `.repository-analysis/graph/` (requires index sqlite) |
| 3 | `analyze-issue` | `run/` issue artifacts |
| 4 | `analyze-mr` | `run/` MR artifacts |
| 5 | `update-issue` | `run/` update preview |

Downstream skills read **whatever exists** in `index/` and `graph/` (see `references/analysis-inputs.md`).

## Setup

```bash
python -m pip install -r skills/mr-impact-method/scripts/requirements.txt
python skills/mr-impact-method/scripts/setup.py --project-root .
python tools/validate_skills.py --strict
```
