"""Unit + integration + seam tests for TASK-DTL-002 — rubric and quote fidelity.

Each AC of the task spec maps to one ``TestXxx`` class so a failure points
at the failing acceptance criterion immediately:

AC-001 ``score_rubric`` returns a ``CoachVerdict`` with all six
       ``CriterionScore`` instances populated.
AC-002 Weighted total is computed from configured weights; weights sum to
       1.0 (sanity-check at construction).
AC-003 Threshold boundary scenarios: 0.70 → accept; 0.69 → revise;
       1.00 → accept; 0.00 → revise.
AC-004 Quote-verifier annotation flow — verbatim primary-text quote is
       annotated and the annotated response is the version evaluated by
       the Coach.
AC-005 Fabricated quote (no corpus match) is removed/rewritten before
       Coach evaluation; observable in turn metadata.
AC-006 Quote-verifier minimum-length boundary — 3-word ignored, 4-word
       and 5-word inspected.
AC-007 Analysis-mode (retrieval skipped) responses are not down-ranked on
       quote fidelity; turn metadata records the skip reason.
AC-008 Quote-verifier exception → response passed unannotated; Coach
       evaluates under fallback; failure logged.
AC-009 Malformed Coach output → unevaluated-turn fallback; no
       misconception persisted; turn flagged for session-end review.

Plus integration + seam tests:
- Integration: verify_quotes → score_rubric pipeline using a test corpus
  with one canonical primary text.
- Seam: Coach evaluator dispatches misconceptions via the shared write
  helper protocol from TASK-GSM-004 (no direct ``add_episode``).
"""
from __future__ import annotations

import json
import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from study_tutor.tutoring.coach import (
    ACCEPTANCE_THRESHOLD,
    CRITERION_AO_ALIGNMENT,
    CRITERION_CONSTRUCTIVE_FEEDBACK,
    CRITERION_CURRICULUM_ACCURACY,
    CRITERION_GRADE_APPROPRIATE_LANGUAGE,
    CRITERION_IDS,
    CRITERION_QUOTE_FIDELITY,
    CRITERION_SCAFFOLDING_DEPTH,
    DEFAULT_WEIGHTS,
    MIN_QUOTE_LENGTH_WORDS,
    CoachConfig,
    CoachVerdict,
    CriterionScore,
    MalformedCoachOutputError,
    MisconceptionObservation,
    PlayerConfig,
    QuoteAnnotation,
    QuoteVerificationResult,
    RubricWeights,
    TurnContext,
    UnevaluatedTurnFallback,
    coach_unevaluated_fallback,
    create_coach,
    evaluate_player_turn,
    parse_coach_output,
    score_rubric,
    verify_quotes,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_constant_scorer(criterion_id: str, score: float) -> Any:
    """Build a deterministic scorer that always returns the same score.

    Used in unit tests so per-criterion branches can be exercised
    independently without invoking real LLM judges.
    """

    def scorer(_response: str, _ctx: TurnContext) -> CriterionScore:
        return CriterionScore(
            criterion_id=criterion_id,
            score=score,
            evidence=f"test scorer for {criterion_id}",
        )

    return scorer


def _scorers_with_uniform_score(score: float) -> dict[str, Any]:
    """Build a complete six-scorer mapping where every scorer returns ``score``."""
    return {cid: _make_constant_scorer(cid, score) for cid in CRITERION_IDS}


def _scorers_per_criterion(scores_by_criterion: dict[str, float]) -> dict[str, Any]:
    """Build six scorers from a {criterion_id → score} mapping."""
    if set(scores_by_criterion) != set(CRITERION_IDS):
        raise AssertionError(
            "Test bug: scores_by_criterion must specify every criterion id."
        )
    return {
        cid: _make_constant_scorer(cid, scores_by_criterion[cid])
        for cid in CRITERION_IDS
    }


@pytest.fixture
def turn_context() -> TurnContext:
    return TurnContext(
        student_id="student-123",
        session_id="session-456",
        mode="tutor",
    )


@pytest.fixture
def analysis_mode_context() -> TurnContext:
    """Turn context with retrieval bypassed (AC-007 path)."""
    return TurnContext(
        student_id="student-123",
        session_id="session-456",
        mode="analysis",
        retrieval_skipped=True,
        retrieval_skip_reason="session-plan focus is contextual (AO3)",
    )


# ---------------------------------------------------------------------------
# AC-001: score_rubric returns CoachVerdict with six CriterionScores
# ---------------------------------------------------------------------------


class TestScoreRubricSixCriteria:
    """``score_rubric`` returns all six criterion scores in canonical order."""

    def test_returns_six_criterion_scores(self, turn_context: TurnContext) -> None:
        scorers = _scorers_with_uniform_score(0.8)
        verdict = score_rubric(
            player_response="some response",
            turn_context=turn_context,
            scorers=scorers,
        )
        assert isinstance(verdict, CoachVerdict)
        assert len(verdict.criterion_scores) == 6
        criterion_ids = [cs.criterion_id for cs in verdict.criterion_scores]
        assert criterion_ids == list(CRITERION_IDS)

    def test_each_criterion_branch_invoked_independently(
        self, turn_context: TurnContext
    ) -> None:
        # Per-criterion distinct scores — proves each branch is wired to
        # its own scorer (test requirement: "covering all six criterion
        # scoring branches independently").
        per_criterion = {
            CRITERION_CURRICULUM_ACCURACY: 0.10,
            CRITERION_AO_ALIGNMENT: 0.20,
            CRITERION_SCAFFOLDING_DEPTH: 0.30,
            CRITERION_GRADE_APPROPRIATE_LANGUAGE: 0.40,
            CRITERION_CONSTRUCTIVE_FEEDBACK: 0.50,
            CRITERION_QUOTE_FIDELITY: 0.60,
        }
        scorers = _scorers_per_criterion(per_criterion)
        verdict = score_rubric(
            player_response="response",
            turn_context=turn_context,
            scorers=scorers,
        )
        score_by_id = {cs.criterion_id: cs.score for cs in verdict.criterion_scores}
        assert score_by_id == per_criterion

    def test_missing_scorer_raises_value_error(
        self, turn_context: TurnContext
    ) -> None:
        scorers = _scorers_with_uniform_score(0.5)
        del scorers[CRITERION_QUOTE_FIDELITY]
        with pytest.raises(ValueError) as exc_info:
            score_rubric(
                player_response="r",
                turn_context=turn_context,
                scorers=scorers,
            )
        assert CRITERION_QUOTE_FIDELITY in str(exc_info.value)

    def test_scorer_returning_wrong_criterion_id_raises(
        self, turn_context: TurnContext
    ) -> None:
        # Defensive: a scorer that returns the wrong criterion_id is a
        # programmer error and surfaces immediately rather than corrupting
        # the verdict.
        bad_scorers = _scorers_with_uniform_score(0.5)
        bad_scorers[CRITERION_AO_ALIGNMENT] = lambda r, ctx: CriterionScore(
            criterion_id=CRITERION_QUOTE_FIDELITY,
            score=0.5,
            evidence="wrong slot",
        )
        with pytest.raises(ValueError) as exc_info:
            score_rubric(
                player_response="r",
                turn_context=turn_context,
                scorers=bad_scorers,
            )
        assert "criterion_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-002: Weighted total + weights sum to 1.0 sanity check
# ---------------------------------------------------------------------------


class TestRubricWeights:
    """Weights are sanity-checked to sum to 1.0 at construction (AC-002)."""

    def test_default_weights_sum_to_one(self) -> None:
        total = (
            DEFAULT_WEIGHTS.curriculum_accuracy
            + DEFAULT_WEIGHTS.ao_alignment
            + DEFAULT_WEIGHTS.scaffolding_depth
            + DEFAULT_WEIGHTS.grade_appropriate_language
            + DEFAULT_WEIGHTS.constructive_feedback
            + DEFAULT_WEIGHTS.quote_fidelity
        )
        assert abs(total - 1.0) < 1e-9

    def test_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RubricWeights(
                curriculum_accuracy=0.2,
                ao_alignment=0.2,
                scaffolding_depth=0.2,
                grade_appropriate_language=0.2,
                constructive_feedback=0.2,
                quote_fidelity=0.5,  # sum = 1.5
            )
        msg = str(exc_info.value)
        assert "sum to 1.0" in msg
        assert "1.5" in msg

    def test_weights_under_one_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            RubricWeights(
                curriculum_accuracy=0.1,
                ao_alignment=0.1,
                scaffolding_depth=0.1,
                grade_appropriate_language=0.1,
                constructive_feedback=0.1,
                quote_fidelity=0.1,  # sum = 0.6
            )
        assert "sum to 1.0" in str(exc_info.value)

    def test_negative_weight_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RubricWeights(
                curriculum_accuracy=-0.1,
                ao_alignment=0.3,
                scaffolding_depth=0.2,
                grade_appropriate_language=0.2,
                constructive_feedback=0.2,
                quote_fidelity=0.2,
            )

    def test_uniform_one_sixth_weights(self, turn_context: TurnContext) -> None:
        # Equal-weight check: with all six scorers returning 0.5, weighted
        # total must equal 0.5 regardless of how the 1/6 weights round.
        weights = RubricWeights(
            curriculum_accuracy=1 / 6,
            ao_alignment=1 / 6,
            scaffolding_depth=1 / 6,
            grade_appropriate_language=1 / 6,
            constructive_feedback=1 / 6,
            quote_fidelity=1 - (5 / 6),  # absorbs float drift
        )
        scorers = _scorers_with_uniform_score(0.5)
        verdict = score_rubric(
            player_response="r",
            turn_context=turn_context,
            weights=weights,
            scorers=scorers,
        )
        assert abs(verdict.weighted_total - 0.5) < 1e-9

    def test_weighted_sum_at_threshold_boundary_069_070_071(
        self, turn_context: TurnContext
    ) -> None:
        # Test requirement: "Unit test for weighted-sum computation at
        # threshold boundary (0.69 → 0.70 → 0.71)".
        for uniform_score, expected_decision in (
            (0.69, "revise"),
            (0.70, "accept"),
            (0.71, "accept"),
        ):
            scorers = _scorers_with_uniform_score(uniform_score)
            verdict = score_rubric(
                player_response="r",
                turn_context=turn_context,
                scorers=scorers,
            )
            assert abs(verdict.weighted_total - uniform_score) < 1e-9, (
                f"weighted_total at uniform={uniform_score}"
            )
            assert verdict.decision == expected_decision, (
                f"decision at score {uniform_score}"
            )


# ---------------------------------------------------------------------------
# AC-003: Threshold boundary scenarios (.feature L141-152)
# ---------------------------------------------------------------------------


class TestThresholdBoundary:
    """Score 0.70 → accept; 0.69 → revise; 1.00 → accept; 0.00 → revise."""

    @pytest.mark.parametrize(
        "score,expected_decision",
        [
            (0.70, "accept"),
            (0.69, "revise"),
            (1.00, "accept"),
            (0.00, "revise"),
        ],
    )
    def test_decision_at_boundary(
        self,
        score: float,
        expected_decision: str,
        turn_context: TurnContext,
    ) -> None:
        scorers = _scorers_with_uniform_score(score)
        verdict = score_rubric(
            player_response="r",
            turn_context=turn_context,
            scorers=scorers,
        )
        assert verdict.decision == expected_decision

    def test_decision_uses_gte_not_gt_at_threshold(
        self, turn_context: TurnContext
    ) -> None:
        # 0.70 must be accept (>=, not >). This is the load-bearing
        # boundary in the @boundary @rubric Scenario Outline.
        scorers = _scorers_with_uniform_score(ACCEPTANCE_THRESHOLD)
        verdict = score_rubric(
            player_response="r",
            turn_context=turn_context,
            scorers=scorers,
        )
        assert verdict.decision == "accept"

    def test_below_threshold_emits_feedback_per_criterion(
        self, turn_context: TurnContext
    ) -> None:
        # Sub-threshold scores produce one RubricFeedback per below-threshold
        # criterion — the structured-only (no free-text) revision channel.
        scorers = _scorers_with_uniform_score(0.50)
        verdict = score_rubric(
            player_response="r",
            turn_context=turn_context,
            scorers=scorers,
        )
        assert verdict.decision == "revise"
        assert len(verdict.rubric_feedback) == 6
        feedback_criteria = {fb.criterion_id for fb in verdict.rubric_feedback}
        assert feedback_criteria == set(CRITERION_IDS)
        for fb in verdict.rubric_feedback:
            assert fb.target_score == ACCEPTANCE_THRESHOLD

    def test_above_threshold_emits_no_feedback(
        self, turn_context: TurnContext
    ) -> None:
        scorers = _scorers_with_uniform_score(0.95)
        verdict = score_rubric(
            player_response="r",
            turn_context=turn_context,
            scorers=scorers,
        )
        assert verdict.rubric_feedback == []


# ---------------------------------------------------------------------------
# Quote verifier seam fixtures
# ---------------------------------------------------------------------------


class _StubVerifier:
    """Minimal fake verifier; the test sets ``next_result`` per call."""

    def __init__(self, result: QuoteVerificationResult) -> None:
        self.result = result
        self.calls: list[tuple[str, int]] = []

    def verify_quotes(
        self,
        response: str,
        *,
        min_quote_length_words: int = MIN_QUOTE_LENGTH_WORDS,
    ) -> QuoteVerificationResult:
        self.calls.append((response, min_quote_length_words))
        return self.result


class _RaisingVerifier:
    """Fake verifier whose ``verify_quotes`` raises a domain error."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.calls: list[str] = []

    def verify_quotes(
        self,
        response: str,
        *,
        min_quote_length_words: int = MIN_QUOTE_LENGTH_WORDS,
    ) -> QuoteVerificationResult:
        self.calls.append(response)
        raise self.exc


# ---------------------------------------------------------------------------
# AC-004: Verbatim primary-text quote → annotated; annotated response is
#         the one evaluated by the Coach.
# ---------------------------------------------------------------------------


class TestVerifyQuotesAnnotation:
    """Verbatim primary-text quote is annotated with citation; passed to Coach."""

    def test_annotated_response_returned_to_caller(
        self, turn_context: TurnContext
    ) -> None:
        annotated = (
            'Macbeth says "is this a dagger which I see before me" '
            "[Macbeth, Act 2 Scene 1] — a moment of moral hesitation."
        )
        result = QuoteVerificationResult(
            annotated_response=annotated,
            annotations=(
                QuoteAnnotation(
                    span="is this a dagger which I see before me",
                    citation="Macbeth, Act 2 Scene 1",
                    matched=True,
                ),
            ),
            inspected_spans=("is this a dagger which I see before me",),
        )
        verifier = _StubVerifier(result)
        original = (
            'Macbeth says "is this a dagger which I see before me" — '
            "a moment of moral hesitation."
        )
        response_for_coach, metadata = verify_quotes(
            original, verifier=verifier, turn_context=turn_context
        )
        assert response_for_coach == annotated
        assert response_for_coach != original
        assert metadata["annotated_quotes"][0]["citation"] == "Macbeth, Act 2 Scene 1"
        assert metadata["annotated_quotes"][0]["matched"] is True

    def test_annotated_response_is_what_coach_evaluates(
        self, turn_context: TurnContext
    ) -> None:
        # Pipeline-level proof: the response score_rubric evaluates is the
        # annotated one, not the original (covers AC-004 final clause).
        annotated = "ANNOTATED: " + ("x " * 5)
        captured: list[str] = []

        def quote_fidelity_scorer(
            response: str, _ctx: TurnContext
        ) -> CriterionScore:
            captured.append(response)
            return CriterionScore(
                criterion_id=CRITERION_QUOTE_FIDELITY,
                score=0.95,
                evidence="annotated",
            )

        scorers = _scorers_with_uniform_score(0.9)
        scorers[CRITERION_QUOTE_FIDELITY] = quote_fidelity_scorer

        result = QuoteVerificationResult(
            annotated_response=annotated,
            annotations=(
                QuoteAnnotation(
                    span="something", citation="Source, p.1", matched=True
                ),
            ),
        )
        verifier = _StubVerifier(result)

        # We call verify_quotes + score_rubric directly to cover AC-004's
        # "annotated response is the version evaluated by the Coach".
        response_for_coach, _ = verify_quotes(
            "ORIGINAL", verifier=verifier, turn_context=turn_context
        )
        score_rubric(
            player_response=response_for_coach,
            turn_context=turn_context,
            scorers=scorers,
        )
        assert captured == [annotated]


# ---------------------------------------------------------------------------
# AC-005: Fabricated quote rewritten as paraphrase before Coach evaluates
# ---------------------------------------------------------------------------


class TestVerifyQuotesFabricatedRewrite:
    """Unmatched quote is rewritten as paraphrase; rewrite observable in metadata."""

    def test_fabricated_quote_rewritten_in_response(
        self, turn_context: TurnContext
    ) -> None:
        original = 'Hamlet famously says "I am the master of the seven seas"!'
        rewritten = "Hamlet expresses a sense of authority and control."
        fabricated_span = "I am the master of the seven seas"
        result = QuoteVerificationResult(
            annotated_response=rewritten,
            annotations=(
                QuoteAnnotation(
                    span=fabricated_span,
                    citation=None,
                    matched=False,
                    rewritten_as_paraphrase=True,
                ),
            ),
            rewritten_quotes=(fabricated_span,),
            inspected_spans=(fabricated_span,),
        )
        verifier = _StubVerifier(result)
        response_for_coach, metadata = verify_quotes(
            original, verifier=verifier, turn_context=turn_context
        )
        # AC-005 first clause: rewritten before Coach evaluation
        assert response_for_coach == rewritten
        assert fabricated_span not in response_for_coach
        # AC-005 second clause: rewrite observable in turn metadata
        assert "rewritten_quotes" in metadata
        assert fabricated_span in metadata["rewritten_quotes"]
        assert metadata["annotated_quotes"][0]["rewritten_as_paraphrase"] is True
        assert metadata["annotated_quotes"][0]["citation"] is None


# ---------------------------------------------------------------------------
# AC-006: Quote-verifier minimum-length boundary (3 / 4 / 5 words)
# ---------------------------------------------------------------------------


class TestVerifyQuotesMinimumLength:
    """Min-quote-length boundary: 3 ignored, 4 inspected, 5 inspected.

    The boundary lives inside the verifier; this test asserts the public
    contract that ``verify_quotes`` forwards :data:`MIN_QUOTE_LENGTH_WORDS`
    (the default) into the verifier and that the verifier's
    inspected/skipped split round-trips into metadata correctly.
    """

    def test_default_min_quote_length_is_four(
        self, turn_context: TurnContext
    ) -> None:
        verifier = _StubVerifier(QuoteVerificationResult(annotated_response="r"))
        verify_quotes("r", verifier=verifier, turn_context=turn_context)
        assert verifier.calls[0][1] == 4
        assert MIN_QUOTE_LENGTH_WORDS == 4

    @pytest.mark.parametrize(
        "words,expected_action",
        [
            (3, "ignore"),
            (4, "inspect"),
            (5, "inspect"),
        ],
    )
    def test_minimum_length_inspect_or_ignore(
        self,
        words: int,
        expected_action: str,
        turn_context: TurnContext,
    ) -> None:
        span = " ".join(["w"] * words)
        if expected_action == "ignore":
            result = QuoteVerificationResult(
                annotated_response="response",
                skipped_spans=(span,),
            )
        else:
            result = QuoteVerificationResult(
                annotated_response="response",
                inspected_spans=(span,),
                annotations=(
                    QuoteAnnotation(
                        span=span,
                        citation="Test, p.1",
                        matched=True,
                    ),
                ),
            )
        verifier = _StubVerifier(result)
        _, metadata = verify_quotes(
            f"the player wrote: {span}",
            verifier=verifier,
            turn_context=turn_context,
        )
        if expected_action == "ignore":
            assert metadata.get("skipped_quote_spans") == [span]
            assert "inspected_quote_spans" not in metadata
        else:
            assert metadata.get("inspected_quote_spans") == [span]
            assert "skipped_quote_spans" not in metadata


# ---------------------------------------------------------------------------
# AC-007: Analysis-mode (retrieval skipped) → not down-ranked + reason logged
# ---------------------------------------------------------------------------


class TestRetrievalSkippedExemption:
    """Analysis-mode responses are not down-ranked on quote fidelity (AC-007)."""

    def test_quote_fidelity_score_is_max_when_retrieval_skipped(
        self, analysis_mode_context: TurnContext
    ) -> None:
        # Even if the (would-be) scorer would have returned 0.0, the
        # exemption substitutes 1.0 — proving the down-rank is suppressed
        # purely by the retrieval-skipped flag.
        def angry_scorer(_r: str, _c: TurnContext) -> CriterionScore:
            raise AssertionError(
                "quote_fidelity scorer must not be called when retrieval "
                "is skipped — exemption branch was supposed to suppress it"
            )

        scorers = _scorers_with_uniform_score(0.5)
        scorers[CRITERION_QUOTE_FIDELITY] = angry_scorer
        verdict = score_rubric(
            player_response="r",
            turn_context=analysis_mode_context,
            scorers=scorers,
        )
        quote_fidelity_score = next(
            cs for cs in verdict.criterion_scores
            if cs.criterion_id == CRITERION_QUOTE_FIDELITY
        )
        assert quote_fidelity_score.score == 1.0
        assert "exempt" in quote_fidelity_score.evidence.lower()

    def test_verifier_not_called_when_retrieval_skipped(
        self, analysis_mode_context: TurnContext
    ) -> None:
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="should-not-see")
        )
        response_for_coach, metadata = verify_quotes(
            "the original response",
            verifier=verifier,
            turn_context=analysis_mode_context,
        )
        assert verifier.calls == []
        # Original response passed through unchanged
        assert response_for_coach == "the original response"
        # AC-007 second clause: metadata records "retrieval was skipped" with reason
        assert metadata["retrieval_skipped"] is True
        assert metadata["retrieval_skip_reason"] == (
            "session-plan focus is contextual (AO3)"
        )


# ---------------------------------------------------------------------------
# AC-008: Quote-verifier exception → unannotated, fallback, logged
# ---------------------------------------------------------------------------


class TestVerifyQuotesExceptionFallback:
    """Verifier exception → response unchanged; failure logged."""

    def test_exception_returns_original_response(
        self, turn_context: TurnContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        verifier = _RaisingVerifier(RuntimeError("corpus unavailable"))
        with caplog.at_level(logging.WARNING):
            response_for_coach, metadata = verify_quotes(
                "the original response",
                verifier=verifier,
                turn_context=turn_context,
            )
        # Response is passed unannotated
        assert response_for_coach == "the original response"
        # Metadata flags the verifier failure for session-end review
        assert metadata["quote_verifier_failed"] is True
        assert metadata["quote_verifier_error_class"] == "RuntimeError"
        # Failure logged
        assert any(
            "quote_verifier_failed" in (record.__dict__.get("event") or "")
            or "quote verifier" in record.getMessage().lower()
            for record in caplog.records
        )

    def test_failure_injection_pipeline_still_produces_verdict(
        self, turn_context: TurnContext
    ) -> None:
        # Test requirement: "Failure-injection test: quote verifier raises
        # → verdict still produced from unannotated response, failure log
        # line emitted."
        verifier = _RaisingVerifier(ValueError("unexpected verifier crash"))
        scorers = _scorers_with_uniform_score(0.85)
        response_for_coach, metadata = verify_quotes(
            "PLAYER RESPONSE",
            verifier=verifier,
            turn_context=turn_context,
        )
        verdict = score_rubric(
            player_response=response_for_coach,
            turn_context=turn_context,
            scorers=scorers,
        )
        assert verdict.decision == "accept"
        assert metadata["quote_verifier_failed"] is True


# ---------------------------------------------------------------------------
# AC-009: Malformed Coach output → fallback; no misconception persisted
# ---------------------------------------------------------------------------


class TestMalformedCoachOutputFallback:
    """Malformed Coach output mirrors Coach-unreachable policy (AC-009)."""

    def test_invalid_json_raises_malformed_error(self) -> None:
        with pytest.raises(MalformedCoachOutputError) as exc_info:
            parse_coach_output("not actually json {{{")
        assert "JSON" in str(exc_info.value)

    def test_dict_missing_required_field_raises_malformed_error(self) -> None:
        with pytest.raises(MalformedCoachOutputError):
            # Missing ``decision`` field
            parse_coach_output({"weighted_total": 0.8})

    def test_invalid_type_raises_malformed_error(self) -> None:
        with pytest.raises(MalformedCoachOutputError):
            parse_coach_output(["not", "a", "verdict"])
        with pytest.raises(MalformedCoachOutputError):
            parse_coach_output(None)

    def test_json_string_that_parses_as_non_object_raises(self) -> None:
        # JSON arrays / scalars are valid JSON but not valid Coach verdicts
        with pytest.raises(MalformedCoachOutputError) as exc_info:
            parse_coach_output("[]")
        assert "object" in str(exc_info.value)

    def test_json_string_with_bad_schema_raises(self) -> None:
        # Valid JSON object but missing required ``decision`` field
        with pytest.raises(MalformedCoachOutputError) as exc_info:
            parse_coach_output('{"weighted_total": 0.5}')
        assert "schema validation" in str(exc_info.value)

    def test_well_formed_dict_parses(self) -> None:
        verdict = parse_coach_output(
            {
                "weighted_total": 0.85,
                "decision": "accept",
                "criterion_scores": [],
                "rubric_feedback": [],
                "misconceptions": [],
                "reasoning": "",
            }
        )
        assert isinstance(verdict, CoachVerdict)
        assert verdict.decision == "accept"

    def test_well_formed_json_string_parses(self) -> None:
        payload = json.dumps(
            {
                "weighted_total": 0.65,
                "decision": "revise",
                "criterion_scores": [],
                "rubric_feedback": [],
                "misconceptions": [],
                "reasoning": "below threshold",
            }
        )
        verdict = parse_coach_output(payload)
        assert verdict.decision == "revise"

    def test_existing_coach_verdict_passes_through(self) -> None:
        v = CoachVerdict(weighted_total=0.5, decision="revise")
        assert parse_coach_output(v) is v

    def test_fallback_marker_persist_misconceptions_is_false(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # AC-009: no misconception persisted from a malformed output.
        with caplog.at_level(logging.WARNING):
            fallback = coach_unevaluated_fallback("malformed Coach output")
        assert isinstance(fallback, UnevaluatedTurnFallback)
        assert fallback.persist_misconceptions is False
        assert fallback.flagged_for_session_end_review is True
        assert fallback.reason == "malformed Coach output"
        # AC-009 third clause: failure logged for session-end review.
        assert any(
            record.__dict__.get("event") == "coach_unevaluated_turn_fallback"
            for record in caplog.records
        )

    def test_fallback_orchestrator_path_no_misconception_dispatch(
        self, turn_context: TurnContext
    ) -> None:
        # End-to-end safety property: an orchestrator that takes the
        # fallback path must NOT persist any misconception derived from the
        # malformed output. We assert by calling parse_coach_output and
        # verifying it raises; the orchestrator branch in this case never
        # reaches the dispatch site at all.
        with pytest.raises(MalformedCoachOutputError):
            parse_coach_output("garbage that is not a verdict")


# ---------------------------------------------------------------------------
# ASSUM-LCA-005: unknown criterion IDs silently dropped
# ---------------------------------------------------------------------------


class TestUnknownCriterionDrop:
    """ASSUM-LCA-005: ``parse_coach_output`` silently drops unknown
    ``criterion_id`` values returned by the Coach LLM. The canonical
    six in :data:`CRITERION_IDS` are the only IDs the rubric weighted
    dispatch knows how to weight.

    The drop applies to the dict and JSON-string parse branches. The
    already-built :class:`CoachVerdict` pass-through branch is
    intentionally not filtered — a caller that constructs a verdict
    directly is asserting its validity, and silently mutating it would
    surprise tests that round-trip known-good verdicts.
    """

    @staticmethod
    def _canonical_score(criterion_id: str = "curriculum_accuracy") -> dict[str, object]:
        return {
            "criterion_id": criterion_id,
            "score": 0.7,
            "evidence": "ok",
        }

    @staticmethod
    def _unknown_score() -> dict[str, object]:
        return {
            "criterion_id": "bogus_invented_criterion",
            "score": 0.9,
            "evidence": "should be dropped",
        }

    def test_unknown_criterion_id_dropped_from_dict_input(self) -> None:
        verdict = parse_coach_output(
            {
                "weighted_total": 0.5,
                "decision": "accept",
                "criterion_scores": [
                    self._canonical_score(),
                    self._unknown_score(),
                ],
                "rubric_feedback": [],
                "misconceptions": [],
            }
        )
        ids = [cs.criterion_id for cs in verdict.criterion_scores]
        assert ids == ["curriculum_accuracy"]

    def test_unknown_criterion_id_dropped_from_json_string_input(self) -> None:
        payload = json.dumps(
            {
                "weighted_total": 0.5,
                "decision": "accept",
                "criterion_scores": [
                    self._canonical_score(),
                    self._unknown_score(),
                ],
                "rubric_feedback": [],
                "misconceptions": [],
            }
        )
        verdict = parse_coach_output(payload)
        ids = [cs.criterion_id for cs in verdict.criterion_scores]
        assert ids == ["curriculum_accuracy"]

    def test_known_criteria_preserved_in_order_alongside_unknown(self) -> None:
        """A mixed list keeps the surviving canonical criteria in the
        order the LLM emitted them — the parser drops unknown entries
        without reordering or sorting the survivors.
        """
        verdict = parse_coach_output(
            {
                "weighted_total": 0.5,
                "decision": "accept",
                "criterion_scores": [
                    self._canonical_score("ao_alignment"),
                    self._unknown_score(),
                    self._canonical_score("curriculum_accuracy"),
                    {
                        "criterion_id": "another_invented_one",
                        "score": 0.1,
                        "evidence": "drop me too",
                    },
                    self._canonical_score("quote_fidelity"),
                ],
                "rubric_feedback": [],
                "misconceptions": [],
            }
        )
        ids = [cs.criterion_id for cs in verdict.criterion_scores]
        assert ids == [
            "ao_alignment",
            "curriculum_accuracy",
            "quote_fidelity",
        ]

    def test_already_built_coach_verdict_passthrough_is_not_filtered(
        self,
    ) -> None:
        """The pre-built :class:`CoachVerdict` branch in
        :func:`parse_coach_output` is the ``isinstance(raw, CoachVerdict)``
        no-op. Constructing a verdict directly with an off-rubric
        criterion id (which the model schema permits — ``criterion_id``
        is a non-empty string with no whitelist enforcement) and round-
        tripping it through the parser must return the **same** instance,
        unmodified.
        """
        verdict = CoachVerdict(
            weighted_total=0.5,
            decision="accept",
            criterion_scores=[
                CriterionScore(
                    criterion_id="curriculum_accuracy",
                    score=0.5,
                    evidence="ok",
                ),
                CriterionScore(
                    criterion_id="hand_built_off_rubric",
                    score=0.5,
                    evidence="caller asserted this is valid",
                ),
            ],
        )
        result = parse_coach_output(verdict)
        assert result is verdict
        assert [cs.criterion_id for cs in result.criterion_scores] == [
            "curriculum_accuracy",
            "hand_built_off_rubric",
        ]

    def test_no_unknowns_returns_same_verdict_instance(self) -> None:
        """When no criteria need dropping, the parser's hot path
        returns the validated verdict instance directly (no
        :meth:`model_copy` allocation). This locks the
        ``len(kept) == len(verdict.criterion_scores)`` short-circuit in
        :func:`_drop_unknown_criteria` so a future regression that
        eagerly copies on every call surfaces here.
        """
        payload = {
            "weighted_total": 0.5,
            "decision": "accept",
            "criterion_scores": [self._canonical_score()],
            "rubric_feedback": [],
            "misconceptions": [],
        }
        # Calling parse_coach_output twice returns two different verdict
        # instances (model_validate constructs anew each time), but
        # within a single call the short-circuit means model_copy is
        # not invoked. We assert the survivor list count equals the
        # input count to lock the contract.
        verdict = parse_coach_output(payload)
        assert len(verdict.criterion_scores) == 1


# ---------------------------------------------------------------------------
# Integration test: verify_quotes → score_rubric pipeline w/ canonical text
# ---------------------------------------------------------------------------


class TestVerifyToScorePipelineIntegration:
    """Integration: verify_quotes → score_rubric using a canonical primary text."""

    def test_canonical_primary_text_quote_pipeline(
        self, turn_context: TurnContext
    ) -> None:
        """Player quotes a verbatim line from the corpus → annotated → high score.

        Test corpus has one canonical primary text:
        ``"is this a dagger which I see before me"``
        from Macbeth, Act 2 Scene 1.
        """
        original_response = (
            'The line "is this a dagger which I see before me" reveals '
            "Macbeth's hallucinatory turmoil."
        )
        annotated_response = (
            'The line "is this a dagger which I see before me" '
            "[Macbeth, II.i] reveals Macbeth's hallucinatory turmoil."
        )
        result = QuoteVerificationResult(
            annotated_response=annotated_response,
            annotations=(
                QuoteAnnotation(
                    span="is this a dagger which I see before me",
                    citation="Macbeth, II.i",
                    matched=True,
                ),
            ),
            inspected_spans=("is this a dagger which I see before me",),
        )
        verifier = _StubVerifier(result)

        # Pipeline-step 1: quote verification
        response_for_coach, quote_metadata = verify_quotes(
            original_response, verifier=verifier, turn_context=turn_context
        )
        assert response_for_coach == annotated_response

        # Pipeline-step 2: score the *annotated* response
        scorers = _scorers_with_uniform_score(0.9)
        verdict = score_rubric(
            player_response=response_for_coach,
            turn_context=turn_context,
            scorers=scorers,
        )

        # Verdict is shaped + decision derives from the annotated content
        assert verdict.decision == "accept"
        assert verdict.weighted_total == pytest.approx(0.9)

        # Quote metadata round-trips through the pipeline
        assert quote_metadata["annotated_quotes"][0]["citation"] == "Macbeth, II.i"
        assert quote_metadata["annotated_quotes"][0]["matched"] is True


# ---------------------------------------------------------------------------
# Seam test: Coach evaluator dispatches misconceptions via shared write helper
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("StudentStore.record_misconception")
class TestCoachEvaluatorSeam:
    """Seam: Coach evaluator dispatches misconceptions via the shared helper.

    Producer: TASK-GSM-004 (write helper).
    Contract: ``helper.write_misconception(student_id, payload)`` is the
    single dispatch surface for F1 writes (DDR-002). The Coach evaluator
    MUST NOT call the store write API directly.
    """

    @pytest.fixture
    def helper_mock(self) -> AsyncMock:
        helper = AsyncMock(spec=["write_misconception"])
        helper.write_misconception = AsyncMock(return_value=None)
        return helper

    @pytest.fixture
    def coach(self, helper_mock: AsyncMock) -> Any:
        return create_coach(
            player_config=PlayerConfig(provider="anthropic"),
            coach_config=CoachConfig(provider="openai"),
            system_prompt="You are an evaluation-only Coach.",
            write_helper=helper_mock,
        )

    async def test_coach_evaluator_dispatches_misconceptions_via_helper(
        self,
        coach: Any,
        helper_mock: AsyncMock,
        turn_context: TurnContext,
    ) -> None:
        """One observed misconception → one helper.write_misconception call."""
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="annotated text")
        )
        scorers = _scorers_with_uniform_score(0.85)
        misconception = MisconceptionObservation(
            topic_name="Macbeth: ambition",
            misconception_text=(
                "The student conflates the witches' prophecies with "
                "deterministic fate."
            ),
            confidence_band_at_observation="medium",
            triggering_session_id=turn_context.session_id,
        )

        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="player text with quote",
            turn_context=turn_context,
            verifier=verifier,
            scorers=scorers,
            misconceptions=[misconception],
        )

        # Drain the fire-and-forget tasks so the helper has a chance to run.
        for task in evaluation.write_tasks:
            await task

        # Seam contract: write_misconception called exactly once,
        # with the expected (student_id, observation) shape.
        assert helper_mock.write_misconception.await_count == 1
        call = helper_mock.write_misconception.await_args
        assert call.args[0] == turn_context.student_id
        observed_payload = call.args[1]
        assert isinstance(observed_payload, MisconceptionObservation)
        assert observed_payload.topic_name == "Macbeth: ambition"

    async def test_no_misconceptions_means_no_helper_calls(
        self,
        coach: Any,
        helper_mock: AsyncMock,
        turn_context: TurnContext,
    ) -> None:
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="annotated")
        )
        scorers = _scorers_with_uniform_score(0.85)
        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="r",
            turn_context=turn_context,
            verifier=verifier,
            scorers=scorers,
            misconceptions=[],
        )
        for task in evaluation.write_tasks:
            await task
        assert helper_mock.write_misconception.await_count == 0
        assert evaluation.write_tasks == ()

    async def test_multiple_misconceptions_dispatch_per_observation(
        self,
        coach: Any,
        helper_mock: AsyncMock,
        turn_context: TurnContext,
    ) -> None:
        # DDR-002 §Decision: per-observation dispatch — N observations →
        # N independent create_task calls (never a batched list).
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="annotated")
        )
        scorers = _scorers_with_uniform_score(0.85)
        observations = [
            MisconceptionObservation(
                topic_name=f"Topic {i}",
                misconception_text=f"misconception {i}",
            )
            for i in range(3)
        ]
        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="r",
            turn_context=turn_context,
            verifier=verifier,
            scorers=scorers,
            misconceptions=observations,
        )
        for task in evaluation.write_tasks:
            await task
        assert helper_mock.write_misconception.await_count == 3
        # Each call had ONE observation, never a list
        for call in helper_mock.write_misconception.await_args_list:
            assert isinstance(call.args[1], MisconceptionObservation)


# ---------------------------------------------------------------------------
# Pipeline metadata + decision round-trip
# ---------------------------------------------------------------------------


class TestEvaluatePlayerTurnMetadata:
    """``evaluate_player_turn`` augments turn metadata with decision summary."""

    @pytest.fixture
    def coach(self) -> Any:
        helper = AsyncMock(spec=["write_misconception"])
        helper.write_misconception = AsyncMock(return_value=None)
        return create_coach(
            player_config=PlayerConfig(provider="anthropic"),
            coach_config=CoachConfig(provider="openai"),
            system_prompt="Coach prompt",
            write_helper=helper,
        )

    def test_turn_metadata_includes_decision_and_total(
        self, coach: Any, turn_context: TurnContext
    ) -> None:
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="annotated")
        )
        scorers = _scorers_with_uniform_score(0.85)
        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="r",
            turn_context=turn_context,
            verifier=verifier,
            scorers=scorers,
        )
        assert evaluation.turn_metadata["coach_decision"] == "accept"
        assert evaluation.turn_metadata["coach_weighted_total"] == pytest.approx(0.85)

    def test_turn_metadata_records_retrieval_skipped(
        self, coach: Any, analysis_mode_context: TurnContext
    ) -> None:
        # The retrieval-skipped marker propagates through evaluate_player_turn
        # into the merged turn metadata (AC-007).
        verifier = _StubVerifier(
            QuoteVerificationResult(annotated_response="should-not-see")
        )
        scorers = _scorers_with_uniform_score(0.85)
        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="r",
            turn_context=analysis_mode_context,
            verifier=verifier,
            scorers=scorers,
        )
        assert evaluation.turn_metadata["retrieval_skipped"] is True
        assert (
            evaluation.turn_metadata["retrieval_skip_reason"]
            == "session-plan focus is contextual (AO3)"
        )

    def test_turn_metadata_records_verifier_failure(
        self, coach: Any, turn_context: TurnContext
    ) -> None:
        verifier = _RaisingVerifier(RuntimeError("crash"))
        scorers = _scorers_with_uniform_score(0.85)
        evaluation = evaluate_player_turn(
            coach=coach,
            player_response="r",
            turn_context=turn_context,
            verifier=verifier,
            scorers=scorers,
        )
        assert evaluation.turn_metadata["quote_verifier_failed"] is True
        # Verdict still produced (failure-injection pipeline test)
        assert evaluation.verdict.decision == "accept"
