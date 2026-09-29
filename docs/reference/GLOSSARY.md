# Glossary

Key terms used across MR Impact documentation, skills, and the shared engine. Names match repository paths and Copilot slash commands unless noted.

---

## Product and scope

| Term                 | Meaning                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **MR Impact**        | The product: four GitHub Copilot project skills plus one shared Python engine for Issue analysis, repository indexing, Merge Request impact analysis, and Issue updates. |
| **MR Impact Method** | The installable module (`skills/mr-impact-method/`) that holds `bmod.toml`, shared scripts, and config templates. Not a Copilot slash command.                           |
| **V1 / MVP**         | First shippable version defined in [V1_SCOPE.md](V1_SCOPE.md). Narrower than the full [TASK_STATEMENT.md](TASK_STATEMENT.md).                                            |
| **TASK_STATEMENT**   | Long-term product specification: all four functions, evidence model, and quality bar.                                                                                    |
| **Pilot repository** | A real internal repo used to validate indexing and MR analysis before wider rollout.                                                                                     |

---

## Copilot skills (user surface)

| Term                    | Meaning                                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Project skill**       | A skill stored under `.github/skills/<name>/` that VS Code Copilot exposes as a slash command (e.g. `/analyze-issue`).                                 |
| **Slash command**       | User invocation in Copilot Chat: `/analyze-issue`, `/index-repository`, `/analyze-mr`, `/update-issue`. There are exactly four.                        |
| **Skill package**       | Source folder under `skills/<name>/` containing `SKILL.md`, `workflow.md`, steps, and optional `references/`. Synced to `.github/skills/` by setup.    |
| **`SKILL.md`**          | Thin entrypoint (BMAD pattern): tells the agent to run `render_skill.py` once, then follow the printed workflow path. Must not duplicate engine logic. |
| **`/analyze-issue`**    | Skill: analyze input material and produce `00-issue-analysis.md` and `01-generated-issue.md` from `GITLAB_ISSUE_TEMPLATE.md`.                          |
| **`/index-repository`** | Skill: build or refresh a **DEEP** structural index and dependency graph for the current Git repository.                                               |
| **`/analyze-mr`**       | Skill: deterministic MR change analysis, bounded impact graph, runtime/QA scope, and reports (`01`–`04` markdown + JSON).                              |
| **`/update-issue`**     | Skill: local preview `05-issue-update.md` after MR analysis; GitLab apply only when the user explicitly confirms.                                      |

---

## BMAD-style workflow machinery

| Term                             | Meaning                                                                                                                                                                                                                                               |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **BMAD Method**                  | Reference project in `examples/BMAD-METHOD/`: thin `SKILL.md` → `render_skill` → immutable workflow snapshot → step files. MR Impact copies this shape, not BMAD product features.                                                                    |
| **`render_skill.py`**            | Script under `_mr-impact/scripts/` (installed from `skills/mr-impact-method/scripts/`). Merges `customize.toml`, renders Jinja in `workflow.md` and steps, writes a snapshot under `_mr-impact/render/`, prints `read and follow <path>/workflow.md`. |
| **Rendered workflow / snapshot** | Immutable copy of `workflow.md` and `step-*.md` for one run, under `_mr-impact/render/<skill>/…`. The agent must follow this path, not edit sources in `skills/` mid-run.                                                                             |
| **`workflow.md`**                | Top-level orchestration for a skill: conventions, activation, pointer to the first step file.                                                                                                                                                         |
| **Step file**                    | `step-01-*.md`, `step-02-*.md`, … Self-contained instructions; loaded one at a time in order.                                                                                                                                                         |
| **`customize.toml`**             | Per-skill overrides (`[workflow]`: activation steps, `persistent_facts`, `on_complete`). Merged by `render_skill`. User overrides may live in `_mr-impact/custom/<skill>.toml`.                                                                       |
| **`bmod.toml`**                  | Module or skill manifest (BMAD convention). Lists which skills belong to the method module; not copied to `.github/skills/`.                                                                                                                          |
| **`{project-root}`**             | Repository root where `_mr-impact/` and `.repository-analysis/` live.                                                                                                                                                                                 |
| **`{skill-root}`**               | Directory of the skill package (synced copy under `.github/skills/<name>/` or source under `skills/<name>/`).                                                                                                                                         |

---

## Runtime installation (`_mr-impact`)

| Term                    | Meaning                                                                                                                                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`_mr-impact/`**       | Project-local runtime created by **setup**: `config.toml`, copy of hub scripts, `custom/`, and generated `render/` snapshots.                                                                                     |
| **Setup (`setup.py`)**  | `skills/mr-impact-method/scripts/setup.py`: writes config, copies scripts to `_mr-impact/scripts/`, syncs the four skills to `.github/skills/`, seeds optional boundary catalog. Not invoked via a slash command. |
| **`config.toml`**       | Central config under `_mr-impact/` (from `assets/config.template.toml`): paths to engine, run dir, index root, catalog file.                                                                                      |
| **`run_engine.py`**     | Wrapper that runs `uv run --project <engine> python -m mr_impact …` with forwarded CLI arguments. Used in workflow step files.                                                                                    |
| **`resolve_config.py`** | Resolves merged TOML config layers to JSON (BMAD-derived).                                                                                                                                                        |

---

## Shared engine (`skills/_engine`)

| Term                    | Meaning                                                                                                                                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Shared engine**       | Single implementation used by all four skills: indexing, graph, adapters, diff, Issue/MR analysis, reports. No duplicated business logic in skill Markdown.                                    |
| **`mr_impact`**         | Python package name under `skills/_engine/src/mr_impact/`.                                                                                                                                     |
| **`mr-impact` CLI**     | Console entry point (`python -m mr_impact` or `mr-impact`) exposing subcommands: `analyze-issue`, `index-repository`, `analyze-mr`, `update-issue`, and supporting commands.                   |
| **Adapter**             | Pluggable extractor for a file type or operational format (Python `ast`, JIL, SQL, C# structure, generic paths, etc.). Outputs symbols, nodes, and edges with **evidence** and **confidence**. |
| **Reader (iFlow)**      | Optional parsers in `mr_impact/readers/` (from `examples/iFlow`): `python_ast` (stdlib) and `treesitter` (optional grammars). Feeds adapters when wired.                                       |
| **Deterministic layer** | Git, diff, parsing, graph traversal, artifact validation — must not be replaced by LLM guessing.                                                                                               |
| **AI layer**            | Issue interpretation, ambiguity, human-readable reports, template filling — governed by `GITLAB_ISSUE_TEMPLATE.md` and evidence rules.                                                         |

---

## Artifacts and storage

| Term | Meaning |
| --- | --- |
| **Ephemeral run directory** | `.repository-analysis/run/` — per-skill outputs (Issue/MR/update files). Gitignored; cleared before/after runs unless the user keeps artifacts. |
| **Persistent index** | `.repository-analysis/index/` and `.repository-analysis/graph/` — reused across MR runs; not deleted with run cleanup. |
| **`00-issue-analysis.md`** | Analyze Issue: analysis, gaps, assumptions vs requirements, DoR signals. |
| **`01-generated-issue.md`** | Analyze Issue: GitLab-ready Issue body matching current template section order. |
| **`01-mr-analysis.md` … `04-test-plan.md`** | Analyze MR human reports (summary, change context, impact, QA plan). |
| **`05-issue-update.md`** | Update Issue: preview of proposed Issue changes after MR analysis. |
| **Machine-readable JSON** | e.g. `mr-context.json`, `changed-symbols.json`, `impact-graph.json`, `runtime-impact.json`, `test-impact.json` — produced by the engine for tooling and skill presentation. |
| **`GITLAB_ISSUE_TEMPLATE.md`** | Authoritative Issue structure for `/analyze-issue`; canonical copy in `.github/skills/analyze-issue/`. Mirror in `docs/` for readability. |

---

## Indexing and impact

| Term | Meaning |
| --- | --- |
| **DEEP indexing** | Full structural index of the **current** repository: files, symbols, imports/calls where detectable, operational links (JIL, scripts, config). Default for `/index-repository` in V1. |
| **BOUNDARY indexing** | Lightweight cross-repo entity extraction (tables, jobs, APIs) for organization scale. Full auto org-wide pipeline is post-V1; V1 uses optional **boundary catalog** file only. |
| **Dependency graph** | Persisted edges (`IMPORTS`, `CALLS`, `CONFIGURES`, job/script links, etc.) with bounds and confidence. |
| **Boundary catalog** | Optional `.repository-analysis/catalog/boundary-catalog.json` mapping entities (e.g. `table://…`, `job://…`) to candidate repositories. Read-only hints in MR analysis in V1. |
| **Runtime / QA target** | An executable thing QA should run or verify (AutoSys job, batch, script, process) derived from the graph, not only a list of changed files. |
| **Impact classification** | e.g. `DIRECTLY_AFFECTED`, `TRANSITIVELY_AFFECTED`, `POTENTIALLY_AFFECTED`, `UNRESOLVED` for operational entities. |
| **Evidence** | Pointer to source (file, line, detector name) supporting a graph or report claim. |
| **Confidence** | How strongly a relationship is known (exact parse vs heuristic vs unresolved). |
| **Anchor (graph seed)** | A **named** entity from Issue or MR context (job id, symbol, script path) used as the **only** starting point for graph traversal. Not a module-wide or directory-wide filter. |
| **Anchored traversal** | Bounded walk along stored edges from anchors to parents/dependencies; see [issue-anchored-graph-traversal.md](issue-anchored-graph-traversal.md). |

---

## GitLab

| Term | Meaning |
| --- | --- |
| **GitLab MCP** | Model Context Protocol tools in Copilot for fetching Issues/MRs. Preferred for reads when available. |
| **`GITLAB_TOKEN` / `GITLAB_HOST`** | Environment variables for REST API access when MCP is not used or for engine automation. |
| **Preview-only update** | Default for `/update-issue`: generate `05-issue-update.md` locally without mutating the remote Issue. |
| **Apply (opt-in)** | Remote Issue update only after user confirmation and a successful local preview. |

---

## Repository layout (quick map)

| Path | Role |
| --- | --- |
| `skills/<skill-name>/` | Skill source (workflow, steps, template for analyze-issue). |
| `skills/mr-impact-method/` | Module scripts and `bmod.toml`; not a slash command. |
| `skills/_engine/` | Python engine package. |
| `.github/skills/` | Copilot-facing copies (four folders only). |
| `_mr-impact/` | Installed runtime after setup. |
| `.repository-analysis/` | Index, graph, catalog, and ephemeral `run/`. |
| `examples/BMAD-METHOD`, `examples/iFlow` | Reference implementations; not shipped as product code. |

---

## Related documents

- [docs/README.md](../README.md) — Copilot usage examples  
- [V1_SCOPE.md](V1_SCOPE.md) — MVP boundaries  
- [gitlab-integration.md](gitlab-integration.md) — GitLab token and MCP  
- [skills/README.md](../../skills/README.md) — Skill catalog  
