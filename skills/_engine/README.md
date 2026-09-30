# MR Impact engine (`skills/_engine`)

Shared Python package for **DEEP indexing**, Issue prep, MR impact, and Issue update preview. Copilot skills invoke it via `_mr-impact/scripts/run_engine.py`. Canonical CLI and artifacts: [docs/reference/engine-contract.md](../../docs/reference/engine-contract.md). QA dependency chains: [nearest-runtime-impact-paths.md](../../docs/reference/nearest-runtime-impact-paths.md).

**Engine-only changes:** edit Python under `src/mr_impact/` and `tests/` here — not markdown under `skills/<name>/` unless the skill workflow itself must change. After engine edits, run `python tools/quality.py` from the repo root (bundles `_mr-impact/engine` via setup).

## Layout (`src/mr_impact`)

| Area | Role |
| --- | --- |
| `paths.py` | `.repository-analysis/` layout (index, graph, run, catalog) |
| `json_io.py` | Shared JSON read/write for run artifacts |
| `cli.py` / `cli_dispatch.py` | CLI entry and command dispatch |
| `index/` | DEEP index pipeline, SQLite store, language adapters |
| `readers/` | Optional tree-sitter / AST readers used by adapters |
| `graph/` | Impact traversal and nearest runtime QA paths |
| `git/` | Revision parsing and diff-accurate symbol mapping |
| `issue/`, `mr/` | analyze-issue and analyze-mr orchestration |
| `mr/symbols_from_diff.py` | MR index refresh + diff-accurate symbols |
| `mr/run_context.py` | Shared `MrRunContext` after graph/MR computation |
| `mr/payloads.py` | MR run JSON artifacts |
| `mr/reports.py` | `01`–`04` markdown for analyze-mr |
| `artifacts/` | Contract validation (`validate.py`, `contract.py`) |

## Install (optional)

```bash
python -m pip install -e skills/_engine
```

`run_engine.py` also works with `PYTHONPATH=skills/_engine/src` (no install).

## DEEP index and graph (separate commands)

```bash
cd /path/to/your/repo
python -m mr_impact create-index    # .repository-analysis/index/ only
python -m mr_impact create-graph    # .repository-analysis/graph/ from sqlite
```

Legacy: `index-repository --mode deep` runs both in one process.

### Issue and MR commands

```bash
python -m mr_impact analyze-issue --input-dir ./in --template ./GITLAB_ISSUE_TEMPLATE.md --run-dir .repository-analysis/run
python -m mr_impact analyze-mr --revision HEAD~1..HEAD --run-dir .repository-analysis/run
python -m mr_impact update-issue --run-dir .repository-analysis/run
```

Writes:

```text
.repository-analysis/
├── index/
│   ├── repository-index.sqlite
│   ├── repository-index.json
│   └── index-manifest.json
└── graph/
    ├── dependency-graph.json
    └── graph-manifest.json
```

### Adapter order (V1)

1. **JIL** — AutoSys jobs, box links, script paths in `command`
2. **SQL** — Oracle-style objects, `FROM`/`JOIN`, `CALL`/`EXEC`, package member calls
3. **C#** — `.csproj` package/project refs; `.cs` via tree-sitter or regex fallback
4. **Readers** — Python `ast` + optional tree-sitter for other languages (`readers/_lib`)
5. **Generic** — path literals, config file markers

Incremental: unchanged file hashes are skipped on re-run (SQLite).

### Optional tree-sitter grammars

```bash
pip install -r src/mr_impact/readers/requirements.txt
```

Grammars install to `src/mr_impact/readers/_lib` (optional; see `readers/requirements.txt`).

## Tests

```bash
python -m unittest discover -s skills/_engine/tests -p "test_*.py"
```
