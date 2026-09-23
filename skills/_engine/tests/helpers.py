import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))


def command(root, *args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def initialize(root, fixture=None):
    root.mkdir(parents=True, exist_ok=True)
    if fixture:
        shutil.copytree(ROOT / "tests" / "fixtures" / fixture, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    command(root, "init", "--quiet")
    command(root, "config", "user.name", "Fixture Author")
    command(root, "config", "user.email", "fixture@example.invalid")
    command(root, "config", "core.autocrlf", "false")
    command(root, "config", "commit.gpgsign", "false")
    command(root, "add", ".")
    command(root, "commit", "--quiet", "--allow-empty", "-m", "Fixture baseline")
    return command(root, "rev-parse", "HEAD")


def commit(root, message="Fixture change"):
    command(root, "add", ".")
    command(root, "commit", "--quiet", "-m", message)
    return command(root, "rev-parse", "HEAD")


def cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "mr-impact.py"), *map(str, args)],
                          capture_output=True, text=True, cwd=ROOT)
