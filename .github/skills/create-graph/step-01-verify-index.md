# Step 1: Verify Index

## INSTRUCTIONS

1. Check `{project-root}/.repository-analysis/index/repository-index.sqlite` exists.
2. If missing: tell the user to run `/create_index` first and **HALT** (do not run create-graph).

### CHECKPOINT

Confirm sqlite + optional `index-manifest.json` HEAD. Proceed only when index exists.

## NEXT

Read fully and follow `{{ rendered("step-02-run-engine.md") }}`
