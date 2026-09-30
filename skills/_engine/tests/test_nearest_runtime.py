from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from mr_impact.graph.nearest_runtime import compute_primary_qa_targets


class NearestRuntimeTests(unittest.TestCase):
    def test_script_change_resolves_job_and_box(self) -> None:
        edges = [
            {
                "from_file": "jobs/payment.jil",
                "target": "scripts/payment_recon.py",
                "type": "script_path",
                "confidence": "high",
                "evidence": "command",
                "line_start": 4,
                "line_end": 4,
            },
            {
                "from_file": "jobs/payment.jil",
                "target": "EOD_BOX",
                "type": "box_parent",
                "confidence": "high",
                "evidence": "box_name",
                "line_start": 5,
                "line_end": 5,
            },
        ]
        symbols = [
            {"path": "jobs/payment.jil", "name": "PAYMENT_RECON_EOD", "kind": "autosys_job", "line_start": 1, "line_end": 1},
        ]
        touched = [
            {
                "path": "scripts/payment_recon.py",
                "name": "reconcile_payments",
                "kind": "function",
                "line_start": 1,
                "line_end": 2,
                "diff_match": "line",
            }
        ]
        primary, legacy, unresolved = compute_primary_qa_targets(
            edges, symbols, touched, {"scripts/payment_recon.py"}
        )
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0]["job"], "PAYMENT_RECON_EOD")
        self.assertEqual(primary[0]["box"], "EOD_BOX")
        self.assertFalse(unresolved)
        self.assertEqual(legacy[0]["job_or_process"], "PAYMENT_RECON_EOD")

    def test_sql_file_change_via_jil_command(self) -> None:
        edges = [
            {
                "from_file": "jobs/payment.jil",
                "target": "sql/pkg.sql",
                "type": "script_path",
                "confidence": "medium",
                "evidence": "command",
                "line_start": 15,
                "line_end": 15,
            },
            {
                "from_file": "jobs/payment.jil",
                "target": "EOD_BOX",
                "type": "box_parent",
                "confidence": "high",
                "evidence": "box_name",
                "line_start": 16,
                "line_end": 16,
            },
        ]
        symbols = [
            {"path": "jobs/payment.jil", "name": "PAYMENT_SQL_EOD", "kind": "autosys_job", "line_start": 13, "line_end": 13},
            {"path": "sql/pkg.sql", "name": "payment_pkg", "kind": "oracle_package_body", "line_start": 1, "line_end": 1},
        ]
        touched: list[dict] = []
        primary, _, unresolved = compute_primary_qa_targets(
            edges, symbols, touched, {"sql/pkg.sql"}
        )
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0]["job"], "PAYMENT_SQL_EOD")
        self.assertFalse(unresolved)


if __name__ == "__main__":
    unittest.main()
