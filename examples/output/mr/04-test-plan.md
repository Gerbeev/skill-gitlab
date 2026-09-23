# QA validation plan

This is a proposed scope; no tests or operational jobs were executed.

## Code-level tests

- Inspect and run the existing test definition `tests/test_launcher.py` in `repo-a-5ed2cf86b6eb` using its documented runner. Association: indirect; confidence 30/100.

## Process and job execution

### daily-risk (repo-a-5ed2cf86b6eb)

Run or validate DATABRICKS_JOB daily-risk in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 90/100.
Evidence path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate -> databricks-job://daily-risk

- Verify completion and inspect the output of daily-risk against its documented contract.

### daily-risk/calculate (repo-a-5ed2cf86b6eb)

Run or validate DATABRICKS_TASK daily-risk/calculate in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 90/100.
Evidence path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate

- Verify completion and inspect the output of daily-risk/calculate against its documented contract.

### DAILY_RISK_JOB (repo-a-5ed2cf86b6eb)

Run or validate AUTOSYS_JOB DAILY_RISK_JOB in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB

- Verify completion and inspect the output of DAILY_RISK_JOB against its documented contract.

### RISK_EOD_BOX (repo-a-5ed2cf86b6eb)

Run or validate AUTOSYS_BOX RISK_EOD_BOX in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB -> autosys://RISK_EOD_BOX

- Verify completion and inspect the output of RISK_EOD_BOX against its documented contract.

### scripts/run_risk.py (repo-a-5ed2cf86b6eb)

Run or validate SCRIPT scripts/run_risk.py in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: file://src/RiskWriter.scala -> file://scripts/run_risk.py

- Verify completion and inspect the output of scripts/run_risk.py against its documented contract.

### REPORT_EOD_BOX (repo-b-e8f46c259389)

Run or validate AUTOSYS_BOX REPORT_EOD_BOX in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> autosys://REPORT_EOD_BOX

- Verify completion and inspect the output of REPORT_EOD_BOX against its documented contract.
- Compare affected data and downstream consumption for table://RISK/DAILY_EXPOSURE.

### REPORT_GENERATION_EOD (repo-b-e8f46c259389)

Run or validate AUTOSYS_JOB REPORT_GENERATION_EOD in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD

- Verify completion and inspect the output of REPORT_GENERATION_EOD against its documented contract.
- Compare affected data and downstream consumption for table://RISK/DAILY_EXPOSURE.

### reporting.generate_report (repo-b-e8f46c259389)

Run or validate DB_PROCEDURE reporting.generate_report in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT

- Verify completion and inspect the output of reporting.generate_report against its documented contract.
- Compare affected data and downstream consumption for table://RISK/DAILY_EXPOSURE.

### scripts/report.sh (repo-b-e8f46c259389)

Run or validate SCRIPT scripts/report.sh in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh

- Verify completion and inspect the output of scripts/report.sh against its documented contract.
- Compare affected data and downstream consumption for table://RISK/DAILY_EXPOSURE.

### REGULATORY_EXPORT_JOB (repo-c-e118f59fb4bf)

Run or validate AUTOSYS_JOB REGULATORY_EXPORT_JOB in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> [repo-c-e118f59fb4bf] autosys://REPORT_GENERATION_EOD -> autosys://REGULATORY_EXPORT_JOB

- Verify completion and inspect the output of REGULATORY_EXPORT_JOB against its documented contract.
- Compare affected data and downstream consumption for table://RISK/DAILY_EXPOSURE.
- Verify the recorded scheduler dependency and downstream start/completion behavior.

### scripts/export.ps1 (repo-c-e118f59fb4bf)

Run or validate SCRIPT scripts/export.ps1 in the approved QA environment.
Reason: Dependency path connects an MR change to this operational definition. Confidence: 60/100.
Evidence path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> table://REPORTING/DAILY_REPORT -> [repo-c-e118f59fb4bf] table://REPORTING/DAILY_REPORT -> file://scripts/export.ps1

- Verify completion and inspect the output of scripts/export.ps1 against its documented contract.
- Compare affected data and downstream consumption for table://REPORTING/DAILY_REPORT, table://RISK/DAILY_EXPOSURE.

## Integration, regression, and negative paths

- At `src/RiskWriter.scala` hunk 1: Exercise the changed control flow / validation path and its failure/boundary case; compare results with the agreed contract. Reason: Changed lines contain constructs associated with this behavior; runtime semantics are not proven.
- At `src/RiskWriter.scala` hunk 1: Run daily-risk with amounts -1, 0, and 1. Verify rejection occurs before persistence for -1, and the guard permits 0 and 1. Inspect downstream reporting for the affected partition. Reason: The writer now checks that amount is nonnegative before constructing the INSERT statement.
- Validate the explicit criterion: AC1: The writer must reject negative exposure before persistence. Source: `01-generated-issue.md:29`. Candidate files: src/RiskWriter.scala.
- Validate the explicit criterion: AC2: The writer must continue to persist zero exposure. Source: `01-generated-issue.md:30`. Candidate files: src/RiskWriter.scala.
