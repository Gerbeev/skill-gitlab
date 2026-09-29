# Analyze Issue Workflow

**Goal:** Produce `00-issue-analysis.md` and `01-generated-issue.md` from scoped input and the current `GITLAB_ISSUE_TEMPLATE.md`.

**CRITICAL:** If a step directs you to another snapshot file, read it fully and follow it. No exceptions.

## Conventions

- Cross-file references in this workflow are absolute snapshot paths printed by `render_skill.py`.
- `{project-root}` contains `_mr-impact/` after setup.
- `{skill-root}` is the rendered skill snapshot directory (contains `GITLAB_ISSUE_TEMPLATE.md`).

## On Activation

{{ workflow.activation_steps_prepend }}

Load persistent facts:

{{ workflow.persistent_facts }}

{{ workflow.activation_steps_append }}

## FIRST STEP

Read fully and follow: `{{ rendered("step-01-prepare-input.md") }}`
