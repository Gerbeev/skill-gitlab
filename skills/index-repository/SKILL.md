---
name: index-repository
description: Build or incrementally refresh a local deep or boundary repository index for dependency and runtime impact discovery.
---

# Index Repository

Invoke only the shared engine operation `index-repository`:

```text
python skills/_engine/scripts/mr-impact.py index-repository --repo <repository> --deep
```

Resolve the launcher relative to the skill-suite checkout when analyzing another repository.
Use `--boundary` for organization catalog inputs. Default indexing uses committed `HEAD`;
use `--worktree` only when the user wants staged, unstaged, and untracked files included.
Report index location, mode, parsed/reused/skipped counts, and detector limitations.

Read [index storage and maintenance](../../docs/index-storage.md) for configuration,
freshness checks, exclusions, and catalog maintenance. Do not execute indexed code.
