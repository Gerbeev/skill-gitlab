# Step 2: Run Engine

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- analyze-mr --revision "<revision>" --run-dir "{project-root}/.repository-analysis/run"
```

Add `--issue-dir` when Issue artifacts are available.

Non-zero exit → **HALT**.

Verify human reports `01`–`04` and JSON artifacts exist.

## NEXT

Read fully and follow `{{ rendered("step-03-present.md") }}`
