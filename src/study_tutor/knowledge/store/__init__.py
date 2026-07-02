"""study-tutor StudentStore — the Postgres learner-state persistence layer.

Scaffolding for **FEAT-SMP-001** ([ADR-ARCH-023]): replaces the Graphiti/FalkorDB
student model with a study-tutor-owned Postgres (JSONB) store. Layout mirrors the
project's ports/adapters convention:

- :mod:`entities` — Pydantic records (read models re-homed from ``queries.py`` +
  new ``Session``/``Turn``/``Achievement``/``Quest`` rows). No DB driver imported.
- :mod:`port` — the :class:`~study_tutor.knowledge.store.port.StudentStore`
  Protocol callers depend on.
- :mod:`postgres` — the ``PostgresStudentStore`` adapter (skeleton; bodies land
  in the build).
- ``schema_reference.sql`` — the DDL Alembic's first migration encodes.

Wave map: FEAT-SMP-001 implements the writes + ``ping``; FEAT-SMP-002 repoints
``queries.py`` reads here (and deletes the Graphiti copies); FEAT-SMP-003 adds
the session-persistence methods behind the MCP + HTTP/WS adapters; FEAT-SMP-004
deletes the graph plumbing. See
``docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md``.
"""
from __future__ import annotations

from study_tutor.knowledge.store.entities import (
    Achievement,
    ConfidenceUpdate,
    MisconceptionSnapshot,
    Quest,
    SessionRecord,
    SessionStatus,
    SessionTurn,
    StudentState,
    TopicConfidenceSnapshot,
    TopicRecommendation,
    TurnRole,
)
from study_tutor.knowledge.store.port import StudentStore

__all__ = [
    "Achievement",
    "ConfidenceUpdate",
    "MisconceptionSnapshot",
    "Quest",
    "SessionRecord",
    "SessionStatus",
    "SessionTurn",
    "StudentState",
    "StudentStore",
    "TopicConfidenceSnapshot",
    "TopicRecommendation",
    "TurnRole",
]
