"""TASK-RVP-001 — verify the revise decision path is architecturally reachable.

Background
----------

In demo MCP tutor sessions on 2026-05-06, ten ``tutor_turn`` invocations
returned only ``decision=accept`` (×9) or ``decision=fallback`` (×1).
Zero turns showed ``attempts > 1`` or any sign that the orchestrator's
revision loop had been entered. The hypothesis the task tests: was the
``revise`` branch in :class:`PlayerCoachOrchestrator` even reachable, or
did the orchestrator silently route every below-threshold verdict to
``fallback``?

This module is the **trip-wire** for that hypothesis. It mocks the Coach
adapter at the :class:`CoachLike` boundary to emit an explicit
``CoachVerdict(decision="revise", ...)`` on the first turn followed by an
``accept`` on the revised turn, then asserts the three things the task
spec names verbatim:

  (a) :meth:`PlayerLike.revise` is invoked with the Coach's structured
      :class:`RubricFeedback` from the first verdict.
  (b) :meth:`CoachLike.evaluate` is invoked a second time on the revised
      Player response.
  (c) The resulting :class:`TurnResult` carries
      ``decision in {"accept", "exhausted", "fallback"}`` AND
      ``attempts == 2`` (i.e. the revision actually happened).

These assertions complement (not duplicate) the broader AC-002 test in
``test_orchestrator.py``: AC-002's framing is "below-threshold response
is never returned to the learner", whereas this module's framing is
"the revise path is reachable end-to-end" — same code path, different
documentation surface so a future reader debugging the same "I don't see
revise in production" symptom finds this file by name.

See also
--------

- ``docs/state/TASK-RVP-001-revise-path-gap-report.md`` — the diagnostic
  trace through ``orchestrator.py`` / ``rubric.py`` / ``llm_coach_adapter.py``
  that explains *why* this test passes (i.e. why there is no architectural
  gap), and how to read the orchestrator's :data:`TurnDecision` Literal
  (``"accept" | "exhausted" | "fallback"``) which deliberately does **not**
  include ``"revise"`` — ``"revise"`` is a Coach-side verdict, not a
  TurnResult-side decision.
- ``tests/unit/tutoring/test_orchestrator.py::test_revision_then_accept_never_shows_below_threshold_response``
  — the existing AC-002 test that proves the same path from a different
  angle.
"""
from __future__ import annotations

from typing import get_args
from unittest.mock import AsyncMock, MagicMock

import pytest

from study_tutor.tutoring.coach import (
    CoachVerdict,
    CriterionScore,
    RubricFeedback,
)
from study_tutor.tutoring.orchestrator import (
    PlayerCoachOrchestrator,
    TurnDecision,
    TurnResult,
)


def _make_revise_verdict(focus: str) -> CoachVerdict:
    """Build a Coach verdict that should drive the orchestrator into revision.

    The decision is ``"revise"`` (the only non-``"accept"`` value the
    :class:`CoachVerdict` schema admits at factory.py:259), and the
    rubric feedback list is non-empty so the orchestrator has structured
    guidance to forward to :meth:`PlayerLike.revise`.
    """
    return CoachVerdict(
        weighted_total=0.4,
        decision="revise",
        criterion_scores=[
            CriterionScore(criterion_id="c1", score=0.4, evidence="weak"),
        ],
        rubric_feedback=[
            RubricFeedback(
                criterion_id="c1",
                suggested_focus=focus,
                target_score=0.8,
            ),
        ],
        misconceptions=[],
        reasoning="Below threshold on c1.",
    )


def _make_accept_verdict() -> CoachVerdict:
    """Build a Coach verdict that closes out the revision attempt with accept."""
    return CoachVerdict(
        weighted_total=0.92,
        decision="accept",
        criterion_scores=[
            CriterionScore(criterion_id="c1", score=0.92, evidence="strong"),
        ],
        rubric_feedback=[],
        misconceptions=[],
        reasoning="Recovered after revision.",
    )


@pytest.mark.feat_lca
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_coach_revise_signal_drives_player_revise_and_second_evaluation() -> None:
    """End-to-end: revise verdict → Player.revise() → second Coach.evaluate().

    Mocks the :class:`CoachLike` adapter (the boundary the orchestrator
    actually consumes) rather than reaching down into
    :class:`LLMCoachAdapter` or the underlying ``LLMClient``. This is the
    seam ASSUM-LCA-005 prescribes: parsing lives in the adapter, decision
    routing lives in the orchestrator, and this test exercises the
    routing layer in isolation from any LLM I/O.

    The mock Player records both ``respond`` (first attempt) and
    ``revise`` (second attempt) so the test can assert the structured
    feedback handover happened.
    """
    revise_verdict = _make_revise_verdict(focus="topic-X")
    accept_verdict = _make_accept_verdict()

    player = MagicMock()
    player.respond = AsyncMock(return_value="First (weak) Player reply.")
    player.revise = AsyncMock(return_value="Revised (stronger) Player reply.")

    coach = MagicMock()
    coach.evaluate = AsyncMock(side_effect=[revise_verdict, accept_verdict])

    orch = PlayerCoachOrchestrator(player=player, coach=coach)
    result = await orch.run_turn(
        session_state={"sid": "test-rvp-001"},
        learner_message="Why does Macbeth hesitate?",
    )

    # ------------------------------------------------------------------
    # Assertion (a) — Player.revise() was called with the Coach feedback.
    # ------------------------------------------------------------------
    player.revise.assert_awaited_once()
    revise_kwargs = player.revise.call_args.kwargs
    assert revise_kwargs["previous_response"] == "First (weak) Player reply."
    forwarded = revise_kwargs["rubric_feedback"]
    assert len(forwarded) == 1
    assert isinstance(forwarded[0], RubricFeedback)
    # The feedback the orchestrator forwarded matches what the Coach emitted.
    assert forwarded[0].suggested_focus == "topic-X"
    assert forwarded[0].criterion_id == "c1"

    # ------------------------------------------------------------------
    # Assertion (b) — Coach.evaluate() was called a second time on the
    # revised response (i.e. the orchestrator did not short-circuit to
    # fallback after the revise verdict).
    # ------------------------------------------------------------------
    assert coach.evaluate.await_count == 2
    second_call_kwargs = coach.evaluate.call_args_list[1].kwargs
    assert second_call_kwargs["player_response"] == "Revised (stronger) Player reply."

    # ------------------------------------------------------------------
    # Assertion (c) — TurnResult.attempts == 2 AND decision is one of the
    # three allowed TurnDecision values.
    # ------------------------------------------------------------------
    assert isinstance(result, TurnResult)
    assert result.attempts == 2
    assert result.decision in get_args(TurnDecision)
    # And in this specific seeded sequence (revise → accept), the decision
    # is "accept" — proving the loop completed normally rather than
    # exhausting or falling back.
    assert result.decision == "accept"
    assert result.response == "Revised (stronger) Player reply."


@pytest.mark.feat_lca
@pytest.mark.smoke
def test_turn_decision_literal_does_not_include_revise() -> None:
    """Documentation guard: ``revise`` is a Coach-side concept, not a TurnResult.

    Pinned as a property test because the recurring confusion the parent
    task surfaces — operators looking for ``decision="revise"`` on
    returned :class:`TurnResult` objects — is a terminology problem, not
    a code-path problem. The orchestrator deliberately collapses revise
    outcomes into ``accept`` (revision succeeded), ``exhausted`` (3
    revise attempts hit the cap), or ``fallback`` (Coach unreachable
    mid-revision). If a future refactor adds ``"revise"`` to
    :data:`TurnDecision`, this test fails and forces a re-think — that
    addition would also require an audit of every ``result.decision ==``
    site downstream (mcp adapter, session-end summariser, etc.).
    """
    assert get_args(TurnDecision) == ("accept", "exhausted", "fallback")
