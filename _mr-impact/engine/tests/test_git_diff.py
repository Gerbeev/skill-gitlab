from __future__ import annotations

import unittest

from mr_impact.git.diff import LineRange, symbols_touched_by_diff


class GitDiffSymbolFilterTests(unittest.TestCase):
    def test_symbols_overlap_hunks(self) -> None:
        ranges = {"scripts/a.py": [LineRange(2, 4)]}
        symbols = [
            {"path": "scripts/a.py", "name": "before", "line_start": 1, "line_end": 1},
            {"path": "scripts/a.py", "name": "inside", "line_start": 3, "line_end": 3},
            {"path": "scripts/a.py", "name": "after", "line_start": 10, "line_end": 12},
        ]
        touched = symbols_touched_by_diff(
            symbols,
            changed_paths={"scripts/a.py"},
            linked_paths=set(),
            line_ranges=ranges,
        )
        names = {s["name"] for s in touched}
        self.assertEqual(names, {"inside"})
        self.assertEqual(touched[0]["diff_match"], "line")

    def test_linked_jil_included_without_hunks(self) -> None:
        symbols = [
            {"path": "jobs/x.jil", "name": "JOB_A", "kind": "autosys_job", "line_start": 1, "line_end": 1},
        ]
        touched = symbols_touched_by_diff(
            symbols,
            changed_paths={"scripts/a.py"},
            linked_paths={"jobs/x.jil"},
            line_ranges={"scripts/a.py": [LineRange(1, 1)]},
        )
        self.assertEqual(len(touched), 1)
        self.assertEqual(touched[0]["diff_match"], "linked_file")


if __name__ == "__main__":
    unittest.main()
