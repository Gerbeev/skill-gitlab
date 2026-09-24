"""Explicit repository identity and external-resource namespaces."""

import re
from urllib.parse import quote

from .safety import EngineError, read_json

LOCAL_SCHEMES = {"file", "symbol", "external-symbol", "module"}


def settings(root):
    path = root / ".repository-identity.json"
    value = read_json(path) if path.exists() else {}
    if not isinstance(value, dict) or set(value) - {"repository_id", "namespaces"}:
        raise EngineError("Invalid repository identity settings")
    identifier = value.get("repository_id")
    if identifier is not None and (not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", identifier)):
        raise EngineError("Repository identity must be a stable alphanumeric identifier")
    namespaces = value.get("namespaces", {})
    if not isinstance(namespaces, dict) or any(
        not isinstance(k, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", k) or k in LOCAL_SCHEMES
        or not isinstance(v, str) or not v.strip() or len(v) > 256 for k, v in namespaces.items()
    ):
        raise EngineError("Invalid external-resource namespaces")
    return value


def external_entity(key):
    return "://" in key and key.split("://", 1)[0] not in LOCAL_SCHEMES


def qualify(parsed, namespaces):
    def key(value):
        scheme, separator, name = value.partition("://")
        if separator and scheme in namespaces:
            return scheme + "://" + quote(namespaces[scheme], safe="") + "/" + name
        return value
    for node in parsed.nodes:
        node.key = key(node.key)
    for edge in parsed.edges:
        edge.source, edge.target = key(edge.source), key(edge.target)
    return parsed
