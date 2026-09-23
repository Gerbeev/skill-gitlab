# Validation

Run from the project root using Python 3.11 or later and Git:

```text
python -m unittest discover -s skills/_engine/tests -t skills/_engine -v
python -m compileall -q skills/_engine/src skills/_engine/scripts skills/_engine/tests
python skills/_engine/scripts/run-example.py --output docs/examples/output
```

Tests use the standard library and isolated temporary repositories. They do not
execute fixture code or operational jobs. Coverage includes source isolation,
dynamic template sections and instructions, missing facts, interpretation
provenance, incremental/no-op indexing, changes/deletions/renames, worktree
freshness, boundary exports, confidence/graph bounds, representative adapters,
unified diff parsing, before/after symbols, deleted dependencies, lazy candidate
expansion, local preview integrity, and security error paths.

The integration fixture demonstrates:

```text
repo-a: Scala writer + Databricks task + AutoSys launcher
  -> WRITES table://RISK/DAILY_EXPOSURE
repo-b: Oracle reporting procedure + shell launcher + AutoSys reporting job
  -> WRITES table://REPORTING/DAILY_REPORT
repo-c: PowerShell data reader + downstream AutoSys regulatory export
```

The example runner makes temporary Git repositories, creates a real change,
indexes A deeply and B/C at boundary level, aggregates an organization catalog,
generates the Issue artifacts, analyzes the MR, and prepares an Issue update.
It copies the nine MR artifacts, two Issue artifacts, update preview, and measured
validation summary to the requested output directory. Source fixture repositories
and indexes are removed when the temporary workspace closes. Retained reports
are examples, not live indexes. Repository IDs and commit hashes may differ
between runs.

Review `docs/examples/output/mr/04-test-plan.md` for actual QA targets and graph paths.
The runner asserts that local and downstream jobs are found, that changed symbols
are mapped, and that modifying a copied template changes generated headings.

Skill wrapper checks verify four frontmatter names, operation routing, and that
canonical operation instructions route to the common `skills/_engine` package. To validate discovery in a
specific VS Code installation, open this repository in Agent Mode and check the
four skill names; this requires the user's Copilot environment and is not
simulated by the Python test suite.

The optional external `skill-creator` frontmatter validator requires PyYAML.
During implementation it was run with PyYAML isolated under the ignored
`.repository-analysis/validation-deps` directory. PyYAML is not an engine or test
suite dependency and is not required for any of the four local workflows.


Audit regressions and performance measurements:

```text
python skills/_engine/scripts/audit-repro.py
python skills/_engine/scripts/benchmark-index.py --files 1000
```

The audit probe now exits 0 and preserves individual observed results for all 11 bugs.
Regression tests also cover source-bound review, patch newlines, depth/confidence
tradeoffs, artifact integrity, runtime entrypoints, and incremental package resolution.
The benchmark measures Python allocations only; see its recorded limitations.
