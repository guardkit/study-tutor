"""Stage 2 — the ``SessionService`` → ``TurnNotifier`` hook (mirror freshness).

Hermetic: a purpose-built fake store and a recording fake notifier (no Postgres,
no live model, no broker). Pins **when** the mirror is pinged — after each
persisted row in ``turn`` and ``turn_stream``, and once after ``end_session``'s
finalize commits — and the fence that matters most: a notifier that blows up
must never turn a successful turn into a failed one.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from study_tutor.gamification.engine import SettlementResult
from study_tutor.knowledge.store.entities import SessionRecord, SessionTurn
from study_tutor.session.service import SessionService, TutorReply

OWNER = "lilymay"
SESSION_ID = "sess-mirror-1"
T0 = datetime(2026, 7, 31, 10, 15, 0, tzinfo=timezone.utc)


class RecordingNotifier:
    """Records notify() calls, in order, with the transcript length at the time.

    The length snapshot is what proves ordering: a ping recorded at ``rows=1``
    can only have happened after the user row was persisted and before the tutor
    row was.
    """

    def __init__(self, store: "FakeTurnStore | None" = None) -> None:
        self.calls: list[str] = []
        self.rows_at_call: list[int] = []
        self._store = store

    def notify(self, session_id: str) -> None:
        self.calls.append(session_id)
        self.rows_at_call.append(len(self._store.turns) if self._store else -1)


class ExplodingNotifier:
    """A notifier that fails every time — the request path must not care."""

    def __init__(self) -> None:
        self.calls = 0

    def notify(self, session_id: str) -> None:
        self.calls += 1
        raise RuntimeError("notifier is having a bad day")


class FakeTurnStore:
    """Minimal store double: the writes/reads the three hooked methods touch."""

    def __init__(
        self, *, record: SessionRecord | None, turn_count: int = 0
    ) -> None:
        self._record = record
        self.turns: list[SessionTurn] = []
        self._turn_count = turn_count
        self.finalized = False

    async def get_session(self, session_id: str) -> SessionRecord | None:
        if self._record is None or self._record.session_id != session_id:
            return None
        return self._record

    async def get_turns(self, session_id: str) -> list[SessionTurn]:
        return list(self.turns)

    async def append_turn(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        ao_scaffolded: str | None = None,
        quotes_embedded: int = 0,
    ) -> SessionTurn:
        turn = SessionTurn(
            session_id=session_id,
            turn_index=len(self.turns),
            role=role,  # type: ignore[arg-type]
            content=content,
            ts=T0 + timedelta(seconds=len(self.turns)),
        )
        self.turns.append(turn)
        return turn

    async def finalize_session(self, **kwargs: Any) -> SettlementResult:
        self.finalized = True
        return SettlementResult(
            decision=None,
            settled=True,
            replayed=False,
            session_id=SESSION_ID,
            subject="english",
            topic="Macbeth",
            aos_touched=(),
            duration_seconds=300,
            ended_at=T0 + timedelta(minutes=5),
            # I-T6 zero-turn: settles, assembles no completion, emits no event.
            had_turns=False,
        )


def _record(*, status: str = "active", turn_count: int = 0) -> SessionRecord:
    return SessionRecord(
        session_id=SESSION_ID,
        student_id=OWNER,
        subject="english",
        topic="Macbeth",
        status=status,  # type: ignore[arg-type]
        started_at=T0,
        last_activity=T0 + timedelta(minutes=5),
        turn_count=turn_count,
    )


async def _reply(_message: str) -> TutorReply:
    return TutorReply(response="Let's look at Act 1.")


# -------------------- turn() --------------------


async def test_turn_notifies_after_the_user_row_and_after_the_tutor_row() -> None:
    """Two rows persisted ⇒ two pings, each AFTER its row is durable."""
    store = FakeTurnStore(record=_record())
    notifier = RecordingNotifier(store)
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    await service.turn(
        student_id=OWNER,
        session_id=SESSION_ID,
        user_message="What drives Macbeth?",
        reply_fn=_reply,
    )

    assert notifier.calls == [SESSION_ID, SESSION_ID]
    # The user row is visible at the first ping (so the phone renders the
    # question before the tutor has answered); both rows at the second.
    assert notifier.rows_at_call == [1, 2]


async def test_turn_without_a_notifier_is_unchanged() -> None:
    """``turn_notifier=None`` is the ordinary case — no signalling, no breakage."""
    store = FakeTurnStore(record=_record())
    service = SessionService(store=store)

    result = await service.turn(
        student_id=OWNER,
        session_id=SESSION_ID,
        user_message="What drives Macbeth?",
        reply_fn=_reply,
    )

    assert result.tutor_response == "Let's look at Act 1."
    assert len(store.turns) == 2


async def test_a_raising_notifier_never_breaks_the_turn() -> None:
    """A notification is a courtesy to a viewer — never load-bearing."""
    store = FakeTurnStore(record=_record())
    notifier = ExplodingNotifier()
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    result = await service.turn(
        student_id=OWNER,
        session_id=SESSION_ID,
        user_message="What drives Macbeth?",
        reply_fn=_reply,
    )

    assert result.tutor_response == "Let's look at Act 1."
    assert len(store.turns) == 2
    assert notifier.calls == 2  # both hooks fired and both were swallowed


# -------------------- turn_stream() --------------------


async def test_turn_stream_notifies_at_the_same_two_persist_points() -> None:
    store = FakeTurnStore(record=_record())
    notifier = RecordingNotifier(store)
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    async def reply_stream(_message: str):
        yield "Let's "
        yield "look at Act 1."

    events = [
        event
        async for event in service.turn_stream(
            student_id=OWNER,
            session_id=SESSION_ID,
            user_message="What drives Macbeth?",
            reply_stream_fn=reply_stream,
        )
    ]

    assert [e.type for e in events] == ["token", "token", "done"]
    assert notifier.calls == [SESSION_ID, SESSION_ID]
    assert notifier.rows_at_call == [1, 2]


async def test_turn_stream_failure_notifies_only_the_persisted_user_row() -> None:
    """ASSUM-004: no tutor row is persisted, so there is no second ping."""
    store = FakeTurnStore(record=_record())
    notifier = RecordingNotifier(store)
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    async def failing_stream(_message: str):
        yield "Let's "
        raise RuntimeError("model fell over")

    events = [
        event
        async for event in service.turn_stream(
            student_id=OWNER,
            session_id=SESSION_ID,
            user_message="What drives Macbeth?",
            reply_stream_fn=failing_stream,
        )
    ]

    assert [e.type for e in events] == ["token", "error"]
    assert notifier.calls == [SESSION_ID]
    assert len(store.turns) == 1


# -------------------- end_session() --------------------


async def test_end_session_notifies_once_after_finalize_commits() -> None:
    """So a watching stream reads ``ended`` immediately instead of waiting a tick."""
    store = FakeTurnStore(record=_record())
    notifier = RecordingNotifier(store)
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    result = await service.end_session(student_id=OWNER, session_id=SESSION_ID)

    assert result.session_id == SESSION_ID
    assert store.finalized is True
    assert notifier.calls == [SESSION_ID]


async def test_a_raising_notifier_never_breaks_end_session() -> None:
    store = FakeTurnStore(record=_record())
    notifier = ExplodingNotifier()
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    result = await service.end_session(student_id=OWNER, session_id=SESSION_ID)

    assert result.session_id == SESSION_ID
    assert store.finalized is True
    assert notifier.calls == 1


# -------------------- read paths are untouched --------------------


async def test_reads_never_notify() -> None:
    """``turns_since`` and ``session_status`` change nothing — nothing to signal."""
    store = FakeTurnStore(record=_record())
    notifier = RecordingNotifier(store)
    service = SessionService(store=store, turn_notifier=notifier)  # type: ignore[arg-type]

    await service.turns_since(student_id=OWNER, session_id=SESSION_ID, since=0)
    await service.session_status(student_id=OWNER, session_id=SESSION_ID)

    assert notifier.calls == []
