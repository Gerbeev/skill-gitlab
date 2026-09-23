---
name: index-repository
description: Build, refresh, or check a local repository's deep or boundary index for dependency and runtime impact analysis.
---

# Index Repository

Use the shared engine operation `index-repository`:

```text
python skills/_engine/scripts/mr-impact.py index-repository --repo <repository> --deep
```

Resolve the launcher from the suite root, three directories above this skill directory.
Use `--boundary` for organization catalog inputs. Default indexing uses committed `HEAD`;
use `--worktree` only when the user wants staged, unstaged, and untracked files included.
Report index location, mode, parsed/reused/skipped counts, and detector limitations.

Read [index storage and maintenance](../../../docs/index-storage.md) for configuration,
freshness checks, exclusions, and `index-organization` when catalog aggregation is requested.
Do not execute indexed code.
