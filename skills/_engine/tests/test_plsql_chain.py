from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
SRC = ENGINE / "src"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-repo"


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
    )
    return env


class PlsqlChainMrTests(unittest.TestCase):
    def test_plsql_line_change_reaches_autosys_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(FIXTURE, repo)
            env_git = _git_env()
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo,
                check=True,
                capture_output=True,
                env=env_git,
            )

            env = dict(os.environ)
            env["PYTHONPATH"] = str(SRC)
            for cmd in ("create-index", "create-graph"):
                proc = subprocess.run(
                    [sys.executable, "-m", "mr_impact", cmd],
                    cwd=repo,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=f"{cmd}: {proc.stderr}")

            sql = repo / "sql" / "pkg.sql"
            sql.write_text(
                sql.read_text(encoding="utf-8").replace(
                    "ledger_pkg.post_entry", "ledger_pkg.post_entry_v2"
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "add", sql], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "plsql line"],
                cwd=repo,
                check=True,
                capture_output=True,
                env=env_git,
            )

            run_dir = repo / ".repository-analysis" / "run"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mr_impact",
                    "analyze-mr",
                    "--revision",
                    "HEAD~1..HEAD",
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            runtime = json.loads((run_dir / "runtime-impact.json").read_text(encoding="utf-8"))
            primary = runtime.get("primary_qa_targets", [])
            self.assertTrue(primary, msg="expected primary QA target")
            job = primary[0]
            self.assertEqual(job["job"], "PAYMENT_RECON_EOD")
            path_nodes = [h["node"] for h in job.get("path", [])]
            joined = " ".join(path_nodes).lower()
            self.assertIn("payment_pkg.run", joined)
            self.assertIn("paymentservice.cs", joined)
            self.assertIn("payment_recon", joined)

            touched = json.loads((run_dir / "changed-symbols.json").read_text(encoding="utf-8"))
            names = {s.get("name") for s in touched.get("symbols_touched_by_diff", [])}
            self.assertIn("payment_pkg.run", names)


if __name__ == "__main__":
    unittest.main()
