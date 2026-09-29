# Evidence rules (Analyze Issue)

Classify every statement as one of:

- explicit requirement
- constraint
- context
- assumption
- open question
- AI inference (must be labeled)

Never promote inference to Acceptance Criteria without evidence.

## Graph / AutoSys (when index exists)

- Use **anchors** from explicit Issue mentions (job name, script path, symbol)—not “all jobs in module.”
- Report **full paths** along JIL/box/dependency edges; do not list sibling jobs in a box without a path from the anchor.
- See [docs/reference/issue-anchored-graph-traversal.md](../../../docs/reference/issue-anchored-graph-traversal.md).
