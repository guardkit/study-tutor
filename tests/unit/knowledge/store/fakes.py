"""In-memory fake StudentStore for fast, DB-free testing (TASK-SMP-07).

``FakeStudentStore`` implements the full StudentStore Protocol with dict-backed
storage, reproducing the contracted behaviour (band derivation, idempotency,
validation, append-only F1) without a database dependency. Reusable by
FEAT-SMP-002/003 caller tests.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from study_tutor.knowledge.store.entities import (
    ConfidenceUpdate,
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
        self._confidences: dict[tuple[str, str], dict[str, Any]] = {}
        # Misconceptions: list of {...} (append-only)
        self._misconceptions: list[dict[str, Any]] = []
        # Sessions: {session_id: {...}}
        self._sessions: dict[str, dict[str, Any]] = {}
        # Session turns: {session_id: [turns...]}
        self._turns: dict[str, list[dict[str, Any]]] = {}
        # Completed sessions (for idempotency): set of session_ids
        self._completed_sessions: set[str] = set()
        # Reachable flag for ping
        self._reachable = True

    # -- Health -------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if the store is reachable."""
        return self._reachable

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
        self, student_id: str
    ) -> list[TopicConfidence]:
        """Per-topic confidence entities. Empty list when unknown."""
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
        ]

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
        """
        # Unknown learner rejection
        if student_id not in self._students:
            raise ValueError(f"Unknown learner: {student_id}")

        # Idempotency check: if already completed, do nothing
        if session_id in self._completed_sessions:
            return

        # Validate confidence updates
        for update in confidence_updates:
            if not 0 <= update.percentage <= 100:
                raise ValueError(
                    f"Confidence percentage must be in [0, 100]; got {update.percentage}"
                )

        # Apply confidence updates
        for update in confidence_updates:
            await self.apply_confidence_update(
                student_id=student_id, update=update
            )

        # Record misconceptions
        for misc in misconceptions:
            if not misc.topic_ref or not misc.text:
                raise ValueError("Misconception must have topic_ref and text")
            await self.record_misconception(
                student_id=student_id,
                topic_name=misc.topic_ref,
                text=misc.text,
            )

        # Mark as completed (for idempotency)
        self._completed_sessions.add(session_id)

        # Note: XP is not currently tracked in this fake (would be session record)

    async def record_misconception(
        self,
        *,
        student_id: str,
        topic_name: str,
        text: str,
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
        key = (student_id, topic_name)
        band = self._confidences.get(key, {}).get("band", "struggling")

        # Append (no deduplication - ASSUM-006)
        self._misconceptions.append(
            {
                "student_id": student_id,
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

        # Upsert confidence
        key = (student_id, update.topic_name)
        self._confidences[key] = {
            "topic_name": update.topic_name,
            "percentage": update.percentage,
            "band": band,
            "last_revised_at": datetime.now(timezone.utc),
        }

    # -- Session persistence (cross-device contract §5) --------------------

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
        """
        # Check for existing active session if resume requested
        if resume_if_active:
            for sid, sess in self._sessions.items():
                if (
                    sess["student_id"] == student_id
                    and sess["subject"] == subject
                    and sess["status"] == "active"
                ):
                    return (
                        SessionRecord(
                            session_id=sid,
                            student_id=sess["student_id"],
                            subject=sess["subject"],
                            topic=sess.get("topic"),
                            status=sess["status"],
                            started_at=sess["started_at"],
                            last_activity=sess["last_activity"],
                            turn_count=sess["turn_count"],
                            aos_scaffolded=sess.get("aos_scaffolded", []),
                            summary=sess.get("summary"),
                        ),
                        False,  # Not created, resumed
                    )

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
            "aos_scaffolded": [],
            "summary": None,
        }
        self._turns[session_id] = []

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
        """Fetch a session, or None if unknown."""
        sess = self._sessions.get(session_id)
        if not sess:
            return None

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
            summary=sess.get("summary"),
        )

    async def list_sessions(
        self,
        student_id: str,
        *,
        status: SessionStatus | None = None,
        limit: int = DEFAULT_SESSION_LIST_LIMIT,
    ) -> list[SessionRecord]:
        """Recent sessions for a student, newest last_activity first."""
        sessions = [
            SessionRecord(
                session_id=sid,
                student_id=sess["student_id"],
                subject=sess["subject"],
                topic=sess.get("topic"),
                status=sess["status"],
                started_at=sess["started_at"],
                last_activity=sess["last_activity"],
                turn_count=sess["turn_count"],
                aos_scaffolded=sess.get("aos_scaffolded", []),
                summary=sess.get("summary"),
            )
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
    ) -> SessionTurn:
        """Append one turn, bumping turn_count + last_activity."""
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
            summary=sess.get("summary"),
        )

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


__all__ = ["FakeStudentStore"]
