"""Evidence extraction and runtime-template rendering shared by the Issue skill."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .indexing import EXCLUDED
from .safety import EngineError, read_json, read_text, write_text

KINDS = {"requirement", "constraint", "context", "assumption", "open_question", "inference", "validation", "non_goal"}
TEXT_EXTENSIONS = {".md", ".txt", ".rst", ".csv", ".log", ".json"}
CATEGORIES = {
    "problem": {"problem", "current state", "defect", "bug"},
    "outcome": {"outcome", "goal", "objective", "desired", "purpose"},
    "non_goal": {"non-goal", "out of scope", "excluded", "non goal"},
    "requirement": {"acceptance", "requirement", "criterion", "criteria", "must", "shall"},
    "scope": {"scope", "in scope"},
    "constraint": {"constraint", "dependency", "dependencies", "compatibility", "performance", "security"},
    "assumption": {"assumption", "assume"},
    "open_question": {"question", "unknown", "unclear", "unresolved"},
    "validation": {"validation", "test", "scenario", "evidence", "qa"},
}


def category(text):
    lower = text.lower()
    order = ["non_goal", "assumption", "open_question"] + [name for name in CATEGORIES if name not in {"non_goal", "assumption", "open_question"}]
    for name in order:
        words = CATEGORIES[name]
        if any(re.search(r"\b" + re.escape(word), lower) for word in words):
            return name
    return "context"


@dataclass
class Fact:
    text: str
    kind: str
    topic: str
    file: str
    line: int


@dataclass
class Slot:
    id: str
    line: int
    label: str
    section: str
    prefix: str


def discover(root: Path, scope: Path | None, template: Path, output: Path, max_bytes=2_000_000, max_sources=200):
    root = root.resolve()
    selected = (scope or root).resolve()
    if not selected.is_dir():
        raise EngineError("Issue source folder does not exist")
    sources, warnings = {}, []
    # Root input is deliberately shallow; an explicit folder includes its descendants.
    import os
    candidates = []
    if scope is None:
        candidates = sorted(selected.iterdir())
    else:
        for directory, folders, files in os.walk(selected, followlinks=False):
            folders[:] = sorted(f for f in folders if f not in EXCLUDED and not (Path(directory) / f).is_symlink()
                                and (Path(directory) / f).resolve() != output.resolve())
            candidates.extend(Path(directory) / f for f in sorted(files))
            if len(candidates) > max_sources * 20:
                raise EngineError("Issue discovery exceeds source entry limit")
    total = 0
    for path in candidates:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(selected):
            continue
        if path.resolve() == template.resolve() or path.resolve().is_relative_to(output.resolve()):
            continue
        if path.name in {"AGENTS.md", "SKILL.md", "GITLAB_ISSUE_TEMPLATE.md", "ASTRA6_IMPLEMENTATION_INSTRUCTIONS.md"}:
            continue
        if re.match(r"\d\d-.*\.md$", path.name) or path.name.startswith("."):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            if path.suffix.lower() in {".png", ".jpg", ".pdf", ".docx"}:
                warnings.append(f"Text extraction required: {path.relative_to(selected).as_posix()}")
            continue
        name = path.relative_to(selected).as_posix()
        try:
            text = read_text(path, max_bytes)
        except EngineError:
            warnings.append(f"Unreadable or oversized source: {name}")
            continue
        if path.name.lower() in {"readme.md", "license.md", "changelog.md"} and not re.search(r"acceptance|requirement|issue|desired outcome", text, re.I):
            continue
        total += len(text.encode())
        if len(sources) >= max_sources or total > max_bytes * 10:
            raise EngineError("Issue sources exceed aggregate input limit")
        sources[name] = text
    return selected, sources, warnings


def extract_facts(sources):
    facts = []
    for file, text in sources.items():
        heading, in_comment, governance = "", False, False
        for line_no, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if "<!--" in line:
                in_comment = True
            if in_comment:
                if "-->" in line:
                    in_comment = False
                continue
            if line.startswith("#") or re.fullmatch(r"\*\*.+\*\*", line):
                heading = line.strip("#* ")
                if re.match(r"^#{1,2}\s", line):
                    governance = bool(re.search(r"checklist|governance|definition of|\bDoR\b|\bDoD\b", heading, re.I))
                governance |= bool(re.search(r"\bDoR\b|\bDoD\b", heading, re.I))
                continue
            if re.fullmatch(r"[-*_]{3,}", line):
                continue
            line = re.sub(r"^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)]\s*)", "", line).strip()
            if not line or line in {"---", "```"} or line.startswith("```"):
                continue
            topic = category(heading)
            own = category(line)
            if own in {"assumption", "open_question", "non_goal"} or line.endswith("?"):
                topic = "open_question" if line.endswith("?") else own
            elif topic == "context":
                topic = own
            kind = topic if topic in KINDS else "context"
            if governance:
                kind, topic = "context", "governance"
            facts.append(Fact(line, kind, topic, file, line_no))
    return facts


def template_slots(template):
    slots, heading, label, comment = [], "", "", False
    lines = template.splitlines()
    for i, line in enumerate(lines, 1):
        if "<!--" in line:
            comment = True
        if comment:
            if "-->" in line:
                comment = False
            continue
        if re.match(r"^#{1,6}\s", line):
            heading, label = line.lstrip("# "), ""
        if re.fullmatch(r"\s*\*\*.+\*\*\s*", line):
            label = line.strip("* ")
            # A bold field followed by a list has its slot at the list item.
            tail = re.sub(r"<!--[\s\S]*?-->", "", "\n".join(lines[i:]))
            following = next((x.strip() for x in tail.splitlines() if x.strip()), "")
            if not re.match(r"^-(?:\s|$)", following):
                slots.append(Slot(f"L{i}", i, label, heading, "append"))
        elif re.fullmatch(r"\s*-\s*", line):
            slots.append(Slot(f"L{i}", i, label or heading, heading, "- "))
        elif re.fullmatch(r"\s*-\s*\[ \]\s*[^:]+:\s*", line):
            slots.append(Slot(f"L{i}", i, label or heading, heading, line.rstrip() + " "))
        elif re.search(r"\{\{[^}]+\}\}", line):
            slots.append(Slot(f"L{i}", i, re.search(r"\{\{([^}]+)\}\}", line)[1], heading, "placeholder"))
    # New heading-only sections are automatically recognized as content fields.
    for i, line in enumerate(lines, 1):
        if not re.match(r"^#{2,6}\s", line):
            continue
        end = next((j for j in range(i, len(lines)) if re.match(r"^#{1,6}\s", lines[j])), len(lines))
        body = re.sub(r"<!--[\s\S]*?-->", "", "\n".join(lines[i:end])).replace("---", "").strip()
        next_heading = lines[end] if end < len(lines) else ""
        is_container = next_heading.startswith("#" * (len(line) - len(line.lstrip("#")) + 1))
        if not body and not is_container:
            name = line.lstrip("# ")
            slots.append(Slot(f"L{i}", i, name, name, "append"))
    return slots


def _matching(slot, facts):
    topic = category(slot.label)
    if topic == "context":
        topic = category(slot.section)
    if topic == "context":
        words = set(re.findall(r"\w+", slot.label.lower())) - {"notes", "details", "and", "the"}
        return [f for f in facts if words and words & set(re.findall(r"\w+", f.text.lower()))]
    return [f for f in facts if f.topic == topic]


def validate_interpretation(plan, template, slots, sources):
    if plan.get("template_sha256") != hashlib.sha256(template.encode()).hexdigest():
        raise EngineError("Interpretation targets a different template; read the current template again")
    fills = plan.get("fills", {})
    empty_slots = plan.get("empty_slots", [])
    if not isinstance(empty_slots, list) or set(empty_slots) - {s.id for s in slots} or set(empty_slots) & set(fills):
        raise EngineError("Invalid explicitly empty template slots")
    if not isinstance(fills, dict) or set(fills) - {s.id for s in slots}:
        raise EngineError("Interpretation references unknown template slots")
    for slot, items in fills.items():
        if not isinstance(items, list):
            raise EngineError("Template fills must be lists of cited statements")
        for item in items:
            if not isinstance(item, dict) or item.get("kind") not in KINDS or not isinstance(item.get("text"), str):
                raise EngineError("Invalid interpreted statement")
            if "\n" in item["text"] or re.search(r"<!--|^#", item["text"]):
                raise EngineError("Interpreted statements may not change template structure")
            citations = item.get("evidence", [])
            if not citations and item["kind"] not in {"open_question", "inference"}:
                raise EngineError("Factual interpretation requires source evidence")
            for citation in citations:
                if citation.get("file") not in sources:
                    raise EngineError("Interpretation evidence is outside the selected source scope")
                lines = sources[citation["file"]].splitlines()
                start, end = citation.get("start_line"), citation.get("end_line")
                if not isinstance(start, int) or not isinstance(end, int) or not 1 <= start <= end <= len(lines):
                    raise EngineError("Interpretation evidence range does not exist")
            slot_info = next(s for s in slots if s.id == slot)
            if category(slot_info.label) in {"requirement", "scope"} and item["kind"] in {"assumption", "inference", "open_question"}:
                raise EngineError("Assumptions and inference cannot become hard requirements")
    return fills, set(empty_slots)


def analyze_issue(root: Path, output: Path, scope: Path | None = None, template: Path | None = None,
                  interpretation: Path | None = None):
    template = template or root / "GITLAB_ISSUE_TEMPLATE.md"
    template_text = read_text(template)
    selected, sources, warnings = discover(root, scope, template, output)
    facts, slots = extract_facts(sources), template_slots(template_text)
    fills, empty_slots = validate_interpretation(read_json(interpretation), template_text, slots, sources) if interpretation else (None, set())
    generated = template_text.splitlines()
    used, unresolved, records = set(), [], []
    for slot in slots:
        if slot.id in empty_slots:
            if slot.prefix not in {"append", "placeholder"}:
                generated[slot.line - 1] = slot.prefix.rstrip()
            elif slot.prefix == "placeholder":
                generated[slot.line - 1] = re.sub(r"\{\{[^}]+\}\}", "", generated[slot.line - 1])
            continue
        if fills is not None:
            items = fills.get(slot.id, [])
            texts = [("AI inference: " if x["kind"] == "inference" else "Assumption: " if x["kind"] == "assumption" else "") + x["text"] for x in items]
            records.extend((slot.label, x["kind"], x["text"], ", ".join(f"{e['file']}:{e['start_line']}-{e['end_line']}" for e in x.get("evidence", []))) for x in items)
        else:
            candidates = [f for f in _matching(slot, facts) if (f.file, f.line) not in used]
            # Enumerated placeholders consume one statement; the final one retains overflow.
            later_same = any(s.line > slot.line and s.label == slot.label for s in slots)
            if slot.prefix.startswith("- [ ]") and later_same:
                candidates = candidates[:1]
            texts = [f.text for f in candidates]
            for fact in candidates:
                used.add((fact.file, fact.line))
                records.append((slot.label, fact.kind, fact.text, f"{fact.file}:{fact.line}"))
        if not texts:
            unresolved.append(slot.label)
            texts = ["Unresolved: no supporting evidence in the selected sources."]
        if slot.prefix == "append":
            generated[slot.line - 1] += "\n\n" + "\n".join("- " + t for t in texts)
        elif slot.prefix == "placeholder":
            generated[slot.line - 1] = re.sub(r"\{\{[^}]+\}\}", lambda _: "; ".join(texts), generated[slot.line - 1])
        else:
            generated[slot.line - 1] = "\n".join(slot.prefix + t for t in texts)
    clean = re.sub(r"<!--[\s\S]*?-->", "", "\n".join(generated))
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip() + "\n"
    report = ["# Issue analysis", "", f"Source scope: `{selected.name}`. Sources inspected: {len(sources)}.",
              "", f"Current template SHA-256: `{hashlib.sha256(template_text.encode()).hexdigest()}`.", "",
              "## Evidence and classification", ""]
    for fact in facts:
        report.append(f"- **{fact.kind} / {fact.topic}**: {fact.text} (`{fact.file}:{fact.line}`).")
    if not facts:
        report.append("No usable source statements were found. Requirements remain unresolved.")
    report += ["", "## Template population", ""]
    for label, kind, text, evidence in records:
        report.append(f"- **{label}** ({kind}): {text} Evidence: {evidence or 'No source evidence; explicitly unresolved/inferred'}.")
    report += ["", "## Gaps, ambiguity, and readiness", ""]
    report.extend(f"- Missing evidence for template field: {label}." for label in dict.fromkeys(unresolved))
    questions = [f for f in facts if f.kind in {"assumption", "open_question"}]
    report.extend(f"- Clarify {f.kind}: {f.text} (`{f.file}:{f.line}`)." for f in questions)
    # Contradiction candidates are deliberately not resolved automatically.
    for fact in facts:
        if re.search(r"\bnot\b|\bnever\b", fact.text, re.I):
            positive = re.sub(r"\b(?:not|never)\s+", "", fact.text, flags=re.I)
            if any(f.text.lower() == positive.lower() for f in facts):
                report.append(f"- Conflicting source statements require clarification: {fact.file}:{fact.line}.")
    report += ["- Delivery checklists remain unchecked; no implementation or approval evidence was inferred.",
               "- Readiness is derived only from the current template fields and its checklist."]
    report.extend(f"- {warning}" for warning in warnings)
    if fills is None:
        report.append("- Deterministic extraction preserves source wording. A Copilot interpretation pass is required for semantic ambiguity, arbitrary template instructions, and domain-specific readiness judgments.")
    report += ["", "## Sources", ""] + [f"- `{name}`" for name in sources]
    output.mkdir(parents=True, exist_ok=True)
    write_text(output / "00-issue-analysis.md", "\n".join(report) + "\n")
    write_text(output / "01-generated-issue.md", clean)
    return {"outputs": [str(output / "00-issue-analysis.md"), str(output / "01-generated-issue.md")],
            "sources": len(sources), "unresolved_fields": list(dict.fromkeys(unresolved))}


def update_issue(issue: Path, analysis: Path, output: Path, target="Unspecified local Issue", validation: Path | None = None):
    issue_text = read_text(issue)
    context = read_json(analysis / "mr-context.json")
    runtime = read_json(analysis / "runtime-impact.json")
    report = read_text(analysis / "01-mr-analysis.md")
    if not isinstance(context, dict) or context.get("schema_version") != 1 or not isinstance(runtime, dict) or not isinstance(runtime.get("targets"), list):
        raise EngineError("Unsupported or malformed MR report data")
    for filename in ("runtime-impact.json", "01-mr-analysis.md"):
        expected = context.get("artifact_sha256", {}).get(filename)
        actual = hashlib.sha256((analysis / filename).read_bytes()).hexdigest()
        if expected != actual:
            raise EngineError("MR report artifacts are incomplete or changed; regenerate the MR analysis")
    for runtime_target in runtime["targets"]:
        if not isinstance(runtime_target, dict) or any(k not in runtime_target for k in ("target", "repository", "impact", "confidence")):
            raise EngineError("Malformed runtime target")
    evidence = read_text(validation) if validation else "No execution results were supplied. Proposed QA scenarios are not completed validation."
    summary = [f"Changed files: {len(context.get('changes', []))}. Revisions: `{context.get('base') or 'external patch'}..{context.get('head')}`.", ""]
    summary += [f"- {change['status']}: `{change['new_path'] or change['old_path']}`." for change in context.get("changes", [])]
    summary += [f"- {finding['classification']}: {finding['reason']} (`{finding['file']}`, hunk {finding['hunk'] + 1})." for finding in context.get("behavior", [])]
    lines = ["# Issue update preview", "", f"Target Issue: {target}", "Intended operation: append an implementation note locally.",
             "Remote write: disabled; this engine has no remote write adapter.", "Contract changes: none proposed or applied.",
             "", "## Proposed Markdown", "", "### Observed implementation", "", "\n".join(summary),
             "", "### Validation evidence", "", evidence, "", "### Runtime scope", ""]
    lines += [f"- {t['target']} ({t['repository']}): {t['impact']}; confidence {t['confidence']}/100." for t in runtime["targets"]]
    lines += ["", "### Limitations and follow-up", ""]
    lines += [f"- {w}" for w in context.get("warnings", [])]
    lines += ["- Review observed differences with the Issue owner; code changes alone do not establish agreed requirements.",
              "- Record actual QA outcomes and remaining blockers after execution.", "", "## Original Issue preservation", "",
              f"Original Issue SHA-256: `{hashlib.sha256(issue.read_bytes()).hexdigest()}`.",
              "The input Issue and its requirements were not rewritten.", ""]
    write_text(output / "05-issue-update.md", "\n".join(lines))
    return {"output": str(output / "05-issue-update.md"), "remote_write": False}
