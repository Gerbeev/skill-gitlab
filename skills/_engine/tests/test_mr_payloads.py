from __future__ import annotations

import unittest

from mr_impact.artifacts.contract import validate_changed_symbols, validate_runtime_impact
from mr_impact.git.diff import ChangedFile
from mr_impact.mr.payloads import build_mr_json_artifacts
from mr_impact.mr.run_context import MrRunContext


class MrPayloadsTests(unittest.TestCase):
    def _ctx(self, **overrides) -> MrRunContext:
        base = {
            "now": "t",
            "revision": "a..b",
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed": [ChangedFile(status="M", path="x.sql")],
            "symbols": [],
            "indexed_head": "c" * 40,
            "repo_head": "d" * 40,
            "index_stale": False,
            "partial_refresh": None,
            "issue_dir": None,
            "graph_json_present": False,
            "boundary_catalog_present": False,
            "seeds": {"x.sql"},
            "impact_edges": [],
            "primary_qa": [],
            "runtime": [],
            "unresolved": [],
            "boundary_hints": {"hint_count": 0, "hints": []},
            "serialized_line_ranges": {},
        }
        base.update(overrides)
        return MrRunContext(**base)

    def test_artifacts_pass_contract_validators(self) -> None:
        artifacts = build_mr_json_artifacts(self._ctx())
        self.assertEqual(validate_changed_symbols(artifacts.changed_symbols), [])
        self.assertEqual(validate_runtime_impact(artifacts.runtime_impact), [])


if __name__ == "__main__":
    unittest.main()
