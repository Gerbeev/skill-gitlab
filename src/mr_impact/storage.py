"""SQLite storage and bounded, directional impact traversal."""

import json
import sqlite3
from collections import deque
from pathlib import Path

from .models import Limits, record
from .safety import EngineError, validate_output

DDL = """
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files (
 path TEXT PRIMARY KEY, identity TEXT NOT NULL, size INTEGER NOT NULL,
 language TEXT NOT NULL, warnings TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS nodes (
 key TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL, boundary INTEGER NOT NULL,
 metadata TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS definitions (
 node TEXT NOT NULL, file TEXT NOT NULL, evidence TEXT NOT NULL,
 PRIMARY KEY(node,file));
CREATE INDEX IF NOT EXISTS definitions_file ON definitions(file);
CREATE TABLE IF NOT EXISTS symbols (
 id TEXT PRIMARY KEY, file TEXT NOT NULL, qualified_name TEXT NOT NULL, type TEXT NOT NULL,
 start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, language TEXT NOT NULL,
 signature TEXT NOT NULL, confidence INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS symbols_file ON symbols(file,start_line,end_line);
CREATE TABLE IF NOT EXISTS edges (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL, target TEXT NOT NULL, type TEXT NOT NULL,
 confidence INTEGER NOT NULL, file TEXT NOT NULL, evidence TEXT NOT NULL,
 UNIQUE(source,target,type,file,evidence));
CREATE INDEX IF NOT EXISTS edge_source ON edges(source,type,confidence);
CREATE INDEX IF NOT EXISTS edge_target ON edges(target,type,confidence);
CREATE INDEX IF NOT EXISTS edge_file ON edges(file);
"""


class Store:
    def __init__(self, path: Path):
        validate_output(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise EngineError("Refusing symlink database")
        self.path = path
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(DDL)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def state(self):
        row = self.db.execute("SELECT value FROM state WHERE key='repository'").fetchone()
        return json.loads(row[0]) if row else None

    def set_state(self, state):
        self.db.execute("INSERT OR REPLACE INTO state VALUES ('repository',?)", (json.dumps(state),))

    def remove(self, path):
        for table in ("edges", "definitions", "symbols"):
            self.db.execute(f"DELETE FROM {table} WHERE file=?", (path,))
        self.db.execute("DELETE FROM files WHERE path=?", (path,))

    def put(self, file, parsed):
        self.remove(file.path)
        self.db.execute("INSERT INTO files VALUES (?,?,?,?,?)",
                        (file.path, file.identity, file.size, file.language, json.dumps(parsed.warnings)))
        for node in parsed.nodes:
            reference = node.metadata.get("reference_only", False)
            self.db.execute("INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?)",
                            (node.key, node.type, node.name, int(node.boundary), json.dumps(node.metadata)))
            if not reference:
                self.db.execute("UPDATE nodes SET type=?,name=?,boundary=?,metadata=? WHERE key=?",
                                (node.type, node.name, int(node.boundary), json.dumps(node.metadata), node.key))
                self.db.execute("INSERT OR REPLACE INTO definitions VALUES (?,?,?)",
                                (node.key, file.path, json.dumps(record(node.evidence))))
        for symbol in parsed.symbols:
            self.db.execute("INSERT OR REPLACE INTO symbols VALUES (?,?,?,?,?,?,?,?,?)", tuple(record(symbol).values()))
        for edge in parsed.edges:
            for key in (edge.source, edge.target):
                self.db.execute("INSERT OR IGNORE INTO nodes VALUES (?,'UNRESOLVED',?,0,'{}')", (key, key))
            self.db.execute("INSERT OR IGNORE INTO edges(source,target,type,confidence,file,evidence) VALUES (?,?,?,?,?,?)",
                            (edge.source, edge.target, edge.type, edge.evidence.confidence, file.path, json.dumps(record(edge.evidence))))

    def cleanup(self):
        self.db.execute("""DELETE FROM nodes WHERE key NOT IN (SELECT node FROM definitions)
                        AND key NOT IN (SELECT source FROM edges) AND key NOT IN (SELECT target FROM edges)""")

    def node(self, key):
        row = self.db.execute("SELECT * FROM nodes WHERE key=?", (key,)).fetchone()
        if not row:
            return {"key": key, "type": "UNRESOLVED", "name": key, "boundary": 0, "defined": False}
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        result["defined"] = self.db.execute("SELECT 1 FROM definitions WHERE node=? LIMIT 1", (key,)).fetchone() is not None
        return result

    def symbols(self, path):
        return [dict(r) for r in self.db.execute("SELECT * FROM symbols WHERE file=? ORDER BY start_line,id", (path,))]

    def traverse(self, seeds: list[str], limits: Limits, initial_paths=None, initial_confidence=None):
        """Visit dependents in reverse and produced data forward; never walk all imports outward."""
        found, paths, depths, confidence = {}, {}, {}, {}
        queue = deque()
        for seed in sorted(set(seeds))[:limits.max_nodes]:
            found[seed], paths[seed], depths[seed], confidence[seed] = (
                self.node(seed), (initial_paths or {}).get(seed, []), 0, (initial_confidence or {}).get(seed, 100))
            queue.append(seed)
        edges, seen_edges, truncated = [], set(), len(set(seeds)) > limits.max_nodes
        forward = {"WRITES", "PRODUCES", "PUBLISHES_EVENT", "DEFINES", "CONTAINS", "TESTED_BY"}
        reverse = {"CALLS", "REFERENCES", "USES", "IMPORTS", "INHERITS", "IMPLEMENTS", "READS", "CONSUMES",
                   "EXECUTES", "LAUNCHES", "DEPENDS_ON", "CONFIGURES", "DEFINES", "CONTAINS", "TRIGGERS"}
        while queue:
            key = queue.popleft()
            if depths[key] >= limits.max_depth:
                truncated |= bool(self.db.execute("SELECT 1 FROM edges WHERE source=? OR target=? LIMIT 1", (key, key)).fetchone())
                continue
            remaining = limits.max_edges - len(edges)
            forward_types = sorted(forward & set(limits.edge_types)) if limits.edge_types else sorted(forward)
            reverse_types = sorted(reverse & set(limits.edge_types)) if limits.edge_types else sorted(reverse)
            f_placeholders = ",".join("?" for _ in forward_types) or "NULL"
            r_placeholders = ",".join("?" for _ in reverse_types) or "NULL"
            rows = self.db.execute(f"""SELECT * FROM edges
                                  WHERE ((source=? AND type IN ({f_placeholders}))
                                  OR (target=? AND type IN ({r_placeholders}))) AND confidence>=?
                                  ORDER BY confidence DESC,source,target,type LIMIT ?""",
                                   (key, *forward_types, key, *reverse_types, limits.confidence, remaining + 1))
            for row in rows:
                if limits.edge_types and row["type"] not in limits.edge_types:
                    continue
                outgoing = row["source"] == key
                if row["type"] not in (forward if outgoing else reverse):
                    continue
                other = row["target"] if outgoing else row["source"]
                if row["id"] not in seen_edges:
                    if len(edges) >= limits.max_edges:
                        truncated = True
                        break
                    edge = dict(row)
                    edge["evidence"] = json.loads(edge["evidence"])
                    edges.append(edge)
                    seen_edges.add(row["id"])
                if other in found:
                    continue
                if len(found) >= limits.max_nodes:
                    truncated = True
                    continue
                step = {"from": key, "to": other, "type": row["type"],
                        "direction": "forward" if outgoing else "reverse",
                        "confidence": row["confidence"], "evidence": json.loads(row["evidence"])}
                found[other] = self.node(other)
                paths[other] = paths[key] + [step]
                confidence[other] = min(confidence[key], row["confidence"])
                depths[other] = depths[key] + 1
                queue.append(other)
            if len(edges) >= limits.max_edges:
                truncated |= bool(queue)
                break
        return {"nodes": list(found.values()), "edges": edges, "paths": paths,
                "confidence": confidence, "truncated": truncated}
