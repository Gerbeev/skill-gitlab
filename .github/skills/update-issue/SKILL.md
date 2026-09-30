---
name: update-issue
description: 'Prepare 05-issue-update.md after MR analysis. Use when syncing Issue text with analysis results; GitLab apply only via token or MCP after explicit user confirmation. Skip when run/01-mr-analysis.md is missing or Issue sync is not needed.'
---

Run the following command exactly once without changing the current working directory. Replace `{project-root}` with the absolute path to the project root and `{skill-root}` with the absolute path to this skill's directory:

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

If `_mr-impact/scripts/render_skill.py` is missing, run setup once:

```bash
python "{project-root}/skills/mr-impact-method/scripts/setup.py" --project-root "{project-root}"
```

Then run the render command again.

- On success, read and follow the one absolute `workflow.md` path printed to stdout.
- On any other failure (including Python or missing `jinja2`), report the command output and **HALT**. Do not run workflow sources from `skills/` or `.github/skills/` directly without rendering.
