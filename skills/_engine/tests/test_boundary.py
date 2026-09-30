from __future__ import annotations

import unittest

from mr_impact.mr.boundary import match_boundary_hints


class BoundaryMatchTests(unittest.TestCase):
    def test_matches_autosys_job_from_runtime(self) -> None:
        catalog = {
            "version": 1,
            "entities": [
                {
                    "id": "job://AUTOSYS/PAYMENT_RECON_EOD",
                    "kind": "autosys_job",
                    "summary": "EOD recon",
                    "repos": [{"path": "payment-platform", "role": "definition", "confidence": 1.0}],
                }
            ],
        }
        payload = match_boundary_hints(
            catalog,
            changed_paths={"scripts/payment_recon.py"},
            symbols=[],
            runtime_targets=[{"job_or_process": "PAYMENT_RECON_EOD"}],
        )
        self.assertEqual(payload["hint_count"], 1)
        self.assertEqual(payload["hints"][0]["entity_id"], "job://AUTOSYS/PAYMENT_RECON_EOD")


if __name__ == "__main__":
    unittest.main()
