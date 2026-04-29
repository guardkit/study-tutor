---
id: TASK-DTL-002
title: Coach rubric scoring and quote-fidelity integration
task_type: feature
parent_review: TASK-REV-DTL3
feature_id: FEAT-PH1-003
wave: 2
implementation_mode: task-work
complexity: 6
estimated_minutes: 90
dependencies:
  - TASK-DTL-001
status: backlog
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
tags: [feat-ph1-003, coach, rubric, quote-fidelity, FEAT-PH1-004, FEAT-PH1-003]
related_features:
  - FEAT-PH1-003
  - FEAT-PH1-004  # Quote verifier — consumed at this seam
related_tasks:
  - TASK-DTL-001  # Provides CoachVerdict, CriterionScore, RubricFeedback models
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Coach rubric scoring and quote-fidelity integration

## Description

Implement the six-criterion weighted rubric scoring inside the Coach's
evaluator function and integrate the quote verifier (FEAT-PH1-004 seam)
into the pre-Coach pipeline. Includes the documented fallback when the
quote verifier raises.

## Scope

- `score_rubric(player_response, turn_context, weights)` function
  inside the Coach evaluator that:
  - Produces six `CriterionScore` instances: curriculum accuracy,
    AO alignment, scaffolding depth, grade-appropriate language,
    constructive feedback, quote fidelity
  - Computes the weighted total across the six criteria
  - Returns a complete `CoachVerdict` shaped by TASK-DTL-001's models
- Acceptance threshold logic: weighted total `>= 0.70` → decision
  `"accept"`; `< 0.70` → decision `"revise"` (per ASSUM-001)
- Quote-verifier seam — a `verify_quotes(response)` call that runs
  BEFORE the Coach evaluates. The verifier:
  - Annotates verbatim quotes with canonical citations (happy path)
  - Removes/rewrites unmatched quotes as paraphrase (fabricated-quote
    edge case)
  - Skips inspection of spans below 4 words (boundary scenario)
  - Records "retrieval was skipped" with a reason in turn metadata
    when the session is in analysis mode and retrieval is bypassed
- Quote-verifier failure path: if the verifier raises an unexpected
  exception, the response is passed to the Coach **unannotated**, the
  Coach evaluates it under the documented fallback policy, and the
  failure is logged for session-end review (per @edge-case
  @integration scenario at .feature line 442-447)
- Malformed Coach output handling: if the Coach's text cannot be
  parsed into `CoachVerdict`, the loop applies the unevaluated-turn
  fallback policy (mirrors Coach-unreachable per ASSUM-007); no
  misconception derived from malformed output is persisted; turn is
  flagged for session-end review

## Out of Scope

- The quote-verifier internals (FEAT-PH1-004 — this task only consumes
  its protocol)
- The Player-Coach orchestrator (TASK-DTL-003 — this task ships the
  Coach evaluator that the orchestrator calls)
- Coach prompt content tuning (separate concern)

## Acceptance Criteria

- [ ] `score_rubric(...)` returns a `CoachVerdict` with all six
      `CriterionScore` instances populated (covers @key-example @rubric
      scenario "The Coach reports a per-criterion score and a weighted
      total")
- [ ] Weighted total computed from the six criterion scores via the
      configured weights; weights sum to 1.0 (sanity-check assertion at
      Coach factory construction)
- [ ] Threshold boundary scenarios pass: scores 0.70 → accept;
      0.69 → revise; 1.00 → accept; 0.00 → revise (covers @boundary
      @rubric Scenario Outline)
- [ ] Quote-verifier annotation flows: verbatim primary-text quote is
      annotated with canonical citation and the annotated response is
      the version evaluated by the Coach (covers @key-example @rubric
      @quote-fidelity scenario)
- [ ] Fabricated quote (no corpus match) is removed or rewritten as
      paraphrase before Coach evaluation; the rewrite is observable in
      the turn's recorded metadata (covers @edge-case @quote-fidelity
      @safety scenario)
- [ ] Quote-verifier minimum-length boundary: 3-word span ignored;
      4-word and 5-word spans inspected (covers @boundary
      @quote-fidelity Scenario Outline)
- [ ] Analysis-mode (retrieval skipped) responses are not down-ranked
      on quote fidelity; turn metadata records "retrieval was skipped"
      with a reason (covers @edge-case @quote-fidelity @retrieval
      scenario)
- [ ] Quote-verifier exception → response passed unannotated; Coach
      evaluates under fallback; failure logged (covers @edge-case
      @integration @quote-fidelity scenario)
- [ ] Malformed Coach output → unevaluated-turn fallback; no
      misconception persisted; turn flagged for session-end review
      (covers @negative @rubric scenario)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit tests for `score_rubric` covering all six criterion scoring
      branches independently (mock criterion scorers)
- [ ] Unit test for weighted-sum computation at threshold boundary
      (0.69 → 0.70 → 0.71)
- [ ] Integration test for the verify_quotes → score_rubric pipeline
      using a test corpus with one canonical primary text
- [ ] Failure-injection test: quote verifier raises → verdict still
      produced from unannotated response, failure log line emitted
- [ ] Failure-injection test: malformed Coach output → fallback path
      taken, no misconception persisted

## Seam Tests

The following seam test validates the integration contract with the
TASK-GSM-004 producer (shared write helper) at the boundary where this
task's Coach evaluator dispatches misconception writes:

```python
"""Seam test: verify Coach evaluator dispatches misconceptions via the
shared write helper protocol from TASK-GSM-004."""
import pytest
from unittest.mock import AsyncMock


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_coach_evaluator_dispatches_misconceptions_via_helper():
    """Verify Coach evaluator routes misconceptions through the shared
    write helper, not via direct add_episode calls.

    Contract: helper.write_misconception(student_id, payload) is the
    single dispatch surface for F1 writes (DDR-002).
    Producer: TASK-GSM-004
    """
    helper_mock = AsyncMock()
    helper_mock.write_misconception = AsyncMock()

    # Build a Coach with helper injected; run an evaluator pass that
    # produces one misconception observation.
    # ... (test scaffold — concrete imports during implementation)

    # Seam assertion: helper's write_misconception was called once;
    # no other write methods invoked from the Coach evaluator surface.
    assert helper_mock.write_misconception.await_count == 1
```

Concrete imports and the producer payload shape are filled in during
implementation; the assertion shape (helper-method invocation count
+ exclusivity) is the load-bearing seam contract.

## Implementation Notes

**Why criterion weights are configured at Coach factory construction:**
Weights are a tuning surface; baking them into the rubric function
hard-codes them across all sessions. Passing them through the factory
keeps all "what makes a good response" knobs in one place.

**Why malformed Coach output mirrors Coach-unreachable:**
ASSUM-007 + the @negative @rubric scenario set the policy: malformed
output is symmetric with unreachable output — both apply the
documented unevaluated-turn fallback. Treating malformed output more
strictly (e.g. rejecting the turn outright) would over-fire on
transient parsing failures.

**Why retrieval-skipped is recorded in turn metadata:**
The @edge-case @quote-fidelity @retrieval scenario requires that a
turn metadata record states retrieval was skipped with a reason. This
metadata is what the Coach uses to suppress the quote-fidelity
down-rank on AO3 contextual content paths.

## Test Execution Log

[Populated by /task-work]
