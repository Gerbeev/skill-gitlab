# Repository analysis inputs (for downstream skills)

Persistent artifacts live under `{project-root}/.repository-analysis/`. **Use only what exists** — do not require both index and graph.

## Index (`index/`)

Present when `/create-index` has run successfully:

| File | Use |
| --- | --- |
| `index/index-manifest.json` | Freshness (`git_head`, `indexed_at`), stats |
| `index/repository-index.json` | Summary: adapters, languages, counts |
| `index/repository-index.sqlite` | Full symbols/edges source of truth |

If **only** `index/` is populated: prefer manifest + summary JSON; mention that graph JSON is not built yet and offer `/create-graph`.

## Graph (`graph/`)

Present when `/create-graph` has run **after** index:

| File | Use |
| --- | --- |
| `graph/graph-manifest.json` | Node/edge counts, `git_head`, `built_at` |
| `graph/dependency-graph.json` | Traversal-friendly nodes/edges export |

`create-graph` reads `index/repository-index.sqlite` and does not rescan the repo.

## Both folders

When **both** exist: read index manifest for freshness, then use `dependency-graph.json` for bounded traversal; cross-check counts with index summary.

## Neither

If both are missing or empty: tell the user to run `/create-index` first; for graph-backed traversal also `/create-graph`. Do not invent graph edges.

## Staleness

If `git_head` in manifest ≠ current `HEAD`, recommend refreshing index (and graph after index).
