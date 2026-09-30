# Present-step checklist

Before marking a workflow **DONE**:

1. **Paths** — Name output files with repo-relative paths (or editor code citations for snippets).
2. **Engine honesty** — If the engine did not run or failed, do not invent `00-*` / `03-*` / index manifests.
3. **Scope** — MR/issue skills stay neutral on intent correctness; issue skill does not add template sections.
4. **GitLab** — No write to GitLab unless the user explicitly confirmed (update-issue apply step).
5. **Cleanup** — Run `on_complete` from customization unless the user asked to keep run artifacts.
