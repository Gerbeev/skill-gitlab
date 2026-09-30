from __future__ import annotations

import unittest
from pathlib import Path

from mr_impact.index.adapters.jil import JilAdapter

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-repo" / "jobs" / "payment.jil"


class JilAdapterTests(unittest.TestCase):
    def test_parses_condition_and_box_edges(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        symbols, edges, notes = JilAdapter().analyze("jobs/payment.jil", text)
        job_names = {s.name for s in symbols if s.kind == "autosys_job"}
        self.assertIn("PAYMENT_RECON_EOD", job_names)
        self.assertIn("FUNDING_CUTOFF_EOD", job_names)

        by_type = {(e.edge_type, e.target) for e in edges}
        self.assertIn(("condition_dependency", "FUNDING_CUTOFF_EOD"), by_type)
        self.assertIn(("condition_dependency", "LEDGER_CLOSE_EOD"), by_type)
        self.assertIn(("box_parent", "EOD_BOX"), by_type)
        self.assertTrue(any(e.edge_type == "script_path" and "payment_recon" in e.target for e in edges))
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
