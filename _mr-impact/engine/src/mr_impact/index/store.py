from __future__ import annotations

import sqlite3
from pathlib import Path

from mr_impact.models import Edge, FileIndexResult, Symbol

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY,
  language TEXT NOT NULL,
  adapter TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL,
  FOREIGN KEY (path) REFERENCES files(path) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  target TEXT NOT NULL,
  edge_type TEXT NOT NULL,
  confidence TEXT NOT NULL,
  evidence TEXT NOT NULL,
  line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL,
  FOREIGN KEY (path) REFERENCES files(path) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
CREATE INDEX IF NOT EXISTS idx_edges_path ON edges(path);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
"""


class IndexStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def file_hash(self, path: str) -> str | None:
        row = self._conn.execute("SELECT content_hash FROM files WHERE path = ?", (path,)).fetchone()
        return row[0] if row else None

    def replace_file(self, result: FileIndexResult, size_bytes: int, indexed_at: str) -> None:
        self._conn.execute("DELETE FROM edges WHERE path = ?", (result.rel_path,))
        self._conn.execute("DELETE FROM symbols WHERE path = ?", (result.rel_path,))
        self._conn.execute("DELETE FROM files WHERE path = ?", (result.rel_path,))
        self._conn.execute(
            """
            INSERT INTO files(path, language, adapter, content_hash, size_bytes, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.rel_path,
                result.language,
                result.adapter,
                result.content_hash,
                size_bytes,
                indexed_at,
            ),
        )
        self._insert_symbols(result.rel_path, result.symbols)
        self._insert_edges(result.rel_path, result.edges)

    def _insert_symbols(self, path: str, symbols: list[Symbol]) -> None:
        self._conn.executemany(
            """
            INSERT INTO symbols(path, name, kind, line_start, line_end)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(path, s.name, s.kind, s.line_start, s.line_end) for s in symbols],
        )

    def _insert_edges(self, path: str, edges: list[Edge]) -> None:
        self._conn.executemany(
            """
            INSERT INTO edges(path, target, edge_type, confidence, evidence, line_start, line_end)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (path, e.target, e.edge_type, e.confidence, e.evidence, e.line_start, e.line_end)
                for e in edges
            ],
        )

    def remove_file(self, path: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM files WHERE path = ?", (path,)).fetchone()
        if not row:
            return False
        self._conn.execute("DELETE FROM files WHERE path = ?", (path,))
        return True

    def remove_paths_not_in(self, keep: set[str]) -> int:
        rows = self._conn.execute("SELECT path FROM files").fetchall()
        removed = 0
        for (path,) in rows:
            if path not in keep:
                self._conn.execute("DELETE FROM files WHERE path = ?", (path,))
                removed += 1
        return removed

    def commit(self) -> None:
        self._conn.commit()

    def stats(self) -> dict[str, int]:
        files = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        symbols = self._conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        edges = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return {"files": files, "symbols": symbols, "edges": edges}

    def export_summary(self) -> dict:
        by_adapter = self._conn.execute(
            "SELECT adapter, COUNT(*) FROM files GROUP BY adapter ORDER BY adapter"
        ).fetchall()
        by_language = self._conn.execute(
            "SELECT language, COUNT(*) FROM files GROUP BY language ORDER BY language"
        ).fetchall()
        return {
            "files_by_adapter": {a: c for a, c in by_adapter},
            "files_by_language": {lang: c for lang, c in by_language},
            **self.stats(),
        }

    def iter_graph_edges(self) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT path, target, edge_type, confidence, evidence, line_start, line_end
            FROM edges
            """
        ).fetchall()
        return [
            {
                "from_file": r[0],
                "target": r[1],
                "type": r[2],
                "confidence": r[3],
                "evidence": r[4],
                "line_start": r[5],
                "line_end": r[6],
            }
            for r in rows
        ]

    def symbols_for_paths(self, paths: set[str]) -> list[dict]:
        if not paths:
            return []
        placeholders = ",".join("?" for _ in paths)
        rows = self._conn.execute(
            f"""
            SELECT path, name, kind, line_start, line_end
            FROM symbols WHERE path IN ({placeholders})
            ORDER BY path, line_start
            """,
            sorted(paths),
        ).fetchall()
        return [
            {
                "path": r[0],
                "name": r[1],
                "kind": r[2],
                "line_start": r[3],
                "line_end": r[4],
            }
            for r in rows
        ]

    def iter_graph_nodes(self) -> list[dict]:
        symbols = self._conn.execute(
            "SELECT path, name, kind, line_start, line_end FROM symbols"
        ).fetchall()
        nodes = [
            {
                "id": f"sym:{path}:{name}:{line_start}",
                "path": path,
                "name": name,
                "kind": kind,
                "line_start": line_start,
                "line_end": line_end,
            }
            for path, name, kind, line_start, line_end in symbols
        ]
        files = self._conn.execute("SELECT path, language, adapter FROM files").fetchall()
        for path, language, adapter in files:
            nodes.append(
                {
                    "id": f"file:{path}",
                    "path": path,
                    "name": path,
                    "kind": "file",
                    "language": language,
                    "adapter": adapter,
                }
            )
        return nodes
