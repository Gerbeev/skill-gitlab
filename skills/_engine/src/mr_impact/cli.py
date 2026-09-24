"""Single command surface for the four skill operations and index maintenance."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .analysis import analyze_mr
from .catalog import aggregate
from .indexing import IndexConfig, build_index, index_dir, is_fresh
from .issues import analyze_issue, template_slots, update_issue, discover, source_fingerprints, template_instructions
from .models import Limits, record
from .safety import EngineError, read_text
from .storage import Store


def _index_options(parser):
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-files", type=int, default=1_000_000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--adapter", action="append")


def _limits_options(parser):
    for flag, default in (("max-depth", 8), ("max-nodes", 1000), ("max-edges", 4000),
                          ("confidence", 30), ("max-candidates", 20), ("cross-depth", 2), ("max-expansions", 100)):
        parser.add_argument("--" + flag, type=int, default=default)
    parser.add_argument("--edge-type", action="append", default=[])


def parser():
    main = argparse.ArgumentParser(prog="mr-impact", description="Local-first Issue and MR runtime impact analysis")
    commands = main.add_subparsers(dest="operation", required=True)
    issue = commands.add_parser("analyze-issue", help="Generate analysis and a current-template Issue description")
    issue.add_argument("--repo", type=Path, default=Path.cwd())
    issue.add_argument("--source", type=Path)
    issue.add_argument("--template", type=Path)
    issue.add_argument("--interpretation", type=Path)
    issue.add_argument("--require-review", action="store_true")
    issue.add_argument("--output", type=Path, required=True)
    index = commands.add_parser("index-repository", help="Build or refresh a persistent repository index")
    index.add_argument("--repo", type=Path, default=Path.cwd())
    index.add_argument("--cache", type=Path)
    modes = index.add_mutually_exclusive_group()
    modes.add_argument("--deep", action="store_true")
    modes.add_argument("--boundary", action="store_true")
    index.add_argument("--ref", default="HEAD")
    index.add_argument("--worktree", action="store_true")
    index.add_argument("--check", action="store_true", help="Check freshness without refreshing; exit 3 if stale")
    _index_options(index)
    mr = commands.add_parser("analyze-mr", help="Analyze a Git range, commit, or unified patch")
    mr.add_argument("--repo", type=Path, default=Path.cwd())
    mr.add_argument("--base")
    mr.add_argument("--head", default="HEAD")
    mr.add_argument("--commit")
    mr.add_argument("--patch", type=Path)
    mr.add_argument("--cache", type=Path)
    mr.add_argument("--catalog", type=Path)
    mr.add_argument("--issue", type=Path)
    mr.add_argument("--interpretation", type=Path)
    mr.add_argument("--require-review", action="store_true")
    mr.add_argument("--output", type=Path, required=True)
    mr.add_argument("--no-expand", action="store_true")
    _index_options(mr)
    _limits_options(mr)
    update = commands.add_parser("update-issue", help="Generate a local implementation-update preview")
    update.add_argument("--issue", type=Path, required=True)
    update.add_argument("--analysis", type=Path, required=True)
    update.add_argument("--output", type=Path, required=True)
    update.add_argument("--target", default="Unspecified local Issue")
    update.add_argument("--validation", type=Path)
    org = commands.add_parser("index-organization", help="Aggregate repository boundary indexes")
    org.add_argument("--catalog", type=Path, required=True)
    org.add_argument("--index", type=Path, action="append", required=True)
    org.add_argument("--replace", action="store_true")
    query = commands.add_parser("query-graph", help="Inspect bounded impact paths in an existing index")
    query.add_argument("--index", type=Path, required=True)
    query.add_argument("--seed", action="append", required=True)
    _limits_options(query)
    template = commands.add_parser("inspect-template", help="Show current template slots for an agent interpretation")
    template.add_argument("--template", type=Path, required=True)
    inspect = commands.add_parser("inspect-issue", help="Inspect source fingerprints and template slots before interpretation")
    inspect.add_argument("--repo", type=Path, default=Path.cwd())
    inspect.add_argument("--source", type=Path)
    inspect.add_argument("--template", type=Path)
    inspect.add_argument("--output", type=Path, required=True, help="Planned output directory to exclude from sources")
    return main


def _config(args):
    options = {key: getattr(args, key) for key in ("max_file_bytes", "max_files", "workers", "include", "exclude")}
    if args.adapter:
        options["adapters"] = args.adapter
    return IndexConfig(**options)


def _limits(args):
    return Limits(**{key: getattr(args, key) for key in ("max_depth", "max_nodes", "max_edges", "confidence", "max_candidates", "cross_depth", "max_expansions")},
                  edge_types=tuple(args.edge_type))


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.operation == "analyze-issue":
            result = analyze_issue(args.repo, args.output, args.source, args.template, args.interpretation, args.require_review)
        elif args.operation == "index-repository":
            if args.check:
                fresh = is_fresh(args.repo, index_dir(args.repo.resolve(), args.cache), args.ref, args.worktree, _config(args), "boundary" if args.boundary else "deep")
                print(json.dumps({"fresh": fresh}))
                return 0 if fresh else 3
            result = build_index(args.repo, args.cache, "boundary" if args.boundary else "deep", args.ref, args.worktree, _config(args))
        elif args.operation == "analyze-mr":
            result = analyze_mr(args.repo, args.output, args.base, args.head, args.patch, args.commit, args.cache,
                                args.catalog, args.issue, _limits(args), _config(args), not args.no_expand, args.interpretation, args.require_review)
        elif args.operation == "update-issue":
            result = update_issue(args.issue, args.analysis, args.output, args.target, args.validation)
        elif args.operation == "index-organization":
            result = aggregate(args.catalog, args.index, args.replace)
        elif args.operation == "query-graph":
            if not (args.index / "repository-index.sqlite").is_file():
                raise EngineError("Repository index does not exist")
            with Store(args.index / "repository-index.sqlite") as store:
                store.db.execute("BEGIN")
                result = store.traverse(args.seed, _limits(args))
        elif args.operation == "inspect-issue":
            import hashlib
            template = args.template or args.repo / "GITLAB_ISSUE_TEMPLATE.md"
            text = read_text(template)
            _, sources, warnings = discover(args.repo, args.source, template, args.output)
            result = {"template_sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "source_sha256": source_fingerprints(sources), "warnings": warnings,
                      "slots": [record(slot) for slot in template_slots(text)],
                      "instructions": template_instructions(text)}
        elif args.operation == "inspect-template":
            import hashlib
            text = read_text(args.template)
            result = {"template_sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "slots": [record(slot) for slot in template_slots(text)]}
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (EngineError, ValueError, OSError, sqlite3.Error, RecursionError, KeyError, TypeError) as exc:
        # Do not print raw exception payloads from parsers, databases or file contents.
        message = str(exc) if isinstance(exc, EngineError) else f"{type(exc).__name__}: input or storage operation failed"
        print("mr-impact: " + message, file=sys.stderr)
        return 2
