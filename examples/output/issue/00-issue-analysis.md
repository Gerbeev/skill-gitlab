# Issue analysis

Source scope: `issue-input`. Sources inspected: 2.

Current template SHA-256: `2c6ad404dfcc48560db2e2f82edb9ffde283ada1ab247c3409011bb28795372f`.

## Evidence and classification

- **context / problem**: Negative exposure is currently written to the daily reporting table. (`notes.md:4`).
- **context / outcome**: Keep negative exposure out of the daily reporting table. (`notes.md:7`).
- **context / scope**: Validate the daily exposure writer. (`notes.md:10`).
- **non_goal / non_goal**: Do not change the reporting schedule. (`notes.md:13`).
- **requirement / requirement**: The writer must reject negative exposure before persistence. (`notes.md:16`).
- **requirement / requirement**: The writer must continue to persist zero exposure. (`notes.md:17`).
- **constraint / constraint**: The risk.daily_exposure schema must remain compatible with existing readers. (`notes.md:20`).
- **assumption / assumption**: Assume the existing reporting job reads the previous successful partition. (`notes.md:23`).
- **open_question / open_question**: Should rejected records be retained for audit? (`notes.md:26`).
- **validation / validation**: Run the daily risk task with negative, zero, and positive exposure values. (`qa-notes.md:2`).
- **validation / validation**: Compare the reporting output with the last successful baseline. (`qa-notes.md:3`).

## Template population

- **Problem / current state** (context): Negative exposure is currently written to the daily reporting table. Evidence: notes.md:4.
- **Desired outcome** (context): Keep negative exposure out of the daily reporting table. Evidence: notes.md:7.
- **In scope** (context): Validate the daily exposure writer. Evidence: notes.md:10.
- **Out of scope / non-goals** (non_goal): Do not change the reporting schedule. Evidence: notes.md:13.
- **Acceptance Criteria** (requirement): The writer must reject negative exposure before persistence. Evidence: notes.md:16.
- **Acceptance Criteria** (requirement): The writer must continue to persist zero exposure. Evidence: notes.md:17.
- **Constraints & Dependencies** (constraint): The risk.daily_exposure schema must remain compatible with existing readers. Evidence: notes.md:20.
- **Assumptions** (assumption): Assume the existing reporting job reads the previous successful partition. Evidence: notes.md:23.
- **Open questions** (open_question): Should rejected records be retained for audit? Evidence: notes.md:26.
- **Required tests / scenarios** (validation): Run the daily risk task with negative, zero, and positive exposure values. Evidence: qa-notes.md:2.
- **Required tests / scenarios** (validation): Compare the reporting output with the last successful baseline. Evidence: qa-notes.md:3.

## Gaps, ambiguity, and readiness

- Missing evidence for template field: Acceptance Criteria.
- Missing evidence for template field: Evidence.
- Missing evidence for template field: Implementation Notes / Decisions.
- Clarify assumption: Assume the existing reporting job reads the previous successful partition. (`notes.md:23`).
- Clarify open_question: Should rejected records be retained for audit? (`notes.md:26`).
- Delivery checklists remain unchecked; no implementation or approval evidence was inferred.
- Readiness is derived only from the current template fields and its checklist.
- Deterministic extraction preserves source wording. A Copilot interpretation pass is required for semantic ambiguity, arbitrary template instructions, and domain-specific readiness judgments.

## Sources

- `notes.md`
- `qa-notes.md`
