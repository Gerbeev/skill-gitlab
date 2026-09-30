from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "tools" / "validate_file_refs.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_file_refs", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


vf = _load()


class ValidateFileRefsTests(unittest.TestCase):
    def test_skill_relative_reference_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "skills" / "demo-skill" / "references"
            skills.mkdir(parents=True)
            target = skills / "ok.md"
            target.write_text("ok\n", encoding="utf-8")
            step = root / "skills" / "demo-skill" / "step-01.md"
            step.write_text("Read `references/ok.md`.\n", encoding="utf-8")
            refs = vf.extract_markdown_refs(str(step), step.read_text(encoding="utf-8"))
            self.assertEqual(len(refs), 1)
            resolved = vf.resolve_ref(refs[0], str(root / "skills"), str(root))
            self.assertTrue(resolved and Path(resolved).is_file())

    def test_broken_project_file_in_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "demo-skill"
            skill.mkdir(parents=True)
            toml = skill / "customize.toml"
            toml.write_text(
                '[workflow]\npersistent_facts = ["file:{project-root}/docs/missing.md"]\n',
                encoding="utf-8",
            )
            code = vf.run(str(root), strict=True)
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
