"""Execute the complete local workflow in disposable multi-repository fixtures."""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tests.helpers import commit, initialize
from mr_impact.analysis import analyze_mr
from mr_impact.catalog import aggregate
from mr_impact.indexing import build_index
from mr_impact.issues import analyze_issue, update_issue
from mr_impact.safety import read_text, validate_output, write_json, write_text


def run(output: Path):
    validate_output(output)
    with tempfile.TemporaryDirectory(prefix="mr-impact-example-") as temporary:
        work = Path(temporary)
        a, b, c = [work / name for name in ("repo-a", "repo-b", "repo-c")]
        base = initialize(a, "repo-a")
        initialize(b, "repo-b")
        initialize(c, "repo-c")
        writer = a / "src/RiskWriter.scala"
        writer.write_text(writer.read_text().replace("    val query", '    require(amount >= 0, "Negative exposure")\n    val query'), encoding="utf-8", newline="\n")
        head = commit(a, "Reject negative exposure before persistence")
        cache = work / "cache"
        indexes = [build_index(a, cache)] + [build_index(repo, cache, "boundary") for repo in (b, c)]
        noop = build_index(a, cache)
        assert noop["statistics"]["files_parsed"] == 0
        catalog = work / "organization.sqlite"
        organization = aggregate(catalog, [Path(index["directory"]) for index in indexes])
        source = work / "issue-input"
        shutil.copytree(ROOT / "tests/fixtures/issue", source)
        shutil.copy2(ROOT / "GITLAB_ISSUE_TEMPLATE.md", source / "GITLAB_ISSUE_TEMPLATE.md")
        issue_output = work / "issue-output"
        analyze_issue(source, issue_output)
        assert {p.name for p in issue_output.iterdir()} == {"00-issue-analysis.md", "01-generated-issue.md"}
        modified_template = work / "modified-template.md"
        modified_template.write_text("# Revised Issue\n\n## Acceptance Criteria\n\n{{requirements}}\n\n## Audit retention\n", encoding="utf-8")
        modified_output = work / "modified-output"
        analyze_issue(source, modified_output, template=modified_template)
        modified = (modified_output / "01-generated-issue.md").read_text()
        assert "## Audit retention" in modified and "## Scope" not in modified
        mr_output = work / "mr-output"
        issue = issue_output / "01-generated-issue.md"
        analyze_mr(a, mr_output, base, head, cache=cache, catalog=catalog, issue=issue)
        context = json.loads((mr_output / "mr-context.json").read_text())
        change_index = next(i for i, change in enumerate(context["changes"]) if change["new_path"] == "src/RiskWriter.scala")
        interpretation = work / "mr-interpretation.json"
        write_json(interpretation, {"head": head, "diff_sha256": context["diff_sha256"], "findings": [{
            "change_index": change_index, "hunk_index": 0, "classification": "confirmed",
            "summary": "The writer now checks that amount is nonnegative before constructing the INSERT statement.",
            "validation": "Run daily-risk with amounts -1, 0, and 1. Verify rejection occurs before persistence for -1, and the guard permits 0 and 1. Inspect downstream reporting for the affected partition."}]})
        result = analyze_mr(a, mr_output, base, head, cache=cache, catalog=catalog, issue=issue, interpretation=interpretation)
        runtime = json.loads((mr_output / "runtime-impact.json").read_text())["targets"]
        names = {target["target"] for target in runtime}
        required = {"daily-risk", "DAILY_RISK_JOB", "REPORT_GENERATION_EOD", "REGULATORY_EXPORT_JOB"}
        assert required <= names, names
        assert any(step["type"] == "ORGANIZATION_LOOKUP" for target in runtime for step in target["path"])
        mappings = json.loads((mr_output / "changed-symbols.json").read_text())["mappings"]
        assert any(m["symbol"]["qualified_name"] == "writeExposure" for m in mappings)
        update_issue(issue, mr_output, mr_output, "risk#1427")
        for source_dir, destination in ((issue_output, output / "issue"), (mr_output, output / "mr")):
            for source_file in source_dir.iterdir():
                write_text(destination / source_file.name, read_text(source_file, 20_000_000))
        summary = {"initial_indexes": [{"repository": index["state"]["repository_id"],
                                        "mode": index["state"]["mode"], "statistics": index["statistics"]} for index in indexes],
                   "no_op_statistics": noop["statistics"], "organization": organization,
                   "runtime_targets": sorted(names), "candidate_repositories": result["candidate_repositories"],
                   "checks": {"two_issue_outputs": True, "template_mutation": True, "deep_index": True,
                              "boundary_indexes": True, "no_op_reuse": True, "changed_symbol_mapping": True,
                              "cross_repository_runtime_paths": True, "issue_update_preview": True},
                   "operational_jobs_executed": False}
        write_json(output / "validation-summary.json", summary)
        write_text(output / "README.md", "# Generated local workflow example\n\n"
                   "Generated with `python scripts/run-example.py --output examples/output`.\n\n"
                   "- [Issue analysis](issue/00-issue-analysis.md)\n"
                   "- [Generated Issue](issue/01-generated-issue.md)\n"
                   "- [MR analysis](mr/01-mr-analysis.md)\n"
                   "- [Change context](mr/02-change-context.md)\n"
                   "- [Impact evidence](mr/03-impact-analysis.md)\n"
                   "- [QA execution plan](mr/04-test-plan.md)\n"
                   "- [Issue update preview](mr/05-issue-update.md)\n"
                   "- [Measured validation summary](validation-summary.json)\n\n"
                   "These artifacts describe synthetic fixture changes. No operational jobs were run.\n"
                   "Temporary source repositories and indexes are removed after generation.\n")
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "examples/output")
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
