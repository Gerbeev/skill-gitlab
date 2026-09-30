from __future__ import annotations

import unittest

from mr_impact.mr.symbols_from_diff import (
    filter_linked_job_symbols,
    impact_seeds_from_diff,
    jil_sources_for_changed_paths,
)


class SymbolsFromDiffTests(unittest.TestCase):
    def test_jil_sources_from_script_path_edges(self) -> None:
        edges = [
            {
                "from_file": "jobs/pay.jil",
                "target": "scripts/payment_recon.py",
                "type": "script_path",
            }
        ]
        sources = jil_sources_for_changed_paths({"scripts/payment_recon.py"}, edges)
        self.assertEqual(sources, {"jobs/pay.jil"})

    def test_impact_seeds_include_paths_and_symbol_names(self) -> None:
        seeds = impact_seeds_from_diff(
            {"sql/pkg.sql"},
            [{"name": "PKG.FOO", "path": "sql/pkg.sql"}],
        )
        self.assertIn("sql/pkg.sql", seeds)
        self.assertIn("pkg.sql", seeds)
        self.assertIn("PKG.FOO", seeds)

    def test_filter_keeps_non_linked_symbols(self) -> None:
        symbols = [{"name": "X", "kind": "sql_routine", "diff_match": "line"}]
        kept = filter_linked_job_symbols(symbols, set(), [])
        self.assertEqual(kept, symbols)


if __name__ == "__main__":
    unittest.main()
