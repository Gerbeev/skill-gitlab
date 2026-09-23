# Impact analysis

## Code evidence

- changed (head): `RiskWriter` at `src/RiskWriter.scala:3-9`; confidence 60/100.
- changed (head): `writeExposure` at `src/RiskWriter.scala:4-8`; confidence 60/100.

## Runtime and process scope

### daily-risk

Repository: `repo-a-e19caa7497ec`; type: DATABRICKS_JOB.
Impact: **TRANSITIVELY_AFFECTED**; confidence: 90/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate -> databricks-job://daily-risk

- EXECUTES (reverse): `databricks.yml:8-8`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- CONTAINS (reverse): `databricks.yml:6-6`; detector `config-resources`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.

### daily-risk/calculate

Repository: `repo-a-e19caa7497ec`; type: DATABRICKS_TASK.
Impact: **DIRECTLY_AFFECTED**; confidence: 90/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> databricks-job://daily-risk/task/calculate

- EXECUTES (reverse): `databricks.yml:8-8`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.

### DAILY_RISK_JOB

Repository: `repo-a-e19caa7497ec`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- EXECUTES (reverse): `jobs/risk.jil:4-4`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.

### RISK_EOD_BOX

Repository: `repo-a-e19caa7497ec`; type: AUTOSYS_BOX.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py -> autosys://DAILY_RISK_JOB -> autosys://RISK_EOD_BOX

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- EXECUTES (reverse): `jobs/risk.jil:4-4`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- CONTAINS (reverse): `jobs/risk.jil:3-3`; detector `autosys-jil`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.

### scripts/run_risk.py

Repository: `repo-a-e19caa7497ec`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: file://src/RiskWriter.scala -> file://scripts/run_risk.py

- EXECUTES (reverse): `scripts/run_risk.py:2-2`; detector `path-reference`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.

### REPORT_EOD_BOX

Repository: `repo-b-a173a85c12d0`; type: AUTOSYS_BOX.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> autosys://REPORT_EOD_BOX

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- CONTAINS (reverse): `jobs/report.jil:3-3`; detector `autosys-jil`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.

### REPORT_GENERATION_EOD

Repository: `repo-b-a173a85c12d0`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.

### reporting.generate_report

Repository: `repo-b-a173a85c12d0`; type: DB_PROCEDURE.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.

### scripts/report.sh

Repository: `repo-b-a173a85c12d0`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.

### REGULATORY_EXPORT_JOB

Repository: `repo-c-df7b3ae321d4`; type: AUTOSYS_JOB.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> file://sql/report.sql -> file://scripts/report.sh -> autosys://REPORT_GENERATION_EOD -> [repo-c-df7b3ae321d4] autosys://REPORT_GENERATION_EOD -> autosys://REGULATORY_EXPORT_JOB

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- DEFINES (reverse): `sql/report.sql:1-1`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `scripts/report.sh:3-3`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- EXECUTES (reverse): `jobs/report.jil:4-4`; detector `path-reference`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- ORGANIZATION_LOOKUP (reverse): `jobs/export.jil:3-3`; detector `autosys-jil`; revision `e9dc444bac9be08982603a3b49fb473ec823d35e`.
- DEPENDS_ON (reverse): `jobs/export.jil:3-3`; detector `autosys-jil`; revision `e9dc444bac9be08982603a3b49fb473ec823d35e`.

### scripts/export.ps1

Repository: `repo-c-df7b3ae321d4`; type: SCRIPT.
Impact: **POTENTIALLY_AFFECTED**; confidence: 60/100.
Dependency path connects an MR change to this operational definition.

Path: symbol://src/RiskWriter.scala::writeExposure:4 -> table://RISK/DAILY_EXPOSURE -> [repo-b-a173a85c12d0] table://RISK/DAILY_EXPOSURE -> oracle://REPORTING/GENERATE_REPORT -> table://REPORTING/DAILY_REPORT -> [repo-c-df7b3ae321d4] table://REPORTING/DAILY_REPORT -> file://scripts/export.ps1

- WRITES (forward): `src/RiskWriter.scala:6-6`; detector `sql-lexical`; revision `246367f50f8766885ed3ffd61ef75fc4b593a255`.
- ORGANIZATION_LOOKUP (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- READS (reverse): `sql/report.sql:3-3`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- WRITES (forward): `sql/report.sql:4-4`; detector `sql-lexical`; revision `d7a91854bd32ed57d9a5b8e1886ea8382fe74d10`.
- ORGANIZATION_LOOKUP (reverse): `scripts/export.ps1:2-2`; detector `sql-lexical`; revision `e9dc444bac9be08982603a3b49fb473ec823d35e`.
- READS (reverse): `scripts/export.ps1:2-2`; detector `sql-lexical`; revision `e9dc444bac9be08982603a3b49fb473ec823d35e`.

## Unresolved relationships

- `table://RISK/DAILY_EXPOSURE` in `repo-a-e19caa7497ec` has no local definition.
- `table://RISK/DAILY_EXPOSURE` in `repo-a-e19caa7497ec` has no local definition.
- `table://RISK/DAILY_EXPOSURE` in `repo-b-a173a85c12d0` has no local definition.
- `table://REPORTING/DAILY_REPORT` in `repo-b-a173a85c12d0` has no local definition.
- `autosys://REPORT_GENERATION_EOD` in `repo-c-df7b3ae321d4` has no local definition.
- `table://REPORTING/DAILY_REPORT` in `repo-c-df7b3ae321d4` has no local definition.
