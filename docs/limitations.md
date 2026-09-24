# Supported limits and future extensions

The four local workflows are implemented. The following boundaries are explicit:

- Standalone Issue extraction is conservative and preserves source wording.
  Arbitrary template prose, semantic ambiguity, requirement quality, and complex
  contradictions require the Copilot interpretation workflow. Evidence validation
  checks paths/ranges, source fingerprints, and template identity; it cannot prove a paraphrase true.
- C#/Scala extraction is lexical, not a compiler call graph. Python AST calls
  remain candidates when runtime name binding can differ. Reflection, dependency
  injection, generated code, dynamic SQL, environment-expanded launcher paths,
  and external scheduling/runtime state require manual verification.
- Databricks support covers resource jobs/tasks/pipelines and notebook references
  in JSON or a restricted indentation-based YAML subset. Unsupported YAML forms
  produce warnings and generic candidates. No YAML library is installed implicitly.
- Oracle parsing is lightweight. Quoted case-sensitive names, synonyms, search
  paths, and unqualified schemas can need adapter-specific resolution. Canonical
  uppercasing is intentionally documented rather than treated as universal SQL
  identifier semantics.
- Runtime reachability is conservative. File containment can include neighboring
  definitions; static paths do not prove an executable branch runs. One retained
  path per reached node is a bounded explanation, not all possible paths.
- Candidate indexes are reused while new boundary seeds can trigger additional
  bounded traversals. Hop, candidate, node/edge, and total-expansion limits still
  constrain coverage and are reported when reached.
- Catalog inputs are local committed index directories. Detached boundary-JSON
  transport/import, remote clones, and
  service-level catalog scheduling are future extensions.
- Index metadata enumeration is bounded but held in memory; graph traversal and
  exports are SQLite-backed/streamed. Commit tree metadata above the Git output
  limit is rejected. A 1,000-file synthetic benchmark is recorded; billion-line or
  thousand-repository performance has not been benchmarked. No-op runs reuse parses/exports
  but still check Git metadata and stream export hashes for integrity.
- Root commits use an empty-tree comparison. Merge commits use their first parent.
  External binary patches require Git-range analysis; patches without a base cannot
  verify old-side claims. Analysis never applies patches or inspects uncommitted MR
  changes. Indexing supports worktree snapshots separately.
- Text discovery does not perform OCR or extract PDF/Word content. Provide
  provenance-bearing text exports or have the agent inspect available visuals.
- No GitLab API adapter, autonomous remote update, MR approval, test execution,
  or operational job execution is included. Validation reports supplied by users
  remain source evidence, not automatically authenticated CI results.

Future work can add an approved Roslyn helper, complete YAML parsing behind a
narrow optional adapter, snapshot transport, and measured scale benchmarks.
None is required to run the demonstrated local workflow.

Standalone Issue generation returns a draft. Completed semantic delivery requires
the source-bound interpretation and `--require-review` described in the Issue workflow.
MR semantic delivery likewise requires a context-bound review and a decision for
every change. A reviewed result may still have unresolved findings and partial
coverage. Repository IDs and resource namespaces can be configured, but correct
namespace governance remains an operator responsibility. OS locks serialize shared
repository use; immutable multi-revision caches remain a future optimization.
