# Create Graph Workflow

**Goal:** Export `.repository-analysis/graph/` from existing index SQLite. Does **not** rescan the repository.

**CRITICAL:** If a step directs you to another snapshot file, read it fully and follow it. No exceptions.

## Conventions

- Cross-file references are **absolute snapshot paths** from `render_skill.py`.
- `{project-root}` is the repository root.
- Input: `{project-root}/.repository-analysis/index/repository-index.sqlite`
- Output: `{project-root}/.repository-analysis/graph/` only.

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

Read fully and follow: `{{ rendered("step-01-verify-index.md") }}`
