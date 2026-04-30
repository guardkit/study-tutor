"""Smoke tests for FEAT-PH1-003 (DeepAgents Tutoring Loop with Coach).

These tests are wired to the autobuild smoke gate defined in the
FEAT-PH1-003 feature YAML. Both tests carry ``@pytest.mark.smoke`` and
``@pytest.mark.feat_ph1_003`` so the gate's marker expression
``feat_ph1_003 and smoke`` selects them.

Note on the underscore marker: pytest's ``-m`` expression is a Python
expression, so the hyphenated form ``feat-ph1-003`` would be parsed as
``feat - ph1 - 003`` (three subtractions) and silently match nothing —
the same trip-wire that produced the original FEAT-PH1-002 autobuild
smoke-gate exit-5 (TASK-DSP-008 post-mortem). The marker is therefore
registered and used as ``feat_ph1_003`` and any future gate command
must align to the same form.

Both tests exercise :class:`PlayerCoachOrchestrator.run_turn` end-to-end
with inline stub Player and Coach adapters that satisfy the
:class:`PlayerLike` and :class:`CoachLike` Protocols. No external
service, MCP transport, LLM call, or Graphiti write is involved — the
orchestrator's per-turn instantiation + dependency-injected component
adapters make this trivially mockable.

Coverage rationale: two tests cover the two architecturally
load-bearing seams for the Player-Coach loop:

1. **First-attempt accept** — verdict.decision == "accept" on the
   initial Coach evaluation must short-circuit the revision loop and
   return the Player's first response with attempts=1. This is the
   stable-turn guarantee + the @key-example @smoke @player-coach
   scenario in the .feature file.

2. **Coach-unreachable fallback** — when the Coach raises during
   evaluation, the orchestrator must degrade to the unevaluated-turn
   policy: return the Player's response with decision="fallback",
   verdict=None, flagged_for_review=True, and **no** revision attempts
   (per the @negative @fallback scenario at .feature line 254-260).
   This is the load-bearing isolation guarantee — a Coach failure
   never raises into the caller-facing handler (CC-13).

The bounded-revision-loop, lowest-scoring-on-exhaustion,
per-misconception-dispatch, and DDR-003 session.completed-ordering
behaviours are exercised by unit tests in ``tests/unit/tutoring/``.
Smoke gate intentionally stays narrow: any failure here means the
top-level loop is broken.
"""
from __future__ import annotations

from typing import Any

import pytest

from study_tutor.tutoring import (
    CoachUnavailableError,
    PlayerCoachOrchestrator,
    TurnResult,
)
from study_tutor.tutoring.coach import (
    CoachVerdict,
    CriterionScore,
)

pytestmark = [pytest.mark.smoke, pytest.mark.feat_ph1_003]


class _StubAcceptingCoach:
    """CoachLike stub that always returns an accepting verdict.

    Inline rather than imported from the unit test fixtures because
    smoke tests must be self-contained — the gate runs in environments
    where pytest fixture discovery may not have walked into the unit
    tree. The stub satisfies :class:`CoachLike` structurally (only the
    ``evaluate`` coroutine is consulted by the orchestrator).
    """

    async def evaluate(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
    ) -> CoachVerdict:
        return CoachVerdict(
            weighted_total=0.85,
            decision="accept",
            criterion_scores=[
                CriterionScore(
                    criterion_id="curriculum_accuracy",
                    score=0.85,
                    evidence="smoke-stub",
                ),
            ],
            rubric_feedback=[],
            misconceptions=[],
            reasoning="smoke-test verdict",
        )


class _StubRaisingCoach:
    """CoachLike stub that always raises CoachUnavailableError.

    The orchestrator's documented behaviour for any Coach failure is
    the unevaluated-turn fallback. We use the typed exception here
    rather than a plain ``Exception`` so the test asserts the
    documented preferred shape; the orchestrator also handles plain
    exceptions as a defence-in-depth case (see
    ``test_orchestrator.py::test_coach_unreachable_plain_exception``).
    """

    async def evaluate(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
    ) -> CoachVerdict:
        raise CoachUnavailableError("smoke: simulated Coach unreachable")


class _StubPlayer:
    """PlayerLike stub returning a fixed response.

    ``revise`` is implemented for completeness but the smoke tests
    never reach it — both tests exit via either accept-on-first-attempt
    or Coach-unreachable-fallback, neither of which calls revise.
    """

    def __init__(self, response: str = "smoke player response") -> None:
        self._response = response

    async def respond(
        self,
        *,
        session_state: Any,
        learner_message: str,
    ) -> str:
        return self._response

    async def revise(
        self,
        *,
        session_state: Any,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list,
    ) -> str:  # pragma: no cover - smoke path never revises
        return self._response + " (revised)"


@pytest.mark.asyncio
async def test_smoke_orchestrator_accepts_first_player_response_above_threshold() -> None:
    """Happy path: Coach accepts the first Player response.

    The orchestrator must short-circuit the revision loop on the first
    accepting verdict, return the Player's response verbatim, set
    ``decision == "accept"``, ``attempts == 1``, ``verdict`` populated,
    and leave ``flagged_for_review`` False (latency well under budget
    for an inline-stub run).
    """
    orchestrator = PlayerCoachOrchestrator(
        player=_StubPlayer("Macbeth's ambition is the load-bearing arc."),
        coach=_StubAcceptingCoach(),
        quote_verifier=None,
    )

    result: TurnResult = await orchestrator.run_turn(
        session_state={"text_name": "macbeth"},
        learner_message="Why does Macbeth murder Duncan?",
    )

    assert result.decision == "accept"
    assert result.response == "Macbeth's ambition is the load-bearing arc."
    assert result.attempts == 1
    assert result.verdict is not None
    assert result.verdict.decision == "accept"
    assert result.flagged_for_review is False
    assert result.flag_reason is None


@pytest.mark.asyncio
async def test_smoke_orchestrator_falls_back_when_coach_unreachable() -> None:
    """Fallback path: Coach raises → unevaluated-turn fallback.

    The orchestrator must NOT propagate the Coach failure (CC-13: the
    caller-facing path never sees a Graphiti / Coach failure). It must
    return the Player's response under the documented fallback policy
    with ``decision == "fallback"``, ``verdict is None``,
    ``attempts == 1`` (the first-attempt Player response is what the
    learner sees), ``flagged_for_review == True``, and a
    ``flag_reason`` that names the Coach unavailability so the
    session-end review surfaces it.
    """
    orchestrator = PlayerCoachOrchestrator(
        player=_StubPlayer("Best-effort Player reply under Coach fallback."),
        coach=_StubRaisingCoach(),
        quote_verifier=None,
    )

    result: TurnResult = await orchestrator.run_turn(
        session_state={"text_name": "macbeth"},
        learner_message="What is the significance of the witches?",
    )

    assert result.decision == "fallback"
    assert result.response == "Best-effort Player reply under Coach fallback."
    assert result.verdict is None
    assert result.attempts == 1
    assert result.flagged_for_review is True
    assert result.flag_reason is not None
    assert "coach_unreachable" in result.flag_reason
