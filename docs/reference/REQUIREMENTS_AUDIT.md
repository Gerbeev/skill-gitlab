# Requirements assessment

Assessment updated 2026-09-24 against [TASK_STATEMENT.md](TASK_STATEMENT.md)
and its referenced [indexing architecture](MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md).
Implementation evidence comes from the engine, tests, and reproducible fixtures.
Historical implementation prompts and fix reports are not additional requirements.

## Result

Follow-up: `ARCHITECTURE_REVIEW.md` records six additional architectural
findings and their implementation. Local paths no longer match globally; identity
namespaces, recoverable generation manifests, operation locks, repeated-seed
expansion, semantic Issue findings, and explicit MR review/coverage states now
strengthen the earlier baseline. Historical test counts below describe that earlier
revision; current regression commands and scope are in `testing.md`.

The four local operations form a useful, coherent implementation of the core
workflow. They do not establish the entire production quality bar in section 14:
compiler semantics, representative organization-scale load, interactive Copilot
discovery, and agent-level semantic quality still need validation. No numerical
compliance score is justified by the synthetic tests.

## Requirement matrix

| Requirement | Current implementation and evidence | Boundary |
|---|---|---|
| Sections 1, 6, 7, 15: four thin skills, one engine | Four canonical `.github/skills` instructions call one shared Python package. Wrapper checks verify names, operation routing, and reference paths. | Interactive Copilot discovery has not been exercised in VS Code. |
| Section 2: exactly two Issue outputs | Analysis and generated Issue are the only two required files; manifests stay internal. | Existing unrelated files in an output directory are not deleted. |
| Section 2: selected source scope and relevance | Root or explicit-folder discovery, numbered/prior-analysis/README inputs, explicit inclusion/exclusion decisions, source fingerprints, and validated citations. | Images/PDF/Word require available agent context or text extraction. Deterministic extraction alone does not establish relevance. |
| Section 2: current template and instructions | Runtime slots preserve headings and independent token positions. Optional empty fields are supported. Completed output requires agent review of every instruction. | Arbitrary natural-language instructions are interpreted by the agent, not inferred by regex. Legacy/unreviewed CLI output is explicitly a draft. |
| Section 2: requirements versus assumptions and readiness | Ancestor-aware field protection, evidence classification, source-bound review, grouped summaries, and visible gaps. | A valid citation range does not prove that a paraphrase is semantically true. Agent review remains necessary. |
| Section 3: technology-neutral DEEP/BOUNDARY graph | Shared records, SQLite store, adapter protocol, generic fallback, standalone boundary definitions, and compact reverse catalog. | C#/Scala structure remains lexical rather than compiler-bound semantic analysis. |
| Section 3: incremental reuse and freshness | Content identities and config/schema/adapter versions; no-op avoids re-parsing and export rewrites; missing exports recover. Worktree exclusions precede reads. | A first build still enumerates the local repository. Large-scale organization behavior needs representative measurements. |
| Section 4, phases 1-2: deterministic changes and mapping | Validated text patches, exact changed-line positions, normalized Python signatures, initial commits, additions/deletions/renames. | External binary patches use Git ranges instead. Without a base, old patch claims are explicitly unverified. |
| Section 4, phases 3-5: neutral context and behavioral reasoning | Lexical candidates stay uncertain; agent findings bind to head/diff/hunks. No developer-understanding or implementation-correctness score is introduced. | Complex behavioral/non-goal interpretation requires the agent. |
| Section 4, phase 6: bounded local/cross-repository impact | Confidence/depth label search, cycle-safe dominance, edge filters and budgets, batched candidate lookups, lazy candidate-only expansion. | Candidate DEEP indexes are whole-repository indexes; targeted sub-repository extraction is not implemented. |
| Section 4, phase 7: runtime/process discovery | AutoSys, profile references, Databricks subset, scripts, SQL, simple cron/systemd, and explicit event-call candidates. Existing multi-repository fixtures reach downstream reporting/export jobs. | Deployment mappings, arbitrary frameworks, runtime injection, and complex scheduler syntax may remain unresolved. |
| Section 4: QA and report artifacts | Required JSON/Markdown files; targets contain repository, path, confidence, execution/verification guidance. Optional structured scenarios bind preconditions, inputs, expected outcomes, and discovered targets to evidence. | No tests or business jobs are executed by analysis. Missing QA parameters remain explicit questions. |
| Sections 4 and 14: separate readiness/completion context | Issue readiness gaps and MR completion evidence availability are separate. Unknown tests/approval remain unknown; follow-ups are structured. | No remote approval evidence is fetched automatically. |
| Section 5: controlled Issue updates | Local preview, unchanged requirements, supplied validation, structured follow-ups, and integrity checks for all eight supporting MR artifacts. | No remote write adapter. Agreed contract changes still need authoritative user input. |
| Sections 8-10: deterministic/AI split, evidence, trust | Read-only Git allowlist, bounded I/O, no analyzed-code execution, revision/path/confidence evidence, structured JSON redaction, agent review gates. | No claim of exhaustive security validation or automatic semantic truth verification. |

## Resolved interpretation ambiguities

- Section 2's precise two-file output contract takes precedence over treating
  `issue-intent.json` in section 12 as a third mandatory public artifact.
- A boundary reverse catalog is required; a monolithic organization call graph is
  explicitly not required for the first version.
- References to conformance do not override section 4's prohibition on correctness
  scoring against a possibly stale Issue.
- The internal folder layout is flexible. The mandatory architecture remains four
  user-facing operations backed by one physical implementation.

## Simplification and corrections

- Moved the canonical instructions to the existing Copilot discovery paths. This
  removes four redirect files and one unnecessary reference hop per invocation.
  The engine stays in `skills/_engine`; copy the whole suite when reusing it.
- Removed broad filename/English-keyword exclusions from Issue discovery. They
  silently discarded numbered requirements, prior analysis, and relevant README
  context. Source scope, output-directory exclusion, limits, and explicit relevance
  decisions remain in place. Source text never authorizes execution.
- Interpretation validation rejects non-boolean review flags and malformed citation
  containers. Slot lookup is indexed once instead of repeatedly scanning slots.
- Removed the unused `ReportInput` record. Kept shared adapters, bounded SQLite
  traversal, conservative confidence, and the dependency-free engine architecture.
- Removed the completed implementation prompt, overlapping fix/implementation/layout
  reports, closed bug cards, old probe JSON, and the duplicate audit runner. All
  eleven original defect scenarios remain covered in `test_regressions.py`.
- Removed checked-in generated examples and the superseded pre-fix benchmark.
  The example runner and fixtures reproduce outputs on demand in an ignored folder;
  its summary explicitly identifies the Issue result as an unreviewed draft.
  The current [benchmark](benchmark-results.json) remains a historical local baseline.

## Authoring rationale

[OpenAI guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
supports concise, discriminating descriptions, loading only relevant guidance, and
removing over-prescriptive or outdated instructions. Applied here by keeping four
operation-specific entrypoints and removing redirects and completed implementation
instructions rather than adding another orchestration layer.

[Anthropic guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
recommends shallow references and evaluation on representative tasks. The skills
link to the [current operating guide](../README.md). Engine regressions and the reproducible example
check deterministic behavior; [testing.md](testing.md) separately defines agent
acceptance scenarios. Those scenarios are not claimed as executed model evaluations.

## Verification and remaining priorities

Validation on 2026-09-24: 55 tests passed before the revision; all 57 passed after
the changes. Python compilation, the bundled skill validator for all four skills,
and maintained Markdown file links passed. The three-repository example passed all
eight workflow checks, found 11 runtime targets and two candidate repositories,
and reused all six current-repository files with zero no-op parses. Its Issue
status remained `draft`; no operational jobs ran. Unit tests cannot establish
semantic paraphrase quality. Reproduction commands are in [testing.md](testing.md).

Prioritize representative Issue/MR evaluations and real repository fixtures before
adding parsers or infrastructure. Add compiler-backed C#/Scala resolution or broader
YAML support only for demonstrated misses; retain uncertainty for unresolved edges.
Measure actual repository scale before claiming support for thousands of repositories.

The local 1,000-file benchmark measures Python allocations, not total process or
Git/SQLite native memory. Live GitLab writes and business-job execution are outside
the implemented preview/analysis scope. Original requirements and architecture
remain unchanged.
