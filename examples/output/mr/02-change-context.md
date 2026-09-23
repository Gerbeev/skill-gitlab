# Change context

## Issue associations

- **non_goal**: Do not change the reporting schedule. (`01-generated-issue.md:23`).
  Candidate association: unresolved. No lexical association found; context remains unresolved.
- **requirement**: AC1: The writer must reject negative exposure before persistence. (`01-generated-issue.md:29`).
  Candidate association: src/RiskWriter.scala. Lexical context association; manually verify semantic relevance.
- **requirement**: AC2: The writer must continue to persist zero exposure. (`01-generated-issue.md:30`).
  Candidate association: src/RiskWriter.scala. Lexical context association; manually verify semantic relevance.
- **constraint**: The risk.daily_exposure schema must remain compatible with existing readers. (`01-generated-issue.md:37`).
  Candidate association: src/RiskWriter.scala. Lexical context association; manually verify semantic relevance.

## Completion context

- test_execution: not performed
- MR_review_approval: not available locally
- documentation_changed: False

Scope differences and changes to non-goals require contextual review; lexical associations do not establish agreement or test coverage.
