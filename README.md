# MR Impact Copilot Skills

Five VS Code **GitHub Copilot** project skills for Issue analysis, index/graph build, Merge Request impact, and Issue updates—one shared engine, BMAD-style workflows.

| Slash command | Purpose |
| --- | --- |
| `/analyze-issue` | Analysis report + GitLab Issue body from template |
| `/create_index` | DEEP structural index → `.repository-analysis/index/` |
| `/create_graph` | Dependency graph JSON → `.repository-analysis/graph/` (after index) |
| `/analyze-mr` | MR change impact, runtime/QA scope |
| `/update-issue` | Issue update preview (GitLab apply opt-in) |

**More detail:** [docs/README.md](docs/README.md) (extended prompts and outputs) · [Engine contract](docs/reference/engine-contract.md) (CLI + artifacts) · [GLOSSARY](docs/reference/GLOSSARY.md) · [TASK_STATEMENT](docs/reference/TASK_STATEMENT.md) · [V1 scope](docs/reference/V1_SCOPE.md) · [Development plan](docs/DEVELOPMENT_PLAN.md)

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
│   └── skills/                    ← Copilot project skills (5 folders)
│       ├── analyze-issue/
│       ├── create-index/
│       ├── create-graph/
│       ├── analyze-mr/
│       └── update-issue/
├── _mr-impact/                    ← runtime (config + render_skill; gitignore render/)
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
- **Sync** the five Copilot skills → **`.github/skills/`** (see `mr-impact-method/bmod.toml`).
- Optionally seed **`.repository-analysis/catalog/boundary-catalog.json`** from the example file.

Check status:

```bash
python skills/mr-impact-method/scripts/setup.py --project-root . --status
```

Re-run setup after you change files under `skills/` so `.github/skills/` stays in sync.

### Verify Copilot sees the skills

1. Reload VS Code window if skills were just added.
2. Open Copilot Chat → type `/` and confirm: `analyze-issue`, `create-index`, `create-graph`, `analyze-mr`, `update-issue`.

---

## How a skill run works (BMAD pattern)

Each slash command:

1. Agent runs **`_mr-impact/scripts/render_skill.py`** for that skill.
2. Agent follows the printed **`workflow.md`** snapshot (step files in order).
3. Steps call **`run_engine.py`** → `python -m mr_impact …` using the engine bundled under **`_mr-impact/engine/`** after setup (or `skills/_engine/` in development).

If `render_skill` is missing, run **setup** again.

---

## Where outputs go

| Location | Purpose |
| --- | --- |
| `.repository-analysis/run/` | **Per-run** artifacts (Issue/MR/update). **Gitignored.** Delete before/after runs unless you want to keep them. |
| `.repository-analysis/index/` | **Persistent** structural index (`/create_index`). |
| `.repository-analysis/graph/` | **Persistent** graph export (`/create_graph`). Downstream skills use whichever exists. |
| `.repository-analysis/catalog/` | Optional boundary catalog (cross-repo hints). |

Issue template (canonical): **`.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md`**

---

## Usage by stage (workflow)

Typical order for a full change. Each step is also usable alone.

### Stage 1 — Analyze Issue (`/analyze-issue`)

**When:** You have notes, requirements, or an existing Issue text; you want analysis + a template-shaped GitLab description.

**Prepare (optional):**

```text
requirements/my-feature/
├── notes.md
└── requirements.md
```

**Copilot prompt:**

```text
/analyze-issue

Use input folder ./requirements/my-feature/
Generate 00-issue-analysis.md and 01-generated-issue.md in .repository-analysis/run/
Use GITLAB_ISSUE_TEMPLATE.md from the analyze-issue skill.
Do not invent Acceptance Criteria without evidence.
Clean up .repository-analysis/run/ after I confirm.
```

**You get:**

| File | Content |
| --- | --- |
| `00-issue-analysis.md` | Gaps, assumptions, ambiguities, optional anchored dependency paths if index exists |
| `01-generated-issue.md` | Paste-ready Issue body |
| `issue-intent.json` | Structured gaps, anchors, and bounded graph paths |

Optional: fetch Issue from GitLab via MCP or `GITLAB_TOKEN` into `run/gitlab-input/` (see [docs/README.md](docs/README.md#example-2--analyze-issue-gitlab-issue--mcp)).

---

### Stage 2a — Create index (`/create_index`)

**When:** Before MR/issue graph context or after significant repo changes.

```text
/create_index

Deep-index the current repository into .repository-analysis/index/ only.
```

**You get:** `repository-index.sqlite`, `repository-index.json`, `index-manifest.json`.

### Stage 2b — Create graph (`/create_graph`)

**When:** After index exists and you want `dependency-graph.json` for traversal.

```text
/create_graph

Export graph from existing index SQLite into .repository-analysis/graph/.
```

**You get:** `dependency-graph.json`, `graph-manifest.json`. Requires Stage 2a first.

---

### Stage 3 — Analyze Merge Request (`/analyze-mr`)

**When:** You have a branch or MR; use index and/or graph from Stage 2 if present.

**Copilot prompt:**

```text
/analyze-mr

Analyze origin/main..HEAD
Use the existing repository index.
Optional Issue context: 01-generated-issue.md in .repository-analysis/run/ if present.
Focus on runtime jobs and QA scope (AutoSys/JIL where indexed).
```

**You get (in `run/`):** engine-produced artifacts per [engine-contract](docs/reference/engine-contract.md):

| Markdown | JSON |
| --- | --- |
| `01-mr-analysis.md` … `04-test-plan.md` | `mr-context.json`, `changed-symbols.json`, `impact-graph.json`, `runtime-impact.json`, `test-impact.json` |

Requires an existing index (`/create_index` first). Revision format: `base..head` (e.g. `origin/main..HEAD`).

Graph rules: bounded paths from **changed symbols**, not “all jobs in module” ([issue-anchored-graph-traversal](docs/reference/issue-anchored-graph-traversal.md)).

---

### Stage 4 — Update Issue (`/update-issue`)

**When:** After Stage 3; you want a recorded implementation/validation update for GitLab.

**Copilot prompt:**

```text
/update-issue

Use artifacts in .repository-analysis/run/
Generate 05-issue-update.md preview only. Do not write to GitLab unless I say "apply".
```

**You get:** `05-issue-update.md` and `issue-update.json` (engine preview; GitLab apply stays in the skill).

To apply remotely: confirm explicitly; use GitLab MCP or token ([gitlab-integration](docs/reference/gitlab-integration.md)).

---

### Full pipeline (copy-paste)

```text
1. /analyze-issue     → ./requirements/my-feature/
2. /create_index
3. /create_graph      → optional; recommended for MR graph traversal
4. /analyze-mr        → origin/main..HEAD
5. /update-issue      → preview only

Then delete .repository-analysis/run/ if you do not need the files.
```

More examples (GitLab MR, boundary catalog): **[docs/README.md](docs/README.md)**.

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

Validate skill layout (after setup):

```bash
python tools/validate_skills.py --strict
```

---

## Troubleshooting

| Problem | Action |
| --- | --- |
| Slash commands missing | Run setup; confirm `.github/skills/` has **five** folders; reload VS Code. |
| `render_skill.py` not found | Run setup from project root. |
| Stale skill text in Copilot | Edit under `skills/`, re-run setup, reload window. |
| MR analysis empty / no jobs | Run `/create_index` (and `/create_graph` if needed); check JIL/scripts indexed. |
| Token leaks | Never commit `GITLAB_TOKEN`; use env vars or MCP only. |

---

## Repository map

```text
skills/                 # Skill sources (edit here)
.github/skills/         # Copilot entry (generated by setup)
skills/mr-impact-method/# Setup + render_skill + run_engine
skills/_engine/         # Shared Python engine
docs/                   # Templates, glossary, integration guides
examples/               # BMAD + iFlow references (not product code)
```
