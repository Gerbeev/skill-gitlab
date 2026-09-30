# Step 3: Present and Apply

Follow `references/validate-present.md` before closing the run.

1. Show summary of `05-issue-update.md` (and `issue-update.json` if the user wants machine-readable preview).
2. Default: **do not** write to GitLab.

### CHECKPOINT

Present the preview paths and a short summary of proposed Issue changes. **HALT** and wait for the user to confirm they have reviewed the preview.

3. **Only after explicit confirmation to apply:** use GitLab MCP or token per `gitlab-integration.md`. If the user did not ask to apply, skip GitLab writes entirely.
4. After apply (or if preview-only), offer `run/` cleanup per `references/run-cleanup.md`.

{{ workflow.on_complete }}

## DONE
