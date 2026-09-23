# Exposure reporting

## Problem
Negative exposure is currently written to the daily reporting table.

## Desired outcome
Keep negative exposure out of the daily reporting table.

## Scope
Validate the daily exposure writer.

## Non-goals
Do not change the reporting schedule.

## Acceptance Criteria
The writer must reject negative exposure before persistence.
The writer must continue to persist zero exposure.

## Constraints
The risk.daily_exposure schema must remain compatible with existing readers.

## Assumptions
Assume the existing reporting job reads the previous successful partition.

## Open questions
Should rejected records be retained for audit?
