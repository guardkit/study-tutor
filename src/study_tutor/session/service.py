"""App Access ``SessionService`` (FEAT-SMP-003) — transport-agnostic session
orchestration over the durable ``StudentStore``.

This is the thin layer both transports sit on: the MCP adapter today, the
HTTP/WS adapter for the mobile client later. It composes the ``StudentStore``
session methods (``create_session`` / ``get_session`` / ``list_sessions`` /
``append_turn`` / ``get_turns`` / ``end_session`` / ``record_session_completion``)
and adds the two things the port explicitly delegates upward
(``docs/design/contracts/API-session-cross-device.md`` §5): the **ownership
guard** (``SessionForbidden`` when a session's ``student_id`` ≠ the caller) and
the **status guard** (``SessionEnded``), applied via :meth:`_load_owned_session`
on every verb that takes a ``session_id``.

Two-level injection (mirrors the store): the adapters resolve the shared
``SessionService`` via :mod:`session.provider`; the service resolves the
``StudentStore`` via :mod:`knowledge.store.provider`. The service imports **no**
MCP, FastAPI, or Keycloak types — identity is an already-resolved
``student_id: str`` parameter; the LLM/Coach loop is injected as ``reply_fn``.
Writes are ``await``-ed inline (ADR-ARCH-023 D2), never fire-and-forget.

Open decisions for ``/feature-spec`` (from the adversarial design review) — the
scaffolding is deliberately silent on these so the build resolves them once:

* **#1 identity source (high).** The transport must server-resolve ONE
  ``student_id`` (config now; the Keycloak ``sub`` later) and pass the SAME id to
  ALL verbs as the ownership key. The MCP ``tutor_start_session`` ``student_id``
  arg is the planner *learner slug*, NOT identity — keep them separate so the
  guard is neither tautological nor a break.
* **#2 subject (med).** The MCP adapter supplies ``subject`` internally (preserve
  today's ``subject=student_id`` or a role constant) WITHOUT adding a tool arg.
* **#3 wiring (med).** Wire the service into BOTH ``MCPAdapter`` sites in
  ``cli/main.py`` (``serve`` and ``_build_nats_runtime``) via a shared helper.
* **#4 completion producer (med).** :class:`SessionCompletion` is computed by the
  Coach domain logic and handed to :meth:`end_session`; the confidence/XP delta
  policy (the ``Phase1MinimalDeltaPolicy`` heuristic) resolves ``ConfidenceUpdate``
  values from ``StudentStore`` reads.
* **#5 event payload (med).** ``session.started`` / ``turn_completed`` /
  ``completed`` (§8) belong on the service so both transports share them, but the
  emitted payload must reproduce today's ``perform_session_end`` shape
  (events-schema.yaml). Kept OUT of this scaffolding to avoid divergence; the
  build wires the EventBus with the pinned payload.
* **#6 ratify §9 / #8 F4 in-flight resolution.** Ratify the ``SessionForbidden`` /
  ``Unauthenticated`` closed-set extension via ``/design-refine``; F4 in-flight
  turn resolution is out of scope this wave (acceptable under single-user
  last-writer-wins).
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Literal

from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
    SessionRecord,
    SessionStatus,
    SessionTurn,
)
from study_tutor.knowledge.store.port import (
    DEFAULT_SESSION_LIST_LIMIT,
    StudentStore,
)
from study_tutor.knowledge.store.provider import get_student_store
from study_tutor.knowledge.student_model import Misconception
from study_tutor.planner.pipeline import plan_session
from study_tutor.planner.protocols import (
    SessionCompletion as PlannerSessionCompletion,
)
from study_tutor.planner.types import (
    AssessmentObjectiveCode,
    SessionPlan,
    _baseline_plan,
    load_curriculum_defaults,
)
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Planner-hoist configuration (S-R3 §2.1 — relocated from mcp/adapter.py)
# ---------------------------------------------------------------------------

#: Env var controlling the *outer* ``plan_session`` budget invoked inside
#: :meth:`SessionService.start_session` (ASSUM-006, signed off 2026-04-29).
#: Default 2.0s. The single graceful-degradation boundary for the planner: any
#: timeout / internal exception / unknown learner degrades to a baseline plan
#: rather than blocking session creation. Relocated here verbatim from the MCP
#: adapter when planning moved into the core (spec §2.1 / D14).
_PLANNER_HANDLER_BUDGET_ENV: str = "PLANNER_HANDLER_BUDGET_SEC"
_PLANNER_HANDLER_BUDGET_DEFAULT: float = 2.0

#: How many recent ended sessions to read as plan facts — the Rule-4
#: revisit inputs (``session_completions``) and the §6.3(c) anti-repetition
#: lookback (``recent_recommendations``). A single-student window is tiny; a
#: generous cap keeps the 4-day London rotation honest without a heavy read.
_RECENT_SESSIONS_WINDOW: int = 20


def _planner_handler_budget_sec() -> float:
    """Return the outer ``plan_session`` budget for ``start_session``.

    Reads :data:`_PLANNER_HANDLER_BUDGET_ENV` at *call* time so test patching of
    ``os.environ`` flows through without a process restart. Falls back to
    :data:`_PLANNER_HANDLER_BUDGET_DEFAULT` when unset or unparseable.
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


def _curriculum_ao_mapping() -> dict[str, list[AssessmentObjectiveCode]]:
    """``topic_name → [AO codes]`` from the curriculum the planner understands.

    S-R3 §2.1: the planner's ``ao_mapping`` input, sourced from
    ``curriculum_defaults.yaml`` (the same AO source :func:`_baseline_plan`
    already reads) so ``focus_aos`` is populated for curriculum topics rather
    than blanked. A malformed/missing YAML degrades to an empty mapping — the
    planner then reports ``ao_mapping_found=False`` rather than raising.
    """
    try:
        entries = load_curriculum_defaults()
    except Exception:  # noqa: BLE001 — degrade to empty mapping, never raise
        logger.warning("event=curriculum_ao_mapping_unavailable", exc_info=True)
        return {}
    return {
        str(entry["topic_name"]): list(entry.get("focus_aos") or [])
        for entry in entries
        if entry.get("topic_name")
    }


# ---------------------------------------------------------------------------
# Injected domain-loop callables
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TutorReply:
    """One tutor reply from the injected domain loop (``reply_fn``)."""

    response: str
    metadata: Mapping[str, object] | None = None


#: The domain tutor/Coach loop, injected into :meth:`SessionService.turn`. Keeps
#: LLM/orchestrator concerns in the adapter; the service only persists + guards.
ReplyFn = Callable[[str], Awaitable[TutorReply]]

#: Streaming variant: yields tutor tokens as they are produced (WS path, §7).
ReplyStreamFn = Callable[[str], AsyncIterator[str]]


# ---------------------------------------------------------------------------
# Input / result DTOs (frozen — in-process bundles, projected by the transport)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionCompletion:
    """Learner-state deltas persisted at session end (design-review #4).

    Computed by the Coach domain logic and handed in; the store only persists.
    ``xp_awarded`` and ``confidence_updates`` carry the RESOLVED post-session
    values (band derived at write time), not deltas — the write is idempotent on
    ``session_id``.
    """

    topic: str | None
    aos_scaffolded: list[str]
    xp_awarded: int
    confidence_updates: list[ConfidenceUpdate]
    misconceptions: list[Misconception]


@dataclass(frozen=True)
class StartSessionResult:
    session_id: str
    student_id: str
    subject: str
    topic: str | None
    resumed: bool
    #: Transcript, populated only on the resumed branch (a device re-attaching).
    turns: tuple[SessionTurn, ...] | None = None
    #: S-R3 §2.1: the plan the service computed at start (planning moved into
    #: the core, D14). Transports project it: HTTP surfaces ``topic`` /
    #: ``opening_prompt`` / ``focus_aos`` (contract §2.3); MCP its
    #: ``plan_summary``. ``None`` only for pre-S-R3/legacy callers that
    #: construct the result directly.
    plan: SessionPlan | None = None


@dataclass(frozen=True)
class ResumeResult:
    session_id: str
    student_id: str
    status: SessionStatus
    turns: tuple[SessionTurn, ...]


@dataclass(frozen=True)
class TurnResult:
    tutor_response: str
    turn_index: int
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class SessionStatusView:
    session_id: str
    student_id: str
    status: SessionStatus
    turn_count: int
    started_at: datetime
    last_activity: datetime
    resumable: bool


@dataclass(frozen=True)
class EndSessionResult:
    session_id: str
    status: Literal["ended"] = "ended"


@dataclass(frozen=True)
class TurnEvent:
    """A WebSocket stream frame (§7 Rev 1): token/done/transcript/audio_ref/error events.

    Contract §7 Rev 1 frozen event types:
    - token: text chunk (has text)
    - done: terminal marker (has turn_index)
    - transcript: STT result (has text)
    - audio_ref: TTS chunk reference (has seq, chunk_id, url)
    - error: generation failure (has error, error_type)
    """

    type: Literal["token", "done", "transcript", "audio_ref", "error"]
    text: str | None = None
    turn_index: int | None = None
    # Audio reference fields (type="audio_ref")
    seq: int | None = None
    chunk_id: str | None = None
    url: str | None = None
    # Error fields (type="error")
    error: str | None = None
    error_type: str | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SessionService:
    """Composes the ``StudentStore`` session methods with the ownership/status
    guards and event responsibilities the App Access layer owns."""

    def __init__(self, *, store: StudentStore | None = None) -> None:
        """Hold an explicit store (tests) or resolve the wired one per call."""
        self._store = store

    def _resolve_store(self) -> StudentStore:
        store = self._store if self._store is not None else get_student_store()
        if store is None:
            raise RuntimeError(
                "SessionService has no StudentStore wired — "
                "call knowledge.store.provider.set_student_store at startup",
            )
        return store

    async def _load_owned_session(
        self, student_id: str, session_id: str, *, allow_ended: bool = False
    ) -> SessionRecord:
        """The single ownership+status guard the four ``session_id`` verbs reuse.

        ``None`` from the store → ``SessionNotFoundError``; a ``student_id``
        mismatch → ``SessionForbidden``; an ``ended`` session (unless
        ``allow_ended``) → ``SessionEnded``. Centralising this is what the
        contract §5 / port docstring delegation asks for.
        """
        store = self._resolve_store()
        record = await store.get_session(session_id)
        if record is None:
            raise SessionNotFoundError(session_id)
        if record.student_id != student_id:
            raise SessionForbidden(
                f"session {session_id!r} is not owned by {student_id!r}"
            )
        if not allow_ended and record.status == "ended":
            raise SessionEnded(f"session {session_id!r} has ended")
        return record

    async def start_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None = None,
        resume_if_active: bool = False,
    ) -> StartSessionResult:
        """Create a session — or, with ``resume_if_active``, return the caller's
        existing active one (with its transcript). No ownership guard: an
        auth-derived ``student_id`` can only create/resume its own session.

        S-R3 §2.1 / D14: planning now lives here. The plan is computed under the
        2.0s budget/degrade boundary keyed by the **ownership** ``student_id``
        (the same identity the confidence writes use — spec §2.1 read-key fix),
        and its facts persist on the created session row: ``topic`` and
        ``focus_aos`` (in the ``aos_scaffolded`` column, S-R3 §2.1). The
        ``opening_prompt`` is NOT persisted — it rides back in the plan on the
        result only. ``topic`` (the learner-supplied value) is the planner's
        override; the persisted/returned topic is the plan's chosen topic.
        """
        store = self._resolve_store()

        # Plan under the outer budget/degrade boundary. Keyed by the ownership
        # student_id so the planner reads the same learner state the confidence
        # writes key on (spec §2.1). ``topic`` is the learner override.
        plan = await self._plan(
            student_id=student_id, topic_override=topic
        )

        # Persist the plan facts on the row at start (spec §2.1). On a resume the
        # store returns the existing row and ignores these; the freshly-computed
        # plan still rides back on the result for the start response.
        record, created = await store.create_session(
            student_id=student_id,
            subject=subject,
            topic=plan.topic_name,
            aos_scaffolded=list(plan.focus_aos),
            resume_if_active=resume_if_active,
        )
        turns: tuple[SessionTurn, ...] | None = None
        if not created:
            turns = tuple(await store.get_turns(record.session_id))
        return StartSessionResult(
            session_id=record.session_id,
            student_id=record.student_id,
            subject=record.subject,
            topic=record.topic,
            resumed=not created,
            turns=turns,
            plan=plan,
        )

    async def _plan(
        self, *, student_id: str, topic_override: str | None
    ) -> SessionPlan:
        """Run ``plan_session`` under the 2.0s budget/degrade boundary.

        Relocated from ``mcp/adapter.py`` (spec §2.1). Feeds the planner its two
        previously-blanked inputs: the curriculum ``ao_mapping`` (so
        ``focus_aos`` is populated) and the learner's recent ended sessions as
        both Rule-4 ``session_completions`` (revisit signal) and the §6.3(c)
        ``recent_recommendations`` anti-repetition lookback. Any failure mode
        (timeout / internal exception / unknown learner) degrades to
        :func:`_baseline_plan(False)` rather than propagating — session creation
        must never be blocked by the planner.
        """
        store = self._resolve_store()

        # Recent ended sessions = the plan facts the two planner inputs need.
        recent = await store.list_sessions(
            student_id, status="ended", limit=_RECENT_SESSIONS_WINDOW
        )
        session_completions = [
            PlannerSessionCompletion(
                topics_covered=[r.topic] if r.topic else [],
                ended_at=r.last_activity,
            )
            for r in recent
        ]
        recent_recommendations = tuple(
            (r.topic, r.last_activity) for r in recent if r.topic
        )

        budget = _planner_handler_budget_sec()
        try:
            return await asyncio.wait_for(
                plan_session(
                    student_id,
                    topic_override,
                    ao_mapping=_curriculum_ao_mapping(),
                    session_completions=session_completions,
                    recent_recommendations=recent_recommendations,
                ),
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
                    "budget_sec": budget,
                },
            )
            return _baseline_plan(learner_state_available=False)
        except Exception as exc:  # noqa: BLE001 — boundary catch, never re-raise
            logger.exception(
                "planner internal error — degrading to baseline plan",
                extra={
                    "event": "planner_internal_error",
                    "student_id": student_id,
                    "error": str(exc),
                },
            )
            return _baseline_plan(learner_state_available=False)

    async def list_sessions(
        self,
        *,
        student_id: str,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """The caller's recent sessions (ownership-scoped by the partition key —
        no ``session_id``, so no guard is possible or needed)."""
        store = self._resolve_store()
        return await store.list_sessions(student_id, status=status, limit=limit)

    async def resume_session(
        self, *, student_id: str, session_id: str
    ) -> ResumeResult:
        """Rehydrate an owned active session's transcript for a new device."""
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=False
        )
        store = self._resolve_store()
        turns = tuple(await store.get_turns(session_id))
        return ResumeResult(
            session_id=record.session_id,
            student_id=record.student_id,
            status=record.status,
            turns=turns,
        )

    async def turn(
        self,
        *,
        student_id: str,
        session_id: str,
        user_message: str,
        reply_fn: ReplyFn,
    ) -> TurnResult:
        """Persist the user turn, run the injected tutor loop, persist the tutor
        turn — two durable rows per §6 (lossless mid-session device switch)."""
        await self._load_owned_session(student_id, session_id, allow_ended=False)
        store = self._resolve_store()
        await store.append_turn(
            session_id=session_id, role="user", content=user_message
        )
        reply = await reply_fn(user_message)
        tutor_turn = await store.append_turn(
            session_id=session_id, role="tutor", content=reply.response
        )
        return TurnResult(
            tutor_response=reply.response,
            turn_index=tutor_turn.turn_index,
            metadata=reply.metadata,
        )

    async def turn_stream(
        self,
        *,
        student_id: str,
        session_id: str,
        user_message: str,
        reply_stream_fn: ReplyStreamFn,
    ) -> AsyncIterator[TurnEvent]:
        """WS streaming variant (§7 Rev 1): stream tokens with durability.

        Pipeline (TASK-VS2-003):
        1. Guard session ownership/status
        2. Persist user turn
        3. Stream reply tokens, accumulating response
        4. On success: persist tutor turn, yield done
        5. On failure: yield error, persist no tutor turn (ASSUM-004)

        Cancellation safety (ASSUM-005): caller cancellation doesn't prevent
        persistence of complete response. The generation/persistence runs
        detached from the consuming task's lifetime.
        """
        await self._load_owned_session(student_id, session_id, allow_ended=False)
        store = self._resolve_store()

        # Persist user turn before streaming
        await store.append_turn(
            session_id=session_id, role="user", content=user_message
        )

        # Accumulate response while streaming tokens
        accumulated_response = []
        generation_failed = False
        failure_reason = None

        try:
            async for token in reply_stream_fn(user_message):
                accumulated_response.append(token)
                yield TurnEvent(type="token", text=token)
        except Exception as exc:
            # ASSUM-004: generation failure mid-stream
            generation_failed = True
            failure_reason = f"{type(exc).__name__}: {exc}"
            yield TurnEvent(
                type="error",
                error=failure_reason,
                error_type="generation_failed",
            )
            # Don't persist tutor turn on failure
            return

        # Generation succeeded - persist full response
        if not generation_failed:
            full_response = "".join(accumulated_response)
            tutor_turn = await store.append_turn(
                session_id=session_id, role="tutor", content=full_response
            )
            yield TurnEvent(type="done", turn_index=tutor_turn.turn_index)

    async def session_status(
        self, *, student_id: str, session_id: str
    ) -> SessionStatusView:
        """Owned session status — the one verb that reads ``ended`` sessions too
        (``allow_ended=True``, the §9 carve-out)."""
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=True
        )
        return SessionStatusView(
            session_id=record.session_id,
            student_id=record.student_id,
            status=record.status,
            turn_count=record.turn_count,
            started_at=record.started_at,
            last_activity=record.last_activity,
            resumable=(record.status == "active"),
        )

    async def end_session(
        self,
        *,
        student_id: str,
        session_id: str,
        completion: SessionCompletion | None = None,
        topic_hint: str | None = None,
    ) -> EndSessionResult:
        """Transition ``active → ended`` and commit the learner-state deltas —
        awaited inline (ADR-ARCH-023 D2).

        S-R3 §2.4 / D14: **completion assembly lives here**, for ALL transports.
        When ``completion`` is not supplied (the transport path — both HTTP and
        MCP), the service assembles it from the **persisted** session row
        (``topic`` + ``aos_scaffolded`` plan facts) plus store reads, so the two
        transports produce byte-identical writes. The MCP adapter passes only a
        ``topic_hint`` (a weak fallback if the row has no ``topic``); HTTP passes
        neither. An explicit ``completion`` is honoured as-is (the store-ordering
        regression pin and future ``finalize_session`` seam).

        I-T6 zero-turn rule: a session with no turns settles status only — no
        completion write (``build_session_completion`` is skipped for
        ``turn_count == 0``). Event ``session.completed`` is still emitted by the
        transport with the pinned payload; see the module open-decisions.

        W0 ordering (spec §1): the completion write **precedes** the status
        transition. ``record_session_completion`` is gated on
        ``ON CONFLICT … WHERE status != 'ended'``, so it must run while the
        session is still ``active`` — otherwise ``store.end_session`` flips the
        status to ``ended`` in its own committed transaction first and the gate
        never fires, silently dropping the confidence/misconception children.
        Phase E replaces this two-call sequence with a single ``finalize_session``
        transaction (spec §4); until then, ordering is the fix.
        """
        record = await self._load_owned_session(
            student_id, session_id, allow_ended=False
        )
        store = self._resolve_store()

        # Assemble the completion in the core when the transport didn't hand one
        # in (spec §2.4). Derived purely from the persisted row + store reads so
        # HTTP and MCP write identically. I-T6: skip for zero-turn sessions.
        if completion is None and record.turn_count > 0:
            # Local import avoids the completion↔service module import cycle.
            from study_tutor.session.completion import build_session_completion

            topic = record.topic or topic_hint or record.subject
            completion = await build_session_completion(
                store=store,
                student_id=student_id,
                topic=topic,
                # Store rows are (user, tutor) turns; student turns are half.
                student_turn_count=record.turn_count // 2,
                aos_scaffolded=list(record.aos_scaffolded),
                misconceptions_per_topic={},
            )

        if completion is not None:
            await store.record_session_completion(
                student_id=student_id,
                session_id=session_id,
                topic=completion.topic,
                aos_scaffolded=completion.aos_scaffolded,
                xp_awarded=completion.xp_awarded,
                confidence_updates=completion.confidence_updates,
                misconceptions=completion.misconceptions,
            )
        ended = await store.end_session(session_id)
        return EndSessionResult(session_id=ended.session_id)


__all__ = [
    "EndSessionResult",
    "ReplyFn",
    "ReplyStreamFn",
    "ResumeResult",
    "SessionCompletion",
    "SessionService",
    "SessionStatusView",
    "StartSessionResult",
    "TurnEvent",
    "TurnResult",
    "TutorReply",
]
