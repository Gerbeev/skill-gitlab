# MR interpretation and QA workflow

The shared `analyze-mr` operation resolves immutable Git revisions without
checkout, parses unified hunks deterministically, and maps both sides to their
indexed symbols. Before-change graphs preserve evidence for removed code.
Changed files include configuration, dependency/build/CI changes, tests, and
documentation. Structural fallback mappings are explicitly lower-confidence.

## Local and cross-repository impact

The engine traverses dependencies toward callers/consumers and operational
entry points. Data writes and produced entities are followed outward; reads,
execution references, and scheduler dependencies are followed in reverse.
Definitions and containment connect symbols to files, jobs, tasks, and boxes.
It never loads the full persisted graph into Python memory.

When a catalog is supplied, reached boundary entities select candidate
repositories. All shared boundary entities from the current bounded frontier are
used to seed each candidate, so separate flows in a candidate can be reached.
Only candidates are upgraded to deep indexes. Expansion uses the catalog's
recorded commit; a different current HEAD produces a stale-catalog warning and
reduced confidence. An unavailable repository or missing recorded commit is
reported without pretending expansion succeeded.

The path to a runtime target includes edge type, direction, source lines,
revision, detector, and confidence. A cross-repository bridge records the target
repository and catalog commit. The retained path is a deterministic discovered
path, not a proof of exclusive dependency or of complete runtime behavior.

## Agent behavioral interpretation

After the deterministic pass, inspect `mr-context.json`, symbol mappings,
relevant code, and the bounded graph. Use Issue statements as context only.
Explain observed control-flow, validation, error handling, retry/fallback,
persistence, API, configuration, compatibility, and privacy consequences where
the evidence supports them. Classify each finding as `confirmed`, `likely`, or
`hypothesis requiring verification`. Do not turn textual similarity into a
correctness verdict or claim that unexecuted tests pass.

The deterministic report contains lexical hypotheses and neutral Issue
associations. Add semantic findings through an internal interpretation file:

```json
{
  "head": "resolved head from mr-context.json",
  "diff_sha256": "digest from mr-context.json",
  "findings": [
    {
      "change_index": 0,
      "hunk_index": 0,
      "classification": "confirmed",
      "summary": "The writer now rejects a negative amount before constructing the INSERT statement.",
      "validation": "Run the daily risk task with -1, 0, and 1; verify rejection occurs before persistence only for -1."
    }
  ]
}
```

Indexes are zero-based into the deterministic changes/hunks. The engine verifies
revision and diff identity and that the referenced change and hunk exist. The
agent remains responsible for semantic support and useful validation scenarios.
Run the same `analyze-mr` operation with `--interpretation INTERNAL_JSON` to render
the findings through the shared engine. Do not directly edit the generated
summary or runtime JSON: the Issue-update operation verifies their integrity.

## QA output review

Prioritize actual execution targets over lists of source files. For each target,
provide its repository, type, impact classification, reason, path, confidence,
what to run or inspect, and what output/behavior to verify. Undefined targets are
`UNRESOLVED`; a weak link makes the path `POTENTIALLY_AFFECTED`. Even an exact
static reference does not prove runtime execution.

Check code-level tests, process/job execution, and integration/regression cases
separately. Derive negative/boundary scenarios from the actual changed behavior
and explicit acceptance criteria. Never invent a shell command: use a named
job/process and its documented runner when executable syntax is unavailable.
Recommendations do not authorize running an operational job during analysis.

Report stale, missing, dynamic, filtered, or truncated dependencies visibly.
Broader implementation, edits in non-goal areas, and independent change groups
are descriptive review/QA context. They are not automatically errors in the
developer's understanding or implementation.


## Verified patch and commit inputs

External text patches are checked before index/report generation. With `--base`,
the complete transformation of each included file must match both snapshots,
including old/new payload, context, positions, additions, removals, renames, and
end-of-file newline markers. A patch may cover a subset of files. Without `--base`,
head content and deletion absence are checked, while old-side claims remain explicitly
unverified. External binary patches require a Git range instead. Root commits use
an empty-tree comparison and are reported with `base_kind: empty_tree`; merge commits
use the first parent.

Changed-symbol mappings use actual added/removed line positions, not unchanged hunk
context. Python signatures include arguments, annotations, defaults, return annotations,
and async status. Graph traversal keeps nondominated confidence/depth paths, retaining
shorter alternatives when they are needed to respect the depth budget.

## Structured QA scenarios

An interpreted finding may add a `scenario` object with `target` (a discovered entity
ID), `repository`, `preconditions`, `inputs`, and `expected` strings. Unknown targets
are rejected. Its evidence references the finding's changed file/hunk and the runtime
dependency path. Scenarios appear in `test-impact.json` and the QA report with
`executed: false`; they never count as execution evidence. If parameters are missing,
the report asks for them rather than inventing executable commands or expected values.

`completion_checks` records evidence availability separately from correctness.
`follow_up` entries have IDs, status, revision evidence, and an action. Update Issue
preserves these entries and verifies hashes of all eight supporting MR artifacts.
Regenerate older MR output before updating an Issue with the strengthened artifact contract.

## Completed semantic review

The interpretation example above is a legacy draft. For completed delivery, copy
the entire `review_context` object from the current `mr-context.json`, add
`"reviewed": true`, and supply `reviewed_changes` with an entry for every zero-based
change index. Each entry needs `status` (`analyzed`, `unresolved`, or `not_applicable`)
and a nonempty `reason`. For example:

```json
{
  "0": {"status": "analyzed", "reason": "The changed guard precedes persistence; boundary cases are specified."},
  "1": {"status": "unresolved", "reason": "The deployment environment is not documented."}
}
```

Rerun with `--interpretation INTERNAL_JSON --require-review`. A missing review,
missing change decision, or stale context fails before report publication. The
review context binds the diff, revisions, Issue digest, catalog digest, limits,
configuration, schema/adapter versions, index generations, and discovered coverage.
Changing those inputs requires a new review. Copy the context without manually
editing its digests. An empty findings list is acceptable when reasoned change
decisions explain why no behavioral scenario is justified.

`analysis_status` is `draft` or `reviewed`. `semantic_review_status` is `pending`,
`reviewed`, or `reviewed_with_gaps`. `coverage_status` is `partial` when warnings
exist, otherwise `local_only` without a catalog or `bounded` with one. None asserts
exhaustive completeness or successful execution. These statuses appear in reports
and the Issue-update preview. Review remains an agent attestation, not proof that
semantic claims are true. Confidence numbers express detector strength rather
than calibrated probabilities of runtime impact.

## Repeated candidate expansion

Candidate indexing and incoming-seed processing are separate. Later frontiers and
base/head graphs may supply additional seeds to an already indexed repository.
Useful confidence/cross-depth alternatives are processed within `--max-expansions`
as well as the existing candidate, hop, node, and edge budgets. Local `file://`
identities never serve as organization matches. Operation locks protect candidate
stores while they are used; unavailable or busy candidates produce explicit warnings.
