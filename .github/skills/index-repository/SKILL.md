---
name: index-repository
description: 'Build or refresh the deep structural index and dependency graph for the current Git repository. Use before /analyze-mr.'
---

Run the following command exactly once without changing the current working directory. Replace `{project-root}` and `{skill-root}`:

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

If render script is missing, run `skills/mr-impact-method/scripts/setup.py --project-root "{project-root}"`.

- On success, read and follow the absolute `workflow.md` path printed to stdout.
- On failure, report output and **HALT**.
