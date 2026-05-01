---
id: TASK-FIX-AB7A-003
title: Backfill seam test for TASK-PRV-003 (retrieval-decision contract)
task_type: feature
parent_review: TASK-REV-AB7A
feature_id: FEAT-FIX-AB7A
wave: 2
implementation_mode: task-work
complexity: 2
estimated_minutes: 20
dependencies:
  - TASK-FIX-AB7A-001
  - TASK-FIX-AB7A-001b
status: completed
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/feat-fix-ab7a/
tags: [seam-test, contract-test, FEAT-70A4, FEAT-PRV-003, latent-bug-check]
test_results:
  status: passed
  coverage: not_required
  last_run: 2026-04-30T00:00:00Z
  passed: 1
  failed: 0
  duration_seconds: 0.02
  command: ".guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v"
  cwd: ".guardkit/worktrees/FEAT-70A4"
---

# Task: Backfill seam test for TASK-PRV-003 (retrieval-decision contract)

## Description

TASK-PRV-003 was conditionally approved under the same `parallel_contention` rule that masked PRV-002's contract failure. Its seam test was explicitly planned and stubbed at `tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-003-retrieval-decision-function.md:158-184` but never implemented. Wave 3+ tasks (PRV-004 source-filtered retrieval; PRV-006 Coach handover) consume `should_retrieve()`'s `RetrievalDecision` named-tuple contract directly, so a contract violation here cascades.

This task implements the planned seam test as a **gate condition** for resume. Failure → escalate to a code fix on `retrieval.py` before TASK-FIX-AB7A-004.

## Scope

- Implement seam test at `tests/unit/knowledge/test_seam_retrieval_decision.py`.
- Mark with `@pytest.mark.seam` and `@pytest.mark.integration_contract("RetrievalDecision")`.
- Validate the four-branch decision tree returns `RetrievalDecision` named tuples whose `reason` values are **module-level constants** (identity check, not equality).
- No production-code edits in this task.

## Out of Scope

- Modifying `retrieval.py`.
- Backfilling PRV-002's seam test (TASK-FIX-AB7A-002).

## Acceptance Criteria

- [x] File `tests/unit/knowledge/test_seam_retrieval_decision.py` exists in the worktree.
- [x] Imports the public surface: `should_retrieve`, `RetrievalDecision`, and the four `REASON_*` module-level constants.
- [x] Includes a test `test_should_retrieve_returns_named_tuple_contract` that asserts:
      - Result is `isinstance(decision, RetrievalDecision)` (named-tuple check).
      - For `(text_name="nonexistent_text", focus_aos={"AO1","AO2"})`: `decision.reason is REASON_NO_PRIMARY` (identity, not `==`).
      - At least three additional branch assertions covering AO3-only, mixed AO3, and primary-present-non-AO3-only — each using identity (`is`) on the relevant constant.
- [x] Test runs successfully under `.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v` (TASK-FIX-AB7A-001b must have completed first to ensure pytest is in the venv).
- [x] Test exits 0. (If non-zero — STOP. Open a code-fix subtask against `retrieval.py`.)
- [x] Test code passes the project's lint/format checks.

## Test Requirements

The test file IS the deliverable. It must:
- [x] Be collected by `pytest -m seam`.
- [x] Be hermetic (no embedder calls, no FalkorDB; mock `has_primary_text` as needed).
- [x] Run in <1s wall-clock.

## Implementation Notes

**Reference stub** (from `tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-003-retrieval-decision-function.md:158-184`):

```python
import pytest
from study_tutor.knowledge.retrieval import (
    should_retrieve, RetrievalDecision,
    REASON_NO_PRIMARY, REASON_AO3_ONLY,
    REASON_RETRIEVE_PRIMARY, REASON_RETRIEVE_MIXED,
)


@pytest.mark.seam
@pytest.mark.integration_contract("RetrievalDecision")
def test_should_retrieve_returns_named_tuple_contract():
    decision = should_retrieve("nonexistent_text", {"AO1", "AO2"})
    assert isinstance(decision, RetrievalDecision)
    assert decision.reason is REASON_NO_PRIMARY  # identity, not equality
```

Extend the stub to cover the four named branches:

| `focus_aos` | `text_name` (mocked has_primary_text) | Expected reason | Expected mode |
|---|---|---|---|
| `{"AO3"}` | any | `REASON_AO3_ONLY` | `"ao3_bypass"` |
| `{"AO1","AO2"}` | absent | `REASON_NO_PRIMARY` | `"analysis_mode"` |
| `{"AO1","AO2","AO3"}` | present | `REASON_RETRIEVE_MIXED` | `"mixed"` |
| `{"AO1","AO2"}` | present | `REASON_RETRIEVE_PRIMARY` | `"retrieve"` |

**Why identity not equality:** the original PRV-003 task explicitly required reason values to be module-level constants so a future rename fails loudly. If the implementation hard-codes string literals at the call sites, the `is` check catches it; an `==` check would silently pass on stale literals.

## Test Execution Log

**Run:** 2026-04-30 — `/task-work TASK-FIX-AB7A-003`
**Worktree:** `.guardkit/worktrees/FEAT-70A4` (branch `autobuild/FEAT-70A4`)
**Interpreter:** `.guardkit/venv/bin/python` (Python 3.12.3)
**Command:**

```bash
.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v
```

**Result:** ✅ 1 passed in 0.02s (exit 0).

```
tests/unit/knowledge/test_seam_retrieval_decision.py::test_should_retrieve_returns_named_tuple_contract PASSED [100%]
```

**Cross-check** — full seam suite under the same interpreter (worktree-wide):

```
9 passed, 246 deselected in 0.04s
```

All four branches (`REASON_NO_PRIMARY`, `REASON_AO3_ONLY`, `REASON_RETRIEVE_MIXED`, `REASON_RETRIEVE_PRIMARY`) verified via `is`-identity on the module-level constants. No regressions in pre-existing seam tests (`test_seam_pydantic_entities`, `test_seam_corpus_loader`, embedded `test_retrieval.py` seam case).

### Acceptance criteria

- ✅ File exists at `tests/unit/knowledge/test_seam_retrieval_decision.py` in the worktree.
- ✅ Imports `should_retrieve`, `RetrievalDecision`, and the four `REASON_*` constants (plus `clear_primary_text_index`/`register_primary_text` for hermetic branch fixturing).
- ✅ `test_should_retrieve_returns_named_tuple_contract` asserts `isinstance(decision, RetrievalDecision)` plus identity (`is`) on each of the four branch reasons.
- ✅ Collected by `pytest -m seam` (verified in cross-check above).
- ✅ Hermetic — no embedder probe installed, no FalkorDB; uses public registration helpers.
- ✅ Wall-clock 0.02s, well under the 1s budget.
- ✅ Exits 0 — no code-fix subtask required against `retrieval.py`. The conditional approval was, on this evidence, a lucky guess that turned out to hold.
- ✅ Lint/format: project has no configured ruff/black/flake8/mypy pipeline; AST parses cleanly; style mirrors existing `test_seam_pydantic_entities.py`.
