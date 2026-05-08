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

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.queries import (
    Phase1MinimalDeltaPolicy,
    record_topic_confidence_update,
)
from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.planner.pipeline import plan_session
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.tutor_session import (
    SessionNotFoundError,
    SessionStore,
    get_default_store,
)
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator
from study_tutor.tutoring.session_end import EventBus, perform_session_end

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
        store: SessionStore | None = None,
        orchestrator_factory: Any = None,
        write_helper: GraphitiWriteHelper | None = None,
        event_bus: EventBus | None = None,
        graphiti_client: Any | None = None,
    ) -> None:
        self._role = role_config
        self._store = store or get_default_store()
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
        # TASK-GR-WIRE BLOCK-3a: session-end Graphiti writeback dependencies.
        # All three default to ``None`` / a fresh empty bus so existing tests
        # (and any caller that doesn't need Graphiti persistence) continue to
        # work — ``perform_session_end`` accepts ``write_helper=None`` as a
        # graceful no-op for the F3 dispatch, and an unsubscribed
        # :class:`EventBus` is functionally a no-op for the bus emit. The
        # ``graphiti_client`` is held for future read-back uses (e.g.
        # ``mcp__graphiti__get_episodes`` confirmation paths) and is
        # otherwise unused on this code path.
        self._write_helper = write_helper
        self._event_bus = event_bus if event_bus is not None else EventBus()
        self._graphiti_client = graphiti_client

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

        TASK-DSP-006: this is the **graceful-degradation boundary** for
        the planner pipeline. ``session_id`` is minted *before* the
        planner is invoked (AC-002) so a planner failure or timeout
        never blocks session creation. Every failure mode below
        (timeout, internal exception, unknown learner) collapses to
        :func:`_baseline_plan(False) <study_tutor.planner.types._baseline_plan>`
        rather than propagating an exception (AC-001 / AC-009).

        The 2.0s outer guard
        (:data:`_PLANNER_HANDLER_BUDGET_DEFAULT`, ASSUM-006) is the
        binding constraint by design: with the default configuration it
        always fires before the inner 5.0s student-model read timeout
        (``STUDENT_MODEL_READ_TIMEOUT_SEC``, ASSUM-007). The inner
        timeout fires first only when ``PLANNER_HANDLER_BUDGET_SEC`` is
        enlarged — typically only in tests.

        Args:
            student_id: Stable learner slug, e.g. ``"lilymay"``.
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
        # Mint session_id *before* the planner is invoked (AC-002). The
        # legacy session-store create() path doubles as Phase 0
        # compatibility for ``tutor_turn`` / ``tutor_session_end`` which
        # still look up sessions through ``self._store``.
        session = self._store.create(
            subject=student_id, topic=topic_override
        )
        session_id = session.session_id

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
        """Generate one tutor reply for ``user_message`` within the session."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        if session.status == "ended":
            return {
                "error": f"Session '{session_id}' has ended.",
                "error_type": "SessionEnded",
            }

        self._store.append_turn(session_id, "user", user_message)

        # TASK-DTL-003: route through PlayerCoachOrchestrator when a
        # factory is wired (production Phase 1 path). Per-turn
        # construction guarantees concurrency isolation — two concurrent
        # ``tutor_turn`` calls get two independent orchestrator
        # instances and cannot contaminate each other's Coach
        # observations.
        if self._orchestrator_factory is not None:
            # TASK-LCA-003: build the typed SessionState boundary object
            # from the cached SessionPlan + TutorSession. This is the
            # producer for the §4 SessionState integration contract
            # consumed by TASK-LCA-001 (Player adapter) and TASK-LCA-002
            # (Coach adapter). Optional fields default to ``None`` /
            # ``()`` so a baseline-degraded plan (no ``text_name`` /
            # missing ``focus_aos``) still yields a valid construction
            # (ASSUM-LCA-007).
            plan = self._plan_sessions.get(session_id)
            text_name_value = (
                getattr(plan, "text_name", None) if plan is not None else None
            )
            session_state = SessionState(
                session_id=session_id,
                student_id=session.subject,
                text_name=text_name_value if text_name_value else None,
                topic=plan.topic_name if plan is not None else None,
                focus_aos=tuple(plan.focus_aos) if plan is not None else (),
                mode="tutor",
            )
            orchestrator: PlayerCoachOrchestrator = self._orchestrator_factory()
            turn_result = await orchestrator.run_turn(
                session_state=session_state,
                learner_message=user_message,
            )
            self._store.append_turn(session_id, "tutor", turn_result.response)
            return {
                "tutor_response": turn_result.response,
                "decision": turn_result.decision,
                "attempts": turn_result.attempts,
                "flagged_for_review": turn_result.flagged_for_review,
                "duration_seconds": turn_result.duration_seconds,
            }

        provider = player_model or _default_player_model()
        client = LLMClient(provider=provider)

        # Generate in a worker thread so async MCP framework isn't blocked
        # by the synchronous httpx call inside LLMClient.generate().
        response = await asyncio.to_thread(
            client.generate, user_message, self._player_prompt
        )

        self._store.append_turn(session_id, "tutor", response)
        return {"tutor_response": response}

    async def tutor_session_status(self, session_id: str) -> dict[str, Any]:
        """Return current session state."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        return {
            "session_id": session.session_id,
            "status": session.status,
            "turn_count": len(session.turns),
            "started_at": session.started_at.isoformat(),
        }

    async def tutor_session_end(self, session_id: str) -> dict[str, Any]:
        """Mark the session ended (TASK-GR-WIRE BLOCK-3a).

        Delegates to
        :func:`study_tutor.tutoring.session_end.perform_session_end` which
        owns the full FEAT-PH1-003 session-end workflow:

        * F4 in-flight ``tutor_turn`` resolution (3 s inner timeout).
        * I-T6 zero-turn invariant guard — sessions ended before any tutor
          turn flip status to ``"ended"`` but do NOT emit
          ``session.completed`` and do NOT schedule the F3 Graphiti write.
        * DDR-003 ordering: bus emit precedes the F3 ``create_task`` call.
        * F3 fire-and-forget Graphiti write via the injected
          :class:`GraphitiWriteHelper` (graceful no-op if ``None``).
        * Caller-facing return within the ASSUM-004 2 s wall-clock budget
          regardless of Graphiti latency (ADR-ARCH-019).

        ``topics_covered`` and ``aos_exercised`` are sourced from the
        cached :class:`SessionPlan` for ``session_id``. If no plan is
        cached (e.g. a session_id from a prior process restart), both
        default to empty — :func:`build_session_completed_episode` will
        fall back to ``[session.topic]`` if available, otherwise the
        learner subject slug.
        """
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        plan = self._plan_sessions.get(session_id)
        if plan is not None:
            topics_covered = [plan.topic_name]
            aos_exercised = list(plan.focus_aos)
        else:
            # Stale-lookup fallback: a tutor_session_end called for a
            # session_id never seen by this process's tutor_start_session
            # (e.g. server restart between the two endpoints) is still a
            # valid graceful path — the session itself exists in the
            # store, but the per-process plan cache is cold. Empty
            # topics/AOs let perform_session_end derive defaults from
            # session.topic.
            topics_covered = []
            aos_exercised = []

        # transition_state closure — perform_session_end calls this
        # exactly once at the documented ordering point (after I-T6
        # check, before bus emit) so the test surface can assert "state
        # flipped before session.completed dispatched". We do not flip
        # state here ourselves.
        def _transition_state() -> None:
            self._store.end(session_id)

        result = await perform_session_end(
            session=session,
            student_id=session.subject,
            write_helper=self._write_helper,
            event_bus=self._event_bus,
            topics_covered=topics_covered,
            aos_exercised=aos_exercised,
            transition_state=_transition_state,
        )

        # AC-CONF-08 (TASK-GR-CONF / BLOCK-3b): TopicConfidence node
        # update on session end. We dispatch this as a separate fire-
        # and-forget task so the caller-facing path returns within the
        # ASSUM-004 2 s budget regardless of FalkorDB latency on the
        # node load. The helper itself is structured-log-only on every
        # failure mode (AC-CONF-06), so an exception inside the task
        # never escapes to the MCP caller.
        #
        # Skip conditions (graceful degradation):
        #
        # * Zero-turn sessions — ``perform_session_end`` already
        #   suppressed ``session.completed`` and the F3 write under
        #   I-T6, so the F2 episode would be temporally orphaned.
        # * No write_helper — Graphiti not wired (test path / Phase 0
        #   compatibility). Helper would be a no-op anyway, but
        #   skipping avoids the empty task scheduling.
        # * No cached plan — we have no ``topic_ref`` to update; the
        #   F3 episode in ``perform_session_end`` already fell back to
        #   ``session.topic`` and the AC-DEMO-03 entity round-trip
        #   degrades cleanly.
        if (
            len(session.turns) > 0
            and self._write_helper is not None
            and plan is not None
            and self._graphiti_client is not None
        ):
            # ``perform_session_end`` returns only ``{session_id, status}``
            # so we mint our own end timestamp here. This runs synchronously
            # immediately after the bus emit; the few ms drift vs the
            # episode's internal ``ended_at`` is well below any temporal-
            # analytics resolution we care about.
            ended_at = datetime.now(timezone.utc)
            student_turn_count = sum(
                1 for turn in session.turns if turn.role == "user"
            )
            # Phase-1 fallback per the task spec: ``TutorSession`` does
            # not currently track per-turn ``CoachVerdict`` payloads, so
            # we feed an empty misconception map. Phase1MinimalDeltaPolicy
            # produces ``+1`` for engagement-only sessions (turns >= 5)
            # and ``0`` otherwise — both satisfy AC-DEMO-03 because the
            # ``last_revised_at`` flip is the structural change.
            session_summary: dict[str, Any] = {
                "misconceptions_per_topic": {},
                "student_turn_count": student_turn_count,
                "ended_at": ended_at,
                "triggering_session_id": session_id,
            }
            try:
                asyncio.create_task(
                    record_topic_confidence_update(
                        client=self._graphiti_client,
                        write_helper=self._write_helper,
                        student_id=session.subject,
                        topic_ref=plan.topic_name,
                        session_summary=session_summary,
                        policy=Phase1MinimalDeltaPolicy(),
                    ),
                    name=f"topic-confidence-{session_id}",
                )
            except Exception as exc:  # noqa: BLE001 — boundary catch
                # ``asyncio.create_task`` only fails when there's no
                # running loop; in that path we drop the update with a
                # log line — the session is still observably ``ended``
                # and ``perform_session_end`` already emitted
                # ``session.completed``.
                logger.warning(
                    "topic confidence dispatch failed; session.completed "
                    "already emitted",
                    extra={
                        "event": "topic_confidence_dispatch_failed",
                        "session_id": session_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )

        return result

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
