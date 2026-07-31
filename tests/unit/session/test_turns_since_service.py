"""Stage 1 — ``SessionService.turns_since`` (live robot-session mirror delta read).

Hermetic: a purpose-built fake store (no Postgres, no live model, no broker).
Pins the fences the handoff names verbatim — ownership from the caller's
``student_id`` only, ``since`` as a plain 0-based ROW offset into the same
ordered rows ``resume_session`` returns, an empty slice (never an error) once
``since`` reaches the end, and rows served for **ended** sessions too.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study_tutor.knowledge.store.entities import SessionRecord, SessionTurn
from study_tutor.session.errors import SessionForbidden, SessionNotFoundError
from study_tutor.session.service import SessionService, TurnsSinceResult

OWNER = "lilymay"
SESSION_ID = "sess-mirror-1"
T0 = datetime(2026, 7, 31, 10, 15, 0, tzinfo=timezone.utc)


class FakeTurnsStore:
    """Minimal store double: only the two reads ``turns_since`` touches."""

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


def _record(*, student_id: str = OWNER, status: str = "active") -> SessionRecord:
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


def _service(store: FakeTurnsStore) -> SessionService:
    return SessionService(store=store)  # type: ignore[arg-type]


async def test_since_zero_returns_the_full_transcript() -> None:
    """``since=0`` is the whole ordered transcript — identical to resume's rows."""
    rows = _turns(4)
    service = _service(FakeTurnsStore(record=_record(), turns=rows))

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=0
    )

    assert isinstance(result, TurnsSinceResult)
    assert result.turns == tuple(rows)
    assert result.total == 4
    assert result.session_id == SESSION_ID
    assert result.student_id == OWNER


async def test_mid_slice_returns_only_rows_at_or_after_the_offset() -> None:
    """``since`` is a plain ROW offset, not a timestamp and not a pairs count."""
    rows = _turns(6)
    service = _service(FakeTurnsStore(record=_record(), turns=rows))

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=4
    )

    assert result.turns == tuple(rows[4:])
    assert [t.content for t in result.turns] == ["row-4", "row-5"]
    # ``total`` is the RAW row count, never the ``// 2`` pairs projection.
    assert result.total == 6


async def test_since_equal_to_total_returns_empty_with_total() -> None:
    """The steady-state poll: caught up ⇒ empty slice, not an error."""
    rows = _turns(4)
    service = _service(FakeTurnsStore(record=_record(), turns=rows))

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=4
    )

    assert result.turns == ()
    assert result.total == 4


async def test_since_beyond_total_returns_empty_with_total() -> None:
    """A stale/over-large offset is still a normal empty read."""
    service = _service(FakeTurnsStore(record=_record(), turns=_turns(4)))

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=99
    )

    assert result.turns == ()
    assert result.total == 4


async def test_ended_session_still_returns_its_rows() -> None:
    """This reads ended sessions (as ``resume_session`` also does since Stage 0)
    — the poll survives the active→ended transition (no ``SessionEnded``)."""
    rows = _turns(4)
    service = _service(
        FakeTurnsStore(record=_record(status="ended"), turns=rows)
    )

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=0
    )

    assert result.turns == tuple(rows)
    assert result.total == 4
    assert result.status == "ended"


async def test_result_carries_the_session_status() -> None:
    """``status`` rides back so the mirror can render the ended state."""
    service = _service(FakeTurnsStore(record=_record(), turns=_turns(2)))

    result = await service.turns_since(
        student_id=OWNER, session_id=SESSION_ID, since=0
    )

    assert result.status == "active"


async def test_non_owner_is_forbidden() -> None:
    """Ownership is the caller's resolved id vs the session row — never asserted."""
    service = _service(FakeTurnsStore(record=_record(), turns=_turns(4)))

    with pytest.raises(SessionForbidden):
        await service.turns_since(
            student_id="alex", session_id=SESSION_ID, since=0
        )


async def test_unknown_session_raises_not_found() -> None:
    service = _service(FakeTurnsStore(record=None))

    with pytest.raises(SessionNotFoundError):
        await service.turns_since(
            student_id=OWNER, session_id="sess-nope", since=0
        )
