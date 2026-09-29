---
revision: ''
issue_dir: ''
---

# Step 1: Gather Context

## RULES

- Deterministic diff parsing is owned by the engine; do not replace it with narrative guessing.
- Clean `{project-root}/.repository-analysis/run/` before starting unless the user asked to keep prior artifacts.

## INSTRUCTIONS

1. **Revision.** From the prompt, resolve Git range (default `origin/main..HEAD`), MR branches, or patch file. Optional: GitLab MCP / token for MR metadata.
2. **Index.** If `.repository-analysis/index/` is missing or stale, tell the user to run `/index-repository` first; offer to run it.
3. **Issue context.** Optional folder with `01-generated-issue.md` or GitLab fetch output.
4. **Boundary catalog.** If `{project-root}/.repository-analysis/catalog/boundary-catalog.json` exists, note it for cross-repo hints only.

Set `revision` in this step's frontmatter mentally for step 2.

### CHECKPOINT

Present: revision, index state, issue context yes/no. HALT for confirmation if revision is ambiguous.

## NEXT

Read fully and follow `{{ rendered("step-02-run-engine.md") }}`
