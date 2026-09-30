# Step 2: Run Engine

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- analyze-mr --revision "<revision>" --run-dir "{project-root}/.repository-analysis/run"
```

Add `--issue-dir` when Issue artifacts are available.

Non-zero exit → **HALT**.

After zero exit, run validation once:

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- validate-artifacts --profile mr-run --run-dir "{project-root}/.repository-analysis/run"
```

Non-zero validation → **HALT**. Canonical artifact list: `{project-root}/docs/reference/engine-contract.md` (Analyze MR section).

## NEXT

Read fully and follow `{{ rendered("step-03-present.md") }}`
