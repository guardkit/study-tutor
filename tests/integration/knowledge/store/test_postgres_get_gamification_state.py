"""Integration tests for ``PostgresStudentStore.get_gamification_state``.

Read-side gamification projection over the real ``session`` + ``achievement``
tables, **banked-facts** edition (spec §5 / B3): the read sums the ``xp_awarded``
settlement banked on each row — it no longer re-derives XP from durations — and
folds London-calendar streaks and the achievement views. Runs against an
ephemeral PostgreSQL container (see ``conftest.py``).

The final test drives the whole thing end-to-end: a real ``SessionService`` over
real Postgres starts a session, takes a turn, and ends it, then the banked XP is
shown flowing back through BOTH ``POST /api/sessions/{id}/end`` (the Rev 2
gamification block) and ``GET /api/student-model`` (the §2.2.1 enrichment).
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
from study_tutor.session.service import SessionService, TutorReply

UTC = timezone.utc


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
            "created_at": datetime.now(UTC),
        },
    )


async def _add_ended_session(
    conn,
    *,
    session_id: str,
    student_id: str,
    started_at: datetime,
    last_activity: datetime,
    xp_awarded: int,
    status: str = "ended",
) -> None:
    """Seed a session with a **banked** ``xp_awarded`` — the read sums it verbatim."""
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
            "xp_awarded": xp_awarded,
            "aos_scaffolded": "[]",
        },
    )


@pytest.fixture
async def clean_store(postgres_container):
    dsn = postgres_container
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        # FK-safe order: settlement children before their parents.
        await conn.execute(text("DELETE FROM achievement"))
        await conn.execute(text("DELETE FROM topic_confidence_history"))
        await conn.execute(text("DELETE FROM session_turn"))
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM misconception"))
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
    assert state.level_number == 1
    assert state.streak_days == 0
    assert state.longest_streak == 0
    assert state.near_achievements == []
    assert state.recent_achievements == []


async def test_banked_sessions_and_achievements_sum_into_state(
    clean_store, postgres_container
) -> None:
    now = datetime.now(UTC)
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        await _seed_student(conn)
        # Today: banked 180 XP.
        await _add_ended_session(
            conn,
            session_id="sess-today",
            student_id="lilymay",
            started_at=now - timedelta(minutes=40),
            last_activity=now,
            xp_awarded=180,
        )
        # Yesterday: banked 120 XP.
        await _add_ended_session(
            conn,
            session_id="sess-yesterday",
            student_id="lilymay",
            started_at=now - timedelta(days=1, minutes=20),
            last_activity=now - timedelta(days=1),
            xp_awarded=120,
        )
        # An active (in-flight) session banks nothing (status != ended).
        await _add_ended_session(
            conn,
            session_id="sess-active",
            student_id="lilymay",
            started_at=now - timedelta(minutes=30),
            last_activity=now,
            xp_awarded=0,
            status="active",
        )
        # A banked achievement adds its XP to the total (ADR-ARCH-030 D2).
        await conn.execute(
            text(
                "INSERT INTO achievement (achievement_id, student_id, unlocked_at, "
                "xp_awarded, session_id) VALUES (:aid, :sid, :ts, :xp, :session)"
            ),
            {
                "aid": "first_steps",
                "sid": "lilymay",
                "ts": now,
                "xp": 50,
                "session": "sess-today",
            },
        )
    await engine.dispose()

    state = await clean_store.get_gamification_state("lilymay")
    assert state.exists is True
    # total = SUM(session.xp) 300 + SUM(achievement.xp) 50 = 350.
    assert state.total_xp == 350
    assert state.recent_xp == 300  # session XP inside the 7-day window
    assert state.streak_days == 2  # today + yesterday (London credit days)
    assert state.longest_streak == 2
    assert state.level_name == "Apprentice"  # 350 ≥ 300
    # first_steps is banked → surfaces in recent, excluded from near.
    assert [r.id for r in state.recent_achievements] == ["first_steps"]
    assert all(n.id != "first_steps" for n in state.near_achievements)


async def test_streak_uses_london_calendar_across_utc_midnight(
    clean_store, postgres_container
) -> None:
    """A 23:30 UTC BST session lands on the *next* London day (spec §5 test)."""
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        await _seed_student(conn)
        # 2026-07-14 23:30 UTC = 2026-07-15 00:30 London (BST) → credit day 07-15.
        await _add_ended_session(
            conn,
            session_id="sess-a",
            student_id="lilymay",
            started_at=datetime(2026, 7, 14, 22, 30, tzinfo=UTC),
            last_activity=datetime(2026, 7, 14, 23, 30, tzinfo=UTC),
            xp_awarded=120,
        )
        # 2026-07-15 20:00 UTC = 21:00 London → also credit day 07-15.
        await _add_ended_session(
            conn,
            session_id="sess-b",
            student_id="lilymay",
            started_at=datetime(2026, 7, 15, 19, 0, tzinfo=UTC),
            last_activity=datetime(2026, 7, 15, 20, 0, tzinfo=UTC),
            xp_awarded=180,
        )
    await engine.dispose()

    state = await clean_store.get_gamification_state("lilymay")
    # Both sessions resolve to the single London day 2026-07-15.
    assert state.longest_streak == 1
    assert state.total_xp == 300


# -- Full HTTP stack over real Postgres (no fakes in the request path) --------


async def _seed_full_record(dsn: str) -> None:
    """Seed a realistic banked learner record directly in Postgres."""
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        await _seed_student(conn)
        await _add_ended_session(
            conn,
            session_id="e2e-today",
            student_id="lilymay",
            started_at=now - timedelta(minutes=40),
            last_activity=now,
            xp_awarded=180,
        )
        await _add_ended_session(
            conn,
            session_id="e2e-yesterday",
            student_id="lilymay",
            started_at=now - timedelta(days=1, minutes=20),
            last_activity=now - timedelta(days=1),
            xp_awarded=120,
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
    service/reply_fn are never touched by this GET handler. Asserts the original
    R05 fields AND the §2.2.1 enrichment over banked facts.
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
    # Original R05 fields.
    assert body["student_name"] == "Lily May"
    assert body["streak_days"] == 2
    assert body["level_name"] == "Apprentice"  # 300 XP ≥ 300
    assert body["recent_xp"] == 300
    assert body["topic_confidence"] == {"macbeth": 0.7}
    assert body["data_available"] is True
    # §2.2.1 enrichment.
    assert body["total_xp"] == 300
    assert body["level_number"] == 3
    assert body["longest_streak"] == 2
    assert body["next_unlock"] == {"level": 4, "feature": "Quest system"}
    assert isinstance(body["near_achievements"], list)
    assert isinstance(body["recent_achievements"], list)


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


# -- Full banked-XP round trip: start → turn → end → read (spec §5) -----------


async def _echo_reply(user_message: str) -> TutorReply:
    return TutorReply(response=f"tutor: {user_message}")


async def _drive_start_turn_and_stretch(dsn: str) -> str:
    """Clean the DB, then start a session and take a real turn via the composed
    service path, and stretch the turn timestamps to ≥ 20 min so settlement banks
    a real 120 XP.

    Uses its own store/engine (a distinct event loop from the TestClient below),
    persisting to the shared database; the app then reads it back with a fresh
    store bound to the TestClient's loop.
    """
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM achievement"))
        await conn.execute(text("DELETE FROM topic_confidence_history"))
        await conn.execute(text("DELETE FROM session_turn"))
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM misconception"))
        await conn.execute(text("DELETE FROM topic_confidence"))
        await conn.execute(text("DELETE FROM student"))
        await _seed_student(conn)
    await engine.dispose()

    setup_store = PostgresStudentStore(dsn)
    service = SessionService(store=setup_store)
    start = await service.start_session(
        student_id="lilymay", subject="english", topic="Macbeth"
    )
    session_id = start.session_id
    await service.turn(
        student_id="lilymay",
        session_id=session_id,
        user_message="Tell me about Act 1",
        reply_fn=_echo_reply,
    )

    # Backdate the earliest turn so engagement (max−min) is 20 min → 120 XP band.
    stretch = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with stretch.begin() as conn:
        await conn.execute(
            text(
                "UPDATE session_turn SET ts = ts - interval '20 minutes' "
                "WHERE session_id = :sid AND turn_index = 0"
            ),
            {"sid": session_id},
        )
    await stretch.dispose()
    return session_id


def test_banked_xp_flows_through_end_and_student_model(postgres_container) -> None:
    """A real session's banked XP appears in BOTH the end response's gamification
    block and the subsequent GET /api/student-model (spec §5).

    Depends on ``postgres_container`` directly (not the async ``clean_store``
    fixture) so the app's store is constructed in the sync test body and first
    touched in the TestClient's event loop — no cross-loop engine binding.
    """
    session_id = asyncio.run(_drive_start_turn_and_stretch(postgres_container))

    app_store = PostgresStudentStore(postgres_container)
    cfg = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    app = create_app(
        service=SessionService(store=app_store),
        reply_fn=AsyncMock(),
        auth_config=cfg,
        student_store=app_store,
    )
    # A single portal/loop spans both requests (the shared asyncpg pool is bound
    # to one loop) — hence the context-manager form for this two-request test.
    with TestClient(app) as client:
        # End the session through the app → settlement banks 120 XP (20-min band).
        end_resp = client.post(
            f"/api/sessions/{session_id}/end",
            headers={"Authorization": "Bearer token-lilymay"},
        )
        assert end_resp.status_code == 200
        block = end_resp.json()["gamification"]

        # The same banked XP (session + achievement) is now visible on the read
        # (total_xp = SUM(session.xp_awarded) + SUM(achievement.xp_awarded), D2).
        model_resp = client.get(
            "/api/student-model?subject=english",
            headers={"Authorization": "Bearer token-lilymay"},
        )

    # Session bands at 120 XP (20-min standard); the cascade then unlocks
    # First Steps (+50, first qualifying session) and First Century (+50, ≥100
    # total XP) → total 220 (design §13.1 D7 fixed-point cascade).
    assert block["xp_awarded"] == 120
    assert block["total_xp"] == 220
    assert block["level_number"] == 2  # Novice (100 ≤ 220 < 300)
    assert block["level_name"] == "Novice"
    assert block["streak_days"] == 1
    assert block["streak_extended"] is True
    unlocked_ids = {a["id"] for a in block["achievements_unlocked"]}
    assert unlocked_ids == {"first_steps", "first_century"}

    assert model_resp.status_code == 200
    model = model_resp.json()
    assert model["total_xp"] == 220
    assert model["level_name"] == "Novice"
    assert model["streak_days"] == 1
    assert model["recent_xp"] == 120  # session XP in the window (achievement XP excluded)
    assert model["data_available"] is True
    recent_ids = {r["id"] for r in model["recent_achievements"]}
    assert recent_ids == {"first_steps", "first_century"}
