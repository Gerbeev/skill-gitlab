from __future__ import annotations

import unittest
from pathlib import Path

from mr_impact.index.adapters.sql import SqlAdapter

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-repo" / "sql" / "pkg.sql"


class SqlAdapterTests(unittest.TestCase):
    def test_parses_calls_and_package_members(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        symbols, edges, _ = SqlAdapter().analyze("sql/pkg.sql", text)
        self.assertTrue(any(s.kind == "oracle_package_body" for s in symbols))

        by_type_target = {(e.edge_type, e.target) for e in edges}
        self.assertIn(("sql_call", "ledger_pkg.post_entry"), by_type_target)
        self.assertIn(("sql_call", "audit_pkg.log_run"), by_type_target)
        self.assertIn(("sql_call", "payment_staging.flush"), by_type_target)

        routines = [s for s in symbols if s.name == "payment_pkg.run"]
        self.assertTrue(routines, msg="expected payment_pkg.run routine symbol")
        self.assertGreaterEqual(routines[0].line_end, routines[0].line_start + 2)


if __name__ == "__main__":
    unittest.main()
