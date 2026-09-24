# MR Impact skill suite

Four GitHub Copilot Agent Skills share one local Python engine:

- `/analyze-issue`: source analysis and a current-template Issue description.
- `/index-repository`: reusable deep or boundary repository indexing.
- `/analyze-mr`: deterministic change extraction, runtime impact, and QA scope.
- `/update-issue`: a local implementation-update preview.

The engine needs Python 3.11 or later, Git, and Python's bundled SQLite. Core
workflows need no network connection, GitLab credentials, or third-party Python
packages. Repository code, build tools, tests, scripts, and jobs are never executed
by an analysis command.

## Requirements and layout

[TASK_STATEMENT.md](TASK_STATEMENT.md) defines the product contract and references
[the multi-repository architecture](MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md).
[Requirements assessment](REQUIREMENTS_AUDIT.md) records coverage, limitations,
and the rationale for the current simplification.
The root [architecture review](../ARCHITECTURE_REVIEW.md) records the independent
findings, implemented corrections, and remaining production-readiness boundaries.

```text
.github/skills/<operation>/SKILL.md   Four canonical Copilot entrypoints
skills/_engine/src/mr_impact/        One shared Python implementation
skills/_engine/scripts/             Launcher, example runner, benchmark
skills/_engine/tests/               Unit/integration tests and input fixtures
docs/                              Requirements and maintained operating guides
```

## Quick start

From this checkout:

```text
python skills/_engine/scripts/mr-impact.py --help
python skills/_engine/scripts/mr-impact.py analyze-issue --repo /work/risk --source /work/issue-input --output /work/issue-analysis
python skills/_engine/scripts/mr-impact.py index-repository --repo /work/risk --deep
python skills/_engine/scripts/mr-impact.py analyze-mr --repo /work/risk --base main --head HEAD --issue /work/issue-analysis/01-generated-issue.md --output /work/mr-analysis
python skills/_engine/scripts/mr-impact.py update-issue --issue /work/issue-analysis/01-generated-issue.md --analysis /work/mr-analysis --output /work/mr-analysis --target risk#1427
```

The Issue command above produces a draft. For completed Issue delivery, follow
the [inspection and review workflow](issue-workflow.md) and use `--require-review`.
The MR command also produces a deterministic draft. Follow the [MR review workflow](mr-workflow.md)
and rerun with a context-bound interpretation and `--require-review` for reviewed delivery.

Use Windows paths on Windows, and quote paths containing spaces. All relative
CLI paths are relative to the calling working directory. `--repo` defaults to the
current directory. Template lookup defaults to `<repo>/GITLAB_ISSUE_TEMPLATE.md`.
Use `--template` to select a different current template; no template is embedded
in the engine. For this checkout, the maintained template is now
`docs/GITLAB_ISSUE_TEMPLATE.md`; pass `--template docs/GITLAB_ISSUE_TEMPLATE.md`.
The external-project default remains unchanged.

Optional installation, when an approved local setuptools distribution is available:

```text
python -m pip install --no-build-isolation --no-deps -e skills/_engine
mr-impact --help
```

The source launcher is the offline route and requires no package installation.
When using skills from another workspace, install the package or keep this shared
checkout available and invoke its launcher by absolute path. Copying only the four
wrapper files does not install the engine.

## Copilot use

Canonical instructions live directly in `.github/skills/<name>/SKILL.md`; there
is no second set of entrypoints or discovery redirects. Their structure
follows [GitHub's Agent Skills documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills).
Open this project in a Copilot-enabled VS Code workspace and invoke a skill in
Agent Mode. The shared workflows separate deterministic extraction from the
agent's evidence-backed interpretation. VS Code interactive discovery itself is
an environment check; automated tests verify the four skill files and routing.

## Architecture

```text
four skill wrappers -> shared CLI -> typed records and operation services
                                      |
                            composable technology adapters
                                      |
                       per-repository SQLite index and graph
                                      |
                     compact organization boundary catalog
                                      |
                    bounded impact paths and QA runtime targets
```

Implemented adapters cover Python ASTs; C#/Scala/script lexical structure; Oracle
SQL/PLSQL; AutoSys JIL; a restricted Databricks YAML/JSON manifest subset; XML
package/project declarations; and generic paths, URLs, artifacts, and boundary
identifiers. C# extraction is explicitly structural: this environment has a .NET
host but no SDK, so Roslyn binding is unavailable. No fake semantic resolver is used.

## Documentation and examples

- [Complete workflow and CLI reference](workflow.md)
- [Issue interpretation and dynamic templates](issue-workflow.md)
- [MR analysis and QA interpretation](mr-workflow.md)
- [Index storage, freshness, and organization catalogs](index-storage.md)
- [Adapter extension guide](adapters.md)
- [Trust boundaries and resource limits](security.md)
- [Testing and reproducible demonstration](testing.md)
- [Known limitations](limitations.md)

Run `python -m unittest discover -s skills/_engine/tests -t skills/_engine -v` for automated validation. Run
`python skills/_engine/scripts/run-example.py --output docs/examples/output` to recreate the
three-repository demonstration and its human/machine-readable artifacts. Generated
output is ignored by Git; the maintained sources are the runner and test fixtures.
The Issue demonstration is a draft, not an agent-reviewed semantic result.
