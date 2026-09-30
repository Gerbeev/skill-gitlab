#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Validate cross-file references under skills/ (MR Impact).

Checks skill-relative backticked paths, file:{project-root}/… in TOML, and
{project-root}/… references in prose. Runtime-only trees (.repository-analysis/run/)
are skipped when the path does not exist.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib

sys.dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR_NAME = "skills"

SCAN_EXTENSIONS = {".md", ".toml"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".pytest_cache", "_engine"}
STRAY_ALLOWLIST = frozenset({"README.md"})

PROJECT_ROOT_REF = re.compile(r"\{project-root\}/([^\s'\"<>})\]`]+)")
FILE_PREFIX_REF = re.compile(r"file:\{project-root\}/([^\s'\"<>})\]`]+)")
BACKTICK_REF = re.compile(r"`([^`\s]+/[^`\s]+\.(?:md|toml|json|py))`")
ABS_PATH_LEAK = re.compile(r"/Users/|/home/|\b[A-Za-z]:[\\/]")

RUNTIME_PREFIXES = (
    ".repository-analysis/",
    "_mr-impact/",
)

DOC_PLACEHOLDER_SUFFIXES = ("/path",)
DOC_PLACEHOLDER_NAMES = frozenset({"path"})

UNRESOLVABLE = (
    "{skill-root}",
    "{revision}",
    "<",
    "{{",
    "*",
)


class Ref:
    __slots__ = ("file", "raw", "kind", "line")

    def __init__(self, file: str, raw: str, kind: str, line: int | None = None) -> None:
        self.file = file
        self.raw = raw
        self.kind = kind
        self.line = line


def _repo_path(path: str, project_root: str) -> str:
    return os.path.relpath(path, project_root).replace(os.sep, "/")


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", "", match.group(0))


def strip_code_blocks(content: str) -> str:
    return re.sub(r"```.*?```", _blank, content, flags=re.DOTALL)


def get_source_files(skills_dir: str) -> list[str]:
    files: list[str] = []

    def walk(current: str) -> None:
        with os.scandir(current) as it:
            entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            if entry.is_dir(follow_symlinks=False):
                walk(entry.path)
            elif entry.is_file() and os.path.splitext(entry.name)[1] in SCAN_EXTENSIONS:
                files.append(entry.path)

    walk(skills_dir)
    return files


def _is_resolvable(ref_str: str) -> bool:
    if any(token in ref_str for token in UNRESOLVABLE):
        return False
    return True


def _skip_project_path(rel: str) -> bool:
    cleaned = rel.rstrip("/")
    if cleaned in DOC_PLACEHOLDER_NAMES:
        return True
    if any(cleaned.endswith(suffix) for suffix in DOC_PLACEHOLDER_SUFFIXES):
        return True
    for prefix in RUNTIME_PREFIXES:
        if cleaned == prefix.rstrip("/") or cleaned.startswith(prefix):
            return True
    return False


def extract_toml_file_refs(file_path: str, content: str) -> list[Ref]:
    refs: list[Ref] = []
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return refs
    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        return refs
    facts = workflow.get("persistent_facts")
    if not isinstance(facts, list):
        return refs
    for entry in facts:
        if not isinstance(entry, str) or not entry.startswith("file:{project-root}/"):
            continue
        rel = entry.removeprefix("file:{project-root}/")
        refs.append(Ref(file_path, rel, "project-file", 1))
    return refs


def extract_markdown_refs(file_path: str, content: str) -> list[Ref]:
    refs: list[Ref] = []
    stripped = strip_code_blocks(content)
    for match in PROJECT_ROOT_REF.finditer(stripped):
        raw = match.group(1).rstrip(").,;")
        if not _is_resolvable(raw) or _skip_project_path(raw):
            continue
        line = stripped.count("\n", 0, match.start()) + 1
        refs.append(Ref(file_path, raw, "project-root", line))
    for match in BACKTICK_REF.finditer(stripped):
        raw = match.group(1)
        if any(ch in raw for ch in "*<{"):
            continue
        if raw.startswith(("/", "./", "../", ".", "@")):
            continue
        if not _is_resolvable(raw):
            continue
        line = stripped.count("\n", 0, match.start()) + 1
        refs.append(Ref(file_path, raw, "skill-relative", line))
    return refs


def resolve_ref(ref: Ref, skills_dir: str, project_root: str) -> str | None:
    if ref.kind in ("project-root", "project-file"):
        if _skip_project_path(ref.raw):
            return None
        return os.path.normpath(os.path.join(project_root, ref.raw))

    if ref.kind == "skill-relative":
        roots = [os.path.dirname(ref.file)]
        rel = os.path.relpath(ref.file, skills_dir)
        parts = rel.split(os.sep)
        if not rel.startswith("..") and len(parts) > 1:
            skill_root = os.path.join(skills_dir, parts[0])
            if skill_root not in roots:
                roots.append(skill_root)
        first_dir = ref.raw.split("/")[0]
        flag: str | None = None
        for root in roots:
            candidate = os.path.normpath(os.path.join(root, ref.raw))
            if os.path.exists(candidate):
                return candidate
            if flag is None and os.path.isdir(os.path.join(root, first_dir)):
                flag = candidate
        return flag
    return None


def check_absolute_leaks(file_path: str, content: str) -> list[tuple[int, str]]:
    stripped = strip_code_blocks(content)
    leaks: list[tuple[int, str]] = []
    for i, line in enumerate(stripped.split("\n"), start=1):
        if ABS_PATH_LEAK.search(line):
            leaks.append((i, line.strip()))
    return leaks


def run(project_root: str, *, strict: bool = False, verbose: bool = False) -> int:
    skills_dir = os.path.join(project_root, SKILLS_DIR_NAME)
    if not os.path.isdir(skills_dir):
        print(f"skills directory not found: {skills_dir}", file=sys.stderr)
        return 1

    print(f"\nValidating file references in: {skills_dir}")
    mode = "STRICT" if strict else "WARNING"
    print(f"Mode: {mode}\n")

    stray: list[str] = []
    with os.scandir(skills_dir) as it:
        for entry in it:
            if entry.is_file(follow_symlinks=False) and entry.name not in STRAY_ALLOWLIST:
                stray.append(entry.name)

    broken = 0
    leaks_count = 0
    files = get_source_files(skills_dir)

    for file_path in files:
        rel_file = _repo_path(file_path, project_root)
        with open(file_path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        ext = os.path.splitext(file_path)[1]
        refs = extract_toml_file_refs(file_path, content) if ext == ".toml" else []
        refs.extend(extract_markdown_refs(file_path, content))

        file_broken: list[tuple[Ref, str]] = []
        for ref in refs:
            resolved = resolve_ref(ref, skills_dir, project_root)
            if resolved is None:
                continue
            if not os.path.exists(resolved):
                file_broken.append((ref, resolved))
                broken += 1

        file_leaks = check_absolute_leaks(file_path, content)
        leaks_count += len(file_leaks)

        if not (file_broken or file_leaks) and not verbose:
            continue
        if file_broken or file_leaks or (verbose and refs):
            print(rel_file)
            if verbose:
                for ref in refs:
                    print(f"  [scan] {ref.raw}")
            for ref, resolved in file_broken:
                loc = f"line {ref.line}" if ref.line else ""
                print(f"  [BROKEN] {ref.raw} ({loc}) -> {_repo_path(resolved, project_root)}")
            for line_no, text in file_leaks:
                print(f"  [ABS-PATH] line {line_no}: {text}")

    if stray:
        print(f"\n{SKILLS_DIR_NAME}/")
        for name in stray:
            print(f"  [STRAY] {name}: files may not sit directly under skills/")

    has_issues = broken > 0 or leaks_count > 0 or bool(stray)
    print(f"\n{'-' * 50}")
    print(f"Files scanned: {len(files)}")
    print(f"Broken references: {broken}")
    print(f"Absolute path leaks: {leaks_count}")
    print(f"Stray files: {len(stray)}")
    if has_issues and strict:
        print("\n[STRICT] Exiting with failure.")
        return 1
    if has_issues:
        print("\nRun with --strict to fail CI on these issues.")
    else:
        print("\nAll checked references resolve.")
    return 0 if not (has_issues and strict) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate skills/ cross-file references.")
    parser.add_argument("--project-root", default=PROJECT_ROOT)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    return run(os.path.abspath(args.project_root), strict=args.strict, verbose=args.verbose)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
