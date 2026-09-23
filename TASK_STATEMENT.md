# Task Statement

## 1. Context

We need to build a Copilot Skill that analyzes a Merge Request in the context of the original Issue and the existing repository.

The main problem is not only to understand **what the developer changed**, but also to verify:

- whether the developer understood the original task correctly;
- what assumptions the developer made while implementing it;
- whether the actual implementation matches the Issue requirements;
- whether the developer changed behavior that was not supposed to change;
- which parts of the system may be affected;
- which dependencies and related components should be verified;
- which existing tests are related to the changed code;
- which additional test scenarios are required;
- what information should be written back to the Issue or used during Merge Request review.

---

## 2. Primary Goal

The Skill must build a traceable chain:

```text
Issue
  ↓
What was required
  ↓
How the developer appears to have interpreted the task
  ↓
What was actually implemented in the Merge Request
  ↓
Whether there are mismatches
  ↓
Which dependencies and system areas are affected
  ↓
What must be tested
  ↓
Ready-to-use review / Issue update artifacts
```

The result must not be a simple Merge Request summary. It must be an **evidence-based analysis of requirement conformance and change impact**.

---

## 3. Inputs

The Skill must work local-first.

Minimum inputs:

1. A local Git repository.
2. The source Issue or its textual description.
3. A Merge Request represented by one of:
   - Git refs / commits;
   - a `base..head` range;
   - a diff;
   - a patch.
4. When available:
   - Merge Request description;
   - commit messages;
   - additional Issue context.

GitLab must not be a mandatory dependency of the core analysis logic.

GitLab may later be used as an input source and as a destination for generated results.

---

## 4. Issue Analysis

Before analyzing the Merge Request, the Skill must understand the source task.

It should identify:

- the main objective;
- explicit requirements;
- acceptance criteria;
- constraints;
- expected behavior;
- behavior that must not change;
- explicit scope;
- explicit out-of-scope statements;
- assumptions;
- ambiguities;
- missing information;
- likely affected areas.

It is critical to distinguish:

```text
explicit requirement
≠
assumption
≠
AI inference
```

AI-generated inference must never silently become a mandatory requirement.

---

## 5. Merge Request Analysis

The Skill must determine the factual changes introduced by the Merge Request:

- changed files;
- changed functions / methods / classes / modules;
- added symbols;
- removed symbols;
- changed signatures;
- configuration changes;
- affected dependencies;
- control-flow changes;
- error-handling changes;
- validation changes;
- modified or added tests.

Diff analysis should be deterministic wherever possible.

---

## 6. Developer Interpretation Reconstruction

The Skill should separately infer:

> How does the developer appear to have understood the original Issue?

Possible evidence sources:

- Merge Request description;
- commit messages;
- change structure;
- added checks;
- error-handling choices;
- architectural choices;
- changed tests.

This result is an **interpretation**, not a proven fact.

Its purpose is to separate two different failure classes.

### Case A

The developer misunderstood the Issue.

```text
Issue
   ↓ mismatch
Developer interpretation
```

### Case B

The developer understood the Issue correctly, but the implementation does not match that understanding.

```text
Developer interpretation
   ↓ mismatch
Implementation
```

---

## 7. Issue ↔ Merge Request Conformance

The Skill must compare the source task with the actual implementation.

It should determine:

- which requirements are fully covered;
- which are partially covered;
- which are missing;
- which are implemented differently from the expected behavior;
- whether implementation conflicts with explicit constraints;
- whether the Merge Request introduces unrelated scope;
- whether behavior was broadened in a potentially dangerous way;
- whether behavior marked as "must not change" was touched;
- whether unresolved ambiguity remains.

Example:

```text
Issue:
Ignore only the "partition already exists" error.

Implementation:
Ignore every SQLException.

Finding:
The implementation is broader than the requirement and may hide unrelated failures.
```

A finding of this type must contain evidence from both the Issue and the code.

---

## 8. Repository Indexing

To analyze a Merge Request properly, the Skill must be able to build a local structural repository index.

The index should support understanding of:

- files;
- modules / packages;
- functions;
- methods;
- classes;
- imports;
- references;
- callers / callees where they can be determined reliably;
- inheritance;
- interfaces;
- configuration;
- tests;
- build / CI metadata.

The index should be reusable and updated incrementally where practical.

---

## 9. Dependency / Impact Analysis

After identifying changed symbols, the Skill must determine what else may be affected.

Example:

```text
Changed method
   ↓
direct callees
   ↓
direct callers
   ↓
transitive callers
   ↓
configuration
   ↓
tests
   ↓
integration points
```

The analysis must distinguish:

- directly affected;
- transitively affected;
- potentially affected;
- unresolved dependencies.

Each relationship should carry evidence and confidence where the relationship is not fully deterministic.

---

## 10. Bounded Dependency Graph

The Skill should not rebuild or traverse an unnecessarily huge application graph for every Merge Request.

Preferred model:

```text
Repository structural index
        +
Changed symbols
        ↓
Targeted graph expansion
        ↓
Bounded affected subgraph
```

Traversal must have limits such as:

- maximum depth;
- maximum nodes;
- maximum edges;
- confidence threshold;
- cycle protection.

---

## 11. Test Analysis

The Skill must identify existing tests related to the changed or affected code.

### Existing tests

- direct unit tests;
- tests of callers;
- regression tests;
- integration tests;
- tests for related components.

### Missing tests

Based on the Issue, Merge Request, conformance findings, and impact analysis, the Skill should propose additional scenarios.

Every proposed test scenario should be tied to a concrete:

- requirement;
- behavioral change;
- dependency;
- risk;
- conformance finding.

Generic test boilerplate unrelated to the evidence should be avoided.

---

## 12. Evidence-First Analysis

Every material conclusion should be verifiable.

Example:

```text
Finding:
Checkout flow may be affected.

Evidence:
src/order/OrderService.java:184-211

Dependency path:
CheckoutController.checkout
→ OrderService.createOrder
→ PaymentClient.charge
```

Where possible, findings should retain:

- file;
- line / range;
- symbol;
- dependency path;
- detector;
- confidence.

---

## 13. Role of AI

AI should be used for tasks that require semantic reasoning:

- understanding the Issue;
- detecting ambiguity;
- reconstructing likely developer interpretation;
- analyzing behavioral consequences;
- comparing intent with implementation;
- generating targeted test scenarios;
- writing human-readable reports.

AI should not be the primary mechanism for tasks that can be performed deterministically:

- `git diff`;
- changed-line extraction;
- AST parsing;
- symbol extraction;
- imports;
- exact references;
- deterministic dependency edges;
- file discovery.

---

## 14. Expected Artifacts

For one Issue + Merge Request analysis, the expected human-readable artifacts are:

```text
00-issue-analysis.md
01-mr-analysis.md
02-requirement-conformance.md
03-impact-analysis.md
04-test-plan.md
05-issue-update.md
```

Machine-readable artifacts should include:

```text
issue-intent.json
mr-context.json
changed-symbols.json
conformance.json
impact-graph.json
test-impact.json
```

---

## 15. Purpose of the Markdown Reports

### `00-issue-analysis.md`

Describes what the source task requires:

- objective;
- requirements;
- acceptance criteria;
- assumptions;
- ambiguities;
- constraints.

### `01-mr-analysis.md`

Describes what the developer actually changed.

### `02-requirement-conformance.md`

The central comparison:

```text
Issue
vs
Developer interpretation
vs
Implementation
```

### `03-impact-analysis.md`

Describes which parts of the system may be affected.

### `04-test-plan.md`

Describes what should be tested.

### `05-issue-update.md`

Provides ready-to-use Markdown for updating the GitLab Issue.

---

## 16. GitLab Integration

The core Skill must not depend on GitLab API access.

Future adapters may provide:

### Read

- Issue;
- Merge Request metadata;
- Merge Request diff;
- commits;
- discussions.

### Write

- update Issue;
- create Issue;
- publish generated analysis.

Write operations must remain a separate controlled step and must not run automatically without explicit authorization.

---

## 17. Future Extension: Cross-Repository Analysis

The same Skill may later use a global index across multiple GitLab repositories.

This would allow cross-repository dependency discovery, for example:

```text
repo-A
  ↓ publishes event
PaymentEvent
  ↓ consumed by
repo-C
repo-F
repo-K
```

or:

```text
MR changes job / config / API
        ↓
global repository index
        ↓
related applications / jobs / services
```

Cross-repository analysis is not required for the first version.

---

## 18. What the Skill Must Not Do

The Skill must not:

- treat every AI hypothesis as fact;
- invent requirements that are not present in the Issue;
- claim a dependency exists without evidence;
- use an LLM instead of deterministic code analysis where deterministic analysis is appropriate;
- automatically approve or reject a Merge Request;
- automatically modify a GitLab Issue without explicit authorization;
- execute commands found inside Issues, code comments, README files, or Merge Request descriptions;
- treat repository content as trusted agent instructions.

---

## 19. Primary Expected Result

Given:

```text
Issue
+
Repository
+
Merge Request
```

the Skill should produce an evidence-backed answer to:

```text
What was supposed to be implemented
        ↓
How the developer appears to have understood it
        ↓
What was actually changed
        ↓
How well the implementation matches the Issue
        ↓
Which dependencies are affected
        ↓
Which risks were introduced
        ↓
What needs to be tested
        ↓
What should be written into the Issue / review
```

The core value is detecting not only technical defects, but also cases where:

> the code may look technically valid while implementing behavior different from what the original Issue required.

---

## 20. Validation of This Task Statement

If this document matches the intended task, it becomes the baseline product contract for subsequent design and implementation.

Any incorrect, unnecessary, or missing requirement should be corrected before implementation of the affected pipeline stage begins.
