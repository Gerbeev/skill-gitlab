---
name: update-issue
description: Prepare an Issue update preview from completed local MR analysis and supplied validation evidence.
---

# Update Issue

Invoke only the shared engine operation `update-issue`:

```text
python skills/_engine/scripts/mr-impact.py update-issue --issue <analyzed-issue> --analysis <mr-analysis-directory> --output <output-directory>
```

Resolve the launcher from the suite root, three directories above this skill directory.
Supply `--validation` only for actual
execution evidence and `--target` when the Issue identifier is known.
Read [the shared update workflow](../../../docs/workflow.md#issue-update) for preview handling.

Return `05-issue-update.md`. Preserve original requirements, uncertainty, and the distinction between
proposed QA work and completed validation. Describe newly observed behavior factually for review.
Preserve MR semantic-review and coverage status; a draft or partial analysis remains qualified in the preview.
This engine generates local previews and has no remote GitLab write operation.
