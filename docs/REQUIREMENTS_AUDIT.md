# Requirements assessment

The sole requirements source is [TASK_STATEMENT.md](TASK_STATEMENT.md). The original
audit reviewed the working copy over `8b020a2372ff400d8fd69bfc7953530398fe00bb`, including
existing uncommitted changes. This document was updated after the requested fixes.
Architecture notes and previous implementation reports are not additional acceptance
criteria. Code, wrappers, fixtures, and executed tests provide implementation evidence.

## Result

The four-operation local workflow is implemented. All 11 reproducible defects from
the original audit are corrected and covered by probes and regression tests. This is
not a claim of exhaustive language semantics or production validation across thousands
of repositories. Those capability boundaries remain explicit below.

## Requirement matrix

| Requirement | Current implementation and evidence | Boundary |
|---|---|---|
| Sections 1, 6, 7, 15: four thin skills, one engine | Four canonical operation instructions and four discovery redirects call one shared Python package. Routing tests verify paths and names. | Interactive Copilot discovery has not been exercised in VS Code. |
| Section 2: exactly two Issue outputs | Analysis and generated Issue are the only two required files; manifests stay internal. | Existing unrelated files in an output directory are not deleted. |
| Section 2: selected source scope and relevance | Root or explicit-folder discovery, per-source inclusion/exclusion decisions, source fingerprints, and validated citations. | Images/PDF/Word require available agent context or text extraction. Deterministic extraction alone does not establish relevance. |
| Section 2: current template and instructions | Runtime slots preserve headings and independent token positions. Optional empty fields are supported. Completed output requires agent review of every instruction. | Arbitrary natural-language instructions are interpreted by the agent, not inferred by regex. Legacy/unreviewed CLI output is explicitly a draft. |
| Section 2: requirements versus assumptions and readiness | Ancestor-aware field protection, evidence classification, source-bound review, grouped summaries, and visible gaps. | A valid citation range does not prove that a paraphrase is semantically true. Agent review remains necessary. |
| Section 3: technology-neutral DEEP/BOUNDARY graph | Shared records, SQLite store, adapter protocol, generic fallback, standalone boundary definitions, and compact reverse catalog. | C#/Scala structure remains lexical rather than compiler-bound semantic analysis. |
| Section 3: incremental reuse and freshness | Content identities and config/schema/adapter versions; no-op avoids re-parsing and export rewrites; missing exports recover. Worktree exclusions precede reads. | A first build still enumerates the local repository. Large-scale organization behavior needs representative measurements. |
| Section 4, phases 1â€“2: deterministic changes and mapping | Validated text patches, exact changed-line positions, normalized Python signatures, initial commits, additions/deletions/renames. | External binary patches use Git ranges instead. Without a base, old patch claims are explicitly unverified. |
| Section 4, phases 3â€“5: neutral context and behavioral reasoning | Lexical candidates stay uncertain; agent findings bind to head/diff/hunks. No developer-understanding or implementation-correctness score is introduced. | Complex behavioral/non-goal interpretation requires the agent. |
| Section 4, phase 6: bounded local/cross-repository impact | Confidence/depth label search, cycle-safe dominance, edge filters and budgets, batched candidate lookups, lazy candidate-only expansion. | Candidate DEEP indexes are whole-repository indexes; targeted sub-repository extraction is not implemented. |
| Section 4, phase 7: runtime/process discovery | AutoSys, profile references, Databricks subset, scripts, SQL, simple cron/systemd, and explicit event-call candidates. Existing multi-repository fixtures reach downstream reporting/export jobs. | Deployment mappings, arbitrary frameworks, runtime injection, and complex scheduler syntax may remain unresolved. |
| Section 4: QA and report artifacts | Required JSON/Markdown files; targets contain repository, path, confidence, execution/verification guidance. Optional structured scenarios bind preconditions, inputs, expected outcomes, and discovered targets to evidence. | No tests or business jobs are executed by analysis. Missing QA parameters remain explicit questions. |
| Sections 4 and 14: separate readiness/completion context | Issue readiness gaps and MR completion evidence availability are separate. Unknown tests/approval remain unknown; follow-ups are structured. | No remote approval evidence is fetched automatically. |
| Section 5: controlled Issue updates | Local preview, unchanged requirements, supplied validation, structured follow-ups, and integrity checks for all eight supporting MR artifacts. | No remote write adapter. Agreed contract changes still need authoritative user input. |
| Sections 8â€“10: deterministic/AI split, evidence, trust | Read-only Git allowlist, bounded I/O, no analyzed-code execution, revision/path/confidence evidence, structured JSON redaction, agent review gates. | No claim of exhaustive security validation or automatic semantic truth verification. |

## Resolved interpretation ambiguities

- Section 2's precise two-file output contract takes precedence over treating
  `issue-intent.json` in section 12 as a third mandatory public artifact.
- A boundary reverse catalog is required; a monolithic organization call graph is
  explicitly not required for the first version.
- References to conformance do not override section 4's prohibition on correctness
  scoring against a possibly stale Issue.
- The internal folder layout is flexible. The mandatory architecture remains four
  user-facing operations backed by one physical implementation.

## Verification records

[Bug cards](bugs/README.md) preserve original failures and fixed behavior.
[audit-results-before.json](bugs/audit-results-before.json) records 11 reproduced bugs;
[audit-results.json](bugs/audit-results.json) records the current probe output.
The normal suite and dedicated regression tests cover the corrections. A complete
three-repository example is available under [examples/output](examples/output/README.md).

[Benchmark results](benchmark-results.json) measure initial DEEP, no-op, one-file
update, BOUNDARY, and one-candidate expansion on 1,000 synthetic files. Memory values
are tracemalloc Python allocations, not total process or Git/SQLite native memory.
Live Copilot discovery, real GitLab writes, business job execution, compiler semantic
binding, and organization-wide load tests remain outside this validation.

The source TASK_STATEMENT content remains unchanged. Documentation and comments are
maintained in English. User workspace/Obsidian settings and unrelated existing changes
are preserved.

Current verification: 55 tests passed, all 11 probes passed, and all eight canonical/discovery skill files passed the bundled validator. See [FIX_REPORT](FIX_REPORT.md).
