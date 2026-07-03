-- Reference DDL for the study-tutor StudentStore (ADR-ARCH-023, gamification §11).
--
-- REFERENCE ONLY. This is the shape FEAT-SMP-001 encodes as the first Alembic
-- migration. Do NOT apply by hand — the runbook's G7 gate runs
-- `alembic upgrade head` (docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md).
--
-- JSONB is used only for genuinely flexible/nested fields (per-AO observations,
-- scaffolded-AO lists). Scalar learner state stays typed. No pgvector.

-- One learner. (Phase 1 ships Lilymay only; multi-student is a partition key.)
-- Cumulative gamification state (level, total_xp, current_streak, longest_streak
-- per gamification/design.md §11.1) is added by the Phase 2 gamification engine,
-- not W1 — W1 persists per-session XP on session.xp_awarded and derives totals by
-- summation if needed (ASSUM-002; avoids a running-total increment that would
-- complicate record_session_completion's idempotency-on-session_id).
CREATE TABLE student (
    student_id    TEXT PRIMARY KEY,               -- stable slug, e.g. 'lilymay'
    name          TEXT NOT NULL,
    year_group    SMALLINT NOT NULL CHECK (year_group BETWEEN 7 AND 13),
    target_grade  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL
);

-- Per-topic confidence. Band is derived from percentage at write time
-- (confidence_band_for, ASSUM-001) and stored for cheap dashboard reads.
CREATE TABLE topic_confidence (
    student_id       TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    topic_name       TEXT NOT NULL,
    percentage       SMALLINT NOT NULL CHECK (percentage BETWEEN 0 AND 100),
    band             TEXT NOT NULL,               -- struggling|developing|secure|mastered
    last_revised_at  TIMESTAMPTZ NOT NULL,        -- EPOCH_NEVER_REVISED sentinel for baselines
    PRIMARY KEY (student_id, topic_name)
);

CREATE TABLE misconception (
    id           BIGSERIAL PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    topic_name   TEXT NOT NULL,
    text         TEXT NOT NULL,
    observed_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX misconception_recent_idx ON misconception (student_id, observed_at DESC);

-- Durable, student-keyed, resumable sessions (cross-device contract §6).
CREATE TABLE session (
    session_id      TEXT PRIMARY KEY,             -- uuid
    student_id      TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    subject         TEXT NOT NULL,
    topic           TEXT,
    status          TEXT NOT NULL DEFAULT 'active',   -- active|ended
    started_at      TIMESTAMPTZ NOT NULL,
    last_activity   TIMESTAMPTZ NOT NULL,
    turn_count      INTEGER NOT NULL DEFAULT 0 CHECK (turn_count >= 0),
    xp_awarded      INTEGER NOT NULL DEFAULT 0 CHECK (xp_awarded >= 0),  -- per-session XP (gamification §11.1); record_session_completion persists it, idempotent on session_id
    aos_scaffolded  JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary         TEXT
);
-- The "resume where you left off" query: active sessions for a student, newest first.
CREATE INDEX session_resume_idx ON session (student_id, status, last_activity DESC);

-- Per-turn durable append (lossless mid-session device switch, §4/§6).
CREATE TABLE session_turn (
    session_id     TEXT NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    turn_index     INTEGER NOT NULL CHECK (turn_index >= 0),
    role           TEXT NOT NULL,                 -- user|tutor
    content        TEXT NOT NULL,
    ts             TIMESTAMPTZ NOT NULL,
    ao_scaffolded  TEXT,
    PRIMARY KEY (session_id, turn_index)
);

-- First-unlock achievements (gamification §5). Sticky — never revoked.
CREATE TABLE achievement (
    student_id      TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    achievement_id  TEXT NOT NULL,
    unlocked_at     TIMESTAMPTZ NOT NULL,
    xp_awarded      INTEGER NOT NULL CHECK (xp_awarded >= 0),
    PRIMARY KEY (student_id, achievement_id)
);

-- Active/historical quests (gamification §2.3).
CREATE TABLE quest (
    quest_id     TEXT PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    shape        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',  -- active|completed|expired
    started_at   TIMESTAMPTZ NOT NULL,
    expires_at   TIMESTAMPTZ,
    xp_reward    INTEGER NOT NULL CHECK (xp_reward >= 0)
);
CREATE INDEX quest_active_idx ON quest (student_id, status);
