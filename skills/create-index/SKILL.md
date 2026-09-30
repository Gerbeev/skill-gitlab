---
name: create-index
description: 'Build or refresh the DEEP structural index for the current Git repository under .repository-analysis/index/. Use when symbols, adapters, or SQLite index are needed before graph export or MR/issue analysis. Skip when only re-exporting an unchanged graph JSON.'
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
