"""MR orchestration: deterministic changes, bounded runtime discovery, and QA reports."""

import hashlib
import json
import re
from contextlib import ExitStack
from pathlib import Path

from .adapters import RUNTIME_TYPES
from .expansion import expand
from .locking import catalog_lock, locked_repository
from .diff import map_symbols, parse_diff, validate_patch
from .git import git, repository_id, resolve, snapshot
from .indexing import IndexConfig, build_index
from .issues import extract_facts
from .models import ADAPTER_VERSION, SCHEMA_VERSION, Limits, RuntimeTarget, record
from .review import REVIEW_CONTRACT_VERSION, validate_mr_review
from .safety import EngineError, file_digest, read_json, read_text, write_json, write_text
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


@locked_repository
def analyze_mr(root: Path, output: Path, base: str | None = None, head="HEAD", patch: Path | None = None,
               commit: str | None = None, cache: Path | None = None, catalog: Path | None = None,
               issue: Path | None = None, limits: Limits | None = None, config: IndexConfig | None = None,
               expand_candidates=True, interpretation: Path | None = None, require_review=False):
    root = root.resolve()
    limits = limits or Limits()
    config = config or IndexConfig()
    root_commit = False
    if commit:
        if base or patch:
            raise EngineError("--commit cannot be combined with --base or --patch")
        head = resolve(root, commit)
        commit_text = git(root, "cat-file", "commit", head).decode("utf-8", errors="replace")
        parents = re.findall(r"^parent ([0-9a-f]+)$", commit_text.split("\n\n", 1)[0], re.M)
        base = parents[0] if parents else None
        root_commit = not parents
    if not base and not patch and not root_commit:
        raise EngineError("Provide a base revision, a commit, or a patch")
    head_id = resolve(root, head)
    base_id = resolve(root, base) if base else None
    if patch:
        diff = read_text(patch, 20_000_000)
    else:
        operation = ("diff-tree", "--root", "--no-commit-id", "-p") if root_commit else ("diff",)
        refs = (head_id,) if root_commit else (base_id, head_id)
        diff = git(root, *operation, "--no-ext-diff", "--no-textconv", "--find-renames", "--unified=0",
                   "--src-prefix=a/", "--dst-prefix=b/", *refs, "--", max_bytes=20_000_000).decode("utf-8", errors="replace")
    changes = parse_diff(diff)
    warnings = []
    if patch:
        if not base_id:
            warnings.append("External patch: head content verified; old-side claims are unverified without --base.")
        _, new_files = snapshot(root, head_id)
        old_files = snapshot(root, base_id)[1] if base_id else None
        def read_revision(revision, path):
            return git(root, "cat-file", "blob", f"{revision}:{path}", max_bytes=config.max_file_bytes).decode("utf-8", errors="replace")
        validate_patch(changes, old_files, new_files,
                       lambda path: read_revision(base_id, path), lambda path: read_revision(head_id, path))
    indexed = build_index(root, cache, "deep", head_id, config=config)
    previous = build_index(root, cache, "deep", base_id, config=config, slot="base") if base_id else None
    warnings.extend(indexed["statistics"]["warnings"])
    with ExitStack() as stack:
        store = stack.enter_context(Store(Path(indexed["directory"]) / "repository-index.sqlite"))
        before = stack.enter_context(Store(Path(previous["directory"]) / "repository-index.sqlite")) if previous else None
        mappings = map_symbols(changes, store, before)
        if root_commit:
            for mapping in mappings:
                mapping["change"] = "added"
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
        catalog_digest = None
        if catalog:
            stack.enter_context(catalog_lock(catalog))
            catalog_digest = file_digest(catalog)
            candidates, expanded = expand(graphs, root, cache, catalog, limits, config,
                                           expand_candidates, stack, warnings)
            graphs.extend(expanded)
            for group in expanded:
                targets.extend(targets_from_graph(group, group["repository"]))
        unique = {}
        defined_entities = {(t["repository"], t["entity"]) for t in targets if t["impact"] != "UNRESOLVED"}
        for target in targets:
            if target["impact"] == "UNRESOLVED" and (target["repository"], target["entity"]) in defined_entities:
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
        scenarios = []
        review_context = {"contract_version": REVIEW_CONTRACT_VERSION, "schema_version": SCHEMA_VERSION,
                          "adapter_version": ADAPTER_VERSION, "base": base_id, "head": head_id,
                          "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
                          "issue_sha256": file_digest(issue) if issue else None,
                          "catalog_sha256": catalog_digest, "limits": record(limits), "config": record(config),
                          "expand_candidates": expand_candidates, "generation": indexed["state"]["generation"],
                          "base_generation": previous["state"]["generation"] if previous else None,
                          "candidate_generations": {c["repository"]: c.get("generation") for c in candidates},
                          "coverage_sha256": hashlib.sha256(json.dumps({"graphs": graphs, "warnings": warnings},
                                                                      sort_keys=True).encode()).hexdigest()}
        # Use JSON-native lists in both the supplied and generated review contexts.
        review_context = json.loads(json.dumps(review_context))
        plan = read_json(interpretation) if interpretation else {}
        review_status, review_decisions = validate_mr_review(plan, review_context, changes, require_review)
        if interpretation:
            if plan.get("head") != head_id or plan.get("diff_sha256") != hashlib.sha256(diff.encode()).hexdigest():
                raise EngineError("MR interpretation does not match the current diff and head")
            findings = plan.get("findings", [])
            if not isinstance(findings, list) or len(findings) > 500:
                raise EngineError("Invalid MR interpretation findings")
            for finding in findings:
                if not isinstance(finding, dict):
                    raise EngineError("MR findings must be objects")
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
                scenario = finding.get("scenario")
                if scenario is not None:
                    if not isinstance(scenario, dict) or any(not isinstance(scenario.get(key), str) or not scenario[key].strip()
                            for key in ("target", "repository", "preconditions", "inputs", "expected")):
                        raise EngineError("QA scenario requires target, repository, preconditions, inputs, and expected result")
                    target = next((t for t in targets if t["entity"] == scenario["target"] and t["repository"] == scenario["repository"]), None)
                    if target is None:
                        raise EngineError("QA scenario references an undiscovered runtime target")
                    scenarios.append({key: scenario[key] for key in ("target", "repository", "preconditions", "inputs", "expected")} |
                                     {"classification": classification, "file": change.new_path or change.old_path,
                                      "hunk": hunk_index, "path": target["path"], "executed": False})
                behavior.append({"area": "agent interpretation", "classification": classification,
                                 "file": change.new_path or change.old_path, "hunk": hunk_index,
                                 "reason": finding["summary"], "validation": finding["validation"]})
        context = {"schema_version": 1, "repository": repository_id(root), "base": base_id, "base_kind": "empty_tree" if root_commit else "revision" if base_id else "unverified", "head": head_id,
                   "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(), "changes": [record(c) for c in changes],
                   "behavior": behavior, "issue_context": context_mappings, "candidates": candidates,
                   "warnings": list(dict.fromkeys(warnings)), "limits": record(limits),
                   "completion_context": {"test_execution": "not performed", "MR_review_approval": "not available locally",
                                          "documentation_changed": any(_classify_file(c.new_path or c.old_path) == "documentation" for c in changes)}}
        context.update({"analysis_status": "draft" if review_status == "pending" else "reviewed",
                        "semantic_review_status": review_status, "reviewed_changes": review_decisions,
                        "review_context": review_context,
                        "coverage_status": "partial" if warnings else "bounded" if catalog else "local_only"})
        for number, finding in enumerate(behavior, 1):
            finding["id"] = f"finding-{number:03}"
        context["qa_scenarios"] = scenarios
        context["completion_checks"] = [
            {"check": "test_execution", "status": "unknown", "evidence": [], "reason": "Tests were not executed by analysis"},
            {"check": "review_approval", "status": "unknown", "evidence": [], "reason": "No approval evidence supplied"},
            {"check": "documentation_change", "status": "evidence_available" if context["completion_context"]["documentation_changed"] else "unknown",
             "evidence": [c.new_path or c.old_path for c in changes if _classify_file(c.new_path or c.old_path) == "documentation"]}]
        context["follow_up"] = [{"id": f"follow-up-{number:03}", "status": "open", "reason": warning,
                                 "evidence": {"head": head_id}, "action": "Clarify this limitation before relying on complete QA coverage."}
                                for number, warning in enumerate(context["warnings"], 1)]
        output.mkdir(parents=True, exist_ok=True)
        for filename, value in (("mr-context.json", context), ("changed-symbols.json", {"mappings": mappings}),
                                ("impact-graph.json", {"graphs": graphs}), ("runtime-impact.json", {"targets": targets}),
                                ("test-impact.json", {"tests": tests, "missing_coverage_candidate": not bool(tests), "scenarios": scenarios})):
            write_json(output / filename, value)
        _reports(output, context, mappings, graphs, targets, tests)
        context["artifact_sha256"] = {filename: hashlib.sha256((output / filename).read_bytes()).hexdigest()
                                      for filename in ("runtime-impact.json", "changed-symbols.json", "impact-graph.json", "test-impact.json",
                                                       "01-mr-analysis.md", "02-change-context.md", "03-impact-analysis.md", "04-test-plan.md")}
        write_json(output / "mr-context.json", context)
        return {"output": str(output), "changed_files": len(changes), "runtime_targets": len(targets),
                "candidate_repositories": len(candidates), "warnings": context["warnings"],
                "analysis_status": context["analysis_status"], "coverage_status": context["coverage_status"]}


def _reports(output, context, mappings, graphs, targets, tests):
    lines = ["# Merge Request analysis", "", f"Revision: `{context['base'] or ('empty tree' if context.get('base_kind') == 'empty_tree' else 'external patch')}..{context['head']}`.", "",
             f"Observed scope: changed files: {len(context['changes'])}; symbol mappings: {len(mappings)}; runtime targets: {len(targets)}.", "",
             "## Changed areas", ""]
    lines[4:4] = [f"Analysis status: {context['analysis_status']}; semantic review: {context['semantic_review_status']}; coverage: {context['coverage_status']}.",
                  "Confidence values are detector strength levels, not calibrated probabilities of runtime impact.", ""]
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
    lines += ["", "## Semantic change review", ""]
    lines += [f"- Change {int(key) + 1}: {value['status']}. {value['reason']}" for key, value in context["reviewed_changes"].items()]
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
             f"Semantic review: {context['semantic_review_status']}; coverage: {context['coverage_status']}.", "",
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
    lines += ["", "## Evidence-linked scenarios", ""]
    for scenario in context["qa_scenarios"]:
        lines += [f"### {scenario['target']} ({scenario['repository']})", "",
                  f"Preconditions: {scenario['preconditions']}", f"Inputs: {scenario['inputs']}",
                  f"Expected: {scenario['expected']}", f"Evidence: `{scenario['file']}`, hunk {scenario['hunk'] + 1}; {scenario['classification']}.", ""]
    if not context["qa_scenarios"]:
        lines.append("Clarify QA environment, input data, and expected outputs for each runtime target; these parameters were not supplied as structured evidence.")
    write_text(output / "04-test-plan.md", "\n".join(lines) + "\n")
