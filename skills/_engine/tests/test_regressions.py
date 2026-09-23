"""Behavioral regressions for the requirements audit and follow-up improvements."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .helpers import commit, initialize
from mr_impact.adapters import parse
from mr_impact.analysis import analyze_mr
from mr_impact.catalog import aggregate, lookup, repository_matches
from mr_impact.diff import map_symbols, parse_diff, validate_patch
from mr_impact.indexing import IndexConfig, boundary_rows, build_index
from mr_impact.issues import analyze_issue, source_fingerprints, template_instructions, template_slots, update_issue, validate_interpretation
from mr_impact.models import Edge, Evidence, FileRecord, Limits, Node, ParsedFile, record
from mr_impact.safety import EngineError, write_json
from mr_impact.storage import Store


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def issue(self, template, source=""):
        root = self.work / "issue"
        root.mkdir(exist_ok=True)
        (root / "GITLAB_ISSUE_TEMPLATE.md").write_text(template, encoding="utf-8")
        (root / "notes.md").write_text(source, encoding="utf-8")
        return root, self.work / "output"

    def test_independent_placeholders_and_duplicate_names(self):
        root, output = self.issue("## Details\n{{problem}} | {{outcome}} | {{problem}}\n",
                                  "## Problem\nOld behavior fails.\n## Outcome\nNew behavior succeeds.\n")
        template = (root / "GITLAB_ISSUE_TEMPLATE.md").read_text()
        slots = template_slots(template)
        self.assertEqual(len({slot.id for slot in slots}), 3)
        plan = {"template_sha256": hashlib.sha256(template.encode()).hexdigest(), "fills": {
            slot.id: [{"kind": "context", "text": str(i), "evidence": [
                {"file": "notes.md", "start_line": 2, "end_line": 2}]}] for i, slot in enumerate(slots)}}
        path = self.work / "interpretation.json"
        path.write_text(json.dumps(plan))
        analyze_issue(root, output, interpretation=path)
        self.assertIn("0 | 1 | 2", (output / "01-generated-issue.md").read_text())
        plan["empty_slots"] = [slots[1].id]
        del plan["fills"][slots[1].id]
        path.write_text(json.dumps(plan))
        analyze_issue(root, output, interpretation=path)
        self.assertIn("0 |  | 2", (output / "01-generated-issue.md").read_text())

    def test_optional_instruction_and_draft_review_gate(self):
        root, output = self.issue("## Optional notes\n<!-- Leave empty when no evidence exists. -->\n{{notes}}\n")
        result = analyze_issue(root, output)
        self.assertEqual((output / "01-generated-issue.md").read_text().strip(), "## Optional notes")
        self.assertEqual(result["status"], "draft")
        with self.assertRaises(EngineError):
            analyze_issue(root, output, require_review=True)

    def test_review_binds_sources_decisions_and_instructions(self):
        root, output = self.issue("## Details\n<!-- Use concise prose. -->\n{{item}}\n", "Observed behavior.\n")
        template = (root / "GITLAB_ISSUE_TEMPLATE.md").read_text()
        plan = {"reviewed": True, "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                "source_sha256": source_fingerprints({"notes.md": "Observed behavior.\n"}),
                "source_decisions": {"notes.md": {"use": "included", "reason": "Issue context"}},
                "reviewed_instructions": [i["id"] for i in template_instructions(template)],
                "fills": {"L3": [{"kind": "context", "text": "Observed behavior.",
                                  "evidence": [{"file": "notes.md", "start_line": 1, "end_line": 1}]}]}}
        path = self.work / "plan.json"
        path.write_text(json.dumps(plan))
        self.assertEqual(analyze_issue(root, output, interpretation=path, require_review=True)["status"], "reviewed")
        (root / "notes.md").write_text("Different behavior.\n")
        with self.assertRaisesRegex(EngineError, "sources changed"):
            analyze_issue(root, output, interpretation=path)

    def test_requirement_guard_uses_ancestor_sections(self):
        root, output = self.issue("## Acceptance Criteria\n### Details\n{{item}}\n", "Evidence.\n")
        template = (root / "GITLAB_ISSUE_TEMPLATE.md").read_text()
        for kind in ("inference", "assumption", "open_question"):
            plan = {"template_sha256": hashlib.sha256(template.encode()).hexdigest(), "fills": {
                "L3": [{"kind": kind, "text": "Possible change", "evidence": [
                    {"file": "notes.md", "start_line": 1, "end_line": 1}]}]}}
            path = self.work / "plan.json"
            path.write_text(json.dumps(plan))
            with self.subTest(kind=kind), self.assertRaises(EngineError):
                analyze_issue(root, output, interpretation=path)

    def test_interpretation_rejects_false_review_strings_and_malformed_citations(self):
        template = "## Details\n{{item}}\n"
        plan = {"template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                "fills": {"L2": [{"kind": "context", "text": "Observed behavior.", "evidence": []}]}}
        slots = template_slots(template)
        for reviewed in ("false", "true", 1, [], None):
            with self.subTest(reviewed=reviewed), self.assertRaisesRegex(EngineError, "boolean"):
                validate_interpretation(dict(plan, reviewed=reviewed), template, slots, {})
        for citations in ("notes.md:1", ["notes.md:1"], None, {}):
            plan["fills"]["L2"][0]["evidence"] = citations
            with self.subTest(citations=citations), self.assertRaisesRegex(EngineError, "list of citations"):
                validate_interpretation(plan, template, slots, {})

    def mappings(self, before, after, diff):
        class Symbols:
            def __init__(self, text):
                self.items = [record(symbol) for symbol in parse("app.py", text).symbols]

            def symbols(self, path):
                return self.items
        return map_symbols(parse_diff(diff), Symbols(after), Symbols(before))

    def test_context_does_not_change_symbol_mapping(self):
        before = "def first():\n    return 1\n\ndef second():\n    return 2\n"
        after = before.replace("return 1", "return 3")
        diffs = ["@@ -2 +2 @@\n-    return 1\n+    return 3\n",
                 "@@ -1,5 +1,5 @@\n def first():\n-    return 1\n+    return 3\n \n def second():\n     return 2\n"]
        for diff in diffs:
            mappings = self.mappings(before, after, "--- a/app.py\n+++ b/app.py\n" + diff)
            self.assertEqual({m["symbol"]["qualified_name"] for m in mappings}, {"first"})

    def test_signature_tracks_arguments_defaults_return_and_async(self):
        def signature(text):
            return parse("app.py", text).symbols[0].signature
        first = "def calculate(\n    value: int = 1,\n) -> int:\n    return value\n"
        for changed in (first.replace("value: int", "value: str"), first.replace("= 1", "= 2"),
                        first.replace("-> int", "-> str"), first.replace("def calculate", "async def calculate")):
            self.assertNotEqual(signature(first), signature(changed))
        self.assertEqual(signature(first), signature("def calculate(value: int = 1) -> int:\n    return 0\n"))

    def test_patch_validates_deletions_context_and_entire_transformation(self):
        before = "before\nkeep\n"
        after = "after\nkeep\n"
        good = "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n-before\n+after\n keep\n"
        validate_patch(parse_diff(good), {"app.py": True}, {"app.py": True}, lambda p: before, lambda p: after)
        for bad in (good.replace(" keep", " wrong"), good.replace("-before", "-fabricated"),
                    "--- a/app.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-before\n-keep\n"):
            with self.subTest(patch=bad), self.assertRaises(EngineError):
                validate_patch(parse_diff(bad), {"app.py": True}, {"app.py": True}, lambda p: before, lambda p: after)
        deletion = "--- a/app.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-before\n-keep\n"
        validate_patch(parse_diff(deletion), {"app.py": True}, {}, lambda p: before, lambda p: "")
        with self.assertRaises(EngineError):
            validate_patch(parse_diff(good), {"app.py": True}, {"app.py": True}, lambda p: before, lambda p: after + "extra\n")

    def test_root_commit_is_added_against_empty_tree(self):
        root = self.work / "repo"
        root.mkdir()
        (root / "app.py").write_text("def run():\n    return 1\n")
        first = initialize(root)
        output = self.work / "mr"
        analyze_mr(root, output, commit=first, cache=self.work / "cache")
        context = json.loads((output / "mr-context.json").read_text())
        mappings = json.loads((output / "changed-symbols.json").read_text())["mappings"]
        self.assertEqual(context["base_kind"], "empty_tree")
        self.assertTrue(all(c["status"] == "added" for c in context["changes"]))
        self.assertEqual({m["change"] for m in mappings}, {"added"})

    def test_patch_checks_no_newline_markers(self):
        diff = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n\\ No newline at end of file\n+new\n"
        validate_patch(parse_diff(diff), {"app.py": True}, {"app.py": True}, lambda p: "old", lambda p: "new\n")
        with self.assertRaises(EngineError):
            validate_patch(parse_diff(diff), {"app.py": True}, {"app.py": True}, lambda p: "old\n", lambda p: "new\n")

    def test_structured_qa_scenario_and_complete_update_integrity(self):
        root = self.work / "repo"
        root.mkdir()
        script = root / "app.py"
        script.write_text("def run():\n    return 1\n")
        base = initialize(root)
        script.write_text("def run():\n    return 2\n")
        head = commit(root)
        output = self.work / "mr"
        cache = self.work / "cache"
        analyze_mr(root, output, base, head, cache=cache)
        context = json.loads((output / "mr-context.json").read_text())
        target = next(t for t in json.loads((output / "runtime-impact.json").read_text())["targets"]
                      if t["entity"] == "file://app.py")
        plan = {"head": head, "diff_sha256": context["diff_sha256"], "findings": [{
            "change_index": 0, "hunk_index": 0, "classification": "confirmed", "summary": "Return value changed.",
            "validation": "Check the return value.", "scenario": {
                "target": target["entity"], "repository": target["repository"],
                "preconditions": "Use an isolated QA interpreter.", "inputs": "No arguments.", "expected": "Returns 2."}}]}
        path = self.work / "interpretation.json"
        path.write_text(json.dumps(plan))
        analyze_mr(root, output, base, head, cache=cache, interpretation=path)
        tests = json.loads((output / "test-impact.json").read_text())
        self.assertEqual(tests["scenarios"][0]["expected"], "Returns 2.")
        self.assertFalse(tests["scenarios"][0]["executed"])
        issue = self.work / "issue.md"
        issue.write_text("# Issue\nRecord the observed result.\n")
        update_issue(issue, output, output)
        (output / "04-test-plan.md").write_text("Replaced plan")
        with self.assertRaisesRegex(EngineError, "artifacts"):
            update_issue(issue, output, output)
        plan["findings"][0]["scenario"]["target"] = "file://invented.py"
        path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(EngineError, "undiscovered"):
            analyze_mr(root, output, base, head, cache=cache, interpretation=path)

    def test_strong_path_keeps_shorter_alternative_for_depth_budget(self):
        def ev(confidence):
            return Evidence("graph", 1, 1, "fixture", confidence)
        with Store(self.work / "graph.sqlite") as store:
            nodes = [Node(key, "PROCESS", key, ev(100)) for key in "ABCDE"]
            edges = [Edge(a, b, "DEFINES", ev(c)) for a, b, c in
                     [("A", "D", 30), ("A", "B", 100), ("B", "C", 100), ("C", "D", 100), ("D", "E", 100)]]
            store.put(FileRecord("graph", "one", 1, "generic"), ParsedFile(nodes=nodes, edges=edges))
            graph = store.traverse(["A"], Limits(max_depth=3))
            self.assertEqual(graph["confidence"]["D"], 100)
            self.assertEqual(graph["confidence"]["E"], 30)
            self.assertEqual(len(graph["paths"]["E"]), 2)
            limited = store.traverse(["A"], Limits(max_nodes=2, max_edges=1))
            self.assertLessEqual(len(limited["nodes"]), 2)
            self.assertLessEqual(len(limited["edges"]), 1)

    def test_python_relative_and_package_imports_incremental(self):
        root = self.work / "repo"
        (root / "pkg/worker").mkdir(parents=True)
        (root / "pkg/main.py").write_text("from .worker import run\nrun()\n")
        (root / "pkg/worker/__init__.py").write_text("def run():\n    return 1\n")
        initialize(root)
        cache = self.work / "cache"
        result = build_index(root, cache)
        with Store(Path(result["directory"]) / "repository-index.sqlite") as store:
            graph = store.traverse(["file://pkg/worker/__init__.py"], Limits())
            self.assertIn("file://pkg/main.py", graph["paths"])
        (root / "pkg/worker.py").write_text("def run():\n    return 2\n")
        commit(root)
        result = build_index(root, cache)
        self.assertEqual(result["statistics"]["files_parsed"], 1)
        with Store(Path(result["directory"]) / "repository-index.sqlite") as store:
            graph = store.traverse(["file://pkg/worker.py"], Limits())
            self.assertIn("file://pkg/main.py", graph["paths"])

    def test_standalone_boundary_definition_reaches_catalog(self):
        root = self.work / "repo"
        root.mkdir()
        (root / "standalone.sh").write_text("echo ready\n")
        initialize(root)
        result = build_index(root, self.work / "cache", "boundary")
        catalog = self.work / "catalog.sqlite"
        aggregate(catalog, [Path(result["directory"])])
        matches = lookup(catalog, "file://standalone.sh")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["role"], "DEFINES")
        self.assertEqual(repository_matches(catalog, matches[0]["repository"], ["file://standalone.sh"])[0]["entity"], "file://standalone.sh")

    def test_redacted_json_preserves_nested_structure(self):
        output = self.work / "data.json"
        write_json(output, {"token": 123, "items": [{"secret": False}, {"safe": "quoted \\\" text"}], "count": 2, "none": None})
        result = json.loads(output.read_text())
        self.assertEqual(result["token"], "[REDACTED]")
        self.assertEqual(result["items"][0]["secret"], "[REDACTED]")
        self.assertEqual(result["count"], 2)
        self.assertIsNone(result["none"])

    def test_noop_preserves_manifests_and_recovers_missing_export(self):
        root = self.work / "repo"
        initialize(root, "repo-a")
        result = build_index(root, self.work / "cache")
        directory = Path(result["directory"])
        manifest = directory / "manifest.json"
        stamp = manifest.stat().st_mtime_ns
        with patch("mr_impact.indexing.parse", side_effect=AssertionError("Unexpected parse")):
            result = build_index(root, self.work / "cache")
        self.assertEqual(result["statistics"]["files_parsed"], 0)
        self.assertEqual(stamp, manifest.stat().st_mtime_ns)
        (directory / "boundary.json").unlink()
        result = build_index(root, self.work / "cache")
        self.assertTrue((directory / "boundary.json").is_file())
        self.assertEqual(result["statistics"]["files_parsed"], 0)

    def test_excluded_worktree_content_is_never_opened(self):
        root = self.work / "repo"
        initialize(root, "repo-a")
        (root / "vendor").mkdir()
        excluded = root / "vendor/large.bin"
        excluded.write_bytes(b"x" * 100)
        original_open = Path.open

        def checked_open(path, *args, **kwargs):
            if path == excluded:
                raise AssertionError("Excluded file content was read")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", checked_open):
            build_index(root, self.work / "cache", worktree=True)

    def test_runtime_detectors_preserve_actual_entrypoints(self):
        cases = [("jobs.cron", "0 1 * * * python scripts/run.py\n", "WORKFLOW"),
                 ("worker.service", "[Service]\nExecStart=python scripts/run.py\n", "SERVICE"),
                 ("worker.timer", "[Timer]\nUnit=worker.service\n", "PROCESS")]
        for path, text, kind in cases:
            parsed = parse(path, text)
            self.assertTrue(any(n.type == kind for n in parsed.nodes))
            self.assertTrue(any(e.type in {"EXECUTES", "TRIGGERS"} for e in parsed.edges))
        producer = parse("producer.py", 'publish_event("orders")\n')
        consumer = parse("consumer.py", 'consume_event("orders")\n')
        self.assertTrue(any(e.type == "PUBLISHES_EVENT" and e.target == "event://orders" for e in producer.edges))
        self.assertTrue(any(e.type == "CONSUMES_EVENT" and e.target == "event://orders" for e in consumer.edges))


if __name__ == "__main__":
    unittest.main()
