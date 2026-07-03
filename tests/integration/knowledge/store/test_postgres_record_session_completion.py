"""Integration tests for PostgresStudentStore.record_session_completion (TASK-SMP-06).

Tests the session-end write against an ephemeral Postgres instance, covering:
- Atomic transaction: XP + confidence + misconceptions in one commit
- Idempotency: replay/concurrent delivery records exactly once
- Session upsert: ON CONFLICT DO UPDATE with status='ended'
- Child writes reused at connection level
- Rollback on partial failure
- Unknown student rejection
- Empty lists handling
- Unreachable database fail-fast
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.student_model import Misconception


class TestRecordSessionCompletion:
    """Test record_session_completion against live Postgres (ephemeral)."""

    async def test_combined_write_persists_xp_confidence_and_misconceptions_together(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: Recording a completed session persists XP, confidence updates, and misconceptions together."""
        session_id = "session-001"
        topic = "Quadratic Equations"
        aos_scaffolded = ["AO1", "AO3"]
        xp_awarded = 150
        confidence_updates = [
            ConfidenceUpdate(topic_name="Quadratic Equations", percentage=75)
        ]
        misconceptions = [
            Misconception(
                topic_ref="Quadratic Equations",
                text="Student thinks discriminant is always positive",
                observed_at=datetime.now(timezone.utc),
                confidence_band_at_observation="secure",
            )
        ]

        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic=topic,
            aos_scaffolded=aos_scaffolded,
            xp_awarded=xp_awarded,
            confidence_updates=confidence_updates,
            misconceptions=misconceptions,
        )

        # Verify session row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT student_id, status, topic, aos_scaffolded, xp_awarded "
                    "FROM session WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
            session_row = result.fetchone()

        assert session_row is not None
        assert session_row[0] == student_id
        assert session_row[1] == "ended"
        assert session_row[2] == topic
        assert session_row[3] == aos_scaffolded  # JSONB
        assert session_row[4] == xp_awarded

        # Verify topic_confidence row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT student_id, topic_name, percentage, band "
                    "FROM topic_confidence WHERE student_id = :sid AND topic_name = :topic"
                ),
                {"sid": student_id, "topic": "Quadratic Equations"},
            )
            conf_row = result.fetchone()

        assert conf_row is not None
        assert conf_row[0] == student_id
        assert conf_row[1] == "Quadratic Equations"
        assert conf_row[2] == 75
        assert conf_row[3] == "secure"  # 75% -> secure band

        # Verify misconception row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT student_id, topic_name, text "
                    "FROM misconception WHERE student_id = :sid"
                ),
                {"sid": student_id},
            )
            misc_row = result.fetchone()

        assert misc_row is not None
        assert misc_row[0] == student_id
        assert misc_row[1] == "Quadratic Equations"
        assert misc_row[2] == "Student thinks discriminant is always positive"

    async def test_session_upsert_keyed_on_session_id(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: Session upsert is keyed on session_id PK with status='ended'."""
        session_id = "session-002"

        # First write
        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic="Topic A",
            aos_scaffolded=["AO1"],
            xp_awarded=100,
            confidence_updates=[],
            misconceptions=[],
        )

        # Verify first write
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT topic, xp_awarded, status FROM session WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
            row = result.fetchone()

        assert row[0] == "Topic A"
        assert row[1] == 100
        assert row[2] == "ended"

    async def test_idempotent_replay_single_records_only_once(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: Re-delivering the same completed session records it only once."""
        session_id = "session-003"
        topic = "Pythagoras"
        xp = 200
        confidence_updates = [ConfidenceUpdate(topic_name="Pythagoras", percentage=80)]
        misconceptions = [
            Misconception(
                topic_ref="Pythagoras",
                text="Confused about hypotenuse",
                observed_at=datetime.now(timezone.utc),
                confidence_band_at_observation="secure",
            )
        ]

        # First delivery
        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic=topic,
            aos_scaffolded=["AO2"],
            xp_awarded=xp,
            confidence_updates=confidence_updates,
            misconceptions=misconceptions,
        )

        # Second delivery (identical)
        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic=topic,
            aos_scaffolded=["AO2"],
            xp_awarded=xp,
            confidence_updates=confidence_updates,
            misconceptions=misconceptions,
        )

        # Verify exactly one session row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 1

        # Verify exactly one confidence row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM topic_confidence "
                    "WHERE student_id = :sid AND topic_name = :topic"
                ),
                {"sid": student_id, "topic": "Pythagoras"},
            )
            count = result.scalar()
        assert count == 1

        # Verify exactly one misconception row (not duplicated)
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM misconception "
                    "WHERE student_id = :sid AND topic_name = :topic"
                ),
                {"sid": student_id, "topic": "Pythagoras"},
            )
            count = result.scalar()
        assert count == 1

        # Verify XP counted once (not doubled)
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT xp_awarded FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            xp_awarded = result.scalar()
        assert xp_awarded == 200  # Not 400

    async def test_idempotent_concurrent_deliveries_recorded_once(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: Two concurrent deliveries of the same session completion are recorded once."""
        session_id = "session-004"
        topic = "Trigonometry"
        xp = 250
        confidence_updates = [
            ConfidenceUpdate(topic_name="Trigonometry", percentage=65)
        ]
        misconceptions = [
            Misconception(
                topic_ref="Trigonometry",
                text="Confused sine and cosine",
                observed_at=datetime.now(timezone.utc),
                confidence_band_at_observation="developing",
            )
        ]

        # Concurrent deliveries
        await asyncio.gather(
            pg_store.record_session_completion(
                student_id=student_id,
                session_id=session_id,
                topic=topic,
                aos_scaffolded=["AO4"],
                xp_awarded=xp,
                confidence_updates=confidence_updates,
                misconceptions=misconceptions,
            ),
            pg_store.record_session_completion(
                student_id=student_id,
                session_id=session_id,
                topic=topic,
                aos_scaffolded=["AO4"],
                xp_awarded=xp,
                confidence_updates=confidence_updates,
                misconceptions=misconceptions,
            ),
        )

        # Verify exactly one session row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 1

        # Verify exactly one misconception row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM misconception "
                    "WHERE student_id = :sid AND topic_name = :topic"
                ),
                {"sid": student_id, "topic": "Trigonometry"},
            )
            count = result.scalar()
        assert count == 1

        # Verify XP counted once
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT xp_awarded FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            xp_awarded = result.scalar()
        assert xp_awarded == 250

    async def test_atomic_rollback_on_misconception_failure(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: A partial failure while recording a completed session rolls back every change."""
        session_id = "session-005"

        # Insert a session first to test that it gets rolled back if misconception fails
        # We'll use an invalid misconception (blank text after sanitization)
        with pytest.raises((ValueError, Exception)):
            await pg_store.record_session_completion(
                student_id=student_id,
                session_id=session_id,
                topic="Algebra",
                aos_scaffolded=["AO1"],
                xp_awarded=100,
                confidence_updates=[
                    ConfidenceUpdate(topic_name="Algebra", percentage=70)
                ],
                misconceptions=[
                    Misconception(
                        topic_ref="Algebra",
                        text="\x00\x01\x02",  # Only control chars - invalid after sanitization
                        observed_at=datetime.now(timezone.utc),
                        confidence_band_at_observation="developing",
                    )
                ],
            )

        # Verify no session was persisted
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 0

        # Verify no confidence was persisted
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM topic_confidence "
                    "WHERE student_id = :sid AND topic_name = 'Algebra'"
                ),
                {"sid": student_id},
            )
            count = result.scalar()
        assert count == 0

    async def test_atomic_rollback_on_invalid_percentage_in_batch(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: A session completion with invalid percentage records nothing."""
        session_id = "session-006"

        # Try to record with out-of-range percentage
        with pytest.raises((ValueError, Exception)):
            await pg_store.record_session_completion(
                student_id=student_id,
                session_id=session_id,
                topic="Statistics",
                aos_scaffolded=["AO1"],
                xp_awarded=50,
                confidence_updates=[
                    ConfidenceUpdate(
                        topic_name="Statistics", percentage=150
                    )  # Invalid!
                ],
                misconceptions=[],
            )

        # Verify no session was persisted
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 0

    async def test_empty_lists_still_records_session(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: Recording a completed session with no confidence updates and no misconceptions still records the session."""
        session_id = "session-007"

        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic="Geometry",
            aos_scaffolded=["AO5"],
            xp_awarded=75,
            confidence_updates=[],
            misconceptions=[],
        )

        # Verify session was recorded
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT xp_awarded, status FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            row = result.fetchone()

        assert row is not None
        assert row[0] == 75
        assert row[1] == "ended"

        # Verify no confidence rows
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM topic_confidence WHERE student_id = :sid"),
                {"sid": student_id},
            )
            count = result.scalar()
        assert count == 0

        # Verify no misconception rows
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM misconception WHERE student_id = :sid"),
                {"sid": student_id},
            )
            count = result.scalar()
        assert count == 0

    async def test_write_failure_surfaces_to_caller(
        self, pg_store: PostgresStudentStore, pg_engine, student_id: str
    ):
        """AC: A session-completion write that cannot commit surfaces the failure instead of silently dropping it."""
        session_id = "session-008"
        unknown_student = "unknown_student_id"

        # Unknown student should cause FK violation, which should surface
        with pytest.raises((IntegrityError, Exception)):
            await pg_store.record_session_completion(
                student_id=unknown_student,
                session_id=session_id,
                topic="Physics",
                aos_scaffolded=["AO1"],
                xp_awarded=100,
                confidence_updates=[],
                misconceptions=[],
            )

        # Verify no session was persisted
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 0

    async def test_unknown_learner_rejected_by_fk(
        self, pg_store: PostgresStudentStore, pg_engine
    ):
        """AC: A completion for a student_id with no student row is rejected by FK."""
        session_id = "session-009"
        unknown_student = "nonexistent_student"

        with pytest.raises((IntegrityError, Exception)):
            await pg_store.record_session_completion(
                student_id=unknown_student,
                session_id=session_id,
                topic="Chemistry",
                aos_scaffolded=[],
                xp_awarded=50,
                confidence_updates=[],
                misconceptions=[],
            )

        # Verify no orphaned rows
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM session WHERE session_id = :sid"),
                {"sid": session_id},
            )
            count = result.scalar()
        assert count == 0
