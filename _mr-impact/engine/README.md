# MR Impact engine (`skills/_engine`)

Shared Python package for **DEEP indexing** and (later) MR/issue analysis. Copilot skills invoke it via `_mr-impact/scripts/run_engine.py`.

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
2. **SQL** — Oracle-style `CREATE` objects + weak `FROM`/`JOIN` refs
3. **Readers** — Python `ast` + optional tree-sitter grammars (`readers/_lib`)
4. **Generic** — path literals, `.csproj` refs, config file markers

Incremental: unchanged file hashes are skipped on re-run (SQLite).

### Optional tree-sitter grammars

```bash
pip install -r src/mr_impact/readers/requirements.txt
```

Grammars install to `src/mr_impact/readers/_lib` (see iFlow-style layout).

## Tests

```bash
python -m unittest discover -s skills/_engine/tests -p "test_*.py"
```
