# Astra 6 Implementation Instructions

## Mission

Implement the complete Copilot Agent Skill described by this project.

The target is a production-oriented, local-first Copilot skill suite for GitHub Copilot Agent Mode in VS Code.

Expose exactly four user-facing skills:

1. **`/analyze-issue`**
2. **`/index-repository`**
3. **`/analyze-mr`**
4. **`/update-issue`**

All four must be thin wrappers over one shared physical implementation engine.

Build the complete implementation, scripts, tests, schemas, templates, supporting documentation, and example fixtures required for those capabilities.

Do not stop after producing a plan, skeleton, partial prototype, or first-pass implementation.

Continue until the implementation satisfies the completion criteria in this document or until a truly blocking ambiguity makes a correct implementation impossible.

---

# 1. Operating Mode for GPT-6 Astra

## Work End-to-End

This is an end-to-end implementation task.

You should:

```text
inspect
→ plan internally
→ implement
→ run
→ test
→ inspect results
→ fix failures
→ rerun
→ document
→ finish
```

Do not require the user to approve routine implementation steps.

Do not split the task into a long sequence of user-managed micro-approvals.

Self-decompose the work into whatever internal stages are useful, but keep progressing automatically.

Ask the user only when a missing decision is both:

1. consequential to the product contract; and
2. impossible to resolve from the source documents or repository context.

When a reasonable implementation choice can be made without changing the product contract, make the choice and continue.

## Do Not Stop at the First Working Version

A first implementation is not completion.

After implementation:

- run the relevant tests;
- exercise the CLI/workflows;
- inspect generated artifacts;
- fix defects caused by the implementation;
- rerun affected tests;
- verify the final repository structure;
- verify the skill can be discovered and used by Copilot.

Continue until these checks pass.

## Keep Context Focused

Do not repeatedly load every document for every edit.

Use progressive disclosure:

- read the primary product contract first;
- read architecture documents when implementing the relevant subsystem;
- read templates when implementing template-driven generation;
- inspect nearby implementation/tests before modifying a component.

Avoid duplicating large instructions across multiple files.

---

# 2. Source of Truth

Use these files as the implementation sources of truth.

## Primary Product Contract

```text
TASK_STATEMENT.md
```

This defines required product behavior.

If another planning document conflicts with `TASK_STATEMENT.md`, follow `TASK_STATEMENT.md`.

## Issue Output Contract

```text
GITLAB_ISSUE_TEMPLATE.md
```

This is a dynamic runtime contract.

`Analyze Issue` must generate the GitLab Issue description from the current template.

Do not implement a second hardcoded Issue layout that can drift from this file.

## Indexing / Graph Architecture

```text
MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md
```

Use this when implementing:

- repository indexing;
- local graph storage;
- boundary indexes;
- organization dependency catalog;
- cross-repository discovery;
- lazy deep expansion;
- QA runtime target discovery.


---

# 3. Target Skill Suite Format

Implement four GitHub Copilot Agent Skills:

```text
.github/
└── skills/
    ├── analyze-issue/
    │   └── SKILL.md
    ├── index-repository/
    │   └── SKILL.md
    ├── analyze-mr/
    │   └── SKILL.md
    └── update-issue/
        └── SKILL.md
```

These four skills are the user-facing slash-command surface:

```text
/analyze-issue
/index-repository
/analyze-mr
/update-issue
```

Do not implement a parent `/mr-impact-analysis` skill as the primary interface.

Each `SKILL.md` must:

- use valid YAML frontmatter;
- have one clear responsibility;
- contain a short, specific description for reliable Copilot selection;
- route to exactly one operation of the shared engine;
- avoid duplicating implementation logic or large product specifications.

---

# 4. Shared Physical Engine

Implement one shared engine outside the individual skill wrapper directories.

Preferred structure:

```text
.github/
└── skills/
    ├── analyze-issue/
    │   └── SKILL.md
    ├── index-repository/
    │   └── SKILL.md
    ├── analyze-mr/
    │   └── SKILL.md
    └── update-issue/
        └── SKILL.md

src/
└── mr_impact/
    ├── cli/
    ├── core/
    ├── indexing/
    ├── graph/
    ├── adapters/
    ├── schemas/
    ├── templates/
    ├── reports/
    └── gitlab/
```

A `pyproject.toml` CLI entry point should expose equivalent deterministic commands:

```bash
mr-impact analyze-issue ...
mr-impact index-repository ...
mr-impact analyze-mr ...
mr-impact update-issue ...
```

The skills should invoke or instruct Copilot to invoke these shared operations.

The architecture must be:

```text
four thin Copilot skills
+
one shared Python engine
```

Do not create four separate implementations.

Do not duplicate parsers, graph logic, SQLite storage, templates, schemas, or report generation between skills.

A fix in the shared engine must automatically apply to all four skill workflows.

Supporting workflow documentation may live under a shared documentation/resources location, but the user-facing `SKILL.md` wrappers should remain compact.

---

# 5. Implementation Language and Dependency Policy

## Primary Implementation

Prefer:

```text
Python
Git
SQLite
```

Use Python standard-library functionality wherever practical.

Useful standard-library modules include:

```text
argparse
ast
concurrent.futures
configparser
dataclasses
hashlib
json
logging
pathlib
re
sqlite3
subprocess
tomllib
xml.etree.ElementTree
```

## External Dependencies

Keep third-party dependencies minimal.

Do not introduce infrastructure such as:

```text
Neo4j
Elasticsearch
Sourcegraph
Qdrant
Weaviate
external graph servers
vector databases
```

unless the product contract is explicitly changed.

If an external Python dependency is genuinely necessary:

1. verify that the standard library or an existing runtime cannot solve the requirement reasonably;
2. keep the dependency narrow;
3. isolate it behind an adapter;
4. document why it is needed;
5. provide a graceful fallback where practical.

## Existing Language Runtimes

Use already available and approved developer runtimes when they materially improve correctness.

Examples:

```text
.NET SDK / Roslyn
JVM
```

Do not require them globally if a repository does not use that technology.

---

# 6. Core Architecture

Implement a technology-neutral graph model.

Technology-specific adapters should normalize their results into shared entity and edge types.

Examples of entities:

```text
REPOSITORY
PROJECT
MODULE
FILE
CODE_SYMBOL
PACKAGE
SCRIPT
PROCESS
JOB
WORKFLOW
PIPELINE
AUTOSYS_JOB
AUTOSYS_BOX
DATABRICKS_JOB
DATABRICKS_PIPELINE
DATABRICKS_NOTEBOOK
DB_TABLE
DB_VIEW
DB_PACKAGE
DB_PROCEDURE
DB_FUNCTION
API_ENDPOINT
SERVICE
EVENT
TOPIC
CONFIG
CONFIG_KEY
TEST
```

Examples of edges:

```text
CONTAINS
DEFINES
USES
CALLS
REFERENCES
READS
WRITES
EXECUTES
LAUNCHES
DEPENDS_ON
TRIGGERS
PRODUCES
CONSUMES
CONFIGURES
TESTED_BY
```

Keep the universal model small.

Technology-specific detail belongs in metadata and adapters.

---

# 7. Required Capability — Analyze Issue

Implement exactly two required user-facing outputs.

## Input

By default:

```text
all relevant material from the current repository/project root
```

The user must also be able to provide a specific folder, for example:

```text
./requirements/issue-input/
```

When a folder is explicitly provided, respect that scope and do not use unrelated files outside it unless required project resources such as the Issue template are needed.

## Output 1

```text
00-issue-analysis.md
```

This is the analytical report.

It should explain, based on available evidence:

- problem/current state;
- desired outcome;
- scope/non-goals;
- Acceptance Criteria;
- constraints/dependencies;
- assumptions;
- open questions;
- ambiguity;
- validation expectations;
- missing/conflicting information;
- readiness issues represented by the current template.

Separate explicit facts from inference.

Do not invent requirements.

## Output 2

```text
01-generated-issue.md
```

Generate this file strictly from the **current**:

```text
GITLAB_ISSUE_TEMPLATE.md
```

The template must be parsed/read at execution time.

If the template changes, subsequent generated Issues must automatically follow:

- new sections;
- removed sections;
- renamed sections;
- changed ordering;
- changed embedded instructions.

Do not duplicate the template structure in Python constants or another schema unless the implementation derives that schema automatically from the template.

---

# 8. Required Capability — Index Repository

Implement persistent repository indexing with two logical modes.

## Deep Mode

Used for the repository containing the current MR.

Conceptually:

```text
index repository --deep
```

Build enough detail for local MR impact analysis.

## Boundary Mode

Used for large-scale indexing of other repositories.

Conceptually:

```text
index repository --boundary
```

Focus on cross-repository entities rather than a complete local call graph.

Examples:

- packages/artifacts;
- DB tables/packages/procedures;
- APIs;
- events/topics;
- AutoSys jobs;
- Databricks jobs/pipelines;
- scripts;
- shared configuration;
- services;
- runtime entry points.

## Persistent Storage

Keep local indexes separate from per-MR output.

A reasonable layout is:

```text
.repository-analysis/
├── repositories/
│   └── <repo-id>/
│       ├── manifest.json
│       ├── files.sqlite
│       ├── symbols.sqlite
│       ├── graph.sqlite
│       ├── boundary.json
│       └── state.json
└── organization/
    ├── repositories.sqlite
    ├── entities.sqlite
    ├── dependencies.sqlite
    └── manifest.json
```

The exact schema may differ if a better implementation is justified.

## Incremental Indexing

Use Git state and content identity.

Avoid reparsing unchanged files.

Prefer:

```text
indexed commit
+
current commit
+
git diff
+
blob/content identity
```

to determine what must be updated.

The implementation must be usable on very large repositories.

Do not load the entire dependency graph into Python memory.

---

# 9. Technology Adapters

Create an adapter framework rather than hardcoding one language.

At minimum, implement a useful generic adapter and architecture for specialized adapters.

The design must support repositories containing:

```text
C#
Scala
Databricks
Oracle SQL / PL/SQL
AutoSys JIL
XML
YAML
PowerShell
shell/batch scripts
```

Implement specialized support where practical within this task.

## Generic Adapter

Must provide useful fallback discovery for unknown technologies.

Extract candidates such as:

- files;
- manifests;
- package identifiers;
- URLs;
- obvious DB identifiers;
- job names;
- script references;
- configuration references;
- external artifact identifiers.

Use lower confidence when a relationship is heuristic.

## C# / .NET

If an existing .NET SDK is available, prefer a small Roslyn-based helper for precise symbol/reference extraction.

Do not write a fake regex-based C# semantic resolver.

Provide fallback structural extraction if Roslyn is unavailable.

## Oracle

Implement lightweight extraction for:

- packages;
- package bodies;
- procedures;
- functions;
- tables;
- views;
- triggers;
- reads/writes;
- calls/references.

Mark dynamic SQL with appropriate uncertainty.

## AutoSys JIL

Implement a dedicated lightweight parser.

Extract useful fields such as:

- job name;
- job type;
- command;
- condition;
- box name;
- machine/profile where useful;
- parent/child and upstream/downstream dependencies;
- script/executable references.

## Databricks / Scala

Support discovery of:

- Databricks jobs;
- pipelines;
- tasks;
- notebooks;
- table reads/writes;
- job/task relationships;
- Scala/JVM package/build dependencies;
- useful boundary references.

Perfect Scala semantic analysis is not required for useful boundary indexing.

---

# 10. Organization-Wide Dependency Catalog

Implement the architecture described in:

```text
MULTI_REPOSITORY_INDEXING_ARCHITECTURE.md
```

Each repository should be able to export a compact boundary index.

The organization catalog should provide reverse lookups such as:

```text
entity
→ repositories that provide/use/read/write/execute it
```

Use canonical identifiers where possible, for example:

```text
oracle://SCHEMA/PACKAGE.PROCEDURE
table://CATALOG/SCHEMA/TABLE
autosys://JOB_NAME
nuget://PACKAGE_NAME
maven://GROUP/ARTIFACT
databricks-job://JOB_KEY
event://TOPIC
api://SERVICE/METHOD/PATH
```

Do not build one giant global method-level call graph across every repository.

---

# 11. Required Capability — Analyze Merge Request

This is the core runtime analysis capability.

It must:

1. identify changed files/hunks/symbols deterministically;
2. use the deep index for the current repository;
3. traverse relevant local relationships;
4. identify operational boundary entities;
5. query the organization dependency catalog when available;
6. identify candidate related repositories;
7. deep-expand only candidate repositories when necessary;
8. identify affected processes/jobs/workflows;
9. produce concrete QA execution targets.

The Issue may be used as context.

Do not judge whether the developer understood the Issue correctly.

Do not grade the implementation as correct/incorrect relative to an Issue that may be stale or incomplete.

Describe observed differences factually.

---

# 12. Process / Job / Runtime Impact Is a Core Requirement

The MR analysis is incomplete if it reports only source-code impact while runtime relationships can be discovered.

The system must attempt to identify affected:

- AutoSys jobs;
- AutoSys boxes;
- batch jobs;
- scheduled jobs;
- Databricks jobs;
- Databricks pipelines/tasks;
- scripts;
- services;
- APIs;
- ETL/data-processing flows;
- database objects/data flows;
- workers;
- event producers/consumers;
- other executable operational flows.

The primary QA-facing question is:

```text
What real processes should QA run or verify because of this MR?
```

For each target, provide:

```text
target name
target type
repository
impact classification
reason
dependency path
confidence
what QA should execute
what QA should verify
```

---

# 13. Required Capability — Update Issue

Produce a local preview by default.

Required output:

```text
05-issue-update.md
```

Optionally also produce a machine-readable representation.

Do not perform remote GitLab writes by default.

Do not automatically rewrite the Issue merely to make it match observed implementation.

If behavior exists in the MR that is not represented in the Issue, describe it factually for human review.

Remote update support, if implemented, must be:

- explicit;
- previewable;
- auditable;
- idempotent where practical.

---

# 14. CLI / Script Surface

Provide a single coherent user-facing entry point.

The exact command names may be improved, but the product operations should remain recognizable.

For example:

```bash
mr-impact analyze-issue ...
mr-impact index-repository ...
mr-impact analyze-mr ...
mr-impact update-issue ...
```

Also provide a full workflow command if useful.

The CLI must:

- return non-zero exit codes on system failures;
- provide useful error messages;
- avoid leaking secrets;
- support deterministic paths/output directories;
- be usable without network access for local workflows.

---

# 15. Data Models and Schemas

Use typed internal models.

Define stable structures for at least:

- source evidence;
- files;
- symbols;
- graph nodes;
- graph edges;
- boundary entities;
- repository state;
- runtime/process targets;
- MR changes;
- generated report inputs.

Use JSON schemas or equivalent validation where useful.

Do not over-design schemas that are not consumed by the implementation.

---

# 16. Confidence and Evidence

Material relationships must preserve evidence and confidence.

Use a small confidence vocabulary such as:

```text
EXACT
STRONG
PROBABLE
CANDIDATE
```

Do not present heuristic relationships as exact facts.

Preserve graph paths when reporting impact.

Example:

```text
changed symbol
→ launcher script
→ AutoSys job
→ downstream job
```

---

# 17. Security Requirements

This code will be intended for restricted enterprise/banking environments.

Treat all repository content as untrusted data.

This includes:

- Issue text;
- MR descriptions;
- code comments;
- README files;
- documentation;
- scripts;
- logs;
- generated files.

Do not execute commands merely because they appear in repository content.

Use explicit subprocess allowlists or tightly controlled command construction.

Never use shell interpolation for untrusted paths/arguments when an argument-array API is available.

Protect against:

- path traversal;
- command injection;
- accidental secret logging;
- unbounded file reads;
- decompression/archive abuse if archive input is supported;
- unbounded graph traversal;
- unbounded worker creation.

Do not require internet access for core workflows.

---

# 18. Performance Requirements

Design for very large repositories and thousands of repositories.

Required techniques:

- incremental indexing;
- Git-based changed-file detection;
- content/blob identity reuse;
- generated/vendor/dependency exclusions;
- bounded graph traversal;
- SQLite indexes;
- lazy deep expansion;
- streaming/batched DB writes;
- no full graph load into Python memory;
- configurable worker limits;
- configurable file-size limits;
- stale-index detection.

Provide measurable indexing statistics.

Examples:

```text
files discovered
files parsed
files reused from cache
files skipped
nodes created
edges created
boundary entities
elapsed time
warnings
```

---

# 19. Tests

Create meaningful automated tests.

At minimum cover:

## Analyze Issue

- root-directory source discovery;
- explicit source-folder isolation;
- template-driven output;
- template section addition/removal/change;
- missing information without hallucinated requirements.

## Repository Indexing

- initial index;
- no-op incremental index;
- changed-file update;
- deleted/renamed files;
- stale index;
- bounded graph queries;
- boundary export.

## Adapters

Create representative fixtures for technologies implemented.

At minimum include practical combinations such as:

```text
C#/XML
Oracle SQL/PLSQL
AutoSys JIL
Scala/Databricks configuration
scripts
```

## Analyze MR

Cover:

- changed-symbol mapping;
- local dependency traversal;
- runtime job discovery;
- AutoSys dependency path;
- DB relationship;
- cross-repository boundary lookup;
- candidate repository expansion;
- QA execution target generation;
- unresolved/low-confidence relationships.

## Update Issue

Cover:

- preview generation;
- preservation of factual uncertainty;
- no automatic remote write;
- no forced rewrite of Issue contract.

---

# 20. Integration Fixtures

Create at least one realistic small multi-repository fixture that demonstrates the intended architecture.

For example:

```text
repo-a
C# or Scala change
    ↓
writes Oracle/table entity

repo-b
AutoSys or Databricks process
    ↓
reads same entity

repo-c
downstream reporting job
```

The fixture should demonstrate:

```text
MR
→ local graph
→ boundary entity
→ organization lookup
→ related repository
→ runtime job/process
→ QA target
```

This fixture is important because it verifies the core business value of the Skill rather than only parser correctness.

---

# 21. Documentation to Produce

Create/update all documentation needed to operate the Skill.

At minimum:

```text
.github/skills/analyze-issue/SKILL.md
.github/skills/index-repository/SKILL.md
.github/skills/analyze-mr/SKILL.md
.github/skills/update-issue/SKILL.md
shared engine documentation
workflow docs
CLI usage
index storage explanation
adapter extension guide
security/trust-boundary notes
testing instructions
example prompts
```

Do not duplicate the full `TASK_STATEMENT.md` into every document.

Keep docs focused on their audience.

---

# 22. Final Validation

Before declaring completion:

1. verify the final repository structure;
2. verify all four user-facing skill wrappers exist:
   - `.github/skills/analyze-issue/SKILL.md`
   - `.github/skills/index-repository/SKILL.md`
   - `.github/skills/analyze-mr/SKILL.md`
   - `.github/skills/update-issue/SKILL.md`
3. verify each wrapper routes to exactly one shared-engine operation;
4. verify no business logic is duplicated across the four skill directories;
5. verify the shared CLI exposes all four equivalent operations;
6. run unit tests;
7. run integration tests;
8. execute an `/analyze-issue` fixture;
9. confirm exactly:
   - `00-issue-analysis.md`
   - `01-generated-issue.md`
10. modify a fixture copy of `GITLAB_ISSUE_TEMPLATE.md` and verify generated Issue structure follows it;
11. execute `/index-repository` in deep mode;
12. build at least one boundary index;
13. aggregate a small organization catalog;
14. execute `/analyze-mr` on the multi-repository fixture;
15. verify runtime/process/job targets are found;
16. verify QA recommendations contain evidence paths;
17. execute `/update-issue` and verify preview generation;
18. inspect generated Markdown for usability;
19. fix failures or obviously weak output;
20. rerun affected tests.

Do not report success before this validation is complete.

---

# 23. Deliverables

The final repository should contain a complete working implementation, not only design documents.

Expected categories:

```text
four Copilot Skill wrapper files
shared Python implementation
optional runtime-specific helpers
SQLite/schema/storage layer
technology adapters
templates/resources
unit tests
integration fixtures
integration tests
documentation
example outputs
```

Do not leave core functionality as TODOs or placeholder stubs.

Optional future integrations may remain clearly separated, but the four primary capabilities must work locally.

---

# 24. Completion Report

At the end, provide a concise implementation report containing:

```text
What was implemented
Key architecture decisions
Files/directories created
Supported adapters
Commands available
Tests executed and results
Known limitations
Optional future work
```

Do not ask for review before completing the implementation unless a blocking product decision truly prevents further correct work.

---

# 25. Important Non-Goals

Do not spend time building:

- a polished web UI;
- a hosted service;
- a graph database cluster;
- a vector-search platform;
- autonomous GitLab write behavior;
- exhaustive semantic support for every programming language;
- organization-wide full method-level graphs.

Prioritize the working local skill, reusable index architecture, runtime dependency discovery, and QA execution value.

---

# 26. Decision Rule

When choosing between:

```text
more infrastructure
```

and:

```text
a simpler deterministic local implementation
```

prefer the simpler local implementation unless the simpler design cannot meet the documented requirement.

When choosing between:

```text
perfect language semantics
```

and:

```text
reliable operational dependency discovery
```

prioritize the dependency information that improves MR impact analysis and QA execution targeting.

---

# 27. Start Now

Begin by inspecting the source-of-truth documents and current repository contents.

Create a concise internal implementation plan.

Then execute it end-to-end.

Do not stop after planning.

Do not wait for approval between routine phases.

Continue through implementation, testing, verification, and documentation until the Definition of Done above is satisfied.
