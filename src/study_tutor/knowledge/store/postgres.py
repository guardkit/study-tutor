"""``PostgresStudentStore`` — the Postgres adapter (FEAT-SMP-001 skeleton).

Concrete implementation of the :class:`~study_tutor.knowledge.store.port.StudentStore`
Protocol against the dedicated study-tutor Postgres (JSONB, no pgvector) stood
up by ``docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md``.

**This is a skeleton.** The method bodies raise ``NotImplementedError`` and the
build (FEAT-SMP-001) fills them in. It is dependency-light on purpose — it does
NOT import a database driver at module load, so the tree still imports cleanly
before ``sqlalchemy[asyncio]`` / ``asyncpg`` + Alembic are added to
``pyproject.toml`` during the build. Wiring notes are inline as ``TODO(FEAT-SMP-001)``.

Design intent the build should honour:

- One async engine / connection pool per process, created from
  ``STUDY_TUTOR_PG_DSN`` and injected here (constructor takes the DSN or a
  pre-built pool). Mirror the dependency-injection posture of
  ``knowledge.retrieval.set_collection_provider`` — the hot path never
  constructs its own connection.
- ``record_session_completion`` and ``end_session`` run inside a single
  transaction each; ``append_turn`` bumps ``turn_count`` + ``last_activity``
  atomically with the insert.
- Schema is owned by Alembic; see ``schema_reference.sql`` for the shape the
  first migration encodes.
"""
from __future__ import annotations

from typing import Any

from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
    SessionRecord,
    SessionStatus,
    SessionTurn,
    StudentState,
    TurnRole,
)
from study_tutor.knowledge.store.port import (
    DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    DEFAULT_SESSION_LIST_LIMIT,
)
from study_tutor.knowledge.student_model import Misconception, TopicConfidence

_NOT_IMPLEMENTED = "PostgresStudentStore is a FEAT-SMP-001 skeleton"


class PostgresStudentStore:
    """Postgres-backed :class:`StudentStore`. Skeleton — bodies land in FEAT-SMP-001."""

    def __init__(self, dsn: str, *, pool: Any | None = None) -> None:
        """Hold the DSN (and optionally a pre-built pool).

        TODO(FEAT-SMP-001): if ``pool`` is None, lazily create an async engine
        from ``dsn`` (``sqlalchemy.ext.asyncio.create_async_engine`` or an
        ``asyncpg`` pool). Keep it a single shared instance per process.
        """
        self._dsn = dsn
        self._pool = pool

    # -- Health -------------------------------------------------------------

    async def ping(self) -> bool:  # TODO(FEAT-SMP-001): SELECT 1
        raise NotImplementedError(_NOT_IMPLEMENTED)

    # -- Reads --------------------------------------------------------------

    async def get_student_state(self, student_id: str) -> StudentState:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_topic_confidences(
        self, student_id: str
    ) -> list[TopicConfidence]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_recent_misconceptions(
        self,
        student_id: str,
        *,
        window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    ) -> list[Misconception]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    # -- Learner-state writes ----------------------------------------------

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
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def record_misconception(
        self, *, student_id: str, topic_name: str, text: str
    ) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def apply_confidence_update(
        self, *, student_id: str, update: ConfidenceUpdate
    ) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    # -- Session persistence -----------------------------------------------

    async def create_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None = None,
        resume_if_active: bool = False,
    ) -> tuple[SessionRecord, bool]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def list_sessions(
        self,
        student_id: str,
        *,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def append_turn(
        self,
        *,
        session_id: str,
        role: TurnRole,
        content: str,
        ao_scaffolded: str | None = None,
    ) -> SessionTurn:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def end_session(self, session_id: str) -> SessionRecord:
        raise NotImplementedError(_NOT_IMPLEMENTED)


__all__ = ["PostgresStudentStore"]
