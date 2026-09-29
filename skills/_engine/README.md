# MR Impact engine (`skills/_engine`)

Shared Python package for indexing and analysis. **Copilot skills** call this via `_mr-impact/scripts/run_engine.py` once CLI modules are present under `src/mr_impact/`.

## On disk today

- `src/mr_impact/readers/` — iFlow-derived parsers (`python_ast`, `treesitter`) and `requirements.txt` for optional tree-sitter grammars.
- No `adapters.py` / CLI wiring until the engine implementation lands in this tree.

## Optional parsers (iFlow)

```bash
pip install -r src/mr_impact/readers/requirements.txt
```

Grammars are optional; Python uses stdlib `ast` without extra packages.
