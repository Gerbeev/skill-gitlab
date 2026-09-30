"""Render all four Copilot skills (requires jinja2)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
METHOD = SCRIPTS.parent
REPO = METHOD.parent.parent
SKILLS = REPO / "skills"
COPILOT = (
    "analyze-issue",
    "create-index",
    "create-graph",
    "analyze-mr",
    "update-issue",
)
DISPATCH_PREFIX = "read and follow "


class RenderFourSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        req = SKILLS / "mr-impact-method" / "scripts" / "requirements.txt"
        pip = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
            capture_output=True,
            text=True,
            check=False,
        )
        if pip.returncode != 0:
            self.skipTest(f"jinja2 not installable: {pip.stderr}")

        self._tmp = Path(tempfile.mkdtemp(prefix="mr-impact-render-"))
        self.project = self._tmp / "proj"
        self.project.mkdir()
        (self.project / "nested").mkdir()
        setup = subprocess.run(
            [
                sys.executable,
                str(SKILLS / "mr-impact-method" / "scripts" / "setup.py"),
                "--project-root",
                str(self.project),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(setup.returncode, 0, msg=setup.stdout + setup.stderr)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_each_skill_renders(self) -> None:
        render_py = self.project / "_mr-impact" / "scripts" / "render_skill.py"
        self.assertTrue(render_py.is_file())
        for name in COPILOT:
            skill_dir = SKILLS / name
            result = subprocess.run(
                [
                    sys.executable,
                    str(render_py),
                    "--project-root",
                    str(self.project),
                    "--skill",
                    str(skill_dir),
                ],
                cwd=self.project / "nested",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=f"{name}: {result.stdout}\n{result.stderr}")
            line = result.stdout.strip().splitlines()[-1]
            self.assertTrue(line.startswith(DISPATCH_PREFIX), msg=line)
            workflow = Path(line[len(DISPATCH_PREFIX) :].strip())
            self.assertTrue(workflow.is_file(), msg=str(workflow))
            body = workflow.read_text(encoding="utf-8")
            self.assertIn("workflow-discipline", body)


if __name__ == "__main__":
    unittest.main()
