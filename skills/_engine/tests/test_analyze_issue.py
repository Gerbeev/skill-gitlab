from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
SRC = ENGINE / "src"
TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "analyze-issue"
    / "GITLAB_ISSUE_TEMPLATE.md"
)


class AnalyzeIssueTests(unittest.TestCase):
    def test_cli_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "in"
            input_dir.mkdir()
            (input_dir / "notes.md").write_text(
                "Problem: payments fail.\nJob PAYMENT_RECON_EOD runs scripts/payment_recon.py\n",
                encoding="utf-8",
            )
            run_dir = root / ".repository-analysis" / "run"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(SRC)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mr_impact",
                    "analyze-issue",
                    "--input-dir",
                    str(input_dir),
                    "--template",
                    str(TEMPLATE),
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue((run_dir / "00-issue-analysis.md").is_file())
            self.assertTrue((run_dir / "01-generated-issue.md").is_file())
            self.assertTrue((run_dir / "issue-intent.json").is_file())
            body = (run_dir / "00-issue-analysis.md").read_text(encoding="utf-8")
            self.assertIn("PAYMENT_RECON_EOD", body)
            intent = json.loads((run_dir / "issue-intent.json").read_text(encoding="utf-8"))
            self.assertEqual(intent.get("schema_version"), 1)
            self.assertIn("PAYMENT_RECON_EOD", intent.get("anchors", []))
            self.assertIn("notes.md", intent.get("input_files", []))
            self.assertIsInstance(intent.get("gaps"), list)


if __name__ == "__main__":
    unittest.main()
