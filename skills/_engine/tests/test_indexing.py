import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from .helpers import command, commit, initialize
from mr_impact.indexing import IndexConfig, build_index, is_fresh
from mr_impact.models import Limits
from mr_impact.storage import Store


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.cache = Path(self.tmp.name) / "cache"
        initialize(self.root, "repo-a")

    def test_initial_noop_change_delete_rename_and_freshness(self):
        initial = build_index(self.root, self.cache)
        self.assertGreater(initial["statistics"]["files_parsed"], 0)
        directory = Path(initial["directory"])
        export_time = (directory / "graph/dependency-graph.json").stat().st_mtime_ns
        self.assertTrue(is_fresh(self.root, directory))
        noop = build_index(self.root, self.cache)
        self.assertEqual(noop["statistics"]["files_parsed"], 0)
        self.assertEqual(noop["statistics"]["files_reused"], initial["statistics"]["files_parsed"])
        self.assertEqual((directory / "graph/dependency-graph.json").stat().st_mtime_ns, export_time)
        path = self.root / "src/RiskWriter.scala"
        path.write_text(path.read_text().replace("VALUES (1)", "VALUES (2)"))
        commit(self.root)
        self.assertFalse(is_fresh(self.root, directory))
        updated = build_index(self.root, self.cache)
        self.assertEqual(updated["statistics"]["files_parsed"], 1)
        path.rename(path.with_name("Exposure.scala"))
        (self.root / "build.sbt").unlink()
        commit(self.root, "Rename writer and remove build declaration")
        result = build_index(self.root, self.cache)
        self.assertEqual(result["statistics"]["files_deleted"], 2)
        with Store(directory / "repository-index.sqlite") as store:
            self.assertEqual(store.symbols("src/RiskWriter.scala"), [])
            self.assertTrue(store.symbols("src/Exposure.scala"))
            self.assertFalse(store.db.execute("SELECT 1 FROM edges WHERE file='build.sbt'").fetchone())

    def test_failed_parse_rolls_back_index_state(self):
        initial = build_index(self.root, self.cache)
        path = self.root / "src/RiskWriter.scala"
        path.write_text(path.read_text() + "\n// New source revision\n", newline="\n")
        commit(self.root)
        with patch("mr_impact.indexing.parse", side_effect=RuntimeError("Synthetic detector failure")):
            with self.assertRaises(RuntimeError):
                build_index(self.root, self.cache)
        with Store(Path(initial["directory"]) / "repository-index.sqlite") as store:
            self.assertEqual(store.state()["commit"], initial["state"]["commit"])
            self.assertTrue(store.symbols("src/RiskWriter.scala"))

    def test_worktree_and_committed_snapshot_are_distinct(self):
        index = build_index(self.root, self.cache)
        path = self.root / "new.py"
        path.write_text("def added():\n    return 1\n")
        self.assertTrue(is_fresh(self.root, Path(index["directory"])))
        self.assertFalse(is_fresh(self.root, Path(index["directory"]), worktree=True))
        result = build_index(self.root, self.cache, worktree=True)
        self.assertEqual(result["statistics"]["files_parsed"], 1)

    def test_boundary_export_and_mode_upgrade(self):
        boundary = build_index(self.root, self.cache, "boundary")
        self.assertEqual(boundary["statistics"]["symbols"], 0)
        data = json.loads((Path(boundary["directory"]) / "boundary.json").read_text())
        self.assertTrue(any(row["entity"] == "table://RISK/DAILY_EXPOSURE" for row in data))
        deep = build_index(self.root, self.cache, "deep")
        self.assertGreater(deep["statistics"]["symbols"], 0)

    def test_bounded_traversal_filters_cycles_and_evidence(self):
        result = build_index(self.root, self.cache)
        with Store(Path(result["directory"]) / "repository-index.sqlite") as store:
            small = store.traverse(["file://src/RiskWriter.scala"], Limits(max_nodes=2, max_edges=1))
            self.assertLessEqual(len(small["nodes"]), 2)
            self.assertLessEqual(len(small["edges"]), 1)
            self.assertTrue(small["truncated"])
            graph = store.traverse(["file://src/RiskWriter.scala"], Limits())
            self.assertTrue(any(n["name"] == "DAILY_RISK_JOB" for n in graph["nodes"]))
            self.assertTrue(any(e["evidence"]["file"] == "jobs/risk.jil" for e in graph["edges"]))
            filtered = store.traverse(["file://src/RiskWriter.scala"], Limits(confidence=90, edge_types=("CALLS",)))
            self.assertEqual(filtered["edges"], [])

    def test_exclusion_size_and_adapter_config_invalidation(self):
        (self.root / "vendor").mkdir()
        (self.root / "vendor/big.py").write_text("x=" + "1" * 100)
        (self.root / "large.txt").write_text("a" * 3000)
        commit(self.root)
        result = build_index(self.root, self.cache, config=IndexConfig(max_file_bytes=2000, workers=2))
        self.assertGreaterEqual(result["statistics"]["files_skipped"], 2)
        self.assertTrue(any("Oversized" in w for w in result["statistics"]["warnings"]))
        result = build_index(self.root, self.cache, config=IndexConfig(exclude=["src/*"]))
        with Store(Path(result["directory"]) / "repository-index.sqlite") as store:
            self.assertEqual(store.symbols("src/RiskWriter.scala"), [])
