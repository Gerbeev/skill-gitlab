"""MR orchestration: deterministic changes, bounded runtime discovery, and QA reports."""

import hashlib
import json
import re
from contextlib import ExitStack
from pathlib import Path

from .adapters import RUNTIME_TYPES
from .catalog import lookup, repository_matches
from .diff import map_symbols, parse_diff
from .git import git, repository_id, resolve
from .indexing import IndexConfig, build_index
from .issues import extract_facts
from .models import Limits, RuntimeTarget, record
from .safety import EngineError, read_json, read_text, write_json, write_text
from .storage import Store


def targets_from_graph(graph, repository, prefix=None, cap=100):
    targets = []
    for node in graph["nodes"]:
        if node["type"] not in RUNTIME_TYPES:
            continue
        path = (prefix or []) + graph["paths"][node["key"]]
        confidence = min([cap, graph["confidence"][node["key"]]] + [e["confidence"] for e in (prefix or [])])
        if not node["defined"]:
            impact = "UNRESOLVED"
        elif confidence < 90:
            impact = "POTENTIALLY_AFFECTED"
        else:
            impact = "DIRECTLY_AFFECTED" if len(path) <= 1 else "TRANSITIVELY_AFFECTED"
        reason = ("Dependency path connects an MR change to this operational definition." if path
                  else "The operational definition itself changed.")
        execute = (f"Locate and verify the definition of {node['name']} before execution." if not node["defined"]
                   else f"Run or validate {node['type']} {node['name']} in the approved QA environment.")
        verify = [f"Verify completion and inspect the output of {node['name']} against its documented contract."]
        tables = [e["from"] for e in path if e["from"].startswith("table://")]
        tables += [e["to"] for e in path if e["to"].startswith("table://")]
        if tables:
            verify.append("Compare affected data and downstream consumption for " + ", ".join(sorted(set(tables))) + ".")
        if any(e["type"] == "DEPENDS_ON" for e in path):
            verify.append("Verify the recorded scheduler dependency and downstream start/completion behavior.")
        targets.append(record(RuntimeTarget(node["name"], node["type"], repository, impact, reason, path, confidence, execute, verify, node["key"])))
    return targets


def _path_text(path):
    if not path:
        return "Changed definition (direct evidence in the diff)."
    return " -> ".join([path[0]["from"]] + [
        f"[{edge['repository']}] {edge['to']}" if edge["type"] == "ORGANIZATION_LOOKUP" else edge["to"] for edge in path])


def _classify_file(path):
    lower = path.lower()
    if "test" in lower:
        return "test"
    if lower.endswith((".md", ".txt", ".rst")):
        return "documentation"
    if "ci" in lower or ".github/workflows/" in lower or lower.endswith((".csproj", ".sbt", "pom.xml", "pyproject.toml")):
        return "build / dependency / CI"
    if lower.endswith((".yaml", ".yml", ".xml", ".json", ".config")):
        return "configuration"
    return "implementation"


def _behavior(changes):
    patterns = {"error handling": r"\b(?:throw|raise|catch|except|error)\b",
                "retry / fallback": r"\b(?:retry|fallback|backoff)\b",
                "control flow / validation": r"\b(?:if|else|require|assert|validate|return)\b",
                "persistence / schema": r"\b(?:insert|update|delete|merge|create|alter|saveAsTable)\b",
                "security / privacy": r"\b(?:auth|permission|encrypt|password|token)\b"}
    results = []
    for change in changes:
        for number, hunk in enumerate(change.hunks):
            text = "\n".join(hunk.added + hunk.removed)
            for name, pattern in patterns.items():
                if re.search(pattern, text, re.I):
                    results.append({"area": name, "classification": "hypothesis requiring verification",
                                    "file": change.new_path or change.old_path, "hunk": number,
                                    "reason": "Changed lines contain constructs associated with this behavior; runtime semantics are not proven."})
    return results


def analyze_mr(root: Path, output: Path, base: str | None = None, head="HEAD", patch: Path | None = None,
               commit: str | None = None, cache: Path | None = None, catalog: Path | None = None,
               issue: Path | None = None, limits: Limits | None = None, config: IndexConfig | None = None,
               expand_candidates=True, interpretation: Path | None = None):
    root = root.resolve()
    limits = limits or Limits()
    config = config or IndexConfig()
    if commit:
        if base or patch:
            raise EngineError("--commit cannot be combined with --base or --patch")
        head = resolve(root, commit)
        base = head + "^"
    if not base and not patch:
        raise EngineError("Provide a base revision, a commit, or a patch")
    head_id = resolve(root, head)
    base_id = resolve(root, base) if base else None
    diff = read_text(patch, 20_000_000) if patch else git(root, "diff", "--no-ext-diff", "--no-textconv", "--find-renames",
              "--unified=0", "--src-prefix=a/", "--dst-prefix=b/", base_id, head_id, "--", max_bytes=20_000_000).decode("utf-8", errors="replace")
    changes = parse_diff(diff)
    warnings = []
    if patch:
        warnings.append("External patch analyzed against the selected head. Supply --base for removed-symbol and before-change graph evidence.")
    indexed = build_index(root, cache, "deep", head_id, config=config)
    previous = build_index(root, cache, "deep", base_id, config=config, slot="base") if base_id else None
    warnings.extend(indexed["statistics"]["warnings"])
    with ExitStack() as stack:
        store = stack.enter_context(Store(Path(indexed["directory"]) / "repository-index.sqlite"))
        before = stack.enter_context(Store(Path(previous["directory"]) / "repository-index.sqlite")) if previous else None
        if patch:
            for change in changes:
                if change.new_path and not store.db.execute("SELECT 1 FROM files WHERE path=?", (change.new_path,)).fetchone():
                    raise EngineError("Patch head file is absent from the selected indexed revision")
                if change.new_path and change.hunks:
                    data = git(root, "cat-file", "blob", f"{head_id}:{change.new_path}", max_bytes=config.max_file_bytes).decode("utf-8", errors="replace").splitlines()
                    for hunk in change.hunks:
                        # Added lines must occur in the corresponding head hunk, including context.
                        region = data[max(0, hunk.new_start - 1):hunk.new_start - 1 + hunk.new_count]
                        cursor = 0
                        for added in hunk.added:
                            try:
                                cursor = region.index(added, cursor) + 1
                            except ValueError as exc:
                                raise EngineError("Patch payload does not match the selected head revision") from exc
        mappings = map_symbols(changes, store, before)
        seeds = [m["symbol"]["id"] for m in mappings if m["side"] == "head"]
        # File evidence is necessary for configuration, runtime definitions and lexical fallbacks.
        seeds += ["file://" + c.new_path for c in changes if c.new_path]
        graph = store.traverse(seeds, limits)
        graphs = [{"repository": repository_id(root), "revision": head_id, **graph}]
        targets = targets_from_graph(graph, repository_id(root))
        if before:
            old_seeds = [m["symbol"]["id"] for m in mappings if m["side"] == "base"]
            old_seeds += ["file://" + c.old_path for c in changes if c.old_path]
            old_graph = before.traverse(old_seeds, limits)
            old_graph["confidence"] = {key: min(60, value) for key, value in old_graph["confidence"].items()}
            graphs.append({"repository": repository_id(root), "revision": base_id, "side": "base", **old_graph})
            for target in targets_from_graph(old_graph, repository_id(root), cap=60):
                target["reason"] = "Before-change dependency: verify removal, compatibility, or migration. " + target["reason"]
                target["execute"] = "Verify whether this before-change target still exists; " + target["execute"]
                targets.append(target)
        for group in graphs:
            if group["truncated"]:
                warnings.append("Local graph traversal reached a configured limit; impact coverage is partial.")
        candidates = []
        if catalog:
            seen = {repository_id(root)}
            frontier = [(group, 0) for group in graphs]
            while frontier:
                local, depth = frontier.pop(0)
                if depth >= limits.cross_depth:
                    if any(n["boundary"] for n in local["nodes"]):
                        warnings.append("Cross-repository depth limit reached; further downstream impact is not explored.")
                    continue
                boundaries = [n for n in local["nodes"] if n["boundary"] and local["confidence"][n["key"]] >= limits.confidence]
                for node in boundaries:
                    path_conf = local["confidence"][node["key"]]
                    remaining = limits.max_candidates - len(candidates)
                    matches = lookup(catalog, node["key"], limits.confidence, max(1, remaining + 1), tuple(seen))
                    for match in matches:
                        rid = match["repository"]
                        if rid in seen:
                            continue
                        if len(candidates) >= limits.max_candidates:
                            warnings.append("Cross-repository candidate limit reached; organization coverage is partial.")
                            break
                        seen.add(rid)
                        candidates.append({"repository": rid, "entity": node["key"], "role": match["role"],
                                           "confidence": min(path_conf, match["confidence"]), "expanded": False,
                                           "catalog_commit": match["commit_id"]})
                        if not expand_candidates:
                            warnings.append(f"Candidate {rid} requires deep expansion to identify runtime targets.")
                            continue
                        candidate_root = Path(match["root"])
                        if not candidate_root.is_dir():
                            warnings.append(f"Candidate repository unavailable locally: {rid}")
                            continue
                        try:
                            current_head = resolve(candidate_root, "HEAD")
                            stale = current_head != match["commit_id"]
                            if stale:
                                warnings.append(f"Stale catalog candidate {rid}; using recorded revision {match['commit_id']} for reproducibility.")
                            shared = repository_matches(catalog, rid, [n["key"] for n in boundaries], limits.confidence)
                            initial_paths, initial_confidence = {}, {}
                            for observation in shared:
                                entity = observation["entity"]
                                confidence = min(local["confidence"][entity], observation["confidence"], 60 if stale else 100)
                                bridge = {"from": entity, "to": entity, "type": "ORGANIZATION_LOOKUP",
                                          "direction": "reverse", "confidence": confidence,
                                          "evidence": observation["evidence"], "repository": rid,
                                          "catalog_commit": match["commit_id"]}
                                initial_paths[entity] = local["paths"][entity] + [bridge]
                                initial_confidence[entity] = confidence
                            candidate_index = build_index(candidate_root, cache, "deep", match["commit_id"], config=config)
                            with Store(Path(candidate_index["directory"]) / "repository-index.sqlite") as candidate_store:
                                subgraph = candidate_store.traverse(list(initial_paths), limits, initial_paths, initial_confidence)
                        except EngineError:
                            warnings.append(f"Candidate {rid} could not be indexed at its catalog revision.")
                            continue
                        candidates[-1]["expanded"] = True
                        candidates[-1]["entities"] = list(initial_paths)
                        graphs.append({"repository": rid, "revision": match["commit_id"], **subgraph})
                        targets.extend(targets_from_graph(subgraph, rid))
                        if subgraph["truncated"]:
                            warnings.append(f"Candidate {rid} graph traversal reached a limit.")
                        frontier.append((subgraph, depth + 1))
        unique = {}
        defined_entities = {t["entity"] for t in targets if t["impact"] != "UNRESOLVED"}
        for target in targets:
            if target["impact"] == "UNRESOLVED" and target["entity"] in defined_entities:
                continue
            key = (target["repository"], target["type"], target["target"])
            if key not in unique or target["confidence"] > unique[key]["confidence"]:
                unique[key] = target
        targets = sorted(unique.values(), key=lambda t: (-t["confidence"], t["repository"], t["target"]))
        tests = []
        seen_tests = set()
        for group in graphs:
            for node in group["nodes"]:
                if node["type"] == "TEST":
                    test_identity = (group["repository"], node["key"])
                    if test_identity in seen_tests:
                        continue
                    seen_tests.add(test_identity)
                    path = group["paths"][node["key"]]
                    tests.append({"file": node["name"], "repository": group["repository"],
                                  "classification": "direct" if len(path) <= 1 else "indirect",
                                  "path": path, "confidence": group["confidence"][node["key"]], "executed": False})
        if not tests:
            warnings.append("No related test definition was reached; this is a missing-coverage candidate, not proof that tests do not exist.")
        context_mappings = []
        if issue:
            facts = extract_facts({issue.name: read_text(issue)})
            for fact in facts:
                if fact.kind not in {"requirement", "non_goal", "constraint"}:
                    continue
                words = set(re.findall(r"[a-zA-Z]{4,}", fact.text.lower())) - {"should", "must", "with", "that", "this", "from"}
                related = []
                for change in changes:
                    changed_text = " ".join([change.new_path or change.old_path] + [s for h in change.hunks for s in h.added + h.removed]).lower()
                    if words & set(re.findall(r"[a-zA-Z]{4,}", changed_text)):
                        related.append(change.new_path or change.old_path)
                context_mappings.append({"statement": fact.text, "kind": fact.kind, "evidence": f"{fact.file}:{fact.line}",
                                         "related_files": related, "confidence": "CANDIDATE",
                                         "finding": "Lexical context association; manually verify semantic relevance." if related else "No lexical association found; context remains unresolved."})
        behavior = _behavior(changes)
        if interpretation:
            plan = read_json(interpretation)
            if plan.get("head") != head_id or plan.get("diff_sha256") != hashlib.sha256(diff.encode()).hexdigest():
                raise EngineError("MR interpretation does not match the current diff and head")
            findings = plan.get("findings", [])
            if not isinstance(findings, list) or len(findings) > 500:
                raise EngineError("Invalid MR interpretation findings")
            for finding in findings:
                classification = finding.get("classification")
                change_index, hunk_index = finding.get("change_index"), finding.get("hunk_index")
                if classification not in {"confirmed", "likely", "hypothesis requiring verification"}:
                    raise EngineError("Invalid behavioral confidence classification")
                if not isinstance(change_index, int) or not 0 <= change_index < len(changes):
                    raise EngineError("Interpretation references an unknown change")
                change = changes[change_index]
                if not isinstance(hunk_index, int) or not 0 <= hunk_index < len(change.hunks):
                    raise EngineError("Interpretation references an unknown hunk")
                if not isinstance(finding.get("summary"), str) or not isinstance(finding.get("validation"), str):
                    raise EngineError("Behavioral interpretation requires a summary and a validation scenario")
                behavior.append({"area": "agent interpretation", "classification": classification,
                                 "file": change.new_path or change.old_path, "hunk": hunk_index,
                                 "reason": finding["summary"], "validation": finding["validation"]})
        context = {"schema_version": 1, "repository": repository_id(root), "base": base_id, "head": head_id,
                   "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(), "changes": [record(c) for c in changes],
                   "behavior": behavior, "issue_context": context_mappings, "candidates": candidates,
                   "warnings": list(dict.fromkeys(warnings)), "limits": record(limits),
                   "completion_context": {"test_execution": "not performed", "MR_review_approval": "not available locally",
                                          "documentation_changed": any(_classify_file(c.new_path or c.old_path) == "documentation" for c in changes)}}
        output.mkdir(parents=True, exist_ok=True)
        for filename, value in (("mr-context.json", context), ("changed-symbols.json", {"mappings": mappings}),
                                ("impact-graph.json", {"graphs": graphs}), ("runtime-impact.json", {"targets": targets}),
                                ("test-impact.json", {"tests": tests, "missing_coverage_candidate": not bool(tests)})):
            write_json(output / filename, value)
        _reports(output, context, mappings, graphs, targets, tests)
        context["artifact_sha256"] = {filename: hashlib.sha256((output / filename).read_bytes()).hexdigest()
                                      for filename in ("runtime-impact.json", "01-mr-analysis.md")}
        write_json(output / "mr-context.json", context)
        return {"output": str(output), "changed_files": len(changes), "runtime_targets": len(targets),
                "candidate_repositories": len(candidates), "warnings": context["warnings"]}


def _reports(output, context, mappings, graphs, targets, tests):
    lines = ["# Merge Request analysis", "", f"Revision: `{context['base'] or 'external patch'}..{context['head']}`.", "",
             f"Observed scope: changed files: {len(context['changes'])}; symbol mappings: {len(mappings)}; runtime targets: {len(targets)}.", "",
             "## Changed areas", ""]
    for change in context["changes"]:
        path = change["new_path"] or change["old_path"]
        lines.append(f"- **{change['status']}** `{path}` ({_classify_file(path)}); hunks: {len(change['hunks'])}.")
    lines += ["", "## Behavioral verification hypotheses", ""]
    lines += [f"- **{b['classification']}**: {b['area']} at `{b['file']}`, hunk {b['hunk'] + 1}. {b['reason']}" for b in context["behavior"]]
    if not context["behavior"]:
        lines.append("No behavioral claim was inferred from the changed constructs. Inspect the deterministic diff evidence.")
    lines += ["", "## Limitations", ""] + [f"- {w}" for w in context["warnings"]]
    lines += ["- Issue statements are context; this report makes no implementation-correctness or developer-understanding verdict.", ""]
    write_text(output / "01-mr-analysis.md", "\n".join(lines))
    lines = ["# Change context", "", "## Issue associations", ""]
    for mapping in context["issue_context"]:
        lines += [f"- **{mapping['kind']}**: {mapping['statement']} (`{mapping['evidence']}`).",
                  f"  Candidate association: {', '.join(mapping['related_files']) or 'unresolved'}. {mapping['finding']}"]
    if not context["issue_context"]:
        lines.append("No explicit Issue criteria were supplied or extracted; observed changes remain the primary evidence.")
    lines += ["", "## Completion context", ""] + [f"- {k}: {v}" for k, v in context["completion_context"].items()]
    lines += ["", "Scope differences and changes to non-goals require contextual review; lexical associations do not establish agreement or test coverage.", ""]
    write_text(output / "02-change-context.md", "\n".join(lines))
    lines = ["# Impact analysis", "", "## Code evidence", ""]
    for m in mappings:
        s = m["symbol"]
        lines.append(f"- {m['change']} ({m['side']}): `{s['qualified_name']}` at `{s['file']}:{s['start_line']}-{s['end_line']}`; confidence {s['confidence']}/100.")
    lines += ["", "## Runtime and process scope", ""]
    for target in targets:
        lines += [f"### {target['target']}", "", f"Repository: `{target['repository']}`; type: {target['type']}.",
                  f"Impact: **{target['impact']}**; confidence: {target['confidence']}/100.", target["reason"], "",
                  "Path: " + _path_text(target["path"]), ""]
        for step in target["path"]:
            e = step["evidence"]
            lines.append(f"- {step['type']} ({step['direction']}): `{e['file']}:{e['start_line']}-{e['end_line']}`; detector `{e['detector']}`; revision `{e.get('revision', '')}`.")
        lines.append("")
    if not targets:
        lines += ["No operational target was established in the bounded graph. Runtime wiring remains unresolved; provide scheduler/deployment definitions.", ""]
    lines += ["## Unresolved relationships", ""]
    unresolved = [(g["repository"], n) for g in graphs for n in g["nodes"] if not n.get("defined")]
    lines.extend(f"- `{n['key']}` in `{rid}` has no local definition." for rid, n in unresolved)
    if not unresolved:
        lines.append("No undefined nodes were reached within the configured limits.")
    write_text(output / "03-impact-analysis.md", "\n".join(lines) + "\n")
    lines = ["# QA validation plan", "", "This is a proposed scope; no tests or operational jobs were executed.", "",
             "## Code-level tests", ""]
    lines += [f"- Inspect and run the existing test definition `{t['file']}` in `{t['repository']}` using its documented runner. Association: {t['classification']}; confidence {t['confidence']}/100." for t in tests]
    if not tests:
        lines.append("- Locate test coverage for the changed symbols listed in 03-impact-analysis.md; no connected test was found.")
    lines += ["", "## Process and job execution", ""]
    for target in targets:
        lines += [f"### {target['target']} ({target['repository']})", "", target["execute"],
                  f"Reason: {target['reason']} Confidence: {target['confidence']}/100.",
                  "Evidence path: " + _path_text(target["path"]), ""]
        lines += [f"- {item}" for item in target["verify"]]
        lines.append("")
    lines += ["## Integration, regression, and negative paths", ""]
    for behavior in context["behavior"]:
        scenario = behavior.get("validation", f"Exercise the changed {behavior['area']} path and its failure/boundary case; compare results with the agreed contract.")
        lines.append(f"- At `{behavior['file']}` hunk {behavior['hunk'] + 1}: {scenario} Reason: {behavior['reason']}")
    for mapping in context["issue_context"]:
        if mapping["kind"] == "requirement":
            lines.append(f"- Validate the explicit criterion: {mapping['statement']} Source: `{mapping['evidence']}`. Candidate files: {', '.join(mapping['related_files']) or 'unresolved'}.")
    write_text(output / "04-test-plan.md", "\n".join(lines) + "\n")
