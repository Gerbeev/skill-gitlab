import tempfile
import unittest
from pathlib import Path

from .helpers import ROOT, REPOSITORY, cli
from mr_impact.git import git
from mr_impact.safety import EngineError, redact, safe_relative


class SecurityTests(unittest.TestCase):
    def test_path_and_subprocess_boundaries(self):
        for path in ("../secret", "C:/secret", "/etc/passwd", "a/../../b"):
            with self.assertRaises(EngineError):
                safe_relative(path)
        with self.assertRaises(EngineError):
            git(ROOT, "push", "origin")

    def test_secret_redaction(self):
        value = redact('password=secret token=glpat-abcd https://name:password@example.invalid/path')
        self.assertNotIn("=secret", value)
        self.assertNotIn("glpat-abcd", value)
        self.assertNotIn("name:password", value)

    def test_cli_errors_and_no_remote_write_option(self):
        result = cli("analyze-mr", "--output", "unused")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Provide a base", result.stderr)
        result = cli("update-issue", "--apply")
        self.assertNotEqual(result.returncode, 0)

    def test_four_discoverable_thin_wrappers(self):
        skills = REPOSITORY / ".github/skills"
        operations = {"analyze-issue", "index-repository", "analyze-mr", "update-issue"}
        self.assertEqual({p.name for p in skills.iterdir()}, operations)
        for name in operations:
            files = list((skills / name).iterdir())
            self.assertEqual([p.name for p in files], ["SKILL.md"])
            text = files[0].read_text()
            self.assertTrue(text.startswith(f"---\nname: {name}\ndescription: "))
            self.assertIn(f"`{name}`", text)
            import re
            for target in re.findall(r"\]\(([^)]+)\)", text):
                self.assertTrue((files[0].parent / target.split("#", 1)[0]).is_file(), target)
