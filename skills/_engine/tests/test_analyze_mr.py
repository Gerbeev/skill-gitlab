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


class AnalyzeMrTests(unittest.TestCase):
    def test_analyze_mr_chain(self) -> None:
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

            script = repo / "scripts" / "payment_recon.py"
            script.write_text("def reconcile_payments():\n    return False\n", encoding="utf-8")
            subprocess.run(["git", "add", script], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "change payment"],
                cwd=repo,
                check=True,
                capture_output=True,
                env=env_git,
            )

            catalog_dir = repo / ".repository-analysis" / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            catalog_dir.joinpath("boundary-catalog.json").write_text(
                """{
  "version": 1,
  "entities": [{
    "id": "job://AUTOSYS/PAYMENT_RECON_EOD",
    "kind": "autosys_job",
    "summary": "EOD payment reconciliation",
    "repos": [{"path": "payment-platform", "role": "definition", "confidence": 1.0}]
  }]
}""",
                encoding="utf-8",
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

            for name in (
                "mr-context.json",
                "changed-symbols.json",
                "impact-graph.json",
                "runtime-impact.json",
                "test-impact.json",
                "01-mr-analysis.md",
                "02-change-context.md",
                "03-impact-analysis.md",
                "04-test-plan.md",
                "boundary-hints.json",
            ):
                self.assertTrue((run_dir / name).is_file(), msg=name)

            runtime = json.loads((run_dir / "runtime-impact.json").read_text(encoding="utf-8"))
            jobs = {t["job_or_process"] for t in runtime.get("targets", [])}
            self.assertIn("PAYMENT_RECON_EOD", jobs)

            changed_symbols = json.loads(
                (run_dir / "changed-symbols.json").read_text(encoding="utf-8")
            )
            self.assertTrue(changed_symbols.get("index_partial_refresh"))
            self.assertFalse(changed_symbols.get("index_stale"))
            self.assertIn("scripts/payment_recon.py", changed_symbols.get("mr_refreshed_paths", []))
            touched = changed_symbols.get("symbols_touched_by_diff", [])
            recon = [s for s in touched if s.get("name") == "reconcile_payments"]
            self.assertTrue(recon, msg="expected reconcile_payments in symbols_touched_by_diff")
            self.assertEqual(recon[0].get("diff_match"), "line")
            self.assertIn("scripts/payment_recon.py", changed_symbols.get("changed_line_ranges", {}))

            hints = json.loads((run_dir / "boundary-hints.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(hints.get("hint_count", 0), 1)
            impact_md = (run_dir / "03-impact-analysis.md").read_text(encoding="utf-8")
            self.assertIn("Boundary catalog hints", impact_md)
            self.assertIn("PAYMENT_RECON_EOD", impact_md)

            proc2 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mr_impact",
                    "update-issue",
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, msg=proc2.stderr)
            self.assertTrue((run_dir / "05-issue-update.md").is_file())
            issue_update = json.loads((run_dir / "issue-update.json").read_text(encoding="utf-8"))
            self.assertEqual(issue_update.get("schema_version"), 1)
            self.assertFalse(issue_update.get("gitlab_apply"))
            self.assertTrue(issue_update.get("artifacts_present", {}).get("01-mr-analysis.md"))
            self.assertGreaterEqual(issue_update.get("mr_summary", {}).get("runtime_target_count", 0), 1)

            proc3 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mr_impact",
                    "validate-artifacts",
                    "--profile",
                    "mr-run",
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc3.returncode, 0, msg=proc3.stderr)

            proc4 = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "mr_impact",
                    "validate-artifacts",
                    "--profile",
                    "update-run",
                    "--run-dir",
                    str(run_dir),
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc4.returncode, 0, msg=proc4.stderr)


if __name__ == "__main__":
    unittest.main()
