# GitLab Issue and MR analysis with VS Code Copilot

This project provides four **GitHub Copilot Agent Skills** for local GitLab work. Open the repository in VS Code, select **Agent** in Copilot Chat, and ask the agent to use a skill. The agent reads project evidence, invokes the shared Python engine, reviews its draft, and returns local reports. The engine does not publish to GitLab or run the analyzed project's code, tests, or operational jobs.

| Skill | Use it for | Main result |
| --- | --- | --- |
| `/analyze-issue` | Turn project notes into an evidence-backed Issue draft using the current template | `00-issue-analysis.md`, `01-generated-issue.md` |
| `/index-repository` | Build or refresh a reusable dependency and runtime index | A local SQLite index and summary |
| `/analyze-mr` | Explain a Git change, affected processes/jobs, and QA scope | Four Markdown reports and five JSON artifacts |
| `/update-issue` | Prepare an implementation update after MR analysis | `05-issue-update.md` preview |

The four skill definitions are in [`.github/skills`](../.github/skills). They all use the Python engine under [`skills/_engine`](../skills/_engine). Python 3.11 or later and Git must be available to the VS Code agent terminal. The engine uses the Python standard library and SQLite; no GitLab token, network connection, or Python package installation is needed for the local workflow.

## Start in VS Code

1. Install VS Code with GitHub Copilot enabled and sign in. Make sure `python --version` reports 3.11 or later and `git --version` works in the VS Code terminal.
2. Open **the root of this repository** in VS Code. Keep the complete checkout: copying only the four `SKILL.md` files leaves out the engine. If your target project is elsewhere, add that repository to the same VS Code workspace or give Copilot its absolute path. Keep this suite checkout accessible to the agent.
3. Open Copilot Chat and select **Agent**. Type `/` to find the four skills, then select one and add your task details. VS Code also loads a relevant skill automatically when your request describes its job. See the [VS Code Agent Skills guide](https://code.visualstudio.com/docs/agent-customization/agent-skills) for discovery and invocation behavior.
4. Give the agent the target repository, the source folder or Git range, the output folder, and any current Issue/template/catalog paths. Use absolute paths for a different workspace; quote paths with spaces in any terminal command the agent prepares.
5. Let the agent run its local analysis steps and inspect the generated files. For Issue and MR work, ask for a **reviewed** result. The first engine pass is a deterministic draft; the agent must read the sources, record an evidence-bound interpretation, and rerun with `--require-review` before calling the result reviewed.
6. Check the reported uncertainty, missing inputs, and proposed QA work. A test plan lists work to perform; it is not a record that tests ran. Copy approved Issue text into GitLab through your normal process. `/update-issue` only writes a local preview.

Copilot may ask for normal VS Code terminal approval before invoking Python or Git. Analysis commands read Git snapshots and source files and write reports/indexes. Review the command and selected output paths in that prompt.

### A first, end-to-end prompt

Paste this into **Copilot Chat → Agent** after opening this checkout. Replace paths and branch names with your real ones:

```text
Use the skills in this workspace for a local GitLab workflow.
Target repository: C:\work\risk-engine
Requirements folder: C:\work\risk-engine\requirements\issue-1427
Current template: C:\work\risk-engine\GITLAB_ISSUE_TEMPLATE.md
Analysis output: C:\work\risk-engine\analysis\issue-1427
MR base: origin/main
MR head: HEAD
MR output: C:\work\risk-engine\analysis\mr-1427

First use /analyze-issue. Read the relevant sources and current template,
record inclusion and exclusion decisions, resolve what the evidence supports,
and deliver a reviewed analysis plus Issue draft. Then use /index-repository
on committed HEAD and /analyze-mr for the stated range. Explain behavior and
actual runtime jobs with dependency paths and confidence. Review every change,
mark unknowns explicitly, and deliver a concrete QA plan. Do not run jobs or
claim tests passed. Finally use /update-issue to prepare a local preview from
the generated Issue and MR analysis; preserve unresolved work and validation
status. Show me the resulting file paths and a short summary of gaps.
```

For this suite's own template, use [`docs/GITLAB_ISSUE_TEMPLATE.md`](GITLAB_ISSUE_TEMPLATE.md). For another repository, the default is `<target repository>/GITLAB_ISSUE_TEMPLATE.md`, or specify a different current template explicitly. The template controls Issue structure and writing instructions; it cannot authorize unrelated tool use.

## 1. Analyze an Issue

Use this when you have notes, requirements, earlier analysis, or a folder of project material and need a GitLab Issue description. Root discovery inspects text files directly in the target repository root. When you specify a source folder, the engine inspects its descendants. Numbered requirements files, prior analysis, and relevant README files are eligible; relevance is a documented agent decision. PDF, Word, or images need readable agent context or a traceable text export before their contents can be claimed as evidence.

**Prompt for a selected folder:**

```text
/analyze-issue
Repository: C:\work\risk-engine
Source folder: C:\work\risk-engine\requirements\issue-1427
Template: C:\work\risk-engine\GITLAB_ISSUE_TEMPLATE.md
Output folder: C:\work\risk-engine\analysis\issue-1427

Inspect all discovered sources, including numbered notes, earlier analysis,
and README files. State why each source is included or excluded. Read the
template as it exists now and follow every applicable writing instruction.
Separate requirements from assumptions and open questions. Cite source lines
for every substantive fill and for conflicts, risks, and readiness gaps.
Create the internal interpretation outside the two-file output folder and
rerun with --require-review. Return exactly the two public Markdown files.
```

**What the agent should do:**

1. Run `inspect-issue` to obtain current template slots/instruction IDs and normalized source fingerprints. Inspect relevant source files as data, including conflicts.
2. Build an internal JSON interpretation with a decision for every discovered text source, a review of every template instruction, evidence-linked slot fills, explicit optional empty slots, and cited semantic findings. Do not turn an example or assumption into an acceptance criterion.
3. Run `analyze-issue` with that interpretation and `--require-review`. Stale fingerprints, missing decisions, or unchecked template instructions must be resolved rather than bypassed.
4. Read `00-issue-analysis.md` and `01-generated-issue.md`. Confirm the Issue follows the current template and that missing evidence, contradictions, and readiness gaps remain visible.

The internal interpretation is an agent working artifact, not a third required deliverable. Its identifiers come from the **current** inspection result; illustrative slot IDs in examples are not safe to reuse after template edits. A reviewed status means the agent completed the source-bound process, not that a human approved the requirements.

For example, an agent interpretation for one source may have this shape. The digests, slot IDs, instruction IDs, and line numbers below are placeholders: take them from the current `inspect-issue` result and actual file contents.

```json
{
  "reviewed": true,
  "template_sha256": "<current template digest>",
  "source_sha256": {"notes.md": "<current normalized source digest>"},
  "source_decisions": {
    "notes.md": {"use": "included", "reason": "Contains the agreed input rule"}
  },
  "reviewed_instructions": ["I1"],
  "fills": {
    "L60": [{
      "text": "Reject negative exposure before persistence.",
      "kind": "requirement",
      "evidence": [{"file": "notes.md", "start_line": 16, "end_line": 16}]
    }]
  },
  "empty_slots": ["L124"],
  "findings": [{
    "kind": "ambiguity",
    "severity": "warning",
    "status": "unresolved",
    "text": "The handling of zero exposure needs confirmation.",
    "evidence": [{"file": "notes.md", "start_line": 17, "end_line": 17}]
  }]
}
```

Include every discovered source in `source_decisions`, including excluded files with a reason. Include every current instruction ID in `reviewed_instructions`. Findings may record conflicts, risks, readiness gaps, ambiguities, and classification decisions even when the template has no matching slot. Evidence must cite included, in-scope source lines.

**Example follow-up prompt when the report is incomplete:**

```text
Revisit /analyze-issue. The retention notes disagree. Cite both source lines
in a conflict finding, keep the acceptance criterion unresolved, and regenerate
the reviewed Issue and analysis report. Do not choose a duration by inference.
```

## 2. Index repositories

Index the changed repository before MR analysis when you want an inspectable reusable index. MR analysis also refreshes its required index automatically. **Deep** mode records local symbols and dependencies. **Boundary** mode records the smaller set of operational/data links useful for discovering other repositories. The default snapshot is committed `HEAD`; ask for a worktree snapshot only when staged, unstaged, and untracked files should be included in standalone indexing. MR analysis uses Git revisions, not uncommitted worktree edits.

**Prompt for one repository:**

```text
/index-repository
Deep-index committed HEAD of C:\work\risk-engine.
Report the index path, parsed/reused/skipped file counts, detected runtime
boundaries, and any warnings. Do not execute the indexed code.
```

**Prompt for cross-repository impact:**

```text
Use /index-repository to deep-index C:\work\risk-engine and boundary-index
C:\work\reporting-service and C:\work\regulatory-export at committed HEAD.
Build an organization catalog at C:\work\analysis\organization.sqlite from
those boundary indexes. Report each recorded commit, repository identity,
shared boundary, and any namespace mismatch or stale input.
```

The catalog is local. It selects candidate repositories through observed shared resources such as a database table, job, artifact, or API; MR analysis then deep-indexes candidates within configured limits. Use consistent `.repository-identity.json` resource namespaces across repositories referring to the same external system. Rebuild the catalog after changing identities or namespaces. See the [index and catalog reference](reference/index-storage.md) for storage, freshness, configuration, and resource limits.

## 3. Analyze a merge request

Provide a **known base and head** (for example `origin/main` and `HEAD`), a commit, or a verified unified patch. The skill must ask for a missing base when it cannot establish one locally; it must not silently assume `main`. A local `origin/main` ref must already exist. A supplied Issue is context for scope and terminology, not a correctness score for the developer.

**Prompt for one repository:**

```text
/analyze-mr
Repository: C:\work\risk-engine
Base: origin/main
Head: HEAD
Issue context: C:\work\risk-engine\analysis\issue-1427\01-generated-issue.md
Output: C:\work\risk-engine\analysis\mr-1427

Review the entire Git range. Map changed symbols on both sides, inspect
behavioral consequences in relevant code, and identify impacted entry points,
processes, jobs, and data flows. For every runtime target, include the path,
detector confidence, what QA should run or inspect, and expected observations.
Record a decision for every changed file and mark unsupported behavior as
unresolved. Produce a context-bound interpretation and rerun with
--require-review. Do not run operational jobs or describe proposed tests as passed.
```

**Prompt with an organization catalog:**

```text
/analyze-mr
Analyze C:\work\risk-engine from origin/main to HEAD using
C:\work\analysis\organization.sqlite. Use the Issue draft at
C:\work\risk-engine\analysis\issue-1427\01-generated-issue.md as context.
Expand only catalog-selected candidate repositories. Report downstream
reporting and export jobs with their repository, dependency path, confidence,
and any stale or unavailable catalog snapshot. Save reviewed results under
C:\work\risk-engine\analysis\mr-1427.
```

**What the agent should do:**

1. Run the deterministic MR pass. It resolves immutable Git revisions, extracts diff hunks, maps changed symbols, and traces bounded dependency paths. A first pass is a draft.
2. Inspect `mr-context.json`, the changed symbol map, relevant code, runtime paths, and warnings. Classify supported behavioral findings as `confirmed`, `likely`, or `hypothesis requiring verification`; tie each to a change/hunk. Separate actual execution targets from source files.
3. Copy the complete current `review_context` into an internal interpretation, set `reviewed: true`, and record `reviewed_changes` for **every** zero-based change index with `analyzed`, `unresolved`, or `not_applicable` plus a reason. Include findings and useful validation scenarios where evidence supports them.
4. Rerun with `--interpretation` and `--require-review`. If revisions, Issue, catalog, limits, or index generations changed, create a fresh interpretation. Read the resulting reports and verify the QA plan names real targets and leaves unexecuted scenarios unexecuted.

A reviewed MR interpretation has this shape. Copy the **whole current** `review_context` object from `mr-context.json` in place of the placeholder. The example indexes refer to the current deterministic changes and hunks, starting at zero.

```json
{
  "reviewed": true,
  "review_context": {"<copy the current mr-context.json review_context>": "exactly"},
  "reviewed_changes": {
    "0": {"status": "analyzed", "reason": "The changed guard precedes persistence."},
    "1": {"status": "unresolved", "reason": "The deployment behavior is undocumented."}
  },
  "findings": [{
    "change_index": 0,
    "hunk_index": 0,
    "classification": "confirmed",
    "summary": "The writer now rejects a negative amount before the INSERT.",
    "validation": "Run the daily risk task with -1, 0, and 1; verify the negative case is rejected before persistence."
  }]
}
```

Add one `reviewed_changes` entry for **every** actual change; the example's second entry applies only if there are two changes. An empty `findings` list is valid when the change decisions explain why no behavioral scenario is justified. Do not invent a digest or edit `review_context`: the engine checks its exact contents.

The output folder contains:

```text
01-mr-analysis.md       mr-context.json
02-change-context.md    changed-symbols.json
03-impact-analysis.md   impact-graph.json
04-test-plan.md         runtime-impact.json
                       test-impact.json
```

`analysis_status` distinguishes draft from reviewed output. `semantic_review_status` can still be `reviewed_with_gaps`, and `coverage_status` can be partial. A static dependency is evidence of a possible path, not proof that a runtime branch executed. Do not edit the generated reports or JSON by hand: `/update-issue` checks their integrity.

**Example QA follow-up prompt:**

```text
Open 04-test-plan.md and runtime-impact.json. For each affected AutoSys or
Databricks job, show the changed code to runtime path and the conditions QA
must verify. Separate confirmed effects from hypotheses. If a runner command
is not documented, name the job and request its documented execution procedure;
do not invent a shell command.
```

## 4. Prepare an Issue update

Use this after MR analysis, with the generated or otherwise analyzed Issue text and the intact MR output directory. Add a validation note only if it contains actual test or execution evidence. The skill creates `05-issue-update.md` as a **local preview**; it does not edit the original Issue or make a GitLab API call.

```text
/update-issue
Issue: C:\work\risk-engine\analysis\issue-1427\01-generated-issue.md
MR analysis: C:\work\risk-engine\analysis\mr-1427
Validation evidence: C:\work\risk-engine\qa-results.md
Target: risk-engine#1427
Output: C:\work\risk-engine\analysis\mr-1427

Prepare 05-issue-update.md. Preserve the original requirements and all
unresolved findings. Distinguish planned QA from evidence of completed tests,
include failures and follow-up actions, and carry forward the MR review and
coverage status. Show me the preview before any manual GitLab update.
```

If no validation evidence exists, omit that line and ask the agent to leave validation pending. The engine verifies the supporting MR artifacts before producing a preview; regenerate the MR analysis if files were modified or belong to an older artifact contract.

## Review checklist and common problems

- **Skill missing from `/` menu:** Open the suite root as a VS Code workspace folder, verify `.github/skills/<name>/SKILL.md` is present, choose Agent mode, and check the [VS Code skills configuration](https://code.visualstudio.com/docs/agent-customization/agent-skills). The Python tests cannot prove interactive discovery in your VS Code installation.
- **Engine unavailable in another workspace:** Keep this full checkout open or accessible and tell Copilot where its `skills/_engine/scripts/mr-impact.py` launcher lives. A copied skill wrapper alone cannot run the engine.
- **`analyze-issue` reports a draft or stale review:** Inspect again and refresh the interpretation's template/source digests, source decisions, instruction IDs, and evidence lines. Do not remove `--require-review` to label the result complete.
- **MR base missing or results omit uncommitted edits:** Supply an existing Git base ref and committed head. Use standalone index worktree mode only for indexing local edits; commit or create the intended Git revision for MR range analysis.
- **Cross-repository target absent:** Check boundary indexing, catalog membership, shared resource identifiers/namespaces, recorded commits, candidate limits, and warnings. An absent path is not proof of no impact.
- **A QA plan looks like test evidence:** Treat `04-test-plan.md` as recommendations. Supply a real validation report to `/update-issue` only after tests or jobs are run through your normal process.

See [supported limits](reference/limitations.md) and [trust boundaries](reference/security.md) when interpreting uncertain or sensitive results.

## Command line reference (secondary workflow)

The VS Code agent uses the same local launcher internally. These examples are for maintainers, automation, or a manual fallback. Run them from the suite root; paths for another project should be absolute. The installed `mr-impact` command is optional and equivalent to `python skills/_engine/scripts/mr-impact.py`.

```text
python skills/_engine/scripts/mr-impact.py --help
python skills/_engine/scripts/mr-impact.py inspect-issue --repo REPO --source SOURCE --template TEMPLATE --output ISSUE_OUTPUT
python skills/_engine/scripts/mr-impact.py analyze-issue --repo REPO --source SOURCE --template TEMPLATE --output ISSUE_OUTPUT --interpretation INTERNAL_JSON --require-review
python skills/_engine/scripts/mr-impact.py index-repository --repo REPO --deep
python skills/_engine/scripts/mr-impact.py index-repository --repo OTHER_REPO --boundary
python skills/_engine/scripts/mr-impact.py index-organization --catalog ORG.sqlite --index OTHER_INDEX_DIRECTORY
python skills/_engine/scripts/mr-impact.py analyze-mr --repo REPO --base BASE --head HEAD --issue ISSUE.md --catalog ORG.sqlite --output MR_OUTPUT
python skills/_engine/scripts/mr-impact.py analyze-mr --repo REPO --base BASE --head HEAD --issue ISSUE.md --catalog ORG.sqlite --output MR_OUTPUT --interpretation INTERNAL_JSON --require-review
python skills/_engine/scripts/mr-impact.py update-issue --issue ISSUE.md --analysis MR_OUTPUT --output MR_OUTPUT --validation RESULTS.md --target project#1427
```

`--source`, `--issue`, `--catalog`, and `--validation` are optional where shown; remove the associated flag when you have no such input. `--output` is required for Issue, MR, and update operations. An unreviewed `analyze-issue` or `analyze-mr` run is a draft. Optional variants include `index-repository --check`, `--worktree`, or `--ref REF`; `analyze-mr --commit COMMIT` or `--patch CHANGE.patch --base BASE --head HEAD`; `query-graph`; and `inspect-template`. Use `--help` on an operation for current flags. Invalid input returns exit code 2; an index freshness check returns 3 when stale.

The Issue interpretation structure and MR review-context rules are described above so an agent can build them from current inputs. For exact implementation details, inspect the [Issue skill](../.github/skills/analyze-issue/SKILL.md), [MR skill](../.github/skills/analyze-mr/SKILL.md), and engine schemas rather than reusing old digests or slot IDs. The local demonstration can be generated with `python skills/_engine/scripts/run-example.py --output docs/examples/output`; its Issue is a draft and its temporary commit IDs change between runs.

## Project references

The [`reference` directory](reference) holds the source requirements, architecture and audit records, technical reference, validation guide, and benchmark data. Some historical requirements describe proposed layouts; use this README and the current skill files for operating instructions. The working Issue template stays at [`docs/GITLAB_ISSUE_TEMPLATE.md`](GITLAB_ISSUE_TEMPLATE.md) because the engine and examples use that path. The essential references are:

- [Task statement](reference/TASK_STATEMENT.md) and [multi-repository architecture](reference/MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md)
- [Architecture review](reference/ARCHITECTURE_REVIEW.md) and [requirements assessment](reference/REQUIREMENTS_AUDIT.md)
- [Index storage and organization catalog](reference/index-storage.md) and [technology adapters](reference/adapters.md)
- [Validation and reproducible example](reference/testing.md), [security](reference/security.md), [limitations](reference/limitations.md), and [benchmark results](reference/benchmark-results.json)
