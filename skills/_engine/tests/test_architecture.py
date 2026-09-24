"""Regression coverage for entity identity, recovery, review, and snapshot isolation."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .helpers import cli, commit, initialize
from mr_impact import indexing
from mr_impact.analysis import analyze_mr
from mr_impact.catalog import aggregate, lookup
from mr_impact.git import repository_id
from mr_impact.indexing import build_index, is_fresh, publication_valid
from mr_impact.issues import analyze_issue, source_fingerprints, update_issue
from mr_impact.locking import repository_lock
from mr_impact.models import Limits
from mr_impact.safety import EngineError
from mr_impact.storage import Store


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.cache = self.work / "cache"
        self.output = self.work / "output"

    def repo(self, name, files):
        root = self.work / name
        root.mkdir()
        for file, text in files.items():
            path = root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return root, initialize(root)

    def context(self):
        return json.loads((self.output / "mr-context.json").read_text())

    def test_local_paths_do_not_select_unrelated_repositories(self):
        a, base = self.repo("a", {"run.py": "print(1)\n"})
        b, _ = self.repo("b", {"run.py": "print('unrelated')\n"})
        catalog = self.work / "catalog.sqlite"
        aggregate(catalog, [Path(build_index(b, self.cache, "boundary")["directory"])])
        self.assertEqual(lookup(catalog, "file://run.py"), [])
        (a / "run.py").write_text("print(2)\n")
        commit(a)
        analyze_mr(a, self.output, base, cache=self.cache, catalog=catalog)
        self.assertEqual(self.context()["candidates"], [])

    def test_explicit_identity_survives_relocation_and_namespaces_do_not_collide(self):
        settings = {"repository_id": "payments", "namespaces": {"table": "warehouse-qa"}}
        a, _ = self.repo("a", {".repository-identity.json": json.dumps(settings),
                               "read.sql": "SELECT * FROM app.orders;\n"})
        first = build_index(a, self.cache, "boundary")
        moved = self.work / "moved"
        shutil.copytree(a, moved)
        self.assertEqual(repository_id(moved), "payments")
        self.assertNotEqual(first["directory"], build_index(moved, self.cache)["directory"])
        b, _ = self.repo("b", {".repository-identity.json": json.dumps({"namespaces": {"table": "warehouse-prod"}}),
                               "read.sql": "SELECT * FROM app.orders;\n"})
        second = build_index(b, self.cache, "boundary")
        catalog = self.work / "catalog.sqlite"
        aggregate(catalog, [Path(first["directory"]), Path(second["directory"])])
        self.assertEqual([r["repository"] for r in lookup(catalog, "table://warehouse-qa/APP/ORDERS")], ["payments"])
        self.assertEqual(len(lookup(catalog, "table://warehouse-prod/APP/ORDERS")), 1)

    def test_export_failures_recover_without_reparsing(self):
        for phase in ("boundary.json", "repository-index.json", "dependency-graph.json",
                      "graph-manifest.json", "state.json", "manifest.json"):
            with self.subTest(phase=phase):
                root, _ = self.repo(phase, {"run.py": "print(1)\n"})
                original = build_index(root, self.cache)
                directory = Path(original["directory"])
                (root / "new.py").write_text("print(2)\n")
                commit(root)
                function = "_export_array" if phase in {"boundary.json", "repository-index.json", "dependency-graph.json"} else "write_json"
                real = getattr(indexing, function)

                def interrupted(path, *args, **kwargs):
                    if path.name == phase:
                        raise OSError("Injected publication interruption")
                    return real(path, *args, **kwargs)

                with patch.object(indexing, function, side_effect=interrupted), self.assertRaises(OSError):
                    build_index(root, self.cache)
                self.assertFalse(is_fresh(root, directory))
                recovered = build_index(root, self.cache)
                self.assertEqual(recovered["statistics"]["files_parsed"], 0)
                self.assertTrue(publication_valid(directory, recovered["state"]))
                files = json.loads((directory / "repository-index.json").read_text())
                self.assertIn("new.py", [f["path"] for f in files])

    def test_existing_but_corrupt_export_is_repaired(self):
        root, _ = self.repo("a", {"run.py": "print(1)\n"})
        result = build_index(root, self.cache)
        directory = Path(result["directory"])
        (directory / "repository-index.json").write_text("[]")
        self.assertFalse(is_fresh(root, directory))
        repaired = build_index(root, self.cache)
        self.assertEqual(repaired["statistics"]["files_parsed"], 0)
        self.assertTrue(publication_valid(directory, repaired["state"]))

    def test_diamond_expansion_revisits_new_seeds_without_rebuilding(self):
        a, base = self.repo("a", {"write.sql": "INSERT INTO app.x VALUES (1);\nINSERT INTO app.z VALUES (1);\n"})
        b, _ = self.repo("b", {"one.sql": "SELECT * FROM app.x;\n", "two.sql": "SELECT * FROM app.y;\n",
                               "one.jil": "insert_job: FIRST job_type: c\ncommand: sqlplus one.sql\n",
                               "two.jil": "insert_job: SECOND job_type: c\ncommand: sqlplus two.sql\n"})
        c, _ = self.repo("c", {"bridge.sql": "SELECT * FROM app.z;\nINSERT INTO app.y VALUES (1);\n"})
        catalog = self.work / "catalog.sqlite"
        aggregate(catalog, [Path(build_index(r, self.cache, "boundary")["directory"]) for r in (b, c)])
        (a / "write.sql").write_text("INSERT INTO app.x VALUES (2);\nINSERT INTO app.z VALUES (2);\n")
        commit(a)
        with patch("mr_impact.expansion.build_index", wraps=build_index) as builds:
            analyze_mr(a, self.output, base, cache=self.cache, catalog=catalog, limits=Limits(cross_depth=4))
            self.assertEqual(builds.call_count, 2)
        targets = json.loads((self.output / "runtime-impact.json").read_text())["targets"]
        self.assertTrue({"FIRST", "SECOND"} <= {t["target"] for t in targets})
        candidate = next(c for c in self.context()["candidates"] if c["repository"] == repository_id(b))
        self.assertTrue({"table://APP/X", "table://APP/Y"} <= set(candidate["entities"]))
        analyze_mr(a, self.output, base, cache=self.cache, catalog=catalog, limits=Limits(max_expansions=1))
        self.assertTrue(any("expansion budget" in w for w in self.context()["warnings"]))
        self.assertEqual(self.context()["coverage_status"], "partial")

    def test_old_and_new_boundaries_both_expand_same_candidate(self):
        a, base = self.repo("a", {"write.sql": "INSERT INTO app.old_table VALUES (1);\n"})
        b, _ = self.repo("b", {"old.sql": "SELECT * FROM app.old_table;\n", "new.sql": "SELECT * FROM app.new_table;\n",
                               "old.jil": "insert_job: OLD_FLOW job_type: c\ncommand: sqlplus old.sql\n",
                               "new.jil": "insert_job: NEW_FLOW job_type: c\ncommand: sqlplus new.sql\n"})
        catalog = self.work / "catalog.sqlite"
        aggregate(catalog, [Path(build_index(b, self.cache, "boundary")["directory"])])
        (a / "write.sql").write_text("INSERT INTO app.new_table VALUES (1);\n")
        commit(a)
        analyze_mr(a, self.output, base, cache=self.cache, catalog=catalog)
        targets = json.loads((self.output / "runtime-impact.json").read_text())["targets"]
        self.assertTrue({"OLD_FLOW", "NEW_FLOW"} <= {t["target"] for t in targets})

    def test_semantic_issue_conflict_is_delivered_without_template_slot(self):
        template = "## Scope\n{{scope}}\n"
        source = "Retention is 30 days.\nRetention is 90 days.\n"
        root, _ = self.repo("issue", {"GITLAB_ISSUE_TEMPLATE.md": template, "notes.md": source})
        plan = {"reviewed": True, "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                "source_sha256": source_fingerprints({"notes.md": source}), "reviewed_instructions": [],
                "source_decisions": {"notes.md": {"use": "included", "reason": "Agreed notes conflict"}},
                "findings": [{"kind": "conflict", "severity": "error", "status": "unresolved",
                              "text": "The retention duration conflicts: 30 versus 90 days.",
                              "evidence": [{"file": "notes.md", "start_line": 1, "end_line": 2}]}]}
        path = self.work / "interpretation.json"
        path.write_text(json.dumps(plan))
        analyze_issue(root, self.output, interpretation=path, require_review=True)
        self.assertIn("30 versus 90", (self.output / "00-issue-analysis.md").read_text())
        self.assertEqual(len(list(self.output.iterdir())), 2)
        plan["findings"][0]["evidence"][0]["end_line"] = 100
        path.write_text(json.dumps(plan))
        with self.assertRaises(EngineError):
            analyze_issue(root, self.output, interpretation=path)

    def test_mr_review_gate_context_binding_and_preview_status(self):
        root, base = self.repo("a", {"run.py": "print(1)\n"})
        (root / "run.py").write_text("print(2)\n")
        commit(root)
        issue = self.work / "issue.md"
        issue.write_text("# Issue\nPreserve outputs.\n")
        analyze_mr(root, self.output, base, cache=self.cache, issue=issue)
        context = self.context()
        self.assertEqual(context["analysis_status"], "draft")
        with self.assertRaisesRegex(EngineError, "semantic review"):
            analyze_mr(root, self.output, base, cache=self.cache, issue=issue, require_review=True)
        plan = {"head": context["head"], "diff_sha256": context["diff_sha256"], "reviewed": True,
                "review_context": context["review_context"], "findings": [],
                "reviewed_changes": {"0": {"status": "unresolved", "reason": "Expected output requires owner confirmation"}}}
        path = self.work / "plan.json"
        path.write_text(json.dumps(plan))
        analyze_mr(root, self.output, base, cache=self.cache, issue=issue, interpretation=path, require_review=True)
        self.assertEqual(self.context()["semantic_review_status"], "reviewed_with_gaps")
        update_issue(issue, self.output, self.output)
        self.assertIn("reviewed_with_gaps", (self.output / "05-issue-update.md").read_text())
        issue.write_text("# Issue\nDifferent requirements.\n")
        with self.assertRaisesRegex(EngineError, "context changed"):
            analyze_mr(root, self.output, base, cache=self.cache, issue=issue, interpretation=path)

    def test_other_process_cannot_replace_active_repository_snapshot(self):
        root, base = self.repo("a", {"run.py": "print(1)\n"})
        (root / "run.py").write_text("print(2)\n")
        head = commit(root)
        with repository_lock(root):
            result = build_index(root, self.cache, ref=base)
            child = cli("index-repository", "--repo", root, "--cache", self.cache, "--ref", head)
            self.assertEqual(child.returncode, 2, child.stderr)
            self.assertIn("busy", child.stderr)
            with Store(Path(result["directory"]) / "repository-index.sqlite") as store:
                self.assertEqual(store.state()["commit"], base)
        self.assertEqual(build_index(root, self.cache, ref=head)["state"]["commit"], head)
