# Step 2: Run Engine

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- update-issue --run-dir "{project-root}/.repository-analysis/run"
```

Non-zero exit → **HALT**.

After zero exit:

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- validate-artifacts --profile update-run --run-dir "{project-root}/.repository-analysis/run"
```

Non-zero validation → **HALT**.

## NEXT

`{{ rendered("step-03-present-and-apply.md") }}`
