"""Measure repeatable local indexing scenarios without executing indexed code."""

import argparse
import json
import platform
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "src"))

from tests.helpers import commit, initialize
from mr_impact.analysis import analyze_mr
from mr_impact.catalog import aggregate
from mr_impact.indexing import build_index


def run(files):
    measurements = []

    def measure(name, operation):
        tracemalloc.start()
        start = time.perf_counter()
        try:
            result = operation()
            elapsed = time.perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        measurements.append({"scenario": name, "elapsed_seconds": round(elapsed, 4),
                             "peak_python_bytes": peak, "statistics": result.get("statistics", {}),
                             "candidate_repositories": result.get("candidate_repositories")})
        return result

    with tempfile.TemporaryDirectory(prefix="mr-impact-benchmark-") as temporary:
        work = Path(temporary)
        root = work / "producer"
        (root / "src").mkdir(parents=True)
        for number in range(files):
            (root / f"src/unit_{number}.py").write_text(
                f'def execute_{number}(value: int = 1):\n    query = "INSERT INTO audit.events VALUES (1)"\n    return value\n',
                encoding="utf-8")
        base = initialize(root)
        cache = work / "cache"
        measure("initial_deep", lambda: build_index(root, cache))
        noop = measure("no_op", lambda: build_index(root, cache))
        assert noop["statistics"]["files_parsed"] == 0
        changed = root / "src/unit_0.py"
        changed.write_text(changed.read_text().replace("return value", "return value + 1"), encoding="utf-8")
        head = commit(root)
        updated = measure("one_file_update", lambda: build_index(root, cache))
        assert updated["statistics"]["files_parsed"] == 1
        measure("boundary", lambda: build_index(root, work / "boundary-cache", "boundary"))
        candidate = work / "consumer"
        candidate.mkdir()
        (candidate / "report.sql").write_text("CREATE PROCEDURE REPORT AS\nSELECT * FROM audit.events;\n", encoding="utf-8")
        initialize(candidate)
        boundary = build_index(candidate, cache, "boundary")
        catalog = work / "organization.sqlite"
        aggregate(catalog, [Path(boundary["directory"])])
        impact = measure("candidate_expansion", lambda: analyze_mr(root, work / "mr", base, head, cache=cache, catalog=catalog))
        assert impact["candidate_repositories"] == 1
    return {"python": platform.python_version(), "platform": platform.platform(), "input_files": files,
            "memory_measurement": "Peak Python allocations from tracemalloc; excludes Git subprocess memory and native SQLite allocations.",
            "scope": "Synthetic local repository and one candidate; not an organization-scale performance claim.",
            "measurements": measurements}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.files <= 10000:
        parser.error("--files must be between 1 and 10000")
    print(json.dumps(run(args.files), indent=2))
