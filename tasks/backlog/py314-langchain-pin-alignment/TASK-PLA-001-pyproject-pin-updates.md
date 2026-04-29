---
id: TASK-PLA-001
title: Add `<2` caps to runtime LangChain deps and explicit floors+caps to `[providers]`
status: backlog
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
parent_feature: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
complexity: 2
tags: [pyproject, pinning, langchain-1x, FA04-followup, ddd-southwest-demo]
estimated_effort: "15-30 minutes (mechanical 9-line diff + fresh-3.14-venv pytest re-run)"
dependencies: []
parallel_safe: true  # touches only pyproject.toml + uv.lock; no overlap with PLA-002 (new ADR file) or PLA-003 (README)
conductor_workspace: py314-langchain-pin-alignment-wave1-1
related_tasks:
  - TASK-REV-57BD  # parent diagnostic review (this task is its R1+R2)
  - TASK-PLA-002   # sibling — files ADR-ARCH-020 documenting *this* diff's rationale
  - TASK-PLA-003   # sibling — adds README pinning-policy pointer
related_external_reviews:
  - ".claude/reviews/TASK-REV-57BD-report.md"  # parent review §1 (empirical evidence) + §4 (this task's exact diff) + §1.3 (verified versions table)
  - "jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md"  # rev2 — the cross-repo recipe being applied here
  - "guardkit/docs/guides/portfolio-python-pinning.md"  # rationale for keeping `requires-python` upper bound open
  - "guardkit/.claude/reviews/TASK-REV-FA04-report.md"  # the upstream incident that motivated all of this
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Add `<2` caps to runtime LangChain deps and explicit floors+caps to `[providers]`

## Context

`TASK-REV-57BD`'s diagnostic empirical run on Python 3.14.2 (2026-04-29)
showed that study-tutor's `pyproject.toml` is **80% aligned** with the
ADR-ARCH-010-rev2 portfolio recipe: `requires-python = ">=3.11"` is correct,
the runtime LangChain deps are coherent 1.x, and a fresh-venv install +
`pytest` produces 23/23 passing in 6.84s with **zero langchain-runtime
failures**. The remaining 20% gap — and the only thing this task touches — is
**forward protection**:

- The two runtime LangChain deps (`langchain`, `langchain-core`) lack `<2`
  caps.
- All five `[project.optional-dependencies].providers` entries are
  **completely unpinned** — no floor, no cap.

Today the resolver picks the same coherent 1.x set Jarvis verified on 3.14
(see review §1.3); the diff this task applies locks those resolved versions
in as floors and adds same-major caps to catch the next coordinated
breaking-change wave (the FA04 mechanism: `langchain-core>=0.3` open-floor
let the resolver pick a 1.x core paired with a 0.x agent, producing runtime
`ModuleNotFoundError` from a deleted compat helper).

study-tutor is **DDD South West demo-critical** (autobuild builds
`jarvis / study-tutor / forge` for the demo). High priority — but the diff
is small, mechanical, and behaviour-preserving. Today's resolved versions
become tomorrow's floors; nothing else changes at runtime.

Verbatim from `.claude/reviews/TASK-REV-57BD-report.md` §4 ("Recommended pin
diff"):

> The minimal, behaviour-preserving forward-protection change. Floors match
> today's resolved versions; caps match the FA04 recipe.

## Current state (read directly from `pyproject.toml` — pre-task snapshot)

Lines 11–32 of `pyproject.toml`:

```toml
dependencies = [
    "pydantic>=2.0,<3.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "langchain>=1.2.11",          # ← needs `,<2` cap
    "langchain-core>=1.2.18",     # ← needs `,<2` cap
    "python-dotenv>=1.0",
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.scripts]
study-tutor = "study_tutor.cli.main:cli"

[project.optional-dependencies]
providers = [
    "langchain-openai",            # ← unpinned floor — RISK
    "langchain-anthropic",         # ← unpinned floor — RISK
    "langchain-google-genai",      # ← unpinned floor — RISK
    "langchain-aws",               # ← unpinned floor — RISK
    "langchain-ollama",            # ← unpinned floor — RISK
]
```

**Observation**: study-tutor's runtime pins are coherent 1.x but the
providers are completely unpinned — exactly the structural shape that
ADR-ARCH-010-rev2 §"Revised decision" closed for Jarvis. Empirically the
resolver picks coherent versions today (review §1.3); this task locks that
in.

## Goal

Apply the exact diff from `.claude/reviews/TASK-REV-57BD-report.md` §4 to
`pyproject.toml`, then re-verify the empirical baseline still passes
(`uv pip install -e ".[dev,providers]"` clean + `pytest` 23/23 green) on
Python 3.14.

**No GuardKit changes; no Jarvis changes; no other portfolio-repo changes —
fixes live in this repo.**

## Source artefacts

- This repo: `pyproject.toml`, `uv.lock`, `tests/`
- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §4 (the diff
  to apply, with rationale per pin); §1.3 (the verified-versions table the
  floors come from); §1.2 (the pytest baseline this task must preserve)
- Cross-repo precedent (read-only): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
  rev2 §"Revised decision" — the recipe; floors for shared providers
  (`langchain-anthropic`, `langchain-openai`, `langchain-google-genai`)
  match
- Cross-repo policy (read-only): `guardkit/docs/guides/portfolio-python-pinning.md`
  — confirms why `requires-python = ">=3.11"` (no upper bound) is the
  correct stance and is **not** changed by this task

## Pin diff to apply

Verbatim from `.claude/reviews/TASK-REV-57BD-report.md` §4:

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -8,8 +8,15 @@
 requires-python = ">=3.11"
 license = {text = "MIT"}
 dependencies = [
     "pydantic>=2.0,<3.0",
     "pyyaml>=6.0",
     "click>=8.0",
-    "langchain>=1.2.11",
-    "langchain-core>=1.2.18",
+    "langchain>=1.2.11,<2",
+    "langchain-core>=1.2.18,<2",
     "python-dotenv>=1.0",
     "mcp>=1.0",
     "httpx>=0.27",
@@ -23,11 +25,15 @@

 [project.optional-dependencies]
 providers = [
-    "langchain-openai",
-    "langchain-anthropic",
-    "langchain-google-genai",
-    "langchain-aws",
-    "langchain-ollama",
+    "langchain-openai>=1.2,<2",
+    "langchain-anthropic>=1.4,<2",
+    "langchain-google-genai>=4.2,<5",
+    "langchain-aws>=1.4,<2",
+    "langchain-ollama>=1.1,<2",
 ]
 dev = [
```

Per-pin rationale (also in review §4):

| Pin change | Why |
|---|---|
| `langchain` add `<2` | Forward protection. Upstream did the 0.x→1.x major break; the next one is `<2`'s job to catch. |
| `langchain-core` add `<2` | Same. Coherent-major constraint matching ADR-ARCH-010-rev2. |
| `langchain-openai>=1.2,<2` | Floor matches resolved version today (1.2.1) and Jarvis-verified set. |
| `langchain-anthropic>=1.4,<2` | Floor = 1.4 (today resolves 1.4.2; Jarvis 1.4.1 — both inside `>=1.4`). |
| `langchain-google-genai>=4.2,<5` | Floor matches resolved (4.2.2) and Jarvis (4.2.2). Cap is `<5` because this package's major is decoupled from the langchain-core 1.x cycle. |
| `langchain-aws>=1.4,<2` | Floor = today's resolved 1.4.5; same `<2` cap. *(study-tutor only — not in Jarvis's set.)* |
| `langchain-ollama>=1.1,<2` | Floor = today's resolved 1.1.0; same `<2` cap. *(study-tutor only — not in Jarvis's set.)* |

## What this task deliberately does NOT change

- `requires-python = ">=3.11"` — already correct per portfolio guide;
  closed Python upper bounds decay silently into trapdoors (FA04 mechanism).
- `pydantic>=2.0,<3.0` — already correctly capped.
- `mcp>=1.0` — Anthropic MCP SDK; not part of the LangChain ecosystem; not
  subject to the same risk pattern.
- `httpx>=0.27`, `click>=8.0`, `pyyaml>=6.0`, `python-dotenv>=1.0` — stable
  libraries with predictable major-version cadence; capping them buys nothing.
- **No new dependencies** — `deepagents`, `langgraph`, etc. are out of scope.
  The deepagents ADR/code drift discovered in review §3 + §6 is tracked in
  the separate [TASK-IMP-B7E0](../TASK-IMP-B7E0-deepagents-adr-codebase-drift.md)
  task, which depends on this one landing first.

## Acceptance criteria

- [ ] `pyproject.toml` updated with the exact diff above. No other lines
      changed (whitespace and comments preserved).
- [ ] `uv lock` (or `uv sync`) runs cleanly — `uv.lock` regenerated
      coherently. The lockfile diff should show no version regressions vs
      the empirical baseline (review §1.3 table); patch-level forward
      movement is fine.
- [ ] Fresh Python 3.14 venv install succeeds:
      ```bash
      rm -rf .venv && uv venv --python 3.14 .venv
      uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
      ```
      → exit 0, no resolver errors.
- [ ] `.venv/bin/python -c "import study_tutor"` returns 0.
- [ ] `.venv/bin/python -m pytest --tb=short -q` passes (target: 23/23 —
      same as the review baseline; if test count changed organically,
      verify zero `langchain`-runtime failures introduced by the pin
      tightening).
- [ ] Resolved versions for the seven `langchain-*` packages match (or
      are patch-level newer than) review §1.3's table; documented in the
      commit message or in a note appended to ADR-ARCH-020 if drift is
      observed.
- [ ] No changes to any file outside `pyproject.toml` and `uv.lock`.
- [ ] No GuardKit, Jarvis, forge, agentic-dataset-factory, or specialist-agent
      changes.

## Out of scope

- Drafting `ADR-ARCH-020` to record the pin recipe — covered by **TASK-PLA-002**.
- Adding the README pinning-policy pointer — covered by **TASK-PLA-003**.
- Resolving the `deepagents` ADR/code drift (review §3 + §6) — covered by
  **TASK-IMP-B7E0**, which depends on this task landing first.
- Adding `deepagents` or `langgraph` direct deps — neither is imported in
  the current codebase (review §2 + §3); adding pins for things the code
  doesn't use creates maintenance debt without protection benefit.
- Adding pin-tracking guard tests in the style of Jarvis's
  `tests/test_phase2_dependencies.py` — review §10 R5 placeholder; not
  scoped to FEAT-7BDP.
- Other portfolio repos.

## Suggested workflow

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
git checkout -b feat/py314-langchain-pin-alignment-pyproject

# Apply the diff (Edit tool or manual). Then verify:
rm -rf .venv
uv venv --python 3.14 .venv
uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
.venv/bin/python -c "import study_tutor; print('OK')"
.venv/bin/python -m pytest --tb=short -q

# Confirm resolved versions (should match or patch-newer than review §1.3)
uv pip list --python .venv/bin/python | grep -iE "(langchain|langgraph|pydantic)" | sort

# Stage and commit
git add pyproject.toml uv.lock
git commit -m "fix(deps): pin LangChain ecosystem with <2 caps and provider floors

Forward-protection change matching Jarvis ADR-ARCH-010 rev2's recipe.
Locks today's resolver-picked coherent 1.x set as floors; adds same-major
caps to catch the FA04-class breakage on the next coordinated bump.

Verified on Python 3.14.2: 23/23 pytest passing, zero langchain-runtime
failures. See .claude/reviews/TASK-REV-57BD-report.md §4 for the diff
rationale and §1.3 for the verified-versions table."
```

If running this task in isolation, complexity 2 + direct mode means no
QUICK_OPTIONAL or FULL_REQUIRED architectural review is triggered; the
fresh-venv pytest re-run is the quality gate.

## References

- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §4 (the diff +
  per-pin rationale), §1.2 (pytest baseline), §1.3 (verified versions)
- Cross-repo precedent: `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
  Revision 2 §"Revised decision"
- Portfolio guide: `guardkit/docs/guides/portfolio-python-pinning.md`
- Sibling tasks: TASK-PLA-002 (ADR-ARCH-020), TASK-PLA-003 (README pointer)
- Downstream task: TASK-IMP-B7E0 (deepagents drift) — depends on this
  landing first
