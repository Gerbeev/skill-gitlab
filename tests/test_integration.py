import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from .helpers import ROOT, cli, command, commit, initialize
from mr_impact.analysis import analyze_mr
from mr_impact.catalog import aggregate, lookup
from mr_impact.indexing import build_index
from mr_impact.issues import analyze_issue, update_issue
from mr_impact.models import Limits
from mr_impact.safety import EngineError


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.a, self.b, self.c = (self.work / name for name in ("repo-a", "repo-b", "repo-c"))
        self.base = initialize(self.a, "repo-a")
        initialize(self.b, "repo-b")
        initialize(self.c, "repo-c")
        path = self.a / "src/RiskWriter.scala"
        path.write_text(path.read_text().replace('    val query', '    require(amount >= 0, "Negative exposure")\n    val query'))
        self.head = commit(self.a)
        self.cache, self.out = self.work / "cache", self.work / "analysis"
        self.catalog = self.work / "organization.sqlite"

    def test_full_multirepository_workflow(self):
        issues = self.work / "issue"
        shutil.copytree(ROOT / "tests/fixtures/issue", issues)
        issue_out = self.work / "issue-output"
        result = cli("analyze-issue", "--repo", issues, "--output", issue_out)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(issue_out.iterdir())), 2)
        deep = cli("index-repository", "--repo", self.a, "--cache", self.cache, "--deep")
        self.assertEqual(deep.returncode, 0, deep.stderr)
        directories = []
        for repo in (self.b, self.c):
            indexed = cli("index-repository", "--repo", repo, "--cache", self.cache, "--boundary")
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            directories.append(Path(json.loads(indexed.stdout)["directory"]))
        org = cli("index-organization", "--catalog", self.catalog, "--index", directories[0], "--index", directories[1])
        self.assertEqual(org.returncode, 0, org.stderr)
        reverse = lookup(self.catalog, "table://RISK/DAILY_EXPOSURE")
        self.assertTrue(any(r["role"] == "READS" for r in reverse))
        issue = issue_out / "01-generated-issue.md"
        result = cli("analyze-mr", "--repo", self.a, "--cache", self.cache, "--catalog", self.catalog,
                     "--base", self.base, "--head", self.head, "--issue", issue, "--output", self.out)
        self.assertEqual(result.returncode, 0, result.stderr)
        targets = json.loads((self.out / "runtime-impact.json").read_text())["targets"]
        names = {t["target"] for t in targets}
        self.assertTrue({"daily-risk", "DAILY_RISK_JOB", "REPORT_GENERATION_EOD", "REGULATORY_EXPORT_JOB"} <= names, names)
        report = next(t for t in targets if t["target"] == "REPORT_GENERATION_EOD")
        self.assertTrue(any(s["type"] == "ORGANIZATION_LOOKUP" for s in report["path"]))
        self.assertTrue(any("table://RISK/DAILY_EXPOSURE" in (s["from"], s["to"]) for s in report["path"]))
        self.assertTrue(any(s["evidence"]["file"] == "jobs/report.jil" for s in report["path"]))
        self.assertIn("Evidence path:", (self.out / "04-test-plan.md").read_text())
        mappings = json.loads((self.out / "changed-symbols.json").read_text())["mappings"]
        self.assertTrue(any(m["symbol"]["qualified_name"] == "writeExposure" for m in mappings))
        self.assertEqual({p.name for p in self.out.iterdir()}, {"mr-context.json", "changed-symbols.json", "impact-graph.json", "runtime-impact.json", "test-impact.json",
                         "01-mr-analysis.md", "02-change-context.md", "03-impact-analysis.md", "04-test-plan.md"})
        original = issue.read_bytes()
        result = cli("update-issue", "--issue", issue, "--analysis", self.out, "--output", self.out, "--target", "risk#1427")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(issue.read_bytes(), original)
        preview = (self.out / "05-issue-update.md").read_text()
        self.assertIn("Contract changes: none", preview)
        self.assertIn("No execution results", preview)
        self.assertIn("POTENTIALLY_AFFECTED", preview)
        self.assertIn("Remote write: disabled", preview)

    def test_patch_and_commit_inputs_removed_symbols_and_stale_catalog(self):
        patch = self.work / "change.patch"
        patch.write_text(command(self.a, "diff", "--unified=0", self.base, self.head) + "\n")
        analyze_mr(self.a, self.out, base=self.base, patch=patch, cache=self.cache)
        analyze_mr(self.a, self.out, commit=self.head, cache=self.cache)
        # Deleting a launcher must retain before-change evidence and its job dependency.
        (self.a / "scripts/run_risk.py").unlink()
        removed_head = commit(self.a, "Remove launcher")
        analyze_mr(self.a, self.out, self.head, removed_head, cache=self.cache)
        mappings = json.loads((self.out / "changed-symbols.json").read_text())["mappings"]
        self.assertTrue(any(m["change"] == "removed" and m["symbol"]["qualified_name"] == "run_risk" for m in mappings))
        targets = json.loads((self.out / "runtime-impact.json").read_text())["targets"]
        self.assertTrue(any(t["target"] == "DAILY_RISK_JOB" for t in targets))

    def test_candidate_limit_no_expand_and_no_global_scan(self):
        directories = [Path(build_index(repo, self.cache, "boundary")["directory"]) for repo in (self.b, self.c)]
        aggregate(self.catalog, directories)
        unrelated = self.work / "unrelated"
        initialize(unrelated)
        unrelated_index = Path(build_index(unrelated, self.cache, "boundary")["directory"])
        aggregate(self.catalog, [unrelated_index])
        analyze_mr(self.a, self.out, self.base, cache=self.cache, catalog=self.catalog, limits=Limits(max_candidates=1))
        context = json.loads((self.out / "mr-context.json").read_text())
        self.assertEqual(len(context["candidates"]), 1)
        self.assertEqual(json.loads((unrelated_index / "state.json").read_text())["mode"], "boundary")
        analyze_mr(self.a, self.out, self.base, cache=self.cache, catalog=self.catalog, expand_candidates=False)
        context = json.loads((self.out / "mr-context.json").read_text())
        self.assertTrue(all(not c["expanded"] for c in context["candidates"]))

    def test_mismatching_patch_rejected(self):
        patch = self.work / "wrong.patch"
        patch.write_text('--- a/src/RiskWriter.scala\n+++ b/src/RiskWriter.scala\n@@ -1 +1 @@\n-old\n+not the indexed head\n')
        with self.assertRaises(EngineError):
            analyze_mr(self.a, self.out, patch=patch, cache=self.cache)
