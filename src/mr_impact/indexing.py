"""Incremental content-addressed repository indexes and streaming boundary export."""

import fnmatch
import hashlib
import json
import itertools
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .adapters import ADAPTERS, language, parse
from .git import batch_blobs, content, repository_id, snapshot
from .models import ADAPTER_VERSION, SCHEMA_VERSION, FileRecord, ParsedFile, RepositoryState, record
from .safety import EngineError, validate_output, write_json
from .storage import Store

EXCLUDED = {".git", ".obsidian", ".repository-analysis", ".mr-analysis", "node_modules", "vendor", ".venv",
            "venv", "packages", ".nuget", ".m2", ".gradle", "generated", "build", "target", "dist", "third_party", "__pycache__"}


@dataclass
class IndexConfig:
    max_file_bytes: int = 2_000_000
    max_files: int = 1_000_000
    workers: int = 1
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    adapters: list[str] = field(default_factory=lambda: [a.name for a in ADAPTERS])

    def __post_init__(self):
        if not (1 <= self.workers <= 16 and 1 <= self.max_file_bytes <= 50_000_000 and 1 <= self.max_files <= 5_000_000):
            raise EngineError("Invalid indexing limits")
        if set(self.adapters) - {a.name for a in ADAPTERS}:
            raise EngineError("Unknown adapter name")

    def accepts(self, path):
        parts = Path(path).parts
        return (not any(part in EXCLUDED for part in parts)
                and not any(fnmatch.fnmatch(path, pattern) for pattern in self.exclude)
                and (not self.include or any(fnmatch.fnmatch(path, pattern) for pattern in self.include))
                and not path.endswith((".min.js", ".g.cs", ".generated.cs"))
                and not any(part.lower() in {".env", "id_rsa", "id_ed25519"} for part in parts)
                and not path.lower().endswith((".pem", ".key", ".pfx", ".p12")))


def index_dir(root: Path, cache: Path | None = None, slot: str = "current"):
    if slot not in {"current", "base"}:
        raise EngineError("Invalid index slot")
    return (cache or root / ".repository-analysis") / "repositories" / repository_id(root) / slot


def fingerprint(entries, config):
    digest = hashlib.sha256()
    for path, value in sorted(entries.items()):
        if config.accepts(path):
            digest.update(path.encode() + b"\0" + value[0].encode() + b"\0")
    return digest.hexdigest()


def is_fresh(root, directory, ref="HEAD", worktree=False, config=None, mode=None):
    if not (directory / "repository-index.sqlite").exists():
        return False
    with Store(directory / "repository-index.sqlite") as store:
        old = store.state()
    if not old:
        return False
    config = config or IndexConfig(**old["config"])
    commit, entries = snapshot(root, ref, worktree)
    return (old["commit"] == commit and old["fingerprint"] == fingerprint(entries, config)
            and old["config"] == record(config) and old["schema_version"] == SCHEMA_VERSION
            and old["adapter_version"] == ADAPTER_VERSION and (mode is None or old["mode"] == mode))


def _export_array(path, rows):
    """Write large exports incrementally rather than materializing the graph."""
    import os
    import tempfile
    from .safety import redact
    validate_output(path)
    if path.is_symlink():
        raise EngineError("Refusing symlink export")
    fd, temp = tempfile.mkstemp(prefix=".export-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("[\n")
            first = True
            for row in rows:
                if not first:
                    stream.write(",\n")
                stream.write(redact(json.dumps(dict(row), ensure_ascii=True)))
                first = False
            stream.write("\n]\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def boundary_rows(store):
    for row in store.db.execute("""SELECT n.key entity,n.type,e.type role,e.source,e.confidence,e.evidence
                                  FROM nodes n JOIN edges e ON n.key=e.target WHERE n.boundary=1
                                  ORDER BY n.key,e.source,e.type,e.file"""):
        result = dict(row)
        result["evidence"] = json.loads(result["evidence"])
        yield result


def build_index(root: Path, cache: Path | None = None, mode="deep", ref="HEAD", worktree=False,
                config: IndexConfig | None = None, slot="current"):
    root = root.resolve()
    if mode not in {"deep", "boundary"}:
        raise EngineError("Invalid indexing mode")
    config = config or IndexConfig()
    started = time.monotonic()
    commit, entries = snapshot(root, ref, worktree)
    selected = {p: e for p, e in entries.items() if config.accepts(p)}
    if len(selected) > config.max_files:
        raise EngineError("Repository exceeds configured file limit")
    directory = index_dir(root, cache, slot)
    validate_output(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stats = {"files_discovered": len(entries), "files_parsed": 0, "files_reused": 0,
             "files_skipped": len(entries) - len(selected), "files_deleted": 0, "warnings": []}
    state = record(RepositoryState(repository_id(root), str(root), commit, mode, fingerprint(entries, config), record(config)))
    state["worktree"] = worktree
    with Store(directory / "repository-index.sqlite") as store:
        old = store.state()
        rebuild = not old or any(old.get(k) != state[k] for k in ("mode", "schema_version", "adapter_version", "config"))
        with store.db:
            if rebuild:
                for table in ("files", "symbols", "definitions", "edges", "nodes"):
                    store.db.execute(f"DELETE FROM {table}")
            old_files = {r["path"]: r["identity"] for r in store.db.execute("SELECT path,identity FROM files")}
            for path in old_files.keys() - selected.keys():
                store.remove(path)
                stats["files_deleted"] += 1
            pending = []
            for path, entry in sorted(selected.items()):
                if old_files.get(path) == entry[0]:
                    stats["files_reused"] += 1
                else:
                    pending.append((path, entry))

            def extract(item):
                path, entry, payload = item
                if entry[1] > config.max_file_bytes:
                    return path, entry, ParsedFile(warnings=[f"Oversized file skipped: {path}"]), True
                try:
                    if payload is not None:
                        if b"\0" in payload:
                            raise EngineError("Binary file skipped")
                        text = payload.decode("utf-8-sig", errors="replace")
                    else:
                        text = content(root, path, entry, config.max_file_bytes)
                except EngineError as exc:
                    if "Binary" in str(exc):
                        return path, entry, ParsedFile(warnings=[f"Binary file skipped: {path}"]), True
                    raise
                return path, entry, parse(path, text, mode, commit, config.adapters), False

            # Byte and count bounds cap in-flight blobs and parsed records.
            def batches():
                batch, size = [], 0
                for item in pending:
                    item_size = min(item[1][1], config.max_file_bytes)
                    if batch and (len(batch) >= 64 or size + item_size > max(8_000_000, config.max_file_bytes)):
                        yield batch
                        batch, size = [], 0
                    batch.append(item)
                    size += item_size
                if batch:
                    yield batch

            with ThreadPoolExecutor(max_workers=config.workers) as pool:
                for batch in batches():
                    payloads = batch_blobs(root, batch, config.max_file_bytes)
                    inputs = [(path, entry, payloads.get(path)) for path, entry in batch]
                    for path, entry, parsed, skipped in pool.map(extract, inputs):
                        store.put(FileRecord(path, entry[0], entry[1], language(path)), parsed)
                        stats["files_skipped" if skipped else "files_parsed"] += 1
            store.cleanup()
            store.set_state(state)
        stats["warnings"] = list(itertools.islice((warning for row in store.db.execute("SELECT warnings FROM files ORDER BY path")
                                                   for warning in json.loads(row[0])), 1000))
        for table, key in (("nodes", "nodes_created"), ("edges", "edges_created"), ("symbols", "symbols")):
            stats[key] = store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        stats["boundary_entities"] = store.db.execute("SELECT count(*) FROM nodes WHERE boundary=1").fetchone()[0]
        graph_dir = directory / "graph"
        graph_dir.mkdir(exist_ok=True)
        changed = rebuild or stats["files_parsed"] or stats["files_deleted"] or pending
        if changed or not (directory / "boundary.json").exists():
            _export_array(directory / "boundary.json", boundary_rows(store))
        if changed or not (directory / "repository-index.json").exists():
            _export_array(directory / "repository-index.json", store.db.execute("SELECT * FROM files ORDER BY path"))
        if changed or not (graph_dir / "dependency-graph.json").exists():
            _export_array(graph_dir / "dependency-graph.json", (
                dict(row) | {"evidence": json.loads(row["evidence"])}
                for row in store.db.execute("SELECT source,target,type,confidence,evidence FROM edges ORDER BY source,target,type")))
        write_json(graph_dir / "graph-manifest.json", {"schema_version": SCHEMA_VERSION, "commit": commit,
                                                      "nodes": stats["nodes_created"], "edges": stats["edges_created"]})
    stats["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(directory / "manifest.json", state | {"statistics": stats})
    write_json(directory / "state.json", state)
    return {"directory": str(directory), "state": state, "statistics": stats}
