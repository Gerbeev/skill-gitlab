# Documentation

| Document | Purpose |
| --- | --- |
| [GITLAB_ISSUE_TEMPLATE.md](GITLAB_ISSUE_TEMPLATE.md) | Mirror of the Issue template (canonical: `.github/skills/analyze-issue/GITLAB_ISSUE_TEMPLATE.md`) |
| [reference/TASK_STATEMENT.md](reference/TASK_STATEMENT.md) | Full product specification (four skills, shared engine) |
| [reference/V1_SCOPE.md](reference/V1_SCOPE.md) | **MVP delivery boundary** |
| [reference/MVP_TASK_IMPROVEMENTS.md](reference/MVP_TASK_IMPROVEMENTS.md) | Design rationale and `examples/` patterns |
| [reference/gitlab-integration.md](reference/gitlab-integration.md) | GitLab token + MCP (read / opt-in write) |
| [reference/boundary-catalog.example.json](reference/boundary-catalog.example.json) | Optional cross-repo boundary catalog seed |

Reference examples (not shipped as product code):

- `examples/BMAD-METHOD` — thin Copilot skill → CLI pattern
- `examples/iFlow` — Python / tree-sitter readers and estate indexing

---

## Copilot: project skills

**Four Copilot skills only** — BMAD-style packages under `skills/`, synced to `.github/skills/`:

```text
skills/analyze-issue/       # workflow.md + step-*.md + GITLAB_ISSUE_TEMPLATE.md
skills/index-repository/
skills/analyze-mr/          # step pattern from examples/BMAD-METHOD/bmad-code-review
skills/update-issue/
skills/mr-impact-method/    # module + shared scripts (not a slash command)
skills/_engine/             # shared mr_impact Python package
_mr-impact/                 # runtime after setup (render_skill, config)
.github/skills/             # exactly four folders, synced by setup
```

**Setup** (repo root, not a skill):

```bash
uv run --no-cache skills/mr-impact-method/scripts/setup.py --project-root .
```

Each slash command: `render_skill.py` → follow rendered `workflow.md` (BMAD `bmad-build` / `bmad-code-review` pattern).

Copilot: `/analyze-issue`, `/index-repository`, `/analyze-mr`, `/update-issue`.

### Ephemeral run output

Each skill writes **per-run artifacts** to:

```text
.repository-analysis/run/
```

This directory is **gitignored**. Unless the user asks to keep files:

1. **Before** a new skill run — delete `.repository-analysis/run/` (or let the agent do it).
2. **After** presenting results — delete `.repository-analysis/run/` again.

The **persistent index** stays under `.repository-analysis/index/` and `.repository-analysis/graph/` and is not deleted between runs.

### GitLab (optional)

Set `GITLAB_TOKEN` (and `GITLAB_HOST` if not gitlab.com). When GitLab MCP is enabled in Copilot, prefer MCP to fetch Issues/MRs. Details: [reference/gitlab-integration.md](reference/gitlab-integration.md).

---

## Example 1 — Analyze Issue (local files only)

**Prepare input** in the repo root or a folder:

```text
requirements/payment-recon/
├── notes.md
├── requirements.md
└── qa-notes.md
```

**Copilot prompt:**

```text
/analyze-issue

Use input folder ./requirements/payment-recon/
Use the template in the analyze-issue skill directory.
Write outputs to the ephemeral run folder and show me both files.
Clean up .repository-analysis/run/ after I confirm.
```

**Expected output** (under `.repository-analysis/run/` until cleaned):

| File | What you get |
| --- | --- |
| `00-issue-analysis.md` | Evidence-based analysis: scope, gaps, ambiguities, assumptions vs requirements, DoR notes from the template |
| `01-generated-issue.md` | GitLab-ready Issue body matching **current** `GITLAB_ISSUE_TEMPLATE.md` section order; no invented ACs |

**Snippet shape** (`01-generated-issue.md`):

```markdown
## Problem & Outcome
**Problem / current state**
...

## Acceptance Criteria
- [ ] AC1: Given ... When ... Then ...
```

---

## Example 2 — Analyze Issue (GitLab Issue + MCP)

**Copilot prompt:**

```text
/analyze-issue

Fetch GitLab issue my-group/payment-service#1427 via GitLab MCP.
Save fetched text under .repository-analysis/run/gitlab-input/
Also read ./requirements/issue-1427/ if present.
Generate 00-issue-analysis.md and 01-generated-issue.md in the run folder.
```

**Expected output:** same two files; `00-issue-analysis.md` should cite which material came from GitLab vs local files and flag missing template sections.

---

## Example 3 — Index repository

**Copilot prompt:**

```text
/index-repository

Deep-index the current repository. Refresh only what changed since last index.
```

**Expected output (persistent, not in run/):**

```text
.repository-analysis/
├── index/
│   ├── repository-index.sqlite
│   ├── repository-index.json
│   └── index-manifest.json
└── graph/
    ├── dependency-graph.json
    └── graph-manifest.json
```

**V1 adapter priority:** C# → Oracle SQL/PL/SQL → JIL → then Scala, Java, others.

---

## Example 4 — Analyze MR

**Prerequisite:** index exists (Example 3).

**Copilot prompt:**

```text
/analyze-mr

Analyze origin/main..HEAD
Use the existing repository index.
Issue context: .repository-analysis/run/01-generated-issue.md if still present, else skip.
Focus on runtime jobs and QA execution scope.
```

**Expected output** (ephemeral `run/`):

| File | What you get |
| --- | --- |
| `01-mr-analysis.md` | Executive summary: what changed, risk areas |
| `02-change-context.md` | Files, symbols, neutral Issue mapping (no pass/fail) |
| `03-impact-analysis.md` | Bounded graph impact + AutoSys/JIL/script targets when indexed |
| `04-test-plan.md` | Concrete “run job X / verify Y” items with reasons |
| `runtime-impact.json` | Machine-readable QA targets with paths and confidence |

**Snippet shape** (`04-test-plan.md`):

```markdown
### Run AutoSys job: PAYMENT_RECON_EOD
- **Why:** changed method invoked from scripts/payment_recon.py referenced in JIL
- **Verify:** successful completion; downstream settlement trigger
- **Confidence:** high (evidence: jobs/payment_recon.jil → script path)
```

Optional: copy [boundary-catalog.example.json](reference/boundary-catalog.example.json) to `.repository-analysis/catalog/boundary-catalog.json` for cross-repo **hints** in `03-impact-analysis.md`.

---

## Example 5 — Update Issue (preview only)

**Copilot prompt:**

```text
/update-issue

Use MR artifacts in .repository-analysis/run/
Generate 05-issue-update.md preview only. Do not write to GitLab.
```

**Expected output:**

| File | What you get |
| --- | --- |
| `05-issue-update.md` | Proposed Issue addition/change: implementation summary, validation evidence, follow-ups; factual diff vs current Issue |

---

## Example 6 — Full workflow

```text
1. /analyze-issue  → input ./requirements/my-feature/
2. /index-repository
3. /analyze-mr       → origin/main..HEAD
4. /update-issue     → preview only

After review, delete .repository-analysis/run/
```

**Optional GitLab apply (step 4):**

```text
/update-issue

Show 05-issue-update.md. If I reply "apply", update GitLab issue my-group/payment-service#1427
using GitLab MCP or GITLAB_TOKEN.
```

---

## Example 7 — Analyze MR from GitLab

```text
/analyze-mr

Load MR !58 from GitLab (MCP or token) for project my-group/payment-service.
Map to local git revision and reuse index.
```

**Expected output:** same MR artifact set as Example 4; `mr-context.json` should record MR id and revision range used.
