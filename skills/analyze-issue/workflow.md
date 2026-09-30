# Analyze Issue Workflow

**Goal:** Produce `00-issue-analysis.md` and `01-generated-issue.md` from scoped input and the current `GITLAB_ISSUE_TEMPLATE.md`.

**CRITICAL:** If a step directs you to another snapshot file, read it fully and follow it. No exceptions.

## Conventions

- Cross-file references in this workflow are **absolute snapshot paths** from `render_skill.py`.
- `{project-root}` is the repository root (`_mr-impact/` lives here after setup).
- `{skill-root}` is the rendered snapshot directory (contains `GITLAB_ISSUE_TEMPLATE.md`).
- Ephemeral engine output: `{project-root}/.repository-analysis/run/`.

## On Activation

### Step 1: Prepend

Execute in order (`_None._` or an empty list means skip):

{{ workflow.activation_steps_prepend }}

### Step 2: Persistent facts

Treat every entry below as foundational context. Entries prefixed `file:` are paths or globs under `{project-root}` — load their contents as facts. Other entries are literal facts:

{{ workflow.persistent_facts }}

### Step 3: Workflow discipline

Read fully and follow: `{{ rendered("references/workflow-discipline.md") }}`

### Step 4: Append

{{ workflow.activation_steps_append }}

## FIRST STEP

Read fully and follow: `{{ rendered("step-01-prepare-input.md") }}`
