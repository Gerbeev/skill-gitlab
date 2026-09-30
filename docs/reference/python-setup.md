# Python setup without uv

`uv` is **optional**. Everything in MR Impact runs with a normal **Python 3.11+** install.

## One-time (per machine or venv)

```bash
# Hub scripts (render_skill needs Jinja2)
python -m pip install -r skills/mr-impact-method/scripts/requirements.txt

# Engine: bundled by setup into _mr-impact/engine/ (no separate install required)
python skills/mr-impact-method/scripts/setup.py --project-root .
```

Optional dev install from monorepo:

```bash
python -m pip install -e skills/_engine
```

Optional tree-sitter grammars (indexing): see `skills/_engine/src/mr_impact/readers/requirements.txt`.

## Commands instead of `uv run`

| With uv (optional) | Without uv |
| --- | --- |
| `uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root .` | `python skills/mr-impact-method/scripts/setup.py --project-root .` |
| `uv run --no-cache _mr-impact/scripts/render_skill.py --project-root . --skill skills/analyze-issue` | `python _mr-impact/scripts/render_skill.py --project-root . --skill skills/analyze-issue` |
| `uv run --project skills/_engine python -m mr_impact create-index` | `python _mr-impact/scripts/run_engine.py --project-root . -- create-index` |
| (graph export) | `python _mr-impact/scripts/run_engine.py --project-root . -- create-graph` |

On Windows, if `python` is not on PATH, use `py -3.11` in place of `python`.

## Virtual environment (recommended)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
python -m pip install -r skills/mr-impact-method/scripts/requirements.txt
python -m pip install -e skills/_engine
```

Copilot agents should use the same interpreter (venv activated or full path to `python`).

## Copilot-only workflow (no local CLI)

You can use skills **without** running Python yourself: the agent executes `python …` from the skill steps. You still need:

1. **Setup once** (you or the agent): `python skills/mr-impact-method/scripts/setup.py --project-root .`
2. **`jinja2` installed** for the Python that Copilot uses to run `render_skill.py`.

If `render_skill` fails with `No module named 'jinja2'`, run the pip install line above in that environment.

## When uv is still useful

`uv` speeds up isolated runs and matches BMAD examples in `examples/BMAD-METHOD`. It is not required for this repository.
