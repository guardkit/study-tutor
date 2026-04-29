---
id: TASK-DSP-009
title: Author smoke tests + register markers for FEAT-PH1-002 smoke gate
task_type: implementation
parent_review: TASK-DSP-008
feature_id: FEAT-PH1-002
status: completed
created: '2026-04-29T23:20:00Z'
updated: '2026-04-29T23:55:00Z'
completed: '2026-04-29T23:55:00Z'
completed_location: tasks/completed/TASK-DSP-009/
previous_state: in_review
state_transition_reason: All acceptance criteria verified; smoke gate passing on autobuild/FEAT-PH1-002 worktree
priority: high
complexity: 3
implementation_mode: direct
tags:
- phase-1
- planner
- smoke-tests
- pytest-markers
- feat-ph1-002
- followup
dependencies: []
estimated_minutes: 45
test_results:
  status: passed
  coverage: null
  last_run: '2026-04-29T23:50:00Z'
  gate_command: pytest -m "feat_ph1_002 and smoke" -x --no-cov
  gate_exit_code: 0
  selected: 2
  deselected: 391
  full_suite_passed: 393
  full_suite_duration_seconds: 20.86
---

# Task: Author smoke tests + register markers for FEAT-PH1-002 smoke gate

## Context

The FEAT-PH1-002 autobuild run reported `FEATURE RESULT: FAILED` even
though all six implementation tasks were independently approved. The
post-mortem ([TASK-DSP-008 review report](../../../.claude/reviews/TASK-DSP-008-review-report.md))
confirmed the root cause: **pytest exit 5 (no tests collected)** because
the smoke gate's marker expression `feat-ph1-002 and smoke` matches zero
tests in the worktree (391 deselected / 0 selected).

Specifically:
- Markers `smoke` and `feat-ph1-002` are not registered in
  `[tool.pytest.ini_options].markers` in `pyproject.toml` — only `seam`
  and `integration_contract` are.
- No test under `tests/` carries `@pytest.mark.smoke` or any feature-id
  marker.
- None of TASK-DSP-001..006 had a smoke-test acceptance criterion, so the
  gate was never wired to anything.

This task closes that gap. It is the chosen path **(c)** from the review's
decision matrix.

## Goals

1. Register the `smoke` and `feat-ph1-002` pytest markers in `pyproject.toml`.
2. Author at least one smoke test that exercises the deterministic session
   planner end-to-end and carries both markers.
3. Confirm the autobuild smoke-gate command now exits 0 with ≥1 selected.

## Acceptance Criteria

- [ ] `pyproject.toml` `[tool.pytest.ini_options].markers` block includes:
  - `smoke: fast end-to-end-ish smoke tests run by autobuild smoke gates`
  - `feat-ph1-002: tests scoped to the Deterministic Session Planner feature`
  - (existing `seam` and `integration_contract` entries preserved verbatim)
- [ ] At least one new test exists carrying both
      `@pytest.mark.smoke` and `@pytest.mark.feat-ph1-002`. Suggested
      coverage:
  - Happy path: `plan_session(...)` with state where Rule 1 fires
    (learner override) → returns a plan with `rule_selected='rule_1'`.
  - Fallback path: `plan_session(...)` with no state available →
    rule-6/baseline fallback returns a plan with
    `fallback_used='baseline'`.
  - The smoke test must complete in well under the 60-second gate timeout
    (target: <2s) and must not require any external service (no Graphiti,
    no MCP transport, no LLM calls).
- [ ] Running the exact gate command in the repo:
      `pytest -m "feat-ph1-002 and smoke" -x --no-cov`
      exits **0** with `selected ≥ 1`.
- [ ] Existing tests are unaffected — `pytest -q` still passes the same
      number of items it did before this task (no regressions, no
      newly-collected-then-failing items).
- [ ] Update `[FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml)`
      `status` field from `failed` to `passed` (or whichever value the
      schema uses for "feature green") once the gate passes locally.

## Suggested Approach

1. **Edit `pyproject.toml`**: extend the existing `markers = [...]` list.
   Keep entries one-per-line to match current style.
2. **Add `tests/smoke/test_session_planner.py`** (new directory, new file).
   Use the planner directly:
   ```python
   import pytest
   from study_tutor.planner import plan_session

   pytestmark = [pytest.mark.smoke, pytest.mark.feat_ph1_002]
   # or apply per-test if the dashed marker name doesn't pass through;
   # in that case use @pytest.mark.smoke + @pytest.mark.parametrize naming
   ```
   **Note on marker name:** `feat-ph1-002` contains hyphens. Pytest accepts
   hyphenated markers in `-m` expressions, but `@pytest.mark.feat-ph1-002`
   is not a valid Python attribute. Two viable patterns:
   - `pytestmark = pytest.mark.parametrize` style is wrong here; use
     `pytest.mark.feat_ph1_002` Python-side **and** also register
     `feat_ph1_002` (underscore form) — but then the gate command must
     match. Cleanest fix: register **both** the dashed marker (for the
     `-m` expression) and use `getattr(pytest.mark, "feat-ph1-002")` to
     apply it in code, or keep it simple by using
     `pytestmark = [pytest.mark.smoke, getattr(pytest.mark, "feat-ph1-002")]`.
   - Alternatively, if the implementer prefers to avoid the attribute-name
     gymnastics, propose a follow-up to switch the gate command in
     `[FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml)`
     to use `feat_ph1_002` (underscore) and register that variant. The
     gate command is config, not contract — changing it is fine, but
     surface that change clearly in this task's PR description.
3. **Run the gate command locally** and capture exit code + selected count
   in the task's completion notes.
4. **Update FEAT-PH1-002.yaml `status`** once green.

## Out of Scope

- Authoring an exhaustive smoke suite. **One** end-to-end test (or two —
  happy path + fallback) is sufficient to satisfy the gate. Broader
  smoke coverage can land in a follow-up.
- Touching the GuardKit `smoke_gates` orchestrator module (the
  exit-5-vs-exit-1 disambiguation note). That is filed separately in the
  GuardKit project under R3 of the post-mortem.
- Re-running the full autobuild for FEAT-PH1-002. Local gate-command
  verification is sufficient for this task.

## References

- Post-mortem report: [.claude/reviews/TASK-DSP-008-review-report.md](../../../.claude/reviews/TASK-DSP-008-review-report.md)
- Review task: [TASK-DSP-008](TASK-DSP-008-smoke-gate-failure-review.md)
- Smoke-gate config: [.guardkit/features/FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml)
- Failure log: [docs/history/autobuild-FEAT-PH1-002-history.md:1591-1594](../../../docs/history/autobuild-FEAT-PH1-002-history.md#L1591-L1594)

## Completion Notes (2026-04-29)

### Marker name decision: underscore form

Empirically, pytest's `-m` expression parser treats the expression as
Python — so `feat-ph1-002` is read as `feat - ph1 - 002` (three
subtractions) and silently matches no test. The cleanest fix the task's
"Suggested Approach" §2 already flagged was option two: register the
underscore form (`feat_ph1_002`) and update the gate command in
`FEAT-PH1-002.yaml` to match. Both files are now aligned on the
underscore form on **branch `autobuild/FEAT-PH1-002`** (the worktree
where the planner lives) and on **main** (`.guardkit/features/FEAT-PH1-002.yaml`).

### Changes applied

On `autobuild/FEAT-PH1-002` (worktree at `.guardkit/worktrees/FEAT-PH1-002/`,
where the planner module exists — the smoke tests cannot land on `main`
until that branch merges):

- `pyproject.toml` — added two `[tool.pytest.ini_options].markers`
  entries: `smoke` and `feat_ph1_002` (existing `seam` and
  `integration_contract` preserved verbatim).
- `tests/smoke/__init__.py` — new (package marker).
- `tests/smoke/test_session_planner.py` — two `plan_session` smoke tests
  carrying both markers via module-level
  `pytestmark = [pytest.mark.smoke, pytest.mark.feat_ph1_002]`:
  - **Happy path** — Rule 1 (learner override) short-circuits the
    pipeline; asserts `rule_selected='rule-1'` and `topic_name` matches
    the override.
  - **Fallback path** — `client=None` + no override → baseline plan;
    asserts `fallback_used='baseline'`, `rule_selected='baseline'`, and
    `learner_state_available is False`.
- `.guardkit/features/FEAT-PH1-002.yaml` — gate command updated from
  `pytest -m "feat-ph1-002 and smoke" ...` to
  `pytest -m "feat_ph1_002 and smoke" ...` (underscore form, with a
  comment explaining why).

On `main`:

- `.guardkit/features/FEAT-PH1-002.yaml` — `status: failed` → `passed`
  and gate command updated to underscore form for consistency with the
  worktree branch.
- `tasks/backlog/.../TASK-DSP-009-...md` → `tasks/in_progress/...` (this
  file).

The `pyproject.toml` and `tests/smoke/` changes deliberately do **not**
land on main in this commit — they import from
`study_tutor.planner`, which only exists on the
`autobuild/FEAT-PH1-002` branch. They will arrive on main when that
branch merges.

### Acceptance criteria — verification

- [x] `pyproject.toml` `[tool.pytest.ini_options].markers` block now
      includes `smoke` and `feat_ph1_002` (worktree branch). Existing
      `seam` and `integration_contract` entries preserved verbatim.
- [x] At least one new test exists carrying both
      `@pytest.mark.smoke` and `@pytest.mark.feat_ph1_002`. Two were
      added — happy path + fallback. Each runs in <0.3s in aggregate
      with no external service required (`client=None` returns
      `StudentState(empty=True)` without contacting Graphiti).
- [x] Gate command exits **0** with **2 selected**, 391 deselected:
      ```
      $ pytest -m "feat_ph1_002 and smoke" -x --no-cov
      collected 393 items / 391 deselected / 2 selected
      tests/smoke/test_session_planner.py ..                        [100%]
      ====================== 2 passed, 391 deselected in 0.29s ======================
      ```
- [x] Existing tests are unaffected — `pytest -q --no-cov` reports
      `393 passed in 20.86s` (= the original 391 + 2 new smoke tests;
      same 391 baseline, no regressions).
- [x] `.guardkit/features/FEAT-PH1-002.yaml` `status` is `passed`
      (updated on main).
