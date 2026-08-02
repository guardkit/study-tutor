-- Reference DDL for the study-tutor StudentStore (ADR-ARCH-023, gamification §11).
--
-- LIVING REFERENCE. This file is kept in sync by hand; `alembic upgrade head`
-- is the source of truth for the schema (revisions 3c7cd4bca034 →
-- b7d1e4f92a3c → c3f8a1b6d2e4). Do NOT apply by hand — the runbook's G7 gate runs
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
    subject          TEXT NOT NULL DEFAULT 'english',  -- mastery dimension (rev d5a9c2e7f814, ADR-ARCH-032 / study-room §14)
    topic_name       TEXT NOT NULL,
    percentage       SMALLINT NOT NULL CHECK (percentage BETWEEN 0 AND 100),
    band             TEXT NOT NULL,               -- struggling|developing|secure|mastered
    last_revised_at  TIMESTAMPTZ NOT NULL,        -- EPOCH_NEVER_REVISED sentinel for baselines
    PRIMARY KEY (student_id, subject, topic_name)
);

CREATE TABLE misconception (
    id           BIGSERIAL PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    subject      TEXT NOT NULL DEFAULT 'english',  -- rev d5a9c2e7f814 (ADR-ARCH-032)
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
    text_name       TEXT,                             -- plan-fact captured at start (rev b7d1e4f92a3c, S-E4)
    settled_at      TIMESTAMPTZ,                      -- settlement work-queue marker (rev b7d1e4f92a3c); NULL until settled
    quotes_embedded INTEGER NOT NULL DEFAULT 0 CHECK (quotes_embedded >= 0),  -- cumulative corpus-hit quotes (rev c3f8a1b6d2e4, S-E4 §4.3, R8); append_turn accumulates
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
    session_id      TEXT REFERENCES session(session_id),  -- replay support (rev b7d1e4f92a3c, D1)
    subject         TEXT,                          -- NULL = whole-student (W1); subject-pack rows stamp theirs when the per-subject catalog refactor lands (rev d5a9c2e7f814)
    PRIMARY KEY (student_id, achievement_id)
);

-- Append-only confidence audit trail (rev b7d1e4f92a3c, spec §3). Modeled on
-- misconception; written by settlement from day one (D2 — unbackfillable).
CREATE TABLE topic_confidence_history (
    id           BIGSERIAL PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES student(student_id) ON DELETE CASCADE,
    subject      TEXT NOT NULL DEFAULT 'english',  -- rev d5a9c2e7f814 (ADR-ARCH-032)
    topic_name   TEXT NOT NULL,
    percentage   INTEGER NOT NULL CHECK (percentage BETWEEN 0 AND 100),
    session_id   TEXT,
    recorded_at  TIMESTAMPTZ NOT NULL,
    source       TEXT NOT NULL
);
CREATE INDEX topic_confidence_history_recent_idx ON topic_confidence_history (student_id, recorded_at DESC);

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
