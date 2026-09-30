from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mr_impact.index.pipeline import run_create_graph, run_create_index, run_deep_index
from mr_impact.issue.analyze import run_analyze_issue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mr_impact")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("create-index", "Build or refresh DEEP structural index (index/ only)"),
        ("create-graph", "Export dependency graph JSON from index SQLite (graph/ only)"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--analysis-root", type=Path, default=None)

    issue = sub.add_parser("analyze-issue", help="Produce 00-issue-analysis.md and 01-generated-issue.md")
    issue.add_argument("--input-dir", type=Path, required=True)
    issue.add_argument("--template", type=Path, required=True)
    issue.add_argument("--run-dir", type=Path, required=True)

    legacy = sub.add_parser("index-repository", help="Deprecated: use create-index and create-graph")
    legacy.add_argument("--mode", choices=("deep", "boundary"), default="deep")
    legacy.add_argument("--analysis-root", type=Path, default=None)

    args = parser.parse_args(argv)
    project_root = Path.cwd()

    try:
        if args.command == "create-index":
            summary = run_create_index(project_root, analysis_root=args.analysis_root)
            sys.stdout.write(
                f"index: {summary.get('files', 0)} files "
                f"({summary.get('files_parsed_this_run', 0)} parsed, "
                f"{summary.get('files_unchanged_skipped', 0)} unchanged) "
                f"head={str(summary.get('git_head', ''))[:12]}\n"
            )
            return 0

        if args.command == "create-graph":
            summary = run_create_graph(project_root, analysis_root=args.analysis_root)
            sys.stdout.write(
                f"graph: {summary.get('node_count', 0)} nodes, "
                f"{summary.get('edge_count', 0)} edges "
                f"head={str(summary.get('git_head', ''))[:12]}\n"
            )
            return 0

        if args.command == "analyze-issue":
            summary = run_analyze_issue(
                project_root,
                input_dir=args.input_dir,
                template_path=args.template,
                run_dir=args.run_dir,
            )
            sys.stdout.write(
                f"analyze-issue: {summary['input_files']} inputs, "
                f"{summary['anchors']} anchors, {summary['graph_edges']} graph edges\n"
                f"  {summary['analysis']}\n"
                f"  {summary['generated']}\n"
            )
            return 0

        if args.command == "index-repository":
            if args.mode != "deep":
                sys.stderr.write("error: only --mode deep is supported\n")
                return 2
            summary = run_deep_index(project_root, analysis_root=args.analysis_root)
            sys.stdout.write(f"indexed {summary.get('files', 0)} files (legacy)\n")
            return 0
    except FileNotFoundError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    except ValueError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1

    sys.stderr.write(
        f"error: unknown command '{args.command}'. "
        "Available: create-index, create-graph, analyze-issue\n"
    )
    return 2


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
