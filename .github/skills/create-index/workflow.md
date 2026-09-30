# Create Index Workflow

**Goal:** Refresh `.repository-analysis/index/` (SQLite + manifests). Does **not** write `graph/`.

**CRITICAL:** If a step directs you to another snapshot file, read it fully and follow it. No exceptions.

## Conventions

- Cross-file references are **absolute snapshot paths** from `render_skill.py`.
- `{project-root}` is the repository root.
- Output: `{project-root}/.repository-analysis/index/` only.

## On Activation

### Step 1: Prepend

{{ workflow.activation_steps_prepend }}

### Step 2: Persistent facts

{{ workflow.persistent_facts }}

### Step 3: Workflow discipline

Read fully and follow: `{{ rendered("references/workflow-discipline.md") }}`

### Step 4: Append

{{ workflow.activation_steps_append }}

## FIRST STEP

Read fully and follow: `{{ rendered("step-01-run-engine.md") }}`
