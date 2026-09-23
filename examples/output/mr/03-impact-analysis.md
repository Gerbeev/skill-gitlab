# Impact analysis

## Code evidence

- changed (base): `RiskWriter` at `src/RiskWriter.scala:3-8`; confidence 60/100.
- changed (base): `writeExposure` at `src/RiskWriter.scala:4-7`; confidence 60/100.
- changed (head): `RiskWriter` at `src/RiskWriter.scala:3-9`; confidence 60/100.
- changed (head): `writeExposure` at `src/RiskWriter.scala:4-8`; confidence 60/100.

## Runtime and process scope

### daily-risk

Repository: `repo-a-5ed2cf86b6eb`; type: DATABRICKS_JOB.
Impact: **TRANSITIVELY_AFFECTED**; confidence: 90/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate -> databricks-job://daily-risk

- EXECUTES (reverse): `databricks.yml:8-8`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- CONTAINS (reverse): `databricks.yml:6-6`; detector `config-resources`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.

### daily-risk/calculate

Repository: `repo-a-5ed2cf86b6eb`; type: DATABRICKS_TASK.
Impact: **DIRECTLY_AFFECTED**; confidence: 90/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate

- EXECUTES (reverse): `databricks.yml:8-8`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.

### DAILY_RISK_JOB

Repository: `repo-a-5ed2cf86b6eb`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- EXECUTES (reverse): `jobs/risk.jil:4-4`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.

### RISK_EOD_BOX

Repository: `repo-a-5ed2cf86b6eb`; type: AUTOSYS_BOX.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB -> autosys://RISK_EOD_BOX

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- EXECUTES (reverse): `jobs/risk.jil:4-4`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- CONTAINS (reverse): `jobs/risk.jil:3-3`; detector `autosys-jil`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.

### scripts/run_risk.py

Repository: `repo-a-5ed2cf86b6eb`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.

### REPORT_EOD_BOX

Repository: `repo-b-e8f46c259389`; type: AUTOSYS_BOX.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> autosys://REPORT_EOD_BOX

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- CONTAINS (reverse): `jobs/report.jil:3-3`; detector `autosys-jil`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.

### REPORT_GENERATION_EOD

Repository: `repo-b-e8f46c259389`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.

### reporting.generate_report

Repository: `repo-b-e8f46c259389`; type: DB_PROCEDURE.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.

### scripts/report.sh

Repository: `repo-b-e8f46c259389`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.

### REGULATORY_EXPORT_JOB

Repository: `repo-c-e118f59fb4bf`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> [repo-c-e118f59fb4bf] autosys://REPORT_GENERATION_EOD -> autosys://REGULATORY_EXPORT_JOB

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- ORGANIZATION_LOOKUP (reverse): `jobs/export.jil:3-3`; detector `autosys-jil`; revision `c7fb9d383730f1e52bfe7a550743dc83a5a21c47`.
- DEPENDS_ON (reverse): `jobs/export.jil:3-3`; detector `autosys-jil`; revision `c7fb9d383730f1e52bfe7a550743dc83a5a21c47`.

### scripts/export.ps1

Repository: `repo-c-e118f59fb4bf`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-e8f46c259389] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> table://REPORTING/DAILY_REPORT -> [repo-c-e118f59fb4bf] table://REPORTING/DAILY_REPORT -> file://scripts/export.ps1

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `1e2e8bcf21df73dbd8752adb47b4cdba70479131`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- WRITES (forward): `sql/report.sql:4-4`; detector `sql-lexical`; revision `a2ba0280f078321c5dce237344fdd521bd9ff72b`.
- ORGANIZATION_LOOKUP (reverse): `scripts/export.ps1:2-2`; detector `sql-lexical`; revision `c7fb9d383730f1e52bfe7a550743dc83a5a21c47`.
- READS (reverse): `scripts/export.ps1:2-2`; detector `sql-lexical`; revision `c7fb9d383730f1e52bfe7a550743dc83a5a21c47`.

## Unresolved relationships

- `table://RISK/DAILY_EXPOSURE` in `repo-a-5ed2cf86b6eb` has no local definition.
- `table://RISK/DAILY_EXPOSURE` in `repo-a-5ed2cf86b6eb` has no local definition.
- `table://RISK/DAILY_EXPOSURE` in `repo-b-e8f46c259389` has no local definition.
- `table://REPORTING/DAILY_REPORT` in `repo-b-e8f46c259389` has no local definition.
- `autosys://REPORT_GENERATION_EOD` in `repo-c-e118f59fb4bf` has no local definition.
- `table://REPORTING/DAILY_REPORT` in `repo-c-e118f59fb4bf` has no local definition.
