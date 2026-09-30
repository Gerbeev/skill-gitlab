"""Repository analysis directory layout (index, graph, run, catalog)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ANALYSIS_DIR_NAME = ".repository-analysis"
INDEX_DIR_NAME = "index"
GRAPH_DIR_NAME = "graph"
RUN_DIR_NAME = "run"
CATALOG_DIR_NAME = "catalog"

INDEX_SQLITE = "repository-index.sqlite"
DEPENDENCY_GRAPH_JSON = "dependency-graph.json"
GRAPH_MANIFEST_JSON = "graph-manifest.json"
BOUNDARY_CATALOG_JSON = "boundary-catalog.json"


@dataclass(frozen=True, slots=True)
class AnalysisLayout:
    """Resolved paths under the analysis root."""

    root: Path
    index_dir: Path
    graph_dir: Path
    run_dir: Path
    catalog_dir: Path

    @property
    def index_sqlite(self) -> Path:
        return self.index_dir / INDEX_SQLITE

    @property
    def dependency_graph_json(self) -> Path:
        return self.graph_dir / DEPENDENCY_GRAPH_JSON

    @property
    def graph_manifest_json(self) -> Path:
        return self.graph_dir / GRAPH_MANIFEST_JSON

    @property
    def boundary_catalog_json(self) -> Path:
        return self.catalog_dir / BOUNDARY_CATALOG_JSON

    @property
    def index_present(self) -> bool:
        return self.index_sqlite.is_file()

    @property
    def graph_json_present(self) -> bool:
        return self.dependency_graph_json.is_file()


def resolve_analysis_root(project_root: Path, analysis_root: Path | None = None) -> Path:
    if analysis_root is not None:
        return analysis_root.resolve()
    return (project_root / ANALYSIS_DIR_NAME).resolve()


def analysis_layout(project_root: Path, analysis_root: Path | None = None) -> AnalysisLayout:
    root = resolve_analysis_root(project_root, analysis_root)
    return AnalysisLayout(
        root=root,
        index_dir=root / INDEX_DIR_NAME,
        graph_dir=root / GRAPH_DIR_NAME,
        run_dir=root / RUN_DIR_NAME,
        catalog_dir=root / CATALOG_DIR_NAME,
    )


def analysis_paths(project_root: Path, analysis_root: Path | None = None) -> tuple[Path, Path]:
    """Return ``(index_dir, graph_dir)`` — kept for callers that only need those two paths."""
    layout = analysis_layout(project_root, analysis_root)
    return layout.index_dir, layout.graph_dir


def require_index_sqlite(project_root: Path, analysis_root: Path | None = None) -> tuple[Path, AnalysisLayout]:
    layout = analysis_layout(project_root, analysis_root)
    db = layout.index_sqlite
    if not db.is_file():
        raise FileNotFoundError(
            f"index missing: {db} — run create-index before using the repository index"
        )
    return db, layout
