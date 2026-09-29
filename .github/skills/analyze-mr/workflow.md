# Analyze Merge Request Workflow

**Goal:** Deterministic MR analysis with bounded graph impact and actionable QA/runtime targets.

**CRITICAL:** Read each step file completely before acting.

## Conventions

- `{project-root}` is the repository root.
- Issue context is optional; never output pass/fail vs Issue intent.

## On Activation

{{ workflow.activation_steps_prepend }}

{{ workflow.persistent_facts }}

{{ workflow.activation_steps_append }}

## FIRST STEP

Read fully and follow: `{{ rendered("step-01-gather-context.md") }}`
