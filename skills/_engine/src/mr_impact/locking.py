"""Fail-fast, process-safe operation locks with same-thread reentrancy."""

import os
import hashlib
import tempfile
import threading
from contextlib import contextmanager
from functools import wraps
from inspect import signature
from pathlib import Path

from .safety import EngineError, validate_output

_guard = threading.Lock()
_owners = {}


@contextmanager
def operation_lock(path: Path):
    validate_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path.resolve())
    owner = threading.get_ident()
    with _guard:
        existing = _owners.get(key)
        if existing and existing[0] != owner:
            raise EngineError("Repository or catalog is busy; retry after the active operation completes")
        if existing:
            existing[1] += 1
        else:
            stream = path.open("a+b")
            try:
                if os.name == "nt":
                    import msvcrt
                    if stream.seek(0, 2) == 0:
                        stream.write(b"\0")
                        stream.flush()
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                stream.close()
                raise EngineError("Repository or catalog is busy; retry after the active operation completes") from exc
            _owners[key] = [owner, 1, stream]
    try:
        yield
    finally:
        with _guard:
            entry = _owners[key]
            entry[1] -= 1
            if not entry[1]:
                stream = entry[2]
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                stream.close()
                del _owners[key]


def repository_lock(root: Path):
    # Keep locks outside analyzed worktrees, including when a shared cache is used.
    user = hashlib.sha256(str(Path.home()).encode()).hexdigest()[:16]
    repository = hashlib.sha256(os.path.normcase(str(root.resolve())).encode()).hexdigest()
    return operation_lock(Path(tempfile.gettempdir()) / ("mr-impact-locks-" + user) / (repository + ".lock"))


def locked_repository(function):
    parameters = signature(function)

    @wraps(function)
    def invoke(*args, **kwargs):
        root = parameters.bind(*args, **kwargs).arguments["root"]
        with repository_lock(root):
            return function(*args, **kwargs)
    return invoke


def catalog_lock(path: Path):
    return operation_lock(path.with_name(path.name + ".lock"))


def locked_catalog(function):
    parameters = signature(function)

    @wraps(function)
    def invoke(*args, **kwargs):
        path = parameters.bind(*args, **kwargs).arguments["catalog"]
        with catalog_lock(path):
            return function(*args, **kwargs)
    return invoke
