# Copilot MR Impact Skill

A local-first Copilot Skill for evidence-based analysis of Issue intent, Merge Request implementation, dependency impact, and test scope.

## Current State

Planning phase only. No implementation step has been approved yet.

## Documents

- `GITLAB_ISSUE_TEMPLATE.md` — compact AI-friendly GitLab Issue execution contract derived from DoR/DoD governance and modern engineering issue-writing practices.
- `DOR_DOD_EPIC_ISSUE_LEGACY.md` — legacy Epic/Issue-level DoR/DoD reference, superseded by the 2025 governance document.
- `DOR_DOD_2025.md` — governance Definition of Ready / Definition of Done reference.
- `TASK_STATEMENT.md` — product problem statement and expected behavior.
- `PLAN.md` — detailed implementation plan and approval gates.
- `APPROVALS.md` — current approval state.

## Approval Workflow

Implementation proceeds one plan item at a time.

For the current item:

- `1`, `yes`, or `ok` approves it.
- `0` or `no` rejects it.

A rejected item is not implemented until a revised version is explicitly approved.

After each implemented item:

1. project artifacts are updated;
2. the approval state is updated;
3. a new ZIP package is produced;
4. the next pending item is presented.
