from __future__ import annotations

import unittest

from mr_impact.git.diff import ChangedFile
from mr_impact.mr.reports import index_stale_note, render_mr_analysis, render_test_plan
from mr_impact.mr.run_context import MrRunContext


class MrReportsTests(unittest.TestCase):
    def _minimal_ctx(self, **overrides) -> MrRunContext:
        base = {
            "now": "2026-01-01T00:00:00+00:00",
            "revision": "main..HEAD",
            "base_sha": "aaa" * 10,
            "head_sha": "bbb" * 10,
            "changed": [ChangedFile(status="M", path="sql/a.sql")],
            "symbols": [],
            "indexed_head": "ccc" * 10,
            "repo_head": "ddd" * 10,
            "index_stale": False,
            "partial_refresh": None,
            "issue_dir": None,
            "graph_json_present": False,
            "boundary_catalog_present": False,
            "seeds": set(),
            "primary_qa": [],
            "runtime": [],
            "unresolved": [],
            "impact_edges": [],
            "boundary_hints": {"hint_count": 0, "hints": []},
            "serialized_line_ranges": {},
        }
        base.update(overrides)
        return MrRunContext(**base)

    def test_render_mr_analysis_header(self) -> None:
        text = render_mr_analysis(self._minimal_ctx())
        self.assertIn("# MR analysis", text)
        self.assertIn("sql/a.sql", text)

    def test_stale_note_when_index_behind(self) -> None:
        note = index_stale_note(
            index_stale=True,
            indexed_head="a" * 40,
            repo_head="b" * 40,
            partial_refresh=None,
        )
        self.assertIn("Index stale", note)

    def test_test_plan_fallback_message(self) -> None:
        text = render_test_plan(self._minimal_ctx())
        self.assertIn("No runtime targets", text)


if __name__ == "__main__":
    unittest.main()
