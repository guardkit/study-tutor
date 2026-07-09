"""Integration tests for ``PostgresStudentStore.get_gamification_state``.

Read-side gamification projection (FEAT-VOICE-004 R05) over the real ``session``
table: streak / level / recent-XP derived from ``ended`` sessions. Runs against
an ephemeral PostgreSQL container (see ``conftest.py``).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.testclient import TestClient

from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from study_tutor.knowledge.store.postgres import PostgresStudentStore


async def _seed_student(conn, student_id: str = "lilymay", name: str = "Lily May") -> None:
    await conn.execute(
        text(
            "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
            "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
        ),
        {
            "student_id": student_id,
            "name": name,
            "year_group": 10,
            "target_grade": "7",
            "created_at": datetime.now(timezone.utc),
        },
    )


async def _add_ended_session(
    conn,
    *,
    session_id: str,
    student_id: str,
    started_at: datetime,
    last_activity: datetime,
    status: str = "ended",
) -> None:
    await conn.execute(
        text(
            "INSERT INTO session (session_id, student_id, subject, topic, status, "
            "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded) "
            "VALUES (:session_id, :student_id, :subject, :topic, :status, "
            ":started_at, :last_activity, :turn_count, :xp_awarded, CAST(:aos_scaffolded AS JSONB))"
        ),
        {
            "session_id": session_id,
            "student_id": student_id,
            "subject": "English",
            "topic": "Macbeth",
            "status": status,
            "started_at": started_at,
            "last_activity": last_activity,
            "turn_count": 4,
            "xp_awarded": 0,  # the session-end placeholder; the read derives XP itself
            "aos_scaffolded": "[]",
        },
    )


@pytest.fixture
async def clean_store(postgres_container):
    dsn = postgres_container
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM topic_confidence"))
        await conn.execute(text("DELETE FROM student"))
    await engine.dispose()
    return PostgresStudentStore(dsn)


async def test_unknown_student_returns_exists_false(clean_store) -> None:
    state = await clean_store.get_gamification_state("nobody")
    assert state.exists is False
    assert state.total_xp == 0
    assert state.streak_days == 0


async def test_seeded_but_empty_is_zeroed_beginner(
    clean_store, postgres_container
) -> None:
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        await _seed_student(conn)
    await engine.dispose()

    state = await clean_store.get_gamification_state("lilymay")
    assert state.exists is True
    assert state.student_name == "Lily May"
    assert state.total_xp == 0
    assert state.level_name == "Beginner"
    assert state.streak_days == 0


async def test_ended_sessions_bank_real_xp_streak_and_level(
    clean_store, postgres_container
) -> None:
    now = datetime.now(timezone.utc)
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        await _seed_student(conn)
        # Today: 40-min long session → 180 XP.
        await _add_ended_session(
            conn,
            session_id="sess-today",
            student_id="lilymay",
            started_at=now - timedelta(minutes=40),
            last_activity=now,
        )
        # Yesterday: 20-min standard session → 120 XP.
        await _add_ended_session(
            conn,
            session_id="sess-yesterday",
            student_id="lilymay",
            started_at=now - timedelta(days=1, minutes=20),
            last_activity=now - timedelta(days=1),
        )
        # An active (in-flight) session must not bank XP or extend the streak.
        await _add_ended_session(
            conn,
            session_id="sess-active",
            student_id="lilymay",
            started_at=now - timedelta(minutes=30),
            last_activity=now,
            status="active",
        )
    await engine.dispose()

    state = await clean_store.get_gamification_state("lilymay")
    assert state.exists is True
    assert state.total_xp == 300  # 180 + 120; active session excluded
    assert state.recent_xp == 300  # both completed sessions inside 7-day window
    assert state.streak_days == 2  # today + yesterday
    assert state.level_name == "Apprentice"  # 300 ≥ 300


# -- Full HTTP stack over real Postgres (no fakes in the request path) --------


async def _seed_full_record(dsn: str) -> None:
    """Seed a realistic learner record directly in Postgres."""
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await _seed_student(conn)
        await _add_ended_session(
            conn,
            session_id="e2e-today",
            student_id="lilymay",
            started_at=now - timedelta(minutes=40),
            last_activity=now,
        )
        await _add_ended_session(
            conn,
            session_id="e2e-yesterday",
            student_id="lilymay",
            started_at=now - timedelta(days=1, minutes=20),
            last_activity=now - timedelta(days=1),
        )
        await conn.execute(
            text(
                "INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at) "
                "VALUES (:sid, :topic, :pct, :band, :revised)"
            ),
            {
                "sid": "lilymay",
                "topic": "macbeth",
                "pct": 70,
                "band": "secure",
                "revised": now,
            },
        )
    await engine.dispose()


def test_http_endpoint_happy_over_real_postgres(clean_store, postgres_container) -> None:
    """GET /api/student-model through the real Starlette app + real Postgres.

    The request path uses ONLY the real PostgresStudentStore and real auth —
    service/reply_fn are never touched by this GET handler.
    """
    asyncio.run(_seed_full_record(postgres_container))
    cfg = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay", "token-ghost": "ghost"},
        dev_reset=False,
    )
    client = TestClient(
        create_app(
            service=AsyncMock(),
            reply_fn=AsyncMock(),
            auth_config=cfg,
            student_store=clean_store,
        )
    )
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer token-lilymay"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_name"] == "Lily May"
    assert body["streak_days"] == 2
    assert body["level_name"] == "Apprentice"
    assert body["recent_xp"] == 300
    assert body["topic_confidence"] == {"macbeth": 0.7}
    assert body["near_achievements"] == []
    assert body["data_available"] is True


def test_http_endpoint_unseeded_is_401_over_real_postgres(clean_store) -> None:
    """Unseeded token → 401 via the real student_exists SQL (never 500)."""
    cfg = HTTPAuthConfig(
        token_to_student={"token-ghost": "ghost"}, dev_reset=False
    )
    client = TestClient(
        create_app(
            service=AsyncMock(),
            reply_fn=AsyncMock(),
            auth_config=cfg,
            student_store=clean_store,
        )
    )
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer token-ghost"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"
