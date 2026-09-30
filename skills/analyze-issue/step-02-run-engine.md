# Step 2: Run Engine

## INSTRUCTIONS

Run exactly once:

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- analyze-issue --input-dir "<input-dir>" --template "{skill-root}/GITLAB_ISSUE_TEMPLATE.md" --run-dir "{project-root}/.repository-analysis/run"
```

- Non-zero exit: show stderr and **HALT**. Do not fabricate outputs.
- Zero exit: run validation once:

```bash
python "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- validate-artifacts --profile issue-run --run-dir "{project-root}/.repository-analysis/run" --template "{skill-root}/GITLAB_ISSUE_TEMPLATE.md"
```

Non-zero validation → **HALT** (report stderr; do not invent Issue sections).

## NEXT

Read fully and follow `{{ rendered("step-03-present.md") }}`
