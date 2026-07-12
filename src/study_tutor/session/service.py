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

import logging
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
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)


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
        auth-derived ``student_id`` can only create/resume its own session."""
        store = self._resolve_store()
        record, created = await store.create_session(
            student_id=student_id,
            subject=subject,
            topic=topic,
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
        )

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
    ) -> EndSessionResult:
        """Transition ``active → ended`` and, when a ``completion`` is supplied,
        commit the learner-state deltas — awaited inline (ADR-ARCH-023 D2).

        ``completion=None`` preserves the I-T6 zero-turn rule (the adapter passes
        ``None`` when ``turn_count == 0``): transition only, no completion write.
        Event ``session.completed`` (design-review #5) is emitted by the transport
        with the pinned payload; see the module open-decisions.

        W0 ordering (spec §1): the completion write **precedes** the status
        transition. ``record_session_completion`` is gated on
        ``ON CONFLICT … WHERE status != 'ended'``, so it must run while the
        session is still ``active`` — otherwise ``store.end_session`` flips the
        status to ``ended`` in its own committed transaction first and the gate
        never fires, silently dropping the confidence/misconception children.
        Phase E replaces this two-call sequence with a single ``finalize_session``
        transaction (spec §4); until then, ordering is the fix.
        """
        await self._load_owned_session(student_id, session_id, allow_ended=False)
        store = self._resolve_store()
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
