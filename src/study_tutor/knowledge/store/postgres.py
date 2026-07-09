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

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    text as sql_text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from study_tutor.gamification import build_gamification_state
from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
    GamificationState,
    MisconceptionSnapshot,
    SessionRecord,
    SessionStatus,
    SessionTurn,
    StudentState,
    TopicConfidenceSnapshot,
    TurnRole,
)
from study_tutor.knowledge.store.port import (
    DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    DEFAULT_SESSION_LIST_LIMIT,
)
from study_tutor.knowledge.student_model import (
    Misconception,
    TopicConfidence,
    confidence_band_for,
)

_NOT_IMPLEMENTED = "PostgresStudentStore is a FEAT-SMP-001 skeleton"

# ASCII control characters to strip (preserves TAB, LF, CR per ASSUM-007)
# Strips: \x00-\x08, \x0B-\x0C, \x0E-\x1F, \x7F (DEL)
# Preserves: \x09 (TAB), \x0A (LF), \x0D (CR)
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")

# Maximum length for misconception text (ASSUM-004)
_MAX_MISCONCEPTION_TEXT_LENGTH = 500


def _sanitise_misconception_text(text: str) -> str:
    """Sanitise misconception text: strip control chars, cap at 500 chars.

    Text hygiene for F1 misconception writes (TASK-SMP-05). Reduced from the
    retired sanitiser — ONLY control-char stripping + length cap. Does NOT
    apply NFKC normalisation, zero-width stripping, or injection rejection
    (ASSUM-005: opaque data storage, no extraction LLM on Postgres path).

    Args:
        text: Raw misconception text from observation.

    Returns:
        Sanitised text: control chars removed, capped at 500 chars.
    """
    # Strip ASCII control chars (preserving tab/newline/CR)
    cleaned = _CONTROL_CHARS_PATTERN.sub("", text)

    # Cap at 500 characters
    if len(cleaned) > _MAX_MISCONCEPTION_TEXT_LENGTH:
        cleaned = cleaned[:_MAX_MISCONCEPTION_TEXT_LENGTH]

    return cleaned


async def _upsert_confidence(
    conn: AsyncConnection, student_id: str, update: ConfidenceUpdate
) -> None:
    """Upsert topic_confidence at connection level (reused by record_session_completion).

    Derives band via confidence_band_for at write time and stamps last_revised_at in UTC.
    Enlists in the caller's open transaction.

    Args:
        conn: Open AsyncConnection (already in a transaction).
        student_id: The student identifier (FK to student table).
        update: ConfidenceUpdate with topic_name and percentage [0, 100].

    Raises:
        ValueError: If percentage is outside [0, 100].
    """
    # Derive band (also validates percentage is in [0, 100])
    band = confidence_band_for(update.percentage)

    # Compute timestamp app-side for deterministic/testable UTC
    now_utc = datetime.now(timezone.utc)

    # Build table metadata
    metadata = MetaData()
    topic_confidence = Table(
        "topic_confidence",
        metadata,
        Column("student_id", String),
        Column("topic_name", String),
        Column("percentage", Integer),
        Column("band", String),
        Column("last_revised_at", DateTime(timezone=True)),
    )

    # Build INSERT ... ON CONFLICT DO UPDATE
    stmt = postgresql.insert(topic_confidence).values(
        student_id=student_id,
        topic_name=update.topic_name,
        percentage=update.percentage,
        band=band,
        last_revised_at=now_utc,
    )

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["student_id", "topic_name"],
        set_={
            "percentage": stmt.excluded.percentage,
            "band": stmt.excluded.band,
            "last_revised_at": stmt.excluded.last_revised_at,
        },
    )

    await conn.execute(upsert_stmt)


async def _insert_misconception(
    conn: AsyncConnection, student_id: str, topic_name: str, text: str
) -> None:
    """Insert misconception at connection level (reused by record_session_completion).

    Applies text hygiene (control-char strip + 500-char cap) before insert.
    Enlists in the caller's open transaction.

    Args:
        conn: Open AsyncConnection (already in a transaction).
        student_id: Student identifier (FK to student table).
        topic_name: Topic the misconception relates to.
        text: Raw misconception text from observation.

    Raises:
        ValueError: If topic_name or text (after sanitisation) is blank.
    """
    # Validate topic_name is not blank
    if not topic_name or not topic_name.strip():
        raise ValueError("topic_name cannot be blank")

    # Apply text hygiene: strip control chars, cap at 500
    sanitised_text = _sanitise_misconception_text(text)

    # Validate sanitised text is not blank (catches control-char-only input)
    if not sanitised_text.strip():
        raise ValueError("text cannot be blank after sanitisation")

    # Compute timestamp app-side for deterministic/testable UTC
    observed_at = datetime.now(timezone.utc)

    # Build parameterised INSERT statement
    insert_stmt = sql_text(
        "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
        "VALUES (:student_id, :topic_name, :text, :observed_at)"
    )

    await conn.execute(
        insert_stmt,
        {
            "student_id": student_id,
            "topic_name": topic_name,
            "text": sanitised_text,
            "observed_at": observed_at,
        },
    )


class PostgresStudentStore:
    """Postgres-backed :class:`StudentStore`. Skeleton — bodies land in FEAT-SMP-001."""

    def __init__(self, dsn: str, *, pool: Any | None = None) -> None:
        """Build async engine from DSN or use injected pool.

        When ``pool`` is None, creates exactly one shared ``AsyncEngine`` from
        ``dsn`` (coerced to ``postgresql+asyncpg://`` dialect). When a
        pool/engine is injected via ``pool=``, no engine is built and the
        injected object is used as-is (test seam).
        """
        self._dsn = dsn
        self._pool = pool
        self._engine: AsyncEngine | None = None

        if pool is None:
            # Coerce DSN to asyncpg dialect for async engine
            url = make_url(dsn)
            if url.drivername == "postgresql":
                url = url.set(drivername="postgresql+asyncpg")
            elif url.drivername != "postgresql+asyncpg":
                # Accept postgresql+asyncpg as-is, others coerce
                if not url.drivername.startswith("postgresql"):
                    url = url.set(drivername="postgresql+asyncpg")

            # Build single shared engine (reused for every connection)
            self._engine = create_async_engine(url)

    # -- Health -------------------------------------------------------------

    async def ping(self) -> bool:
        """Health check: SELECT 1 against the database.

        Returns True when the database is reachable. The engine/pool must be
        configured before calling this method.
        """
        if self._pool is not None:
            # Use injected pool/engine
            engine = self._pool
        elif self._engine is not None:
            # Use our built engine
            engine = self._engine
        else:
            raise RuntimeError("No engine or pool configured")

        async with engine.connect() as conn:
            await conn.execute(sql_text("SELECT 1"))
            return True

    # -- Student identity seeding (TASK-APP1-05) ---------------------------

    async def student_exists(self, student_id: str) -> bool:
        """Check if student has an identity row (unseeded-student guard).

        Args:
            student_id: Student identifier to check.

        Returns:
            True if student row exists, False otherwise.

        Raises:
            Database errors propagate (not swallowed).
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection
        async with engine.connect() as conn:
            result = await conn.execute(
                sql_text("SELECT 1 FROM student WHERE student_id = :sid"),
                {"sid": student_id},
            )
            return result.fetchone() is not None

    async def seed_student(
        self,
        student_id: str,
        *,
        name: str,
        year_group: int,
        target_grade: str,
    ) -> bool:
        """Seed student identity row idempotently (TASK-APP1-05).

        Uses INSERT ... ON CONFLICT DO NOTHING semantics to ensure exactly one
        row per student_id. Identity row ONLY — does not touch topic_confidence
        or other learner state (baseline seeding stays with FEAT-SMP-004).

        Args:
            student_id: Student identifier (PK).
            name: Student full name.
            year_group: Year group (7-13 per schema CHECK constraint).
            target_grade: Target GCSE grade.

        Returns:
            True if row was inserted, False if already existed (idempotent).

        Raises:
            ValueError: If year_group is outside [7, 13] range.
            Database errors propagate (constraint violations, etc.).
        """
        # Validate year_group range (matches schema CHECK constraint)
        if not (7 <= year_group <= 13):
            raise ValueError(f"year_group must be between 7 and 13, got {year_group}")

        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Compute timestamp app-side for deterministic/testable UTC
        now_utc = datetime.now(timezone.utc)

        # Build table metadata
        metadata = MetaData()
        student_table = Table(
            "student",
            metadata,
            Column("student_id", String, primary_key=True),
            Column("name", String),
            Column("year_group", Integer),
            Column("target_grade", String),
            Column("created_at", DateTime(timezone=True)),
        )

        # INSERT ... ON CONFLICT DO NOTHING (idempotent)
        stmt = postgresql.insert(student_table).values(
            student_id=student_id,
            name=name,
            year_group=year_group,
            target_grade=target_grade,
            created_at=now_utc,
        )

        # ON CONFLICT: do nothing, return 0 rows
        # We use RETURNING to detect if insert happened
        idempotent_stmt = stmt.on_conflict_do_nothing(
            index_elements=["student_id"]
        ).returning(student_table.c.student_id)

        # Execute in transaction
        async with engine.begin() as conn:
            result = await conn.execute(idempotent_stmt)
            inserted_row = result.fetchone()

        # If a row was returned, insert happened; otherwise already existed
        return inserted_row is not None

    async def truncate_sessions(self) -> dict[str, int]:
        """Truncate session and session_turn tables (dev reset, TASK-APP1-05).

        Deletes ALL rows from session and session_turn tables. Learner-state
        tables (student, topic_confidence, misconception, achievement, quest)
        are NOT touched — XP/streak/confidence survive the reset.

        Returns:
            Dict with deleted counts: {"sessions": N, "turns": M}

        Raises:
            Database errors propagate.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Single transaction for both truncates
        async with engine.begin() as conn:
            # Count before deletion
            session_count_result = await conn.execute(
                sql_text("SELECT COUNT(*) FROM session")
            )
            session_count = session_count_result.scalar()

            turn_count_result = await conn.execute(
                sql_text("SELECT COUNT(*) FROM session_turn")
            )
            turn_count = turn_count_result.scalar()

            # TRUNCATE both tables (CASCADE handles FK constraints)
            await conn.execute(sql_text("TRUNCATE TABLE session CASCADE"))

        return {"sessions": session_count or 0, "turns": turn_count or 0}

    # -- Reads --------------------------------------------------------------

    async def get_student_state(self, student_id: str) -> StudentState:
        """Aggregate learner snapshot from Postgres (TASK-SMP2-03).

        Returns a complete StudentState combining student profile, topic
        confidences, recent misconceptions, and most recent session ID.

        Early-returns StudentState(empty=True) when student_id has no row,
        avoiding unnecessary child queries. DB/connection errors propagate
        for graceful degradation by callers.

        Args:
            student_id: Student identifier to query.

        Returns:
            StudentState with empty=False for known students, empty=True for
            unknown. All timestamps are timezone-aware UTC.

        Raises:
            Database errors propagate (not swallowed) so callers can degrade.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection (all four SELECTs on one connection)
        async with engine.connect() as conn:
            # 1. Check student existence FIRST (early return for unknown learner)
            student_result = await conn.execute(
                sql_text(
                    "SELECT student_id, year_group, target_grade "
                    "FROM student "
                    "WHERE student_id = :sid"
                ),
                {"sid": student_id},
            )
            student_row = student_result.fetchone()

            # Unknown student → empty=True (avoids three more queries)
            if student_row is None:
                return StudentState(empty=True)

            # Extract student profile
            year_group = student_row[1]
            target_grade = student_row[2]

            # 2. Read topic_confidence rows → TopicConfidenceSnapshot[]
            confidence_result = await conn.execute(
                sql_text(
                    "SELECT topic_name, percentage, band, last_revised_at "
                    "FROM topic_confidence "
                    "WHERE student_id = :sid "
                    "ORDER BY last_revised_at DESC"
                ),
                {"sid": student_id},
            )
            confidence_rows = confidence_result.fetchall()

            topic_confidences = [
                TopicConfidenceSnapshot(
                    topic_name=row[0],
                    percentage=row[1],
                    band=row[2],
                    last_revised_at=row[3],
                )
                for row in confidence_rows
            ]

            # 3. Read misconception rows within 30-day window → MisconceptionSnapshot[]
            cutoff = datetime.now(timezone.utc) - timedelta(
                days=DEFAULT_MISCONCEPTION_WINDOW_DAYS
            )
            misconception_result = await conn.execute(
                sql_text(
                    "SELECT topic_name, text, observed_at "
                    "FROM misconception "
                    "WHERE student_id = :sid AND observed_at >= :cutoff "
                    "ORDER BY observed_at DESC"
                ),
                {"sid": student_id, "cutoff": cutoff},
            )
            misconception_rows = misconception_result.fetchall()

            recent_misconceptions = [
                MisconceptionSnapshot(
                    topic_name=row[0],
                    text=row[1],
                    observed_at=row[2],
                )
                for row in misconception_rows
            ]

            # 4. Read most recent session_id by last_activity DESC
            session_result = await conn.execute(
                sql_text(
                    "SELECT session_id "
                    "FROM session "
                    "WHERE student_id = :sid "
                    "ORDER BY last_activity DESC "
                    "LIMIT 1"
                ),
                {"sid": student_id},
            )
            session_row = session_result.fetchone()
            most_recent_session_id = session_row[0] if session_row else None

            # Assemble StudentState
            return StudentState(
                empty=False,
                stale=False,  # Retired graph-era flag (ASSUM-005)
                student_id=student_id,
                year_group=year_group,
                target_grade=target_grade,
                subjects=[],  # No source in Postgres schema (ASSUM-002)
                current_texts=[],  # No source in Postgres schema (ASSUM-002)
                topic_confidences=topic_confidences,
                recent_misconceptions=recent_misconceptions,
                most_recent_session_id=most_recent_session_id,
            )

    async def get_gamification_state(self, student_id: str) -> GamificationState:
        """Read-side gamification snapshot (streak / level / XP) from Postgres.

        Derives real streak / level / recent-XP from the student's ``ended``
        sessions via ``study_tutor.gamification`` (a *minimal real* slice of the
        gamification design; near-achievements/quests are Phase-2 FEAT-PO-007).

        Returns ``GamificationState(exists=False)`` for an unknown student.
        DB/connection errors propagate so callers degrade, as ``get_student_state``.
        """
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        async with engine.connect() as conn:
            # Student existence + display name (early return for unknown learner)
            student_result = await conn.execute(
                sql_text("SELECT name FROM student WHERE student_id = :sid"),
                {"sid": student_id},
            )
            student_row = student_result.fetchone()
            if student_row is None:
                return GamificationState(exists=False)

            # Completed sessions only — active/in-flight sessions do not yet
            # bank XP or extend a streak (gamification §4.1).
            session_result = await conn.execute(
                sql_text(
                    "SELECT started_at, last_activity "
                    "FROM session "
                    "WHERE student_id = :sid AND status = 'ended'"
                ),
                {"sid": student_id},
            )
            ended_sessions = [
                (row[0], row[1]) for row in session_result.fetchall()
            ]

        student_name = student_row[0] or student_id
        return build_gamification_state(
            student_name=student_name,
            ended_sessions=ended_sessions,
            today=datetime.now(timezone.utc).date(),
        )

    async def get_topic_confidences(self, student_id: str) -> list[TopicConfidence]:
        """Read per-topic confidence entities from Postgres (TASK-SMP2-01).

        Returns one TopicConfidence domain entity per topic_confidence row for
        the given student, ordered newest last_revised_at first.

        Args:
            student_id: Student identifier to query.

        Returns:
            List of TopicConfidence entities. Empty list if student has no rows
            or is unknown (no student existence pre-check — graceful degradation).

        Raises:
            Database errors propagate (not swallowed) so the caller can degrade.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            # Parameterised SELECT with ORDER BY last_revised_at DESC
            result = await conn.execute(
                sql_text(
                    "SELECT topic_name, percentage, band, last_revised_at "
                    "FROM topic_confidence "
                    "WHERE student_id = :sid "
                    "ORDER BY last_revised_at DESC"
                ),
                {"sid": student_id},
            )

            rows = result.fetchall()

            # Map rows to TopicConfidence domain entities
            confidences = [
                TopicConfidence(
                    student_ref=student_id,
                    topic_ref=row[0],  # topic_name
                    percentage=row[1],  # percentage
                    band=row[2],  # band (verbatim from column, no re-derivation)
                    last_revised_at=row[3],  # last_revised_at (TIMESTAMPTZ, UTC-aware)
                )
                for row in rows
            ]

            return confidences

    async def get_recent_misconceptions(
        self,
        student_id: str,
        *,
        window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    ) -> list[Misconception]:
        """Read recent misconceptions from Postgres (TASK-SMP2-02).

        Returns one Misconception domain entity per misconception row for the
        given student observed within the trailing window_days, ordered newest
        observed_at first.

        The confidence_band_at_observation field is approximated from the
        learner's CURRENT confidence band for that topic via LEFT JOIN with
        topic_confidence, defaulting to "struggling" when no confidence row exists.

        Args:
            student_id: Student identifier to query.
            window_days: Trailing window in days (default 30). Boundary is inclusive.

        Returns:
            List of Misconception entities. Empty list if student has no in-window
            rows or is unknown (no student existence pre-check — graceful degradation).

        Raises:
            Database errors propagate (not swallowed) so the caller can degrade.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Compute cutoff timestamp (inclusive boundary)
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            # Parameterised SELECT with LEFT JOIN for band approximation
            result = await conn.execute(
                sql_text(
                    "SELECT m.topic_name, m.text, m.observed_at, "
                    "COALESCE(tc.band, 'struggling') AS band "
                    "FROM misconception m "
                    "LEFT JOIN topic_confidence tc "
                    "ON tc.student_id = m.student_id AND tc.topic_name = m.topic_name "
                    "WHERE m.student_id = :sid AND m.observed_at >= :cutoff "
                    "ORDER BY m.observed_at DESC"
                ),
                {"sid": student_id, "cutoff": cutoff},
            )

            rows = result.fetchall()

            # Map rows to Misconception domain entities
            misconceptions = [
                Misconception(
                    text=row[1],  # text
                    topic_ref=row[0],  # topic_name
                    observed_at=row[2],  # observed_at (TIMESTAMPTZ, UTC-aware)
                    confidence_band_at_observation=row[
                        3
                    ],  # band (from JOIN or default)
                )
                for row in rows
            ]

            return misconceptions

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
        """F3 — atomic, idempotent session-end write (TASK-SMP-06).

        Persists per-session XP, batch of per-topic confidence updates, and
        observed misconceptions as ONE synchronous transaction. Idempotent on
        session_id: replay/concurrent delivery records exactly once.

        Args:
            student_id: Student identifier (FK to student table).
            session_id: Session identifier (PK, upsert key).
            topic: Optional topic for the session.
            aos_scaffolded: List of AO identifiers scaffolded in session.
            xp_awarded: XP to award (SET, not incremented).
            confidence_updates: Batch of per-topic confidence updates.
            misconceptions: Batch of observed misconceptions.

        Raises:
            ValueError: If any confidence percentage is out of range or misconception validation fails.
            IntegrityError: If student_id has no matching student row (FK violation).
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Single transaction for entire write
        async with engine.begin() as conn:
            # Compute timestamps app-side for deterministic/testable UTC
            now_utc = datetime.now(timezone.utc)

            # Build session table metadata
            metadata = MetaData()
            session_table = Table(
                "session",
                metadata,
                Column("session_id", String, primary_key=True),
                Column("student_id", String),
                Column("subject", String),
                Column("topic", String),
                Column("status", String),
                Column("started_at", DateTime(timezone=True)),
                Column("last_activity", DateTime(timezone=True)),
                Column("turn_count", Integer),
                Column("xp_awarded", Integer),
                Column("aos_scaffolded", postgresql.JSONB),
                Column("summary", String),
            )

            # Session upsert with idempotency gate: only write children when
            # transitioning to 'ended' (first delivery wins, replays are no-ops)
            stmt = postgresql.insert(session_table).values(
                session_id=session_id,
                student_id=student_id,
                subject="",  # Required field, empty for now (cross-device contract)
                topic=topic,
                status="ended",
                started_at=now_utc,
                last_activity=now_utc,
                turn_count=0,
                xp_awarded=xp_awarded,
                aos_scaffolded=aos_scaffolded,
                summary=None,
            )

            # ON CONFLICT: update only if not already ended (idempotency gate)
            # RETURNING session_id tells us if this call performed the transition
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["session_id"],
                set_={
                    "status": "ended",
                    "topic": stmt.excluded.topic,
                    "xp_awarded": stmt.excluded.xp_awarded,
                    "aos_scaffolded": stmt.excluded.aos_scaffolded,
                    "last_activity": stmt.excluded.last_activity,
                },
                # Only update if not already ended (idempotency gate)
                where=session_table.c.status != "ended",
            ).returning(session_table.c.session_id)

            result = await conn.execute(upsert_stmt)
            transition_happened = result.fetchone() is not None

            # Only write children if this call performed the active→ended transition
            # (or inserted a new row). Replays see status='ended' already and skip.
            if transition_happened:
                # Upsert confidence updates
                for update in confidence_updates:
                    await _upsert_confidence(conn, student_id, update)

                # Insert misconceptions
                for misc in misconceptions:
                    await _insert_misconception(
                        conn, student_id, misc.topic_ref, misc.text
                    )

    async def record_misconception(
        self, *, student_id: str, topic_name: str, text: str
    ) -> None:
        """F1 — synchronous misconception INSERT with text hygiene (TASK-SMP-05).

        Records a single Coach-observed misconception, writing one row to the
        misconception table with observed_at = now(UTC). Text is sanitised
        (control-char strip + 500-char cap) before persistence, but prompt-
        injection rejection is NOT applied (ASSUM-005: opaque storage).

        Args:
            student_id: Student identifier (FK to student table).
            topic_name: Topic the misconception relates to.
            text: Raw misconception text from observation.

        Raises:
            ValueError: If topic_name or text (after sanitisation) is blank.
            IntegrityError: If student_id has no matching student row (FK violation).
        """
        # Execute in a transaction (awaited inline, no fire-and-forget)
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        async with engine.begin() as conn:
            await _insert_misconception(conn, student_id, topic_name, text)

    async def apply_confidence_update(
        self, *, student_id: str, update: ConfidenceUpdate
    ) -> None:
        """Upsert topic_confidence with derived band (F2 write path).

        Persists the resolved confidence percentage, derives the band at write
        time via confidence_band_for, and stamps last_revised_at in UTC.

        Args:
            student_id: The student identifier (FK to student table).
            update: ConfidenceUpdate with topic_name and percentage [0, 100].

        Raises:
            ValueError: If percentage is outside [0, 100].
            IntegrityError: If student_id has no matching student row (FK violation).
        """
        # Execute in a transaction
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        async with engine.begin() as conn:
            await _upsert_confidence(conn, student_id, update)

    # -- Session persistence -----------------------------------------------

    async def create_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None = None,
        resume_if_active: bool = False,
    ) -> tuple[SessionRecord, bool]:
        """Create a session, or resume the active one.

        Returns (record, created) - created=True for new, False for resumed.
        ONE transaction (ASSUM-003): SELECT for resume check + INSERT if needed.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Compute now for timestamps (deterministic, tz-aware)
        now = datetime.now(timezone.utc)

        # Use transaction for atomicity (resume check + conditional insert)
        async with engine.begin() as conn:
            # If resume requested, check for existing active session
            if resume_if_active:
                result = await conn.execute(
                    sql_text(
                        "SELECT session_id, student_id, subject, topic, status, "
                        "started_at, last_activity, turn_count, aos_scaffolded, summary "
                        "FROM session "
                        "WHERE student_id = :sid AND subject = :subj AND status = 'active' "
                        "ORDER BY last_activity DESC LIMIT 1"
                    ),
                    {"sid": student_id, "subj": subject},
                )
                row = result.fetchone()

                if row is not None:
                    # Resume existing session
                    return (
                        SessionRecord(
                            session_id=row[0],
                            student_id=row[1],
                            subject=row[2],
                            topic=row[3],
                            status=row[4],
                            started_at=row[5],
                            last_activity=row[6],
                            turn_count=row[7],
                            aos_scaffolded=row[8] if row[8] else [],
                            summary=row[9],
                        ),
                        False,  # Not created, resumed
                    )

            # Create new session
            session_id = str(uuid4())
            await conn.execute(
                sql_text(
                    "INSERT INTO session "
                    "(session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded, summary) "
                    "VALUES "
                    "(:session_id, :student_id, :subject, :topic, :status, "
                    ":started_at, :last_activity, :turn_count, :xp_awarded, :aos_scaffolded, :summary)"
                ),
                {
                    "session_id": session_id,
                    "student_id": student_id,
                    "subject": subject,
                    "topic": topic,
                    "status": "active",
                    "started_at": now,
                    "last_activity": now,
                    "turn_count": 0,
                    "xp_awarded": 0,
                    "aos_scaffolded": "[]",
                    "summary": None,
                },
            )

            return (
                SessionRecord(
                    session_id=session_id,
                    student_id=student_id,
                    subject=subject,
                    topic=topic,
                    status="active",
                    started_at=now,
                    last_activity=now,
                    turn_count=0,
                    aos_scaffolded=[],
                    summary=None,
                ),
                True,  # Created
            )

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch a session, or None if unknown.

        Returns SessionRecord with all fields mapped from DB row.
        Note: xp_awarded exists in DB but NOT on SessionRecord.
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            result = await conn.execute(
                sql_text(
                    "SELECT session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, aos_scaffolded, summary "
                    "FROM session WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
            row = result.fetchone()

            if row is None:
                return None

            return SessionRecord(
                session_id=row[0],
                student_id=row[1],
                subject=row[2],
                topic=row[3],
                status=row[4],
                started_at=row[5],
                last_activity=row[6],
                turn_count=row[7],
                aos_scaffolded=row[8] if row[8] else [],
                summary=row[9],
            )

    async def list_sessions(
        self,
        student_id: str,
        *,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """List sessions for a student, newest last_activity first.

        Returns SessionRecord list ordered by last_activity DESC, capped at limit.
        Optional status filter narrows to active or ended when supplied.
        Returns [] for a student with no sessions (no existence pre-check needed).
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            # Build query with optional status filter
            if status is not None:
                query = sql_text(
                    "SELECT session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, aos_scaffolded, summary "
                    "FROM session "
                    "WHERE student_id = :sid AND status = :status "
                    "ORDER BY last_activity DESC LIMIT :limit"
                )
                params = {"sid": student_id, "status": status, "limit": limit}
            else:
                query = sql_text(
                    "SELECT session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, aos_scaffolded, summary "
                    "FROM session "
                    "WHERE student_id = :sid "
                    "ORDER BY last_activity DESC LIMIT :limit"
                )
                params = {"sid": student_id, "limit": limit}

            result = await conn.execute(query, params)
            rows = result.fetchall()

            # Map rows to SessionRecord entities
            sessions = [
                SessionRecord(
                    session_id=row[0],
                    student_id=row[1],
                    subject=row[2],
                    topic=row[3],
                    status=row[4],
                    started_at=row[5],
                    last_activity=row[6],
                    turn_count=row[7],
                    aos_scaffolded=row[8] if row[8] else [],
                    summary=row[9],
                )
                for row in rows
            ]

            return sessions

    async def append_turn(
        self,
        *,
        session_id: str,
        role: TurnRole,
        content: str,
        ao_scaffolded: str | None = None,
    ) -> SessionTurn:
        """Append one turn, bumping turn_count + last_activity atomically.

        Args:
            session_id: Target session UUID
            role: 'learner' or 'tutor'
            content: Turn content (message text)
            ao_scaffolded: Optional AO scaffold type applied

        Returns:
            SessionTurn with the inserted turn (turn_index is 0-based, monotonic)

        Raises:
            IntegrityError: If session_id is unknown (FK constraint violation)
            Database errors propagate
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Compute timestamp (tz-aware UTC)
        now = datetime.now(timezone.utc)

        # ONE transaction: read turn_count (FOR UPDATE), insert turn, update session
        async with engine.begin() as conn:
            # Read current turn_count (this becomes the new turn's index)
            # FOR UPDATE locks the row to prevent race conditions
            result = await conn.execute(
                sql_text(
                    "SELECT turn_count FROM session WHERE session_id = :sid FOR UPDATE"
                ),
                {"sid": session_id},
            )
            row = result.fetchone()

            if row is None:
                # Unknown session - let the FK constraint reject the insert
                # (but we've detected it early, so provide a clear message)
                # The FK will raise IntegrityError if we proceed
                pass

            turn_index = row[0] if row else 0

            # Insert turn
            await conn.execute(
                sql_text(
                    "INSERT INTO session_turn "
                    "(session_id, turn_index, role, content, ts, ao_scaffolded) "
                    "VALUES (:session_id, :turn_index, :role, :content, :ts, :ao_scaffolded)"
                ),
                {
                    "session_id": session_id,
                    "turn_index": turn_index,
                    "role": role,
                    "content": content,
                    "ts": now,
                    "ao_scaffolded": ao_scaffolded,
                },
            )

            # Update session: bump turn_count and last_activity
            await conn.execute(
                sql_text(
                    "UPDATE session "
                    "SET turn_count = turn_count + 1, last_activity = :now "
                    "WHERE session_id = :sid"
                ),
                {"now": now, "sid": session_id},
            )

        # Return the SessionTurn
        return SessionTurn(
            session_id=session_id,
            turn_index=turn_index,
            role=role,
            content=content,
            ts=now,
            ao_scaffolded=ao_scaffolded,
        )

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        """Get ordered transcript for a session.

        Returns SessionTurn list ordered by turn_index ascending.
        Returns [] when the session has no turns or is unknown (no existence pre-check).
        """
        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            result = await conn.execute(
                sql_text(
                    "SELECT session_id, turn_index, role, content, ts, ao_scaffolded "
                    "FROM session_turn "
                    "WHERE session_id = :sid "
                    "ORDER BY turn_index"
                ),
                {"sid": session_id},
            )
            rows = result.fetchall()

            # Map rows to SessionTurn entities
            turns = [
                SessionTurn(
                    session_id=row[0],
                    turn_index=row[1],
                    role=row[2],
                    content=row[3],
                    ts=row[4],
                    ao_scaffolded=row[5],  # Pass through as str | None
                )
                for row in rows
            ]

            return turns

    async def end_session(self, session_id: str) -> SessionRecord:
        """Transition session status to 'ended' and stamp last_activity.

        Args:
            session_id: Target session UUID

        Returns:
            SessionRecord with updated status='ended' and fresh last_activity

        Raises:
            SessionNotFoundError: If session_id is unknown
            Database errors propagate
        """
        # Import error here to avoid circular import issues
        from study_tutor.session.errors import SessionNotFoundError

        # Get engine/pool
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        # Compute timestamp (tz-aware UTC)
        now = datetime.now(timezone.utc)

        # Update status and last_activity, returning the updated row
        async with engine.begin() as conn:
            result = await conn.execute(
                sql_text(
                    "UPDATE session "
                    "SET status = 'ended', last_activity = :now "
                    "WHERE session_id = :sid "
                    "RETURNING session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, aos_scaffolded, summary"
                ),
                {"now": now, "sid": session_id},
            )
            row = result.fetchone()

            if row is None:
                # Session not found - raise typed error
                raise SessionNotFoundError(f"Session not found: {session_id}")

            # Map row to SessionRecord
            return SessionRecord(
                session_id=row[0],
                student_id=row[1],
                subject=row[2],
                topic=row[3],
                status=row[4],
                started_at=row[5],
                last_activity=row[6],
                turn_count=row[7],
                aos_scaffolded=row[8] if row[8] else [],
                summary=row[9],
            )


__all__ = ["PostgresStudentStore"]
