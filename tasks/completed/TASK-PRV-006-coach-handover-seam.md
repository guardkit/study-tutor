---
complexity: 4
consumer_context:
- consumes: VerifierMetadata
  driver: pydantic
  format_note: Consumes the (rewritten_response, VerifierMetadata) tuple from verify_quotes;
    rewritten response is what the Coach evaluates
  framework: Pydantic v2 (BaseModel)
  task: TASK-PRV-005
- consumes: RetrievalDecision
  driver: stdlib
  format_note: Forwards RetrievalDecision.reason into VerifierMetadata.retrieval_skipped_reason
    for Coach quote-fidelity suppression in AnalysisMode
  framework: Python NamedTuple
  task: TASK-PRV-003
dependencies:
- TASK-PRV-005
estimated_minutes: 55
feature_id: FEAT-PRV4
id: TASK-PRV-006
implementation_mode: task-work
parent_review: TASK-REV-PRV4
priority: high
related_features:
- FEAT-PH1-004
- FEAT-PH1-003
status: completed
updated: '2026-04-30T22:20:00Z'
tags:
- feat-ph1-004
- feat-ph1-003
- coach
- handover
- integration
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: Coach handover seam — wire verifier into PlayerCoachOrchestrator
wave: 4
---

# Task: Coach handover seam — wire verifier into PlayerCoachOrchestrator

## Description

Wire `verify_quotes` into the existing `PlayerCoachOrchestrator`
(from FEAT-PH1-003) so the **rewritten** response is what reaches
the Coach, and `VerifierMetadata` accompanies it. This is the
contract surface consumed by TASK-DTL-002's `score_rubric.
quote_fidelity` criterion.

## Scope

- New module `src/study_tutor/knowledge/coach_handover.py`
  exposing a single thin function `apply_quote_verification(
  player_response: str, corpus_chunks: list[CorpusChunk],
  session_text_name: str, retrieval_skipped_reason: str | None
  ) -> tuple[str, VerifierMetadata]`
- Update `src/study_tutor/tutoring/orchestrator.py` (the
  `PlayerCoachOrchestrator` from FEAT-PH1-003) to call
  `apply_quote_verification` between Player.produce() and
  Coach.evaluate(). The Coach receives the rewritten response, not
  the original.
- Forward the `retrieval_skipped_reason` from `should_retrieve()`
  into the `VerifierMetadata` so the Coach can suppress
  `quote_fidelity` down-rank in AnalysisMode (per TASK-DTL-002
  acceptance criterion "analysis-mode responses not down-ranked")
- Failure-path: if `verify_quotes` raises, the original response is
  passed unannotated to the Coach with `VerifierMetadata()` (empty
  defaults) and a `verifier_exception` flag set; failure logged for
  session-end review (per TASK-DTL-002 acceptance criterion
  "verifier-exception → unannotated to Coach")
- Surface `verifier_metadata` in turn metadata so session-end
  summaries can include verifier events
- **Do not** modify TASK-DTL-002's `score_rubric` — that task
  already specifies how it consumes `VerifierMetadata`. This task
  delivers the seam, not the criterion logic.

## Out of Scope

- The Coach's `quote_fidelity` criterion mapping (TASK-DTL-002
  already implemented)
- Verifier internals (TASK-PRV-005)
- Retrieval-decision logic (TASK-PRV-003)
- Integration smoke (TASK-PRV-007)

## Acceptance Criteria

- [ ] Coach receives the **rewritten** response, not the original
      (covers @edge-case @verify @integration @coach-handover
      scenario)
- [ ] `VerifierMetadata` accompanies the rewritten response and is
      passed to the Coach evaluator (covers Group E coach-handover
      contract)
- [ ] AnalysisMode skip path sets `retrieval_skipped_reason` in
      metadata; Coach suppresses `quote_fidelity` down-rank for the
      turn (covers @key-example @smoke @retrieval @analysis-mode +
      TASK-DTL-002 acceptance criterion)
- [ ] Verifier exception → unannotated response passed to Coach
      with empty `VerifierMetadata` and a `verifier_exception` flag;
      failure logged (covers TASK-DTL-002 acceptance criterion
      "verifier-exception → unannotated")
- [ ] Per-turn `verifier_metadata` is recorded in turn metadata
      (visible at session-end)
- [ ] No regression to FEAT-PH1-003 — existing
      `PlayerCoachOrchestrator` tests still pass
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test: `apply_quote_verification` returns
      `(rewritten_response, metadata)` tuple
- [ ] Unit test: `retrieval_skipped_reason` is forwarded into
      metadata
- [ ] Failure-injection test: `verify_quotes` patched to raise →
      orchestrator continues, Coach receives original response with
      empty metadata + `verifier_exception` flag
- [ ] Integration test: orchestrator end-to-end with Macbeth
      corpus + a Player response containing a verbatim Shakespeare
      quote → Coach receives the annotated response
- [ ] Integration test: orchestrator end-to-end in AnalysisMode
      (Inspector Calls, no primary text) → Coach receives the
      original response with `retrieval_skipped_reason` set; Coach
      does not penalise on `quote_fidelity`

## Seam Tests

```python
"""Seam test: verify the Coach receives the rewritten response and
the verifier metadata, not the original response."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from study_tutor.knowledge.coach_handover import apply_quote_verification


@pytest.mark.seam
@pytest.mark.integration_contract("VerifierMetadata")
async def test_orchestrator_passes_rewritten_response_to_coach(
    orchestrator, macbeth_corpus
):
    """Verify the orchestrator's per-turn pipeline routes the
    verifier-rewritten response to the Coach, not the original
    Player response.

    Contract: PRV-005 produces (rewritten, VerifierMetadata); the
    handover seam ensures the Coach evaluator's first argument is
    the rewritten response.
    Producer: TASK-PRV-005 (verify_quotes)
    Consumer: TASK-DTL-002 (score_rubric.quote_fidelity)
    """
    coach_mock = AsyncMock()
    orchestrator.coach = coach_mock

    original_response = (
        'Lady Macbeth cries "Out, damned spot!" '
        'and "fabricated quote that does not exist".'
    )
    # ... (run a turn — concrete fixture during implementation)

    # Seam assertion: Coach.evaluate received the rewritten response
    coach_args = coach_mock.evaluate.await_args
    rewritten = coach_args.args[0]

    assert "fabricated quote" not in rewritten, \
        "Coach must not see the original fabricated quote"
    assert "(5.1" in rewritten or "Act 5" in rewritten, \
        "Coach must see the citation-annotated primary quote"

    # And verifier_metadata passed alongside
    metadata = coach_args.kwargs.get("verifier_metadata")
    assert metadata is not None
    assert metadata.primary_matches, "expected one primary match"
    assert metadata.stripped, "expected one no-match strip"
```

## Implementation Notes

**Why a separate `coach_handover.py` module:** keeps the
verification boundary out of `orchestrator.py` to preserve the
FEAT-PH1-003 module's single responsibility (Player-Coach loop
orchestration). The handover function is pure logic over
verifier output + retrieval decision; isolating it makes both
sides easier to test.

**Why verifier exceptions don't fail the turn:** safety-first.
If the verifier breaks, falling back to unannotated-response
+ Coach-evaluates-as-if-no-verifier is a graceful degradation
that's already specified in TASK-DTL-002. The alternative —
failing the turn — would surface as a worse user experience.

**Why we don't modify the Coach's score_rubric here:** TASK-DTL-002
already shipped (`status: in_review`) and specifies how it consumes
VerifierMetadata. This task only delivers the seam; the criterion
mapping is the Coach's responsibility.

## Test Execution Log

[Populated by /task-work]