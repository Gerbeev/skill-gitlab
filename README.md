# MR Impact Copilot Skills

Four VS Code **GitHub Copilot** project skills for Issue analysis, repository indexing, Merge Request impact, and Issue updates—one shared engine, BMAD-style workflows.

| Slash command | Purpose |
| --- | --- |
| `/analyze-issue` | Analysis report + GitLab Issue body from template |
| `/index-repository` | Deep structural index and dependency graph |
| `/analyze-mr` | MR change impact, runtime/QA scope |
| `/update-issue` | Issue update preview (GitLab apply opt-in) |

**More detail:** [docs/README.md](docs/README.md) (extended prompts and outputs) · [GLOSSARY](docs/reference/GLOSSARY.md) · [TASK_STATEMENT](docs/reference/TASK_STATEMENT.md) · [V1 scope](docs/reference/V1_SCOPE.md)

---

## Prerequisites

- **VS Code** with **GitHub Copilot** and **Agent** mode (project skills / slash commands).
- **Git** repository opened as the workspace root (the project you analyze).
- **[uv](https://docs.astral.sh/uv/)** installed (`uv` on PATH) for setup and the Python engine.
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
│   └── skills/                    ← Copilot project skills (4 folders)
│       ├── analyze-issue/
│       ├── index-repository/
│       ├── analyze-mr/
│       └── update-issue/
├── _mr-impact/                    ← runtime (config + render_skill; gitignore render/)
└── skills/                        ← source of truth (edit here, then re-run setup)
```

**Do not** move skills to `.cursor/skills` or other paths unless your Copilot version documents a different project-skill location—this project standardizes on **`.github/skills/`**.

### One-time setup (required)

From the **project root** (where `.git` lives):

```bash
uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root .
```

Setup will:

- Create **`_mr-impact/config.toml`** and install scripts under **`_mr-impact/scripts/`** (`render_skill.py`, `run_engine.py`, …).
- **Sync** `skills/analyze-issue`, `index-repository`, `analyze-mr`, `update-issue` → **`.github/skills/`** (only these four).
- Optionally seed **`.repository-analysis/catalog/boundary-catalog.json`** from the example file.

Check status:

```bash
uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root . --status
```

Re-run setup after you change files under `skills/` so `.github/skills/` stays in sync.

### Verify Copilot sees the skills

1. Reload VS Code window if skills were just added.
2. Open Copilot Chat → type `/` and confirm: `analyze-issue`, `index-repository`, `analyze-mr`, `update-issue`.

---

## How a skill run works (BMAD pattern)

Each slash command:

1. Agent runs **`_mr-impact/scripts/render_skill.py`** for that skill.
2. Agent follows the printed **`workflow.md`** snapshot (step files in order).
3. Steps call **`run_engine.py`** → `python -m mr_impact …` when the engine is installed under `skills/_engine/`.

If `render_skill` is missing, run **setup** again.

---

## Where outputs go

| Location | Purpose |
| --- | --- |
| `.repository-analysis/run/` | **Per-run** artifacts (Issue/MR/update). **Gitignored.** Delete before/after runs unless you want to keep them. |
| `.repository-analysis/index/`, `graph/` | **Persistent** index; reused for `/analyze-mr`. |
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

Optional: fetch Issue from GitLab via MCP or `GITLAB_TOKEN` into `run/gitlab-input/` (see [docs/README.md](docs/README.md#example-2--analyze-issue-gitlab-issue--mcp)).

---

### Stage 2 — Index repository (`/index-repository`)

**When:** Before MR analysis (or when you need graph-backed Issue dependency context).

**Copilot prompt:**

```text
/index-repository

Deep-index the current repository. Incremental refresh if index already exists.
```

**You get (persistent):** `repository-index.sqlite`, `dependency-graph.json`, manifests under `.repository-analysis/index/` and `graph/`.

Run once per repo (refresh after large changes or new commits).

---

### Stage 3 — Analyze Merge Request (`/analyze-mr`)

**When:** You have a branch or MR and an index from Stage 2.

**Copilot prompt:**

```text
/analyze-mr

Analyze origin/main..HEAD
Use the existing repository index.
Optional Issue context: 01-generated-issue.md in .repository-analysis/run/ if present.
Focus on runtime jobs and QA scope (AutoSys/JIL where indexed).
```

**You get (in `run/`):** `01-mr-analysis.md` … `04-test-plan.md`, plus JSON (`runtime-impact.json`, etc.).

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

**You get:** `05-issue-update.md` (and optional `issue-update.json`).

To apply remotely: confirm explicitly; use GitLab MCP or token ([gitlab-integration](docs/reference/gitlab-integration.md)).

---

### Full pipeline (copy-paste)

```text
1. /analyze-issue     → ./requirements/my-feature/
2. /index-repository
3. /analyze-mr        → origin/main..HEAD
4. /update-issue      → preview only

Then delete .repository-analysis/run/ if you do not need the files.
```

More examples (GitLab MR, boundary catalog): **[docs/README.md](docs/README.md)**.

---

## Engine note

The Python engine lives in **`skills/_engine/`** (`mr_impact` package). Skill workflows call it via **`_mr-impact/scripts/run_engine.py`**. Until the full engine is present in your checkout, steps that invoke `mr-impact` will fail—see [skills/_engine/README.md](skills/_engine/README.md).

Install engine deps when available:

```bash
uv sync --project skills/_engine
```

Optional tree-sitter grammars (iFlow list): `skills/_engine/src/mr_impact/readers/requirements.txt`.

---

## Troubleshooting

| Problem | Action |
| --- | --- |
| Slash commands missing | Run setup; confirm `.github/skills/` has four folders; reload VS Code. |
| `render_skill.py` not found | Run setup from project root. |
| Stale skill text in Copilot | Edit under `skills/`, re-run setup, reload window. |
| MR analysis empty / no jobs | Run `/index-repository` first; check JIL/scripts indexed. |
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
