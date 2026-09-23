import unittest

from .helpers import ROOT
from mr_impact.adapters import canonical, parse, simple_yaml


class AdapterTests(unittest.TestCase):
    def test_python_symbols_and_call(self):
        result = parse("a.py", "def callee():\n    return 1\n\ndef caller():\n    return callee()\n")
        self.assertEqual([s.qualified_name for s in result.symbols], ["callee", "caller"])
        self.assertEqual(result.symbols[1].end_line, 5)
        self.assertTrue(any(e.type == "CALLS" and e.evidence.start_line == 5 for e in result.edges))

    def test_csharp_is_structural_not_semantic(self):
        result = parse("Client.cs", (ROOT / "tests/fixtures/repo-b/src/ReportClient.cs").read_text())
        self.assertTrue(any(s.qualified_name == "ReadExposure" for s in result.symbols))
        self.assertTrue(all(s.confidence <= 60 for s in result.symbols))
        self.assertTrue(any("Roslyn" in w for w in result.warnings))

    def test_nuget_xml(self):
        result = parse("App.csproj", '<Project><PackageReference Include="Bank.Core" Version="1" /></Project>')
        self.assertTrue(any(e.target == "nuget://bank.core" and e.type == "USES" for e in result.edges))

    def test_xml_entities_rejected(self):
        result = parse("a.xml", '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///secret">]><x>&e;</x>')
        self.assertTrue(any("rejected" in w for w in result.warnings))

    def test_oracle_definitions_reads_writes_dynamic(self):
        text = "CREATE OR REPLACE PACKAGE BODY risk.pkg AS\nPROCEDURE run AS\nBEGIN\nSELECT * FROM risk.input;\nINSERT INTO risk.output VALUES (1);\nEXECUTE IMMEDIATE query;\nUPDATE risk.dynamic SET x=1;\nEND;"
        result = parse("risk.pkb", text)
        self.assertTrue(any(n.type == "DB_PACKAGE" for n in result.nodes))
        self.assertTrue(any(e.target == "table://RISK/INPUT" and e.type == "READS" for e in result.edges))
        self.assertTrue(any(e.target == "table://RISK/OUTPUT" and e.type == "WRITES" for e in result.edges))
        self.assertTrue(any(e.target == "table://RISK/DYNAMIC" and e.evidence.confidence == 30 for e in result.edges))

    def test_autosys_box_command_and_downstream(self):
        result = parse("jobs.jil", "insert_job: BOX job_type: b\ninsert_job: JOB job_type: c\nbox_name: BOX\ncommand: python scripts/run.py\ncondition: s(UPSTREAM)\n")
        self.assertTrue(any(n.type == "AUTOSYS_BOX" for n in result.nodes))
        self.assertTrue(any(e.source == "autosys://JOB" and e.target == "file://scripts/run.py" and e.type == "EXECUTES" for e in result.edges))
        self.assertTrue(any(e.source == "autosys://JOB" and e.target == "autosys://UPSTREAM" for e in result.edges))

    def test_databricks_yaml_and_json(self):
        text = (ROOT / "tests/fixtures/repo-a/databricks.yml").read_text()
        parsed = parse("databricks.yml", text)
        self.assertTrue(any(n.type == "DATABRICKS_JOB" for n in parsed.nodes))
        self.assertTrue(any(e.target == "file://src/RiskWriter.scala" and e.source.endswith("/calculate") for e in parsed.edges))
        import json
        json_parsed = parse("jobs.json", json.dumps(simple_yaml(text)))
        self.assertEqual({n.key for n in parsed.nodes if n.boundary}, {n.key for n in json_parsed.nodes if n.boundary})

    def test_generic_and_path_escape(self):
        result = parse("unknown.xyz", 'launch scripts/run.sh\nendpoint=https://example.invalid/api\nrun ../../../outside.sh\n')
        self.assertTrue(any(e.target == "file://scripts/run.sh" for e in result.edges))
        self.assertTrue(any(n.type == "API_ENDPOINT" for n in result.nodes))
        self.assertFalse(any("outside" in e.target for e in result.edges))

    def test_boundary_avoids_symbol_extraction(self):
        result = parse("a.py", "def f():\n return 1\n", "boundary")
        self.assertEqual(result.symbols, [])

    def test_canonical_database_identity(self):
        self.assertEqual(canonical("table", '"Risk"."Daily_Exposure"'), "table://RISK/DAILY_EXPOSURE")
