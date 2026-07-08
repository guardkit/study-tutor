"""``StudentStore`` — the persistence port for the learner model (FEAT-SMP-001).

This is the seam the migration hangs on. Callers (the MCP/HTTP adapters, the
Coach, the session planner) depend on **this Protocol**, never on a concrete
store; the Postgres adapter ([ADR-ARCH-023]) is injected at startup, exactly as
the ChromaDB collection is injected into ``knowledge.retrieval`` today. A
fake/in-memory implementation of the same Protocol backs the tests.

The method set is deliberately the union of:

1. **The read/write surface being replaced** — ``get_student_state`` and the
   session-completion write (the prior async write helper's F1/F2/F3 flush
   points), so FEAT-SMP-002 can swap
   the adapter behind the existing callers without changing their call sites.
2. **The cross-device session contract** (``docs/design/contracts/API-session-cross-device.md``)
   — ``create_session`` / ``list_sessions`` / ``get_turns`` / ``append_turn`` /
   ``end_session`` for durable, resumable, student-keyed sessions.

Async note: every method is ``async`` and **awaited inline**. Per ADR-ARCH-023
D2 the writes are *synchronous from the caller's flow* (the session-end handler
awaits the transaction to completion) — they are simply not the fire-and-forget
``asyncio.create_task`` dispatch the old 79-second graph write forced. A ms-scale
Postgres upsert does not need, and no longer gets, that machinery.

Ownership: methods taking a ``session_id`` do NOT themselves enforce the
``student_id`` ownership check — that ``SessionForbidden`` guard is the App
Access / MCP adapter's job (session contract §5), so this port stays a thin data
surface. The store returns ``None`` for an unknown ``session_id`` rather than
raising, mirroring the graceful-degradation contract of the read path today.

Status: scaffolding for FEAT-SMP-001's ``/feature-spec`` to react to.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
    SessionRecord,
    SessionStatus,
    SessionTurn,
    StudentState,
    TurnRole,
)
from study_tutor.knowledge.student_model import Misconception, TopicConfidence

#: Trailing window (days) over which misconceptions count as "recent" — matches
#: ``queries.MISCONCEPTION_WINDOW_DAYS`` so planner behaviour is unchanged.
DEFAULT_MISCONCEPTION_WINDOW_DAYS: int = 30

#: Default page size for ``list_sessions`` (a device's "resume" list).
DEFAULT_SESSION_LIST_LIMIT: int = 20


@runtime_checkable
class StudentStore(Protocol):
    """Structural contract for the learner-state + session persistence layer."""

    # -- Health -------------------------------------------------------------

    async def ping(self) -> bool:
        """Return ``True`` if the store is reachable. Used by the boot smoke
        (mirrors ``retrieval.get_collection_provider``'s startup check)."""
        ...

    # -- Reads (handler + planner) -----------------------------------------

    async def get_student_state(self, student_id: str) -> StudentState:
        """Aggregate snapshot. Returns ``StudentState(empty=True)`` when the
        student is unknown or the store is unreachable — never raises for the
        read path (graceful degradation, as today)."""
        ...

    async def get_topic_confidences(
        self, student_id: str
    ) -> list[TopicConfidence]:
        """Per-topic confidence entities the planner ranks over
        (``PlannerContext.topic_confidences``). Empty list when unknown."""
        ...

    async def get_recent_misconceptions(
        self,
        student_id: str,
        *,
        window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    ) -> list[Misconception]:
        """Misconceptions observed within ``window_days`` — feeds
        ``PlannerContext.misconceptions`` (rule-4)."""
        ...

    # -- Learner-state writes (replace the prior write helper F1/F2/F3) -----

    async def record_session_completion(
        self,
        *,
        student_id: str,
        session_id: str,
        topic: str | None,
        aos_scaffolded: list[str],
        xp_awarded: int,
        confidence_updates: list[ConfidenceUpdate],
        misconceptions: list[Misconception],
    ) -> None:
        """The session-end write — XP, per-topic confidence, and misconceptions
        committed in **one transaction** on the ``active → ended`` boundary
        (ADR-ARCH-023 D2). Idempotent on the ``session_id`` so a retried
        session-end does not double-award XP."""
        ...

    async def record_misconception(
        self,
        *,
        student_id: str,
        topic_name: str,
        text: str,
    ) -> None:
        """F1 — a single Coach-observed misconception, written synchronously
        (ms-scale; no fire-and-forget needed)."""
        ...

    async def apply_confidence_update(
        self, *, student_id: str, update: ConfidenceUpdate
    ) -> None:
        """F2 — persist one resolved topic-confidence value (band derived at
        write time via ``confidence_band_for``)."""
        ...

    # -- Session persistence (cross-device contract §5) --------------------

    async def create_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None = None,
        resume_if_active: bool = False,
    ) -> tuple[SessionRecord, bool]:
        """Create a session, or resume the active one.

        Returns ``(record, created)`` — ``created=True`` for a brand-new
        session, ``False`` when ``resume_if_active`` matched an existing
        ``active`` session for ``(student_id, subject)`` and that one is
        returned instead. The boolean is a transient signal (not a column on
        ``SessionRecord``) so the service populates the contract's ``resumed``
        field without a race-prone list-then-create pre-check."""
        ...

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch a session, or ``None`` if unknown."""
        ...

    async def list_sessions(
        self,
        student_id: str,
        *,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """Recent sessions for a student, newest ``last_activity`` first — the
        "resume where you left off" list."""
        ...

    async def append_turn(
        self,
        *,
        session_id: str,
        role: TurnRole,
        content: str,
        ao_scaffolded: str | None = None,
    ) -> SessionTurn:
        """Durably append one turn (per-turn commit → lossless device switch),
        bumping ``turn_count`` + ``last_activity`` in the same transaction."""
        ...

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        """Ordered transcript for ``resume_session`` — a new device renders
        the thread from these."""
        ...

    async def end_session(self, session_id: str) -> SessionRecord:
        """Transition ``active → ended`` and stamp the summary. The learner
        deltas are written by ``record_session_completion`` in the same
        session-end flow (the adapter/service composes the two)."""
        ...


__all__ = [
    "DEFAULT_MISCONCEPTION_WINDOW_DAYS",
    "DEFAULT_SESSION_LIST_LIMIT",
    "StudentStore",
]
