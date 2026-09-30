from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

_MIN_CONFIDENCE = {"high": 0.9, "medium": 0.7, "low": 0.5}

_UPSTREAM_EDGE_TYPES = frozenset(
    {
        "sql_call",
        "sql_reference",
        "script_path",
        "calls",
        "csharp_using",
        "package_reference",
        "project_reference",
        "job_reference",
        "box_member",
        "path_literal",
    }
)

_PATH_LIKE = re.compile(r"[/\\]")


def _norm(value: str) -> str:
    return value.replace("\\", "/").strip().lower()


def _confidence_value(raw: str | float | None) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if raw is None:
        return 0.5
    return _MIN_CONFIDENCE.get(str(raw).lower(), 0.5)


@dataclass(frozen=True)
class PathHop:
    node: str
    node_type: str
    from_file: str | None
    edge_type: str | None
    evidence: str | None

    def as_dict(self) -> dict:
        return {
            "node": self.node,
            "type": self.node_type,
            "from_file": self.from_file,
            "edge_type": self.edge_type,
            "evidence": self.evidence,
        }


@dataclass
class PrimaryQaTarget:
    job: str
    box: str | None
    impact: str
    seed: dict
    path: list[PathHop] = field(default_factory=list)
    recommended_run: list[str] = field(default_factory=list)
    recommended_verify: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def as_dict(self) -> dict:
        return {
            "job": self.job,
            "box": self.box,
            "impact": self.impact,
            "seed": self.seed,
            "path": [h.as_dict() for h in self.path],
            "recommended_run": self.recommended_run,
            "recommended_verify": self.recommended_verify,
            "confidence": round(self.confidence, 3),
        }

    def legacy_target(self) -> dict:
        path_str = " → ".join(h.node for h in self.path) if self.path else self.job
        why = (
            f"Nearest indexed path from {self.seed.get('name', self.seed.get('path', 'change'))} "
            f"to job `{self.job}`"
        )
        if self.box:
            why += f" (box `{self.box}`)"
        return {
            "job_or_process": self.job,
            "why_affected": why,
            "suggested_run": self.recommended_run[0] if self.recommended_run else f"Run `{self.job}`",
            "suggested_verify": (
                self.recommended_verify[0]
                if self.recommended_verify
                else f"Confirm job `{self.job}` completes successfully"
            ),
            "dependency_path": path_str,
            "confidence": (
                "high"
                if self.confidence >= 0.85
                else "medium"
                if self.confidence >= 0.7
                else "low"
            ),
        }


class _RuntimeGraph:
    def __init__(self, edges: list[dict], symbols: list[dict]) -> None:
        self.edges = edges
        self.symbols = symbols
        self._incoming: dict[str, list[dict]] = {}
        self._jobs_by_file: dict[str, list[str]] = {}
        self._box_by_jil: dict[str, str | None] = {}
        self._symbols_by_file: dict[str, list[dict]] = {}

        for sym in symbols:
            path = str(sym.get("path", "")).replace("\\", "/")
            self._symbols_by_file.setdefault(path, []).append(sym)
            if sym.get("kind") == "autosys_job":
                self._jobs_by_file.setdefault(path, []).append(str(sym["name"]))

        for edge in edges:
            target_key = _norm(str(edge.get("target", "")))
            if not target_key:
                continue
            self._incoming.setdefault(target_key, []).append(edge)
            if edge.get("type") == "box_parent":
                jil = str(edge.get("from_file", "")).replace("\\", "/")
                self._box_by_jil[jil] = str(edge.get("target", ""))

    def _incoming_edges(self, node_keys: set[str]) -> list[dict]:
        found: list[dict] = []
        seen: set[int] = set()
        for key in node_keys:
            for edge in self._incoming.get(key, []):
                if edge.get("type") not in _UPSTREAM_EDGE_TYPES:
                    continue
                eid = id(edge)
                if eid in seen:
                    continue
                seen.add(eid)
                found.append(edge)
        return found

    def _node_keys_for_symbol(self, sym: dict) -> set[str]:
        path = str(sym.get("path", "")).replace("\\", "/")
        name = str(sym.get("name", ""))
        keys = {_norm(name), _norm(f"{path}:{name}")}
        if "." in name:
            keys.add(_norm(name.split(".")[-1]))
            keys.add(_norm(name.replace(".", "/")))
        return {k for k in keys if k}

    def _node_keys_for_path(self, path: str) -> set[str]:
        path = path.replace("\\", "/")
        keys = {_norm(path), _norm(Path(path).name)}
        return {k for k in keys if k}

    def _hop_for_file(self, path: str, edge: dict | None) -> PathHop:
        p = path.replace("\\", "/")
        ntype = "JIL" if p.endswith(".jil") or p.endswith(".job") else "FILE"
        if p.endswith(".sql") or "/sql/" in p.lower():
            ntype = "SQL_FILE"
        elif p.endswith(".py"):
            ntype = "SCRIPT"
        elif p.endswith(".cs"):
            ntype = "CODE_FILE"
        return PathHop(
            node=p,
            node_type=ntype,
            from_file=p,
            edge_type=edge.get("type") if edge else None,
            evidence=edge.get("evidence") if edge else None,
        )

    def _hop_for_symbol(self, sym: dict) -> PathHop:
        kind = str(sym.get("kind", "symbol"))
        ntype = "SQL_OBJECT" if kind.startswith("oracle_") else kind.upper()
        return PathHop(
            node=str(sym["name"]),
            node_type=ntype,
            from_file=str(sym.get("path", "")).replace("\\", "/"),
            edge_type=None,
            evidence=f"symbol {sym.get('diff_match', 'indexed')}",
        )

    def _hop_for_job(self, job: str, jil_file: str, box: str | None) -> PathHop:
        return PathHop(
            node=job,
            node_type="AUTOSYS_JOB",
            from_file=jil_file,
            edge_type="script_path",
            evidence=f"job definition in {jil_file}",
        )

    def _hop_for_box(self, box: str, jil_file: str) -> PathHop:
        return PathHop(
            node=box,
            node_type="AUTOSYS_BOX",
            from_file=jil_file,
            edge_type="box_parent",
            evidence=f"box_name in {jil_file}",
        )

    def _jobs_for_jil(self, jil_path: str, script_hint: str | None) -> list[str]:
        jobs = list(self._jobs_by_file.get(jil_path, []))
        if not jobs:
            return []
        if not script_hint:
            return []
        hint = _norm(script_hint)
        job_symbols = [s for s in self._symbols_by_file.get(jil_path, []) if s.get("kind") == "autosys_job"]
        matched: list[str] = []
        for edge in self.edges:
            if edge.get("from_file") != jil_path or edge.get("type") != "script_path":
                continue
            target = _norm(str(edge.get("target", "")))
            if target != hint and hint not in target and target not in hint:
                continue
            cmd_line = int(edge.get("line_start") or 0)
            candidate: tuple[int, str] | None = None
            for sym in job_symbols:
                job_line = int(sym.get("line_start") or 0)
                if job_line <= cmd_line:
                    if candidate is None or job_line > candidate[0]:
                        candidate = (job_line, str(sym["name"]))
            if candidate:
                matched.append(candidate[1])
        if matched:
            return matched
        if len(jobs) == 1:
            return jobs
        return jobs[:1]

    def _box_for_jil(self, jil_path: str) -> str | None:
        return self._box_by_jil.get(jil_path)

    def find_nearest_jobs(
        self,
        seeds: list[dict],
        *,
        max_depth: int = 12,
        max_paths: int = 5,
    ) -> tuple[list[PrimaryQaTarget], list[dict]]:
        """Return primary QA targets and unresolved seed records."""
        results: list[PrimaryQaTarget] = []
        unresolved: list[dict] = []
        seen_jobs: set[str] = set()

        for seed in seeds:
            target = self._shortest_path_to_job(seed, max_depth=max_depth)
            if target is None:
                unresolved.append(
                    {
                        "seed": seed,
                        "reason": "No indexed path to an AutoSys job within depth limit",
                        "prefix": self._best_prefix(seed, max_depth=max_depth),
                    }
                )
                continue
            if target.job in seen_jobs:
                continue
            seen_jobs.add(target.job)
            results.append(target)
            if len(results) >= max_paths:
                break

        return results, unresolved

    def _shortest_path_to_job(self, seed: dict, *, max_depth: int) -> PrimaryQaTarget | None:
        best: PrimaryQaTarget | None = None
        start_hops = self._initial_hops(seed)
        if not start_hops:
            return None

        # BFS state: (frontier keys, path hops, last file path, depth)
        queue: deque[tuple[set[str], list[PathHop], str | None, int]] = deque()
        visited: set[str] = set()

        initial_keys = set()
        for hop in start_hops:
            initial_keys |= self._keys_from_hop(hop)
        queue.append((initial_keys, start_hops, start_hops[-1].from_file, 0))

        while queue:
            keys, path, last_file, depth = queue.popleft()
            state_sig = "|".join(sorted(keys))
            if state_sig in visited:
                continue
            visited.add(state_sig)

            if last_file and (last_file.endswith(".jil") or last_file.endswith(".job")):
                script_hint = None
                for hop in reversed(path):
                    candidate = (hop.from_file or hop.node or "").replace("\\", "/")
                    if candidate.endswith((".py", ".sql", ".pls", ".sh", ".ps1")):
                        script_hint = candidate
                        break
                    if hop.node_type == "SCRIPT" or hop.node.endswith(".py"):
                        script_hint = hop.node
                        break
                for job in self._jobs_for_jil(last_file, script_hint):
                    box = self._box_for_jil(last_file)
                    job_hops = list(path) + [self._hop_for_job(job, last_file, box)]
                    if box:
                        job_hops.append(self._hop_for_box(box, last_file))
                    conf = self._path_confidence(job_hops)
                    candidate = PrimaryQaTarget(
                        job=job,
                        box=box,
                        impact="DIRECTLY_AFFECTED",
                        seed=seed,
                        path=job_hops,
                        recommended_run=[f"Run AutoSys job `{job}` in QA after deploy"],
                        recommended_verify=[
                            f"Confirm `{job}` completes; re-check behavior tied to {seed.get('name', seed.get('path'))}"
                        ],
                        confidence=conf,
                    )
                    if best is None or len(job_hops) < len(best.path) or (
                        len(job_hops) == len(best.path) and conf > best.confidence
                    ):
                        best = candidate
                if best:
                    return best

            if depth >= max_depth:
                continue

            for edge in self._incoming_edges(keys):
                caller_file = str(edge.get("from_file", "")).replace("\\", "/")
                if not caller_file:
                    continue
                hop = self._hop_for_file(caller_file, edge)
                next_path = path + [hop]
                next_keys = self._keys_from_hop(hop)
                # Also match symbols defined in caller file
                for sym in self._symbols_by_file.get(caller_file, []):
                    next_keys |= self._node_keys_for_symbol(sym)
                queue.append((next_keys, next_path, caller_file, depth + 1))

        return best

    def _best_prefix(self, seed: dict, *, max_depth: int) -> list[dict]:
        """Longest resolved prefix when no job is reached."""
        start_hops = self._initial_hops(seed)
        if not start_hops:
            return []
        keys = set()
        for hop in start_hops:
            keys |= self._keys_from_hop(hop)
        path = list(start_hops)
        for _ in range(max_depth):
            incoming = self._incoming_edges(keys)
            if not incoming:
                break
            edge = incoming[0]
            caller_file = str(edge.get("from_file", "")).replace("\\", "/")
            hop = self._hop_for_file(caller_file, edge)
            path.append(hop)
            keys = self._keys_from_hop(hop)
        return [h.as_dict() for h in path]

    def _initial_hops(self, seed: dict) -> list[PathHop]:
        kind = seed.get("kind")
        if kind == "changed_file":
            path = str(seed["path"]).replace("\\", "/")
            return [
                PathHop(
                    node=path,
                    node_type="FILE",
                    from_file=path,
                    edge_type=None,
                    evidence="MR changed file",
                )
            ]
        if "name" in seed and "path" in seed:
            sym = seed
            return [self._hop_for_symbol(sym)]
        return []

    def _keys_from_hop(self, hop: PathHop) -> set[str]:
        keys = {_norm(hop.node)}
        if hop.from_file:
            keys |= self._node_keys_for_path(hop.from_file)
        if _PATH_LIKE.search(hop.node):
            keys |= self._node_keys_for_path(hop.node)
        return {k for k in keys if k}

    def _path_confidence(self, hops: list[PathHop]) -> float:
        values = []
        for hop in hops:
            if hop.edge_type:
                # recover from matching edges
                for edge in self._incoming.get(_norm(hop.node), []):
                    if edge.get("from_file") == hop.from_file:
                        values.append(_confidence_value(edge.get("confidence")))
                        break
                else:
                    values.append(0.75)
            else:
                values.append(0.8)
        if not values:
            return 0.7
        return sum(values) / len(values)


def seeds_from_mr_context(
    symbols_touched: list[dict],
    changed_paths: set[str],
) -> list[dict]:
    seeds: list[dict] = []
    seen: set[str] = set()
    for sym in symbols_touched:
        key = f"{sym.get('path')}:{sym.get('name')}"
        if key in seen:
            continue
        seen.add(key)
        seeds.append(
            {
                "kind": sym.get("kind"),
                "name": sym.get("name"),
                "path": sym.get("path"),
                "line_start": sym.get("line_start"),
                "line_end": sym.get("line_end"),
                "diff_match": sym.get("diff_match"),
            }
        )
    for path in sorted(changed_paths):
        norm = path.replace("\\", "/")
        if any(s.get("path") == norm for s in seeds):
            continue
        seeds.append({"kind": "changed_file", "path": norm})
    return seeds


def jobs_for_jil_script(
    edges: list[dict],
    symbols: list[dict],
    jil_path: str,
    script_hint: str,
) -> list[str]:
    graph = _RuntimeGraph(edges, symbols)
    return graph._jobs_for_jil(jil_path.replace("\\", "/"), script_hint)


def _primary_from_linked_job(
    graph: _RuntimeGraph,
    seed: dict,
    changed_paths: set[str],
    edges: list[dict],
) -> PrimaryQaTarget | None:
    if seed.get("kind") != "autosys_job" or seed.get("diff_match") != "linked_file":
        return None
    jil = str(seed.get("path", "")).replace("\\", "/")
    job = str(seed.get("name", ""))
    normalized = {p.replace("\\", "/") for p in changed_paths}
    for cp in sorted(normalized):
        for edge in edges:
            if edge.get("from_file") != jil or edge.get("type") != "script_path":
                continue
            target = str(edge.get("target", "")).replace("\\", "/")
            if not (
                target == cp or target.endswith("/" + cp) or cp.endswith("/" + target) or cp == target
            ):
                continue
            if job not in graph._jobs_for_jil(jil, cp):
                continue
            box = graph._box_for_jil(jil)
            hops = [
                PathHop(
                    node=cp,
                    node_type="SQL_FILE" if cp.endswith(".sql") else "SCRIPT",
                    from_file=cp,
                    edge_type="script_path",
                    evidence=edge.get("evidence"),
                ),
                PathHop(
                    node=jil,
                    node_type="JIL",
                    from_file=jil,
                    edge_type="script_path",
                    evidence=edge.get("evidence"),
                ),
                graph._hop_for_job(job, jil, box),
            ]
            if box:
                hops.append(graph._hop_for_box(box, jil))
            return PrimaryQaTarget(
                job=job,
                box=box,
                impact="DIRECTLY_AFFECTED",
                seed=seed,
                path=hops,
                recommended_run=[f"Run AutoSys job `{job}` in QA after deploy"],
                recommended_verify=[f"Confirm changed artifact `{cp}` via job `{job}`"],
                confidence=_confidence_value(edge.get("confidence")),
            )
    return None


def compute_primary_qa_targets(
    edges: list[dict],
    symbols: list[dict],
    symbols_touched: list[dict],
    changed_paths: set[str],
    *,
    max_depth: int = 12,
    max_paths: int = 5,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (primary_qa_targets as dicts, legacy targets, unresolved)."""
    graph = _RuntimeGraph(edges, symbols)
    seeds = seeds_from_mr_context(symbols_touched, changed_paths)
    primaries_objs: list[PrimaryQaTarget] = []
    seen_jobs: set[str] = set()
    deferred_seeds: list[dict] = []
    for seed in seeds:
        linked = _primary_from_linked_job(graph, seed, changed_paths, edges)
        if linked:
            if linked.job not in seen_jobs:
                seen_jobs.add(linked.job)
                primaries_objs.append(linked)
            continue
        deferred_seeds.append(seed)
    more, unresolved = graph.find_nearest_jobs(
        deferred_seeds, max_depth=max_depth, max_paths=max_paths
    )
    for item in more:
        if item.job in seen_jobs:
            continue
        seen_jobs.add(item.job)
        primaries_objs.append(item)
        if len(primaries_objs) >= max_paths:
            break
    primary_dicts = [p.as_dict() for p in primaries_objs]
    legacy = [p.legacy_target() for p in primaries_objs]

    if not legacy:
        # Direct script_path fallback for changed scripts without symbol overlap
        graph_fallback = _RuntimeGraph(edges, symbols)
        for path in changed_paths:
            norm = path.replace("\\", "/")
            for edge in edges:
                if edge.get("type") != "script_path":
                    continue
                target = str(edge.get("target", "")).replace("\\", "/")
                if not (
                    target == norm
                    or target.endswith("/" + norm)
                    or norm.endswith("/" + target)
                    or norm == target
                ):
                    continue
                jil = str(edge.get("from_file", "")).replace("\\", "/")
                for job in graph_fallback._jobs_for_jil(jil, norm):
                    box = graph_fallback._box_for_jil(jil)
                    hop_script = PathHop(
                        node=norm,
                        node_type="SCRIPT",
                        from_file=norm,
                        edge_type="script_path",
                        evidence=edge.get("evidence"),
                    )
                    hop_jil = PathHop(
                        node=jil,
                        node_type="JIL",
                        from_file=jil,
                        edge_type="script_path",
                        evidence=edge.get("evidence"),
                    )
                    hops = [hop_script, hop_jil, graph_fallback._hop_for_job(job, jil, box)]
                    if box:
                        hops.append(graph_fallback._hop_for_box(box, jil))
                    p = PrimaryQaTarget(
                        job=job,
                        box=box,
                        impact="DIRECTLY_AFFECTED",
                        seed={"kind": "changed_file", "path": norm},
                        path=hops,
                        recommended_run=[f"Run AutoSys job `{job}` in QA after deploy"],
                        recommended_verify=[f"Confirm changed script `{norm}` via job `{job}`"],
                        confidence=_confidence_value(edge.get("confidence")),
                    )
                    if not any(d.get("job") == job for d in primary_dicts):
                        primary_dicts.append(p.as_dict())
                        legacy.append(p.legacy_target())
                        primaries_objs.append(p)

    unresolved = [
        item
        for item in unresolved
        if not _seed_covered_by_primaries(item.get("seed", {}), primary_dicts)
    ]
    return primary_dicts, legacy, unresolved


def _seed_covered_by_primaries(seed: dict, primary_dicts: list[dict]) -> bool:
    if not primary_dicts:
        return False
    path = str(seed.get("path", "")).replace("\\", "/")
    name = seed.get("name")
    for primary in primary_dicts:
        ps = primary.get("seed", {})
        if path and ps.get("path") == path:
            return True
        if name and ps.get("name") == name:
            return True
        for hop in primary.get("path", []):
            node = str(hop.get("node", "")).replace("\\", "/")
            from_file = str(hop.get("from_file", "")).replace("\\", "/")
            if path and (path == node or path == from_file):
                return True
    return False
