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

import json
import logging
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

from study_tutor.gamification import (
    EndedSessionFact,
    HeldAchievementFact,
    build_gamification_state,
)
from study_tutor.gamification.economy import (
    MIN_SESSION_SECONDS,
    london_date,
    started_after_evening,
    started_before_morning,
)
from study_tutor.gamification.engine import (
    GamificationDecision,
    PriorFacts,
    SessionFacts,
    SettlementResult,
    decide,
)
from study_tutor.gamification.catalog_w2 import POETRY_PIONEER_SLUG
from study_tutor.gamification.signals import (
    DEVELOPING_FLOOR,
    W2Signals,
    any_six_ao_session,
    compute_mastered_texts,
    eras_covered,
    genre_week_achieved,
    max_confidence_gain_over_window,
)
from study_tutor.gamification.texts import UNSEEN_POETRY_SLUG
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

logger = logging.getLogger(__name__)

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
        Column("subject", String),
        Column("topic_name", String),
        Column("percentage", Integer),
        Column("band", String),
        Column("last_revised_at", DateTime(timezone=True)),
    )

    # Build INSERT ... ON CONFLICT DO UPDATE. The conflict key is the
    # widened (student_id, subject, topic_name) primary key (rev
    # d5a9c2e7f814, ADR-ARCH-032) — the same topic name carries an
    # independent confidence per subject.
    stmt = postgresql.insert(topic_confidence).values(
        student_id=student_id,
        subject=update.subject,
        topic_name=update.topic_name,
        percentage=update.percentage,
        band=band,
        last_revised_at=now_utc,
    )

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["student_id", "subject", "topic_name"],
        set_={
            "percentage": stmt.excluded.percentage,
            "band": stmt.excluded.band,
            "last_revised_at": stmt.excluded.last_revised_at,
        },
    )

    await conn.execute(upsert_stmt)


async def _insert_misconception(
    conn: AsyncConnection,
    student_id: str,
    topic_name: str,
    text: str,
    subject: str = "english",
) -> None:
    """Insert misconception at connection level (reused by record_session_completion).

    Applies text hygiene (control-char strip + 500-char cap) before insert.
    Enlists in the caller's open transaction.

    Args:
        conn: Open AsyncConnection (already in a transaction).
        student_id: Student identifier (FK to student table).
        topic_name: Topic the misconception relates to.
        text: Raw misconception text from observation.
        subject: Mastery dimension the observation lands under
            (ADR-ARCH-032); callers on the settlement/completion paths
            pass the session row's subject.

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
        "INSERT INTO misconception "
        "(student_id, subject, topic_name, text, observed_at) "
        "VALUES (:student_id, :subject, :topic_name, :text, :observed_at)"
    )

    await conn.execute(
        insert_stmt,
        {
            "student_id": student_id,
            "subject": subject,
            "topic_name": topic_name,
            "text": sanitised_text,
            "observed_at": observed_at,
        },
    )


async def _read_prior_facts(
    conn: AsyncConnection, student_id: str, exclude_session_id: str
) -> PriorFacts:
    """Assemble :class:`PriorFacts` for settlement, EXCLUDING the session under
    settlement (spec §4.2 / ADR-ARCH-030 D6).

    Excluding ``exclude_session_id`` from every aggregate is what makes the
    winner's ``decide()`` inputs and a later replay's inputs identical: the
    winner reads prior-without-self *before* banking self, the replay reads
    prior-without-self *after* self is banked, and both see the same "other
    rows" state. All day/window arithmetic is Europe/London (design §13.1 D6).
    """
    params = {"sid": student_id, "ex": exclude_session_id}

    total_row = (
        await conn.execute(
            sql_text(
                "SELECT "
                "COALESCE((SELECT SUM(xp_awarded) FROM session "
                "  WHERE student_id = :sid AND session_id <> :ex), 0) "
                "+ COALESCE((SELECT SUM(xp_awarded) FROM achievement "
                "  WHERE student_id = :sid "
                "  AND session_id IS DISTINCT FROM :ex), 0)"
            ),
            params,
        )
    ).fetchone()
    total_xp = int(total_row[0] or 0)

    held_rows = (
        await conn.execute(
            sql_text(
                "SELECT achievement_id FROM achievement "
                "WHERE student_id = :sid AND session_id IS DISTINCT FROM :ex"
            ),
            params,
        )
    ).fetchall()
    held = frozenset(row[0] for row in held_rows)

    # Every OTHER ended session with its turn min/max — qualifying (≥120 s)
    # sessions contribute a streak credit day and the start-window counts.
    sess_rows = (
        await conn.execute(
            sql_text(
                "SELECT s.started_at, t.min_ts, t.max_ts, t.cnt "
                "FROM session s "
                "LEFT JOIN ("
                "  SELECT session_id, min(ts) AS min_ts, max(ts) AS max_ts, "
                "         count(*) AS cnt "
                "  FROM session_turn GROUP BY session_id"
                ") t ON t.session_id = s.session_id "
                "WHERE s.student_id = :sid AND s.status = 'ended' "
                "AND s.session_id <> :ex"
            ),
            params,
        )
    ).fetchall()

    credit_days: set = set()
    morning = 0
    evening = 0
    qualifying = 0
    for started_at, min_ts, max_ts, cnt in sess_rows:
        if not cnt or min_ts is None or max_ts is None:
            continue  # zero-turn / unstamped → 0 engagement → not qualifying
        engagement = (max_ts - min_ts).total_seconds()
        if engagement < MIN_SESSION_SECONDS:
            continue
        qualifying += 1
        credit_days.add(london_date(max_ts))
        if started_before_morning(started_at):
            morning += 1
        if started_after_evening(started_at):
            evening += 1

    return PriorFacts(
        total_xp=total_xp,
        streak_credit_days=frozenset(credit_days),
        held_achievement_ids=held,
        morning_qualifying_count=morning,
        evening_qualifying_count=evening,
        qualifying_session_count=qualifying,
    )


async def _engagement_facts(
    conn: AsyncConnection, session_id: str
) -> tuple[float, datetime | None, bool]:
    """Return ``(engagement_seconds, last_turn_at, had_turns)`` from the session's
    turns (spec §4.2 step 3). Zero rows → ``(0.0, None, False)``."""
    row = (
        await conn.execute(
            sql_text(
                "SELECT min(ts), max(ts), count(*) "
                "FROM session_turn WHERE session_id = :sid"
            ),
            {"sid": session_id},
        )
    ).fetchone()
    min_ts, max_ts, cnt = row
    if not cnt or min_ts is None or max_ts is None:
        return 0.0, None, False
    return (max_ts - min_ts).total_seconds(), max_ts, True


async def _read_w2_facts(conn: AsyncConnection, student_id: str) -> W2Signals:
    """Assemble the W2 capture-wave signals from the student's persisted state
    (spec §2.3 note / scope §4).

    Called *after* this session's confidence + quote + AO capture is persisted, so
    the winner's snapshot and a later replay's snapshot (both reading the same
    committed rows, including the settling session) reconstruct identical signals.
    The heavy lifting — R1 text-mastery mean, R6 rolling-window gains, R7 genre
    week, R9 six-AO session — lives in the pure ``gamification.signals`` helpers.
    """
    # -- Studied topics: latest confidence + the text each was studied under ----
    # The text association comes from the confidence-history audit trail
    # (session_id → session.text_name); the authoritative latest % is the current
    # topic_confidence row.
    topic_rows = (
        await conn.execute(
            sql_text(
                "SELECT tc.topic_name, tc.percentage, ("
                "  SELECT s.text_name FROM topic_confidence_history h "
                "  JOIN session s ON h.session_id = s.session_id "
                "  WHERE h.student_id = tc.student_id "
                "    AND h.topic_name = tc.topic_name "
                "    AND s.text_name IS NOT NULL "
                "  ORDER BY h.recorded_at DESC LIMIT 1"
                ") AS text_slug "
                "FROM topic_confidence tc WHERE tc.student_id = :sid"
            ),
            {"sid": student_id},
        )
    ).fetchall()
    studied_topic_count = len(topic_rows)
    min_topic_confidence = (
        min(int(r[1]) for r in topic_rows) if topic_rows else 0
    )
    topic_text_confidences = [
        (r[0], r[2], int(r[1])) for r in topic_rows if r[2]
    ]
    mastered_texts = compute_mastered_texts(topic_text_confidences)
    unseen_confidence = max(
        (int(r[1]) for r in topic_rows if r[2] == UNSEEN_POETRY_SLUG),
        default=0,
    )

    # -- Ended sessions: distinct texts, genre week, eras, Poetry-Pioneer count -
    sess_rows = (
        await conn.execute(
            sql_text(
                "SELECT text_name, last_activity FROM session "
                "WHERE student_id = :sid AND status = 'ended'"
            ),
            {"sid": student_id},
        )
    ).fetchall()
    distinct_texts = {r[0] for r in sess_rows if r[0]}
    distinct_text_count = len(distinct_texts)
    poetry_pioneer_sessions = sum(
        1 for r in sess_rows if r[0] == POETRY_PIONEER_SLUG
    )
    genre_week = genre_week_achieved(
        (london_date(r[1]), r[0]) for r in sess_rows if r[0]
    )
    eras = eras_covered(distinct_texts)

    # -- Per-session observed AO sets (Six-AO Sampler, R9) ----------------------
    ao_rows = (
        await conn.execute(
            sql_text(
                "SELECT st.session_id, "
                "       array_agg(DISTINCT st.ao_scaffolded) AS aos "
                "FROM session_turn st JOIN session s "
                "  ON st.session_id = s.session_id "
                "WHERE s.student_id = :sid AND st.ao_scaffolded IS NOT NULL "
                "GROUP BY st.session_id"
            ),
            {"sid": student_id},
        )
    ).fetchall()
    six_ao = any_six_ao_session(list(r[1] or ()) for r in ao_rows)

    # -- Cumulative embedded quotes (Quote Champion/Master, R8) -----------------
    quotes_total = (
        await conn.execute(
            sql_text(
                "SELECT COALESCE(SUM(quotes_embedded), 0) FROM session "
                "WHERE student_id = :sid AND status = 'ended'"
            ),
            {"sid": student_id},
        )
    ).scalar()

    # -- Rolling 7-day confidence gains (Climbing / Breakthrough, R6) -----------
    history_rows = (
        await conn.execute(
            sql_text(
                "SELECT topic_name, recorded_at, percentage "
                "FROM topic_confidence_history WHERE student_id = :sid"
            ),
            {"sid": student_id},
        )
    ).fetchall()
    max_gain = max_confidence_gain_over_window(
        (r[0], london_date(r[1]), int(r[2])) for r in history_rows
    )

    return W2Signals(
        mastered_texts=mastered_texts,
        poetry_pioneer_sessions=poetry_pioneer_sessions,
        unseen_confidence=unseen_confidence,
        distinct_text_count=distinct_text_count,
        genre_week_achieved=genre_week,
        eras_covered=eras,
        six_ao_session=six_ao,
        max_confidence_gain_7d=max_gain,
        total_quotes_embedded=int(quotes_total or 0),
        studied_topic_count=studied_topic_count,
        min_topic_confidence=min_topic_confidence,
    )


async def _bank_settlement(
    conn: AsyncConnection,
    *,
    student_id: str,
    session_id: str,
    now: datetime,
    session_facts: SessionFacts,
    confidence_updates: list[ConfidenceUpdate],
    misconceptions: list[Misconception],
    subject: str = "english",
) -> GamificationDecision:
    """Run the engine and bank its result inside the caller's savepoint.

    Writes ``session.xp_awarded`` + ``settled_at`` (both stamped here so a fault
    that rolls back this savepoint leaves ``settled_at`` NULL for the sweep,
    ADR-ARCH-030 D4), inserts achievement rows (``ON CONFLICT DO NOTHING``,
    carrying ``session_id`` for replay), appends ``topic_confidence_history``
    rows, and runs the confidence / misconception helpers.

    Ordering (S-E4): the confidence upserts + history inserts happen FIRST so the
    W2 signal read (:func:`_read_w2_facts`) sees this session's confidence, giving
    the winner and a later replay the same W2 snapshot. Both stay inside the
    savepoint, so a fault still rolls the whole settlement back.
    """
    # ADR-ARCH-032: the session row's subject is authoritative for every
    # mastery write banked here — stamp it over whatever the caller set.
    confidence_updates = [
        update.model_copy(update={"subject": subject})
        for update in confidence_updates
    ]

    for update in confidence_updates:
        await _upsert_confidence(conn, student_id, update)
        await conn.execute(
            sql_text(
                "INSERT INTO topic_confidence_history "
                "(student_id, subject, topic_name, percentage, session_id, "
                "recorded_at, source) "
                "VALUES (:sid, :subject, :topic, :pct, :session_id, :now, "
                "'session')"
            ),
            {
                "sid": student_id,
                "subject": update.subject,
                "topic": update.topic_name,
                "pct": update.percentage,
                "session_id": session_id,
                "now": now,
            },
        )

    w2 = await _read_w2_facts(conn, student_id)
    prior = await _read_prior_facts(conn, student_id, session_id)
    decision = decide(prior, session_facts, now, w2=w2)

    await conn.execute(
        sql_text(
            "UPDATE session SET xp_awarded = :xp, settled_at = :now "
            "WHERE session_id = :sid"
        ),
        {"xp": decision.xp_awarded, "now": now, "sid": session_id},
    )

    for award in decision.unlocked:
        await conn.execute(
            sql_text(
                "INSERT INTO achievement "
                "(student_id, achievement_id, unlocked_at, xp_awarded, session_id) "
                "VALUES (:sid, :aid, :now, :xp, :session_id) "
                "ON CONFLICT (student_id, achievement_id) DO NOTHING"
            ),
            {
                "sid": student_id,
                "aid": award.id,
                "now": now,
                "xp": award.xp,
                "session_id": session_id,
            },
        )

    for misc in misconceptions:
        await _insert_misconception(
            conn, student_id, misc.topic_ref, misc.text, subject
        )

    return decision


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

    async def delete_sessions_for_student(
        self, student_id: str
    ) -> dict[str, int]:
        """Delete ONE student's sessions + turns (scoped dev reset, 2026-08-04).

        The suite-isolation fix: ``POST /__dev__/reset`` now derives the
        caller from the bearer and deletes that student's rows only —
        the store-wide :meth:`truncate_sessions` wiped every student's
        transcripts when the live suite reset as the real primary
        student (known-issues, 2026-08-03). Learner-state tables are
        untouched, same as the store-wide variant.

        Returns:
            Dict with deleted counts: {"sessions": N, "turns": M}
        """
        if self._pool is not None:
            engine = self._pool
        elif self._engine is not None:
            engine = self._engine
        else:  # pragma: no cover
            raise RuntimeError("No engine or pool configured")

        async with engine.begin() as conn:
            turn_count = (
                await conn.execute(
                    sql_text(
                        "SELECT COUNT(*) FROM session_turn t "
                        "JOIN session s ON s.session_id = t.session_id "
                        "WHERE s.student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).scalar()
            session_count = (
                await conn.execute(
                    sql_text(
                        "SELECT COUNT(*) FROM session WHERE student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).scalar()
            # session_turn rows cascade with their sessions (FK ON DELETE
            # CASCADE, schema_reference.sql).
            await conn.execute(
                sql_text("DELETE FROM session WHERE student_id = :sid"),
                {"sid": student_id},
            )

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
                    "SELECT topic_name, percentage, band, last_revised_at, "
                    "subject "
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
                    subject=row[4],
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
        """Read-side gamification snapshot from **banked** settlement facts (spec §5).

        Reads the XP the Phase-E engine already banked — ``total_xp =
        SUM(session.xp_awarded) + SUM(achievement.xp_awarded)`` (ADR-ARCH-030 D2)
        — plus the student's ``achievement`` rows, and folds them via
        ``study_tutor.gamification`` into streak / longest-streak / level / recent
        XP and the recent/near achievement views (contract §2.2.1). No XP is
        re-derived from durations here; the read only sums what settlement wrote,
        so this snapshot and the ``end_session`` block can never disagree.

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

            # Completed sessions only — active/in-flight sessions have not settled
            # (no banked XP, no streak credit) (gamification §4.1).
            session_result = await conn.execute(
                sql_text(
                    "SELECT started_at, last_activity, xp_awarded "
                    "FROM session "
                    "WHERE student_id = :sid AND status = 'ended'"
                ),
                {"sid": student_id},
            )
            ended_sessions = [
                EndedSessionFact(
                    started_at=row[0],
                    last_activity=row[1],
                    xp_awarded=int(row[2] or 0),
                )
                for row in session_result.fetchall()
            ]

            achievement_result = await conn.execute(
                sql_text(
                    "SELECT achievement_id, unlocked_at, xp_awarded "
                    "FROM achievement WHERE student_id = :sid"
                ),
                {"sid": student_id},
            )
            achievements = [
                HeldAchievementFact(
                    id=row[0],
                    unlocked_at=row[1],
                    xp_awarded=int(row[2] or 0),
                )
                for row in achievement_result.fetchall()
            ]

        student_name = student_row[0] or student_id
        return build_gamification_state(
            student_name=student_name,
            ended_sessions=ended_sessions,
            achievements=achievements,
            today=london_date(datetime.now(timezone.utc)),
        )

    async def get_topic_confidences(
        self, student_id: str, subject: str | None = None
    ) -> list[TopicConfidence]:
        """Read per-topic confidence entities from Postgres (TASK-SMP2-01).

        Returns one TopicConfidence domain entity per topic_confidence row for
        the given student, ordered newest last_revised_at first.

        Args:
            student_id: Student identifier to query.
            subject: When given, only that subject's rows (ADR-ARCH-032 /
                study-room §14 — the mastery surfaces filter by subject).
                ``None`` returns every subject's rows (whole-student
                consumers, e.g. the planner, unchanged).

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

        subject_clause = "AND subject = :subject " if subject is not None else ""
        params: dict[str, Any] = {"sid": student_id}
        if subject is not None:
            params["subject"] = subject

        # Read-only connection (no transaction needed)
        async with engine.connect() as conn:
            # Parameterised SELECT with ORDER BY last_revised_at DESC
            result = await conn.execute(
                sql_text(
                    "SELECT topic_name, percentage, band, last_revised_at "
                    "FROM topic_confidence "
                    "WHERE student_id = :sid "
                    + subject_clause
                    + "ORDER BY last_revised_at DESC"
                ),
                params,
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
                # ADR-ARCH-032 D4: a session row minted by this legacy
                # end-first path gets the shared default (this previously
                # wrote '' — the empty-subject writer the plan's
                # contradiction list named).
                subject="english",
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
            # RETURNING session_id tells us if this call performed the
            # transition; RETURNING subject gives the row's REAL subject (an
            # existing row keeps its own — set_ never touches subject) so the
            # mastery child-writes below land under it (ADR-ARCH-032).
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
            ).returning(session_table.c.session_id, session_table.c.subject)

            result = await conn.execute(upsert_stmt)
            returned = result.fetchone()
            transition_happened = returned is not None
            row_subject = returned[1] if returned else "english"
            # Defensive: rows persisted before the service-boundary
            # normalisation may still carry '' — mastery writes never do.
            if not row_subject:
                row_subject = "english"

            # Only write children if this call performed the active→ended transition
            # (or inserted a new row). Replays see status='ended' already and skip.
            if transition_happened:
                # Upsert confidence updates under the session's subject
                for update in confidence_updates:
                    await _upsert_confidence(
                        conn,
                        student_id,
                        update.model_copy(update={"subject": row_subject}),
                    )

                # Insert misconceptions
                for misc in misconceptions:
                    await _insert_misconception(
                        conn, student_id, misc.topic_ref, misc.text, row_subject
                    )

    async def finalize_session(
        self,
        *,
        student_id: str,
        session_id: str,
        now: datetime,
        confidence_updates: list[ConfidenceUpdate],
        misconceptions: list[Misconception],
        aos_scaffolded: list[str],
        topic: str | None,
    ) -> SettlementResult:
        """Settle a session in ONE transaction (spec §4.2 / ADR-ARCH-030 D3).

        The status UPDATE (``WHERE status='active'``) is the sole gate: the
        caller that flips ``active → ended`` settles inside a savepoint; a
        non-matching UPDATE means already-ended → the replay path returns the
        identical decision from prior-facts-excluding-self (D6). An unknown
        session raises ``SessionNotFoundError``. A settlement fault rolls back
        the savepoint, commits the end, and leaves ``settled_at`` NULL (D4).
        """
        from study_tutor.session.errors import SessionNotFoundError

        engine = self._require_engine()

        async with engine.begin() as conn:
            gate = (
                await conn.execute(
                    sql_text(
                        "UPDATE session SET status = 'ended', last_activity = :now "
                        "WHERE session_id = :sid AND status = 'active' "
                        "RETURNING started_at, subject, topic, aos_scaffolded, "
                        "text_name"
                    ),
                    {"now": now, "sid": session_id},
                )
            ).fetchone()

            if gate is None:
                # Not active: either already-ended (replay) or unknown (error).
                existing = (
                    await conn.execute(
                        sql_text(
                            "SELECT started_at, subject, topic, aos_scaffolded, "
                            "text_name "
                            "FROM session WHERE session_id = :sid"
                        ),
                        {"sid": session_id},
                    )
                ).fetchone()
                if existing is None:
                    raise SessionNotFoundError(f"Session not found: {session_id}")
                return await self._replay_settlement(
                    conn, student_id, session_id, existing, now
                )

            started_at, subject, sess_topic, aos_col, _sess_text_name = gate
            # Defensive (ADR-ARCH-032): rows persisted before the
            # service-boundary normalisation may carry '' — mastery
            # writes and the settlement result never do.
            subject = subject or "english"
            engagement, last_turn_at, had_turns = await _engagement_facts(
                conn, session_id
            )
            session_facts = SessionFacts(
                engagement_seconds=engagement,
                started_at=started_at,
                last_turn_at=last_turn_at,
            )

            decision: GamificationDecision | None
            settled = True
            try:
                async with conn.begin_nested():
                    decision = await _bank_settlement(
                        conn,
                        student_id=student_id,
                        session_id=session_id,
                        now=now,
                        session_facts=session_facts,
                        confidence_updates=confidence_updates,
                        misconceptions=misconceptions,
                        subject=subject,
                    )
            except Exception:  # noqa: BLE001 — settlement is best-effort (D4)
                logger.error(
                    "event=settlement_fault session_id=%s student_id=%s "
                    "— session ended, settled_at left NULL for the sweep",
                    session_id,
                    student_id,
                    exc_info=True,
                )
                decision = None
                settled = False

        aos_touched = tuple(aos_scaffolded or (aos_col or []))
        return SettlementResult(
            decision=decision,
            settled=settled,
            replayed=False,
            session_id=session_id,
            subject=subject,
            topic=topic if topic is not None else sess_topic,
            aos_touched=aos_touched,
            duration_seconds=int(engagement),
            ended_at=now,
            had_turns=had_turns,
        )

    async def _replay_settlement(
        self,
        conn: AsyncConnection,
        student_id: str,
        session_id: str,
        existing_row: Any,
        now: datetime,
    ) -> SettlementResult:
        """Reconstruct the identical decision for an already-ended session (D6).

        Recomputes ``decide()`` from prior-facts-excluding-self plus this
        session's (immutable) engagement facts — deterministically identical to
        what the winner banked, without re-writing any row (exactly-once).
        """
        started_at, subject, sess_topic, aos_col, _sess_text_name = existing_row
        engagement, last_turn_at, had_turns = await _engagement_facts(
            conn, session_id
        )
        session_facts = SessionFacts(
            engagement_seconds=engagement,
            started_at=started_at,
            last_turn_at=last_turn_at,
        )
        prior = await _read_prior_facts(conn, student_id, session_id)
        w2 = await _read_w2_facts(conn, student_id)
        decision = decide(prior, session_facts, now, w2=w2)
        return SettlementResult(
            decision=decision,
            settled=True,
            replayed=True,
            session_id=session_id,
            subject=subject,
            topic=sess_topic,
            aos_touched=tuple(aos_col or []),
            duration_seconds=int(engagement),
            ended_at=now,
            had_turns=had_turns,
        )

    async def sweep_settle_session(
        self, *, session_id: str, now: datetime
    ) -> SettlementResult | None:
        """Settle one ``status='ended' AND settled_at IS NULL`` session (spec §4.3).

        The recovery + historical-backfill path. Claims the row atomically
        (``settled_at`` is stamped only inside the savepoint, so a fault leaves
        it NULL for a retry), runs the SAME ``decide()`` the live path uses, and
        banks XP + achievements. Idempotent: a row that is not ended-and-unsettled
        returns ``None`` (already swept, or still active). Gamification-only — it
        does not synthesise confidence/misconception deltas (none exist at sweep
        time); engagement falls back to ``last_activity − started_at`` for a
        turn-less session.
        """
        engine = self._require_engine()

        async with engine.begin() as conn:
            # Claim via row lock (single attended sweep; no settled_at yet).
            row = (
                await conn.execute(
                    sql_text(
                        "SELECT student_id, started_at, last_activity, subject, "
                        "topic, aos_scaffolded "
                        "FROM session "
                        "WHERE session_id = :sid AND status = 'ended' "
                        "AND settled_at IS NULL FOR UPDATE"
                    ),
                    {"sid": session_id},
                )
            ).fetchone()
            if row is None:
                return None

            student_id, started_at, last_activity, subject, topic, aos_col = row
            engagement, last_turn_at, had_turns = await _engagement_facts(
                conn, session_id
            )
            if not had_turns:
                # Spec §4.3 fallback: derive engagement from the session bounds.
                engagement = max(
                    0.0, (last_activity - started_at).total_seconds()
                )
                last_turn_at = last_activity
            session_facts = SessionFacts(
                engagement_seconds=engagement,
                started_at=started_at,
                last_turn_at=last_turn_at,
            )

            decision: GamificationDecision | None = None
            settled = True
            try:
                async with conn.begin_nested():
                    decision = await _bank_settlement(
                        conn,
                        student_id=student_id,
                        session_id=session_id,
                        now=now,
                        session_facts=session_facts,
                        confidence_updates=[],
                        misconceptions=[],
                    )
            except Exception:  # noqa: BLE001 — leave NULL for the next sweep (D4)
                logger.error(
                    "event=sweep_settlement_fault session_id=%s student_id=%s",
                    session_id,
                    student_id,
                    exc_info=True,
                )
                decision = None
                settled = False

        return SettlementResult(
            decision=decision,
            settled=settled,
            replayed=False,
            session_id=session_id,
            subject=subject,
            topic=topic,
            aos_touched=tuple(aos_col or []),
            duration_seconds=int(engagement),
            ended_at=now,
            had_turns=had_turns,
        )

    async def list_unsettled_ended_sessions(self) -> list[str]:
        """Session ids of every ``status='ended' AND settled_at IS NULL`` row —
        the sweep's work queue (spec §4.3), oldest first."""
        engine = self._require_engine()
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    sql_text(
                        "SELECT session_id FROM session "
                        "WHERE status = 'ended' AND settled_at IS NULL "
                        "ORDER BY last_activity ASC"
                    )
                )
            ).fetchall()
        return [row[0] for row in rows]

    def _require_engine(self) -> Any:
        """Return the injected pool or the built engine, or raise."""
        if self._pool is not None:
            return self._pool
        if self._engine is not None:
            return self._engine
        raise RuntimeError("No engine or pool configured")

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
        aos_scaffolded: list[str] | None = None,
        text_name: str | None = None,
        resume_if_active: bool = False,
    ) -> tuple[SessionRecord, bool]:
        """Create a session, or resume the active one.

        Returns (record, created) - created=True for new, False for resumed.
        ONE transaction (ASSUM-003): SELECT for resume check + INSERT if needed.

        S-R3 §2.1: ``aos_scaffolded`` persists the plan's ``focus_aos`` at
        start-time onto the created row (``None`` → ``[]``). S-E4 / scope §4.2:
        ``text_name`` persists the canonical set-text slug the plan resolved to
        (``None`` when no known set text). Resumes ignore both.
        """
        # Plan facts persisted at start (S-R3 §2.1). Serialised to a JSON
        # array literal for the JSONB column, matching the existing "[]" write.
        planned_aos = list(aos_scaffolded) if aos_scaffolded else []
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
                        "started_at, last_activity, turn_count, aos_scaffolded, summary, "
                        "text_name, quotes_embedded "
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
                            text_name=row[10],
                            quotes_embedded=row[11] if row[11] is not None else 0,
                        ),
                        False,  # Not created, resumed
                    )

            # Create new session
            session_id = str(uuid4())
            await conn.execute(
                sql_text(
                    "INSERT INTO session "
                    "(session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded, "
                    "text_name, quotes_embedded, summary) "
                    "VALUES "
                    "(:session_id, :student_id, :subject, :topic, :status, "
                    ":started_at, :last_activity, :turn_count, :xp_awarded, :aos_scaffolded, "
                    ":text_name, :quotes_embedded, :summary)"
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
                    "aos_scaffolded": json.dumps(planned_aos),
                    "text_name": text_name,
                    "quotes_embedded": 0,
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
                    aos_scaffolded=planned_aos,
                    text_name=text_name,
                    quotes_embedded=0,
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
                    "started_at, last_activity, turn_count, aos_scaffolded, summary, "
                        "text_name, quotes_embedded "
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
                text_name=row[10],
                quotes_embedded=row[11] if row[11] is not None else 0,
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
                    "started_at, last_activity, turn_count, aos_scaffolded, summary, "
                        "text_name, quotes_embedded "
                    "FROM session "
                    "WHERE student_id = :sid AND status = :status "
                    "ORDER BY last_activity DESC LIMIT :limit"
                )
                params = {"sid": student_id, "status": status, "limit": limit}
            else:
                query = sql_text(
                    "SELECT session_id, student_id, subject, topic, status, "
                    "started_at, last_activity, turn_count, aos_scaffolded, summary, "
                        "text_name, quotes_embedded "
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
                    text_name=row[10],
                    quotes_embedded=row[11] if row[11] is not None else 0,
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
        quotes_embedded: int = 0,
    ) -> SessionTurn:
        """Append one turn, bumping turn_count + last_activity atomically.

        Args:
            session_id: Target session UUID
            role: 'learner' or 'tutor'
            content: Turn content (message text)
            ao_scaffolded: Optional Coach-observed AO scaffolded this turn (S-E4,
                R9 — feeds Six-AO Sampler)
            quotes_embedded: Corpus-hit quotations the verifier confirmed this
                turn (S-E4 / scope §4.3, R8); added to session.quotes_embedded

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

            # Update session: bump turn_count + last_activity, and accumulate the
            # per-turn corpus-hit quote count into the session counter (S-E4 §4.3).
            await conn.execute(
                sql_text(
                    "UPDATE session "
                    "SET turn_count = turn_count + 1, last_activity = :now, "
                    "quotes_embedded = quotes_embedded + :quotes "
                    "WHERE session_id = :sid"
                ),
                {"now": now, "sid": session_id, "quotes": max(0, int(quotes_embedded))},
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
                    "started_at, last_activity, turn_count, aos_scaffolded, summary, "
                    "text_name, quotes_embedded"
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
                text_name=row[10],
                quotes_embedded=row[11] if row[11] is not None else 0,
            )


__all__ = ["PostgresStudentStore"]
