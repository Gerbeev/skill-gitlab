# Step 2: Run Engine

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- analyze-mr --revision "<revision>" --run-dir "{project-root}/.repository-analysis/run"
```

Add `--issue-dir` when Issue artifacts are available.

Non-zero exit → **HALT**.

Verify engine outputs exist under `run/`:

- Markdown: `01-mr-analysis.md` … `04-test-plan.md`
- JSON: `mr-context.json`, `changed-symbols.json`, `impact-graph.json`, `runtime-impact.json`, `test-impact.json`, `boundary-hints.json` (last may be empty hints if no catalog)

Canonical list: `{project-root}/docs/reference/engine-contract.md` (Analyze MR section).

## NEXT

Read fully and follow `{{ rendered("step-03-present.md") }}`
