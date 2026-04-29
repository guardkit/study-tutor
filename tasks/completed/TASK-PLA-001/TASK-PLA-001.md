---
id: TASK-PLA-001
title: Add `<2` caps to runtime LangChain deps and explicit floors+caps to `[providers]`
status: completed
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
feature_id: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
priority: high
complexity: 2
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
completed: 2026-04-29T00:00:00Z
completed_location: tasks/completed/TASK-PLA-001/
organized_files: ["TASK-PLA-001.md"]
tags: [pyproject, pinning, langchain-1x, FA04-followup, ddd-southwest-demo]
dependencies: []
parallel_safe: true
conductor_workspace: py314-langchain-pin-alignment-wave1-1
test_results:
  status: passed
  passed: 23
  failed: 0
  total: 23
  coverage: null
  last_run: 2026-04-29T00:00:00Z
  python: "3.14.2"
  command: ".venv/bin/python -m pytest --tb=short -q"
---

# Add `<2` caps to runtime LangChain deps and explicit floors+caps to `[providers]`

## Context

Implementation subtask from **TASK-REV-57BD** (Python 3.14 + langchain-1.x portfolio alignment review).
See `.claude/reviews/TASK-REV-57BD-report.md` §4 for the review's pin-diff
recommendation and §1.3 for the empirical-evidence table that justifies each
floor.

This is **forward protection only** — today's resolver picks the same coherent
1.x set Jarvis verified on 3.14, and the test suite passes 23/23 on that set.
The diff doesn't change runtime behaviour; it locks in the verified versions
as the resolver's lower bound and adds same-major caps to catch the next
coordinated breaking-change wave (the FA04 mechanism).

## Goal

Apply the exact diff from the review report §4 to `pyproject.toml`, then
re-verify the empirical baseline still passes (`uv pip install -e
".[dev,providers]"` clean + `pytest` 23/23 green) on Python 3.14.

## Pin diff to apply

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

**Do not** change `requires-python = ">=3.11"`, `pydantic>=2.0,<3.0`,
`mcp>=1.0`, `httpx>=0.27`, `click>=8.0`, `pyyaml>=6.0`, or `python-dotenv>=1.0`.
See review §4 for rationale on each non-change.

**Do not** add `deepagents`, `langgraph`, or any other new dependencies in
this task. Those decisions are out of scope (review §3, §6) and any
addition should be a separate task.

## Acceptance criteria

- [ ] `pyproject.toml` updated with the exact diff above (no other lines
      changed; whitespace/comment-preserving).
- [ ] `uv lock` (or `uv sync`) runs cleanly — `uv.lock` regenerated coherently.
      The lockfile diff should show no version regressions vs the empirical
      baseline (review §1.3 table); patch-level forward movement is fine.
- [ ] Fresh 3.14 venv install succeeds:
      ```bash
      rm -rf .venv && uv venv --python 3.14 .venv
      uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
      ```
- [ ] `.venv/bin/python -c "import study_tutor"` returns 0.
- [ ] `.venv/bin/python -m pytest --tb=short -q` passes (target: 23/23 — same
      as the review baseline; if test count changed organically, verify no
      `langchain`-runtime failures introduced by the pin tightening).
- [ ] No changes to any file outside `pyproject.toml` and `uv.lock`.
- [ ] No GuardKit, Jarvis, or sibling-repo changes.

## Out of scope

- ADR drafting (TASK-PLA-002).
- README pinning policy reference (TASK-PLA-003).
- Resolving the deepagents ADR/code drift (review §6 follow-up — not part of
  this feature).

## Verification recipe

The same recipe used in the review:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
rm -rf .venv
uv venv --python 3.14 .venv
uv pip install --upgrade --python .venv/bin/python -e ".[dev,providers]"
.venv/bin/python -c "import study_tutor; print('OK')"
.venv/bin/python -m pytest --tb=short -q
uv pip list --python .venv/bin/python | grep -iE "(langchain|langgraph|pydantic)" | sort
```

Expected last-line output (or close to it — patch-level drift is acceptable):

```
langchain                 1.2.15
langchain-anthropic       1.4.2
langchain-aws             1.4.5
langchain-core            1.3.2
langchain-google-genai    4.2.2
langchain-ollama          1.1.0
langchain-openai          1.2.1
langgraph                 1.1.10
langgraph-checkpoint      4.0.3
langgraph-prebuilt        1.0.12
langgraph-sdk             0.3.13
pydantic                  2.13.3
pydantic-core             2.46.3
pydantic-settings         2.14.0
```

## References

- Review report: `.claude/reviews/TASK-REV-57BD-report.md` §4 (pin diff
  rationale), §1.3 (verified versions table).
- Cross-repo precedent: `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
  Revision 2 §"Revised decision".
- Portfolio guide: `guardkit/docs/guides/portfolio-python-pinning.md`.

## Implementation Summary

Applied the exact pin diff from review §4 to `pyproject.toml`: added `<2` caps
to `langchain` and `langchain-core` in runtime `dependencies`, and replaced
the five completely-unpinned `[providers]` entries with explicit floor+cap
specifiers matching the empirically-verified 1.x versions
(`langchain-openai>=1.2,<2`, `langchain-anthropic>=1.4,<2`,
`langchain-google-genai>=4.2,<5`, `langchain-aws>=1.4,<2`,
`langchain-ollama>=1.1,<2`). 9-line net diff; no other lines touched.

`uv lock` regenerated cleanly — 7 insertions / 7 deletions in `uv.lock`,
specifier-metadata only, zero version regressions vs the review baseline.

## Verification result

Re-ran the review's empirical recipe verbatim on Python 3.14.2:

- Fresh `.venv` install of `.[dev,providers]` succeeded.
- `import study_tutor` → 0.
- **`pytest` 23/23 passed in 6.79s** (matches review baseline 23/23 in 6.84s).
- Resolved versions table matches the baseline exactly:
  langchain 1.2.15, langchain-core 1.3.2, langchain-anthropic 1.4.2,
  langchain-aws 1.4.5, langchain-google-genai 4.2.2, langchain-ollama 1.1.0,
  langchain-openai 1.2.1, langgraph 1.1.10, pydantic 2.13.3.
- Scope clean: only `pyproject.toml` and `uv.lock` modified.

## Notes

- This task is **forward-protection only** — today's resolver picks the same
  coherent 1.x set with or without the `<2` caps; the diff just locks the
  next coordinated breaking-change wave (the FA04 mechanism) out of the
  resolver's search space.
- `langchain-protocol 0.0.13` appeared as a new transitive vs the review
  snapshot. Not a regression — it's a pulled-in dependency of the same
  resolved 1.x set, just absent from the review's `grep -iE "(langchain|...)"`
  filter at the time. Tests pass with it present.
- Out-of-scope items (ADR — TASK-PLA-002, README pinning policy —
  TASK-PLA-003) untouched per task spec.
