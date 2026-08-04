"""In-memory fake StudentStore for fast, DB-free testing (TASK-SMP-07).

``FakeStudentStore`` implements the full StudentStore Protocol with dict-backed
storage, reproducing the contracted behaviour (band derivation, idempotency,
validation, append-only F1) without a database dependency. Reusable by
FEAT-SMP-002/003 caller tests.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from study_tutor.gamification import (
    EndedSessionFact,
    HeldAchievementFact,
    build_gamification_state,
)
from study_tutor.gamification.economy import (
    MIN_SESSION_SECONDS,
    london_date,
    session_xp,
    started_after_evening,
    started_before_morning,
)
from study_tutor.gamification.catalog_w2 import POETRY_PIONEER_SLUG
from study_tutor.gamification.engine import (
    PriorFacts,
    SessionFacts,
    SettlementResult,
    decide,
)
from study_tutor.gamification.signals import (
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

# ASCII control characters to strip (preserves TAB, LF, CR per ASSUM-007)
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
_MAX_MISCONCEPTION_TEXT_LENGTH = 500


def _sanitise_misconception_text(text: str) -> str:
    """Sanitise misconception text: strip control chars, cap at 500 chars."""
    cleaned = _CONTROL_CHARS_PATTERN.sub("", text)
    if len(cleaned) > _MAX_MISCONCEPTION_TEXT_LENGTH:
        cleaned = cleaned[:_MAX_MISCONCEPTION_TEXT_LENGTH]
    return cleaned


class FakeStudentStore:
    """In-memory StudentStore for fast, DB-free testing.

    Implements the full StudentStore Protocol with dict-backed storage.
    Write-path methods reproduce contracted behaviour:
    - Band derivation via confidence_band_for
    - Idempotency on session_id (record_session_completion)
    - Unknown-learner rejection (FK simulation)
    - ±range validation (percentage 0-100, year_group 7-13)
    - Append-only F1 (record_misconception: no dedup)
    """

    def __init__(self) -> None:
        # Student records: {student_id: {...}}
        self._students: dict[str, dict[str, Any]] = {}
        # Topic confidences: {(student_id, topic_name): {...}}
        self._confidences: dict[tuple[str, str, str], dict[str, Any]] = {}  # (student_id, subject, topic_name) — ADR-ARCH-032
        # Misconceptions: list of {...} (append-only)
        self._misconceptions: list[dict[str, Any]] = []
        # Sessions: {session_id: {...}}
        self._sessions: dict[str, dict[str, Any]] = {}
        # Session turns: {session_id: [turns...]}
        self._turns: dict[str, list[dict[str, Any]]] = {}
        # Completed sessions (for idempotency): set of session_ids
        self._completed_sessions: set[str] = set()
        # Achievements: {(student_id, achievement_id): {...}} (settlement-written)
        self._achievements: dict[tuple[str, str], dict[str, Any]] = {}
        # Confidence history: append-only list of settlement rows.
        self._confidence_history: list[dict[str, Any]] = []
        # Reachable flag for ping
        self._reachable = True

    # -- Health -------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if the store is reachable."""
        return self._reachable

    async def student_exists(self, student_id: str) -> bool:
        """Whether the student has an identity row (auth unseeded-guard)."""
        return student_id in self._students

    async def delete_sessions_for_student(
        self, student_id: str
    ) -> dict[str, int]:
        """Scoped dev reset (mirrors PostgresStudentStore, 2026-08-04):
        delete ONE student's sessions + turns; learner state untouched."""
        doomed = [
            sid
            for sid, sess in self._sessions.items()
            if sess["student_id"] == student_id
        ]
        turn_count = sum(len(self._turns.get(sid, [])) for sid in doomed)
        for sid in doomed:
            self._sessions.pop(sid, None)
            self._turns.pop(sid, None)
            self._completed_sessions.discard(sid)
        return {"sessions": len(doomed), "turns": turn_count}

    # -- Reads (handler + planner) -----------------------------------------

    async def get_student_state(self, student_id: str) -> StudentState:
        """Aggregate snapshot. Returns empty=True when student unknown."""
        student = self._students.get(student_id)
        if not student:
            return StudentState(empty=True)

        # Get topic confidences for this student
        topic_confs = [
            TopicConfidenceSnapshot(
                topic_name=conf["topic_name"],
                band=conf["band"],
                percentage=conf["percentage"],
                last_revised_at=conf["last_revised_at"],
                subject=conf.get("subject", "english"),
            )
            for key, conf in self._confidences.items()
            if key[0] == student_id
        ]

        # Get recent misconceptions
        recent_miscs = [
            MisconceptionSnapshot(
                topic_name=misc["topic_name"],
                text=misc["text"],
                observed_at=misc["observed_at"],
            )
            for misc in self._misconceptions
            if misc["student_id"] == student_id
        ]

        return StudentState(
            empty=False,
            stale=False,
            student_id=student_id,
            year_group=student.get("year_group"),
            target_grade=student.get("target_grade"),
            subjects=[],
            current_texts=[],
            topic_confidences=topic_confs,
            recent_misconceptions=recent_miscs,
            most_recent_session_id=None,
        )

    async def get_topic_confidences(
        self, student_id: str, subject: str | None = None
    ) -> list[TopicConfidence]:
        """Per-topic confidence entities. Empty list when unknown.

        ``subject`` filters to one mastery dimension (ADR-ARCH-032);
        ``None`` returns every subject's rows (mirrors PostgresStudentStore).
        """
        student = self._students.get(student_id)
        if not student:
            return []

        return [
            TopicConfidence(
                student_ref=student_id,
                topic_ref=conf["topic_name"],
                percentage=conf["percentage"],
                band=conf["band"],
                last_revised_at=conf["last_revised_at"],
            )
            for key, conf in self._confidences.items()
            if key[0] == student_id
            and (subject is None or conf.get("subject", "english") == subject)
        ]

    async def get_gamification_state(self, student_id: str) -> GamificationState:
        """Read-side gamification snapshot from in-memory **banked** facts (spec §5).

        Reads banked ``xp_awarded`` off ended session rows and the achievement
        rows settlement wrote, then folds them through the same
        ``study_tutor.gamification`` builder as the Postgres store, so fake and
        real derive identical streak / level / XP / achievement views.
        """
        student = self._students.get(student_id)
        if not student:
            return GamificationState(exists=False)

        ended_sessions = [
            EndedSessionFact(
                started_at=sess["started_at"],
                last_activity=sess["last_activity"],
                xp_awarded=int(sess.get("xp_awarded", 0) or 0),
            )
            for sess in self._sessions.values()
            if sess["student_id"] == student_id and sess["status"] == "ended"
        ]
        achievements = [
            HeldAchievementFact(
                id=aid,
                unlocked_at=row["unlocked_at"],
                xp_awarded=int(row.get("xp_awarded", 0) or 0),
            )
            for (sid_key, aid), row in self._achievements.items()
            if sid_key == student_id
        ]
        return build_gamification_state(
            student_name=student.get("name") or student_id,
            ended_sessions=ended_sessions,
            achievements=achievements,
            today=london_date(datetime.now(timezone.utc)),
        )

    async def get_recent_misconceptions(
        self,
        student_id: str,
        *,
        window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
    ) -> list[Misconception]:
        """Misconceptions observed within window_days."""
        student = self._students.get(student_id)
        if not student:
            return []

        now = datetime.now(timezone.utc)
        window_cutoff = now.timestamp() - (window_days * 24 * 3600)

        return [
            Misconception(
                text=misc["text"],
                topic_ref=misc["topic_name"],
                observed_at=misc["observed_at"],
                confidence_band_at_observation=misc["band_at_observation"],
            )
            for misc in self._misconceptions
            if (
                misc["student_id"] == student_id
                and misc["observed_at"].timestamp() >= window_cutoff
            )
        ]

    # -- Learner-state writes (replace GraphitiWriteHelper F1/F2/F3) --------

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
        """Session-end write: XP, confidence, misconceptions in one transaction.

        Idempotent on session_id - retried session-end does not double-award XP.

        Idempotency is **status-based** to match Postgres (whose gate is
        ``ON CONFLICT … WHERE status != 'ended'``): if the session row already
        exists and is ``ended``, the children are dropped as a no-op. This makes
        ``end_session`` *participate* in the gate (W0 spec §1) — calling
        ``end_session`` before this write reproduces the drop the composed-service
        path used to suffer, so fake and Postgres agree. When no session row
        exists (callers that write completions directly, e.g. producer tests),
        the phantom-row idempotency falls back to ``_completed_sessions``.
        """
        # Unknown learner rejection
        if student_id not in self._students:
            raise ValueError(f"Unknown learner: {student_id}")

        # Status-based idempotency gate (mirrors the Postgres WHERE status != 'ended'):
        # an already-ended session — or a previously-recorded phantom — is a no-op.
        session = self._sessions.get(session_id)
        if session is not None and session["status"] == "ended":
            return
        if session is None and session_id in self._completed_sessions:
            return

        # Validate confidence updates
        for update in confidence_updates:
            if not 0 <= update.percentage <= 100:
                raise ValueError(
                    f"Confidence percentage must be in [0, 100]; got {update.percentage}"
                )

        # ADR-ARCH-032: the session row's subject is authoritative for the
        # mastery child-writes (mirrors the Postgres RETURNING-subject path);
        # a row minted by this end-first path defaults to english.
        row_subject = (session.get("subject") if session else None) or "english"

        # Apply confidence updates under the session's subject
        for update in confidence_updates:
            await self.apply_confidence_update(
                student_id=student_id,
                update=update.model_copy(update={"subject": row_subject}),
            )

        # Record misconceptions
        for misc in misconceptions:
            if not misc.topic_ref or not misc.text:
                raise ValueError("Misconception must have topic_ref and text")
            await self.record_misconception(
                student_id=student_id,
                topic_name=misc.topic_ref,
                text=misc.text,
                subject=row_subject,
            )

        # Transition the session to 'ended' (status-based idempotency, mirrors the
        # Postgres upsert). For an existing row we flip status + bank topic/xp/aos;
        # with no row we fall back to the phantom-completed set.
        if session is not None:
            session["status"] = "ended"
            session["last_activity"] = datetime.now(timezone.utc)
            session["topic"] = topic
            session["xp_awarded"] = xp_awarded
            session["aos_scaffolded"] = list(aos_scaffolded)
        else:
            self._completed_sessions.add(session_id)

        # Note: XP is not currently tracked in this fake (would be session record)

    # -- Settlement (spec §4.2 / §4.3 — mirrors PostgresStudentStore) -------

    def _prior_facts(self, student_id: str, exclude_session_id: str) -> PriorFacts:
        """Assemble PriorFacts EXCLUDING the session under settlement (D6)."""
        total_xp = sum(
            int(sess.get("xp_awarded", 0) or 0)
            for sid, sess in self._sessions.items()
            if sess["student_id"] == student_id and sid != exclude_session_id
        )
        total_xp += sum(
            int(row.get("xp_awarded", 0) or 0)
            for (sid_key, _aid), row in self._achievements.items()
            if sid_key == student_id and row.get("session_id") != exclude_session_id
        )
        held = frozenset(
            aid
            for (sid_key, aid), row in self._achievements.items()
            if sid_key == student_id and row.get("session_id") != exclude_session_id
        )

        credit_days: set[date] = set()
        morning = evening = qualifying = 0
        for sid, sess in self._sessions.items():
            if (
                sess["student_id"] != student_id
                or sess["status"] != "ended"
                or sid == exclude_session_id
            ):
                continue
            engagement, last_turn = self._engagement(sid)
            if engagement < MIN_SESSION_SECONDS or last_turn is None:
                continue
            qualifying += 1
            credit_days.add(london_date(last_turn))
            if started_before_morning(sess["started_at"]):
                morning += 1
            if started_after_evening(sess["started_at"]):
                evening += 1

        return PriorFacts(
            total_xp=total_xp,
            streak_credit_days=frozenset(credit_days),
            held_achievement_ids=held,
            morning_qualifying_count=morning,
            evening_qualifying_count=evening,
            qualifying_session_count=qualifying,
        )

    def _engagement(self, session_id: str) -> tuple[float, datetime | None]:
        """(engagement_seconds, last_turn_at) from the session's turns."""
        turns = self._turns.get(session_id, [])
        if not turns:
            return 0.0, None
        stamps = [t["ts"] for t in turns]
        return (max(stamps) - min(stamps)).total_seconds(), max(stamps)

    def _w2_signals(self, student_id: str) -> W2Signals:
        """Assemble the W2 capture-wave signals from in-memory state (spec §2.3
        note / scope §4) — mirrors ``postgres._read_w2_facts`` so fake and real
        derive the identical W2 tranche."""
        topics = {
            topic: int(conf["percentage"])
            for (sid, _subject, topic), conf in self._confidences.items()
            if sid == student_id
        }
        studied_topic_count = len(topics)
        min_topic_confidence = min(topics.values()) if topics else 0

        # topic → text via the LATEST confidence-history row (session → text_name).
        hist = sorted(
            (h for h in self._confidence_history if h["student_id"] == student_id),
            key=lambda h: h["recorded_at"],
        )
        topic_text: dict[str, str] = {}
        for h in hist:
            sess = self._sessions.get(h["session_id"])
            text_name = sess.get("text_name") if sess else None
            if text_name:
                topic_text[h["topic_name"]] = text_name  # last wins (ascending)
        topic_text_confidences = [
            (topic, topic_text[topic], pct)
            for topic, pct in topics.items()
            if topic in topic_text
        ]
        mastered = compute_mastered_texts(topic_text_confidences)
        unseen = max(
            (
                pct
                for topic, pct in topics.items()
                if topic_text.get(topic) == UNSEEN_POETRY_SLUG
            ),
            default=0,
        )

        ended = [
            s
            for s in self._sessions.values()
            if s["student_id"] == student_id and s["status"] == "ended"
        ]
        distinct_texts = {s.get("text_name") for s in ended if s.get("text_name")}
        poetry_pioneer = sum(
            1 for s in ended if s.get("text_name") == POETRY_PIONEER_SLUG
        )
        genre_week = genre_week_achieved(
            (london_date(s["last_activity"]), s.get("text_name"))
            for s in ended
            if s.get("text_name")
        )
        eras = eras_covered(distinct_texts)

        session_ao_sets: list[set[str]] = []
        for sid, turns in self._turns.items():
            sess = self._sessions.get(sid)
            if not sess or sess["student_id"] != student_id:
                continue
            aos = {t.get("ao_scaffolded") for t in turns if t.get("ao_scaffolded")}
            if aos:
                session_ao_sets.append(aos)
        six_ao = any_six_ao_session(session_ao_sets)

        quotes_total = sum(int(s.get("quotes_embedded", 0) or 0) for s in ended)
        max_gain = max_confidence_gain_over_window(
            (h["topic_name"], london_date(h["recorded_at"]), int(h["percentage"]))
            for h in hist
        )

        return W2Signals(
            mastered_texts=mastered,
            poetry_pioneer_sessions=poetry_pioneer,
            unseen_confidence=unseen,
            distinct_text_count=len(distinct_texts),
            genre_week_achieved=genre_week,
            eras_covered=eras,
            six_ao_session=six_ao,
            max_confidence_gain_7d=max_gain,
            total_quotes_embedded=quotes_total,
            studied_topic_count=studied_topic_count,
            min_topic_confidence=min_topic_confidence,
        )

    def _bank_settlement(
        self,
        *,
        student_id: str,
        session_id: str,
        now: datetime,
        session_facts: SessionFacts,
        confidence_updates: list[ConfidenceUpdate],
        misconceptions: list[Misconception],
        subject: str = "english",
    ) -> Any:
        """Run the engine and bank its result (mirrors ``postgres._bank_settlement``).

        Validates the misconceptions FIRST so a poison child raises before any
        mutation (the fake's all-or-nothing savepoint stand-in), then applies the
        confidence writes BEFORE reading the W2 signals so the winner and a replay
        see the same W2 snapshot, then decides + banks XP/achievements.
        """
        for misc in misconceptions:
            if not misc.topic_ref or not _sanitise_misconception_text(misc.text).strip():
                raise ValueError("Misconception must have topic_ref and non-blank text")

        # ADR-ARCH-032: the session's subject is authoritative for every
        # mastery write banked here (mirrors postgres._bank_settlement).
        for update in confidence_updates:
            self._confidences[(student_id, subject, update.topic_name)] = {
                "topic_name": update.topic_name,
                "subject": subject,
                "percentage": update.percentage,
                "band": confidence_band_for(update.percentage),
                "last_revised_at": now,
            }
            self._confidence_history.append(
                {
                    "student_id": student_id,
                    "subject": subject,
                    "topic_name": update.topic_name,
                    "percentage": update.percentage,
                    "session_id": session_id,
                    "recorded_at": now,
                    "source": "session",
                }
            )

        w2 = self._w2_signals(student_id)
        prior = self._prior_facts(student_id, session_id)
        decision = decide(prior, session_facts, now, w2=w2)

        sess = self._sessions[session_id]
        sess["xp_awarded"] = decision.xp_awarded
        sess["settled_at"] = now
        for award in decision.unlocked:
            self._achievements.setdefault(
                (student_id, award.id),
                {"xp_awarded": award.xp, "unlocked_at": now, "session_id": session_id},
            )
        for misc in misconceptions:
            self._misconceptions.append(
                {
                    "student_id": student_id,
                    "topic_name": misc.topic_ref,
                    "text": _sanitise_misconception_text(misc.text),
                    "observed_at": now,
                    "band_at_observation": self._confidences.get(
                        (student_id, subject, misc.topic_ref), {}
                    ).get("band", "struggling"),
                }
            )
        return decision

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
        """Settle a session in one logical transaction (spec §4.2)."""
        from study_tutor.session.errors import SessionNotFoundError

        sess = self._sessions.get(session_id)
        if sess is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        engagement, last_turn_at = self._engagement(session_id)
        had_turns = bool(self._turns.get(session_id))
        session_facts = SessionFacts(
            engagement_seconds=engagement,
            started_at=sess["started_at"],
            last_turn_at=last_turn_at,
        )
        subject = sess["subject"]
        aos_touched = tuple(aos_scaffolded or sess.get("aos_scaffolded", []))

        if sess["status"] == "ended":
            # Replay: reconstruct the identical decision, write nothing (D6).
            prior = self._prior_facts(student_id, session_id)
            w2 = self._w2_signals(student_id)
            decision = decide(prior, session_facts, now, w2=w2)
            return SettlementResult(
                decision=decision,
                settled=True,
                replayed=True,
                session_id=session_id,
                subject=subject,
                topic=sess.get("topic"),
                aos_touched=tuple(sess.get("aos_scaffolded", [])),
                duration_seconds=int(engagement),
                ended_at=now,
                had_turns=had_turns,
            )

        # Winner: the status flip is the gate (outside the savepoint).
        sess["status"] = "ended"
        sess["last_activity"] = now
        settled = True
        try:
            decision = self._bank_settlement(
                student_id=student_id,
                session_id=session_id,
                now=now,
                session_facts=session_facts,
                confidence_updates=confidence_updates,
                misconceptions=misconceptions,
                subject=subject or "english",
            )
        except Exception:  # noqa: BLE001 — settlement is best-effort (D4)
            decision = None
            settled = False

        return SettlementResult(
            decision=decision,
            settled=settled,
            replayed=False,
            session_id=session_id,
            subject=subject,
            topic=topic if topic is not None else sess.get("topic"),
            aos_touched=aos_touched,
            duration_seconds=int(engagement),
            ended_at=now,
            had_turns=had_turns,
        )

    async def sweep_settle_session(
        self, *, session_id: str, now: datetime
    ) -> SettlementResult | None:
        """Settle one ended-and-unsettled session (spec §4.3). Idempotent."""
        sess = self._sessions.get(session_id)
        if sess is None or sess["status"] != "ended" or sess.get("settled_at") is not None:
            return None

        student_id = sess["student_id"]
        engagement, last_turn_at = self._engagement(session_id)
        had_turns = bool(self._turns.get(session_id))
        if not had_turns:
            engagement = max(
                0.0, (sess["last_activity"] - sess["started_at"]).total_seconds()
            )
            last_turn_at = sess["last_activity"]
        session_facts = SessionFacts(
            engagement_seconds=engagement,
            started_at=sess["started_at"],
            last_turn_at=last_turn_at,
        )
        decision = self._bank_settlement(
            student_id=student_id,
            session_id=session_id,
            now=now,
            session_facts=session_facts,
            confidence_updates=[],
            misconceptions=[],
        )
        return SettlementResult(
            decision=decision,
            settled=True,
            replayed=False,
            session_id=session_id,
            subject=sess["subject"],
            topic=sess.get("topic"),
            aos_touched=tuple(sess.get("aos_scaffolded", [])),
            duration_seconds=int(engagement),
            ended_at=now,
            had_turns=had_turns,
        )

    async def list_unsettled_ended_sessions(self) -> list[str]:
        """Session ids of every ended-and-unsettled row (spec §4.3)."""
        rows = [
            (sid, sess["last_activity"])
            for sid, sess in self._sessions.items()
            if sess["status"] == "ended" and sess.get("settled_at") is None
        ]
        rows.sort(key=lambda r: r[1])
        return [sid for sid, _ in rows]

    async def record_misconception(
        self,
        *,
        student_id: str,
        topic_name: str,
        text: str,
        subject: str = "english",
    ) -> None:
        """F1 - single Coach-observed misconception, append-only (no dedup)."""
        # Unknown learner rejection
        if student_id not in self._students:
            raise ValueError(f"Unknown learner: {student_id}")

        # Validate inputs
        if not topic_name or not text:
            raise ValueError("Misconception must have topic_name and text")

        # Sanitise text
        sanitised = _sanitise_misconception_text(text)

        # Get current band for this topic (if exists, else struggling)
        key = (student_id, subject, topic_name)
        band = self._confidences.get(key, {}).get("band", "struggling")

        # Append (no deduplication - ASSUM-006)
        self._misconceptions.append(
            {
                "student_id": student_id,
                "subject": subject,
                "topic_name": topic_name,
                "text": sanitised,
                "observed_at": datetime.now(timezone.utc),
                "band_at_observation": band,
            }
        )

    async def apply_confidence_update(
        self, *, student_id: str, update: ConfidenceUpdate
    ) -> None:
        """F2 - persist one topic-confidence value (band derived at write)."""
        # Unknown learner rejection
        if student_id not in self._students:
            raise ValueError(f"Unknown learner: {student_id}")

        # Validate percentage range
        if not 0 <= update.percentage <= 100:
            raise ValueError(
                f"Confidence percentage must be in [0, 100]; got {update.percentage}"
            )

        # Derive band
        band = confidence_band_for(update.percentage)

        # Upsert confidence under the (student, subject, topic) key
        # (ADR-ARCH-032 — mirrors the widened Postgres primary key).
        key = (student_id, update.subject, update.topic_name)
        self._confidences[key] = {
            "topic_name": update.topic_name,
            "subject": update.subject,
            "percentage": update.percentage,
            "band": band,
            "last_revised_at": datetime.now(timezone.utc),
        }

    # -- Session persistence (cross-device contract §5) --------------------

    def _to_record(self, session_id: str, sess: dict[str, Any]) -> SessionRecord:
        """Map an in-memory session dict to a :class:`SessionRecord`."""
        return SessionRecord(
            session_id=session_id,
            student_id=sess["student_id"],
            subject=sess["subject"],
            topic=sess.get("topic"),
            status=sess["status"],
            started_at=sess["started_at"],
            last_activity=sess["last_activity"],
            turn_count=sess["turn_count"],
            aos_scaffolded=sess.get("aos_scaffolded", []),
            text_name=sess.get("text_name"),
            quotes_embedded=int(sess.get("quotes_embedded", 0) or 0),
            summary=sess.get("summary"),
        )

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
        S-R3 §2.1: ``aos_scaffolded`` persists the plan's ``focus_aos`` at
        start-time onto the created row (``None`` → ``[]``). S-E4 / scope §4.2:
        ``text_name`` persists the canonical set-text slug. Resumes ignore both.
        """
        planned_aos = list(aos_scaffolded) if aos_scaffolded else []
        # Check for existing active session if resume requested
        if resume_if_active:
            for sid, sess in self._sessions.items():
                if (
                    sess["student_id"] == student_id
                    and sess["subject"] == subject
                    and sess["status"] == "active"
                ):
                    return (self._to_record(sid, sess), False)

        # Create new session
        session_id = str(uuid4())
        now = datetime.now(timezone.utc)
        self._sessions[session_id] = {
            "student_id": student_id,
            "subject": subject,
            "topic": topic,
            "status": "active",
            "started_at": now,
            "last_activity": now,
            "turn_count": 0,
            "aos_scaffolded": list(planned_aos),
            "text_name": text_name,
            "quotes_embedded": 0,
            "summary": None,
        }
        self._turns[session_id] = []

        return (self._to_record(session_id, self._sessions[session_id]), True)

    async def get_session(self, session_id: str) -> SessionRecord | None:
        """Fetch a session, or None if unknown."""
        sess = self._sessions.get(session_id)
        if not sess:
            return None
        return self._to_record(session_id, sess)

    async def list_sessions(
        self,
        student_id: str,
        *,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """Recent sessions for a student, newest last_activity first."""
        sessions = [
            self._to_record(sid, sess)
            for sid, sess in self._sessions.items()
            if sess["student_id"] == student_id
            and (status is None or sess["status"] == status)
        ]

        # Sort by last_activity descending
        sessions.sort(key=lambda s: s.last_activity, reverse=True)

        return sessions[:limit]

    async def append_turn(
        self,
        *,
        session_id: str,
        role: TurnRole,
        content: str,
        ao_scaffolded: str | None = None,
        quotes_embedded: int = 0,
    ) -> SessionTurn:
        """Append one turn, bumping turn_count + last_activity, accumulating the
        per-turn corpus-hit quote count into the session counter (S-E4 §4.3)."""
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Unknown session: {session_id}")

        turn_index = sess["turn_count"]
        now = datetime.now(timezone.utc)

        turn = {
            "session_id": session_id,
            "turn_index": turn_index,
            "role": role,
            "content": content,
            "ts": now,
            "ao_scaffolded": ao_scaffolded,
        }

        self._turns.setdefault(session_id, []).append(turn)
        sess["turn_count"] += 1
        sess["last_activity"] = now
        sess["quotes_embedded"] = int(sess.get("quotes_embedded", 0) or 0) + max(
            0, int(quotes_embedded)
        )

        return SessionTurn(
            session_id=session_id,
            turn_index=turn_index,
            role=role,
            content=content,
            ts=now,
            ao_scaffolded=ao_scaffolded,
        )

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        """Ordered transcript for resume_session."""
        turns = self._turns.get(session_id, [])
        return [
            SessionTurn(
                session_id=t["session_id"],
                turn_index=t["turn_index"],
                role=t["role"],
                content=t["content"],
                ts=t["ts"],
                ao_scaffolded=t.get("ao_scaffolded"),
            )
            for t in turns
        ]

    async def end_session(self, session_id: str) -> SessionRecord:
        """Transition active → ended and stamp the summary."""
        sess = self._sessions.get(session_id)
        if not sess:
            raise ValueError(f"Unknown session: {session_id}")

        sess["status"] = "ended"
        sess["last_activity"] = datetime.now(timezone.utc)

        return self._to_record(session_id, sess)

    # -- Test helpers -------------------------------------------------------

    def add_student(
        self,
        student_id: str,
        *,
        name: str = "Test Student",
        year_group: int = 10,
        target_grade: str = "7",
    ) -> None:
        """Helper for tests: add a student to the store."""
        if not 7 <= year_group <= 13:
            raise ValueError(f"year_group must be in [7, 13]; got {year_group}")

        self._students[student_id] = {
            "student_id": student_id,
            "name": name,
            "year_group": year_group,
            "target_grade": target_grade,
            "created_at": datetime.now(timezone.utc),
        }

    def set_unreachable(self, unreachable: bool = True) -> None:
        """Helper for tests: simulate store unreachable."""
        self._reachable = not unreachable

    def add_topic_confidence(
        self,
        student_id: str,
        topic_name: str,
        percentage: int,
        *,
        last_revised_at: datetime | None = None,
        subject: str = "english",
    ) -> None:
        """Helper for tests: seed one topic-confidence row (band derived)."""
        self._confidences[(student_id, subject, topic_name)] = {
            "topic_name": topic_name,
            "subject": subject,
            "percentage": percentage,
            "band": confidence_band_for(percentage),
            "last_revised_at": last_revised_at or datetime.now(timezone.utc),
        }

    def add_ended_session(
        self,
        student_id: str,
        *,
        started_at: datetime,
        last_activity: datetime,
        subject: str = "english",
        topic: str | None = None,
        xp_awarded: int | None = None,
        text_name: str | None = None,
        quotes_embedded: int = 0,
    ) -> str:
        """Helper for tests: add a completed (``ended``) session with a **banked**
        ``xp_awarded`` so the banked-facts projection reads it directly (spec §5).

        ``xp_awarded`` defaults to the engagement-band XP for the ``started_at →
        last_activity`` duration (``session_xp``), matching what settlement would
        have banked; pass an explicit value to stage a specific banked total.
        ``text_name`` / ``quotes_embedded`` seed the W2 capture-wave signals.

        Returns the generated session_id.
        """
        banked = (
            xp_awarded
            if xp_awarded is not None
            else session_xp((last_activity - started_at).total_seconds())
        )
        session_id = str(uuid4())
        self._sessions[session_id] = {
            "student_id": student_id,
            "subject": subject,
            "topic": topic,
            "status": "ended",
            "started_at": started_at,
            "last_activity": last_activity,
            "turn_count": 0,
            "aos_scaffolded": [],
            "text_name": text_name,
            "quotes_embedded": quotes_embedded,
            "summary": None,
            "xp_awarded": banked,
        }
        self._turns[session_id] = []
        return session_id


__all__ = ["FakeStudentStore"]
