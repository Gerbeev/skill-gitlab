"""Resolve mr_impact engine locations (dev source vs bundled runtime)."""

from __future__ import annotations

from pathlib import Path

ENGINE_SRC = Path("src") / "mr_impact"


def _is_engine_root(root: Path) -> bool:
    return (root / ENGINE_SRC).is_dir()


def engine_from_config(project_root: Path) -> Path | None:
    try:
        from config_utils import ConfigError, load_central_config
    except ImportError:
        return None
    try:
        cfg = load_central_config(project_root)
    except ConfigError:
        return None
    raw = cfg.get("core", {}).get("engine_project")
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = Path(raw.replace("{project-root}", project_root.as_posix()))
    return candidate if _is_engine_root(candidate) else None


def resolve_source_engine_for_copy(project_root: Path, method_dir: Path) -> Path | None:
    """Checkout paths used when setup copies the engine into ``_mr-impact/engine``."""
    for candidate in (project_root / "skills" / "_engine", method_dir.parent / "_engine"):
        if _is_engine_root(candidate):
            return candidate
    return None


def resolve_runtime_engine_root(project_root: Path) -> Path:
    """Path passed to ``run_engine`` (config override, bundle, then dev checkout)."""
    configured = engine_from_config(project_root)
    if configured is not None:
        return configured
    bundled = project_root / "_mr-impact" / "engine"
    if _is_engine_root(bundled):
        return bundled
    return project_root / "skills" / "_engine"
