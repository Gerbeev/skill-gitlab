# Audit fixes and improvements

Completed in the working tree on 2026-09-23. Requirements: [TASK_STATEMENT.md](TASK_STATEMENT.md).
No commit, push, GitLab mutation, or operational job execution was performed.

## Outcome

All 11 originally reproduced defects are fixed. [Individual bug cards](bugs/README.md)
include original behavior, the correction, and regression acceptance. Original probe
results are preserved alongside the current zero-failure results.

The shared engine now validates patches against selected snapshots, maps exact changed
lines, normalizes Python signatures, resolves relative/package imports, retains stronger
graph evidence, exports standalone boundary definitions, writes valid redacted JSON,
and supports initial commits. Template tokens remain independent and requirement guards
use parent sections. Standalone Issue generation is an explicit draft; completed delivery
requires current source hashes, source decisions, instruction review, and --require-review.

Additional improvements include concise Issue summaries, structured evidence-linked QA
scenarios, completion/follow-up records, integrity checks across all supporting MR
artifacts, and basic cron/systemd/event/profile detection. No-op index work and I/O
allocation were reduced, exclusions precede worktree reads, and catalog queries are batched.

## Verification

- 55 unit/integration/regression tests passed, including 17 added regression tests.
- All 11 original audit probes now report `reproduced: false`; exit code 0.
- All four canonical skill files and four discovery redirects passed the bundled
  skill-creator validator using the existing isolated PyYAML dependency directory.
- The complete three-repository example passed all eight built-in checks and was
  regenerated under [examples/output](examples/output/README.md).
- Python compilation and local Markdown target checks passed.
- Documentation and comments were checked for remaining Cyrillic text; none remains
  in docs, skills, or discovery files. Documentation is written in English.

## Measured local performance

One synthetic run on 1,000 files and one candidate repository:

| Scenario | Seconds | Peak Python MiB | Files parsed |
|---|---:|---:|---|
| initial_deep | 2.1115 | 1.102 | 1000 |
| no_op | 0.1226 | 0.332 | 0 |
| one_file_update | 0.5395 | 0.74 | 1 |
| boundary | 1.5103 | 0.651 | 1000 |
| candidate_expansion | 2.5232 | 2.533 | MR workflow |

[Raw measurement](benchmark-results.json) records environment and counters. Python
allocation peaks exclude native SQLite and Git subprocess memory. The no-op parses
zero files; the one-file change parses exactly one. These are local single-run
measurements, not production latency guarantees or organization-scale load validation.

## Compatibility and remaining limits

Adapter version 2 triggers a one-time rebuild of old indexes. Regenerate older MR
reports before Update Issue because its artifact integrity contract now covers eight
files. Legacy Issue interpretations remain usable for drafts; completed review requires
the new manifest fields. Multi-token template rows use per-occurrence slot IDs.

Compiler-backed C#/Scala resolution, complete framework/deployment semantics, targeted
partial indexing within candidate repositories, and organization-scale validation remain
future capabilities. Static heuristics retain explicit uncertainty. Live Copilot discovery
has not been verified interactively in VS Code. See [the assessment](REQUIREMENTS_AUDIT.md)
and [maintenance guidance](IMPROVEMENT_INSTRUCTIONS.md) for the precise boundaries.
