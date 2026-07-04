"""MCP adapter for the tutor role (Phase 0 + Phase 1 wiring).

Registers four tools on the FastMCP server:

* ``tutor_start_session`` — sync classification (per ADR-ARCH-017); mints
  ``session_id`` *before* the deterministic planner is invoked so a
  planner failure or timeout never blocks session creation. The plan is
  produced by :func:`study_tutor.planner.pipeline.plan_session` wrapped in
  a 2.0s outer ``asyncio.wait_for`` guard (ASSUM-006, signed off
  2026-04-29). Any failure mode — timeout, internal exception, unknown
  learner — degrades to :func:`_baseline_plan(False)` rather than
  propagating; this is the single graceful-degradation boundary for the
  planner pipeline.
* ``tutor_turn`` — sync; generates one tutor reply per user message.
* ``tutor_session_status`` — sync; pure read of session state.
* ``tutor_session_end`` — sync caller-facing return; delegates to
  :func:`study_tutor.tutoring.session_end.perform_session_end` for the
  DDR-003-ordered ``session.completed`` emit + F3 Graphiti write
  fire-and-forget dispatch (TASK-GR-WIRE BLOCK-3a). Returns within the
  ASSUM-004 2 s wall-clock budget regardless of Graphiti latency per
  ADR-ARCH-019.

SR-03: every handler resolves the provider via ``_default_player_model()``
at call time — no module-level provider hard-coding.

SR-07: ``tutor_session_end`` description is *only* ``"marks session ended"``.
The Phase 1 Graphiti write happens inside ``perform_session_end`` as a
fire-and-forget task — not user-facing text.

Concurrency note (TASK-DSP-006): the per-instance ``_plan_sessions`` dict
is keyed by ``session.session_id``. UUID4 collision probability is
effectively zero, and :class:`SessionPlan` is ``frozen=True``, so no
explicit lock is required — concurrent ``tutor_start_session`` invocations
for the same learner produce two distinct UUIDs and cannot overwrite each
other's plan.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from datetime import datetime, timezone

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.planner.pipeline import plan_session
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.completion import build_session_completion
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)
from study_tutor.session.provider import get_session_service
from study_tutor.session.service import SessionService, TutorReply
from study_tutor.session.wiring import resolve_student_id
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator
from study_tutor.tutoring.session_end import EventBus, SESSION_COMPLETED_EVENT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outer-guard configuration (ASSUM-006)
# ---------------------------------------------------------------------------

#: TASK-DSP-006 — env var that controls the *outer* MCP-handler budget
#: (ASSUM-006, signed off 2026-04-29). Default 2.0s. Independently
#: configurable from the inner read timeout
#: (``STUDENT_MODEL_READ_TIMEOUT_SEC``, ASSUM-007) so tests can patch one
#: boundary without affecting the other. The outer guard is the binding
#: constraint in the default configuration.
_PLANNER_HANDLER_BUDGET_ENV: str = "PLANNER_HANDLER_BUDGET_SEC"
_PLANNER_HANDLER_BUDGET_DEFAULT: float = 2.0


def _planner_handler_budget_sec() -> float:
    """Return the outer ``plan_session`` budget for ``tutor_start_session``.

    Reads :data:`_PLANNER_HANDLER_BUDGET_ENV` from the environment at
    *call* time so test patching of ``os.environ`` flows through without
    a process restart. Falls back to
    :data:`_PLANNER_HANDLER_BUDGET_DEFAULT` when the var is unset or
    unparseable.
    """
    raw = os.environ.get(_PLANNER_HANDLER_BUDGET_ENV)
    if raw is None:
        return _PLANNER_HANDLER_BUDGET_DEFAULT
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "ignoring unparseable %s=%r; using default %.1fs",
            _PLANNER_HANDLER_BUDGET_ENV,
            raw,
            _PLANNER_HANDLER_BUDGET_DEFAULT,
        )
        return _PLANNER_HANDLER_BUDGET_DEFAULT


def _plan_summary(plan: SessionPlan) -> dict[str, Any]:
    """Project a :class:`SessionPlan` into the MCP-response summary shape.

    The summary surfaces the fields a learner-facing client needs to render
    the first session turn — ``topic_name`` and ``rule_selected`` are
    required by AC-003; the rest are included so observability and the
    coach side can audit the plan without a second round-trip.
    """
    return {
        "topic_name": plan.topic_name,
        "rule_selected": plan.rule_selected,
        "fallback_used": plan.fallback_used,
        "focus_aos": list(plan.focus_aos),
        "opening_prompt": plan.opening_prompt,
        "suggested_duration_minutes": plan.suggested_duration_minutes,
        "rationale": plan.rationale,
        "related_misconceptions": list(plan.related_misconceptions),
        "ao_mapping_found": plan.ao_mapping_found,
        "learner_state_available": plan.learner_state_available,
    }


class MCPAdapter:
    """Dispatches MCP tool calls for the tutor role."""

    def __init__(
        self,
        role_config: RoleConfig,
        session_service: SessionService | None = None,
        orchestrator_factory: Any = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._role = role_config
        self._session_service = session_service or get_session_service()
        if self._session_service is None:
            raise RuntimeError(
                "MCPAdapter requires a SessionService — call "
                "session.wiring.build_session_service at startup or inject one"
            )
        # Store the StudentStore reference for build_session_completion.
        self._student_store = self._session_service._resolve_store()
        self._player_prompt = role_config.load_player_prompt()
        # Track warm-up task so pytest/GC don't complain about orphans.
        self._warmup_tasks: set[asyncio.Task[Any]] = set()
        # Per-instance plan store (TASK-DSP-006). Keyed by session_id;
        # holds the immutable :class:`SessionPlan` produced by
        # :func:`plan_session` for subsequent ``tutor_turn`` consumption.
        self._plan_sessions: dict[str, SessionPlan] = {}
        # TASK-DTL-003: optional per-turn orchestrator factory. When
        # supplied, ``tutor_turn`` builds a fresh
        # :class:`PlayerCoachOrchestrator` per call (per-session
        # isolation invariant) and routes the turn through it. When
        # ``None``, the Phase 0 single-LLM path is preserved so this
        # change is backward-compatible.
        self._orchestrator_factory = orchestrator_factory
        # TASK-SMP3-06: EventBus for session.completed emission.
        # Defaults to a fresh empty bus so existing tests continue to work.
        self._event_bus = event_bus if event_bus is not None else EventBus()

        # TASK-LCA-004 — boot-time smoke check (AC-LCA-02 / AC-LCA-08).
        #
        # When an orchestrator factory is wired (Phase-1 production path
        # via ``cli/main.py:serve``), invoke it once and discard the
        # result so any structural misconfiguration — most importantly
        # the same-provider rejection raised by
        # :func:`validate_coach_config` and the unset-env-var rejection
        # raised by :func:`_default_coach_model` — surfaces at server
        # boot rather than at first user turn. This converts a latent
        # "first turn 500s with `LLMProviderError`" failure mode into a
        # fail-fast boot-time error that the operator sees in the
        # systemd/launchd log before any client connects.
        #
        # The Phase-0 backward-compatible path (``orchestrator_factory
        # is None``) intentionally skips this check: there is no factory
        # to invoke, no Coach to validate, and existing tests + the
        # Phase-0 single-LLM smoke path must continue to construct the
        # adapter without supplying one.
        if self._orchestrator_factory is not None:
            self._orchestrator_factory()  # noqa: F841 — discarded; smoke-check invocation only

            # TASK-RAG-002 — RAG boot smoke. The collection provider is
            # wired by ``cli.rag_wiring.build_rag_providers`` at serve
            # startup. If wired, verify it returns a non-None
            # collection; if unwired (graceful-degradation envelope),
            # log structured ``rag_disabled`` so the operator's log pane
            # shows the state. Gated on ``orchestrator_factory is not
            # None`` because the Phase-0 backward-compat path doesn't
            # build orchestrators (and therefore doesn't run RAG).
            from study_tutor.knowledge.retrieval import (
                get_collection_provider as _get_cp,
            )

            provider = _get_cp()
            if provider is not None:
                if provider() is None:
                    logger.warning(
                        "event=rag_disabled "
                        "reason=collection_provider_returned_none"
                    )
            else:
                logger.warning(
                    "event=rag_disabled reason=collection_provider_unwired"
                )

    async def tutor_start_session(
        self,
        student_id: str,
        topic_override: str | None = None,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Create a session and plan it via the deterministic planner.

        TASK-SMP3-06: session creation is now durable via SessionService.
        The session is minted *before* the planner is invoked (AC-002) so
        a planner failure or timeout never blocks session creation. Every
        failure mode below (timeout, internal exception, unknown learner)
        collapses to :func:`_baseline_plan(False) <study_tutor.planner.types._baseline_plan>`
        rather than propagating an exception (AC-001 / AC-009).

        The 2.0s outer guard (:data:`_PLANNER_HANDLER_BUDGET_DEFAULT`,
        ASSUM-006) is the binding constraint by design.

        Args:
            student_id: Planner learner slug, e.g. ``"lilymay"``. This is
                the PLANNER input (today's subject value per ASSUM-002),
                NOT the ownership identity.
            topic_override: Optional learner-supplied topic. When set,
                Rule 1 short-circuits the rule list inside
                :func:`plan_session`.
            player_model: Optional override for the LLM provider used by
                the warm-up call. Defaults to
                :func:`_default_player_model`.

        Returns:
            ``{"session_id": <uuid4>, "plan_summary": {...}}`` — see
            :func:`_plan_summary` for the summary shape.
        """
        # TASK-SMP3-06: resolve the single-user identity (ownership key).
        # This is the OWNERSHIP identity, kept SEPARATE from the planner
        # slug (ASSUM-001).
        identity = resolve_student_id()

        # Mint session_id *before* the planner is invoked (AC-002).
        # SessionService.start_session creates the durable session.
        result = await self._session_service.start_session(
            student_id=identity,
            subject=student_id,
            topic=topic_override,
        )
        session_id = result.session_id

        # Fire-and-forget LLM warm-up so the first ``tutor_turn`` doesn't
        # pay cold-start latency. Independent of the planner so a planner
        # timeout doesn't cancel the warm-up.
        provider = player_model or _default_player_model()
        warmup = asyncio.create_task(
            self._warm_up(provider), name=f"warmup-{session_id}"
        )
        self._warmup_tasks.add(warmup)
        warmup.add_done_callback(self._warmup_tasks.discard)

        budget = _planner_handler_budget_sec()
        try:
            plan = await asyncio.wait_for(
                plan_session(student_id, topic_override),
                timeout=budget,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "planner exceeded %.2fs handler budget — degrading to "
                "baseline plan",
                budget,
                extra={
                    "event": "planner_handler_budget_exceeded",
                    "student_id": student_id,
                    "session_id": session_id,
                    "budget_sec": budget,
                },
            )
            plan = _baseline_plan(learner_state_available=False)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            # Any non-timeout failure mode: log with traceback (so
            # observability captures the root cause) and degrade. Never
            # re-raise — the MCP contract is "always return a plan".
            logger.exception(
                "planner internal error — degrading to baseline plan",
                extra={
                    "event": "planner_internal_error",
                    "student_id": student_id,
                    "session_id": session_id,
                    "error": str(exc),
                },
            )
            plan = _baseline_plan(learner_state_available=False)

        self._plan_sessions[session_id] = plan
        return {
            "session_id": session_id,
            "plan_summary": _plan_summary(plan),
        }

    async def tutor_turn(
        self,
        session_id: str,
        user_message: str,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Generate one tutor reply for ``user_message`` within the session.

        TASK-SMP3-06: now delegates to SessionService.turn with the
        orchestrator/Phase-0 loop wrapped as reply_fn.
        """
        identity = resolve_student_id()

        # Build the reply_fn that wraps the orchestrator/Phase-0 loop.
        # SessionService.turn will call this after persisting the user turn.
        async def reply_fn(msg: str) -> TutorReply:
            plan = self._plan_sessions.get(session_id)
            # TASK-DTL-003: route through PlayerCoachOrchestrator when a
            # factory is wired (production Phase 1 path).
            if self._orchestrator_factory is not None:
                # TASK-LCA-003: build the typed SessionState boundary object
                # from the cached SessionPlan. Optional fields default to
                # ``None`` / ``()`` so a baseline-degraded plan still yields
                # a valid construction (ASSUM-LCA-007).
                text_name_value = (
                    getattr(plan, "text_name", None) if plan is not None else None
                )
                session_state = SessionState(
                    session_id=session_id,
                    student_id=identity,
                    text_name=text_name_value if text_name_value else None,
                    topic=plan.topic_name if plan is not None else None,
                    focus_aos=tuple(plan.focus_aos) if plan is not None else (),
                    mode="tutor",
                )
                orchestrator: PlayerCoachOrchestrator = self._orchestrator_factory()
                turn_result = await orchestrator.run_turn(
                    session_state=session_state,
                    learner_message=msg,
                )
                return TutorReply(
                    response=turn_result.response,
                    metadata={
                        "decision": turn_result.decision,
                        "attempts": turn_result.attempts,
                        "flagged_for_review": turn_result.flagged_for_review,
                        "duration_seconds": turn_result.duration_seconds,
                    },
                )

            # Phase 0 path: single-LLM reply.
            provider = player_model or _default_player_model()
            client = LLMClient(provider=provider)
            response = await asyncio.to_thread(
                client.generate, msg, self._player_prompt
            )
            return TutorReply(response=response)

        # Delegate to SessionService.turn, mapping exceptions to the
        # existing error envelopes.
        try:
            result = await self._session_service.turn(
                student_id=identity,
                session_id=session_id,
                user_message=user_message,
                reply_fn=reply_fn,
            )
        except SessionNotFoundError:
            return _session_not_found(session_id)
        except SessionEnded:
            return {
                "error": f"Session '{session_id}' has ended.",
                "error_type": "SessionEnded",
            }
        except SessionForbidden as exc:
            return {
                "error": str(exc),
                "error_type": "SessionForbidden",
            }

        # Re-project metadata into the unchanged response shape.
        if result.metadata:
            return {
                "tutor_response": result.tutor_response,
                **result.metadata,
            }
        return {"tutor_response": result.tutor_response}

    async def tutor_session_status(self, session_id: str) -> dict[str, Any]:
        """Return current session state.

        TASK-SMP3-06: now delegates to SessionService.session_status.
        """
        identity = resolve_student_id()
        try:
            status = await self._session_service.session_status(
                student_id=identity,
                session_id=session_id,
            )
        except SessionNotFoundError:
            return _session_not_found(session_id)
        except SessionForbidden as exc:
            return {
                "error": str(exc),
                "error_type": "SessionForbidden",
            }

        return {
            "session_id": status.session_id,
            "status": status.status,
            "turn_count": status.turn_count,
            "started_at": status.started_at.isoformat(),
        }

    async def tutor_session_end(self, session_id: str) -> dict[str, Any]:
        """Mark the session ended (TASK-SMP3-06).

        Now delegates to SessionService.end_session with a durable
        completion payload. The I-T6 zero-turn invariant is preserved:
        sessions ended before any tutor turn flip status to ``"ended"``
        but do NOT emit ``session.completed`` and do NOT write learner-state
        deltas (``completion=None``).

        DDR-003 ordering: ``session.completed`` is emitted BEFORE
        SessionService.end_session persists the completion (emit-before-write).

        ``topics_covered`` and ``aos_exercised`` are sourced from the
        cached :class:`SessionPlan` for ``session_id``. If no plan is
        cached, both default to empty.
        """
        identity = resolve_student_id()

        # Load the session to check turn count and get session data.
        try:
            status = await self._session_service.session_status(
                student_id=identity,
                session_id=session_id,
            )
        except SessionNotFoundError:
            return _session_not_found(session_id)
        except SessionForbidden as exc:
            return {
                "error": str(exc),
                "error_type": "SessionForbidden",
            }

        # Extract plan data for topics_covered and aos_exercised.
        plan = self._plan_sessions.get(session_id)
        if plan is not None:
            topic = plan.topic_name
            aos_exercised = list(plan.focus_aos)
        else:
            # Stale-lookup fallback: a tutor_session_end called for a
            # session_id never seen by this process's tutor_start_session
            # (e.g. server restart between the two endpoints) is still a
            # valid graceful path. Use empty defaults.
            topic = status.student_id  # Fallback to subject
            aos_exercised = []

        # I-T6 zero-turn invariant: sessions with no turns do NOT emit
        # session.completed and do NOT write learner-state deltas.
        completion = None
        if status.turn_count > 0:
            # Build the SessionCompletion via the pure store-backed producer.
            # Assumes all turns are (user, tutor) pairs; student_turn_count
            # is half the total.
            student_turn_count = status.turn_count // 2
            completion = await build_session_completion(
                store=self._student_store,
                student_id=identity,
                topic=topic,
                student_turn_count=student_turn_count,
                aos_scaffolded=aos_exercised,
                misconceptions_per_topic={},  # ASSUM-007 placeholder
            )

            # DDR-003: emit session.completed BEFORE the SessionService write.
            # Preserve the exact payload shape from session_end.py:440-450.
            ended_at = datetime.now(timezone.utc)
            payload: dict[str, Any] = {
                "session_id": session_id,
                "student_id": identity,
                "subject_slug": status.student_id,
                "topics_covered": [topic],
                "aos_exercised": aos_exercised,
                "turn_count": status.turn_count,
                "narrative_summary": "",  # Not produced by this cutover
                "started_at": status.started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
            }
            await self._event_bus.emit(SESSION_COMPLETED_EVENT, payload)

        # Delegate to SessionService.end_session with the completion.
        try:
            await self._session_service.end_session(
                student_id=identity,
                session_id=session_id,
                completion=completion,
            )
        except SessionNotFoundError:
            return _session_not_found(session_id)
        except SessionForbidden as exc:
            return {
                "error": str(exc),
                "error_type": "SessionForbidden",
            }

        return {"session_id": session_id, "status": "ended"}

    async def _warm_up(self, provider: str) -> None:
        """Fire an empty generate() to prime the Ollama model into memory."""
        try:
            client = LLMClient(provider=provider)
            await asyncio.to_thread(client.generate, "", None)
        except Exception as exc:  # noqa: BLE001 — warm-up must never crash
            logger.debug("Warm-up call failed (non-fatal): %s", exc)


def _session_not_found(session_id: str) -> dict[str, Any]:
    return {
        "error": f"Session '{session_id}' not found.",
        "error_type": "SessionNotFoundError",
    }
