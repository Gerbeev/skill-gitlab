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
operation instructions reference the common engine workflows. To validate discovery in a
specific VS Code installation, open this repository in Agent Mode and check the
four skill names; this requires the user's Copilot environment and is not
simulated by the Python test suite.

Generated output under `docs/examples/output` is ignored by Git. Keep fixtures and
the runner as the maintained source rather than committing reports with temporary
repository paths, commit hashes, and stale validation counts. The example's Issue
output is an unreviewed draft; its MR interpretation is fixture-authored.


Performance measurement (when changing indexing or traversal):

```text
python skills/_engine/scripts/benchmark-index.py --files 1000
```

`test_regressions.py` covers all eleven original audit defects, source-bound review,
patch newlines, depth/confidence
tradeoffs, artifact integrity, runtime entrypoints, and incremental package resolution.
The benchmark measures Python allocations only; see its recorded limitations.

`test_architecture.py` exercises local-path catalog isolation, stable logical IDs,
resource namespaces, interruption at every export-publication phase, corrupt export
recovery, converging and base/head dependency paths, total expansion limits,
semantic Issue findings without template slots, MR review/context invalidation,
preview status propagation, and cross-process snapshot-lock contention. These tests
create isolated repositories and do not execute their source code or business jobs.

The recorded benchmark predates export digest verification; rerun it when establishing
current performance expectations. It is not an organization-scale acceptance result.

## Agent acceptance scenarios

Run these in the intended Copilot/model environment when changing skill behavior.
Use temporary repositories and output directories. Record model/version, prompt,
input revision, outputs, and observed failures. These are evaluation cases, not a
claim that engine tests measure model reasoning or that these cases already passed.

| Request and inputs | Observable acceptance criteria |
|---|---|
| `/analyze-issue`: use the Issue fixture plus `01-requirements.md`, a relevant README, an unrelated note, and a conflicting assumption; change a template instruction. | Exactly two public files; current template preserved; relevant numbered/README inputs considered; unrelated source excluded explicitly; conflicts surfaced; assumption not promoted into acceptance criteria; reviewed manifest matches current sources. |
| `/index-repository`, then `/analyze-mr`: use the three-repository fixture and negative-exposure change from the example runner, with the generated catalog. | No-op parses zero files; only candidate repositories expand; QA names daily-risk and downstream reporting/export jobs with paths and confidence; proposed tests are not described as executed; stale or missing catalogs are disclosed. |
| `/update-issue`: use completed MR artifacts with a validation note reporting a failure, then repeat after tampering with one supporting artifact. | Preview preserves the failure and original requirements, reports follow-ups, and makes no remote write; tampered artifacts are rejected. |

Compare agent runs with and without the skill where practical. Judge evidence,
scope, output usability, and missed runtime targets rather than exact prose or
number of instruction steps. Exercise actual VS Code slash-command discovery
separately from the Python wrapper checks.
