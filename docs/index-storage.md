# Index storage and organization maintenance

Default location is `<repo>/.repository-analysis`; `--cache PATH` selects a shared
cache. Repository IDs contain a readable folder name and a hash of its absolute
local path. Repositories with equal folder names remain distinct. Moving a clone
creates a new cache identity; remove the previous catalog entry via a deliberate
catalog rebuild when replacing a clone.

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
covering the run. A failure rolls back state and index changes. Large exports
stream to atomic temporary files; no-op runs reuse existing large exports.
If an export is missing it is recreated from SQLite. External tampering with
cache files is unsupported; cache directories must be access controlled.

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
20 candidate repositories, and two cross-repository hops. A run has at most two
local graphs plus one graph per selected candidate. Candidate traversal limits
are per candidate, so the total graph bound is `(2 + max_candidates)` times the
local node/edge limits. Graph paths are bounded by these limits and cross depth.

Git command output is capped at 64 MB (diffs at 20 MB) and commands have a
120-second timeout. Extremely large trees beyond that metadata bound need a
partitioned include scope or future streaming Git-tree enumeration. No billion-
line benchmark has been performed. Configurable ceilings are safeguards, not a
claim that maximum settings fit every workstation.


## Audit fixes and reuse behavior

Adapter version 2 rebuilds older indexes once. Subsequent exact no-op builds return
statistics without rewriting manifests or exports. A missing export is regenerated
without re-parsing unchanged files. Excluded worktree files are filtered before their
contents are read; oversized dirty files are recorded without hashing their contents.

Boundary exports include standalone definitions as well as relationship observations.
Candidate observation lookup batches up to 400 entities per SQLite query. Python relative
imports use package-relative paths; package `__init__.py` resolution is refreshed when
files are added or removed without re-parsing unchanged callers. The original import
target remains in edge provenance for reversible resolution.

Edge evidence retains the extraction revision, while the graph/index manifest records
the current snapshot revision. Unchanged blobs can therefore reuse extraction evidence
without claiming that parsing was repeated at every commit.

Synthetic timing and Python-allocation measurements are in [benchmark-results.json](benchmark-results.json).
They cover 1,000 files and one candidate repository, not thousands of repositories.
