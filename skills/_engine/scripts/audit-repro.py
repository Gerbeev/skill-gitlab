"""Reproduce audit findings without changing the checkout or executing fixture code.

Exit 1 means documented bugs were reproduced, 0 means none were reproduced.
This is an audit probe, not the normal acceptance test suite.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

from tests.helpers import commit, initialize
from mr_impact.adapters import parse
from mr_impact.analysis import analyze_mr
from mr_impact.diff import map_symbols, parse_diff
from mr_impact.indexing import boundary_rows, build_index
from mr_impact.issues import analyze_issue, template_slots, validate_interpretation
from mr_impact.models import Edge, Evidence, FileRecord, Limits, Node, ParsedFile
from mr_impact.safety import EngineError, write_json
from mr_impact.storage import Store


def main():
    results = []

    def report(number, observed, detail):
        results.append({"id": f"BUG-{number:03}", "reproduced": bool(observed), "observed": detail})

    with tempfile.TemporaryDirectory(prefix="mr-impact-audit-") as temp:
        work = Path(temp)
        issue = work / "issue"
        issue.mkdir()
        template = issue / "GITLAB_ISSUE_TEMPLATE.md"
        template.write_text("## Details\n{{problem}} | {{outcome}}\n", encoding="utf-8")
        (issue / "notes.md").write_text("## Problem\nOld behavior fails.\n## Outcome\nNew behavior succeeds.\n", encoding="utf-8")
        out = work / "issue-output"
        analyze_issue(issue, out)
        generated = (out / "01-generated-issue.md").read_text(encoding="utf-8")
        report(1, "Old behavior fails. | Old behavior fails." in generated, generated.strip())

        template.write_text("## Optional notes\n<!-- Leave empty when no evidence exists. -->\n{{notes}}\n", encoding="utf-8")
        empty = work / "empty"
        empty.mkdir()
        analyze_issue(issue, out, scope=empty)
        generated = (out / "01-generated-issue.md").read_text(encoding="utf-8")
        report(2, "Unresolved:" in generated, generated.strip())

        template_text = "## Acceptance Criteria\n{{item}}\n"
        slots = template_slots(template_text)
        plan = {"template_sha256": hashlib.sha256(template_text.encode()).hexdigest(), "fills": {
            slots[0].id: [{"kind": "inference", "text": "Require an audit service.", "evidence": []}]}}
        try:
            validate_interpretation(plan, template_text, slots, {})
            accepted = True
        except EngineError:
            accepted = False
        report(3, accepted, {"inference_in_acceptance_criteria_accepted": accepted})

        class Symbols:
            def __init__(self, parsed):
                from dataclasses import asdict
                self.items = [asdict(s) for s in parsed.symbols]

            def symbols(self, path):
                return self.items

        before_text = "def first():\n    return 1\n\ndef second():\n    return 2\n"
        after_text = before_text.replace("return 1", "return 3")
        patch = "--- a/app.py\n+++ b/app.py\n@@ -1,5 +1,5 @@\n def first():\n-    return 1\n+    return 3\n \n def second():\n     return 2\n"
        mappings = map_symbols(parse_diff(patch), Symbols(parse("app.py", after_text)), Symbols(parse("app.py", before_text)))
        names = sorted({m["symbol"]["qualified_name"] for m in mappings})
        report(4, "second" in names, {"mapped_functions": names, "actually_changed": "first"})

        before_text = "def calculate(\n    amount: int,\n):\n    return amount\n"
        after_text = before_text.replace("amount: int", "amount: str")
        patch = "--- a/app.py\n+++ b/app.py\n@@ -2 +2 @@\n-    amount: int,\n+    amount: str,\n"
        mappings = map_symbols(parse_diff(patch), Symbols(parse("app.py", after_text)), Symbols(parse("app.py", before_text)))
        kinds = sorted({m["change"] for m in mappings})
        report(5, "signature_changed" not in kinds, {"mapping_types": kinds})

        repo = work / "repository"
        initialize(repo)
        (repo / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        head = commit(repo)
        patch_file = work / "false-deletion.patch"
        patch_file.write_text("diff --git a/app.py b/app.py\ndeleted file mode 100644\n--- a/app.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-def imaginary():\n-    return 999\n", encoding="utf-8")
        try:
            analyze_mr(repo, work / "mr", base=head, head=head, patch=patch_file, cache=work / "cache")
            accepted = True
        except EngineError:
            accepted = False
        report(6, accepted, {"fabricated_deletion_accepted_at_identical_base_head": accepted})

        with Store(work / "graph.sqlite") as store:
            evidence = lambda confidence: Evidence("graph.txt", 1, 1, "audit-fixture", confidence)
            parsed = ParsedFile(
                nodes=[Node(key, "PROCESS", key, evidence(100)) for key in ("A", "B", "C")],
                edges=[Edge("A", "C", "DEFINES", evidence(30)), Edge("A", "B", "DEFINES", evidence(100)), Edge("B", "C", "DEFINES", evidence(100))])
            store.put(FileRecord("graph.txt", "fixture", 1, "generic"), parsed)
            graph = store.traverse(["A"], Limits())
            report(7, graph["confidence"].get("C") == 30, {"C_confidence": graph["confidence"].get("C"), "available_path_confidence": 100})

        worker = parse("pkg/worker.py", "def run():\n    return 1\n")
        caller = parse("pkg/main.py", "from .worker import run\nrun()\n")
        with Store(work / "imports.sqlite") as store:
            store.put(FileRecord("pkg/worker.py", "worker", 1, "python"), worker)
            store.put(FileRecord("pkg/main.py", "main", 1, "python"), caller)
            graph = store.traverse(["file://pkg/worker.py"], Limits())
            reached = [n["key"] for n in graph["nodes"]]
        report(8, "file://pkg/main.py" not in reached, {"import_targets": [e.target for e in caller.edges if e.type == "IMPORTS"], "reached": reached})

        with Store(work / "boundary.sqlite") as store:
            store.put(FileRecord("standalone.sh", "script", 10, "shell"), parse("standalone.sh", "echo ready\n", mode="boundary"))
            rows = list(boundary_rows(store))
            node = store.node("file://standalone.sh")
        report(9, bool(node["boundary"]) and not rows, {"boundary_node": bool(node["boundary"]), "catalog_rows": rows})

        json_file = work / "redacted.json"
        write_json(json_file, {"token": 123})
        raw = json_file.read_text(encoding="utf-8")
        try:
            json.loads(raw)
            invalid = False
        except json.JSONDecodeError:
            invalid = True
        report(10, invalid, {"serialized_json": raw.strip(), "invalid_json": invalid})

        initial_repo = work / "initial"
        initial_repo.mkdir()
        (initial_repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
        initial_commit = initialize(initial_repo)
        try:
            analyze_mr(initial_repo, work / "initial-analysis", commit=initial_commit, cache=work / "initial-cache")
            error = None
        except EngineError as exc:
            error = str(exc)
        report(11, error is not None, {"root_commit_error": error})

    print(json.dumps({"findings": results, "reproduced": sum(r["reproduced"] for r in results)}, ensure_ascii=False, indent=2))
    return 1 if any(r["reproduced"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
