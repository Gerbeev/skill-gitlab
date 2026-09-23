# Repository layout and migration

```text
.github/skills/<operation>/SKILL.md   Minimal Copilot discovery redirects
skills/
  analyze-issue/SKILL.md             Canonical operation instructions
  index-repository/SKILL.md
  analyze-mr/SKILL.md
  update-issue/SKILL.md
  _engine/
    pyproject.toml                  One installable Python package
    src/mr_impact/                  Shared implementation
    scripts/                        CLI, example, audit probes, benchmark
    tests/                          Tests and input fixtures
docs/
  README.md                         Documentation entry point
  TASK_STATEMENT.md                  Original requirements, unchanged
  GITLAB_ISSUE_TEMPLATE.md           Current project template
  REQUIREMENTS_AUDIT.md              Current assessment
  IMPROVEMENT_INSTRUCTIONS.md        Implementation and maintenance guidance
  bugs/                             Individual bug records and before/after evidence
  examples/output/                  Generated workflow examples
```

All implementation, executable helpers, tests, and canonical skill instructions are
under `skills`. The four `.github/skills` files only route to canonical instructions;
no business logic is duplicated. Symbolic links required unavailable administrator
privileges in the current Windows session, so portable text redirects preserve the
project discovery path. Live Copilot discovery still needs an interactive VS Code check.

Markdown in test fixtures is input data. `SKILL.md` files are agent entry instructions,
not user guides. Ordinary documentation and report examples belong under `docs`.
Existing `.git`, `.github`, `.gitattributes`, `.gitignore`, `.obsidian`, and ignored
`.repository-analysis` data remain in place. No unrelated settings were changed.

## Commands from the repository root

```text
python skills/_engine/scripts/mr-impact.py --help
python -m pip install --no-build-isolation --no-deps -e skills/_engine
python -m unittest discover -s skills/_engine/tests -t skills/_engine -v
python skills/_engine/scripts/run-example.py --output docs/examples/output
```

Repeat an existing editable installation using the new package path. Installation is
optional when using the source launcher. For this checkout pass
`--template docs/GITLAB_ISSUE_TEMPLATE.md`; the external-project default remains
`<repo>/GITLAB_ISSUE_TEMPLATE.md` and is never silently replaced with this suite's template.

Original layouts in TASK_STATEMENT remain requirement examples. Current commands live
in [README](README.md) and the workflow guides. Adapter version 2 invalidates older
indexes automatically; regenerate MR reports for the expanded update-integrity contract.
