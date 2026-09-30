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
            (run / "mr-context.json").write_text(
                json.dumps(
                    {"schema_version": 1, "generated_at": "t", "revision": "a..b"},
                ),
                encoding="utf-8",
            )
            (run / "changed-symbols.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "revision": "a..b",
                        "base_sha": "a",
                        "head_sha": "b",
                        "changed_files": [],
                        "symbols_touched_by_diff": [],
                    }
                ),
                encoding="utf-8",
            )
            (run / "impact-graph.json").write_text(
                json.dumps({"schema_version": 1, "edges": []}),
                encoding="utf-8",
            )
            (run / "runtime-impact.json").write_text(
                json.dumps({"schema_version": 2, "primary_qa_targets": [], "targets": []}),
                encoding="utf-8",
            )
            (run / "test-impact.json").write_text(
                json.dumps({"schema_version": 1, "scenarios": []}),
                encoding="utf-8",
            )
            (run / "boundary-hints.json").write_text(
                json.dumps({"hint_count": 0, "hints": []}),
                encoding="utf-8",
            )
            for name in (
                "01-mr-analysis.md",
                "02-change-context.md",
                "03-impact-analysis.md",
                "04-test-plan.md",
            ):
                (run / name).write_text("# x\n", encoding="utf-8")
            self.assertEqual(validate_profile("mr-run", run), [])


if __name__ == "__main__":
    unittest.main()
