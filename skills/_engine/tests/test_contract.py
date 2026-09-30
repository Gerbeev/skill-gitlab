from __future__ import annotations

import unittest

from mr_impact.artifacts.contract import (
    validate_changed_symbols,
    validate_runtime_impact,
)


class ContractTests(unittest.TestCase):
    def test_changed_symbols_minimal_valid(self) -> None:
        payload = {
            "schema_version": 1,
            "revision": "a..b",
            "base_sha": "a",
            "head_sha": "b",
            "changed_files": [],
            "symbols_touched_by_diff": [],
        }
        self.assertEqual(validate_changed_symbols(payload), [])

    def test_runtime_v2_requires_primary_qa(self) -> None:
        errors = validate_runtime_impact({"schema_version": 2})
        self.assertTrue(any("primary_qa_targets" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
