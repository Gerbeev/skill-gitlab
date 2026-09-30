from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
SRC = ENGINE / "src"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-repo"


class DeepIndexTests(unittest.TestCase):
    def test_deep_index_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(FIXTURE, repo)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            env_git = os_environ()
            env_git.update(
                {
                    "GIT_AUTHOR_NAME": "t",
                    "GIT_COMMITTER_NAME": "t",
                    "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_EMAIL": "t@t",
                }
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo,
                check=True,
                capture_output=True,
                env=env_git,
            )

            env = os_environ()
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
                self.assertEqual(proc.returncode, 0, msg=f"{cmd}: {proc.stdout}{proc.stderr}")

            analysis = repo / ".repository-analysis"
            self.assertTrue((analysis / "index" / "repository-index.sqlite").is_file())
            manifest = json.loads((analysis / "index" / "index-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "deep")
            self.assertTrue(manifest["stats"]["files"] >= 3)

            graph = json.loads((analysis / "graph" / "dependency-graph.json").read_text(encoding="utf-8"))
            targets = {e["target"] for e in graph["edges"]}
            self.assertTrue(any("payment_recon" in t for t in targets))


def os_environ():
    import os

    return dict(os.environ)


if __name__ == "__main__":
    unittest.main()
