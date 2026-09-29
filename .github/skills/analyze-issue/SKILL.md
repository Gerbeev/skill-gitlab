---
name: analyze-issue
description: 'Analyze Issue source material and generate 00-issue-analysis.md plus 01-generated-issue.md from the skill-root GITLAB_ISSUE_TEMPLATE.md. Use when preparing or refining a GitLab Issue from requirements.'
---

Run the following command exactly once without changing the current working directory. Replace `{project-root}` with the absolute path to the project root and `{skill-root}` with the absolute path to this skill's directory:

```bash
python "{project-root}/_mr-impact/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

If `_mr-impact/scripts/render_skill.py` is missing, run setup once:

```bash
python "{project-root}/skills/mr-impact-method/scripts/setup.py" --project-root "{project-root}"
```

- On success, read and follow the one absolute `workflow.md` path printed to stdout.
- On any other failure (including Python or missing `jinja2`), report the command output and **HALT**. Do not run workflow sources directly without rendering.
