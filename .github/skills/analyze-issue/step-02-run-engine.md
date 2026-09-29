# Step 2: Run Engine

## INSTRUCTIONS

Run exactly once:

```bash
uv run --no-cache "{project-root}/_mr-impact/scripts/run_engine.py" --project-root "{project-root}" -- analyze-issue --input-dir "<input-dir>" --template "{skill-root}/GITLAB_ISSUE_TEMPLATE.md" --run-dir "{project-root}/.repository-analysis/run"
```

- Non-zero exit: show stderr and **HALT**. Do not fabricate outputs.
- Zero exit: verify `00-issue-analysis.md` and `01-generated-issue.md` exist under the run dir.

## NEXT

Read fully and follow `{{ rendered("step-03-present.md") }}`
