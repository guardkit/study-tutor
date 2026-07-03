"""Tests for the Coach handover seam (TASK-PRV-006).

Covers every acceptance criterion in
``tasks/design_approved/TASK-PRV-006-coach-handover-seam.md``:

AC-001 Coach receives the rewritten response, not the original.
AC-002 ``VerifierMetadata`` accompanies the rewritten response and is
       passed to the Coach evaluator.
AC-003 AnalysisMode skip path sets ``retrieval_skipped_reason`` in
       metadata; Coach can suppress ``quote_fidelity`` down-rank.
AC-004 Verifier exception → unannotated response passed to Coach with
       empty ``VerifierMetadata`` and ``verifier_exception=True``;
       failure logged.
AC-005 Per-turn ``verifier_metadata`` is recorded in turn metadata
       (visible at session-end via :class:`TurnResult`).
AC-006 No regression — existing :class:`PlayerCoachOrchestrator` tests
       still pass when ``coach_handover`` is not wired (covered by
       ``tests/unit/tutoring/test_orchestrator.py``; this file adds
       coverage for the *wired* path).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from study_tutor.knowledge.coach_handover import apply_quote_verification
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.tutoring.coach import CoachVerdict, CriterionScore, RubricFeedback
from study_tutor.tutoring.orchestrator import (
    PlayerCoachOrchestrator,
    TurnResult,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _macbeth_corpus() -> list[CorpusChunk]:
    """Tiny Macbeth fixture with one primary chunk for verifier tests."""
    return [
        CorpusChunk(
            text=(
                "Out, damned spot! out, I say! One: two: why, then, "
                "tis time to do't."
            ),
            source_type=SourceType.PRIMARY_TEXT,
            source_path="corpus/primary/macbeth.txt",
            text_name="Macbeth",
            citation_anchor=PlayCitationAnchor(act=5, scene=1, line=35),
            chunk_index=0,
        ),
    ]


def _verdict(
    *,
    decision: str = "accept",
    weighted_total: float = 0.9,
    rubric_feedback: list[RubricFeedback] | None = None,
) -> CoachVerdict:
    return CoachVerdict(
        weighted_total=weighted_total,
        decision=decision,  # type: ignore[arg-type]
        criterion_scores=[
            CriterionScore(criterion_id="c1", score=weighted_total, evidence="e"),
        ],
        rubric_feedback=rubric_feedback or [],
        misconceptions=[],
        reasoning="",
    )


def _make_player(*, responses: list[str], revisions: list[str] | None = None):
    player = MagicMock()
    player.respond = AsyncMock(side_effect=list(responses))
    player.revise = AsyncMock(side_effect=list(revisions or []))
    return player


def _make_coach(*, verdicts: list[CoachVerdict]):
    coach = MagicMock()
    coach.evaluate = AsyncMock(side_effect=list(verdicts))
    return coach


# ---------------------------------------------------------------------------
# apply_quote_verification — unit tests (AC-001, AC-002, AC-003, AC-004)
# ---------------------------------------------------------------------------


def test_apply_quote_verification_returns_rewritten_response_and_metadata() -> None:
    """AC-001 / AC-002: returns ``(rewritten_response, VerifierMetadata)`` tuple."""
    response = (
        'Lady Macbeth cries "Out, damned spot! out, I say! One: two: why, '
        'then, tis time to do" in her sleep.'
    )
    rewritten, metadata = apply_quote_verification(
        response, _macbeth_corpus(), session_text_name="Macbeth"
    )

    assert isinstance(rewritten, str)
    assert isinstance(metadata, VerifierMetadata)
    # The verifier annotates the verbatim primary match with a citation.
    assert "(5.1.35)" in rewritten
    # Exactly one primary match recorded.
    assert len(metadata.primary_matches) == 1
    assert metadata.primary_matches[0].text_name == "Macbeth"
    # No exception flag on the success path.
    assert metadata.verifier_exception is False


def test_apply_quote_verification_forwards_retrieval_skipped_reason() -> None:
    """AC-003: ``retrieval_skipped_reason`` is forwarded into metadata."""
    skip_reason = "analysis_mode:no_primary_text"
    rewritten, metadata = apply_quote_verification(
        "Plain text with no quoted spans at all.",
        corpus_chunks=[],
        session_text_name="An Inspector Calls",
        retrieval_skipped_reason=skip_reason,
    )

    assert metadata.retrieval_skipped_reason == skip_reason
    # Coach uses verifier_exception=False + retrieval_skipped_reason set
    # to suppress the down-rank without treating the turn as a verifier
    # failure.
    assert metadata.verifier_exception is False


def test_apply_quote_verification_returns_original_on_verifier_exception(
    monkeypatch, caplog
) -> None:
    """AC-004: verifier exception → unannotated response + verifier_exception flag.

    The Coach must still receive *something* — silently failing the turn
    on a verifier hiccup is a worse outcome than continuing with an
    unannotated reply (per the implementation note in the task spec).
    """
    original_response = 'She says "I shall never wash my hands again."'

    def _raises(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("simulated verifier corruption")

    # Patch the underlying verifier inside the handover module so the
    # try/except branch fires.
    monkeypatch.setattr(
        "study_tutor.knowledge.coach_handover.verify_quotes",
        _raises,
    )

    with caplog.at_level("WARNING"):
        rewritten, metadata = apply_quote_verification(
            original_response,
            _macbeth_corpus(),
            session_text_name="Macbeth",
            retrieval_skipped_reason=None,
        )

    # Original response, unchanged. The Coach evaluates as if no
    # verifier ran at all.
    assert rewritten == original_response
    # Metadata is empty + carries the exception flag.
    assert metadata.verifier_exception is True
    assert metadata.primary_matches == []
    assert metadata.no_match_strips == []
    assert metadata.retrieval_skipped_reason is None
    # Failure was logged for session-end review (per AC).
    assert any(
        "coach_handover.verifier_exception" in rec.message
        or rec.event == "coach_handover_verifier_exception"  # type: ignore[attr-defined]
        for rec in caplog.records
        if hasattr(rec, "event") or "coach_handover" in rec.message
    )


def test_apply_quote_verification_preserves_skip_reason_on_exception(
    monkeypatch,
) -> None:
    """Verifier exception still preserves the retrieval_skipped_reason hint.

    The Coach uses *either* ``verifier_exception`` *or*
    ``retrieval_skipped_reason`` to suppress quote_fidelity down-rank,
    so dropping the skip reason on the exception path would degrade
    Coach behaviour for AnalysisMode+verifier-fault turns. We forward
    both signals.
    """

    def _raises(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "study_tutor.knowledge.coach_handover.verify_quotes",
        _raises,
    )

    _, metadata = apply_quote_verification(
        "any response",
        corpus_chunks=[],
        session_text_name="Macbeth",
        retrieval_skipped_reason="analysis_mode:embedder_timeout",
    )

    assert metadata.verifier_exception is True
    assert metadata.retrieval_skipped_reason == "analysis_mode:embedder_timeout"


# ---------------------------------------------------------------------------
# Orchestrator integration — Coach receives rewritten + metadata (AC-001/002/005)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_passes_rewritten_response_to_coach() -> None:
    """AC-001: Coach.evaluate receives the rewritten Player response.

    Seam test mirroring the contract in the task spec: the orchestrator
    must route the verifier-rewritten response to the Coach, not the
    raw Player output containing fabricated quotes.
    """
    original_response = (
        'Lady Macbeth cries "Out, damned spot! out, I say! One: two: why, '
        'then, tis time to do" and "this fabricated quote does not exist".'
    )

    corpus = _macbeth_corpus()

    def handover(
        response: str, learner_message: str, session_state: Any
    ) -> tuple[str, VerifierMetadata]:
        return apply_quote_verification(
            response, corpus, session_text_name="Macbeth"
        )

    accept = _verdict(decision="accept", weighted_total=0.9)
    player = _make_player(responses=[original_response])
    coach = _make_coach(verdicts=[accept])

    orch = PlayerCoachOrchestrator(
        player=player, coach=coach, coach_handover=handover
    )
    result = await orch.run_turn(
        session_state={"sid": "s1"}, learner_message="discuss the spot"
    )

    # AC-001: the Coach received the *rewritten* response, not the raw one.
    coach_kwargs = coach.evaluate.call_args.kwargs
    rewritten_passed_to_coach = coach_kwargs["player_response"]
    assert rewritten_passed_to_coach != original_response
    assert "(5.1.35)" in rewritten_passed_to_coach
    # The fabricated quote ("this fabricated quote does not exist") must
    # have been stripped of its quote marks before reaching the Coach.
    assert (
        '"this fabricated quote does not exist"'
        not in rewritten_passed_to_coach
    )

    # AC-002: VerifierMetadata accompanies the rewritten response.
    assert "verifier_metadata" in coach_kwargs
    metadata = coach_kwargs["verifier_metadata"]
    assert isinstance(metadata, VerifierMetadata)
    assert len(metadata.primary_matches) == 1
    assert len(metadata.no_match_strips) == 1
    assert metadata.verifier_exception is False

    # AC-005: TurnResult exposes verifier_metadata for session-end summaries.
    assert isinstance(result, TurnResult)
    assert result.verifier_metadata is metadata
    assert result.response == rewritten_passed_to_coach


@pytest.mark.asyncio
async def test_orchestrator_forwards_retrieval_skipped_reason_in_analysis_mode() -> None:
    """AC-003: AnalysisMode skip → retrieval_skipped_reason flows to Coach metadata.

    When retrieval is skipped (no primary corpus, AO3-only, embedder
    timeout), the verifier sees an empty corpus and can only produce
    NoMatchStrip entries. The retrieval_skipped_reason must reach the
    Coach so it suppresses the quote_fidelity down-rank for the turn.
    """
    raw_response = "An Inspector Calls explores collective responsibility."

    def handover(
        response: str, learner_message: str, session_state: Any
    ) -> tuple[str, VerifierMetadata]:
        return apply_quote_verification(
            response,
            corpus_chunks=[],  # AnalysisMode: no primary corpus
            session_text_name=session_state["text_name"],
            retrieval_skipped_reason="analysis_mode:no_primary_text",
        )

    accept = _verdict(decision="accept", weighted_total=0.85)
    player = _make_player(responses=[raw_response])
    coach = _make_coach(verdicts=[accept])

    orch = PlayerCoachOrchestrator(
        player=player, coach=coach, coach_handover=handover
    )
    result = await orch.run_turn(
        session_state={"text_name": "An Inspector Calls"},
        learner_message="What is the play about?",
    )

    coach_kwargs = coach.evaluate.call_args.kwargs
    metadata = coach_kwargs["verifier_metadata"]
    assert metadata.retrieval_skipped_reason == "analysis_mode:no_primary_text"
    assert metadata.verifier_exception is False
    # The raw response (no quoted spans) is unchanged by the verifier.
    assert coach_kwargs["player_response"] == raw_response

    # AC-005: surfaced into TurnResult for session-end review.
    assert result.verifier_metadata is metadata
    assert result.verifier_metadata.retrieval_skipped_reason == (
        "analysis_mode:no_primary_text"
    )


# ---------------------------------------------------------------------------
# Failure-injection: orchestrator survives verifier exceptions (AC-004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_continues_when_verifier_raises(monkeypatch) -> None:
    """AC-004: verifier exception → orchestrator passes original to Coach with empty metadata + flag.

    The orchestrator's contract is that the Coach always evaluates
    *something*; a verifier hiccup must not crash the turn.
    """
    raw_response = 'A reply with "some quoted span here please"'

    def handover_using_real_apply(
        response: str, learner_message: str, session_state: Any
    ) -> tuple[str, VerifierMetadata]:
        return apply_quote_verification(
            response, _macbeth_corpus(), session_text_name="Macbeth"
        )

    # Inject a failure into the underlying verifier so the handover's
    # fallback branch fires.
    def _raises(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("simulated verifier corruption")

    monkeypatch.setattr(
        "study_tutor.knowledge.coach_handover.verify_quotes", _raises
    )

    accept = _verdict(decision="accept", weighted_total=0.8)
    player = _make_player(responses=[raw_response])
    coach = _make_coach(verdicts=[accept])

    orch = PlayerCoachOrchestrator(
        player=player, coach=coach, coach_handover=handover_using_real_apply
    )
    result = await orch.run_turn(
        session_state={}, learner_message="any prompt"
    )

    # The Coach received the *original* (unannotated) response and
    # metadata with the exception flag set.
    coach_kwargs = coach.evaluate.call_args.kwargs
    assert coach_kwargs["player_response"] == raw_response
    metadata = coach_kwargs["verifier_metadata"]
    assert metadata.verifier_exception is True
    assert metadata.primary_matches == []

    # The turn still completed successfully.
    assert result.decision == "accept"
    assert result.response == raw_response
    assert result.verifier_metadata is metadata


# ---------------------------------------------------------------------------
# AC-006 — No regression: orchestrator without coach_handover is pass-through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_without_handover_does_not_pass_verifier_metadata() -> None:
    """When ``coach_handover`` is not wired, behaviour matches FEAT-PH1-003.

    No ``verifier_metadata`` kwarg is added to the Coach.evaluate call
    and ``TurnResult.verifier_metadata`` is ``None``. This guarantees
    legacy callers (existing FEAT-PH1-003 tests, MCP wiring before
    PRV-006 lands) see no behavioural change.
    """
    raw_response = "Plain reply."
    accept = _verdict(decision="accept", weighted_total=0.9)
    player = _make_player(responses=[raw_response])
    coach = _make_coach(verdicts=[accept])

    orch = PlayerCoachOrchestrator(player=player, coach=coach)
    result = await orch.run_turn(
        session_state={}, learner_message="hi"
    )

    coach_kwargs = coach.evaluate.call_args.kwargs
    assert "verifier_metadata" not in coach_kwargs
    assert coach_kwargs["player_response"] == raw_response
    assert result.verifier_metadata is None
    assert result.response == raw_response


@pytest.mark.asyncio
async def test_orchestrator_runs_handover_on_each_revision() -> None:
    """Every Player attempt gets verified — revisions can introduce new quotes.

    Confirms that the per-attempt record's verifier_metadata reflects
    the *attempt*'s output (not the first attempt's), so when the
    revision loop releases the lowest-scoring attempt on exhaustion
    the released TurnResult.verifier_metadata matches that attempt.
    """
    revisions_made: list[str] = []

    def handover(
        response: str, learner_message: str, session_state: Any
    ) -> tuple[str, VerifierMetadata]:
        # Tag each metadata with the revision count so the test can
        # tell which attempt's metadata was preserved.
        revisions_made.append(response)
        meta = VerifierMetadata(
            retrieval_skipped_reason=f"attempt:{len(revisions_made)}"
        )
        return (response + " (verified)", meta)

    revise_v1 = _verdict(
        decision="revise",
        weighted_total=0.2,
        rubric_feedback=[
            RubricFeedback(criterion_id="c1", suggested_focus="x", target_score=0.8)
        ],
    )
    accept_v2 = _verdict(decision="accept", weighted_total=0.95)
    player = _make_player(
        responses=["raw_first"],
        revisions=["raw_revised"],
    )
    coach = _make_coach(verdicts=[revise_v1, accept_v2])

    orch = PlayerCoachOrchestrator(
        player=player, coach=coach, coach_handover=handover
    )
    result = await orch.run_turn(session_state={}, learner_message="q")

    # Handover ran twice — once for the initial response, once for the
    # revision.
    assert len(revisions_made) == 2
    assert revisions_made == ["raw_first", "raw_revised"]
    # The released TurnResult carries the *second* (revision) metadata,
    # matching the accepted attempt.
    assert result.decision == "accept"
    assert result.response == "raw_revised (verified)"
    assert result.verifier_metadata is not None
    assert result.verifier_metadata.retrieval_skipped_reason == "attempt:2"
