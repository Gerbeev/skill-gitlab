# Issue analysis

Source scope: `issue-input`. Sources inspected: 2.

Current template SHA-256: `2c6ad404dfcc48560db2e2f82edb9ffde283ada1ab247c3409011bb28795372f`.

## Evidence and classification

Review status: draft; semantic review required.

- **context / problem**: Negative exposure is currently written to the daily reporting table. (notes.md:4).
- **context / outcome**: Keep negative exposure out of the daily reporting table. (notes.md:7).
- **context / scope**: Validate the daily exposure writer. (notes.md:10).
- **non_goal / non_goal**: Do not change the reporting schedule. (notes.md:13).
- **requirement / requirement**: The writer must reject negative exposure before persistence. (notes.md:16).
- **requirement / requirement**: The writer must continue to persist zero exposure. (notes.md:17).
- **constraint / constraint**: The risk.daily_exposure schema must remain compatible with existing readers. (notes.md:20).
- **assumption / assumption**: Assume the existing reporting job reads the previous successful partition. (notes.md:23).
- **open_question / open_question**: Should rejected records be retained for audit? (notes.md:26).
- **validation / validation**: Run the daily risk task with negative, zero, and positive exposure values. (qa-notes.md:2).
- **validation / validation**: Compare the reporting output with the last successful baseline. (qa-notes.md:3).

## Template population

- **Problem / current state** (context): notes.md:4.
- **Desired outcome** (context): notes.md:7.
- **In scope** (context): notes.md:10.
- **Out of scope / non-goals** (non_goal): notes.md:13.
- **Acceptance Criteria** (requirement): notes.md:16.
- **Acceptance Criteria** (requirement): notes.md:17.
- **Constraints & Dependencies** (constraint): notes.md:20.
- **Assumptions** (assumption): notes.md:23.
- **Open questions** (open_question): notes.md:26.
- **Required tests / scenarios** (validation): qa-notes.md:2.
- **Required tests / scenarios** (validation): qa-notes.md:3.

## Gaps, ambiguity, and readiness

- Missing evidence for template field: Acceptance Criteria.
- Missing evidence for template field: Evidence.
- Missing evidence for template field: Implementation Notes / Decisions.
- Clarify assumption: Assume the existing reporting job reads the previous successful partition. (`notes.md:23`).
- Clarify open_question: Should rejected records be retained for audit? (`notes.md:26`).
- Delivery checklists remain unchecked; no implementation or approval evidence was inferred.
- Readiness is derived only from the current template fields and its checklist.
- Deterministic extraction preserves source wording. A Copilot interpretation pass is required for semantic ambiguity, arbitrary template instructions, and domain-specific readiness judgments.

## Source decisions

- `notes.md`: included provisionally; Awaiting semantic relevance review
- `qa-notes.md`: included provisionally; Awaiting semantic relevance review

## Pending template instruction review

- I1 at template lines 3-19: agent review required.
- I2 at template lines 21-21: agent review required.
- I3 at template lines 25-28: agent review required.
- I4 at template lines 38-40: agent review required.
- I5 at template lines 54-58: agent review required.
- I6 at template lines 68-73: agent review required.
- I7 at template lines 81-84: agent review required.
- I8 at template lines 98-101: agent review required.
- I9 at template lines 109-109: agent review required.
- I10 at template lines 117-122: agent review required.
