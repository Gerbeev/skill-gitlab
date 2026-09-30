---
name: analyze-mr
description: 'Analyze a Merge Request with deterministic diff, impact graph, and runtime/job QA scope. Use when reviewing an MR or branch and the repository index is available or should be built first.'
---

Run the following command exactly once:

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

- On success, follow the printed `workflow.md` path.
- On failure, **HALT**.
