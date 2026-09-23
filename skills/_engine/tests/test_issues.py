import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from .helpers import ROOT, REPOSITORY
from mr_impact.issues import analyze_issue, discover, extract_facts, template_slots
from mr_impact.safety import EngineError


class IssueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "project"
        shutil.copytree(ROOT / "tests/fixtures/issue", self.root)
        self.output = Path(self.tmp.name) / "output"

    def test_root_discovery_exact_two_outputs_and_separation(self):
        analyze_issue(self.root, self.output)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"00-issue-analysis.md", "01-generated-issue.md"})
        result = (self.output / "01-generated-issue.md").read_text()
        self.assertIn("reject negative exposure", result)
        self.assertIn("previous successful partition", result.split("## Assumptions")[1])
        self.assertNotIn("previous successful partition", result.split("## Acceptance Criteria")[1].split("## Constraints")[0])
        self.assertIn("negative, zero, and positive", result)
        self.assertIn("- [ ] Required tests pass", result)
        self.assertIn("Do not change the reporting schedule.", result.split("**Out of scope / non-goals**")[1].split("## Acceptance Criteria")[0])
        self.assertNotIn("Do not change the reporting schedule.", result.split("**Desired outcome**")[1].split("## Scope")[0])

    def test_explicit_scope_isolation(self):
        scope = self.root / "selected"
        scope.mkdir()
        (scope / "notes.md").write_text("## Acceptance Criteria\nThe system must retain audit rows.\n")
        analyze_issue(self.root, self.output, scope)
        result = (self.output / "01-generated-issue.md").read_text()
        self.assertIn("retain audit rows", result)
        self.assertNotIn("negative exposure", result)

    def test_source_names_do_not_discard_relevant_material(self):
        scope = self.root / "selected"
        scope.mkdir()
        inputs = {
            "01-requirements.md": "## Acceptance Criteria\nRetain audit rows.\n",
            "README.md": "## Problem\nDaily exports lose rows.\n",
            "02-prior-analysis.md": "## Constraint\nKeep the existing schedule.\n",
        }
        for name, text in inputs.items():
            (scope / name).write_text(text, encoding="utf-8")
        output = scope / "generated"
        template = self.root / "GITLAB_ISSUE_TEMPLATE.md"
        analyze_issue(self.root, output, scope)
        # Re-running must keep prior analysis as input but exclude this run's outputs.
        _, sources, _ = discover(self.root, scope, template, output)
        self.assertEqual(sources, inputs)
        result = (output / "01-generated-issue.md").read_text()
        self.assertIn("Retain audit rows", result)
        self.assertIn("Daily exports lose rows", result)

    def test_template_add_remove_rename_reorder(self):
        template = self.root / "GITLAB_ISSUE_TEMPLATE.md"
        template.write_text("# Work\n\n## New audit requirement\n\n{{requirement}}\n\n## Retention details\n")
        analyze_issue(self.root, self.output)
        result = (self.output / "01-generated-issue.md").read_text()
        self.assertIn("## New audit requirement", result)
        self.assertIn("## Retention details", result)
        self.assertNotIn("## Scope", result)
        self.assertLess(result.index("## New audit"), result.index("## Retention"))
        self.assertIn("Unresolved", result)

    def test_no_sources_does_not_invent_requirements(self):
        scope = self.root / "empty"
        scope.mkdir()
        analyze_issue(self.root, self.output, scope)
        result = (self.output / "01-generated-issue.md").read_text()
        self.assertIn("Unresolved", result)
        self.assertNotIn("reject negative", result)

    def test_interpretation_is_bound_to_template_and_scope(self):
        template = (self.root / "GITLAB_ISSUE_TEMPLATE.md").read_text()
        slot = next(s for s in template_slots(template) if s.label == "Acceptance Criteria")
        plan = {"template_sha256": hashlib.sha256(template.encode()).hexdigest(), "fills": {slot.id: [
            {"text": "Reject negative exposure before persistence.", "kind": "requirement",
             "evidence": [{"file": "notes.md", "start_line": 16, "end_line": 16}]}]}}
        path = Path(self.tmp.name) / "interpretation.json"
        path.write_text(json.dumps(plan))
        analyze_issue(self.root, self.output, interpretation=path)
        self.assertIn("Reject negative exposure", (self.output / "01-generated-issue.md").read_text())
        plan["fills"][slot.id][0]["evidence"][0]["file"] = "../outside.md"
        path.write_text(json.dumps(plan))
        with self.assertRaises(EngineError):
            analyze_issue(self.root, self.output, interpretation=path)
        plan["template_sha256"] = "stale"
        path.write_text(json.dumps(plan))
        with self.assertRaises(EngineError):
            analyze_issue(self.root, self.output, interpretation=path)

    def test_assumption_cannot_fill_requirement(self):
        template = (self.root / "GITLAB_ISSUE_TEMPLATE.md").read_text()
        slot = next(s for s in template_slots(template) if s.label == "Acceptance Criteria")
        plan = {"template_sha256": hashlib.sha256(template.encode()).hexdigest(), "fills": {slot.id: [
            {"text": "Assume audit is required.", "kind": "assumption", "evidence": [{"file": "notes.md", "start_line": 1, "end_line": 1}]}]}}
        path = Path(self.tmp.name) / "plan.json"
        path.write_text(json.dumps(plan))
        with self.assertRaises(EngineError):
            analyze_issue(self.root, self.output, interpretation=path)

    def test_actual_project_template_preserves_outcome_and_checklist(self):
        template = REPOSITORY / "docs/GITLAB_ISSUE_TEMPLATE.md"
        analyze_issue(self.root, self.output, template=template)
        generated = (self.output / "01-generated-issue.md").read_text()
        self.assertIn("Keep negative exposure", generated.split("**Desired outcome**")[1].split("## Scope")[0])
        self.assertNotIn("Unresolved", generated.split("## Delivery Checklist")[1].split("### Ready")[0])
        self.assertNotIn("<!--", generated)
        import re
        self.assertEqual(re.findall(r"^#{1,6} .+", template.read_text(), re.M), re.findall(r"^#{1,6} .+", generated, re.M))
        facts = extract_facts({"issue.md": generated})
        requirements = [f.text for f in facts if f.kind == "requirement"]
        self.assertFalse(any("Final implementation matches" in text or text == "--" for text in requirements))

    def test_changed_embedded_instruction_with_interpretation(self):
        template = self.root / "GITLAB_ISSUE_TEMPLATE.md"
        template.write_text("# Issue\n\n## Acceptance Criteria\n<!-- Use a single concise sentence. -->\n{{criterion}}\n\n## Optional notes\n<!-- Leave empty when unsupported. -->\n{{notes}}\n")
        text = template.read_text()
        slots = template_slots(text)
        plan = {"template_sha256": hashlib.sha256(text.encode()).hexdigest(), "fills": {slots[0].id: [
            {"text": "Reject negative exposure and preserve zero exposure.", "kind": "requirement",
             "evidence": [{"file": "notes.md", "start_line": 16, "end_line": 17}]}]}, "empty_slots": [slots[1].id]}
        path = Path(self.tmp.name) / "plan.json"
        path.write_text(json.dumps(plan))
        analyze_issue(self.root, self.output, interpretation=path)
        text = (self.output / "01-generated-issue.md").read_text()
        self.assertEqual(text.split("## Optional notes")[1].strip(), "")
        self.assertIn("Reject negative exposure and preserve zero exposure.", text)
