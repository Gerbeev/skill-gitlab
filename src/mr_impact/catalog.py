"""Compact organization reverse index. No global method-level graph."""

import json
import sqlite3
from pathlib import Path

from .indexing import boundary_rows
from .safety import EngineError, validate_output, write_json
from .storage import Store

CATALOG_DDL = """
CREATE TABLE IF NOT EXISTS repositories (
 id TEXT PRIMARY KEY, root TEXT NOT NULL, directory TEXT NOT NULL, commit_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dependencies (
 repository TEXT NOT NULL, entity TEXT NOT NULL, type TEXT NOT NULL, role TEXT NOT NULL,
 source TEXT NOT NULL, confidence INTEGER NOT NULL, evidence TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS reverse_lookup ON dependencies(entity,confidence,repository);
CREATE INDEX IF NOT EXISTS repository_dependencies ON dependencies(repository);
"""


def connect(path):
    validate_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise EngineError("Refusing symlink catalog")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(CATALOG_DDL)
    return db


def aggregate(catalog: Path, directories: list[Path], replace=False):
    db = connect(catalog)
    try:
        with db:
            if replace:
                db.execute("DELETE FROM dependencies")
                db.execute("DELETE FROM repositories")
            for directory in directories:
                if not (directory / "repository-index.sqlite").is_file():
                    raise EngineError("Repository index does not exist")
                with Store(directory / "repository-index.sqlite") as store:
                    state = store.state()
                    if not state:
                        raise EngineError("Repository index has no completed state")
                    if state.get("worktree"):
                        raise EngineError("Organization catalogs require committed indexes for reproducible candidate expansion")
                    rid = state["repository_id"]
                    db.execute("DELETE FROM dependencies WHERE repository=?", (rid,))
                    db.execute("INSERT OR REPLACE INTO repositories VALUES (?,?,?,?,?)",
                               (rid, state["root"], str(directory.resolve()), state["commit"], state["fingerprint"]))
                    for row in boundary_rows(store):
                        db.execute("INSERT INTO dependencies VALUES (?,?,?,?,?,?,?)",
                                   (rid, row["entity"], row["type"], row["role"], row["source"],
                                    row["confidence"], json.dumps(row["evidence"])))
        counts = {name: db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in ("repositories", "dependencies")}
        write_json(catalog.with_suffix(".manifest.json"), {"schema_version": 1, **counts})
        return counts
    finally:
        db.close()


def lookup(catalog: Path, entity: str, confidence=30, limit=20, exclude=()):
    if not catalog.is_file():
        raise EngineError("Organization catalog does not exist")
    db = sqlite3.connect(f"{catalog.resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in exclude) or "NULL"
        exclusion = f"AND r.id NOT IN ({placeholders})" if exclude else ""
        rows = db.execute(f"""WITH matches AS (
                              SELECT d.*,r.root,r.directory,r.commit_id,r.fingerprint,
                              ROW_NUMBER() OVER (PARTITION BY r.id ORDER BY d.confidence DESC,d.role,d.source) priority
                              FROM dependencies d JOIN repositories r ON d.repository=r.id
                              WHERE d.entity=? AND d.confidence>=? {exclusion})
                              SELECT * FROM matches WHERE priority=1
                              ORDER BY confidence DESC,repository LIMIT ?""",
                          (entity, confidence, *exclude, limit))
        return [dict(row) | {"evidence": json.loads(row["evidence"])} for row in rows]
    finally:
        db.close()


def repository_matches(catalog: Path, repository: str, entities: list[str], confidence=30):
    """Return one evidence-backed observation per reached boundary for a candidate."""
    db = sqlite3.connect(f"{catalog.resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        matches = []
        for entity in entities:
            row = db.execute("""SELECT * FROM dependencies WHERE repository=? AND entity=? AND confidence>=?
                               ORDER BY confidence DESC,role,source LIMIT 1""", (repository, entity, confidence)).fetchone()
            if row:
                matches.append(dict(row) | {"evidence": json.loads(row["evidence"])})
        return matches
    finally:
        db.close()
