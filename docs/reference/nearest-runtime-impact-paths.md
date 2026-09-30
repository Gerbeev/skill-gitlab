# Nearest runtime impact paths (QA-facing dependency chains)

**Status:** Implemented in `mr_impact` (Phase 2b). Gaps: deep .NET↔SQL caller edges depend on index quality; `impact-graph.json` remains diagnostic-only. This document is the authoritative specification for how `/analyze-mr` and `/update-issue` must use the index and graph. Implementation work follows this contract.

**Audience:** QA, release engineers, and developers attaching validation scope to GitLab Issues.

**Related:** [issue-anchored-graph-traversal.md](issue-anchored-graph-traversal.md) (bounded walks), [engine-contract.md](engine-contract.md) (artifacts), [TASK_STATEMENT.md](TASK_STATEMENT.md) (full product spec).

### Постановка (кратко)

При изменении даже одной строки в PL/SQL (или объекта БД) анализ должен по индексу и графу восстановить **ближайшую** цепочку: процедура/пакет → вызывающий код (.NET, другой пакет) → скрипт/команда → **конкретный** AutoSys job и **box**. Не выдавать сотни job’ов из ночного батча. Результат оформляется для Issue (`05-issue-update.md`), чтобы QA понимали, **что перезапустить** для проверки функционала. То же для изменений таблиц и данных, насколько позволяет индекс.

---

## 1. Problem statement

Today, Issue update preview (`/update-issue`) is largely assembled from MR markdown excerpts and coarse `runtime-impact.json` entries. Graph traversal from MR seeds can over-expand (many edges, weak semantics) and often **does not** reconstruct the operational chain a human needs:

- Which **exact** database object or line-level change started the impact.
- Which **PL/SQL package/procedure** (or table/DML) it belongs to.
- Which **callers** (.NET, SQL, other packages) reach that code.
- Which **AutoSys job** (and **box**) is the nearest executable entry point to run in QA.

Listing hundreds of jobs because they share a nightly batch, box, or module is **incorrect** for this product. Those jobs are transitively related by schedule, not by the **shortest evidence-backed path** from **this** change.

---

## 2. Goal

For each meaningful change in a Merge Request, produce **one or a few nearest dependency chains** from the change to **concrete QA actions**:

| Layer (examples) | What to name on the path |
| --- | --- |
| Database | Table, view, package, procedure/function, line range (when indexed) |
| Application | .NET type/method, script path, config key |
| Operations | AutoSys **job**, parent **box**, optional immediate `DEPENDS_ON` consumer |

The output must be suitable to **paste into the Issue** (via `05-issue-update.md` / GitLab apply) so testers know **what to rerun** without re-deriving the estate graph.

---

## 3. Core rules

### 3.1 Seeds come from the diff, not from modules

| Source | Seed |
| --- | --- |
| Changed file + hunk lines | Resolve to **symbols** (`symbols_touched_by_diff`) and **DB objects** when the SQL/PL/SQL adapter indexed them |
| Changed JIL / launcher | Job id + command → script |
| Changed table DDL/DML artifacts | Table/view name + operation kind (`READS_TABLE` / `WRITES_TABLE` when indexed) |

Do **not** seed traversal from “payment module”, “all jobs in `jobs/night/`”, or an entire package file when only one procedure body changed.

### 3.2 Walk **upstream** toward runtime entry

From each seed, follow stored edges **toward callers and schedulers** (same direction policy as [issue-anchored-graph-traversal.md](issue-anchored-graph-traversal.md) §4):

```text
changed line / symbol / table
  → enclosing procedure / package member
  → SQL or app callers (CALLS, sql_call, INVOKES, …)
  → script or binary entry referenced by a job command
  → AUTOSYS_JOB
  → AUTOSYS_BOX (CONTAINS on the path only)
```

Downstream batch siblings and unrelated jobs in the same box are **out of scope** unless a **direct** `DEPENDS_ON` (or equivalent) edge exists from the primary job on the path.

### 3.3 “Nearest” path selection

When multiple paths exist, rank and report:

1. **Shortest** hop count among edges with `confidence ≥` reportable threshold (V1: 0.7 unless documented otherwise).
2. Prefer paths that include an **indexed evidence** pointer (file, line, detector).
3. Prefer a **single primary job** per seed; add **secondary** jobs only when another path is within one hop and has distinct validation (e.g. explicit `DEPENDS_ON` consumer named in AC).

Hard caps (same family as anchored traversal): `max_depth`, `max_nodes`, `max_paths_per_seed` — defaults may be tightened for MR/update (fewer nodes than exploratory graph dumps).

### 3.4 Anti-patterns (forbidden outputs)

| Bad output | Why |
| --- | --- |
| Flat list of 500+ AutoSys jobs | Batch/box/module association ≠ impact from this diff |
| Every job in `BOX_NIGHTLY_*` | Sibling explosion; see §5.2 in issue-anchored doc |
| Only changed file paths, no job | Analyze MR / update incomplete when index links exist |
| Invented edges or jobs | Violates deterministic layer; mark `UNRESOLVED` instead |

---

## 4. Reference scenario (PL/SQL line change)

**Change:** one line inside a procedure body in Oracle PL/SQL.

**Expected chain (illustrative):**

```text
Seed: PKG_PAYMENT.RECONCILE (procedure), lines 120–121 (evidence: diff hunk)
  ← CALLS / sql_call ← OTHER_PKG.RUN_BATCH (if indexed)
  ← CALLS ← PaymentReconciliationService.Run (.NET)
  ← script_path / INVOKES ← scripts/payment_recon.py
  ← COMMAND_REF ← AUTOSYS_JOB PAYMENT_RECON_EOD
  ← CONTAINS ← AUTOSYS_BOX BOX_EOD_PAYMENTS
```

**QA section in Issue update (human-readable):**

| Field | Example |
| --- | --- |
| Primary job | `PAYMENT_RECON_EOD` |
| Box | `BOX_EOD_PAYMENTS` |
| Why | Job command runs script that calls .NET service that executes `PKG_PAYMENT.RECONCILE` |
| Run | `PAYMENT_RECON_EOD` in QA after deploy |
| Verify | Reconciliation output / downstream settlement trigger per AC |

Optional: one **downstream** job only if `SETTLEMENT_EOD` has `DEPENDS_ON → PAYMENT_RECON_EOD` in parsed JIL.

---

## 5. Database object changes

When the MR changes **schema** or **data-access** artifacts (tables, migrations, synonyms, packages):

1. Seed from changed symbols and `READS_TABLE` / `WRITES_TABLE` / `REFERENCES` edges when present.
2. Walk to procedures/views that touch the table, then to app and job layers as in §3.2.
3. If only DML in a repo script is changed, seed the script and resolve invoked SQL objects from the index.

If the index cannot link table → job, report the **longest resolved prefix** and mark the remainder `UNRESOLVED` with a concrete gap (“no edge from `TABLE_X` to callers in index”).

---

## 6. Required artifacts

### 6.1 Produced by `/analyze-mr` (upstream)

The MR run must materialize structured chains **before** update-issue concatenates prose:

| Artifact | Role |
| --- | --- |
| `changed-symbols.json` | Line-accurate seeds (`changed_line_ranges`, `symbols_touched_by_diff`) |
| `impact-graph.json` | **Deprecated for QA listing:** raw bounded edges; not a substitute for nearest paths |
| `runtime-impact.json` | Must evolve to **primary QA targets** + `nearest_paths[]` (see below) |
| `test-impact.json` | Scenarios derived from **primary** targets, not exhaustive job inventory |

### 6.2 Produced by `/update-issue`

| Artifact | Role |
| --- | --- |
| `05-issue-update.md` | Issue-ready sections: implementation summary + **QA / runtime (nearest paths)** + limitations |
| `issue-update.json` | Structured preview for tooling and GitLab apply |

**Mandatory markdown subsection (preview):** `## QA / runtime (nearest paths)` — one block per primary chain: seed → path → job → box → run/verify bullets.

### 6.3 `runtime-impact.json` / `issue-update.json` (target shape)

Planned fields (schema version bump when implemented):

```json
{
  "schema_version": 2,
  "primary_qa_targets": [
    {
      "job": "PAYMENT_RECON_EOD",
      "box": "BOX_EOD_PAYMENTS",
      "impact": "DIRECTLY_AFFECTED",
      "seed": { "kind": "sql_procedure", "name": "PKG_PAYMENT.RECONCILE", "path": "db/pkg_payment.sql", "lines": [120, 121] },
      "path": [
        { "node": "PKG_PAYMENT.RECONCILE", "type": "SQL_PROCEDURE", "evidence": "…" },
        { "node": "PaymentReconciliationService.Run", "type": "CODE_SYMBOL", "evidence": "…" },
        { "node": "scripts/payment_recon.py", "type": "SCRIPT", "evidence": "…" },
        { "node": "PAYMENT_RECON_EOD", "type": "AUTOSYS_JOB", "evidence": "…" },
        { "node": "BOX_EOD_PAYMENTS", "type": "AUTOSYS_BOX", "evidence": "…" }
      ],
      "recommended_run": ["PAYMENT_RECON_EOD"],
      "recommended_verify": ["…"],
      "confidence": 0.92
    }
  ],
  "secondary_qa_targets": [],
  "unresolved": []
}
```

Until the engine emits this shape, skills must **not** claim full nearest-path analysis in prose.

---

## 7. Division of responsibility

| Component | Responsibility |
| --- | --- |
| Index + adapters | Symbols, SQL calls, JIL, script_path, table refs with evidence |
| `analyze-mr` | Diff-accurate seeds; **nearest path** computation; `runtime-impact.json` / `04-test-plan.md` |
| `update-issue` | Promote MR chains into Issue-oriented preview; no new graph logic in the skill layer |
| Copilot skill (agent) | Present paths; never replace missing engine data with guessed jobs |

---

## 8. Acceptance criteria (product)

1. A one-line PL/SQL change yields **at least one** primary job when the repository index connects procedure → app → JIL.
2. Output includes **job + box** when `CONTAINS` exists on the path.
3. Output does **not** include large job lists solely because jobs share a batch or directory.
4. `05-issue-update.md` is attachable to the Issue for QA without reading raw `impact-graph.json`.
5. Table/package DDL changes trace to QA targets when edges exist; otherwise explicit `UNRESOLVED` with prefix path.

---

## 9. Remaining gaps

| Area | Limitation |
| --- | --- |
| `impact-graph.json` | Still populated via bounded `impact_from_seeds` (diagnostic); do not use for QA job lists |
| Cross-layer chains | Index emits `sql_call` from SQL source + string literals (`.cs`/`.py`), `calls` from C#/Python readers; exotic drivers may still yield `unresolved` |
| Direct SQL job | If JIL command points at `sql/pkg.sql`, that job wins as shortest path over app stack — expected |
| Org scale | Cross-repo jobs need boundary catalog + local path prefix |

Delivered in engine Phase 2b — see [DEVELOPMENT_PLAN.md](../DEVELOPMENT_PLAN.md).
