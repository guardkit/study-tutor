"""Stage 0 — ``SessionService.resume_session`` reads **ended** sessions.

The phone's Session-History screen reads a finished conversation by resuming
it (handoff ``docs/runbooks/HANDOFF-spark-live-robot-session-mirror.md`` Stage
0, 2026-07-31 binding addendum). This is a READ widening only: the response
shape is unchanged (``status`` already carried ``ended``) and terminality
(contract §4 "no re-open") stays enforced on the WRITE verbs — pinned here.

Hermetic: a purpose-built fake store (no Postgres, no live model, no broker).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study_tutor.knowledge.store.entities import SessionRecord, SessionTurn
from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
)
from study_tutor.session.service import ResumeResult, SessionService

OWNER = "lilymay"
SESSION_ID = "sess-history-1"
T0 = datetime(2026, 7, 31, 10, 15, 0, tzinfo=timezone.utc)


class FakeResumeStore:
    """Minimal store double: only the two reads ``resume_session`` touches."""

    def __init__(
        self,
        *,
        record: SessionRecord | None,
        turns: list[SessionTurn] | None = None,
    ) -> None:
        self._record = record
        self._turns = list(turns or [])

    async def get_session(self, session_id: str) -> SessionRecord | None:
        if self._record is None or self._record.session_id != session_id:
            return None
        return self._record

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        return list(self._turns)


def _record(*, student_id: str = OWNER, status: str = "ended") -> SessionRecord:
    return SessionRecord(
        session_id=SESSION_ID,
        student_id=student_id,
        subject="english",
        topic="Macbeth",
        status=status,  # type: ignore[arg-type]
        started_at=T0,
        last_activity=T0 + timedelta(minutes=5),
        turn_count=4,
    )


def _turns(count: int = 4) -> list[SessionTurn]:
    return [
        SessionTurn(
            session_id=SESSION_ID,
            turn_index=i,
            role="user" if i % 2 == 0 else "tutor",
            content=f"row-{i}",
            ts=T0 + timedelta(seconds=i),
        )
        for i in range(count)
    ]


def _service(store: FakeResumeStore) -> SessionService:
    return SessionService(store=store)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# The widened read
# --------------------------------------------------------------------------


async def test_resume_of_ended_session_returns_ordered_transcript() -> None:
    """The History read: full ordered transcript + ``status: "ended"``, no raise."""
    rows = _turns(4)
    service = _service(FakeResumeStore(record=_record(status="ended"), turns=rows))

    result = await service.resume_session(
        student_id=OWNER, session_id=SESSION_ID
    )

    assert isinstance(result, ResumeResult)
    assert result.status == "ended"
    assert result.turns == tuple(rows)
    assert [t.content for t in result.turns] == ["row-0", "row-1", "row-2", "row-3"]
    assert result.session_id == SESSION_ID
    assert result.student_id == OWNER


async def test_resume_of_active_session_is_unchanged() -> None:
    """The pre-existing active read is untouched by the widening."""
    rows = _turns(2)
    service = _service(FakeResumeStore(record=_record(status="active"), turns=rows))

    result = await service.resume_session(
        student_id=OWNER, session_id=SESSION_ID
    )

    assert result.status == "active"
    assert result.turns == tuple(rows)


async def test_resume_of_ended_session_with_no_turns_is_empty_not_an_error() -> None:
    """A finished but empty conversation is a normal 'no rows' read."""
    service = _service(FakeResumeStore(record=_record(status="ended"), turns=[]))

    result = await service.resume_session(
        student_id=OWNER, session_id=SESSION_ID
    )

    assert result.status == "ended"
    assert result.turns == ()


# --------------------------------------------------------------------------
# The guards that are NOT widened
# --------------------------------------------------------------------------


async def test_non_owner_resuming_an_ended_session_is_forbidden() -> None:
    """Ownership comes from the caller's resolved id — the widening is status-only."""
    service = _service(FakeResumeStore(record=_record(status="ended"), turns=_turns(4)))

    with pytest.raises(SessionForbidden):
        await service.resume_session(student_id="alex", session_id=SESSION_ID)


async def test_unknown_session_still_raises_not_found() -> None:
    service = _service(FakeResumeStore(record=None))

    with pytest.raises(SessionNotFoundError):
        await service.resume_session(student_id=OWNER, session_id="sess-nope")


# --------------------------------------------------------------------------
# Terminality pins — the WRITE verbs still refuse an ended session (§4)
# --------------------------------------------------------------------------


async def test_turn_on_an_ended_session_still_raises_session_ended() -> None:
    """§4 "no re-open" — the read widening must not leak into the write path."""
    service = _service(FakeResumeStore(record=_record(status="ended"), turns=_turns(4)))

    async def _never_called(_: str) -> str:  # pragma: no cover - guard fires first
        raise AssertionError("reply_fn must not run on an ended session")

    with pytest.raises(SessionEnded):
        await service.turn(
            student_id=OWNER,
            session_id=SESSION_ID,
            user_message="one more?",
            reply_fn=_never_called,  # type: ignore[arg-type]
        )


async def test_end_session_on_an_ended_session_still_raises_session_ended() -> None:
    """No re-end / no re-open: ``ended`` stays terminal for the write verbs."""
    service = _service(FakeResumeStore(record=_record(status="ended"), turns=_turns(4)))

    with pytest.raises(SessionEnded):
        await service.end_session(student_id=OWNER, session_id=SESSION_ID)
