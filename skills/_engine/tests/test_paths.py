from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mr_impact.paths import (
    ANALYSIS_DIR_NAME,
    analysis_layout,
    require_index_sqlite,
)


class AnalysisLayoutTests(unittest.TestCase):
    def test_default_layout_under_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = analysis_layout(root)
            self.assertEqual(layout.root, (root / ANALYSIS_DIR_NAME).resolve())
            self.assertEqual(layout.index_sqlite.name, "repository-index.sqlite")
            self.assertFalse(layout.index_present)

    def test_require_index_raises_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FileNotFoundError) as ctx:
                require_index_sqlite(root)
            self.assertIn("create-index", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
