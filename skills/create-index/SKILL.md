---
name: create-index
description: 'Build or refresh the DEEP structural index for the current Git repository under .repository-analysis/index/. Use when symbols, adapters, or SQLite index are needed before graph export or MR/issue analysis.'
---

Run the following command exactly once without changing the current working directory. Replace `{project-root}` and `{skill-root}`:

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

If render script is missing, run `python "{project-root}/skills/mr-impact-method/scripts/setup.py" --project-root "{project-root}"`.

- On success, read and follow the absolute `workflow.md` path printed to stdout.
- On failure, report output and **HALT**.
