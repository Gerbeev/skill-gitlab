# Issue

## Problem & Outcome

**Problem / current state**

- Negative exposure is currently written to the daily reporting table.

**Desired outcome**

- Keep negative exposure out of the daily reporting table.

---

## Scope

**In scope**

- Validate the daily exposure writer.

**Out of scope / non-goals**

- Do not change the reporting schedule.

---

## Acceptance Criteria

- [ ] AC1: The writer must reject negative exposure before persistence.
- [ ] AC2: The writer must continue to persist zero exposure.
- [ ] AC3: Unresolved: no supporting evidence in the selected sources.

---

## Constraints & Dependencies

- The risk.daily_exposure schema must remain compatible with existing readers.

---

## Assumptions / Open Questions

**Assumptions**

- Assume the existing reporting job reads the previous successful partition.

**Open questions**

- Should rejected records be retained for audit?

---

## Validation

**Required tests / scenarios**

- Run the daily risk task with negative, zero, and positive exposure values.
- Compare the reporting output with the last successful baseline.

**Evidence**

- Unresolved: no supporting evidence in the selected sources.

---

## Implementation Notes / Decisions

- Unresolved: no supporting evidence in the selected sources.

---

## Delivery Checklist

### Ready (DoR)

- [ ] Problem, desired outcome, and scope are clear.
- [ ] Acceptance Criteria are testable and understood.
- [ ] Relevant dependencies and constraints are known, or explicitly recorded as unknown.
- [ ] Required GitLab metadata, labels, estimate, and target release/iteration are set where applicable.

### Done (DoD)

- [ ] Final implementation matches the Issue and its Acceptance Criteria, or the Issue was updated to the agreed final behavior.
- [ ] Required tests pass and evidence is linked.
- [ ] Related MR(s) are linked, reviewed, approved, and merged where applicable.
- [ ] Relevant documentation is updated where applicable.
- [ ] Developer/runtime validation is complete where applicable, with no known critical blocker remaining.
