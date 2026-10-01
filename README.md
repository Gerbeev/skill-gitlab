# MR Impact Copilot Skills

Six VS Code **GitHub Copilot** project skills for Issue workspace setup, Issue analysis, index/graph build, Merge Request impact, and Issue updates—one shared engine, BMAD-style workflows.

| Slash command | Purpose |
| --- | --- |
| `/initialize-repo` | Per-feature **issue folder**: templates + links (GitLab Issue/MR, branch) so downstream skills read one place |
| `/analyze-issue` | Analysis report + GitLab Issue body from template |
| `/create-index` | DEEP structural index → `.repository-analysis/index/` |
| `/create-graph` | Dependency graph JSON → `.repository-analysis/graph/` (after index) |
| `/analyze-mr` | MR change impact, runtime/QA scope |
| `/update-issue` | Issue update preview (GitLab apply opt-in) |

**More detail:** [docs/README.md](docs/README.md) · [Engine contract](docs/reference/engine-contract.md) (CLI + artifacts) · [GLOSSARY](docs/reference/GLOSSARY.md) · [TASK_STATEMENT](docs/reference/TASK_STATEMENT.md) · [V1 scope](docs/reference/V1_SCOPE.md) · [Development plan](docs/DEVELOPMENT_PLAN.md)

## Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Option A — Use this repository as your project](#option-a--use-this-repository-as-your-project)
  - [Option B — Add skills to another Git repository](#option-b--add-skills-to-another-git-repository)
  - [One-time setup (required)](#one-time-setup-required)
  - [Verify Copilot sees the skills](#verify-copilot-sees-the-skills)
- [How a skill run works (BMAD pattern)](#how-a-skill-run-works-bmad-pattern)
- [Where outputs go](#where-outputs-go)
- [Usage by stage (workflow)](#usage-by-stage-workflow)
  - [Stage 0 — Initialize issue workspace](#stage-0--initialize-issue-workspace-initialize-repo)
  - [Stage 1 — Analyze Issue](#stage-1--analyze-issue-analyze-issue)
  - [Stage 2a — Create index](#stage-2a--create-index-create-index)
  - [Stage 2b — Create graph](#stage-2b--create-graph-create-graph)
  - [Stage 3 — Analyze Merge Request](#stage-3--analyze-merge-request-analyze-mr)
  - [Stage 4 — Update Issue](#stage-4--update-issue-update-issue)
  - [Full pipeline](#full-pipeline)
- [Engine note](#engine-note)
- [Troubleshooting](#troubleshooting)
- [Repository map](#repository-map)

---

## Prerequisites

- **VS Code** with **GitHub Copilot** and **Agent** mode (project skills / slash commands).
- **Git** repository opened as the workspace root (the project you analyze).
- **Python 3.11+** (`python` or Windows `py -3.11`). **`uv` is not required** — see [python-setup](docs/reference/python-setup.md).
- One-time: `pip install -r skills/mr-impact-method/scripts/requirements.txt` (Jinja2 for `render_skill`).
- Optional: **`GITLAB_TOKEN`** / **GitLab MCP** for fetching Issues or MRs ([gitlab-integration](docs/reference/gitlab-integration.md)).

---

## Installation

You do **not** copy skills by hand into random folders. Use this repo’s layout and **setup** once per target project.

### Option A — Use this repository as your project

1. Clone or open `skill-gitlab` (or your fork) in VS Code.
2. From the **repository root**, run setup (see below).
3. Copilot reads skills from **`.github/skills/`** in that same root.

### Option B — Add skills to another Git repository

1. Copy or submodule the contents you need into the **target repo**:
   - `skills/` (all skill sources + `mr-impact-method/` + `_engine/`)
   - `docs/` (recommended, for templates and references)
2. Open the **target repo** as the workspace in VS Code.
3. Run setup from the **target repo root** (not from a subfolder).

After setup, Copilot only needs:

```text
<your-project-root>/
├── .github/
│   └── skills/                    ← Copilot project skills (6 folders)
│       ├── initialize-repo/
│       ├── analyze-issue/
│       ├── create-index/
│       ├── create-graph/
│       ├── analyze-mr/
│       └── update-issue/
├── _mr-impact/                    ← runtime after setup (gitignored; run setup.py)
└── skills/                        ← source of truth (edit here, then re-run setup)
```

**Do not** move skills to `.cursor/skills` or other paths unless your Copilot version documents a different project-skill location—this project standardizes on **`.github/skills/`**.

### One-time setup (required)

From the **project root** (where `.git` lives):

```bash
python -m pip install -r skills/mr-impact-method/scripts/requirements.txt
python skills/mr-impact-method/scripts/setup.py --project-root .
```

On Windows, if `python` is missing, use `py -3.11` instead of `python`.

Setup will:

- Create **`_mr-impact/config.toml`**, bundle **`_mr-impact/engine/`** (Python `mr_impact` package), and install scripts under **`_mr-impact/scripts/`**.
- **Sync** Copilot skills → **`.github/skills/`** (see `mr-impact-method/bmod.toml`). The set includes **`initialize-repo`** once that skill is added under `skills/`; until then, setup syncs the other five.
- Optionally seed **`.repository-analysis/catalog/boundary-catalog.json`** from the example file.

Check status:

```bash
python skills/mr-impact-method/scripts/setup.py --project-root . --status
```

Re-run setup after you change files under `skills/` so `.github/skills/` stays in sync.

### Verify Copilot sees the skills

1. Reload VS Code window if skills were just added.
2. Open Copilot Chat → type `/` and confirm: `initialize-repo`, `analyze-issue`, `create-index`, `create-graph`, `analyze-mr`, `update-issue`.

---

## How a skill run works (BMAD pattern)

Each slash command:

1. Agent runs **`_mr-impact/scripts/render_skill.py`** for that skill.
2. Agent follows the printed **`workflow.md`** snapshot (step files in order).
3. Steps call **`run_engine.py`** → `python -m mr_impact …` using the engine bundled under **`_mr-impact/engine/`** after setup (or `skills/_engine/` in development).

If `render_skill` is missing, run **setup** again.

**In Copilot Chat**, pass only **run parameters** (paths, revision, GitLab ids, opt-in flags). Workflow, templates, and engine calls are defined in the skill—do not restate them in the prompt.

---

## Where outputs go

| Location | Purpose |
| --- | --- |
| `.repository-analysis/run/` | **Per-run** artifacts (Issue/MR/update). **Gitignored.** Delete before/after runs unless you want to keep them. |
| `.repository-analysis/index/` | **Persistent** structural index (`/create-index`). |
| `.repository-analysis/graph/` | **Persistent** graph export (`/create-graph`). Downstream skills use whichever exists. |
| `.repository-analysis/catalog/` | Optional boundary catalog (cross-repo hints). |
| `issues/<slug>/` (recommended) | **Per-feature issue workspace** created by `/initialize-repo` — user-edited notes, requirements, GitLab links; other skills take `issue:` / `input:` from here |

Issue template (canonical): **`.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md`**

Per-feature workspace files (planned convention, filled by you after `/initialize-repo`): see [Stage 0](#stage-0--initialize-issue-workspace-initialize-repo).

---

## Usage by stage (workflow)

**Canonical order** (same as [skills/mr-impact-method/references/module.md](skills/mr-impact-method/references/module.md#full-change-pipeline-canonical-order)): initialize issue workspace → analyze Issue → index → graph (optional) → analyze MR → update Issue. Each step is also usable alone.

### Stage 0 — Initialize issue workspace (`/initialize-repo`)

**When:** You start a new feature or change and want one folder in the repo that holds everything the pipeline needs—links to GitLab Issue/MR, branch names, and empty templates for you to fill before running other skills.

**What it does (planned):** Create or refresh an **issue workspace** under a stable path (recommended: `issues/<slug>/`). Copy or generate starter files (notes, requirements, manifest with GitLab URLs and ids) so `/analyze-issue`, `/analyze-mr`, and `/update-issue` can read the same `issue:` / `input:` root instead of ad-hoc `requirements/` layouts. The skill source is not wired in `skills/` yet—only this README entry; full workflow steps will follow in a later change.

**Prompt (parameters only, illustrative):**

```text
/initialize-repo
slug: my-feature
gitlab issue: https://gitlab.example.com/group/project/-/issues/42
```

Optional: `path: ./issues/my-feature/` if you already chose the folder name.

**You get (illustrative layout):**

```text
issues/my-feature/
├── issue-workspace.md      # links: GitLab Issue/MR, default branch, revision hints
├── notes.md                # your context (template)
└── requirements.md         # what should be achieved (template)
```

Commit this folder if your team tracks requirements in Git; keep secrets and tokens out of it.

---

### Stage 1 — Analyze Issue (`/analyze-issue`)

**When:** The issue workspace exists (Stage 0) or you already have notes; you want analysis + a template-shaped GitLab description.

**Input:** Prefer the folder from `/initialize-repo`:

```text
issues/my-feature/
├── issue-workspace.md
├── notes.md
└── requirements.md
```

Legacy ad-hoc layout (`requirements/<name>/` with `notes.md` + `requirements.md`) still works until skills standardize on the issue workspace.

**Prompt (parameters only):**

```text
/analyze-issue
input: ./issues/my-feature/
```

Or, for an existing GitLab Issue: add `issue: <project>#<iid>` or point at fetched text under `run/gitlab-input/` ([gitlab-integration](docs/reference/gitlab-integration.md)).

**You get:**

| File | Content |
| --- | --- |
| `00-issue-analysis.md` | Gaps, assumptions, ambiguities, optional anchored dependency paths if index exists |
| `01-generated-issue.md` | Paste-ready Issue body |
| `issue-intent.json` | Structured gaps, anchors, and bounded graph paths |

---

### Stage 2a — Create index (`/create-index`)

**When:** Before MR/issue graph context or after significant repo changes.

**Prompt:**

```text
/create-index
```

**You get:** `repository-index.sqlite`, `repository-index.json`, `index-manifest.json` under `.repository-analysis/index/`.

### Stage 2b — Create graph (`/create-graph`)

**When:** After index exists and you want `dependency-graph.json` for traversal.

**Prompt:**

```text
/create-graph
```

**You get:** `dependency-graph.json`, `graph-manifest.json` under `.repository-analysis/graph/`. Requires Stage 2a first.

---

### Stage 3 — Analyze Merge Request (`/analyze-mr`)

**When:** You have a branch or MR; index and/or graph from Stage 2 are used when present.

**Prompt:**

```text
/analyze-mr
revision: origin/main..HEAD
issue context (optional): .repository-analysis/run/01-generated-issue.md
```

**You get (in `run/`):** engine-produced artifacts per [engine-contract](docs/reference/engine-contract.md):

| Markdown | JSON |
| --- | --- |
| `01-mr-analysis.md` … `04-test-plan.md` | `mr-context.json`, `changed-symbols.json`, `impact-graph.json`, `runtime-impact.json`, `test-impact.json` |

Requires an existing index (`/create-index` first). Revision format: `base..head` (e.g. `origin/main..HEAD`).

Graph rules (in skill/docs, not in the prompt): bounded **nearest** paths from **diff-accurate** seeds to primary AutoSys job/box — not “all jobs in module” ([issue-anchored-graph-traversal](docs/reference/issue-anchored-graph-traversal.md), [nearest-runtime-impact-paths](docs/reference/nearest-runtime-impact-paths.md)).

---

### Stage 4 — Update Issue (`/update-issue`)

**When:** After Stage 3; you want a recorded implementation/validation update for GitLab.

**Prompt:**

```text
/update-issue
run: .repository-analysis/run/
apply: no
```

Say `apply: yes` (or confirm in chat) only when you want GitLab write; see [gitlab-integration](docs/reference/gitlab-integration.md).

**You get:** `05-issue-update.md` and `issue-update.json` (preview). Target content includes **QA / runtime (nearest paths)** for testers ([nearest-runtime-impact-paths](docs/reference/nearest-runtime-impact-paths.md)).

---

### Full pipeline

Run stages in order; each line is a separate chat message (or one message with the same parameter style):

```text
/initialize-repo
slug: my-feature

/analyze-issue
input: ./issues/my-feature/

/create-index

/create-graph

/analyze-mr
revision: origin/main..HEAD

/update-issue
run: .repository-analysis/run/
apply: no
```

GitLab and boundary catalog: **[gitlab-integration](docs/reference/gitlab-integration.md)** · **[boundary-catalog.example.json](docs/reference/boundary-catalog.example.json)** · doc index: **[docs/README.md](docs/README.md)**.

---

## Engine note

Source of truth: **`skills/_engine/`** (`mr_impact`). **Setup** copies it to **`_mr-impact/engine/`**; skills invoke **`_mr-impact/scripts/run_engine.py`**. Canonical commands and run files: [engine-contract](docs/reference/engine-contract.md).

Direct CLI (from repo root, after setup or with `PYTHONPATH`):

```bash
python _mr-impact/scripts/run_engine.py --project-root . -- create-index
python _mr-impact/scripts/run_engine.py --project-root . -- analyze-mr --revision HEAD~1..HEAD --run-dir .repository-analysis/run
```

Optional editable install for development:

```bash
python -m pip install -e skills/_engine
```

See [skills/_engine/README.md](skills/_engine/README.md).

Optional tree-sitter grammars: `skills/_engine/src/mr_impact/readers/requirements.txt`.  
**Without uv:** [docs/reference/python-setup.md](docs/reference/python-setup.md).

Before push (mirrors CI):

```bash
python tools/quality.py
```

---

## Troubleshooting

| Problem | Action |
| --- | --- |
| Slash commands missing | Run setup; confirm `.github/skills/` has the expected skill folders (six with `initialize-repo`); reload VS Code. |
| Issue folder missing / skills ask for `input:` | Run `/initialize-repo` first, then point `input:` or `issue:` at `issues/<slug>/`. |
| `render_skill.py` not found | Run setup from project root. |
| Stale skill text in Copilot | Edit under `skills/`, re-run setup, reload window. |
| MR analysis empty / no jobs | Run `/create-index` (and `/create-graph` if needed); check JIL/scripts indexed. |
| Token leaks | Never commit `GITLAB_TOKEN`; use env vars or MCP only. |

---

## Repository map

```text
skills/                 # Skill sources (edit here)
.github/skills/         # Copilot entry (generated by setup)
skills/mr-impact-method/# Setup + render_skill + run_engine
skills/_engine/         # Shared Python engine
docs/                   # Templates, glossary, integration guides
examples/BMAD-METHOD/   # BMAD reference (not product code)
```
