"""Integration tests for PostgresStudentStore.get_recent_misconceptions (TASK-SMP2-02).

Tests the window-filtered SELECT over misconception with band-at-observation
approximation via LEFT JOIN to topic_confidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text as sql_text

from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.student_model import Misconception


@pytest.mark.asyncio
async def test_returns_misconceptions_within_window(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """Recent misconceptions observed within window_days are returned."""
    now = datetime.now(timezone.utc)

    # Insert misconceptions at different times
    async with pg_engine.begin() as conn:
        # Within window (20 days ago)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "algebra",
                "text": "Confuses variable with coefficient",
                "observed": now - timedelta(days=20),
            },
        )
        # Within window (10 days ago)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "geometry",
                "text": "Forgets Pythagoras theorem",
                "observed": now - timedelta(days=10),
            },
        )
        # Outside window (40 days ago)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "calculus",
                "text": "Confuses derivative with integral",
                "observed": now - timedelta(days=40),
            },
        )

    # Query with default 30-day window
    result = await pg_store.get_recent_misconceptions(student_id)

    assert len(result) == 2
    assert all(isinstance(m, Misconception) for m in result)

    # Newest first (geometry at 10 days ago)
    assert result[0].topic_ref == "geometry"
    assert result[0].text == "Forgets Pythagoras theorem"
    assert result[1].topic_ref == "algebra"
    assert result[1].text == "Confuses variable with coefficient"


@pytest.mark.asyncio
async def test_window_boundary_inclusive(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """Misconception observed exactly window_days ago is INCLUDED."""
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        # Well within window (25 days ago - should be included)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "algebra",
                "text": "At 25-day mark",
                "observed": now - timedelta(days=25),
            },
        )
        # Well outside window (35 days ago - should be excluded)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "geometry",
                "text": "At 35-day mark",
                "observed": now - timedelta(days=35),
            },
        )
        # Just inside window (29 days ago - should be included)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "calculus",
                "text": "At 29-day mark",
                "observed": now - timedelta(days=29),
            },
        )

    result = await pg_store.get_recent_misconceptions(student_id, window_days=30)

    # Should return exactly 2: the ones at 25 and 29 days
    assert len(result) == 2
    texts = {m.text for m in result}
    assert "At 25-day mark" in texts
    assert "At 29-day mark" in texts
    assert "At 35-day mark" not in texts


@pytest.mark.asyncio
async def test_custom_window_narrows_results(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """A caller-supplied window_days narrows results."""
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        # 5 days ago
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "algebra",
                "text": "Recent one",
                "observed": now - timedelta(days=5),
            },
        )
        # 15 days ago
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "geometry",
                "text": "Older one",
                "observed": now - timedelta(days=15),
            },
        )

    # With 7-day window, only the 5-day-old one should appear
    result = await pg_store.get_recent_misconceptions(student_id, window_days=7)

    assert len(result) == 1
    assert result[0].text == "Recent one"


@pytest.mark.asyncio
async def test_band_approximation_from_current_confidence(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """confidence_band_at_observation is populated from current topic_confidence."""
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        # Insert misconception for algebra
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "algebra",
                "text": "Variable confusion",
                "observed": now - timedelta(days=10),
            },
        )
        # Insert misconception for geometry (no confidence row)
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "geometry",
                "text": "Shape confusion",
                "observed": now - timedelta(days=5),
            },
        )
        # Insert current confidence for algebra
        await conn.execute(
            sql_text(
                "INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at) "
                "VALUES (:sid, :topic, :pct, :band, :revised)"
            ),
            {
                "sid": student_id,
                "topic": "algebra",
                "pct": 75,
                "band": "developing",
                "revised": now,
            },
        )

    result = await pg_store.get_recent_misconceptions(student_id)

    assert len(result) == 2

    # Find each misconception
    algebra_misc = next(m for m in result if m.topic_ref == "algebra")
    geometry_misc = next(m for m in result if m.topic_ref == "geometry")

    # Algebra should have current band from topic_confidence
    assert algebra_misc.confidence_band_at_observation == "developing"

    # Geometry should default to "struggling" (no confidence row)
    assert geometry_misc.confidence_band_at_observation == "struggling"


@pytest.mark.asyncio
async def test_text_and_observed_at_direct_from_row(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """text, topic_ref, and observed_at come straight from the row."""
    now = datetime.now(timezone.utc)
    observed_time = now - timedelta(days=5)  # Within default 30-day window

    async with pg_engine.begin() as conn:
        await conn.execute(
            sql_text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:sid, :topic, :text, :observed)"
            ),
            {
                "sid": student_id,
                "topic": "trigonometry",
                "text": "SOHCAHTOA confusion",
                "observed": observed_time,
            },
        )

    result = await pg_store.get_recent_misconceptions(student_id)

    assert len(result) == 1
    m = result[0]
    assert m.text == "SOHCAHTOA confusion"
    assert m.topic_ref == "trigonometry"
    assert m.observed_at == observed_time


@pytest.mark.asyncio
async def test_no_misconceptions_returns_empty(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """Student with no in-window misconceptions returns empty list."""
    result = await pg_store.get_recent_misconceptions(student_id)

    assert result == []


@pytest.mark.asyncio
async def test_unknown_student_returns_empty(
    pg_store: PostgresStudentStore, pg_engine
):
    """Unknown student_id returns empty list (graceful degradation)."""
    result = await pg_store.get_recent_misconceptions("unknown-student-999")

    assert result == []


@pytest.mark.asyncio
async def test_ordered_newest_first(
    pg_store: PostgresStudentStore, pg_engine, student_id: str
):
    """Results are ordered by observed_at DESC (newest first)."""
    now = datetime.now(timezone.utc)

    times = [
        now - timedelta(days=25),
        now - timedelta(days=5),
        now - timedelta(days=15),
    ]

    async with pg_engine.begin() as conn:
        for i, t in enumerate(times):
            await conn.execute(
                sql_text(
                    "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                    "VALUES (:sid, :topic, :text, :observed)"
                ),
                {
                    "sid": student_id,
                    "topic": f"topic-{i}",
                    "text": f"Misconception {i}",
                    "observed": t,
                },
            )

    result = await pg_store.get_recent_misconceptions(student_id)

    assert len(result) == 3
    # Should be ordered by observed_at DESC
    assert result[0].observed_at == times[1]  # 5 days ago (newest)
    assert result[1].observed_at == times[2]  # 15 days ago
    assert result[2].observed_at == times[0]  # 25 days ago (oldest)
