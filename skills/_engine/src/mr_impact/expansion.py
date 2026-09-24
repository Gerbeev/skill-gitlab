"""Bounded cross-repository work queue with reusable indexes and new seed labels."""

from collections import deque
from pathlib import Path

from .catalog import lookup, repository_matches
from .git import repository_id, resolve
from .identity import external_entity
from .indexing import build_index
from .locking import repository_lock
from .safety import EngineError
from .storage import Store


def expand(graphs, root, cache, catalog, limits, config, enabled, stack, warnings):
    origin = repository_id(root)
    frontier = deque((group, 0) for group in graphs)
    candidates, stores, labels, failed = {}, {}, {}, set()
    expanded = []
    operations = 0
    while frontier:
        local, depth = frontier.popleft()
        boundaries = [n for n in local["nodes"] if n["boundary"] and external_entity(n["key"])
                      and local["confidence"][n["key"]] >= limits.confidence]
        if depth >= limits.cross_depth:
            if boundaries:
                warnings.append("Cross-repository depth limit reached; further downstream impact is not explored.")
            continue
        matches = {}
        for node in boundaries:
            # Include already indexed candidates so new incoming seeds are not lost.
            for match in lookup(catalog, node["key"], limits.confidence, limits.max_candidates + 1,
                                (origin, local["repository"])):
                matches.setdefault(match["repository"], match)
        for rid, match in sorted(matches.items()):
            if rid in failed:
                continue
            if rid not in candidates:
                if len(candidates) >= limits.max_candidates:
                    warnings.append("Cross-repository candidate limit reached; organization coverage is partial.")
                    continue
                candidates[rid] = {"repository": rid, "entity": match["entity"], "role": match["role"],
                                   "confidence": min(local["confidence"][match["entity"]], match["confidence"]),
                                   "expanded": False, "catalog_commit": match["commit_id"], "entities": []}
            candidate = candidates[rid]
            if not enabled:
                warnings.append(f"Candidate {rid} requires deep expansion to identify runtime targets.")
                continue
            if operations >= limits.max_expansions:
                warnings.append("Cross-repository expansion budget reached; impact coverage is partial.")
                return list(candidates.values()), expanded
            candidate_root = Path(match["root"])
            try:
                if rid not in stores:
                    if not candidate_root.is_dir():
                        raise EngineError("Candidate repository is unavailable locally")
                    stack.enter_context(repository_lock(candidate_root))
                    if repository_id(candidate_root) != rid:
                        raise EngineError("Catalog repository identity changed")
                    current_head = resolve(candidate_root, "HEAD")
                    stale = current_head != match["commit_id"]
                    if stale:
                        warnings.append(f"Stale catalog candidate {rid}; using recorded revision {match['commit_id']} for reproducibility.")
                    indexed = build_index(candidate_root, cache, "deep", match["commit_id"], config=config)
                    store = stack.enter_context(Store(Path(indexed["directory"]) / "repository-index.sqlite"))
                    stores[rid] = (store, stale)
                    candidate["generation"] = indexed["state"]["generation"]
                    warnings.extend(indexed["statistics"]["warnings"])
                store, stale = stores[rid]
                observations = repository_matches(catalog, rid, [n["key"] for n in boundaries], limits.confidence)
                initial_paths, initial_confidence = {}, {}
                for observation in observations:
                    entity = observation["entity"]
                    value = min(local["confidence"][entity], observation["confidence"], 60 if stale else 100)
                    seen = labels.setdefault((rid, entity), [])
                    if any(d <= depth + 1 and c >= value for d, c in seen):
                        continue
                    seen[:] = [(d, c) for d, c in seen if not (depth + 1 <= d and value >= c)]
                    seen.append((depth + 1, value))
                    bridge = {"from": entity, "to": entity, "type": "ORGANIZATION_LOOKUP",
                              "direction": "reverse", "confidence": value, "evidence": observation["evidence"],
                              "repository": rid, "catalog_commit": match["commit_id"]}
                    initial_paths[entity] = local["paths"][entity] + [bridge]
                    initial_confidence[entity] = value
                if not initial_paths:
                    continue
                operations += 1
                subgraph = store.traverse(list(initial_paths), limits, initial_paths, initial_confidence)
            except EngineError as exc:
                failed.add(rid)
                warnings.append(f"Candidate {rid} could not be expanded: {exc}")
                continue
            candidate["expanded"] = True
            candidate["entities"] = sorted(set(candidate["entities"]) | initial_paths.keys())
            candidate["confidence"] = max(candidate["confidence"], max(initial_confidence.values()))
            group = {"repository": rid, "revision": match["commit_id"], **subgraph}
            expanded.append(group)
            if subgraph["truncated"]:
                warnings.append(f"Candidate {rid} graph traversal reached a limit.")
            frontier.append((group, depth + 1))
    return list(candidates.values()), expanded
