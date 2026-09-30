# Step 2: Run Engine

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- update-issue --run-dir "{project-root}/.repository-analysis/run"
```

Non-zero exit → **HALT**.

Verify `05-issue-update.md` and `issue-update.json` exist.

## NEXT

`{{ rendered("step-03-present-and-apply.md") }}`
