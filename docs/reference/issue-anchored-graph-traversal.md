# Issue-anchored dependency and node search

This document defines how **related nodes** and **dependencies** are discovered when you run **`/analyze-issue`**, and how that differs from **`/analyze-mr`**. It is a design contract for the engine and skills so graph search stays **bounded**, **evidence-backed**, and **path-specific**—especially for large **AutoSys** job trees.

**Status:** Specification for implementation (V1). The shared engine must follow this policy; skills must not instruct open-ended “find everything related to module X” graph scans.

---

## 1. What `/analyze-issue` does vs does not do

| Responsibility | Graph usage |
| --- | --- |
| **Primary** | Parse Issue input scope; produce `00-issue-analysis.md` and `01-generated-issue.md` from the template. |
| **Optional (dependency context)** | When a **repository index already exists**, enrich `00-issue-analysis.md` with **anchored** dependency/runtime paths tied to **explicit** Issue mentions—not a full impact analysis. |
| **Not in scope** | Replace `/analyze-mr`; grade implementation; unbounded repository scan; “all jobs in a module.” |

If the user only analyzes Issue text and no index exists, the skill reports that **dependency paths require `/create_index` first** (and `/create_graph` when JSON traversal is needed) and lists **named** dependencies from the Issue prose only (no invented graph edges).

---

## 2. Core rule: anchors, not filters

Graph expansion always starts from **anchors** (seeds), never from broad filters.

| Allowed anchor sources (Issue analysis) | Not allowed as expansion seeds |
| --- | --- |
| Job name explicitly in Issue/notes (`PAYMENT_RECON_EOD`) | “All AutoSys jobs in payment module” |
| Script path or command line quoted in Issue (`scripts/payment_recon.py`) | “Everything under `jobs/*.jil`” |
| Class/method/SQL object named in AC or constraints | “All jobs that reference assembly `Payment.dll`” |
| File path named in Issue | Entire module/package without a named symbol or job |
| Table/API id from Issue or boundary catalog **only when named** | Reverse lookup from catalog without a local graph edge from an anchor |

**Anchors** are extracted deterministically (regex + index symbol lookup for exact names). The LLM may **summarize** paths in `00-issue-analysis.md` but must **not** add graph nodes that are not reachable from anchors under the rules below.

Optional machine output: `issue-intent.json` with an `anchors[]` list (`type`, `name`, `source_file`, `line_in_issue`, `evidence`).

---

## 3. Prerequisites

```text
/create_index  (then /create_graph when graph JSON is needed)
        ↓
 persisted graph under .repository-analysis/graph/
        ↓
/analyze-issue  (may call query-graph with anchors)
```

Without an index, Issue analysis remains **text-only** for dependencies.

---

## 4. Traversal algorithm (bounded subgraph)

All graph walks use the same **anchored BFS/DFS** with hard limits (see [TASK_STATEMENT.md](TASK_STATEMENT.md) §4 Phase 6):

| Parameter | Typical V1 default | Purpose |
| --- | --- | --- |
| `max_depth` | 8–12 operational hops; fewer for `POTENTIALLY_AFFECTED` | Prevent crossing entire scheduler estate |
| `max_nodes` | 200–500 per anchor set | Cap result size |
| `max_edges` | 2× `max_nodes` | Cap work |
| `min_confidence` | 0.7 for “reportable”; below → `UNRESOLVED` | Drop weak heuristic edges |
| `edge_type_filter` | Per phase (see §5) | Avoid wrong edge semantics |
| `cycle_detection` | on | No infinite box/job loops |

**Direction policy**

| Starting anchor type | Allowed directions | Edge types (examples) |
| --- | --- | --- |
| Code symbol (class/method) | **Upstream** toward runtime entry | `CALLS` ← callers, `SCRIPT_INVOKES`, `CONFIGURES`, `REFERENCES` |
| Script path | Toward **job definitions** that invoke it | `JOB_LAUNCHES`, `COMMAND_REF`, file path match |
| Named AutoSys job | **Along declared dependencies only** | `DEPENDS_ON`, `CONTAINS` (parent box), command → script → code |
| SQL/PL/SQL object | To readers/writers and named jobs if linked | `READS_TABLE`, `WRITES_TABLE`, `REFERENCES` (when indexed) |

**Forbidden traversal patterns**

- **Module-wide expansion:** “all nodes tagged with module `payment`” or “all jobs in repo under `jobs/payment/`” unless the Issue anchor is exactly that **folder path** and the user asked for inventory (still capped by `max_nodes`).
- **Sibling explosion:** from job `A` inside box `B`, do **not** include every other job in box `B` unless there is a **direct** `DEPENDS_ON` / `CONTAINS` path from the anchor to that sibling.
- **Downstream fan-out from catalog only:** boundary catalog may suggest **other repositories**; it does not add nodes inside the current repo without a local edge path from an anchor.

Every reported node must include a **`path[]`** from anchor to target (node ids + edge types + evidence).

---

## 5. AutoSys / JIL (large job trees)

### 5.1 What indexing stores (conceptual)

During `/create_index` (and graph export via `/create_graph` when needed), the JIL adapter records **nodes** and **edges**, for example:

```text
AUTOSYS_JOB     PAYMENT_RECON_EOD
AUTOSYS_BOX     BOX_EOD_PAYMENTS
SCRIPT          scripts/payment_recon.py
CODE_SYMBOL     PaymentReconciliationService.run
```

```text
PAYMENT_RECON_EOD  --COMMAND_REF-->  scripts/payment_recon.py
scripts/payment_recon.py  --INVOKES-->  PaymentReconciliationService.run
BOX_EOD_PAYMENTS  --CONTAINS-->  PAYMENT_RECON_EOD
SETTLEMENT_EOD    --DEPENDS_ON-->  PAYMENT_RECON_EOD   (downstream consumer)
```

Boxes, conditions, and upstream/downstream job names come from **parsed JIL**, not from guessing module ownership.

### 5.2 Issue says: “change `PaymentReconciliationService.run`”

**Correct** anchored traversal:

```text
Anchor: CODE_SYMBOL PaymentReconciliationService.run
  ← SCRIPT scripts/payment_recon.py        (evidence: line in script)
  ← JOB PAYMENT_RECON_EOD                  (evidence: command in JIL)
  ← BOX BOX_EOD_PAYMENTS                   (CONTAINS, parent only on path)
  → JOB SETTLEMENT_EOD                     (only if DEPENDS_ON edge exists from PAYMENT_RECON_EOD)
```

**Incorrect** (must not happen):

```text
Filter: module = Payment
  → all 400 jobs in jobs/payment/*.jil
  → all jobs in BOX_EOD_PAYMENTS siblings
```

### 5.3 Issue names a job: `PAYMENT_RECON_EOD`

Anchors = that job id only (exact match in index).

- Walk **up:** box parents via `CONTAINS` (path to root box on this branch only).
- Walk **down:** `DEPENDS_ON` / condition-linked jobs **one hop at a time** within `max_depth`.
- Walk **in:** command → script → symbols **for that job’s command line only**.

Do not attach unrelated jobs that share a filename prefix or directory.

### 5.4 Reporting in `00-issue-analysis.md`

Use a subsection **Dependency context (anchored)**:

- List anchors found in Issue text.
- For each anchor, show **at most** the bounded paths above.
- Mark paths truncated by limits: `… truncated at depth N`.
- Separate **explicit Issue requirements** from **graph-derived context** (latter is not new AC).

---

## 6. Relationship to `/analyze-mr`

| Aspect | `/analyze-issue` | `/analyze-mr` |
| --- | --- | --- |
| **Seeds** | Names/paths **explicit in Issue material** | **Changed symbols** from deterministic diff |
| **Goal** | Clarify scope, risks, validation context for planning | QA/runtime scope for **this** change |
| **Graph API** | `query-graph --anchors-from-issue …` (conceptual) | `analyze-mr` impact subgraph from `changed-symbols.json` |
| **AutoSys** | Paths from Issue-mentioned jobs/code only | Paths from **changed** code/scripts to jobs |

Issue anchors and MR changed-symbol sets may **overlap**; MR analysis does not re-run Issue-wide expansion unless an anchor is still relevant to changed files.

---

## 7. Engine surface (planned)

```bash
# After index exists — inspect paths for Issue planning (no MR required)
mr-impact query-graph \
  --repo . \
  --anchors issue-anchors.json \
  --max-depth 10 \
  --max-nodes 300 \
  --min-confidence 0.7 \
  --edge-types CALLS,SCRIPT_INVOKES,JOB_LAUNCHES,CONTAINS,DEPENDS_ON,CONFIGURES \
  --output .repository-analysis/run/issue-graph.json
```

`analyze-issue` may invoke this internally when anchors are non-empty and index freshness checks pass.

**Freshness:** if index commit ≠ current `HEAD`, skill should recommend `/create_index` (and `/create_graph` if graph paths are needed) before trusting paths.

---

## 8. Examples (good vs bad)

### Good

Issue note: *“Update PAYMENT_RECON_EOD; verify SETTLEMENT_EOD still triggers.”*

Anchors: `PAYMENT_RECON_EOD`, `SETTLEMENT_EOD`.

Report:

- Path `PAYMENT_RECON_EOD → … → PaymentReconciliationService.run` (if indexed).
- Path `PAYMENT_RECON_EOD → DEPENDS_ON → SETTLEMENT_EOD` **only if** edge exists in JIL.

### Bad (reject / do not implement)

Issue note: *“Payment module reconciliation area.”*

- Do **not** return every job under `jobs/payment/`.
- Do return: “No exact job or symbol anchor; add job name or script path, or run MR analysis after implementation.”

---

## 9. Skill instructions (Copilot)

In `/analyze-issue` workflow steps, the agent must:

1. Extract anchors from Issue input **before** any graph call.
2. Refuse unbounded prompts (“list all AutoSys jobs for this service”).
3. Call the engine graph query with anchors + limits; present **paths**, not flat job lists.
4. Never treat graph-derived jobs as Acceptance Criteria unless the Issue already states them.

---

## 10. Related documents

- [TASK_STATEMENT.md](TASK_STATEMENT.md) — bounded graph traversal (MR Phase 6–7)
- [V1_SCOPE.md](V1_SCOPE.md) — JIL adapter priority
- [GLOSSARY.md](GLOSSARY.md) — anchor, runtime target, evidence
- [boundary-catalog.example.json](boundary-catalog.example.json) — cross-repo hints only with local paths
