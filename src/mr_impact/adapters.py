"""Composable bounded extractors. Heuristic structure is never semantic resolution."""

import ast
import json
import posixpath
import re
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from typing import Protocol

from .models import Confidence as C, Edge, Evidence, Node, ParsedFile, Symbol
from .safety import EngineError, safe_relative

LANGUAGES = {".py": "python", ".cs": "csharp", ".scala": "scala", ".sql": "sql",
             ".pks": "plsql", ".pkb": "plsql", ".jil": "autosys", ".xml": "xml",
             ".csproj": "xml", ".yaml": "yaml", ".yml": "yaml", ".json": "json",
             ".ps1": "powershell", ".sh": "shell", ".bat": "batch", ".cmd": "batch"}
SCRIPT_EXT = {".py", ".ps1", ".sh", ".bat", ".cmd"}
RUNTIME_TYPES = {"SCRIPT", "AUTOSYS_JOB", "AUTOSYS_BOX", "DATABRICKS_JOB",
                 "DATABRICKS_PIPELINE", "DATABRICKS_TASK", "DB_PROCEDURE", "DB_FUNCTION",
                 "DB_TRIGGER", "SERVICE", "API_ENDPOINT", "WORKFLOW", "PROCESS"}


def language(path):
    return LANGUAGES.get(PurePosixPath(path).suffix.lower(), "generic")


def canonical(kind: str, name: str) -> str:
    name = name.strip(" \t\r\n\"'`[];")
    if kind in {"table", "oracle"}:
        name = re.sub(r'["`\[\]]', "", name).replace(".", "/").upper()
    elif kind in {"nuget", "maven"}:
        name = name.lower()
    return kind + "://" + name


class Context:
    def __init__(self, path: str, text: str, mode: str, revision: str):
        self.path, self.text, self.mode, self.revision = path, text, mode, revision
        self.lines = text.splitlines()
        self.result = ParsedFile()
        self.file_key = "file://" + path
        suffix = PurePosixPath(path).suffix.lower()
        kind = "SCRIPT" if suffix in SCRIPT_EXT else "FILE"
        if "test" in PurePosixPath(path).stem.lower() or any(p in {"tests", "test"} for p in PurePosixPath(path).parts):
            kind = "TEST"
        elif suffix in {".yml", ".yaml", ".xml", ".json", ".config", ".csproj"}:
            kind = "CONFIG"
        if path.startswith(".github/workflows/") or PurePosixPath(path).name == ".gitlab-ci.yml":
            kind = "WORKFLOW"
        self.node(self.file_key, kind, path, 1, C.EXACT, boundary=kind in RUNTIME_TYPES)

    def evidence(self, line, detector, confidence=C.STRONG, end=None):
        return Evidence(self.path, max(1, line), max(1, end or line), detector, confidence, self.revision)

    def node(self, key, kind, name, line, confidence=C.STRONG, boundary=False, metadata=None):
        self.result.nodes.append(Node(key, kind, name, self.evidence(line, "declaration", confidence), boundary, metadata or {}))
        return key

    def edge(self, source, target, kind, line, detector, confidence=C.STRONG):
        self.result.edges.append(Edge(source, target, kind, self.evidence(line, detector, confidence)))

    def owner(self, line):
        symbols = [s for s in self.result.symbols if s.start_line <= line <= s.end_line]
        return min(symbols, key=lambda s: s.end_line - s.start_line).id if symbols else self.file_key

    def symbol(self, name, kind, start, end, signature, confidence=C.PROBABLE):
        key = f"symbol://{self.path}::{name}:{start}"
        self.result.symbols.append(Symbol(key, self.path, name, kind, start, max(start, end), language(self.path), signature, confidence))
        self.node(key, "CODE_SYMBOL", name, start, confidence)
        self.edge(self.file_key, key, "DEFINES", start, "symbol-range", confidence)
        return key

    def reference(self, token: str, line: int, source=None, kind="EXECUTES", confidence=C.PROBABLE):
        token = token.strip(" \"'")
        if token.startswith(("/", "$", "%")) or ":" in token:
            self.result.warnings.append(f"Unresolved runtime path at {self.path}:{line}")
            return
        # Root-relative paths are explicit; ./ and ../ are relative to the referring file.
        normalized = posixpath.normpath(posixpath.join(posixpath.dirname(self.path), token)) if token.startswith(".") else token
        try:
            normalized = safe_relative(normalized)
        except EngineError:
            self.result.warnings.append(f"Out-of-scope runtime path at {self.path}:{line}")
            return
        key = "file://" + normalized
        self.node(key, "FILE", normalized, line, confidence, metadata={"reference_only": True})
        self.edge(source or self.owner(line), key, kind, line, "path-reference", confidence)


class Adapter(Protocol):
    name: str
    def accepts(self, path: str) -> bool: ...
    def extract(self, context: Context) -> None: ...


class PythonAdapter:
    name = "python-ast"

    def accepts(self, path):
        return path.endswith(".py")

    def extract(self, c):
        if c.mode == "boundary":
            return
        try:
            tree = ast.parse(c.text)
        except (SyntaxError, RecursionError):
            c.result.warnings.append(f"Python syntax unavailable: {c.path}")
            return
        names = {}

        def visit(node, prefix=""):
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = prefix + item.name
                    key = c.symbol(name, "class" if isinstance(item, ast.ClassDef) else "function",
                                   item.lineno, item.end_lineno, c.lines[item.lineno - 1].strip(), C.EXACT)
                    names.setdefault(item.name, []).append(key)
                    if isinstance(item, ast.ClassDef):
                        for base in item.bases:
                            if isinstance(base, ast.Name):
                                c.edge(key, "external-symbol://" + base.id, "INHERITS", item.lineno, self.name, C.CANDIDATE)
                    visit(item, name + ".")
                else:
                    visit(item, prefix)
        visit(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                candidates = names.get(node.func.id, [])
                if len(candidates) == 1:
                    c.edge(c.owner(node.lineno), candidates[0], "CALLS", node.lineno, self.name, C.PROBABLE)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                for module in filter(None, modules):
                    target = "file://" + module.replace(".", "/") + ".py"
                    c.edge(c.owner(node.lineno), target, "IMPORTS", node.lineno, self.name, C.CANDIDATE)


class StructureAdapter:
    name = "structural-fallback"

    def accepts(self, path):
        return PurePosixPath(path).suffix.lower() in {".cs", ".scala", ".ps1", ".sh"}

    def extract(self, c):
        if c.mode == "boundary":
            return
        # These ranges are lexical approximations, not binding or overload resolution.
        patterns = [r"\b(class|interface|trait|object)\s+(\w+)",
                    r"\b(def|function)\s+(\w+)\s*(?:\(|\{)"]
        if c.path.endswith(".cs"):
            patterns.append(r"\b(?:public|private|protected|internal)\s+(?:static\s+|async\s+|virtual\s+|override\s+)*(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(")
        for i, line in enumerate(c.lines, 1):
            if line.lstrip().startswith(("//", "#", "*")):
                continue
            match = next((m for pattern in patterns if (m := re.search(pattern, line))), None)
            if not match:
                continue
            depth, opened, end = 0, False, i
            for j in range(i - 1, len(c.lines)):
                clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', c.lines[j].split("//", 1)[0])
                depth += clean.count("{") - clean.count("}")
                opened |= "{" in clean
                end = j + 1
                if opened and depth <= 0 or (not opened and (";" in clean or j > i + 2)):
                    break
            c.symbol(match.group(2), match.group(1) if match.group(1) in {"class", "interface", "trait", "object"} else "method",
                     i, end, line.strip(), C.PROBABLE)
        if c.path.endswith(".cs"):
            c.result.warnings.append(f"C# lexical structure only; no Roslyn binding: {c.path}")


class GenericAdapter:
    name = "generic"

    def accepts(self, path):
        return True

    def extract(self, c):
        for i, line in enumerate(c.lines, 1):
            if line.lstrip().startswith(("#", "//", "--", "<!--")):
                continue
            for match in re.finditer(r"(?:[\w./$%-]+\.(?:py|ps1|sh|bat|cmd|sql|scala|jar|dll|exe|json|yaml|yml|config))\b", line):
                token = match.group()
                if token != c.path:
                    c.reference(token, i, kind="CONFIGURES" if token.endswith(("json", "yaml", "yml", "config")) else "EXECUTES")
            for match in re.finditer(r"https?://[^\s\"'<>]+", line):
                from urllib.parse import urlsplit
                url = urlsplit(match.group())
                target = canonical("api", (url.hostname or "unknown") + url.path)
                c.node(target, "API_ENDPOINT", target, i, C.CANDIDATE, True)
                c.edge(c.owner(i), target, "USES", i, self.name, C.CANDIDATE)
            for match in re.finditer(r"\b(nuget|maven|oracle|table|event|autosys)://([\w./-]+)", line):
                key = canonical(match[1], match[2])
                c.node(key, {"table": "DB_TABLE", "oracle": "DB_PROCEDURE", "autosys": "AUTOSYS_JOB",
                             "event": "EVENT"}.get(match[1], "PACKAGE"), match[2], i, C.CANDIDATE, True)
                c.edge(c.owner(i), key, "USES", i, self.name, C.CANDIDATE)
            # Package and import declarations are structural evidence only.
            if match := re.search(r'^\s*(?:package|namespace)\s+([\w.]+)', line):
                key = c.node("module://" + match[1], "MODULE", match[1], i)
                c.edge(key, c.file_key, "CONTAINS", i, self.name)
            if match := re.search(r'^\s*(?:using|import)\s+([\w.]+)', line):
                c.edge(c.file_key, "module://" + match[1], "IMPORTS", i, self.name, C.CANDIDATE)
            if match := re.search(r'"([\w.-]+)"\s*%%?\s*"([\w.-]+)"\s*%\s*"([^"\n]+)"', line):
                key = canonical("maven", match[1] + "/" + match[2])
                c.node(key, "PACKAGE", match[2], i, C.STRONG, True, {"version": match[3]})
                c.edge(c.file_key, key, "USES", i, self.name)


class SqlAdapter:
    name = "sql-lexical"

    def accepts(self, path):
        return PurePosixPath(path).suffix.lower() in {".sql", ".pks", ".pkb", ".scala", ".py", ".cs"}

    def extract(self, c):
        sql_file = language(c.path) in {"sql", "plsql"}
        package = ""
        current = None
        dynamic = False
        for i, line in enumerate(c.lines, 1):
            clean = re.sub(r"--.*$", "", line)
            if clean.lstrip().startswith(("//", "#")):
                continue
            dynamic |= bool(re.search(r"\bEXECUTE\s+IMMEDIATE\b|\bDBMS_SQL\b", clean, re.I))
            if sql_file and (m := re.search(r"\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?)?(PACKAGE\s+BODY|PACKAGE|PROCEDURE|FUNCTION|TABLE|VIEW|TRIGGER)\s+([\w.]+)", clean, re.I)):
                kind, name = m[1].upper().replace(" ", "_"), m[2]
                if kind.startswith("PACKAGE"):
                    package = name
                elif package and "." not in name and kind in {"PROCEDURE", "FUNCTION"}:
                    name = package + "." + name
                target = canonical("table" if kind in {"TABLE", "VIEW"} else "oracle", name)
                c.node(target, "DB_" + ("PACKAGE" if kind == "PACKAGE_BODY" else kind), name, i, C.STRONG, True)
                c.edge(c.file_key, target, "DEFINES", i, self.name)
                current = target
                if c.mode == "deep":
                    c.symbol(name, kind.lower(), i, len(c.lines), clean.strip(), C.PROBABLE)
            for pattern, role in [(r"\b(?:FROM|JOIN)\s+([\w.]+)", "READS"),
                                  (r"\b(?:INSERT\s+INTO|MERGE\s+INTO|UPDATE|DELETE\s+FROM)\s+([\w.]+)", "WRITES"),
                                  (r'\.(?:table|load)\(\s*["\x27]([\w.]+)', "READS"),
                                  (r'\.(?:saveAsTable|insertInto)\(\s*["\x27]([\w.]+)', "WRITES")]:
                for m in re.finditer(pattern, clean, re.I):
                    if m[1].upper() in {"SELECT", "SET", "DUAL"}:
                        continue
                    confidence = C.CANDIDATE if dynamic else (C.STRONG if sql_file else C.PROBABLE)
                    key = canonical("table", m[1])
                    c.node(key, "DB_TABLE", m[1], i, confidence, True, {"reference_only": True})
                    c.edge(current or c.owner(i), key, role, i, self.name, confidence)
            for m in re.finditer(r"\b(?:CALL|EXEC(?:UTE)?)\s+([\w.]+)\s*\(|\b([A-Za-z_]\w*\.[A-Za-z_]\w*)\s*\(", clean, re.I):
                name = m[1] or m[2]
                if not sql_file and not m[1]:
                    continue
                key = canonical("oracle", name)
                c.node(key, "DB_PROCEDURE", name, i, C.CANDIDATE, True, {"reference_only": True})
                c.edge(current or c.owner(i), key, "CALLS", i, self.name, C.CANDIDATE)
        if dynamic:
            c.result.warnings.append(f"Dynamic SQL requires runtime verification: {c.path}")


class AutosysAdapter:
    name = "autosys-jil"

    def accepts(self, path):
        return path.lower().endswith(".jil")

    def extract(self, c):
        jobs = []
        for i, line in enumerate(c.lines, 1):
            clean = line.split("/*", 1)[0].strip()
            if m := re.match(r"insert_job\s*:\s*([^\s]+)(.*)", clean, re.I):
                jobs.append((m[1], i, {}))
                clean = m[2].strip()
            if jobs:
                for m in re.finditer(r"(job_type|command|condition|box_name|machine|profile)\s*:\s*(.*?)(?=\s+\w+\s*:|$)", clean, re.I):
                    jobs[-1][2][m[1].lower()] = (m[2].strip(), i)
        for name, start, fields in jobs:
            box = fields.get("job_type", ("", 0))[0].lower() == "b"
            key = canonical("autosys", name)
            c.node(key, "AUTOSYS_BOX" if box else "AUTOSYS_JOB", name, start, C.EXACT, True,
                   {k: v[0] for k, v in fields.items() if k in {"job_type", "machine", "profile"}})
            c.edge(c.file_key, key, "DEFINES", start, self.name, C.EXACT)
            if "box_name" in fields:
                value, line = fields["box_name"]
                parent = canonical("autosys", value)
                c.node(parent, "AUTOSYS_BOX", value, line, C.EXACT, True, {"reference_only": True})
                c.edge(parent, key, "CONTAINS", line, self.name, C.EXACT)
            if "condition" in fields:
                value, line = fields["condition"]
                for name in re.findall(r"\b(?:s|f|d|n|t|success|failure)\s*\(\s*([\w.-]+)\s*\)", value, re.I):
                    parent = canonical("autosys", name)
                    c.node(parent, "AUTOSYS_JOB", name, line, C.EXACT, True, {"reference_only": True})
                    c.edge(key, parent, "DEPENDS_ON", line, self.name, C.EXACT)
            if "command" in fields:
                command, line = fields["command"]
                tokens = re.findall(r'"([^"\n]+)"|\x27([^\x27\n]+)\x27|(\S+)', command)
                refs = [next(x for x in t if x) for t in tokens]
                matched = False
                for ref in refs:
                    if PurePosixPath(ref).suffix.lower() in SCRIPT_EXT | {".sql", ".exe", ".jar", ".dll"}:
                        c.reference(ref, line, key, confidence=C.EXACT)
                        matched = True
                if not matched:
                    c.result.warnings.append(f"Unresolved AutoSys executable at {c.path}:{line}")


def simple_yaml(text):
    """Parse only the indentation/mapping/list subset used by bundle resource manifests.

    Tags, aliases, anchors, flow collections and multiline scalars are rejected.
    This intentionally does not claim to implement the YAML language.
    """
    rows = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw or re.search(r"(^|\s)[&*!]|:\s*[>|\[{]", raw):
            raise ValueError("Unsupported YAML construct")
        rows.append((len(raw) - len(raw.lstrip()), raw.strip()))

    def scalar(value):
        return value.strip().strip('"\x27')

    def block(index, indent):
        is_list = rows[index][1].startswith("- ")
        value = [] if is_list else {}
        while index < len(rows) and rows[index][0] == indent:
            text = rows[index][1]
            index += 1
            if is_list:
                if not text.startswith("- "):
                    raise ValueError("Mixed YAML collection")
                text = text[2:]
                if ":" in text:
                    key, rest = text.split(":", 1)
                    item = {key: scalar(rest)}
                    if index < len(rows) and rows[index][0] > indent:
                        child, index = block(index, rows[index][0])
                        if rest.strip():
                            item.update(child)
                        else:
                            item[key] = child
                    value.append(item)
                else:
                    value.append(scalar(text))
            else:
                if ":" not in text:
                    raise ValueError("Expected YAML mapping")
                key, rest = text.split(":", 1)
                if rest.strip():
                    value[key] = scalar(rest)
                elif index < len(rows) and rows[index][0] > indent:
                    value[key], index = block(index, rows[index][0])
                else:
                    value[key] = {}
        return value, index
    if not rows:
        return {}
    result, end = block(0, rows[0][0])
    if end != len(rows):
        raise ValueError("Inconsistent YAML indentation")
    return result


class ConfigAdapter:
    name = "config-resources"

    def accepts(self, path):
        return PurePosixPath(path).suffix.lower() in {".xml", ".csproj", ".json", ".yaml", ".yml"}

    def extract(self, c):
        if c.path.endswith((".xml", ".csproj")):
            if "<!DOCTYPE" in c.text.upper() or "<!ENTITY" in c.text.upper():
                c.result.warnings.append(f"XML declarations rejected: {c.path}")
                return
            try:
                root = ET.fromstring(c.text)
            except ET.ParseError:
                c.result.warnings.append(f"Malformed XML: {c.path}")
                return
            for element in root.iter():
                tag = element.tag.split("}")[-1]
                name = element.attrib.get("Include", "")
                if tag == "PackageReference" and name:
                    key = canonical("nuget", name)
                    line = next((i for i, t in enumerate(c.lines, 1) if name in t), 1)
                    c.node(key, "PACKAGE", name, line, C.EXACT, True, {"version": element.attrib.get("Version", "unknown")})
                    c.edge(c.file_key, key, "USES", line, self.name, C.EXACT)
                if tag == "ProjectReference" and name:
                    c.reference(name.replace("\\", "/") if name.startswith(".") else "./" + name.replace("\\", "/"), 1, kind="DEPENDS_ON", confidence=C.EXACT)
            return
        try:
            data = json.loads(c.text) if c.path.endswith(".json") else simple_yaml(c.text)
        except (ValueError, RecursionError):
            c.result.warnings.append(f"Config subset unsupported; generic candidates only: {c.path}")
            return
        if not isinstance(data, dict):
            return
        resources = data.get("resources", {})
        if not isinstance(resources, dict):
            return
        def line_of(value):
            return next((i for i, line in enumerate(c.lines, 1) if str(value) in line), 1)
        for collection, kind, scheme in [("jobs", "DATABRICKS_JOB", "databricks-job"),
                                          ("pipelines", "DATABRICKS_PIPELINE", "databricks-pipeline")]:
            values = resources.get(collection, {})
            if not isinstance(values, dict):
                continue
            for name, spec in values.items():
                if not isinstance(spec, dict):
                    continue
                line = line_of(name)
                key = canonical(scheme, name)
                c.node(key, kind, name, line, C.STRONG, True)
                c.edge(c.file_key, key, "DEFINES", line, self.name)
                tasks = spec.get("tasks", [])
                if not isinstance(tasks, list):
                    continue
                for task in tasks:
                    if not isinstance(task, dict):
                        continue
                    task_name = str(task.get("task_key", "unnamed"))
                    task_key = key + "/task/" + task_name
                    line = line_of(task_name)
                    c.node(task_key, "DATABRICKS_TASK", name + "/" + task_name, line, C.STRONG, True)
                    c.edge(key, task_key, "CONTAINS", line, self.name)
                    notebook = task.get("notebook_task", {})
                    if isinstance(notebook, dict) and notebook.get("notebook_path"):
                        c.reference(str(notebook["notebook_path"]), line_of(notebook["notebook_path"]), task_key, confidence=C.STRONG)
                    for dependency in task.get("depends_on", []) if isinstance(task.get("depends_on", []), list) else []:
                        if isinstance(dependency, dict) and "task_key" in dependency:
                            c.edge(task_key, key + "/task/" + str(dependency["task_key"]), "DEPENDS_ON", line, self.name)
                for library in spec.get("libraries", []) if isinstance(spec.get("libraries", []), list) else []:
                    if isinstance(library, dict) and isinstance(library.get("notebook"), dict):
                        value = library["notebook"].get("path")
                        if value:
                            c.reference(str(value), line_of(value), key, confidence=C.STRONG)


ADAPTERS: tuple[Adapter, ...] = (PythonAdapter(), StructureAdapter(), SqlAdapter(), AutosysAdapter(), ConfigAdapter(), GenericAdapter())


def parse(path: str, text: str, mode="deep", revision="", adapters=None) -> ParsedFile:
    c = Context(path, text, mode, revision)
    for adapter in ADAPTERS:
        if (adapters is None or adapter.name in adapters or adapter.name == "generic") and adapter.accepts(path):
            adapter.extract(c)
    return c.result
