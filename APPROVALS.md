# Approval State

This file tracks the step-by-step implementation approvals.

## Status meanings

- `PENDING` — not reviewed yet.
- `APPROVED` — approved for implementation.
- `REJECTED` — rejected and must not be implemented in its current form.
- `IMPLEMENTED` — implemented and verified.
- `REWORK` — implemented but requires changes.

## Approval commands

For the current item:

- `1`, `yes`, `ok`, or equivalent → approve.
- `0`, `no`, or equivalent → reject.

Only one pending item is presented for approval at a time.

| ID | Status | Item |
|---|---|---|
| P01 | PENDING | Freeze MVP scope and contracts |
| P02 | PENDING | Define domain model and evidence model |
| P03 | PENDING | Create project skeleton and packaging |
| P04 | PENDING | Configuration and run workspace |
| P05 | PENDING | Issue ingestion |
| P06 | PENDING | Issue Intent Analysis |
| P07 | PENDING | MR/change ingestion |
| P08 | PENDING | Repository index v1 |
| P09 | PENDING | Language adapter framework |
| P10 | PENDING | Changed-symbol mapping |
| P11 | PENDING | Dependency graph v1 |
| P12 | PENDING | Bounded impact traversal |
| P13 | PENDING | Developer interpretation reconstruction |
| P14 | PENDING | Issue ↔ Developer Intent conformance |
| P15 | PENDING | Issue ↔ Implementation conformance |
| P16 | PENDING | Behavioral change analysis |
| P17 | PENDING | Test discovery |
| P18 | PENDING | Test plan generation |
| P19 | PENDING | Report generation |
| P20 | PENDING | Single orchestration CLI |
| P21 | PENDING | SKILL.md orchestration contract |
| P22 | PENDING | Test suite and fixtures |
| P23 | PENDING | Security, privacy, and prompt-injection hardening |
| P24 | PENDING | Observability and reproducibility |
| P25 | PENDING | GitLab read adapter |
| P26 | PENDING | GitLab Issue update preview |
| P27 | PENDING | Optional GitLab write adapter |
| P28 | PENDING | Performance and large-repository hardening |
| P29 | PENDING | Cross-repository design spike |
| P30 | PENDING | v1 release gate |
