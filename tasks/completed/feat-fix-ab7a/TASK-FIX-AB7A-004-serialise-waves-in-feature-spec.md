---
id: TASK-FIX-AB7A-004
title: Serialise wave 3 of FEAT-70A4 to avoid shared-BDD-glue contention
task_type: feature
parent_review: TASK-REV-AB7A
feature_id: FEAT-FIX-AB7A
wave: 3
implementation_mode: direct
complexity: 1
estimated_minutes: 10
dependencies:
  - TASK-FIX-AB7A-002
  - TASK-FIX-AB7A-003
status: completed
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
completed_location: tasks/completed/feat-fix-ab7a/
tags: [autobuild, parallel-contention, FEAT-70A4, wave-plan]
test_results:
  status: passed
  coverage: n/a
  last_run: 2026-04-30T00:00:00Z
---

# Task: Serialise wave 3 of FEAT-70A4 to avoid shared-BDD-glue contention

## Description

Wave 2 of FEAT-70A4 ran TASK-PRV-002 and TASK-PRV-003 in parallel; both wrote step definitions to the same 888-line BDD glue file `features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py`. Independent test verification failed for both tasks; the conditional-approval rule (`coach_validator.py:861-866`) approved them anyway because all Player gates passed. The same hazard applies to **wave 3** (`[TASK-PRV-004, TASK-PRV-005]`): both tasks add step definitions to the same BDD glue file.

**Fix:** edit `.guardkit/features/FEAT-70A4.yaml` `orchestration.parallel_groups` to split wave 3 into two single-task waves. Waves 1, 2, 4, and 5 are unchanged (wave 2 already executed; wave 4 and wave 5 already had a single task each).

## Scope

- Edit `.guardkit/features/FEAT-70A4.yaml`.
- Change the `orchestration.parallel_groups` list ONLY.
- Do not touch `smoke_gates`, `tasks`, `execution`, or any other section.

## Out of Scope

- Wave 2 plan (already executed).
- The smoke-gate command itself (TASK-FIX-AB7A-001).

## Acceptance Criteria

- [ ] After edit, `orchestration.parallel_groups` reads:
      ```yaml
      parallel_groups:
      - - TASK-PRV-001
      - - TASK-PRV-002
        - TASK-PRV-003
      - - TASK-PRV-004
      - - TASK-PRV-005
      - - TASK-PRV-006
      - - TASK-PRV-007
      ```
- [ ] `recommended_parallel: 2` is unchanged (other features may still benefit).
- [ ] `estimated_duration_minutes` may be updated to reflect the new wave count if accurate, but is not strictly required.
- [ ] No other section of the YAML is modified (verify via `git diff .guardkit/features/FEAT-70A4.yaml` — only the `parallel_groups` list lines should change).
- [ ] YAML is still valid (`python3 -c "import yaml; yaml.safe_load(open('.guardkit/features/FEAT-70A4.yaml'))"`).
- [ ] **Pre-resume gate:** before this task is marked complete, all 5 verification commands from `tasks/backlog/feat-fix-ab7a/IMPLEMENTATION-GUIDE.md §"Pre-Resume Verification"` exit 0. If TASK-FIX-AB7A-002 or 003 seam tests fail, do NOT complete this task — open a code-fix subtask first.

## Test Requirements

- Acceptance criteria #1, #4, #5 are the verification.
- The pre-resume gate (acceptance #6) is critical — it is the only safety net for the conditional-approval rule's blind spot.

## Implementation Notes

**Why split wave 3 only:**
- Original `parallel_groups`: `[[PRV-001], [PRV-002, PRV-003], [PRV-004, PRV-005], [PRV-006], [PRV-007]]`
- Wave 1 already ran (PRV-001 alone, no contention)
- Wave 2 already ran (PRV-002 + PRV-003 — already-poisoned, conditional-approved)
- Wave 3 (PRV-004 + PRV-005) has not run; this is the dangerous one — both share the same BDD glue
- Waves 4, 5 are already single-task — no change needed

**Why not also serialise upstream features generally:** that would belong upstream in `/feature-plan` (filed as GK-UPSTREAM-3 in the addendum). For THIS feature, the local YAML edit is sufficient.

**Why this task is in wave 3 of FEAT-FIX-AB7A:** it can only run after the seam-test gate passes (depends on 002 and 003), and it must run before 005 (resume).

**This task and TASK-FIX-AB7A-001 BOTH edit FEAT-70A4.yaml** — that's why they're in different waves of FEAT-FIX-AB7A. The whole point of this fix feature is to model the right way to handle shared-source edits.

## Test Execution Log

### 2026-04-30 — /task-work TASK-FIX-AB7A-004 (micro mode, complexity 1)

**YAML edit applied** to `.guardkit/features/FEAT-70A4.yaml`:
- Single change: split wave-3 list `[TASK-PRV-004, TASK-PRV-005]` into two single-task waves.
- Diff confirmed scoped to the `parallel_groups` block (other diff lines are pre-existing autobuild state from prior runs, present at session start).

**Acceptance criteria:**
- [x] AC #1: `parallel_groups` matches spec — verified via `python3 -c "import yaml; ..."` showing 6 single-task waves except wave 2 which keeps `[002, 003]` (already executed).
- [x] AC #2: `recommended_parallel: 2` unchanged.
- [x] AC #3: `estimated_duration_minutes: 418` left unchanged (not strictly required).
- [x] AC #4: My edit modified only the `parallel_groups` list; no other section was touched.
- [x] AC #5: YAML is valid (`yaml.safe_load` succeeds).
- [x] AC #6: Pre-resume gate — all 5 verification commands exit 0 (run from `.guardkit/worktrees/FEAT-70A4`):
  - Step 0: `.guardkit/venv/bin/python -m pip install -e ".[dev]"` exit 0; `pytest.__version__ == 9.0.3` (≥ 9.0.2 expected) ✅
  - Step 1: import of `corpus_models` (CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor) ✅
  - Step 2: `pytest tests/unit/knowledge/ -x -q` → 255 passed in 8.70s ✅
  - Step 3: `pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v` → 1 passed (test_corpus_chunk_carries_typed_citation_anchor) ✅
  - Step 4: `pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v` → 1 passed (test_should_retrieve_returns_named_tuple_contract) ✅
  - Step 5: smoke-gate-equivalent (set -e; pip install [dev]; import; pytest knowledge) → 255 passed in 8.63s, exit 0 ✅

**Outcome:** All quality gates passed. Wave 3 is now safely serialised; on resume, TASK-PRV-004 and TASK-PRV-005 will run in separate single-task waves with no shared-BDD-glue contention. Task moved IN_PROGRESS → IN_REVIEW.
