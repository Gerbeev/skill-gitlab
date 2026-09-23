# Copilot Skill: Issue → MR Traceability & Impact Analysis

## 1. Goal

Build a production-oriented Copilot Skill that analyzes the relationship between an Issue and a Merge Request:

**Issue intent → developer interpretation → actual implementation → dependency / impact scope → test scope → review / Issue artifacts.**

The Skill must be **local-first** and must not depend on GitLab API availability. GitLab integration is added as a separate adapter after the local pipeline is stable.

---

## 2. Core Principles

1. **Deterministic analysis first, LLM reasoning second.**
   - Git diff parsing, symbol extraction, dependency edges, and test discovery are not delegated to an LLM when they can be determined statically.
   - LLM reasoning is used for semantic interpretation, ambiguity detection, behavioral analysis, conformance reasoning, and report generation.

2. **The Issue is the source of intended behavior.**
   - A Merge Request is analyzed relative to Issue intent rather than in isolation.
   - Explicit requirements are separated from assumptions and inferences.

3. **Evidence for every material conclusion.**
   - Findings should preserve file, symbol, line/range, detector, dependency path, and confidence where applicable.
   - Unsupported conclusions are not allowed.

4. **Local-first execution.**
   - Primary input: local repository + Git refs / patch / diff.
   - GitLab API is an optional adapter.

5. **Incremental repository analysis.**
   - Do not rebuild the entire repository index for every Merge Request unless necessary.

6. **Language adapters.**
   - The core pipeline remains language-agnostic.
   - Language-specific parsers are isolated behind adapters.

7. **Fail closed on uncertainty.**
   - An inference must not become a requirement violation.
   - An uncertain dependency must not be presented as confirmed.

---

## 3. Approval Workflow

Each implementation item below is an independent approval unit.

Statuses:

- `PENDING`
- `APPROVED`
- `REJECTED`
- `IMPLEMENTED`
- `REWORK`

Workflow:

1. Present exactly one next `PENDING` item.
2. The user approves or rejects it.
3. Implementation starts only after approval.
4. After implementation, update project artifacts, approval state, and the ZIP.
5. Present the next pending item.
6. A rejected item is not implemented until it is revised and approved.

---

## 4. Target Repository Layout

```text
copilot-mr-impact-skill/
├── TASK_STATEMENT.md
├── PLAN.md
├── APPROVALS.md
├── README.md
├── pyproject.toml
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── golden/
└── .github/
    └── skills/
        └── mr-impact-analysis/
            ├── SKILL.md
            ├── scripts/
            │   ├── analyze.py
            │   ├── collect_issue.py
            │   ├── collect_mr.py
            │   ├── index_repo.py
            │   ├── extract_symbols.py
            │   ├── build_graph.py
            │   ├── analyze_conformance.py
            │   ├── analyze_impact.py
            │   ├── discover_tests.py
            │   ├── generate_reports.py
            │   └── gitlab_sync.py
            ├── core/
            │   ├── models.py
            │   ├── config.py
            │   ├── evidence.py
            │   ├── graph.py
            │   ├── storage.py
            │   ├── pipeline.py
            │   └── errors.py
            ├── adapters/
            │   ├── change_source.py
            │   ├── local_git.py
            │   ├── patch_file.py
            │   ├── gitlab.py
            │   ├── languages/
            │   │   ├── base.py
            │   │   ├── python.py
            │   │   ├── java.py
            │   │   └── generic.py
            │   └── llm/
            │       └── copilot.py
            ├── schemas/
            │   ├── issue-intent.schema.json
            │   ├── mr-context.schema.json
            │   ├── repository-index.schema.json
            │   ├── conformance.schema.json
            │   ├── impact.schema.json
            │   └── test-impact.schema.json
            ├── prompts/
            │   ├── issue-intent.md
            │   ├── developer-intent.md
            │   ├── conformance.md
            │   ├── behavioral-impact.md
            │   ├── test-plan.md
            │   └── issue-update.md
            └── templates/
                ├── 00-issue-analysis.md
                ├── 01-mr-analysis.md
                ├── 02-requirement-conformance.md
                ├── 03-impact-analysis.md
                ├── 04-test-plan.md
                └── 05-issue-update.md
```

The layout may evolve, but the separation between **core / adapters / scripts / prompts / schemas / templates** should remain.

---

# 5. Detailed Implementation Plan

## P01 — Freeze MVP Scope and Contracts
**Status:** PENDING

### Goal
Define exactly what belongs in the first working version and prevent the MVP from expanding into a cross-repository platform.

### MVP Inputs
- Local Git repository.
- Issue text from a local file or CLI input.
- Merge Request represented as:
  - `base_ref..head_ref`; or
  - `.diff` / `.patch`.
- Optional Merge Request description.
- Optional commit messages.

### MVP Outputs
- `issue-intent.json`
- `mr-context.json`
- `changed-symbols.json`
- `conformance.json`
- `impact-graph.json`
- `test-impact.json`
- `00-issue-analysis.md`
- `01-mr-analysis.md`
- `02-requirement-conformance.md`
- `03-impact-analysis.md`
- `04-test-plan.md`
- `05-issue-update.md`

### Explicitly Outside MVP
- Cross-repository dependency graph.
- Automatic GitLab Issue mutation.
- Automatic Merge Request approval/rejection.
- Full dynamic/runtime tracing.
- Vector database / semantic code index.
- Multi-agent orchestration.

### Acceptance
One CLI run can process a local repository + Issue + Merge Request refs and produce the complete machine-readable and Markdown artifact set.

---

## P02 — Define Domain Model and Evidence Model
**Status:** PENDING

### Goal
Define stable typed contracts between every pipeline stage before implementation expands.

### Core Models
- `IssueSource`
- `IssueStatement`
- `IssueIntent`
- `Requirement`
- `AcceptanceCriterion`
- `Constraint`
- `Assumption`
- `Ambiguity`
- `ChangeSet`
- `ChangedFile`
- `ChangedHunk`
- `Symbol`
- `ChangedSymbol`
- `DependencyEdge`
- `Evidence`
- `DeveloperIntent`
- `ConformanceFinding`
- `ImpactFinding`
- `TestCandidate`
- `AnalysisRun`

### Statement Classification
Every extracted Issue statement is classified as one of:

- `EXPLICIT_REQUIREMENT`
- `ACCEPTANCE_CRITERION`
- `CONSTRAINT`
- `CONTEXT`
- `ASSUMPTION`
- `INFERENCE`
- `AMBIGUITY`
- `OUT_OF_SCOPE`

### Evidence Contract
Every material finding must support provenance:

```json
{
  "file": "src/example.py",
  "symbol": "ExampleService.run",
  "start_line": 10,
  "end_line": 24,
  "detector": "python_ast",
  "confidence": 1.0
}
```

### Acceptance
No downstream stage depends on unstructured free text from the previous stage when a typed structured representation is available.

---

## P03 — Create Project Skeleton and Packaging
**Status:** PENDING

### Goal
Create the minimal working Python package and Copilot Skill directory.

### Deliverables
- `pyproject.toml`
- package metadata
- CLI entry point
- `.github/skills/mr-impact-analysis/SKILL.md`
- base directories
- test layout
- linting / typing / test configuration

### Constraints
- Pin the Python version.
- Keep dependencies controlled and minimal.
- Core must not depend on a GitLab SDK.

### Acceptance
- package installs locally;
- CLI starts;
- unit-test command works;
- Skill directory can be invoked independently.

---

## P04 — Configuration and Run Workspace
**Status:** PENDING

### Goal
Define one configuration contract and a reproducible directory structure for each analysis run.

### Proposed Run Directory

```text
.mr-analysis/
└── runs/
    └── <run-id>/
        ├── input/
        ├── intermediate/
        ├── reports/
        ├── logs/
        └── manifest.json
```

### Configuration
- repository path
- base/head refs
- patch path
- Issue path
- Merge Request metadata
- graph depth
- maximum nodes/edges
- language adapters
- output directory
- confidence thresholds

### Security
- path traversal protection;
- no secrets persisted in run artifacts;
- token redaction in logs.

### Acceptance
A complete run can be reproduced from its manifest and configuration.

---

## P05 — Issue Ingestion
**Status:** PENDING

### Goal
Load Issue content without requiring GitLab.

### MVP Sources
- Markdown/text file.
- CLI argument or stdin.

### Later Source
- GitLab Issue API.

### Normalization
- title
- body
- acceptance criteria
- checklists
- links/references
- labels/metadata when available

### Acceptance
Every supported source is normalized into the same deterministic input model without using an LLM.

---

## P06 — Issue Intent Analysis
**Status:** PENDING

### Goal
Convert prose Issue content into a structured intent contract.

### Extract
- objective
- explicit requirements
- acceptance criteria
- constraints
- behavior that must not change
- assumptions
- inferred expectations
- ambiguities
- possible affected areas
- explicit out-of-scope statements

### Critical Rule
An LLM-derived inference cannot automatically become an explicit requirement.

### Outputs
- `issue-intent.json`
- `00-issue-analysis.md`

### Acceptance
Every statement contains:
- classification;
- source/reference;
- confidence;
- explicit-vs-inferred status.

---

## P07 — Merge Request / Change Ingestion
**Status:** PENDING

### Goal
Produce a deterministic `ChangeSet`.

### Sources
- local refs: `base..head`
- patch/diff file

### Extract
- changed files
- added/deleted/modified/renamed status
- hunks
- old/new line ranges
- commit list when refs are available
- Merge Request description when provided

### Rules
- no LLM diff parsing;
- binary, generated, and vendor files are classified separately.

### Acceptance
The same diff always produces the same normalized `ChangeSet`.

---

## P08 — Repository Index v1
**Status:** PENDING

### Goal
Build a local structural repository index.

### Indexed Entities
- files
- language
- modules/packages
- symbols
- imports
- basic references
- tests
- configuration files
- build/CI files

### Storage
Primary candidate: SQLite.

### Incremental Strategy
Use file hashes / content hashes and re-index only changed units.

### Not Included Yet
- embeddings
- semantic vector retrieval
- organization-wide graph

### Acceptance
Re-indexing an unchanged repository does not require reparsing all files.

---

## P09 — Language Adapter Framework
**Status:** PENDING

### Goal
Separate the generic pipeline from language-specific parsing.

### Adapter Interface
At minimum:
- detect files
- extract symbols
- extract imports
- extract references/calls where reliable
- identify tests
- map changed lines to symbols

### Initial Adapter Order
1. `generic`
2. the primary language of the target production repository
3. additional languages

### Decision Gate
Select the first production language before implementing its parser adapter.

### Acceptance
The core pipeline contains no language-specific AST logic.

---

## P10 — Changed-Symbol Mapping
**Status:** PENDING

### Goal
Convert the raw diff into an exact list of affected symbols.

### Logic
- changed lines → containing symbol
- added symbol
- removed symbol
- signature change
- body-only change
- configuration-only change
- module/global change

### Output
`changed-symbols.json`

### Acceptance
Every changed symbol is linked to concrete changed hunks and evidence.

---

## P11 — Dependency Graph v1
**Status:** PENDING

### Goal
Build a structural dependency graph around repository code.

### Initial Edge Types
- `IMPORTS`
- `CALLS`
- `REFERENCES`
- `INHERITS`
- `IMPLEMENTS`
- `TESTED_BY`
- `CONFIGURES`

### Optional Later Edge Types
- `READS_TABLE`
- `WRITES_TABLE`
- `PUBLISHES_EVENT`
- `CONSUMES_EVENT`
- `CALLS_ENDPOINT`

### Edge Metadata
- detector
- confidence
- evidence
- static/deduced
- source and target symbols/files

### Acceptance
The graph API can retrieve a bounded N-hop neighborhood from changed symbols.

---

## P12 — Bounded Impact Traversal
**Status:** PENDING

### Goal
Determine likely blast radius without unbounded graph traversal.

### Controls
- maximum depth
- maximum nodes
- maximum edges
- edge-type allowlist
- confidence threshold
- cycle detection

### Categories
- directly affected
- transitively affected
- potentially affected
- unresolved

### Acceptance
Every traversal is deterministic and protected by explicit resource budgets.

---

## P13 — Developer Interpretation Reconstruction
**Status:** PENDING

### Goal
Separately infer how the developer appears to have interpreted the Issue.

### Inputs
- Merge Request description
- commit messages
- changed symbols
- diff summary
- optional supplied comments

### Output
`DeveloperIntent`

### Important
This is interpretation rather than fact. All conclusions must preserve confidence and provenance.

### Acceptance
Developer intent is never mixed with factual implementation data.

---

## P14 — Issue ↔ Developer Intent Conformance
**Status:** PENDING

### Goal
Detect semantic mismatch between the requirement and the developer's apparent interpretation.

### Findings
- covered
- partially covered
- missing
- potential misunderstanding
- extra scope
- unresolved ambiguity

### Guardrail
An Issue statement classified as `INFERENCE` cannot produce a hard violation.

### Acceptance
Each finding links to Issue statements and relevant Merge Request evidence.

---

## P15 — Issue ↔ Implementation Conformance
**Status:** PENDING

### Goal
Check whether the actual code matches the expected behavior contract.

### Example Finding Types
- requirement implemented
- requirement absent
- implementation broader than requirement
- behavior conflicts with constraint
- must-not-change path modified
- ambiguous implementation

### Output
`conformance.json`

### Acceptance
Every hard mismatch requires both an explicit requirement/constraint and code evidence.

---

## P16 — Behavioral Change Analysis
**Status:** PENDING

### Goal
Separate syntactic code changes from behavioral consequences.

### Analyze
- control-flow changes
- error-handling changes
- validation changes
- state mutation
- retry/fallback behavior
- configuration changes
- API/schema contract changes where detectable

### AI Role
The LLM receives a bounded evidence package rather than the whole repository by default.

### Acceptance
The report distinguishes:
- confirmed behavioral change;
- likely behavioral change;
- hypothesis requiring verification.

---

## P17 — Test Discovery
**Status:** PENDING

### Goal
Find existing tests related to changed and affected code.

### Sources
- naming conventions
- dependency graph
- imports/references
- test metadata
- nearby test files
- build tooling

### Output
`test-impact.json`

### Categories
- direct tests
- indirect/regression tests
- integration tests
- missing coverage candidates

### Acceptance
Every discovered existing test has a concrete rationale or evidence path.

---

## P18 — Test Plan Generation
**Status:** PENDING

### Goal
Generate targeted test scenarios from Issue intent, conformance findings, and impact analysis.

### Include
- happy path
- Issue-specific regression
- negative/error paths
- must-not-change paths
- impacted callers
- configuration/runtime dependencies
- missing coverage

### Avoid
- invented executable commands unless confirmed by the build system;
- generic scenarios unrelated to evidence.

### Output
`04-test-plan.md`

### Acceptance
Every proposed scenario maps to at least one requirement, finding, or impact edge.

---

## P19 — Report Generation
**Status:** PENDING

### Goal
Generate stable Markdown artifacts for developers and reviewers.

### Reports
1. `00-issue-analysis.md`
2. `01-mr-analysis.md`
3. `02-requirement-conformance.md`
4. `03-impact-analysis.md`
5. `04-test-plan.md`
6. `05-issue-update.md`

### Formatting
- concise executive summary;
- inline evidence;
- clear separation of facts, inference, and ambiguity;
- no unsupported verdicts.

### Acceptance
Reports are understandable without opening JSON, while every material conclusion remains traceable to structured artifacts.

---

## P20 — Single Orchestration CLI
**Status:** PENDING

### Goal
Provide one primary entry point instead of requiring manual invocation of internal scripts.

### Proposed Commands

```bash
mr-impact index ...
mr-impact issue ...
mr-impact mr ...
mr-impact analyze ...
mr-impact report ...
mr-impact full ...
```

### Full Pipeline

```text
collect issue
→ analyze issue
→ collect MR
→ index/update repository
→ map changed symbols
→ expand dependency graph
→ reconstruct developer intent
→ conformance analysis
→ impact analysis
→ test discovery
→ report generation
```

### Acceptance
`full` executes the complete MVP pipeline in one command and returns a non-zero exit code on a system failure.

---

## P21 — SKILL.md Orchestration Contract
**Status:** PENDING

### Goal
Define exactly how Copilot invokes the engine and interprets its artifacts.

### SKILL.md Must Define
- triggers
- allowed inputs
- exact execution sequence
- when to index
- when to rerun
- evidence rules
- confidence rules
- prohibited hallucination behavior
- artifact locations
- failure behavior
- presentation rules

### Key Principle
Copilot invokes the deterministic engine rather than replacing it with arbitrary reasoning.

### Acceptance
The Skill instructions minimize execution-path variation for identical inputs.

---

## P22 — Test Suite and Fixtures
**Status:** PENDING

### Goal
Make the pipeline reproducible and testable before using real corporate repositories.

### Minimum Fixtures
- correct implementation
- missing requirement
- over-broad exception handling
- unrelated extra scope
- renamed file/symbol
- deleted symbol
- config-only Merge Request
- indirect dependency
- missing test coverage
- cyclic dependencies
- ambiguous Issue
- Issue containing inferred but non-explicit requirements

### Tests
- unit
- integration
- golden-output
- deterministic rerun

### Acceptance
Critical conformance cases are covered by reproducible fixtures.

---

## P23 — Security, Privacy, and Prompt-Injection Hardening
**Status:** PENDING

### Goal
Prevent repository content, Issue text, and Merge Request descriptions from acting as agent instructions.

### Controls
- treat repository / Issue / Merge Request content as untrusted data;
- delimit external content;
- never execute commands merely because they appear in repository text;
- explicit subprocess allowlist;
- sanitize paths;
- cap file sizes;
- cap graph traversal;
- cap LLM context;
- avoid secrets in reports/logs;
- detect likely generated/vendor content.

### Important
Indirect prompt injection through Issue text, code comments, documentation, and Merge Request descriptions is a primary agentic attack surface.

### Acceptance
Untrusted repository text cannot alter the Skill execution policy.

---

## P24 — Observability and Reproducibility
**Status:** PENDING

### Goal
Make it possible to explain why a specific run produced a specific result.

### Manifest / Log Fields
- run_id
- repository commit
- base/head
- config hash
- tool version
- parser versions
- analyzed files
- skipped files
- timings
- warnings/errors
- LLM model metadata where available
- token/cost metadata where available

### Acceptance
Every report can be linked to an exact analysis run manifest.

---

## P25 — GitLab Read Adapter
**Status:** PENDING

### Goal
After the local pipeline is stable, add optional GitLab inputs.

### Read Operations
- Issue
- Merge Request metadata
- diffs
- commits
- optional discussions

### Architecture
The GitLab adapter converts remote data into the same `IssueSource` / `ChangeSet` models used by local adapters.

### Security
- token from environment or secret store;
- read-only token preferred;
- no token in logs;
- retry/backoff/timeouts.

### Acceptance
For the same Merge Request, local and GitLab-backed ingestion produce equivalent normalized input.

---

## P26 — GitLab Issue Update Preview
**Status:** PENDING

### Goal
Before any remote write, generate an exact preview of the intended Issue update.

### Output
- target project/Issue
- generated Markdown
- intended operation
- diff against the existing generated section when possible

### Acceptance
No remote mutation occurs during this stage.

---

## P27 — Optional GitLab Write Adapter
**Status:** PENDING

### Goal
Add controlled create/update operations after a separate approval.

### Controls
- explicit CLI flag;
- explicit target Issue;
- idempotency marker;
- dry-run by default;
- audit log;
- no automatic destructive rewrite.

### Acceptance
Repeated runs do not duplicate the automatically generated section.

---

## P28 — Performance and Large-Repository Hardening
**Status:** PENDING

### Goal
Validate the approach against large repositories and monorepos.

### Optimize
- incremental parsing
- SQLite indexes
- bounded graph traversal
- ignore patterns
- generated/vendor exclusions
- parallel parsing where safe
- cache invalidation

### Benchmarks
Track:
- initial indexing time
- incremental update time
- Merge Request analysis time
- peak memory
- graph size
- LLM context size

### Acceptance
Performance regressions are measured rather than guessed.

---

## P29 — Cross-Repository Design Spike
**Status:** PENDING

### Goal
Only after the single-repository MVP is production-ready, define the organization-wide graph extension.

### Research Questions
- repository identity
- shared artifacts
- jobs/schedulers
- events/topics
- APIs
- database dependencies
- packages
- deployment manifests
- ownership
- versioned edges
- stale-index detection

### Important
Do not build the global platform automatically during this step.

### Acceptance
Produce a separate architecture decision record covering cost/benefit and the migration path from the current index.

---

## P30 — v1 Release Gate
**Status:** PENDING

### Goal
Perform final review of the first Skill version.

### Required Checks
- deterministic pipeline passes;
- fixtures pass;
- no hard finding without evidence;
- ambiguity is preserved;
- prompt-injection controls are active;
- execution budgets are enforced;
- local mode requires no GitLab access;
- reports are stable;
- documentation is complete.

### Deliverable
A versioned ZIP containing the full Skill, tests, documentation, and sample output.

---

# 6. Implementation Order

```text
P01 Scope
 ↓
P02 Domain / Evidence model
 ↓
P03 Skeleton
 ↓
P04 Run / config
 ↓
P05 Issue ingestion
 ↓
P06 Issue intent
 ↓
P07 MR ingestion
 ↓
P08 Repository index
 ↓
P09 Language adapters
 ↓
P10 Changed symbols
 ↓
P11 Dependency graph
 ↓
P12 Impact traversal
 ↓
P13 Developer interpretation
 ↓
P14 Intent conformance
 ↓
P15 Implementation conformance
 ↓
P16 Behavioral analysis
 ↓
P17 Test discovery
 ↓
P18 Test plan
 ↓
P19 Reports
 ↓
P20 CLI orchestration
 ↓
P21 Copilot SKILL.md
 ↓
P22 Tests
 ↓
P23 Security hardening
 ↓
P24 Observability
 ↓
P25 GitLab read
 ↓
P26 Update preview
 ↓
P27 Optional GitLab write
 ↓
P28 Performance
 ↓
P29 Cross-repository spike
 ↓
P30 Release gate
```

---

# 7. Architecture Checkpoint

```text
                  ┌──────────────────────┐
                  │      Issue Input     │
                  └──────────┬───────────┘
                             │
                    Issue Normalization
                             │
                    Issue Intent Analysis
                             │
                             ▼
                     IssueIntent JSON
                             │
                             │
┌───────────────┐    ┌───────▼────────┐
│ Local Git/MR  │───▶│   ChangeSet    │
└───────────────┘    └───────┬────────┘
                             │
                   Changed Symbol Mapping
                             │
                    ┌────────▼─────────┐
                    │ Repository Index │
                    └────────┬─────────┘
                             │
                    Dependency Subgraph
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     Developer Intent             Implementation Facts
              │                             │
              └──────────────┬──────────────┘
                             ▼
                    Conformance Engine
                             │
                             ▼
                       Impact Engine
                             │
                             ▼
                     Test Discovery
                             │
                             ▼
                      Report Generator
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  Human Reports        Machine JSON        Issue Update
```

---

# 8. Main Technical Risks

## Risk 1 — False Certainty

The most dangerous failure mode is presenting an inferred dependency or inferred requirement as a fact.

**Mitigation:** evidence + confidence + explicit/inferred classification.

## Risk 2 — Weak Static Analysis

Dynamic dispatch, reflection, dependency injection, generated code, and runtime wiring may produce an incomplete call graph.

**Mitigation:** adapter-specific confidence, unresolved edges, and later runtime/config detectors.

## Risk 3 — LLM Prompt Injection

Issue text, Merge Request descriptions, code comments, and documentation are untrusted external content.

**Mitigation:** strict execution policy, bounded context, and separation between data and instructions.

## Risk 4 — Over-Engineered Indexing

Building an organization-wide semantic platform too early would delay useful MVP results.

**Mitigation:** SQLite structural index + targeted N-hop graph first.

## Risk 5 — Language Fragmentation

Different ecosystems require different parsers.

**Mitigation:** stable language adapter interface before implementing multiple language backends.

---

# 9. MVP Definition of Done

The MVP is complete when a command equivalent to:

```bash
mr-impact full \
  --repo . \
  --issue ./issue.md \
  --base main \
  --head feature/example
```

produces a reproducible run containing:

- structured Issue intent;
- deterministic change set;
- changed-symbol map;
- bounded dependency impact;
- Issue-vs-Merge-Request conformance findings;
- existing test discovery;
- proposed regression test plan;
- evidence-backed Markdown reports;
- no GitLab dependency;
- no unsupported hard conclusions.

---

# 10. First Approval Item

The first approval gate is **P01 — Freeze MVP Scope and Contracts**.

After approval, implementation must remain within this MVP boundary until a later approved item explicitly expands the scope.
