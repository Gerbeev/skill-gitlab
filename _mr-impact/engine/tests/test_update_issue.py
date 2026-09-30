from __future__ import annotations

import json
import unittest
from pathlib import Path

from mr_impact.issue.update import build_issue_update_payload

FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "update-run"


class UpdateIssuePayloadTests(unittest.TestCase):
    def test_build_payload_from_minimal_run(self) -> None:
        payload = build_issue_update_payload(FIXTURE_RUN, generated_at="2020-01-01T00:00:00+00:00")
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["sections"]["observed_implementation"]["present"])
        self.assertEqual(payload["mr_summary"]["runtime_target_count"], 1)
        self.assertEqual(len(payload["runtime_targets"]), 1)


if __name__ == "__main__":
    unittest.main()
