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
* ``tutor_session_end`` — sync; marks session ended (Phase 0 no-op beyond
  status flip; Phase 1 adds async Graphiti write per DEC-02).

SR-03: every handler resolves the provider via ``_default_player_model()``
at call time — no module-level provider hard-coding.

SR-07: ``tutor_session_end`` description is *only* ``"marks session ended"``.
The Phase 1 Graphiti write is a ``# TODO(phase-1)`` in code, not user-facing text.

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

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.planner.pipeline import plan_session
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.tutor_session import (
    SessionNotFoundError,
    SessionStore,
    get_default_store,
)

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

        provider = player_model or _default_player_model()
        client = LLMClient(provider=provider)

        self._store.append_turn(session_id, "user", user_message)

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
        """Mark the session ended.

        Phase 0: flip status only. Phase 1 adds a Graphiti write here per
        DEC-02 — kept out of the tool description (SR-07).
        """
        # TODO(phase-1): add async Graphiti write per DEC-02
        try:
            self._store.end(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

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
