# QA / runtime focus (from BMAD verification-gap pattern)

When presenting MR analysis:

- Every validation scenario needs a **concrete reason** tied to graph evidence (symbol, JIL, script path, config key).
- Prefer **what to run** (job/process name) over file lists alone.
- Classify operational impact: DIRECTLY_AFFECTED, TRANSITIVELY_AFFECTED, POTENTIALLY_AFFECTED, UNRESOLVED.
- Do not invent shell commands unless the repository shows them.
