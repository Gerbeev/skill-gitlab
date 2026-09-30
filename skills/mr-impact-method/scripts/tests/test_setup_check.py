import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import setup_check  # noqa: E402


class SetupCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir(parents=True)
        self.skills = self.project / "skills"
        self.skills.mkdir(parents=True)

    def _skill_dir(self, name: str) -> Path:
        folder = self.skills / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "references").mkdir(exist_ok=True)
        (folder / "references" / "workflow-discipline.md").write_text("# discipline\n", encoding="utf-8")
        return folder

    def test_no_project_root_owes_nothing(self) -> None:
        folder = self._skill_dir("analyze-mr")
        self.assertEqual(setup_check.owed(folder, None), [])

    def test_missing_runtime_is_reported(self) -> None:
        folder = self._skill_dir("create-index")
        notes = setup_check.owed(folder, self.project)
        self.assertTrue(any("_mr-impact" in note for note in notes))

    def test_create_graph_without_index(self) -> None:
        runtime = self.project / "_mr-impact" / "scripts"
        runtime.mkdir(parents=True)
        (runtime / "render_skill.py").write_text("# stub\n", encoding="utf-8")
        engine = self.project / "skills" / "_engine" / "src" / "mr_impact"
        engine.mkdir(parents=True)
        (engine / "__init__.py").write_text("", encoding="utf-8")
        folder = self._skill_dir("create-graph")
        notes = setup_check.owed(folder, self.project)
        self.assertTrue(any("create-index" in note for note in notes))

    def test_analyze_mr_requires_index(self) -> None:
        runtime = self.project / "_mr-impact" / "scripts"
        runtime.mkdir(parents=True)
        (runtime / "render_skill.py").write_text("# stub\n", encoding="utf-8")
        engine = self.project / "skills" / "_engine" / "src" / "mr_impact"
        engine.mkdir(parents=True)
        (engine / "__init__.py").write_text("", encoding="utf-8")
        folder = self._skill_dir("analyze-mr")
        notes = setup_check.owed(folder, self.project)
        self.assertTrue(any("analyze-mr" in note or "create-index" in note for note in notes))

    def test_update_issue_without_mr_artifact(self) -> None:
        runtime = self.project / "_mr-impact" / "scripts"
        runtime.mkdir(parents=True)
        (runtime / "render_skill.py").write_text("# stub\n", encoding="utf-8")
        engine = self.project / "skills" / "_engine" / "src" / "mr_impact"
        engine.mkdir(parents=True)
        (engine / "__init__.py").write_text("", encoding="utf-8")
        folder = self._skill_dir("update-issue")
        notes = setup_check.owed(folder, self.project)
        self.assertTrue(any("01-mr-analysis.md" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
