"""Player-Coach orchestrator with bounded revision loop (TASK-DTL-003).

This module owns the per-turn :class:`PlayerCoachOrchestrator` that wires the
quote-verifier → Player → Coach pipeline together for a single tutoring turn,
applies the bounded revision loop policy from ASSUM-002, and enforces the
fallback / isolation / stable-turn invariants from FEAT-PH1-003.

Per-turn instantiation is the load-bearing concurrency guarantee:
:class:`PlayerCoachOrchestrator` keeps **no session-scoped state**. Two
concurrent sessions get two independent orchestrator instances and there is
no shared mutable container that one session's Coach could write into and
another's could read out of (per the @edge-case @concurrency scenario).

Cross-references:
    - ASSUM-002 (MAX_REVISION_ATTEMPTS = 3)
    - ASSUM-008 (no Coach free-text on revision; RubricFeedback only)
    - @boundary @revision-loop scenario (lowest-scoring on exhaustion)
    - @negative @fallback scenarios (Coach-unreachable, Player-unreachable)
    - @negative @invariant scenario (misconfigured-loop guard)
    - @edge-case @concurrency scenario (per-session isolation)
    - @edge-case @revision-loop scenario (stable-turn guarantee)
    - TASK-DTL-001 (Coach factory + canonical CoachVerdict / RubricFeedback)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Protocol, runtime_checkable

from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.tutoring.coach import CoachVerdict, RubricFeedback

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Coach-handover seam type alias (TASK-PRV-006)
# ---------------------------------------------------------------------------

#: Signature of the optional coach-handover callable wired into the
#: orchestrator between Player and Coach. Given the Player's raw
#: response, the learner's message (used as the retrieval query — see
#: TASK-RAG-002), and the opaque session_state, it returns
#: ``(response_for_coach, verifier_metadata)``. The arg order is
#: ``(raw_response, learner_message, session_state)``. Production wiring
#: binds :func:`study_tutor.knowledge.coach_handover.apply_quote_verification`
#: with corpus chunks / session_text_name / retrieval_skipped_reason
#: derived from session_state at call time, and uses ``learner_message``
#: as the retrieval query (matches the @key-example fixtures in
#: TASK-PRV-004). Tests inject simple lambdas or stubs.
CoachHandover = Callable[[str, str, Any], tuple[str, VerifierMetadata]]


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Hard cap on revision attempts per turn (ASSUM-002). After three
#: below-threshold revisions we stop asking for more and release the
#: lowest-scoring reply observed across the whole attempt sequence.
#: Module-level (not config) keeps the contract greppable; if it ever
#: becomes tunable it migrates to runtime config and this constant moves
#: to the default.
MAX_REVISION_ATTEMPTS: int = 3

#: Per-turn p95 latency budget (seconds). Anything above this is logged
#: as ``latency_over_budget`` with the turn flagged for session-end
#: review; we still return the response to the learner — over-budget is
#: an observability signal, not an error mode.
LATENCY_BUDGET_SECONDS: float = 30.0


#: Decision tag attached to :class:`TurnResult.decision`. ``"deferred"`` is the
#: async-Coach return tag (ADR-ARCH-026 D1): the response was delivered before
#: the Coach evaluated, so no accept/revise decision is available at return time.
TurnDecision = Literal["accept", "exhausted", "fallback", "deferred"]


#: Module-level registry of in-flight background Coach tasks (ADR-ARCH-026 D1).
#: asyncio keeps only a weak reference to a bare task, so a fire-and-forget
#: evaluation can be garbage-collected mid-flight — we hold a strong reference
#: here and drop it in the done-callback. The Coach is a background MONITOR (the
#: learner already has the response), so a task that raises is logged and
#: suppressed, never surfaced to the turn.
_BACKGROUND_COACH_TASKS: "set[asyncio.Task[Any]]" = set()


def _background_coach_done(task: "asyncio.Task[Any]") -> None:
    """Done-callback for background Coach tasks: drop the ref, log any escape."""
    _BACKGROUND_COACH_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning(
            "background Coach task raised (suppressed — response already delivered)",
            extra={
                "event": "orchestrator_async_coach_task_error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OrchestratorConfigurationError(ValueError):
    """Raised when a session-start invariant is violated.

    Subclasses :class:`ValueError` so the existing MCP boundary catch
    (``except ValueError``) handles it without code changes, while still
    allowing precise targeting via ``except OrchestratorConfigurationError``
    in tests and audit tooling. Mirrors :class:`CoachConfigurationError`'s
    pattern from TASK-DTL-001.
    """


class PlayerUnavailableError(RuntimeError):
    """Raised by Player adapters when the upstream provider is unreachable.

    Distinct from :class:`Exception` so the orchestrator can branch on
    "this is a known-unavailable provider" vs "this is an unexpected
    bug". The Player-unreachable mid-revision scenario uses this signal
    to trigger the unevaluated-turn fallback (per the @edge-case
    @integration @fallback scenario).

    Adapters MAY raise plain ``Exception``\\ s instead — those will be
    re-classified as provider-unavailable by the orchestrator's catch
    site. This subclass is the documented preferred shape.
    """


class CoachUnavailableError(RuntimeError):
    """Raised by Coach adapters when evaluation cannot complete.

    Documented preferred shape for "Coach returned no response within its
    evaluation budget" (per the @negative @fallback scenario). Same
    re-classification rule as :class:`PlayerUnavailableError` applies:
    plain exceptions are still treated as Coach-unavailable.
    """


# ---------------------------------------------------------------------------
# Component protocols (Player / Coach / QuoteVerifier)
# ---------------------------------------------------------------------------


@runtime_checkable
class PlayerLike(Protocol):
    """Structural protocol for the Player agent adapter.

    The orchestrator calls :meth:`respond` on the first attempt and
    :meth:`revise` on every subsequent attempt. The split surfaces the
    crucial fact that **revision input is strictly :class:`RubricFeedback`**
    — there is no free-text channel for Coach reasoning to leak through
    (ASSUM-008 + the @edge-case @security @revision-loop scenario).
    """

    async def respond(
        self,
        *,
        session_state: Any,
        learner_message: str,
    ) -> str:  # pragma: no cover - protocol declaration only
        ...

    async def revise(
        self,
        *,
        session_state: Any,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list[RubricFeedback],
    ) -> str:  # pragma: no cover - protocol declaration only
        ...


@runtime_checkable
class CoachLike(Protocol):
    """Structural protocol for the Coach evaluator adapter.

    Returns a fully-validated :class:`CoachVerdict` (TASK-DTL-001 schema)
    or raises :class:`CoachUnavailableError` if evaluation cannot
    complete. The orchestrator does not interpret the verdict shape
    beyond ``decision`` and ``weighted_total`` — all rubric / feedback
    routing is driven off those two fields.
    """

    async def evaluate(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
    ) -> CoachVerdict:  # pragma: no cover - protocol declaration only
        ...


@runtime_checkable
class QuoteVerifierLike(Protocol):
    """Structural protocol for the quote-verifier adapter (FEAT-PH1-004).

    The orchestrator runs the quote verifier first, before either Player
    or Coach. The return value is opaque here (the verifier's report
    schema lives in FEAT-PH1-004); we only consume the side-effect of
    "did this raise?" for the boundary, plus pass the report through to
    Player/Coach via :class:`SessionState`-shaped containers if the
    caller chose to route it.
    """

    async def verify(
        self,
        *,
        session_state: Any,
        learner_message: str,
    ) -> Any:  # pragma: no cover - protocol declaration only
        ...


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurnResult:
    """Outcome of a single :meth:`PlayerCoachOrchestrator.run_turn` call.

    Frozen so a downstream consumer cannot mutate the recorded latency or
    decision after the fact; that protects the session-end audit log,
    which uses these fields directly.

    Attributes:
        response: The learner-facing reply. NEVER includes Coach
            free-text reasoning (ASSUM-006 / ASSUM-008).
        decision: How the turn terminated — ``accept`` for above-threshold
            on any attempt, ``exhausted`` for three failed revisions
            (lowest-scoring released), ``fallback`` for Coach-unreachable
            or Player-unavailable mid-revision.
        verdict: The Coach verdict associated with ``response`` when one
            was produced; ``None`` on Coach-unreachable fallback.
        attempts: Number of Player invocations made (1..MAX_REVISION_ATTEMPTS).
            Always ≥1; revisions add to this counter.
        flagged_for_review: ``True`` when the turn warrants session-end
            review (exhaustion, fallback, or over-budget latency).
        flag_reason: Human-readable string describing why the turn was
            flagged. ``None`` iff ``flagged_for_review is False``.
        duration_seconds: Wall-clock latency of the entire ``run_turn``
            call. Compared against :data:`LATENCY_BUDGET_SECONDS` to set
            the over-budget marker.
    """

    response: str
    decision: TurnDecision
    verdict: CoachVerdict | None
    attempts: int
    flagged_for_review: bool
    flag_reason: str | None
    duration_seconds: float
    #: Verifier output for the **released** response (i.e. the one in
    #: :attr:`response`), surfaced so session-end summaries can include
    #: per-turn verifier events (TASK-PRV-006). ``None`` when no
    #: ``coach_handover`` was wired (legacy FEAT-PH1-003 callers) or
    #: when the turn fell back before any Player response was produced
    #: (Player-unavailable on first attempt). When the verifier raised,
    #: the metadata's ``verifier_exception`` flag is ``True``.
    verifier_metadata: VerifierMetadata | None = None


# ---------------------------------------------------------------------------
# Misconfigured-loop guard (session-start invariant)
# ---------------------------------------------------------------------------


def validate_loop_configuration(
    *,
    route_coach_reasoning_to_learner: bool = False,
    revision_input_channel: str = "rubric_feedback",
    max_revision_attempts: int = MAX_REVISION_ATTEMPTS,
) -> None:
    """Refuse session start if the loop would leak Coach text to the learner.

    This is the @negative @invariant scenario (.feature line 293-296):
    a misconfigured loop that routes Coach reasoning into the
    learner-facing response path is a security failure, not a quality
    failure — so we refuse session start outright rather than letting
    the session run with a contaminated path.

    Args:
        route_coach_reasoning_to_learner: Sentinel that misconfigured
            wiring would set to ``True``. Any truthy value is rejected.
        revision_input_channel: Documented value of the channel the
            Player consumes on revision. The only acceptable value is
            ``"rubric_feedback"`` (per ASSUM-008); anything else
            indicates a regressed wiring.
        max_revision_attempts: Asserted ``> 0`` and ``<=`` the module
            constant. A non-positive value would short-circuit revision
            entirely; an over-large value would burn the latency budget.

    Raises:
        OrchestratorConfigurationError: With a message that names the
            specific invariant violated. Each branch carries a distinct
            message so the failure is unambiguously identifiable.
    """
    if route_coach_reasoning_to_learner:
        raise OrchestratorConfigurationError(
            "Orchestrator refused: loop configuration would route Coach "
            "reasoning into the learner-facing response path. The Coach "
            "evaluator output is session-only by ASSUM-006 + ASSUM-008; "
            "a learner-visible Coach text channel is a prompt-injection "
            "and pedagogy-leak surface."
        )
    if revision_input_channel != "rubric_feedback":
        raise OrchestratorConfigurationError(
            f"Orchestrator refused: revision_input_channel must be "
            f"'rubric_feedback' (per ASSUM-008). Got "
            f"{revision_input_channel!r}; any other value would re-enable "
            f"the prose-passthrough channel TASK-DTL-001 specifically "
            f"closed."
        )
    if max_revision_attempts <= 0:
        raise OrchestratorConfigurationError(
            f"Orchestrator refused: max_revision_attempts must be > 0 "
            f"(got {max_revision_attempts}). A non-positive value would "
            f"short-circuit the revision loop and silently downgrade the "
            f"acceptance bar."
        )
    if max_revision_attempts > MAX_REVISION_ATTEMPTS:
        raise OrchestratorConfigurationError(
            f"Orchestrator refused: max_revision_attempts cap is "
            f"{MAX_REVISION_ATTEMPTS} (per ASSUM-002); got "
            f"{max_revision_attempts}. Raising the cap risks blowing the "
            f"per-turn latency budget."
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AttemptRecord:
    """Internal record of one Player attempt within the revision loop.

    Frozen + per-attempt-instantiated so the lowest-scoring selection
    routine cannot accidentally mutate an earlier record while picking
    the released reply. The :attr:`verifier_metadata` field captures
    the verifier output for the *rewritten* response stored on
    :attr:`response`, so on exhaustion the released attempt carries
    its own verifier signal forward into :class:`TurnResult`.
    """

    response: str
    verdict: CoachVerdict
    verifier_metadata: VerifierMetadata | None = None


class PlayerCoachOrchestrator:
    """Per-turn Player-Coach orchestrator (single public coroutine).

    Constructed fresh per turn — the class deliberately holds **no
    session-scoped mutable state**. Two concurrent
    :class:`PlayerCoachOrchestrator` instances can therefore run against
    two different sessions on a shared event loop without contamination
    (per the @edge-case @concurrency scenario): there is no class-level
    container into which one session's Coach observations could leak.

    The constructor takes the three component adapters
    (:class:`PlayerLike`, :class:`CoachLike`, optional
    :class:`QuoteVerifierLike`), an optional flag-emitter callback for
    session-end review markers, and the latency budget. All of these are
    DI parameters — production wiring lives in
    :mod:`study_tutor.mcp.adapter` and tests inject mocks.
    """

    def __init__(
        self,
        *,
        player: PlayerLike,
        coach: CoachLike,
        quote_verifier: QuoteVerifierLike | None = None,
        coach_handover: CoachHandover | None = None,
        on_flag: Callable[[str, dict[str, Any]], Awaitable[None] | None] | None = None,
        latency_budget_seconds: float = LATENCY_BUDGET_SECONDS,
        max_revision_attempts: int = MAX_REVISION_ATTEMPTS,
        coach_evaluation: Literal["sync", "async"] = "sync",
    ) -> None:
        """Wire the orchestrator with its components.

        Args:
            player: Player adapter (responds + revises).
            coach: Coach adapter (evaluates).
            quote_verifier: Optional quote-verifier adapter; when
                ``None`` the verifier step is skipped (used by tests
                that don't need it; production wiring always supplies
                one).
            coach_handover: Optional callable wiring TASK-PRV-005's
                :func:`verify_quotes` into the per-turn pipeline
                (TASK-PRV-006). Given
                ``(player_response, learner_message, session_state)`` it
                returns ``(response_for_coach, verifier_metadata)``. The
                ``learner_message`` arg (added by TASK-RAG-002) is the
                retrieval query — without it the closure cannot ground
                its primary-text RAG against what the learner asked.
                When supplied, the orchestrator runs it after every
                Player call (initial and revisions) and routes the
                rewritten response to the Coach instead of the raw
                Player text. ``None`` (the default) preserves the
                FEAT-PH1-003 behaviour where the Coach sees the raw
                Player response and ``TurnResult.verifier_metadata`` is
                ``None``.
            on_flag: Optional sync-or-async callback invoked when a turn
                is flagged for session-end review. The orchestrator does
                NOT block on the callback's return — it is a write-only
                observability sink.
            latency_budget_seconds: Per-turn wall-clock budget; turns
                exceeding this are flagged but still returned.
            max_revision_attempts: Hard cap on revision attempts.
                Defaults to :data:`MAX_REVISION_ATTEMPTS`.

        Raises:
            OrchestratorConfigurationError: If
                ``max_revision_attempts`` violates
                :func:`validate_loop_configuration`.
        """
        validate_loop_configuration(max_revision_attempts=max_revision_attempts)

        self._player = player
        self._coach = coach
        self._quote_verifier = quote_verifier
        self._coach_handover = coach_handover
        self._on_flag = on_flag
        self._latency_budget_seconds = latency_budget_seconds
        self._max_revision_attempts = max_revision_attempts
        # ADR-ARCH-026 D1: "async" returns the Player response immediately and
        # runs the Coach as a background monitor (no revision loop); "sync"
        # (default, backward-compatible) keeps the FEAT-PH1-003 pre-send gate.
        # Production wiring opts into "async" explicitly.
        self._coach_evaluation = coach_evaluation

    async def run_turn(
        self,
        session_state: Any,
        learner_message: str,
    ) -> TurnResult:
        """Run one Player-Coach turn end-to-end.

        Pipeline:

        1. Quote-verifier (if configured)
        2. Player.respond → Coach.evaluate
        3. If ``decision == "accept"``: return immediately (stable-turn
           guarantee — no further revision is emitted in its place per
           the @edge-case @revision-loop scenario at .feature line 400-404).
        4. If ``decision == "revise"``: ask Player to revise using
           **only** the structured :class:`RubricFeedback` from the
           verdict; re-evaluate; repeat up to ``max_revision_attempts``
           times.
        5. On exhaustion: release the **lowest-scoring** reply observed
           across the attempt sequence (per the @boundary @revision-loop
           scenario; preserves the diagnostic signal of "the system
           truly tried and these were the outputs").
        6. Coach-unreachable fallback: if the Coach raises (or returns
           no response within its budget), return the Player's response
           under the unevaluated-turn fallback policy with **no**
           revision attempts (per @negative @fallback scenario).
        7. Player-unreachable mid-revision fallback: if the Player
           provider becomes unavailable between attempts, fall back to
           the unevaluated-turn policy with the latest accepted/observed
           response and a provider-unavailable flag.

        Args:
            session_state: Opaque per-session payload threaded into
                every component call. The orchestrator does not read
                fields from it — components do — so its shape is
                whatever the caller wires up.
            learner_message: The learner's input for this turn.

        Returns:
            A :class:`TurnResult` describing the chosen reply, the
            decision tag, the duration, and any flags set.

        Raises:
            OrchestratorConfigurationError: If a session-start invariant
                fails (this is propagated rather than absorbed; it is a
                deployment error, not a runtime fallback condition).
        """
        start = time.monotonic()

        # Quote verifier runs first; failures here are not part of the
        # Coach/Player fallback policy — they propagate to the caller
        # which is the boundary that handles "we cannot serve this turn
        # at all". The verifier is the only step that can reject before
        # spending any tokens.
        if self._quote_verifier is not None:
            await self._quote_verifier.verify(
                session_state=session_state,
                learner_message=learner_message,
            )

        # First Player attempt.
        try:
            first_raw_response = await self._player.respond(
                session_state=session_state,
                learner_message=learner_message,
            )
        except PlayerUnavailableError as exc:
            return self._fallback_player_unavailable_first_attempt(
                start=start,
                reason=f"player_unavailable_first_attempt: {exc}",
            )

        # Coach-handover seam (TASK-PRV-006): run quote verification on
        # the Player response, then send the *rewritten* text to the
        # Coach with structured VerifierMetadata alongside. When no
        # handover is wired (FEAT-PH1-003 legacy callers / tests that
        # don't need it), the response is passed through unchanged and
        # ``verifier_metadata`` stays ``None``.
        first_response, first_metadata = self._apply_coach_handover(
            first_raw_response, learner_message, session_state
        )

        # ADR-ARCH-026 D1 — async Coach mode: the learner-visible response
        # (Player + synchronous quote-handover, D3) is ready. Hand the rubric
        # evaluation to a background monitor and return NOW; no revision loop
        # runs on the caller path. This is the streaming-ready shape — a
        # pre-send gate is incompatible with token streaming (D4).
        if self._coach_evaluation == "async":
            self._dispatch_async_coach(
                session_state=session_state,
                learner_message=learner_message,
                player_response=first_response,
                verifier_metadata=first_metadata,
            )
            return self._build_result(
                response=first_response,
                verdict=None,
                decision="deferred",
                attempts=1,
                start=start,
                flag_reason=None,
                verifier_metadata=first_metadata,
            )

        # Coach evaluation. If the Coach is unreachable here, we return
        # the Player's response under the unevaluated-turn fallback and
        # explicitly do NOT enter the revision loop (per the @negative
        # @fallback scenario; an absent Coach evaluation cannot drive
        # revision decisions).
        try:
            first_verdict = await self._evaluate_with_metadata(
                session_state=session_state,
                learner_message=learner_message,
                player_response=first_response,
                verifier_metadata=first_metadata,
            )
        except Exception as exc:  # noqa: BLE001 — boundary catch
            return await self._fallback_coach_unreachable(
                start=start,
                response=first_response,
                verifier_metadata=first_metadata,
                exc=exc,
            )

        # Stable-turn guarantee: once an attempt is accepted, return
        # immediately. No revision can be emitted "in its place" because
        # we never re-enter the loop after this branch.
        if first_verdict.decision == "accept":
            return self._build_result(
                response=first_response,
                verdict=first_verdict,
                decision="accept",
                attempts=1,
                start=start,
                flag_reason=None,
                verifier_metadata=first_metadata,
            )

        # Below-threshold first attempt: enter the bounded revision loop.
        attempts: list[_AttemptRecord] = [
            _AttemptRecord(
                response=first_response,
                verdict=first_verdict,
                verifier_metadata=first_metadata,
            )
        ]
        previous_response = first_response
        latest_feedback = list(first_verdict.rubric_feedback)

        for attempt_index in range(2, self._max_revision_attempts + 1):
            try:
                revised_raw_response = await self._player.revise(
                    session_state=session_state,
                    learner_message=learner_message,
                    previous_response=previous_response,
                    rubric_feedback=latest_feedback,
                )
            except PlayerUnavailableError as exc:
                return await self._fallback_player_unavailable_mid_revision(
                    start=start,
                    attempts=attempts,
                    exc=exc,
                )
            except Exception as exc:  # noqa: BLE001 — boundary catch
                # Defence-in-depth: any revision-time provider failure
                # is treated as Player-unavailable. Same fallback shape
                # as the typed-exception branch.
                return await self._fallback_player_unavailable_mid_revision(
                    start=start,
                    attempts=attempts,
                    exc=exc,
                )

            # Re-run the verifier on every revision: each revision is a
            # fresh Player generation that may introduce new quotes the
            # previous verification did not see (per TASK-PRV-006: the
            # Coach must always evaluate the rewritten text).
            revised_response, revised_metadata = self._apply_coach_handover(
                revised_raw_response, learner_message, session_state
            )

            try:
                revised_verdict = await self._evaluate_with_metadata(
                    session_state=session_state,
                    learner_message=learner_message,
                    player_response=revised_response,
                    verifier_metadata=revised_metadata,
                )
            except Exception as exc:  # noqa: BLE001 — boundary catch
                # Coach-unreachable mid-revision: same policy as
                # first-attempt Coach-unreachable — fall back without
                # any further revision attempts.
                return await self._fallback_coach_unreachable(
                    start=start,
                    response=revised_response,
                    verifier_metadata=revised_metadata,
                    exc=exc,
                )

            attempts.append(
                _AttemptRecord(
                    response=revised_response,
                    verdict=revised_verdict,
                    verifier_metadata=revised_metadata,
                )
            )

            if revised_verdict.decision == "accept":
                return self._build_result(
                    response=revised_response,
                    verdict=revised_verdict,
                    decision="accept",
                    attempts=attempt_index,
                    start=start,
                    flag_reason=None,
                    verifier_metadata=revised_metadata,
                )

            previous_response = revised_response
            latest_feedback = list(revised_verdict.rubric_feedback)

        # Exhaustion: pick the lowest-scoring attempt. Per the @boundary
        # @revision-loop scenario this preserves the diagnostic signal
        # that "the system tried, these were the outputs"; releasing the
        # latest attempt would mask a regression where revisions get
        # progressively worse.
        lowest = min(attempts, key=lambda record: record.verdict.weighted_total)
        flag_reason = (
            f"revision_exhausted: {self._max_revision_attempts} attempts, "
            f"released lowest weighted_total={lowest.verdict.weighted_total:.4f}"
        )
        await self._emit_flag(flag_reason, {"attempts": len(attempts)})
        return self._build_result(
            response=lowest.response,
            verdict=lowest.verdict,
            decision="exhausted",
            attempts=len(attempts),
            start=start,
            flag_reason=flag_reason,
            verifier_metadata=lowest.verifier_metadata,
        )

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Coach-handover helpers (TASK-PRV-006)
    # ------------------------------------------------------------------

    def _apply_coach_handover(
        self,
        raw_response: str,
        learner_message: str,
        session_state: Any,
    ) -> tuple[str, VerifierMetadata | None]:
        """Run the configured handover, or pass-through if none is wired.

        Returns ``(response_for_coach, verifier_metadata)``. When
        ``coach_handover`` is ``None`` (legacy callers), the raw
        response is returned unchanged with metadata ``None`` so existing
        FEAT-PH1-003 tests see no behavioural change. When wired, the
        callable's exceptions are *not* caught here — the handover's
        own contract (TASK-PRV-006) is to absorb verifier exceptions
        internally and return ``verifier_exception=True`` metadata; any
        exception escaping the handover is a bug at the handover layer
        and propagates to the caller for visibility.

        The ``learner_message`` argument (TASK-RAG-002) is forwarded
        verbatim to the handover so it can use it as the retrieval
        query.
        """
        if self._coach_handover is None:
            return raw_response, None
        return self._coach_handover(raw_response, learner_message, session_state)

    async def _evaluate_with_metadata(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
        verifier_metadata: VerifierMetadata | None,
    ) -> CoachVerdict:
        """Call ``coach.evaluate`` forwarding ``verifier_metadata`` when present.

        Older Coach adapters (FEAT-PH1-003 era) don't accept the
        ``verifier_metadata`` keyword. We only include it in the call
        when a handover actually produced one — that keeps existing
        adapters working unchanged while letting TASK-DTL-002's
        Coach implementation consume the structured metadata.
        """
        if verifier_metadata is not None:
            return await self._coach.evaluate(
                session_state=session_state,
                learner_message=learner_message,
                player_response=player_response,
                verifier_metadata=verifier_metadata,
            )
        return await self._coach.evaluate(
            session_state=session_state,
            learner_message=learner_message,
            player_response=player_response,
        )

    # ------------------------------------------------------------------
    # Async Coach monitor (ADR-ARCH-026 D1)
    # ------------------------------------------------------------------

    def _dispatch_async_coach(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
        verifier_metadata: VerifierMetadata | None,
    ) -> None:
        """Fire-and-forget the Coach evaluation off the caller path.

        The learner already received ``player_response``; the Coach here is a
        background MONITOR that evaluates once (no revision) and emits an
        ``on_flag`` review marker for below-threshold turns. Mirrors the
        ADR-ARCH-019 fire-and-forget discipline. ``run_turn`` is only awaited
        inside a running loop, so ``ensure_future`` succeeds normally; if a
        loop is somehow absent we close the coroutine rather than leak it —
        the monitor is best-effort and the response is already delivered.
        """
        coro = self._run_async_coach(
            session_state=session_state,
            learner_message=learner_message,
            player_response=player_response,
            verifier_metadata=verifier_metadata,
        )
        try:
            task = asyncio.ensure_future(coro)
        except RuntimeError:
            coro.close()
            return
        _BACKGROUND_COACH_TASKS.add(task)
        task.add_done_callback(_background_coach_done)

    async def _run_async_coach(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
        verifier_metadata: VerifierMetadata | None,
    ) -> None:
        """Background Coach body: evaluate once, flag below-threshold turns.

        Never raises — the response is already with the learner, so any
        failure is logged and suppressed (the done-callback is the backstop).
        A below-threshold verdict is surfaced via ``on_flag`` for session-end
        review: the same signal that used to drive a live revision, now
        observational (ASSUM-001 threshold, ADR-ARCH-026 D1).
        """
        try:
            verdict = await self._evaluate_with_metadata(
                session_state=session_state,
                learner_message=learner_message,
                player_response=player_response,
                verifier_metadata=verifier_metadata,
            )
        except Exception as exc:  # noqa: BLE001 — background monitor never raises
            logger.warning(
                "background Coach evaluation failed (non-fatal — response delivered)",
                extra={
                    "event": "orchestrator_async_coach_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return
        if verdict.decision != "accept":
            await self._emit_flag(
                f"async_coach_below_threshold: decision={verdict.decision} "
                f"weighted_total={verdict.weighted_total:.4f}",
                {"decision": verdict.decision},
            )

    async def _fallback_coach_unreachable(
        self,
        *,
        start: float,
        response: str,
        exc: BaseException,
        verifier_metadata: VerifierMetadata | None = None,
    ) -> TurnResult:
        """Return the Player's response under the Coach-unreachable policy.

        Per the @negative @fallback scenario: when Coach evaluation
        cannot complete, the Player's response is returned to the
        learner with the turn flagged for session-end review and **no**
        revision attempts made. We log with traceback so observability
        captures the failure mode without silently swallowing it.
        """
        logger.warning(
            "Coach unreachable — falling back to unevaluated Player response",
            extra={
                "event": "orchestrator_coach_unreachable",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        flag_reason = f"coach_unreachable: {type(exc).__name__}: {exc}"
        await self._emit_flag(flag_reason, {})
        return self._build_result(
            response=response,
            verdict=None,
            decision="fallback",
            attempts=1,
            start=start,
            flag_reason=flag_reason,
            verifier_metadata=verifier_metadata,
        )

    async def _fallback_player_unavailable_mid_revision(
        self,
        *,
        start: float,
        attempts: list[_AttemptRecord],
        exc: BaseException,
    ) -> TurnResult:
        """Player provider died between the first response and a revision.

        Per the @edge-case @integration @fallback scenario: degrade to
        the unevaluated-turn policy using the most recent
        already-collected response (the previous attempt is the
        learner's best available option since the revision never came
        back).
        """
        logger.warning(
            "Player unavailable mid-revision — falling back to last response",
            extra={
                "event": "orchestrator_player_unavailable_mid_revision",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "completed_attempts": len(attempts),
            },
        )
        last = attempts[-1]
        flag_reason = (
            f"player_unavailable_mid_revision: {type(exc).__name__}: {exc}"
        )
        await self._emit_flag(flag_reason, {"completed_attempts": len(attempts)})
        return self._build_result(
            response=last.response,
            verdict=last.verdict,
            decision="fallback",
            attempts=len(attempts),
            start=start,
            flag_reason=flag_reason,
            verifier_metadata=last.verifier_metadata,
        )

    def _fallback_player_unavailable_first_attempt(
        self,
        *,
        start: float,
        reason: str,
    ) -> TurnResult:
        """Player died before producing any response at all.

        We have no learner-facing text to release. The contract is
        ``run_turn`` always returns a :class:`TurnResult`; the consumer
        (``tutor_turn`` MCP handler) decides whether to render this as
        a tool error or as a graceful "please try again" message.
        """
        logger.warning(
            "Player unavailable on first attempt — empty fallback",
            extra={
                "event": "orchestrator_player_unavailable_first_attempt",
                "reason": reason,
            },
        )
        # Best-effort flag emission; we cannot await here because this
        # helper is sync (called from the synchronous-caught first-attempt
        # branch). Schedule the callback as a task instead.
        if self._on_flag is not None:
            try:
                result = self._on_flag(reason, {})
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as exc:  # noqa: BLE001 — flag must not crash turn
                logger.warning(
                    "on_flag callback raised; suppressed: %s", exc
                )
        return self._build_result(
            response="",
            verdict=None,
            decision="fallback",
            attempts=0,
            start=start,
            flag_reason=reason,
        )

    # ------------------------------------------------------------------
    # Result + flag helpers
    # ------------------------------------------------------------------

    def _build_result(
        self,
        *,
        response: str,
        verdict: CoachVerdict | None,
        decision: TurnDecision,
        attempts: int,
        start: float,
        flag_reason: str | None,
        verifier_metadata: VerifierMetadata | None = None,
    ) -> TurnResult:
        """Assemble a :class:`TurnResult`, applying the latency-budget flag.

        Latency over-budget is additive to any caller-supplied
        ``flag_reason`` — it is a separate observability signal and
        should never silently override an existing flag (e.g. a
        Coach-unreachable flag must remain visible alongside an
        over-budget flag).
        """
        duration = time.monotonic() - start
        over_budget = duration > self._latency_budget_seconds
        if over_budget:
            latency_reason = (
                f"latency_over_budget: {duration:.4f}s > "
                f"{self._latency_budget_seconds:.2f}s"
            )
            logger.warning(
                "turn exceeded latency budget",
                extra={
                    "event": "orchestrator_latency_over_budget",
                    "duration_seconds": duration,
                    "budget_seconds": self._latency_budget_seconds,
                },
            )
            if flag_reason is None:
                flag_reason = latency_reason
            else:
                flag_reason = f"{flag_reason}; {latency_reason}"

        return TurnResult(
            response=response,
            decision=decision,
            verdict=verdict,
            attempts=attempts,
            flagged_for_review=flag_reason is not None,
            flag_reason=flag_reason,
            duration_seconds=duration,
            verifier_metadata=verifier_metadata,
        )

    async def _emit_flag(self, reason: str, extra: dict[str, Any]) -> None:
        """Invoke the optional ``on_flag`` callback without blocking the turn.

        We tolerate sync and async callbacks; failures inside the
        callback are logged and suppressed — observability sinks must
        never crash the learner-facing path.
        """
        if self._on_flag is None:
            return
        try:
            result = self._on_flag(reason, extra)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001 — flag must not crash turn
            logger.warning(
                "on_flag callback raised; suppressed",
                extra={
                    "event": "orchestrator_flag_callback_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )


__all__ = [
    "LATENCY_BUDGET_SECONDS",
    "MAX_REVISION_ATTEMPTS",
    "CoachHandover",
    "CoachLike",
    "CoachUnavailableError",
    "OrchestratorConfigurationError",
    "PlayerCoachOrchestrator",
    "PlayerLike",
    "PlayerUnavailableError",
    "QuoteVerifierLike",
    "TurnDecision",
    "TurnResult",
    "validate_loop_configuration",
]
