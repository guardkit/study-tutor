"""Coach rubric scoring + quote-fidelity integration (TASK-DTL-002).

This module is the **rubric layer** of the Coach evaluator. It owns three
responsibilities, each derived from an acceptance-criterion family of the
TASK-DTL-002 spec:

1. :func:`score_rubric` — produces six :class:`CriterionScore` instances
   from injected per-criterion scorers, computes the weighted total via
   the configured :class:`RubricWeights` (sanity-checked at construction
   to sum to 1.0), derives the binary accept/revise decision against
   :data:`ACCEPTANCE_THRESHOLD` (0.70 per ASSUM-001), and emits a
   :class:`RubricFeedback` entry per below-threshold criterion. The result
   is a fully-shaped :class:`CoachVerdict` (TASK-DTL-001 model).

2. :func:`verify_quotes` — the consumer-side seam against the FEAT-PH1-004
   quote verifier. Runs **before** the Coach evaluates so the response the
   Coach sees is the annotated/rewritten version. Owns three documented
   policy branches:

   * **Happy path**: verifier annotates verbatim primary-text quotes with
     their canonical citation and the annotated text is the version
     scored.
   * **Fabricated quote**: unmatched spans are removed or rewritten as
     paraphrase; the rewrite is observable in ``turn.metadata``.
   * **Below minimum**: spans below :data:`MIN_QUOTE_LENGTH_WORDS` (4 words
     per FEAT-PH1-004 §4) are not inspected.
   * **Retrieval skipped (analysis mode)**: verifier is bypassed; metadata
     records "retrieval was skipped" with a reason; quote-fidelity is
     **not** down-ranked (the score is recorded as max with an exemption
     evidence string).
   * **Verifier exception**: the response is passed to the Coach
     unannotated, the failure is logged for session-end review, and the
     Coach evaluates under the documented unevaluated-turn fallback (per
     @edge-case @integration @quote-fidelity scenario at .feature L442-447).

3. :func:`parse_coach_output` + :func:`coach_unevaluated_fallback` — the
   malformed-Coach-output safety net. Per ASSUM-007 + the @negative
   @rubric scenario, malformed output mirrors Coach-unreachable: apply the
   unevaluated-turn fallback, persist no misconception, flag the turn for
   session-end review.

:func:`evaluate_player_turn` is the thin pipeline that wires the three
together. It calls ``coach.schedule_misconception_write`` for every
observed misconception — the **single** Graphiti dispatch surface per
DDR-002 / TASK-GSM-004 seam contract. The Coach evaluator never touches
``add_episode`` or any other write API directly.

Cross-references:
    - ASSUM-001 (acceptance threshold = 0.70 weighted)
    - ASSUM-006 (long Coach reasoning flagged, never inlined into Player)
    - ASSUM-007 (Coach-unreachable / unevaluated-turn fallback)
    - DDR-002 (Coach AsyncSubAgent owns Graphiti misconception writes)
    - FEAT-PH1-004 §4 (4-word minimum quote-span length)
    - .feature L442-447 (@edge-case @integration @quote-fidelity)
    - .feature L243-250 (@negative @rubric — malformed Coach output)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from study_tutor.tutoring.coach.factory import (
    Coach,
    CoachVerdict,
    CriterionScore,
    MisconceptionObservation,
    RubricFeedback,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Weighted-total threshold above which the Coach decision is ``"accept"``.
#: Set to 0.70 per ASSUM-001. The threshold uses ``>=`` (not ``>``) so a
#: response scoring exactly 0.70 is accepted (boundary scenario in
#: deepagents-tutoring-loop.feature lines 147-152).
ACCEPTANCE_THRESHOLD: float = 0.70

#: Minimum span length (words) the quote verifier inspects, per FEAT-PH1-004
#: §4. Spans strictly below this length are returned in
#: :attr:`QuoteVerificationResult.skipped_spans` and never round-tripped
#: against the corpus. The boundary scenario is: 3-word → ignore; 4-word and
#: 5-word → inspect.
MIN_QUOTE_LENGTH_WORDS: int = 4

# Per-criterion id constants. Re-exported so callers (and the Coach prompt
# templates) reference the same string symbols rather than literal strings
# scattered across modules.
CRITERION_CURRICULUM_ACCURACY: str = "curriculum_accuracy"
CRITERION_AO_ALIGNMENT: str = "ao_alignment"
CRITERION_SCAFFOLDING_DEPTH: str = "scaffolding_depth"
CRITERION_GRADE_APPROPRIATE_LANGUAGE: str = "grade_appropriate_language"
CRITERION_CONSTRUCTIVE_FEEDBACK: str = "constructive_feedback"
CRITERION_QUOTE_FIDELITY: str = "quote_fidelity"

#: Canonical ordering of the six rubric criteria. Used by :func:`score_rubric`
#: to iterate scorers in a deterministic order — important so test snapshots
#: of ``CoachVerdict.criterion_scores`` are stable.
CRITERION_IDS: tuple[str, ...] = (
    CRITERION_CURRICULUM_ACCURACY,
    CRITERION_AO_ALIGNMENT,
    CRITERION_SCAFFOLDING_DEPTH,
    CRITERION_GRADE_APPROPRIATE_LANGUAGE,
    CRITERION_CONSTRUCTIVE_FEEDBACK,
    CRITERION_QUOTE_FIDELITY,
)

#: Frozen set view of :data:`CRITERION_IDS` for O(1) membership checks in
#: :func:`_drop_unknown_criteria` (ASSUM-LCA-005). Re-deriving on every call
#: would be cheap but allocating once at module import keeps the filter
#: site allocation-free on the hot Coach-evaluate path.
_CANONICAL_CRITERION_IDS: frozenset[str] = frozenset(CRITERION_IDS)

#: Floating-point tolerance for the weights-sum-to-1.0 sanity check. The
#: tolerance is intentionally tight (1e-9) — drift larger than this almost
#: always indicates a configuration mistake (e.g. weights of {0.2, 0.2, 0.2,
#: 0.2, 0.1, 0.05} that sum to 0.95) rather than IEEE-754 representation
#: error.
_WEIGHT_SUM_TOLERANCE: float = 1e-9


# ---------------------------------------------------------------------------
# Rubric weights (factory-construction sanity check per AC-002)
# ---------------------------------------------------------------------------


class RubricWeights(BaseModel):
    """Weights for the six rubric criteria; must sum to 1.0.

    The ``weights sum to 1.0`` check is the AC-002 sanity-check assertion
    at Coach factory construction: the Coach evaluator is the place this
    invariant lives, not the orchestrator. Validation runs at construction
    via :meth:`_weights_must_sum_to_one` so a configuration mistake fails
    loudly before any session is built.

    ``frozen=True`` makes weights immutable post-construction so tests and
    runtime callers cannot mutate one weight and silently invalidate the
    sum-to-1.0 invariant. Each field is bounded ``[0.0, 1.0]`` so a
    negative-weight regression surfaces at field validation, before the
    sum check.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    curriculum_accuracy: float = Field(ge=0.0, le=1.0)
    ao_alignment: float = Field(ge=0.0, le=1.0)
    scaffolding_depth: float = Field(ge=0.0, le=1.0)
    grade_appropriate_language: float = Field(ge=0.0, le=1.0)
    constructive_feedback: float = Field(ge=0.0, le=1.0)
    quote_fidelity: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _weights_must_sum_to_one(self) -> "RubricWeights":
        """AC-002 sanity check: the six weights must sum to 1.0."""
        total = (
            self.curriculum_accuracy
            + self.ao_alignment
            + self.scaffolding_depth
            + self.grade_appropriate_language
            + self.constructive_feedback
            + self.quote_fidelity
        )
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"RubricWeights must sum to 1.0; got {total!r}. "
                f"Per AC-002 of TASK-DTL-002 the weights are sanity-checked at "
                f"Coach factory construction time. Adjust the per-criterion "
                f"weights so the sum is exactly 1.0 (within "
                f"{_WEIGHT_SUM_TOLERANCE} tolerance)."
            )
        return self

    def as_mapping(self) -> Mapping[str, float]:
        """Return a criterion_id → weight mapping in :data:`CRITERION_IDS` order.

        Used by :func:`score_rubric` to look up the weight for each criterion
        without having to grow a parallel dict at call time.
        """
        return {
            CRITERION_CURRICULUM_ACCURACY: self.curriculum_accuracy,
            CRITERION_AO_ALIGNMENT: self.ao_alignment,
            CRITERION_SCAFFOLDING_DEPTH: self.scaffolding_depth,
            CRITERION_GRADE_APPROPRIATE_LANGUAGE: self.grade_appropriate_language,
            CRITERION_CONSTRUCTIVE_FEEDBACK: self.constructive_feedback,
            CRITERION_QUOTE_FIDELITY: self.quote_fidelity,
        }


#: Reasonable default rubric weights — emphasis on curriculum accuracy, AO
#: alignment, and quote fidelity (the three highest-impact criteria for the
#: GCSE literature use case). Sum verified at construction.
DEFAULT_WEIGHTS: RubricWeights = RubricWeights(
    curriculum_accuracy=0.20,
    ao_alignment=0.20,
    scaffolding_depth=0.15,
    grade_appropriate_language=0.10,
    constructive_feedback=0.15,
    quote_fidelity=0.20,
)


# ---------------------------------------------------------------------------
# Turn context
# ---------------------------------------------------------------------------


@dataclass
class TurnContext:
    """Per-turn context the rubric pipeline reads + augments.

    ``retrieval_skipped`` is the load-bearing flag for the @edge-case
    @quote-fidelity @retrieval scenario: when the session-plan focus is
    contextual (analysis mode), retrieval is bypassed and the response
    must not be down-ranked on quote fidelity. The pipeline records the
    skip reason in ``metadata`` and short-circuits the verifier.

    ``metadata`` is the sink :func:`verify_quotes` mutates to record
    annotated quotes, rewritten fabrications, inspected/skipped span
    lists, and verifier-failure markers. It is the same dict the
    orchestrator persists onto the turn record for session-end review.
    """

    student_id: str = ""
    session_id: str = ""
    mode: str = "tutor"
    retrieval_skipped: bool = False
    retrieval_skip_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Quote verifier seam (FEAT-PH1-004 consumer-side protocol)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuoteAnnotation:
    """One inspected quote span and the verifier's resolution.

    ``citation`` is ``None`` for spans that were rewritten as paraphrase
    (fabricated-quote case). ``rewritten_as_paraphrase`` is the explicit
    boolean so a caller does not have to second-guess ``citation is None``
    — there might be future verifier branches where ``None`` carries a
    different meaning.
    """

    span: str
    citation: str | None
    matched: bool
    rewritten_as_paraphrase: bool = False


@dataclass(frozen=True)
class QuoteVerificationResult:
    """Output of :meth:`QuoteVerifierLike.verify_quotes`.

    ``annotated_response`` is the *single* string the Coach evaluates —
    it is the ground truth for AC-004 ("the annotated response is the
    version evaluated by the Coach") and AC-005 ("the Coach evaluates
    the rewritten response, not the original").

    ``inspected_spans`` and ``skipped_spans`` are the boundary observable
    for AC-006 (the 3/4/5-word minimum-length scenario).
    """

    annotated_response: str
    annotations: tuple[QuoteAnnotation, ...] = ()
    rewritten_quotes: tuple[str, ...] = ()
    inspected_spans: tuple[str, ...] = ()
    skipped_spans: tuple[str, ...] = ()


@runtime_checkable
class QuoteVerifierLike(Protocol):
    """Structural protocol for the FEAT-PH1-004 quote verifier.

    The Coach module consumes this protocol; the implementation lives in
    the FEAT-PH1-004 wave. Using a Protocol (rather than a hard import)
    keeps the rubric module testable with simple mock objects and avoids
    pulling the corpus + retrieval stack into Coach unit tests.
    """

    def verify_quotes(
        self,
        response: str,
        *,
        min_quote_length_words: int = MIN_QUOTE_LENGTH_WORDS,
    ) -> QuoteVerificationResult:  # pragma: no cover - protocol declaration
        ...


# ---------------------------------------------------------------------------
# Quote verifier wrapper (handles failure path + retrieval-skipped branch)
# ---------------------------------------------------------------------------


def verify_quotes(
    response: str,
    *,
    verifier: QuoteVerifierLike,
    turn_context: TurnContext,
    min_quote_length_words: int = MIN_QUOTE_LENGTH_WORDS,
) -> tuple[str, dict[str, Any]]:
    """Run the quote verifier seam and return ``(response_for_coach, metadata)``.

    The returned ``response_for_coach`` is the string the Coach should
    evaluate. The returned ``metadata`` dict has the verifier's findings —
    annotated quotes, rewritten fabrications, inspected/skipped span
    lists, retrieval-skipped marker, or verifier-failure marker — and is
    intended to be merged into ``turn_context.metadata`` for session-end
    review.

    Three policy branches:

    1. ``turn_context.retrieval_skipped`` is ``True``: the verifier is
       bypassed, ``metadata["retrieval_skipped"] = True``, and the
       skip reason is recorded. The original response is returned
       unchanged.
    2. The verifier raises any exception: ``metadata`` is annotated with
       ``quote_verifier_failed = True`` plus the error class, the
       failure is logged with structured fields, and the **original
       response** is returned unannotated. Per the @edge-case @integration
       @quote-fidelity scenario the Coach evaluates the unannotated
       response under the documented fallback policy.
    3. Happy path: the verifier's :class:`QuoteVerificationResult` is
       unpacked into metadata and ``annotated_response`` is returned.

    Args:
        response: The Player response text to verify.
        verifier: An object satisfying :class:`QuoteVerifierLike`.
        turn_context: Turn metadata; consulted for the
            ``retrieval_skipped`` short-circuit.
        min_quote_length_words: Minimum span length the verifier should
            inspect. Defaults to :data:`MIN_QUOTE_LENGTH_WORDS` (4).

    Returns:
        ``(response_for_coach, metadata_updates)``: the response the Coach
        should evaluate plus a metadata dict the orchestrator merges onto
        the turn record.
    """
    metadata: dict[str, Any] = {}

    if turn_context.retrieval_skipped:
        metadata["retrieval_skipped"] = True
        metadata["retrieval_skip_reason"] = (
            turn_context.retrieval_skip_reason or "retrieval was skipped"
        )
        return response, metadata

    try:
        result = verifier.verify_quotes(
            response, min_quote_length_words=min_quote_length_words
        )
    except Exception as exc:
        # Broad except is intentional and bounded: the quote verifier is an
        # integration boundary (FEAT-PH1-004) and any of corpus retrieval,
        # citation-resolution, or rewrite-LLM may raise. Per AC and the
        # @edge-case @integration @quote-fidelity scenario, the loop must
        # NOT propagate the failure — it logs and falls back to evaluating
        # the unannotated response.
        logger.warning(
            "quote verifier raised unexpected exception; falling back to "
            "unannotated Coach evaluation",
            extra={
                "event": "quote_verifier_failed",
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
                "session_id": turn_context.session_id,
            },
        )
        metadata["quote_verifier_failed"] = True
        metadata["quote_verifier_error_class"] = exc.__class__.__name__
        metadata["quote_verifier_error_message"] = str(exc)
        return response, metadata

    if result.annotations:
        metadata["annotated_quotes"] = [
            {
                "span": ann.span,
                "citation": ann.citation,
                "matched": ann.matched,
                "rewritten_as_paraphrase": ann.rewritten_as_paraphrase,
            }
            for ann in result.annotations
        ]
    if result.rewritten_quotes:
        metadata["rewritten_quotes"] = list(result.rewritten_quotes)
    if result.inspected_spans:
        metadata["inspected_quote_spans"] = list(result.inspected_spans)
    if result.skipped_spans:
        metadata["skipped_quote_spans"] = list(result.skipped_spans)

    return result.annotated_response, metadata


# ---------------------------------------------------------------------------
# Per-criterion scorer protocol
# ---------------------------------------------------------------------------


CriterionScorer = Callable[[str, TurnContext], CriterionScore]
"""A callable that produces a :class:`CriterionScore` for a single criterion.

Tests inject deterministic scorers (e.g. ``lambda r, ctx: CriterionScore(...)``)
so the rubric branches can be exercised independently per the test
requirement "Unit tests for ``score_rubric`` covering all six criterion
scoring branches independently (mock criterion scorers)".
"""

ScorerMap = Mapping[str, CriterionScorer]
"""A mapping ``criterion_id → scorer``. Must contain every id in
:data:`CRITERION_IDS`; missing ids are flagged at :func:`score_rubric` entry."""


def _exemption_score_for_skipped_retrieval() -> CriterionScore:
    """Build the AC-007 quote-fidelity exemption score (analysis-mode path).

    Recorded with ``score=1.0`` so the weighted total is not down-ranked,
    plus an evidence string that explains the exemption to a human reading
    the verdict during session-end review.
    """
    return CriterionScore(
        criterion_id=CRITERION_QUOTE_FIDELITY,
        score=1.0,
        evidence=(
            "exempt — retrieval was skipped for this turn (analysis mode); "
            "quote-fidelity not down-ranked per AC-007"
        ),
    )


# ---------------------------------------------------------------------------
# score_rubric
# ---------------------------------------------------------------------------


def score_rubric(
    *,
    player_response: str,
    turn_context: TurnContext,
    scorers: ScorerMap,
    weights: RubricWeights = DEFAULT_WEIGHTS,
    threshold: float = ACCEPTANCE_THRESHOLD,
    misconceptions: list[MisconceptionObservation] | None = None,
    reasoning: str = "",
) -> CoachVerdict:
    """Compute a :class:`CoachVerdict` from per-criterion scorers.

    Pipeline:

    1. Validate every criterion in :data:`CRITERION_IDS` has a scorer
       (missing scorers fail loud).
    2. For each criterion, call its scorer (or, for ``quote_fidelity`` when
       ``turn_context.retrieval_skipped`` is True, substitute the
       exemption score).
    3. Compute ``weighted_total = sum(score_i * weight_i)`` over the six
       criteria, clamped defensively to ``[0.0, 1.0]`` to absorb IEEE-754
       drift on the ``1.0`` corner.
    4. Decision: ``weighted_total >= threshold → "accept"``; else
       ``"revise"``. Note ``>=`` (not ``>``) so 0.70 is accepted (per the
       @boundary @rubric Scenario Outline).
    5. Build a :class:`RubricFeedback` entry per below-threshold criterion.
    6. Return a :class:`CoachVerdict` with all six scores, the feedback
       list, the (possibly empty) misconception list, and the verdict
       reasoning.

    Args:
        player_response: The (already quote-verified, if applicable)
            Player response text.
        turn_context: Turn context — the ``retrieval_skipped`` flag drives
            the quote-fidelity exemption branch (AC-007).
        scorers: Per-criterion scorer mapping. Must contain every id in
            :data:`CRITERION_IDS`.
        weights: :class:`RubricWeights` whose six weights sum to 1.0.
            Sanity-checked at the weights' construction; passed through
            here.
        threshold: Decision threshold. Defaults to
            :data:`ACCEPTANCE_THRESHOLD` (0.70).
        misconceptions: Optional list of
            :class:`MisconceptionObservation`. Pass-through into the
            verdict — the orchestrator dispatches them via
            :meth:`Coach.schedule_misconception_write`.
        reasoning: Free-text Coach reasoning. ``CoachVerdict`` flags
            ``reasoning_long`` automatically when word-count exceeds the
            REASONING_LONG_WORD_THRESHOLD.

    Returns:
        A fully-shaped :class:`CoachVerdict`.

    Raises:
        ValueError: If ``scorers`` is missing any criterion id, or if a
            scorer returns a :class:`CriterionScore` whose ``criterion_id``
            does not match the expected slot.
    """
    _check_scorer_completeness(scorers)

    weight_map = weights.as_mapping()

    scores: list[CriterionScore] = []
    weighted_total: float = 0.0

    for criterion_id in CRITERION_IDS:
        if (
            criterion_id == CRITERION_QUOTE_FIDELITY
            and turn_context.retrieval_skipped
        ):
            criterion_score = _exemption_score_for_skipped_retrieval()
        else:
            scorer = scorers[criterion_id]
            criterion_score = scorer(player_response, turn_context)
            if criterion_score.criterion_id != criterion_id:
                raise ValueError(
                    f"Scorer for {criterion_id!r} returned a CriterionScore "
                    f"with criterion_id={criterion_score.criterion_id!r}; "
                    f"this is a programmer error — each scorer must emit a "
                    f"CriterionScore matching its slot."
                )

        scores.append(criterion_score)
        weighted_total += criterion_score.score * weight_map[criterion_id]

    # Defensive clamp: the per-criterion field validator caps each score at
    # [0.0, 1.0] and weights sum to 1.0, so the mathematical maximum is 1.0.
    # Float arithmetic can drift fractionally past 1.0 (e.g. 1.0000000000002)
    # which would fail CoachVerdict's ``le=1.0`` field validation. Clamp
    # before constructing the verdict so we don't have to widen the verdict's
    # validation surface.
    weighted_total = max(0.0, min(1.0, weighted_total))

    decision = "accept" if weighted_total >= threshold else "revise"

    feedback = _build_feedback(scores, threshold)

    return CoachVerdict(
        weighted_total=weighted_total,
        decision=decision,
        criterion_scores=scores,
        rubric_feedback=feedback,
        misconceptions=list(misconceptions or []),
        reasoning=reasoning,
    )


def _check_scorer_completeness(scorers: ScorerMap) -> None:
    """Fail fast when a scorer for any of the six criteria is missing."""
    missing = [c for c in CRITERION_IDS if c not in scorers]
    if missing:
        raise ValueError(
            f"score_rubric: scorers must provide a callable for every "
            f"criterion in CRITERION_IDS; missing: {missing!r}. The Coach "
            f"evaluator cannot produce a six-criterion CoachVerdict without "
            f"all scorers wired."
        )


def _build_feedback(
    scores: list[CriterionScore], threshold: float
) -> list[RubricFeedback]:
    """Build a :class:`RubricFeedback` entry per below-threshold criterion.

    Per ASSUM-008 + the @security @revision-loop scenario,
    :class:`RubricFeedback` is structured-only (no free-text dump). The
    ``suggested_focus`` is set to the criterion id itself — a fixed-vocab
    string — so the Player's revision prompt can branch on a known set of
    focus markers rather than parsing free text.
    """
    feedback: list[RubricFeedback] = []
    for criterion_score in scores:
        if criterion_score.score < threshold:
            feedback.append(
                RubricFeedback(
                    criterion_id=criterion_score.criterion_id,
                    suggested_focus=criterion_score.criterion_id,
                    target_score=threshold,
                )
            )
    return feedback


# ---------------------------------------------------------------------------
# Malformed Coach output handling (mirrors Coach-unreachable per ASSUM-007)
# ---------------------------------------------------------------------------


class MalformedCoachOutputError(ValueError):
    """Raised when raw Coach output cannot be parsed into a :class:`CoachVerdict`.

    Subclasses :class:`ValueError` so existing ``except ValueError`` callers
    catch it (consistent with :class:`CoachConfigurationError` in
    ``factory.py``). The orchestrator's response to this exception is the
    documented unevaluated-turn fallback (per the @negative @rubric scenario).
    """


def _drop_unknown_criteria(verdict: CoachVerdict) -> CoachVerdict:
    """Filter unknown criterion IDs out of ``verdict.criterion_scores``.

    Per ASSUM-LCA-005 + the LCA-002 AC: unknown criterion IDs from raw
    Coach LLM output are silently dropped — the canonical six in
    :data:`CRITERION_IDS` are the only IDs the rubric weighted-total
    dispatch knows how to weight, and an LLM-invented criterion would
    otherwise survive validation (``CriterionScore.criterion_id`` is a
    plain non-empty string with no whitelist enforcement on the model
    itself).

    The filter is applied only on the dict and JSON-string parse
    branches in :func:`parse_coach_output`. The pre-built
    :class:`CoachVerdict` pass-through branch is intentionally left
    untouched: a caller that constructed a verdict directly is asserting
    its validity, and silently mutating that object would surprise tests
    that round-trip known-good verdicts.

    ``weighted_total`` is **not** recomputed when criteria are dropped.
    Phase-1 acceptance is intentionally lenient about post-drop
    divergence (per ASSUM-LCA-010 — calibration is Phase-2 territory);
    re-aggregating here would also re-introduce the rubric-weight
    coupling we are trying to keep parser-side parser-only. The
    downstream :func:`score_rubric` call site recomputes the weighted
    total against the canonical scorer set anyway.
    """
    kept = [
        cs
        for cs in verdict.criterion_scores
        if cs.criterion_id in _CANONICAL_CRITERION_IDS
    ]
    if len(kept) == len(verdict.criterion_scores):
        # Common case: nothing to drop — return the same instance so the
        # parser's hot path does not allocate a copy on every well-formed
        # verdict.
        return verdict
    return verdict.model_copy(update={"criterion_scores": kept})


def parse_coach_output(raw: Any) -> CoachVerdict:
    """Parse raw Coach output into a :class:`CoachVerdict`.

    Accepts three input shapes — the three the Coach LLM-shim might
    produce on different code paths:

    * An already-built :class:`CoachVerdict` (no-op).
    * A ``dict`` (e.g. from a structured-output adapter).
    * A JSON ``str`` (e.g. from a raw text-completion provider).

    Anything else — including ``None``, a list, an int — raises
    :class:`MalformedCoachOutputError`. Schema-validation failures from
    Pydantic are wrapped in :class:`MalformedCoachOutputError` so the
    orchestrator has exactly one exception class to catch.

    Per ASSUM-LCA-005, unknown criterion IDs in ``criterion_scores`` are
    silently dropped on the ``dict`` and ``str`` parse branches via
    :func:`_drop_unknown_criteria`. The already-built
    :class:`CoachVerdict` pass-through branch is intentionally not
    filtered — a caller that constructed the verdict directly is
    asserting its validity.

    Raises:
        MalformedCoachOutputError: If parsing or schema validation fails.
            The orchestrator applies the unevaluated-turn fallback.
    """
    if isinstance(raw, CoachVerdict):
        return raw

    if isinstance(raw, dict):
        try:
            verdict = CoachVerdict.model_validate(raw)
        except ValidationError as exc:
            raise MalformedCoachOutputError(
                f"Coach output dict failed CoachVerdict schema validation: {exc}"
            ) from exc
        return _drop_unknown_criteria(verdict)

    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MalformedCoachOutputError(
                f"Coach output is not valid JSON: {exc.msg} at line "
                f"{exc.lineno} col {exc.colno}"
            ) from exc
        if not isinstance(payload, dict):
            raise MalformedCoachOutputError(
                f"Coach output JSON must be an object, got "
                f"{type(payload).__name__}"
            )
        try:
            verdict = CoachVerdict.model_validate(payload)
        except ValidationError as exc:
            raise MalformedCoachOutputError(
                f"Coach output JSON failed CoachVerdict schema validation: {exc}"
            ) from exc
        return _drop_unknown_criteria(verdict)

    raise MalformedCoachOutputError(
        f"Coach output of type {type(raw).__name__} is not parseable; "
        f"expected CoachVerdict, dict, or JSON string."
    )


@dataclass(frozen=True)
class UnevaluatedTurnFallback:
    """Marker the orchestrator routes the unevaluated-turn fallback against.

    Per ASSUM-007 + the @negative @rubric scenario, the fallback policy
    is symmetric across malformed-output and Coach-unreachable: pass the
    Player response through to the learner unevaluated, persist no
    misconception (``persist_misconceptions=False`` is a hard property,
    not a default), and flag the turn for session-end review.

    ``frozen=True`` makes the policy non-mutable post-construction — the
    orchestrator should not be able to flip ``persist_misconceptions``
    True after the fact and silently re-enable misconception writes from
    a malformed output.
    """

    reason: str
    flagged_for_session_end_review: bool = True
    persist_misconceptions: bool = False


def coach_unevaluated_fallback(reason: str) -> UnevaluatedTurnFallback:
    """Build the unevaluated-turn fallback marker and log the failure.

    The log line uses event name ``coach_unevaluated_turn_fallback`` so the
    session-end review surface can filter for it. The function is the
    single construction site for :class:`UnevaluatedTurnFallback` so a
    grep for the event name maps 1:1 to fallback dispatches in production
    logs.
    """
    logger.warning(
        "coach output unevaluated; applying unevaluated-turn fallback",
        extra={
            "event": "coach_unevaluated_turn_fallback",
            "reason": reason,
        },
    )
    return UnevaluatedTurnFallback(reason=reason)


# ---------------------------------------------------------------------------
# Pipeline: verify_quotes → score_rubric → dispatch misconceptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoachEvaluation:
    """Bundle returned by :func:`evaluate_player_turn`.

    Wraps the verdict, the merged turn metadata, and the list of
    fire-and-forget write tasks so the orchestrator has a single object
    to thread through the loop. Frozen so a downstream consumer cannot
    accidentally mutate the verdict surface (the verdict itself is a
    Pydantic model with strict ``extra="forbid"``; this freeze covers
    the surrounding bundle).
    """

    verdict: CoachVerdict
    turn_metadata: dict[str, Any]
    write_tasks: tuple[Any, ...]


def evaluate_player_turn(
    *,
    coach: Coach,
    player_response: str,
    turn_context: TurnContext,
    verifier: QuoteVerifierLike,
    scorers: ScorerMap,
    weights: RubricWeights = DEFAULT_WEIGHTS,
    threshold: float = ACCEPTANCE_THRESHOLD,
    misconceptions: list[MisconceptionObservation] | None = None,
    reasoning: str = "",
) -> CoachEvaluation:
    """End-to-end Coach evaluator: verify_quotes → score_rubric → dispatch.

    This is the single Coach-side entry point the orchestrator
    (TASK-DTL-003) calls per turn. It owns the integration shape, NOT the
    orchestration of revisions or fallback routing — those stay in
    TASK-DTL-003's surface.

    The misconception-write site is :meth:`Coach.schedule_misconception_write`
    (the **only** Graphiti dispatch surface — DDR-002 / TASK-GSM-004 seam
    contract). The Coach evaluator never reaches around the helper and never
    calls ``add_episode`` / any other write API directly. The seam test in
    the task spec asserts ``helper.write_misconception.await_count == 1``
    when one misconception is observed; that assertion is what this method
    promises.

    Args:
        coach: A :class:`Coach` constructed via ``create_coach``. Owns the
            injected write helper.
        player_response: The Player's raw turn response text.
        turn_context: Turn context. ``student_id`` is required when
            ``misconceptions`` is non-empty (it is the dispatch key on
            the helper).
        verifier: The FEAT-PH1-004 quote verifier.
        scorers: Per-criterion scorer mapping (six required).
        weights: :class:`RubricWeights`. Defaults to :data:`DEFAULT_WEIGHTS`.
        threshold: Decision threshold. Defaults to :data:`ACCEPTANCE_THRESHOLD`.
        misconceptions: Optional misconceptions observed by the Coach
            during this turn. Each is dispatched fire-and-forget via the
            shared write helper.
        reasoning: Optional Coach reasoning text. Pass-through into the
            verdict's ``reasoning`` field.

    Returns:
        A :class:`CoachEvaluation` bundle with the verdict, the merged
        turn metadata (verifier findings + decision summary), and the
        list of fire-and-forget write tasks (tests can ``await`` them;
        production code must not).
    """
    annotated_response, quote_metadata = verify_quotes(
        player_response,
        verifier=verifier,
        turn_context=turn_context,
    )

    # Merge into a fresh dict — never mutate the caller's
    # ``turn_context.metadata`` directly. The orchestrator owns persistence
    # of this dict onto the turn record.
    turn_metadata: dict[str, Any] = dict(turn_context.metadata)
    turn_metadata.update(quote_metadata)

    verdict = score_rubric(
        player_response=annotated_response,
        turn_context=turn_context,
        scorers=scorers,
        weights=weights,
        threshold=threshold,
        misconceptions=misconceptions,
        reasoning=reasoning,
    )

    # Dispatch each misconception observation via the shared write helper.
    # Per DDR-002 each call is one ``asyncio.create_task`` — the helper's
    # contract accepts ONE observation per call, never a batch. The Coach's
    # ``schedule_misconception_write`` enforces that on the dispatch side.
    write_tasks: list[Any] = []
    for observation in verdict.misconceptions:
        task = coach.schedule_misconception_write(
            turn_context.student_id, observation
        )
        write_tasks.append(task)

    turn_metadata["coach_decision"] = verdict.decision
    turn_metadata["coach_weighted_total"] = verdict.weighted_total

    return CoachEvaluation(
        verdict=verdict,
        turn_metadata=turn_metadata,
        write_tasks=tuple(write_tasks),
    )


__all__ = [
    "ACCEPTANCE_THRESHOLD",
    "MIN_QUOTE_LENGTH_WORDS",
    "CRITERION_CURRICULUM_ACCURACY",
    "CRITERION_AO_ALIGNMENT",
    "CRITERION_SCAFFOLDING_DEPTH",
    "CRITERION_GRADE_APPROPRIATE_LANGUAGE",
    "CRITERION_CONSTRUCTIVE_FEEDBACK",
    "CRITERION_QUOTE_FIDELITY",
    "CRITERION_IDS",
    "CoachEvaluation",
    "CriterionScorer",
    "DEFAULT_WEIGHTS",
    "MalformedCoachOutputError",
    "QuoteAnnotation",
    "QuoteVerificationResult",
    "QuoteVerifierLike",
    "RubricWeights",
    "ScorerMap",
    "TurnContext",
    "UnevaluatedTurnFallback",
    "coach_unevaluated_fallback",
    "evaluate_player_turn",
    "parse_coach_output",
    "score_rubric",
    "verify_quotes",
]
