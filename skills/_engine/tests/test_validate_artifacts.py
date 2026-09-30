from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ENGINE_SRC))

from mr_impact.artifacts.validate import validate_issue_run, validate_mr_run, validate_profile


class ValidateArtifactsTests(unittest.TestCase):
    def test_issue_run_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_issue_run(Path(tmp))
            self.assertTrue(any("00-issue-analysis.md" in e for e in errors))

    def test_issue_run_minimal_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "00-issue-analysis.md").write_text("# analysis\n", encoding="utf-8")
            (run / "01-generated-issue.md").write_text("## Problem & Outcome\n", encoding="utf-8")
            (run / "issue-intent.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "generated_at": "t",
                        "input_files": [],
                        "gaps": [],
                        "anchors": [],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(validate_issue_run(run), [])

    def test_mr_run_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            errors = validate_mr_run(run)
            self.assertGreater(len(errors), 0)
            for name in (
                "mr-context.json",
                "changed-symbols.json",
                "impact-graph.json",
                "runtime-impact.json",
                "test-impact.json",
                "01-mr-analysis.md",
                "02-change-context.md",
                "03-impact-analysis.md",
                "04-test-plan.md",
                "boundary-hints.json",
            ):
                (run / name).write_text("{}" if name.endswith(".json") else "# x\n", encoding="utf-8")
            self.assertEqual(validate_profile("mr-run", run), [])


if __name__ == "__main__":
    unittest.main()
