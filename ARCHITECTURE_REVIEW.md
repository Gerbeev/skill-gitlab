# Architecture review and implementation record

Date: 2026-09-24. Original review baseline: `0b634da64d9078efbc39a2f8b40c461fb142b7ca`.

The architecture is appropriate for a local-first MVP: four thin skills share one deterministic Python engine, repository indexes, and a compact organization dependency catalog. The implementation should remain a modular monolith. A graph service, vector database, or separate implementation per skill would not address the defects identified in this review.

The original review found six actionable concerns. The changes described below address them without claiming compiler-level completeness, proven organization-scale performance, or independently verified model reasoning.

## Evidence and scope

The review inspected `docs/TASK_STATEMENT.md`, its referenced multi-repository architecture, all four skill wrappers, operating guides, the shared engine, fixtures, and tests. The original baseline passed 57 tests. Two additional isolated experiments reproduced defects that those tests did not cover:

- Independent repositories containing `run.py` matched globally through `file://run.py` at confidence 100.
- An export failure after a successful SQLite transaction left stale JSON files that the following index operation incorrectly accepted as current.

Other findings came from code inspection and were identified as limitations or risks rather than reproduced failures. The follow-up implementation adds dedicated regression coverage, including actual temporary Git repositories and cross-process lock contention. Test commands and acceptance scenarios are maintained in `docs/testing.md`.

## Sound architectural choices retained

| Choice | Implementation | Value |
|---|---|---|
| Four operation-specific wrappers | `.github/skills/*/SKILL.md` routes to a single CLI | Fixes benefit all workflows without duplicating business logic. |
| Local modular monolith | Python, Git, bundled SQLite | Suitable for restricted environments and offline operation. |
| Deterministic extraction and separate interpretation | Git/diff/index/graph services plus evidence-bound interpretation | Language models do not replace structural change extraction. |
| Technology-neutral graph | Shared records, composable adapters, generic fallback | Supports heterogeneous repositories without a global compiler graph. |
| Deep indexes and compact boundary catalog | Local detail, organization reverse lookup, lazy candidate expansion | Avoids deeply scanning every repository for each MR. |
| Incremental indexing | Blob identities and configuration/version fingerprints | Reuses unchanged parsing while detecting deletions and configuration changes. |
| Both sides of an MR | Head/base indexes and old dependency paths | Preserves evidence for removed code and dependencies. |
| Bounded directional traversal | SQL adjacency, confidence/depth labels, explicit budgets | Bounds work and explains discovered paths. |
| Runtime-oriented QA targets | Jobs, scripts, workflows, database flows | Addresses the central requirement beyond changed-file lists. |
| Template-driven Issue generation | Current template, source decisions, citations, review gate | Preserves the authoritative structure and distinguishes assumptions. |
| Local Issue preview | Artifact hashes and unchanged input requirements | Separates proposed validation from actual execution evidence. |
| Restricted execution boundary | Read-only Git allowlist and no analyzed-code execution | Repository content cannot authorize commands or remote writes. |

Separate tables in one SQLite database satisfy the requirement for logical separation of structural data and relationships. Helper CLI commands do not violate the four-skill product surface.

## A1: Repository-local and organization identities

Priority: P1. Original status: reproduced defect.

Previously, script/workflow nodes used `file://<relative-path>` as an organization boundary. The catalog equated a file's local existence with resource identity across projects. Common paths could create false candidates and consume the candidate budget before genuine dependencies were considered.

Implemented correction:

- Local file, symbol, external-symbol, and module keys stay local and are excluded from exported organization observations and lookup, including lookups against older catalogs.
- External resources such as tables and AutoSys jobs remain eligible for evidence-backed matching.
- Optional `.repository-identity.json` supplies a stable repository ID and resource namespaces. Physical cache paths retain a checkout-path hash so two checkouts with the same logical ID cannot overwrite each other's cache.
- Runtime target deduplication includes repository identity; a definition in another repository no longer suppresses a local unresolved target.

Acceptance coverage checks independent identical file paths, stable identity after checkout relocation, separate caches, external-resource matches, and namespace isolation.

Operators must configure consistent namespaces for the same external resource. Unqualified names remain an assumption about a shared domain; the engine cannot infer database instances, scheduler installations, or deployment environments from names alone. See `docs/index-storage.md`.

## A2: Recoverable publication of index exports

Priority: P1. Original status: reproduced defect.

Previously, SQLite state committed before exports were written, but the no-op check required only that the old export files existed. A failure between those steps could leave inconsistent representations indefinitely. The catalog read SQLite directly, so the reproduced defect demonstrated inconsistent published exports rather than corruption of the catalog database.

Implemented correction:

- State has a deterministic generation ID bound to repository, snapshot, mode, configuration, identity settings, and engine versions.
- The final manifest records that generation and SHA-256 digests of the exported artifacts.
- Freshness and no-op reuse validate generation and export integrity.
- Missing, interrupted, or corrupt exports are recreated from SQLite without reparsing unchanged files.
- The manifest is published last. Export cursors are closed even when publication fails.

Fault-injection regressions cover boundary, file, and graph exports plus both manifests and state publication. Individual file replacement remains atomic; readers requiring a coherent external export set must validate the manifest and respect the operation lock. This is recoverable publication, not a new immutable-snapshot storage system.

## A3: Re-entering candidate repositories through new boundaries

Priority: P1. Original status: code-confirmed limitation, already acknowledged by the previous limitations guide.

Previously, a repository-level `seen` set prevented expansion after the first visit. A path A to B through X could mask a later path A to C to B through Y, including a disconnected operational flow. Different base/head boundaries could have the same problem.

Implemented correction in `expansion.py`:

- Index each selected candidate once per analysis.
- Maintain a queue of graph frontiers and nondominated confidence/cross-depth labels for each candidate/entity pair.
- Revisit an already indexed candidate when it receives new seeds or a useful confidence/depth alternative.
- Retain candidate, hop, per-traversal, and total expansion budgets; report partial coverage when a limit is reached.
- Reuse open candidate stores protected for the analysis lifetime.

Regression coverage includes a converging graph, distinct old/new boundaries, single-build reuse, bounded cycles, and expansion-budget exhaustion.

This is still conservative reachability. The retained explanation is one discovered path per node within each traversal, not a proof that all runtime branches execute.

## A4: Semantic Issue findings in the analysis report

Priority: P2. Original status: code-confirmed contract limitation.

Previously, interpretation could populate template slots, but the analysis report primarily used lexical classification and a narrow negation-based contradiction detector. A conflict such as 30-day versus 90-day retention had no dedicated delivery channel when the template lacked a matching slot.

Implemented correction:

- Interpretation supports a bounded `findings` list with kind, severity, resolution status, text, citations, and an optional template-section reference.
- Kinds cover conflict, ambiguity, risk, readiness, and classification.
- Validation rejects out-of-scope, excluded, or invalid-range citations.
- The analysis report renders semantic findings independently of template slots and labels the remaining lexical checks as fallback observations.
- Template-population reporting includes interpreted content and evidence.

The two-public-file contract remains unchanged. Tests verify a conflict delivered without a template slot and rejection of invalid evidence. Range/hash checks establish provenance, not semantic truth; model-level evaluation remains necessary.

## A5: Explicit MR semantic-review and coverage status

Priority: P2. Original status: contract limitation partly mitigated by skill instructions.

Previously, the MR workflow requested agent review but the engine had no equivalent of the Issue review gate. Integrity-checked artifacts could still contain only deterministic hypotheses and generic target guidance.

Implemented correction:

- Deterministic and legacy interpretation runs explicitly remain `draft` with semantic review `pending`.
- Completed review requires `reviewed: true`, the exact generated `review_context`, and a reasoned decision for every changed file.
- `--require-review` rejects missing or incomplete review before report publication.
- Decisions may be analyzed, unresolved, or not applicable; honest gaps are not replaced with invented scenarios.
- Review context binds head/base, diff, Issue content, catalog content, configuration, limits, engine versions, index generations, and discovered coverage.
- Reports and Issue previews preserve analysis, semantic-review, and coverage status.

Coverage is reported as partial, local-only, or bounded rather than claiming exhaustive completeness. Review is an agent attestation, not a correctness verdict or test-execution result. Regression coverage exercises draft rejection, reviewed-with-gaps delivery, preview propagation, and stale context invalidation.

## A6: Isolation of mutable index slots

Priority: P2. Original status: architectural concurrency risk; no competing-writer experiment was run during the original review.

SQLite transactions protected individual updates but not the entire build-then-read analysis lifecycle. Different heads or DEEP/BOUNDARY requests could otherwise replace a shared current/base slot between operations.

Implemented correction:

- Reentrant per-repository operation locks span indexing and the complete MR analysis.
- Candidate locks are retained while their stores are used.
- OS locks also protect catalog aggregation versus catalog-backed analysis.
- Contention fails promptly with a retryable error rather than waiting into a lock-order deadlock.
- Standalone graph queries and catalog reads use SQLite read transactions.

A subprocess regression proves a competing index request cannot replace a protected snapshot and can succeed after release. This is the lightweight MVP isolation option recommended by the review. Immutable revision/config snapshots and a separate blob parse cache remain a potential future optimization for higher concurrency, not a prerequisite for this local version.

## Remaining architectural work

### Adapter quality and evidence

C#/Scala extraction remains lexical, Python runtime binding remains uncertain, and Databricks YAML support is intentionally restricted. Optional compiler-backed resolvers and richer YAML parsing should be added in response to measured missed dependencies. Confidence values are detector-strength categories, not calibrated probabilities of runtime impact.

File-level seeds and containment can include neighboring definitions. This trades precision for conservative coverage. Future evaluation should measure unnecessary QA targets as well as missed targets. Extraction revision and current snapshot revision remain distinct when unchanged blobs reuse earlier evidence.

### Scale and operational transport

The refreshed benchmark covers 1,000 synthetic files and one candidate after the corrections. This run measured approximately 2.12 seconds for initial deep indexing, 0.135 for no-op, 0.486 for one-file update, 1.47 for boundary indexing, and 2.64 for candidate expansion. These local measurements are not organization-scale performance promises. The memory metric excludes Git and native SQLite allocations. Raw results are in `docs/benchmark-results.json`.

Representative organization benchmarks, total process RSS, high-degree dependency cases, concurrent usage, catalog transport, remote clone scheduling, and service-level SLAs remain unverified. Hash-validating exports adds I/O proportional to export size on no-op checks and must be included in future measurements.

### Agent behavior

Engine tests do not establish Copilot discovery or model reasoning quality. Run the acceptance scenarios in `docs/testing.md` in the intended model environment, recording prompts, model/version, source revisions, outputs, missed runtime targets, irrelevant scope, and semantic mistakes. Do not infer production readiness from the number of passing tests.

## Suitability against the task statement

| Workflow | Assessment | Remaining boundary |
|---|---|---|
| Analyze Issue | Appropriate template/provenance/review architecture; semantic findings now have a delivery path | Agent interpretation quality and arbitrary prose still need evaluation. |
| Index Repository | Reusable local index with recoverable exports and operation isolation | Immutable concurrent snapshots and measured enterprise scale remain future work. |
| Analyze MR | Useful deterministic changes, bounded operational reachability, and explicit review status | Static reachability cannot prove runtime execution or exhaustive impact. |
| Update Issue | Appropriate local preview with preserved requirements and review status | No remote write adapter or authenticated execution evidence. |
| Organization discovery | Correct boundary-catalog direction with namespaces and repeated-seed expansion | Namespace governance, transport, and representative load testing are operational requirements. |

The implementation is a stronger basis for engineer-assisted local analysis after these corrections. It should help most where scheduler, script, and data dependencies are explicit. Dynamic configuration and incomplete runtime definitions still require investigation; absence of a discovered dependency is not proof of no impact.

The task statement's precise rules take precedence over ambiguous general wording: Issue analysis has two public outputs, Issue context does not authorize correctness scoring, and the compact reverse catalog does not imply a mandatory organization-wide method graph.

## Follow-up validation

- Final automated suite: **66 tests passed** in 58.735 seconds on Windows with Python 3.14.6.
- The three-repository example passed all eight checks, found 11 runtime targets and two candidate repositories, and reused six files with zero no-op parses. MR semantic review was `reviewed`; coverage remained explicitly `partial`. The Issue example remained a draft. No operational jobs were executed.
- Compilation, whitespace checks, and local Markdown links passed. All four skill frontmatters and their local references passed structural checks. The bundled skill validator could not run because PyYAML was unavailable, so equivalent checks for these simple frontmatters were performed directly without installing dependencies.
- The final source/documentation scan found no Cyrillic text. The architecture review and maintained documentation are in English.
- OS lock contention was exercised across Windows processes. The Unix lock branch and interactive Copilot behavior were not exercised in this environment.
