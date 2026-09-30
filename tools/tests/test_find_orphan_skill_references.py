from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tools" / "find_orphan_skill_references.py"


def _load():
    spec = importlib.util.spec_from_file_location("find_orphan_skill_references", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FindOrphanTests(unittest.TestCase):
    def test_detects_unlinked_reference(self) -> None:
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills" / "demo-skill" / "references"
            skills.mkdir(parents=True)
            orphan = skills / "orphan-only.md"
            orphan.write_text("# orphan\n", encoding="utf-8")
            (skills.parent / "workflow.md").write_text("# wf\n", encoding="utf-8")
            original = mod.SKILLS
            mod.SKILLS = Path(tmp) / "skills"
            try:
                found = mod.find_orphans()
            finally:
                mod.SKILLS = original
            self.assertIn("demo-skill/references/orphan-only.md", found)

    def test_linked_reference_not_orphan(self) -> None:
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "skills" / "demo-skill"
            ref_dir = base / "references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "linked.md").write_text("# linked\n", encoding="utf-8")
            (base / "step-01.md").write_text("follow references/linked.md\n", encoding="utf-8")
            original = mod.SKILLS
            mod.SKILLS = Path(tmp) / "skills"
            try:
                found = mod.find_orphans()
            finally:
                mod.SKILLS = original
            self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
