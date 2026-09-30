from __future__ import annotations

import unittest
from pathlib import Path

from mr_impact.cli_dispatch import build_parser, dispatch_command


class CliParserTests(unittest.TestCase):
    def test_all_commands_parse(self) -> None:
        parser = build_parser()
        for argv in (
            ["create-index"],
            ["create-graph", "--analysis-root", "/tmp/analysis"],
            ["analyze-issue", "--input-dir", "in", "--template", "t.md", "--run-dir", "run"],
            ["analyze-mr", "--revision", "main..HEAD", "--run-dir", "run"],
            ["update-issue", "--run-dir", "run"],
            ["validate-artifacts", "--profile", "mr-run", "--run-dir", "run"],
            ["index-repository", "--mode", "deep"],
        ):
            args = parser.parse_args(argv)
            self.assertTrue(args.command)

    def test_unknown_command_returns_two(self) -> None:
        class Args:
            command = "not-a-command"

        self.assertEqual(dispatch_command(Args(), Path.cwd()), 2)


if __name__ == "__main__":
    unittest.main()
