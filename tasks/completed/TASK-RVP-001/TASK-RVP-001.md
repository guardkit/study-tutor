---
id: TASK-RVP-001
title: Verify revise decision path is architecturally reachable in Player-Coach orchestrator
task_type: review
status: completed
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T00:00:00+00:00
completed: 2026-05-06T00:00:00+00:00
completed_location: tasks/completed/TASK-RVP-001/
previous_state: in_review
complexity: 4
related:
  - TASK-PTS-001
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LSP-002
tags:
  - plumbing-verification
  - player-coach-loop
  - orchestrator
  - revise-path
  - decision-routing
  - coach-output-parsing
  - feat_lca
context_files:
  - src/study_tutor/tutoring/orchestrator.py
  - src/study_tutor/tutoring/coach/factory.py
  - src/study_tutor/tutoring/adapters/llm_coach_adapter.py
test_results:
  status: passing
  coverage: null
  last_run: 2026-05-06
---

# Verify revise decision path is architecturally reachable in Player-Coach orchestrator

## Problem

Across two demo sessions on **2026-05-06** (10 total `tutor_turn` calls),
the `decision=revise` path with `attempts > 1` was **never exercised**.
The observed decisions were:

- `accept` — 9 turns
- `fallback` with `flagged_for_review=true` — 1 turn

This is **not necessarily a Coach quality issue**. The Coach is
`qwen36-workhorse` without ChromaDB RAG, so it has no curriculum ground
truth to evaluate factual accuracy against. It correctly caught a
structurally incoherent response (Player confusing Macbeth/Lady Macbeth
throughout) and flagged it, which is reasonable given its constraints.

However, it returned `fallback` rather than `revise`, which raises the
question: **is the `revise` branch in the orchestrator reachable at all,
or is there a code-path issue that means even a Coach returning an
explicit `revise` signal would be routed to `fallback` instead?**

## Scope — plumbing only, not Coach quality

This task confirms the **mechanical path works end-to-end**. It does
**NOT** attempt to:

- Improve Coach evaluation quality
- Tune the rubric
- Add RAG / ChromaDB retrieval
- Adjust the Coach prompt

Coach quality improvements depend on ChromaDB retrieval being wired in,
which is a separate feature. This task is strictly about whether the
plumbing exists for a `revise` signal to flow through.

## Investigation Areas

### 1. `src/study_tutor/tutoring/orchestrator.py` — trace `run_turn`

- Under what conditions does it set `decision=revise`?
- Is there a code path from Coach output → `revise` decision →
  `LLMPlayerAdapter.revise()` call → second Coach evaluation → return
  with `attempts=2`?
- Or does the branching logic default to `fallback` whenever the Coach
  doesn't return `accept`?

### 2. `src/study_tutor/tutoring/coach/factory.py` — `parse_coach_output`

- What structured shape must the Coach LLM response have to trigger
  `revise` rather than `fallback`?
- Is the parser expecting a specific format (e.g. JSON with a `decision`
  field, or a keyword like `"REVISE"`) that the freeform Coach output
  never matches?

### 3. `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` — `evaluate()`

- Does it return a structured object with a `decision` field, or a raw
  string that the orchestrator interprets?
- Where is the boundary between adapter parsing and orchestrator
  routing?

## Required Deliverable

A unit test in `tests/unit/` that:

1. Mocks the Coach adapter to return an explicit `revise` signal with
   feedback text.
2. Runs a turn through the orchestrator.
3. Asserts:
   - **(a)** `LLMPlayerAdapter.revise()` is called with the Coach's
     feedback.
   - **(b)** The Coach evaluates the revised response (second call to
     `evaluate()`).
   - **(c)** The returned result has `decision` ∈ {`accept`, `revise`,
     `fallback`} (depending on the second evaluation) and `attempts=2`.

If the test **cannot be made to pass** because the orchestrator code
does not support the revise path, **document exactly where the gap is**
and what code change is needed to make it reachable. In that case the
deliverable becomes a diagnostic report (markdown) under
`docs/state/TASK-RVP-001-revise-path-gap-report.md` with:

- Exact file:line of the gap
- Minimal code change to close it
- Whether the change is in `orchestrator.py`, `factory.py`,
  `llm_coach_adapter.py`, or a combination

## Acceptance Criteria

- [x] Trace of `run_turn` in `src/study_tutor/tutoring/orchestrator.py`
      documented — what condition triggers `decision=revise` vs
      `decision=fallback`. (See report §1.)
- [x] Trace of `parse_coach_output` documented — what structured shape
      triggers each decision. (Note: function actually lives in
      `src/study_tutor/tutoring/coach/rubric.py:642`, not `factory.py`;
      schema lives in `factory.py:237`. See report §2.)
- [x] Trace of `LLMCoachAdapter.evaluate()` return type in
      `src/study_tutor/tutoring/adapters/llm_coach_adapter.py`
      documented. (See report §3.)
- [x] **Both** deliverables produced:
      (a) `tests/unit/tutoring/test_revise_path_reachable.py` exists and
      passes — mocks `CoachLike` to return `decision="revise"` then
      `accept`, asserts `Player.revise()` called with structured rubric
      feedback, second `Coach.evaluate()` call, `attempts=2`, and
      `decision in TurnDecision`.
      (b) Diagnostic report at
      `docs/state/TASK-RVP-001-revise-path-gap-report.md` documents the
      finding (no architectural gap; the user's confusion was
      terminology — `CoachVerdict.decision="revise"` vs
      `TurnResult.decision in {"accept","exhausted","fallback"}`).
- [x] `pytest tests/unit/tutoring/ -x` passes (236 passed).
- [x] `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
      passes (5 passed, 1 skipped — no regression).
- [x] No change to Coach prompt, rubric weights, or any model-side
      configuration — this task is plumbing-only.
- [x] No new dependency on ChromaDB or RAG retrieval — Coach quality
      improvements remain out of scope.

## Out of Scope

- Improving Coach evaluation quality (rubric tuning, prompt edits).
- Wiring ChromaDB / RAG retrieval into the Coach.
- Adjusting the rubric weights in `src/study_tutor/tutoring/coach/rubric.py`.
- Any change to `src/study_tutor/tutoring/coach/sanitise.py` beyond what
  is needed to expose the revise path.
- Multi-attempt loops (`attempts > 2`) — current orchestrator presumably
  caps at one revise; verifying that cap is also out of scope.

## Files Involved

- `src/study_tutor/tutoring/orchestrator.py` — `run_turn` logic.
- `src/study_tutor/tutoring/coach/factory.py` — `parse_coach_output`.
- `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` — `evaluate()`
  return shape.
- `src/study_tutor/tutoring/adapters/llm_player_adapter.py` — `revise()`
  method (mock target).
- `tests/unit/tutoring/` — new test file (path TBD by investigation).

## Reproduction Evidence

- **2026-05-06**: Two demo MCP tutor sessions, 10 total `tutor_turn`
  invocations. 9 returned `decision=accept`, 1 returned
  `decision=fallback` with `flagged_for_review=true`. **Zero** turns
  returned `decision=revise` or `attempts=2`.

## Implementation Notes

- The diagnostic-report fallback (acceptance criterion (b)) is a
  legitimate deliverable, not a failure mode. If the orchestrator
  genuinely lacks a revise branch, surfacing that explicitly is more
  valuable than forcing a green test against broken plumbing.
- Mocks should target the Coach **adapter** boundary
  (`LLMCoachAdapter.evaluate()`), not the underlying `LLMClient`, so
  the test exercises the orchestrator's decision-routing logic rather
  than the Coach's parsing logic. If `evaluate()` itself does the
  parsing and returns a structured object, the mock should return that
  structured object directly.
- If the parser is the bottleneck (i.e. `parse_coach_output` never
  emits `revise`), a secondary unit test against `parse_coach_output`
  with a hand-crafted Coach payload may also be warranted — note that
  in the diagnostic report.

## Test Execution Log

**Run date:** 2026-05-06

```
$ pytest tests/unit/tutoring/test_revise_path_reachable.py -v
tests/unit/tutoring/test_revise_path_reachable.py::test_coach_revise_signal_drives_player_revise_and_second_evaluation PASSED [ 50%]
tests/unit/tutoring/test_revise_path_reachable.py::test_turn_decision_literal_does_not_include_revise PASSED [100%]
2 passed in 0.06s

$ pytest tests/unit/tutoring/ -x -q
236 passed, 1 warning in 1.28s

$ pytest -m "feat_lca and smoke" tests/unit tests/integration -x -q
5 passed, 1 skipped, 844 deselected, 1 warning in 0.81s
```

## Finding

**No architectural gap.** The revise path is reachable end-to-end.

The user's reproduction observation ("9 `accept`, 1 `fallback`, zero
`revise`") reflected a **terminology mismatch**, not a code-path issue:

- `CoachVerdict.decision` is `Literal["accept", "revise"]`
  (`factory.py:259`) — a Coach-side concept.
- `TurnResult.decision` is `Literal["accept", "exhausted", "fallback"]`
  (`orchestrator.py:73`) — never `"revise"`. A `revise` verdict drives
  the loop, and the loop's outcome is one of the three terminal
  decisions.

The fingerprint of "revise path was exercised" in production is
`TurnResult.attempts > 1`, not `decision == "revise"`. The 10 demo
turns all showed `attempts == 1`, which means the qwen36-workhorse
Coach (without ChromaDB RAG) never returned a `revise` verdict that
the parser could ingest — that is a Coach-quality / parsing concern,
explicitly **out of scope** for this task and tracked separately.

See `docs/state/TASK-RVP-001-revise-path-gap-report.md` for the full
trace through `orchestrator.py` / `rubric.py` / `llm_coach_adapter.py`.
