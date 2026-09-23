# Multi-Repository Indexing Architecture

## 1. Purpose

This document defines the indexing and dependency-graph architecture for environments with:

- thousands of repositories;
- billions of lines of source code;
- multiple technology stacks;
- large dependency trees;
- restricted banking environments where introducing additional infrastructure or unapproved tools is difficult.

The design must support repositories containing combinations of:

- C# / .NET;
- Scala / JVM;
- Databricks;
- Oracle SQL / PL/SQL;
- XML;
- YAML;
- AutoSys JIL;
- PowerShell / shell / batch scripts;
- configuration files;
- other current or future technologies.

The architecture must remain usable without requiring a dedicated graph database, search cluster, code-intelligence server, or vector database.

The preferred core dependencies are:

```text
Python
Git
SQLite
existing approved language runtimes/toolchains where available
```

---

# 2. Core Principle

Do not attempt to build one complete semantic call graph for every repository.

Instead, use a two-level architecture:

```text
Local Repository Indexes
        +
Organization Dependency Catalog
```

The local repository index may contain detailed implementation relationships.

The organization-level catalog contains only the boundary entities required to connect repositories.

This keeps global indexing compact and allows deep analysis only where needed.

---

# 3. Universal Intermediate Model

Technology-specific parsers must emit a shared graph representation.

The global architecture is therefore:

```text
language / platform adapters
            ↓
universal entities and relationships
            ↓
local repository graph
            ↓
boundary export
            ↓
organization dependency catalog
```

Universal node types may include:

```text
REPOSITORY
SOLUTION
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

Universal edge types should remain intentionally small:

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

Adapters may add specialized metadata without creating incompatible graph models.

---

# 4. Repository Adapter Model

Each repository may use multiple adapters.

Conceptual interface:

```python
class RepositoryAdapter:
    def detect(self, repository): ...
    def scan_files(self, repository): ...
    def extract_entities(self, files): ...
    def extract_edges(self, files): ...
    def extract_boundary_entities(self): ...
```

Example adapters:

```text
GenericAdapter

DotNetAdapter
JvmAdapter
ScalaAdapter
DatabricksAdapter

OracleAdapter
SqlAdapter

AutosysAdapter

XmlAdapter
YamlAdapter

PowerShellAdapter
ShellAdapter
```

A single repository may use several adapters at once.

Example:

```text
Scala
+
Databricks
+
YAML
+
SQL
```

---

# 5. Generic Adapter

A Generic Adapter is mandatory.

Unknown or unsupported technologies must not make indexing fail.

At minimum, the Generic Adapter should extract:

- file paths;
- extensions;
- manifests;
- script references;
- URLs;
- obvious database identifiers;
- job identifiers;
- artifact/package names;
- configuration references;
- string-based dependency candidates.

Generic findings should use lower confidence unless validated by a specialized adapter.

---

# 6. Local Repository Index

Each repository has its own persistent index.

Suggested layout:

```text
.repository-analysis/
└── repositories/
    └── <repository-id>/
        ├── manifest.json
        ├── files.sqlite
        ├── symbols.sqlite
        ├── graph.sqlite
        ├── boundary.json
        └── state.json
```

The exact storage format may evolve, but the logical separation must remain.

The local index may contain:

- files;
- symbols;
- project/module structure;
- imports;
- references;
- method/class relationships;
- configuration relationships;
- tests;
- database relationships;
- runtime/process relationships;
- job/workflow relationships.

The local graph should be detailed enough to support:

```text
changed code
→ operational boundary
→ affected job/process/workflow
```

---

# 7. Indexing Modes

The Skill should support two repository indexing modes.

## 7.1 Deep Index

Used primarily for the repository containing the current Merge Request.

Conceptually:

```text
index repository --deep
```

Deep indexing may include:

- file catalog;
- project/module graph;
- symbols;
- references;
- calls where reliable;
- tests;
- runtime entry points;
- database objects;
- scripts;
- jobs;
- workflows;
- operational relationships.

The goal is accurate local impact analysis.

## 7.2 Boundary Index

Used primarily for the thousands of other repositories.

Conceptually:

```text
index repository --boundary
```

Boundary indexing should avoid expensive full semantic parsing.

It should focus on entities that can connect repositories:

- packages/artifacts;
- database objects;
- tables;
- APIs;
- events/topics;
- AutoSys jobs;
- Databricks resources;
- scripts;
- shared configuration;
- services;
- external runtime entry points.

The result should be compact and cheap to aggregate globally.

---

# 8. Boundary Index

Each repository exports a compact `boundary.json`.

Example:

```json
{
  "repository": "payment-processing",
  "commit": "abc123",
  "provides": [
    "nuget://bank.payment.core",
    "api://payment/reconcile"
  ],
  "uses": [
    "db://PAYMENT/PAYMENT_TRANSACTION",
    "oracle://PAYMENT/PAYMENT_PKG.RECONCILE"
  ],
  "runtime": [
    "autosys://PAYMENT_RECON_EOD"
  ]
}
```

Databricks example:

```json
{
  "repository": "risk-databricks",
  "commit": "def456",
  "provides": [
    "databricks-job://daily-risk-calculation"
  ],
  "uses": [
    "table://risk/positions",
    "table://risk/counterparty"
  ],
  "writes": [
    "table://risk/daily_exposure"
  ]
}
```

The boundary index is the bridge between local repository analysis and organization-wide dependency discovery.

---

# 9. Canonical Entity Identifiers

Cross-repository matching requires stable canonical identifiers.

Examples:

```text
db://ORACLE_SCHEMA/TABLE

oracle://SCHEMA/PACKAGE.PROCEDURE

autosys://JOB_NAME
autosys-box://BOX_NAME

nuget://PACKAGE_NAME

maven://GROUP_ID/ARTIFACT_ID

databricks-job://JOB_KEY
databricks-pipeline://PIPELINE_NAME

table://CATALOG/SCHEMA/TABLE

event://TOPIC

api://SERVICE/METHOD/PATH
```

Adapters must normalize equivalent references to the same identifier where possible.

Example:

```text
C# code references PAYMENT_PKG.RECONCILE
Oracle repository defines PAYMENT_PKG.RECONCILE
```

Both should map to:

```text
oracle://PAYMENT/PAYMENT_PKG.RECONCILE
```

---

# 10. Organization Dependency Catalog

The global catalog aggregates boundary indexes from all repositories.

Suggested storage:

```text
.organization-index/
├── repositories.sqlite
├── entities.sqlite
├── dependencies.sqlite
└── manifest.json
```

This catalog should not contain every internal method from every repository.

It should contain only organization-level entities and repository relationships.

Primary reverse-index pattern:

```text
entity
→ repositories that provide/use/read/write/execute it
```

Example:

```text
table://risk/daily_exposure
    ├── repo-A WRITES
    ├── repo-B READS
    ├── repo-C READS
    └── repo-D READS
```

or:

```text
maven://com.bank/risk-core
    ├── repo-15 PROVIDES
    ├── repo-16 USES
    └── repo-38 USES
```

---

# 11. Organization Index Build

Organization indexing is a separate operation from MR analysis.

Conceptually:

```text
index organization
```

Initial build:

```text
repo 1
repo 2
repo 3
...
repo N
    ↓
boundary index
    ↓
organization catalog
```

After the initial build, repositories should be updated incrementally.

---

# 12. Incremental Indexing

Git should be used as the primary change detector.

Persist per-repository state such as:

```text
repository
default branch
indexed commit
index version
adapter versions
```

Update flow:

```text
previous indexed commit
        ↓
current commit
        ↓
git diff
        ↓
changed files only
        ↓
incremental adapter processing
        ↓
update local graph
        ↓
update boundary index
        ↓
update global catalog
```

Full repository reparsing should be avoided unless:

- index schema changes;
- adapter logic changes materially;
- the index is corrupt;
- repository history/state cannot be reconciled.

---

# 13. Content-Addressed File Indexing

Where practical, use Git object/blob identity rather than recalculating every file from scratch.

Conceptually:

```text
path
+
blob SHA
```

If the blob SHA has not changed, the previous parsed result can be reused.

This is especially important for very large repositories.

---

# 14. Lazy Deep Expansion

The organization catalog is used to select candidate repositories.

MR analysis flow:

```text
current MR
    ↓
deep local repository index
    ↓
changed symbols
    ↓
boundary entities
    ↓
organization reverse index
    ↓
candidate repositories
    ↓
deep/on-demand analysis only for candidates
```

Example:

```text
5000 repositories
    ↓
global boundary lookup
    ↓
12 candidate repositories
    ↓
targeted deep analysis
    ↓
3 confirmed operational dependencies
```

The system must not deep-scan all repositories for every Merge Request.

---

# 15. Cross-Repository MR Impact Flow

Full conceptual flow:

```text
                Current MR Repository
                         │
                         ▼
                    Deep Index
                         │
                         ▼
                  Changed Symbols
                         │
                         ▼
                  Boundary Entities
                         │
                         ▼
              Organization Reverse Index
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
          Candidate Repo B    Candidate Repo F
               │                   │
        Local/Deep Graph     Local/Deep Graph
               │                   │
               └─────────┬─────────┘
                         ▼
              Cross-Repository Impact
                         │
                         ▼
                  QA Runtime Scope
```

---

# 16. Operational Graph Priority

For the intended use case, operational relationships are often more valuable than a compiler-perfect global call graph.

The graph should prioritize paths such as:

```text
changed symbol
→ process
→ script
→ AutoSys job
→ downstream job
```

or:

```text
changed Scala code
→ Databricks task
→ table
→ downstream repository
→ reporting job
```

or:

```text
changed Oracle package
→ table
→ consuming service
→ scheduled process
```

The main goal is to identify concrete runtime targets QA can execute or validate.

---

# 17. Technology-Specific Examples

## C# / .NET

Where an approved .NET SDK is already available, a small Roslyn-based helper may be used for precise symbols and references.

The global model remains technology-neutral.

Example:

```text
C# method
→ USES
oracle://PAYMENT/PAYMENT_PKG.RECONCILE
```

## Scala / JVM

Useful extraction includes:

- package;
- class/object/trait;
- methods;
- build dependencies;
- SQL/table references;
- Databricks references.

Perfect semantic analysis is not required for boundary discovery.

## Databricks

Extract:

- jobs;
- pipelines;
- tasks;
- notebooks;
- table reads/writes;
- dependencies between tasks/resources.

Example:

```text
databricks-job://daily-risk
→ EXECUTES
notebook://calculate-risk
→ WRITES
table://risk/daily_exposure
```

## Oracle

Extract:

- packages;
- procedures;
- functions;
- tables;
- views;
- triggers;
- reads/writes;
- procedure/package calls.

## AutoSys

Extract:

- jobs;
- boxes;
- commands;
- conditions;
- parent/child relationships;
- upstream/downstream dependencies;
- script/executable references.

## XML / YAML / Scripts

Use them primarily to discover:

- configuration relationships;
- job definitions;
- runtime launchers;
- scripts;
- packages;
- DB references;
- cross-system identifiers.

---

# 18. Confidence Model

Every non-trivial relationship should have confidence.

Suggested classes:

```text
EXACT
STRONG
PROBABLE
CANDIDATE
```

Example approximate numeric mapping:

```text
EXACT      1.00
STRONG     0.90+
PROBABLE   0.60+
CANDIDATE  0.30+
```

Examples:

```text
AutoSys JIL explicitly executes script
→ EXACT

SQL parser sees SELECT FROM TABLE
→ STRONG

string literal matches database object
→ PROBABLE

filename similarity only
→ CANDIDATE
```

Automatic cross-repository expansion should use a configurable confidence threshold.

---

# 19. Storage Strategy

Preferred first implementation:

```text
SQLite
```

Do not load the whole graph into Python memory.

Store normalized nodes and edges.

Conceptual schema:

```sql
nodes(
    id INTEGER PRIMARY KEY,
    type TEXT,
    key TEXT,
    repository_id INTEGER,
    metadata TEXT
)

edges(
    source_id INTEGER,
    target_id INTEGER,
    type TEXT,
    confidence REAL,
    evidence TEXT
)
```

Indexes should support both forward and reverse traversal.

Conceptually:

```sql
CREATE INDEX edge_source_idx
ON edges(source_id, type);

CREATE INDEX edge_target_idx
ON edges(target_id, type);
```

---

# 20. Bounded Graph Traversal

Every graph traversal must be bounded.

Controls:

```text
max_depth
max_nodes
max_edges
confidence_threshold
allowed_edge_types
cycle_detection
```

This applies to both local and cross-repository traversal.

---

# 21. Dependency Source Exclusions

Do not deeply index large external dependency source trees by default.

Examples:

```text
node_modules
vendor
.venv
NuGet package cache
Maven cache
Gradle cache
generated
build
target
dist
third_party
```

Instead, index dependency identity:

```text
package
artifact
version
reference relationship
```

Deep source analysis should occur only when explicitly needed and available.

---

# 22. Restricted Banking Environment

The architecture is intentionally compatible with restricted enterprise environments.

Core implementation should be possible with:

```text
Python standard library
Git
SQLite
```

Optional adapters may use already approved runtimes, such as:

```text
.NET SDK / Roslyn
JVM
```

No dedicated infrastructure is required for the first version.

Not required:

```text
Neo4j
Elasticsearch
Sourcegraph
Qdrant
Weaviate
graph server
vector database
```

---

# 23. Relationship to Analyze MR

`Analyze MR` must use this architecture in the following order:

```text
1. Use or refresh the deep index for the current repository.
2. Map MR changes to local symbols/entities.
3. Traverse the local graph.
4. Identify boundary entities.
5. Query the organization dependency catalog.
6. Identify candidate related repositories.
7. Deep-scan only candidate repositories when needed.
8. Identify affected processes/jobs/workflows across repositories.
9. Convert the result into QA execution targets.
```

The analysis is incomplete when cross-repository evidence exists but the Skill reports only local code-level impact.

---

# 24. QA-Oriented Output

Cross-repository analysis should answer:

```text
Which repositories are related to this change?
Which processes/jobs/workflows are affected?
Why are they related?
What dependency path connects them?
What should QA execute?
What should QA verify?
How confident is the relationship?
```

Example:

```text
Changed:
RiskWriter.writeExposure

Boundary:
WRITES table://risk/daily_exposure

Cross-repository consumers:
- reporting-service
- regulatory-export

Runtime targets:
- REPORT_GENERATION_EOD
- REGULATORY_EXPORT_JOB

QA:
1. Run DAILY_RISK_JOB.
2. Run/verify REPORT_GENERATION_EOD.
3. Run/verify REGULATORY_EXPORT_JOB.
4. Validate risk.daily_exposure output.
```

---

# 25. Design Summary

The architecture is:

```text
deep local indexing
+
compact repository boundary indexes
+
organization-wide reverse dependency catalog
+
lazy deep expansion
```

This provides:

- technology independence;
- scalability to thousands of repositories;
- compatibility with restricted enterprise environments;
- incremental indexing;
- efficient MR analysis;
- cross-repository dependency discovery;
- concrete QA runtime targets.

The key optimization is not a specific parser or graph library.

It is the separation between:

```text
deep local graph
```

and:

```text
compact global boundary graph
```

combined with incremental indexing and on-demand expansion.
