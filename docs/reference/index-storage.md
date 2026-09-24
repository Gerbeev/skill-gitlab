# Index storage and organization maintenance

Default location is `<repo>/.repository-analysis`; `--cache PATH` selects a shared
cache. By default, repository IDs contain a readable folder name and a hash of
the absolute local path. For stable organization identity, configure
`.repository-identity.json` as described below. Physical caches remain distinct
for separate checkouts even when they share an explicit logical repository ID.

```text
CACHE/
  repositories/<repository-id>/
    current/
      repository-index.sqlite
      repository-index.json
      boundary.json
      manifest.json
      state.json
      graph/
        dependency-graph.json
        graph-manifest.json
    base/
      ... same layout for the most recently analyzed base ...
```

One SQLite database physically stores logically separate file, symbol,
definition, and edge tables. This keeps per-file replacement transactional.
Structural JSON export is separate from graph JSON export and per-MR reports.
The graph is queried directly in SQLite through forward and reverse indexes;
JSON exports are for interchange and inspection, not query-time graph loading.

## Identity, freshness, and incremental updates

Git tree blob IDs are the primary committed-content change detector. The engine
enumerates the selected tree, compares path/blob identity with the previous
index, and parses only new/changed units. Deletions and renames remove old
symbols and file-owned edges. Worktree mode combines Git changed/untracked paths
with chunked SHA-256 hashes for modified content. A commit alone is not enough
to establish worktree freshness.

The state persists commit, mode, schema and adapter versions, configuration, and
a selected-content fingerprint. A schema/adapter/configuration/mode change
requires a rebuild. `--check` validates freshness without refreshing; stale
results use exit code 3. Deep analysis refreshes its required index automatically.
Each candidate is analyzed at the catalog's recorded committed snapshot.

Changed committed blobs are read with `git cat-file --batch`, avoiding a Git
process for every file. Batches contain at most 64 files and normally 8 MB of
content (a configured larger single-file limit can raise that byte bound).
Per-file writes use bounded worker batches, one SQLite writer, and a transaction
covering the run. An extraction/transaction failure rolls back state and index changes. Large exports
stream to atomic temporary files. A final manifest binds all exports to a generation
and their SHA-256 digests. No-op runs validate these digests and reuse intact exports.
Missing, corrupt, or interrupted exports are recreated from SQLite without reparsing.
Digest verification adds I/O proportional to export size. Cache directories must
remain access controlled; hashes establish consistency rather than authenticity.

Statistics include discovered, parsed, reused, skipped, and deleted files;
current node/edge/symbol counts; boundary entity count; elapsed time; and bounded
warnings. `nodes_created` and `edges_created` are current total counts, not the
delta created by the latest run. Skipped warnings persist across cache reuse.

## Boundaries and catalog

Boundary export records are typed by entity, relationship/role, source node,
confidence, and evidence. `DEFINES` represents a provider; `READS`, `WRITES`,
`USES`, `EXECUTES`, and scheduler edges retain their observed role. SQL names are
uppercased and dot-separated components become slash-separated canonical keys,
for example `table://RISK/DAILY_EXPOSURE`. Unknown schema/catalog components are
not fabricated. NuGet identities are case-normalized. AutoSys/job names retain
their case.

```text
mr-impact index-repository --repo REPO_B --boundary --cache CACHE
mr-impact index-repository --repo REPO_C --boundary --cache CACHE
mr-impact index-organization --catalog ORG.sqlite --index INDEX_B --index INDEX_C
```

`ORG.sqlite` stores repository snapshots and compact dependency observations,
with an entity/confidence/repository reverse index. The catalog imports
normalized boundary observations directly from the repository databases,
streaming them without loading exports into memory. `boundary.json` remains
the compact portable inspection/export artifact. This version's import command
requires the repository index directory, not a detached JSON-only export.

Catalog updates are transactional and replace each specified repository's old
observations. Worktree snapshots cannot be published to the catalog: lazy
expansion must be reproducible from recorded commits. Catalog construction is a
separate operation; MR analysis never scans all organization repositories.

## Resource budgets

Defaults: 2 MB per file, one million selected files, one worker, graph depth 8,
1,000 nodes and 4,000 edges per repository traversal, confidence at least 30,
20 candidate repositories, two cross-repository hops, and 100 total candidate
traversals (`--max-expansions`). Each candidate is indexed once but may receive
new seeds in later frontiers. The total retained graph bound is at most
`(2 + max_expansions)` times the local node/edge limits. Candidate/entity labels
retain useful confidence/depth alternatives; cycles and all work remain bounded.

Git command output is capped at 64 MB (diffs at 20 MB) and commands have a
120-second timeout. Extremely large trees beyond that metadata bound need a
partitioned include scope or future streaming Git-tree enumeration. No billion-
line benchmark has been performed. Configurable ceilings are safeguards, not a
claim that maximum settings fit every workstation.


## Audit fixes and reuse behavior

Adapter version 3 rebuilds older indexes once. Subsequent exact no-op builds return
statistics without rewriting manifests or exports. A missing export is regenerated
without re-parsing unchanged files. Excluded worktree files are filtered before their
contents are read; oversized dirty files are recorded without hashing their contents.

Boundary exports include external-resource definitions and relationship observations.
Local file, symbol, external-symbol, and module identities never match across repositories.
Candidate observation lookup batches up to 400 entities per SQLite query. Python relative
imports use package-relative paths; package `__init__.py` resolution is refreshed when
files are added or removed without re-parsing unchanged callers. The original import
target remains in edge provenance for reversible resolution.

Edge evidence retains the extraction revision, while the graph/index manifest records
the current snapshot revision. Unchanged blobs can therefore reuse extraction evidence
without claiming that parsing was repeated at every commit.

Synthetic timing and Python-allocation measurements are in [benchmark-results.json](benchmark-results.json).
They cover 1,000 files and one candidate repository, not thousands of repositories.

## Stable identities and resource namespaces

Optional repository-root configuration:

```json
{
  "repository_id": "risk-engine",
  "namespaces": {
    "table": "warehouse-qa",
    "oracle": "warehouse-qa",
    "autosys": "scheduler-qa"
  }
}
```

The ID accepts 1-128 letters, digits, dots, underscores, or hyphens. Keep it stable
when moving a checkout. Use the same resource namespace in all repositories that
refer to the same external installation. Namespace values are URL-encoded; a table
becomes `table://@warehouse-qa/RISK/DAILY_EXPOSURE`. The reserved `@` distinguishes
namespaces from unqualified name components. Unconfigured schemes preserve
their existing keys and assume a shared naming domain. Identity settings are
data, never executable instructions, and changes invalidate the index generation.
Re-aggregate the catalog after changing identities or namespaces. Catalog membership
uses logical repository IDs; publishing another checkout of the same logical ID
replaces its previous catalog entry.

## Publication and concurrency

The database transaction completes before export publication. The generation and
artifact hashes in `manifest.json`, published last, establish a complete exported
set. External consumers should acquire the operation lock and validate that manifest
before reading several exports; individual atomic replacements alone do not provide
a transactional view of the entire directory. Failed publication is repaired on retry.

Indexing and MR analysis acquire per-repository OS locks for their full lifecycle;
candidate locks remain held while candidate stores are used. Lock files live in a
user-specific system temporary directory outside the worktree. Catalog locks live
beside the catalog. Contention fails promptly with a retryable busy error. Locks are
released by the OS if a process exits; persistent lock files are not stale ownership.
Standalone graph queries and catalog aggregation read a consistent SQLite transaction.
Mutable current/base slots remain serialized; immutable concurrent snapshots are
not implemented. Direct engine callers should use these operation APIs rather than
mutating Store objects concurrently.
