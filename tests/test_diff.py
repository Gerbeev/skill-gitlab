import unittest

from .helpers import ROOT
from mr_impact.diff import parse_diff
from mr_impact.safety import EngineError


class DiffTests(unittest.TestCase):
    def test_add_delete_rename_and_zero_count(self):
        text = ('diff --git a/new.py b/new.py\nnew file mode 100644\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+x=1\n'
                'diff --git a/old.py b/old.py\ndeleted file mode 100644\n--- a/old.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x=0\n'
                'diff --git a/a.py b/b.py\nsimilarity index 100%\nrename from a.py\nrename to b.py\n')
        changes = parse_diff(text)
        self.assertEqual([c.status for c in changes], ["added", "deleted", "renamed"])
        self.assertEqual(changes[0].hunks[0].old_count, 0)
        self.assertEqual(changes[2].new_path, "b.py")

    def test_quoted_spaces_binary_and_context(self):
        text = 'diff --git "a/a file.py" "b/a file.py"\n--- "a/a file.py"\n+++ "b/a file.py"\n@@ -1,2 +1,2 @@\n same\n-old\n+new\n'
        change = parse_diff(text)[0]
        self.assertEqual(change.new_path, "a file.py")
        self.assertEqual(change.hunks[0].added, ["new"])
        self.assertTrue(parse_diff("diff --git a/a.bin b/a.bin\nBinary files a/a.bin and b/a.bin differ\n")[0].binary)

    def test_malformed_or_traversal_rejected(self):
        for text in ("not a diff", "diff --git a/../evil b/../evil\n", "--- a/a.py\n+++ b/a.py\n@@ -1,2 +1 @@\n-old\n+new\n"):
            with self.assertRaises(EngineError):
                parse_diff(text)
