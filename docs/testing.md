# Validation

Run from the project root using Python 3.11 or later and Git:

```text
python -m unittest discover -v
python -m compileall -q src scripts tests
python scripts/run-example.py --output examples/output
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

Review `examples/output/mr/04-test-plan.md` for actual QA targets and graph paths.
The runner asserts that local and downstream jobs are found, that changed symbols
are mapped, and that modifying a copied template changes generated headings.

Skill wrapper checks verify four frontmatter names, operation routing, and that
business logic lives outside skill directories. To validate discovery in a
specific VS Code installation, open this repository in Agent Mode and check the
four skill names; this requires the user's Copilot environment and is not
simulated by the Python test suite.

The optional external `skill-creator` frontmatter validator requires PyYAML.
During implementation it was run with PyYAML isolated under the ignored
`.repository-analysis/validation-deps` directory. PyYAML is not an engine or test
suite dependency and is not required for any of the four local workflows.
