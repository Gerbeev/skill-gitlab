---
revision: ''
issue_dir: ''
---

# Step 1: Gather Context

## RULES

- Deterministic diff parsing is owned by the engine; do not replace it with narrative guessing.
- Clean `{project-root}/.repository-analysis/run/` before starting unless the user asked to keep prior artifacts.
- Read `references/analysis-inputs.md` and use **only artifacts that exist** under `.repository-analysis/index/` and/or `graph/`.

## INSTRUCTIONS

1. **Revision.** From the prompt, resolve Git range (default `origin/main..HEAD`), MR branches, or patch file. Optional: GitLab MCP / token for MR metadata.
2. **Index / graph (optional, use what exists).**
   - If `index/repository-index.sqlite` or `index/index-manifest.json` exists → load freshness (`git_head`) and summary; use SQLite-backed detail when graph JSON is absent.
   - If `graph/dependency-graph.json` exists → use for bounded traversal; if **both** index and graph exist, prefer graph JSON for traversal and index manifest for freshness/stats.
   - If **neither** folder has useful artifacts → tell the user to run `/create_index`; offer `/create_graph` when traversal needs JSON export. Do not invent edges.
   - If index exists but graph does not → proceed with index-only context; mention `/create_graph` if deeper traversal is needed.
3. **Issue context.** Optional folder with `01-generated-issue.md` or GitLab fetch output.
4. **Boundary catalog.** If `{project-root}/.repository-analysis/catalog/boundary-catalog.json` exists, note it for cross-repo hints only.

Set `revision` in this step's frontmatter mentally for step 2.

### CHECKPOINT

Present: revision; index yes/no; graph yes/no; issue context yes/no. HALT for confirmation if revision is ambiguous.

## NEXT

Read fully and follow `{{ rendered("step-02-run-engine.md") }}`
