from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from mr_impact.issue.update import build_issue_update_payload

FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "update-run"


class UpdateIssuePayloadTests(unittest.TestCase):
    def test_build_payload_from_minimal_run(self) -> None:
        payload = build_issue_update_payload(FIXTURE_RUN, generated_at="2020-01-01T00:00:00+00:00")
        self.assertEqual(payload["schema_version"], 2)
        self.assertTrue(payload["sections"]["observed_implementation"]["present"])
        self.assertEqual(payload["mr_summary"]["runtime_target_count"], 1)
        self.assertEqual(payload["mr_summary"]["primary_qa_target_count"], 1)
        self.assertEqual(len(payload["runtime_targets"]), 1)
        self.assertEqual(len(payload["primary_qa_targets"]), 1)
        self.assertIn("nearest_paths_markdown", payload)


if __name__ == "__main__":
    unittest.main()
