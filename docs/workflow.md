# Operating the four skills

All commands below use the same `mr-impact` entry point. In an uninstalled
checkout, substitute `python skills/_engine/scripts/mr-impact.py` for `mr-impact`.

## Analyze Issue

```text
mr-impact analyze-issue --repo REPO --output OUTPUT
mr-impact analyze-issue --repo REPO --source INPUT_FOLDER --template TEMPLATE --output OUTPUT --interpretation INTERNAL_JSON
```

Root discovery is shallow by default. An explicit source folder is recursive,
excluding dependency/generated trees and symlinks. `--source` does not change the
default template location. Read [Issue workflow](issue-workflow.md) before agent
interpretation. The two user-facing artifacts are `00-issue-analysis.md` and
`01-generated-issue.md`.

Example prompt:

```text
/analyze-issue
Use all relevant material under ./requirements/issue-1427.
Generate the analysis report and the Issue description using the current template.
Keep assumptions separate from requirements and identify missing evidence.
```

## Index Repository

```text
mr-impact index-repository --repo REPO --deep
mr-impact index-repository --repo REPO --boundary --cache CACHE
mr-impact index-repository --repo REPO --deep --worktree
mr-impact index-repository --repo REPO --deep --check
```

Committed `HEAD` is the default; `--ref REF` selects another commit without checking
it out. `--worktree` is an explicit snapshot of current tracked/untracked local
files. The repository must have at least one commit.

Indexing options: `--include GLOB`, `--exclude GLOB` (repeatable), `--adapter NAME`
(repeatable; generic extraction always remains enabled), `--workers 1..16`,
`--max-file-bytes`, and `--max-files`. Include/exclude patterns are case-sensitive
on systems where Python fnmatch is case-sensitive; use repository path spelling.
No-op indexing reuses parsed files and large JSON exports.

Example prompt:

```text
/index-repository
Refresh the deep index of committed HEAD. Report cache reuse and unresolved detectors.
```

## Analyze MR

```text
mr-impact analyze-mr --repo REPO --base BASE --head HEAD --output OUTPUT
mr-impact analyze-mr --repo REPO --commit COMMIT --output OUTPUT
mr-impact analyze-mr --repo REPO --patch CHANGE.patch --base BASE --head HEAD --output OUTPUT
mr-impact analyze-mr --repo REPO --base BASE --catalog CATALOG.sqlite --issue ISSUE.md --output OUTPUT
```

`--commit` compares a non-root commit with its first parent. `--patch` accepts a
unified `.diff` or `.patch` and requires the selected head to contain its resulting
files. Add `--base` for removed symbols and before-change dependencies. A mismatch
between a patch and its indexed head is an error. No patch is applied.

`--catalog` enables bounded cross-repository discovery; `--no-expand` reports
candidates without deep indexing them. Graph options are `--max-depth`,
`--max-nodes`, `--max-edges`, `--confidence 0..100`, and repeatable `--edge-type`.
`--max-candidates` and `--cross-depth` bound organization expansion.

Optional `--interpretation JSON` adds cited agent behavioral findings after the
deterministic pass. Read [MR workflow](mr-workflow.md).

The output contains four Markdown reports and five machine-readable artifacts:

```text
01-mr-analysis.md       mr-context.json
02-change-context.md    changed-symbols.json
03-impact-analysis.md   impact-graph.json
04-test-plan.md         runtime-impact.json
                       test-impact.json
```

Example prompt:

```text
/analyze-mr
Analyze main..HEAD using the organization catalog.
Identify affected runtime jobs and data flows and give QA concrete execution targets.
Use the Issue as context without grading the implementation against it.
```

## Issue update

```text
mr-impact update-issue --issue ISSUE.md --analysis MR_OUTPUT --output OUTPUT --target project#1427
mr-impact update-issue --issue ISSUE.md --analysis MR_OUTPUT --output OUTPUT --validation RESULTS.md
```

The required Issue input should be the analyzed description, with the original
Issue optionally retained by the caller. `--validation` adds actual supplied
execution evidence, never an inferred test pass. The operation validates report
integrity and writes `05-issue-update.md`. It does not modify the input Issue and
has no remote write adapter. Contract changes require an authoritative agreement;
this implementation only proposes factual implementation notes and follow-up.

Example prompt:

```text
/update-issue
Prepare a local update preview from the completed analysis and qa-results.md.
Record observed changes, validation evidence, uncertainty, and follow-up work.
```

## Maintenance commands

```text
mr-impact index-organization --catalog ORG.sqlite --index INDEX_A --index INDEX_B
mr-impact query-graph --index INDEX_DIRECTORY --seed file://scripts/run.py --max-depth 5
mr-impact inspect-template --template docs/GITLAB_ISSUE_TEMPLATE.md
```

Catalog updates replace each listed repository's observations; unrelated entries
remain. `--replace` deliberately replaces the complete catalog membership.
These helpers do not add user-facing skills.

Successful commands return 0. Invalid input or a system failure returns 2.
`index-repository --check` returns 3 when stale. JSON summaries go to stdout;
sanitized errors go to stderr. Command construction uses argument arrays.
