---
name: analyze-mr
description: 'Analyze a Merge Request: deterministic diff, impact graph, runtime/job QA scope. Uses repository index. Adapted from BMAD code-review workflow shape.'
---

Run the following command exactly once:

```bash
uv run --no-cache "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

- On success, follow the printed `workflow.md` path.
- On failure, **HALT**.
