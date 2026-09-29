---
name: update-issue
description: 'Prepare 05-issue-update.md after MR analysis. Optional GitLab apply via token or MCP after explicit user confirmation.'
---

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

- On success, follow printed `workflow.md`.
- On failure, **HALT**.
