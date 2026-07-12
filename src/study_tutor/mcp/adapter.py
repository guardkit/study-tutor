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
  :meth:`study_tutor.session.service.SessionService.end_session` for the
  DDR-003-ordered ``session.completed`` emit followed by the
  ``StudentStore.record_session_completion`` write (emit-before-write). The
  store write is a synchronous transactional Postgres upsert (ADR-ARCH-023),
  and the handler returns within the ASSUM-004 2 s wall-clock budget.

SR-03: every handler resolves the provider via ``_default_player_model()``
at call time — no module-level provider hard-coding.

SR-07: ``tutor_session_end`` description is *only* ``"marks session ended"``.
The store write happens inside ``SessionService.end_session`` as a synchronous
transactional Postgres write — not user-facing text.

S-R3 §2.1 / D14: planning and completion assembly moved into the core
(``SessionService`` / the session row). The adapter no longer holds a per-adapter
plan cache — ``tutor_turn`` / ``tutor_session_end`` read the persisted session
record — so it carries no planning state the HTTP path lacks.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from datetime import datetime, timezone

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.planner.types import SessionPlan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)
from study_tutor.session.provider import get_session_service
from study_tutor.session.service import SessionService, TutorReply
from study_tutor.session.wiring import resolve_student_id
from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator
from study_tutor.tutoring.session_end import EventBus, SESSION_COMPLETED_EVENT

logger = logging.getLogger(__name__)


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
        # S-R3 §2.1 / D14: planning + its plan facts live in the core
        # (SessionService / the session row), NOT in a per-adapter cache. The
        # former ``self._plan_sessions`` dict is deleted — ``tutor_turn`` /
        # ``tutor_session_end`` read the persisted session record instead, so
        # the MCP adapter holds no planning state the HTTP path lacks.
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

        # S-R3 §2.1 / D14: planning now lives in SessionService.start_session
        # (under the 2.0s budget/degrade boundary, keyed by the ownership
        # identity). The adapter is a thin skin: it delegates and projects the
        # service's plan into the MCP ``plan_summary`` shape. ``student_id`` (the
        # tool arg / subject slug) is passed as ``topic``-less ``subject``; the
        # learner override rides on ``topic``.
        result = await self._session_service.start_session(
            student_id=identity,
            subject=student_id,
            topic=topic_override,
        )
        session_id = result.session_id

        # Fire-and-forget LLM warm-up so the first ``tutor_turn`` doesn't
        # pay cold-start latency.
        provider = player_model or _default_player_model()
        warmup = asyncio.create_task(
            self._warm_up(provider), name=f"warmup-{session_id}"
        )
        self._warmup_tasks.add(warmup)
        warmup.add_done_callback(self._warmup_tasks.discard)

        return {
            "session_id": session_id,
            "plan_summary": _plan_summary(result.plan)
            if result.plan is not None
            else {},
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
            # TASK-DTL-003: route through PlayerCoachOrchestrator when a
            # factory is wired (production Phase 1 path).
            if self._orchestrator_factory is not None:
                # S-R4 §2.5/§2.6 / D14: the typed SessionState boundary — plan
                # facts, player-context fields and the in-session transcript
                # window — is assembled in the core
                # (``SessionService.build_turn_session_state``), NOT here, so
                # MCP and HTTP feed the Player byte-identical context. The
                # adapter stays a thin tool-shape skin.
                session_state = (
                    await self._session_service.build_turn_session_state(
                        student_id=identity,
                        session_id=session_id,
                    )
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
        """Mark the session ended (TASK-SMP3-06; S-R3 §2.4 cutover).

        Completion **assembly now lives in** ``SessionService.end_session``
        (D14) — the adapter no longer builds a ``SessionCompletion`` and holds no
        plan cache. It reads the persisted session row for the event payload,
        emits ``session.completed`` (DDR-003 emit-before-write, unchanged this
        stage), then delegates to the service, passing only its topic hint (the
        subject slug). ``topics_covered`` / ``aos_exercised`` are sourced from
        the persisted plan facts (``topic`` + ``aos_scaffolded``).

        I-T6 zero-turn invariant preserved: a session ended before any tutor turn
        flips status to ``"ended"`` but does NOT emit ``session.completed`` and
        writes no learner-state deltas (the service skips the completion for
        ``turn_count == 0``).
        """
        identity = resolve_student_id()

        # Load the persisted session row (turn count + plan facts for the event).
        record = await self._student_store.get_session(session_id)
        if record is None:
            return _session_not_found(session_id)
        if record.student_id != identity:
            return {
                "error": f"session {session_id!r} is not owned by {identity!r}",
                "error_type": "SessionForbidden",
            }

        topic = record.topic or record.subject
        aos_exercised = list(record.aos_scaffolded)

        # I-T6 zero-turn invariant: sessions with no turns do NOT emit
        # session.completed. The service independently skips the completion
        # write for zero-turn sessions.
        if record.turn_count > 0:
            # DDR-003: emit session.completed BEFORE the SessionService write.
            ended_at = datetime.now(timezone.utc)
            payload: dict[str, Any] = {
                "session_id": session_id,
                "student_id": identity,
                "subject_slug": record.subject,
                "topics_covered": [topic],
                "aos_exercised": aos_exercised,
                "turn_count": record.turn_count,
                "narrative_summary": "",  # Not produced by this cutover
                "started_at": record.started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
            }
            await self._event_bus.emit(SESSION_COMPLETED_EVENT, payload)

        # Delegate: the service assembles + writes the completion from the
        # persisted row (D14). MCP passes only its topic hint (the subject).
        try:
            await self._session_service.end_session(
                student_id=identity,
                session_id=session_id,
                topic_hint=record.subject,
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
