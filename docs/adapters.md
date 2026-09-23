# Extending technology extraction

`src/mr_impact/adapters.py` defines the `Adapter` protocol and ordered registry.
An adapter implements `name`, `accepts(path)`, and `extract(context)`. Multiple
adapters can process one file. Generic extraction is always enabled. Register a
new adapter in `ADAPTERS`, add focused fixtures/tests, and bump `ADAPTER_VERSION`
when existing parse results become incompatible.

Use the `Context` helpers to emit shared `Node`, `Symbol`, `Edge`, and `Evidence`
records. `Context.owner(line)` attaches a relationship to its narrowest known
symbol; otherwise it uses the file. A reference-only node must set
`metadata={"reference_only": True}`. Only actual definitions belong in the
definitions table. Do not mark a referenced API, procedure, or executable as
locally defined just because its identifier was observed.

Every edge has a source, target, type, detector, source range, revision, and
confidence. Preserve technology-specific details in metadata instead of creating
incompatible schemas. Use stable canonical identifiers for shared boundaries.
Do not infer missing namespaces merely to make two entities match.

## Current adapters

| Adapter | Useful extraction | Confidence / limits |
| --- | --- | --- |
| `python-ast` | Classes/functions, ranges, imports, local named call candidates, inheritance candidates | AST declarations exact; lexical call candidates do not resolve runtime rebinding |
| `structural-fallback` | C#, Scala, PowerShell, shell lexical declarations/ranges | Probable; no C# overload/DI binding or Scala compiler semantics |
| `sql-lexical` | Oracle packages/bodies, procedures/functions, tables/views/triggers, reads/writes/call candidates; embedded SQL and Spark table APIs | Strong in SQL; probable for embedded literals; dynamic SQL is a candidate |
| `autosys-jil` | Jobs/boxes, command references, conditions, containment, machine/profile metadata | Exact explicit JIL fields; unresolved runtime paths remain unresolved |
| `config-resources` | XML project/package references; Databricks jobs/tasks/pipelines and notebook references | Structured declarations; YAML subset only |
| `generic` | File kinds, paths, URLs, explicit boundary URIs, namespaces/imports, Maven declarations | Candidate or probable; URLs are not proof of a local endpoint definition |

No adapter executes or imports the analyzed repository. XML DTD/entity
declarations are rejected. The restricted YAML reader does not support anchors,
tags, flow collections, or multiline scalars; it emits a warning and retains
generic candidates. JSON manifests can represent the same supported Databricks
resource shape without those YAML limitations.

Boundary mode skips detailed Python AST and lexical symbol extraction while
retaining operational and data dependencies. Deep mode adds local symbol detail.

## Confidence

`EXACT=100`, `STRONG=90`, `PROBABLE=60`, `CANDIDATE=30`. Use the lowest confidence
justified by the detector. A graph path's confidence cannot exceed its weakest
link. References derived from dynamic code, arbitrary strings, or unresolved
runtime wiring must not become exact semantic facts.

For a future Roslyn adapter, use an approved installed SDK and a separately
audited helper without executing project targets or restore hooks. Keep its
output in the shared records, preserve the fallback when unavailable, and test
overload/binding cases before claiming semantic precision.
