# Improvement implementation and maintenance instructions

Requirements remain defined solely by [TASK_STATEMENT.md](TASK_STATEMENT.md).
The [assessment](REQUIREMENTS_AUDIT.md) separates implemented guarantees from
capabilities that still need project-specific adapters or real-world validation.

## Implemented corrections

All 11 [bug cards](bugs/README.md) have working-tree fixes and regression coverage:
independent template tokens, optional-field handling and semantic draft status,
ancestor-aware requirements protection, exact diff line mapping, full Python
signatures, snapshot-checked patches, strongest bounded paths, relative imports,
standalone boundary definitions, structural JSON redaction, and initial commits.
Fixes live in the common engine, not duplicated wrapper implementations.

## Implemented workflow improvements

- `inspect-issue` produces current template/source fingerprints, slots, and instruction
  IDs. A reviewed interpretation includes relevance decisions for every source and
  review of every template instruction. `--require-review` prevents draft delivery.
- Issue summaries group repeated statements, avoid repeating full filled text, and
  disclose summary truncation. Full source material and generated fills remain available.
- QA interpretations can attach structured target/repository/precondition/input/expected
  scenarios. Unknown targets are rejected and planned validation remains unexecuted.
- Completion checks describe evidence availability without grading implementation.
  Follow-up records retain IDs, status, revision, reason, and action in Issue previews.
- Update Issue verifies all eight supporting MR artifact hashes. Older outputs must
  be regenerated before using this strengthened integrity contract.
- Runtime detection now covers simple cron entries, systemd services/timers, explicit
  event-call candidates, and AutoSys profile configuration references.

## Implemented efficiency improvements

- Exact no-op index refresh avoids adapters, graph maintenance, and artifact rewrites.
  Missing exports are recovered without parsing unchanged source files.
- Worktree exclusions and size limits are applied before content hashing.
- Organization candidate observations use batches of up to 400 entity IDs per query.
- Git/text readers allocate for actual file/output size rather than the configured
  maximum. Byte limits remain enforced.
- Python package-import resolution refreshes after file changes without parsing
  unchanged callers. Original import targets remain available as provenance.
- Contradiction-candidate lookup uses a precomputed set instead of repeated full scans.

Measure changes with:

```text
python skills/_engine/scripts/benchmark-index.py --files 1000
```

The recorded [benchmark](benchmark-results.json) includes platform, Python version,
file count, elapsed time, Python allocation peak, and indexing counters. The
[earlier buffer-allocation measurement](benchmark-before-buffer-fix.json) is retained
as evidence of the allocation issue discovered during this implementation, not as a
benchmark of the untouched pre-audit product. Timings are single runs and should not
be treated as statistically significant latency improvements.

## Deliberate capability boundaries

The recommendations to add compiler-backed C#/Scala resolution, framework-specific
runtime/deployment mappings, targeted partial indexing inside candidate repositories,
and organization-scale load validation require representative repositories and
additional implementation. They are not relabeled as fixed bugs or implied by passing
synthetic tests. The current engine explicitly reports heuristic and unresolved edges.

When extending these capabilities, add positive, negative, ambiguous, and incremental
fixtures first. Preserve exact-versus-candidate confidence and all provenance. Do not
replace a missing detector with an enum value or broaden scope to an unbounded scan.
Do not build a second fixed Issue schema. Arbitrary source/template prose remains
untrusted data and never authorizes execution or remote mutation.

## Required maintenance checks

```text
python -m unittest discover -s skills/_engine/tests -t skills/_engine -v
python skills/_engine/scripts/audit-repro.py
python -m compileall -q skills/_engine/src skills/_engine/scripts skills/_engine/tests
python skills/_engine/scripts/run-example.py --output <temporary-output-directory>
```

The audit probe must now exit 0. Add a regression asserting correct behavior before
closing a new bug. A no-op must parse zero files; an independent one-file change must
parse one; bounded traversal must preserve configured budgets. Re-run the benchmark
when changing performance-sensitive code and state what its data does and does not
prove. Keep every documentation page, code comment, and docstring in English.
