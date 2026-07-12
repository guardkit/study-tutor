"""Settlement-semantics tests over the fake store (spec §4.2 / §4.3).

Exercises ``finalize_session`` and ``sweep_settle_session`` against the in-memory
``FakeStudentStore`` (which mirrors the Postgres settlement contract): the
exactly-once + identical-replay guarantee, the zero-turn 0-XP settle, the
savepoint-fault behaviour (session still ends, ``settled_at`` NULL), and sweep
idempotency. The real-Postgres proofs live in the integration suite.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.student_model import Misconception
from study_tutor.session.errors import SessionNotFoundError
from tests.unit.knowledge.store.fakes import FakeStudentStore

UTC = timezone.utc
T0 = datetime(2026, 7, 12, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)


async def _active_session_with_turns(
    store: FakeStudentStore, *, engagement_seconds: int, student_id: str = "s1"
) -> str:
    """Create an active session and inject two turns ``engagement_seconds`` apart."""
    record, _ = await store.create_session(
        student_id=student_id, subject="english", topic="Macbeth"
    )
    sid = record.session_id
    first, last = T0, T0 + timedelta(seconds=engagement_seconds)
    store._turns[sid] = [
        {"session_id": sid, "turn_index": 0, "role": "user",
         "content": "q", "ts": first, "ao_scaffolded": None},
        {"session_id": sid, "turn_index": 1, "role": "tutor",
         "content": "a", "ts": last, "ao_scaffolded": None},
    ]
    store._sessions[sid]["turn_count"] = 2
    return sid


async def _seeded() -> FakeStudentStore:
    store = FakeStudentStore()
    store.add_student(student_id="s1", year_group=9)
    return store


async def test_finalize_unknown_session_raises() -> None:
    store = await _seeded()
    with pytest.raises(SessionNotFoundError):
        await store.finalize_session(
            student_id="s1", session_id="nope", now=NOW,
            confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic=None,
        )


async def test_double_end_settles_once_and_replays_identically() -> None:
    """Concurrent double-end: the winner settles, the loser replays the IDENTICAL
    decision, and XP + achievements are banked exactly once (spec §4.2 / D6)."""
    store = await _seeded()
    sid = await _active_session_with_turns(store, engagement_seconds=300)

    first = await store.finalize_session(
        student_id="s1", session_id=sid, now=NOW,
        confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
    )
    second = await store.finalize_session(
        student_id="s1", session_id=sid, now=NOW + timedelta(minutes=1),
        confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
    )

    assert first.replayed is False and first.settled is True
    assert second.replayed is True
    # IDENTICAL decision payloads across the winner and the replay.
    assert first.decision == second.decision
    assert first.decision is not None

    # +60 (5-min band). First Steps (+50) pushes the total to 110, which
    # cascades into First Century (100-XP milestone) in the same settlement
    # (design §13.1 D7): both unlock, in catalog order, exactly once.
    assert first.decision.xp_awarded == 60
    assert [a.id for a in first.decision.unlocked] == ["first_steps", "first_century"]
    assert first.decision.total_xp_after == 160  # 60 + 50 + 50
    assert store._sessions[sid]["xp_awarded"] == 60  # session banks base XP only
    assert len([k for k in store._achievements if k[0] == "s1"]) == 2


async def test_zero_turn_session_settles_at_zero_xp_with_marker() -> None:
    """A zero-turn session settles at 0 XP but IS settled (marker stamped, D5)."""
    store = await _seeded()
    record, _ = await store.create_session(
        student_id="s1", subject="english", topic="Macbeth"
    )
    sid = record.session_id

    result = await store.finalize_session(
        student_id="s1", session_id=sid, now=NOW,
        confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
    )

    assert result.had_turns is False
    assert result.decision is not None and result.decision.xp_awarded == 0
    assert store._sessions[sid]["status"] == "ended"
    assert store._sessions[sid]["settled_at"] == NOW  # settled, at 0 XP


async def test_settlement_fault_ends_session_but_leaves_marker_null() -> None:
    """A poison child raises inside the savepoint: the session still ends, but
    ``settled_at`` stays NULL for the sweep and nothing partial is written (D4)."""
    store = await _seeded()
    sid = await _active_session_with_turns(store, engagement_seconds=300)

    poison = Misconception(
        text="   ",  # blank after sanitisation → raises in the savepoint
        topic_ref="Macbeth",
        observed_at=NOW,
        confidence_band_at_observation="developing",
    )
    result = await store.finalize_session(
        student_id="s1", session_id=sid, now=NOW,
        confidence_updates=[ConfidenceUpdate(topic_name="Macbeth", percentage=55)],
        misconceptions=[poison], aos_scaffolded=[], topic="Macbeth",
    )

    assert result.settled is False
    assert result.decision is None
    # Session ended; settlement marker NULL so the sweep re-settles it.
    assert store._sessions[sid]["status"] == "ended"
    assert store._sessions[sid].get("settled_at") is None
    # No partial writes: neither the confidence row nor an achievement landed.
    assert ("s1", "Macbeth") not in store._confidences
    assert not [k for k in store._achievements if k[0] == "s1"]


async def test_sweep_settles_unsettled_then_is_idempotent() -> None:
    """The sweep settles an ended-and-unsettled session, then skips it (spec §4.3)."""
    store = await _seeded()
    sid = store.add_ended_session(
        "s1", started_at=T0, last_activity=T0 + timedelta(seconds=600)
    )

    assert await store.list_unsettled_ended_sessions() == [sid]

    first = await store.sweep_settle_session(session_id=sid, now=NOW)
    assert first is not None and first.settled is True
    # Turn-less: engagement falls back to last_activity − started_at = 600 s → +60.
    assert first.decision is not None and first.decision.xp_awarded == 60
    assert store._sessions[sid]["settled_at"] == NOW

    # Re-running is a no-op (row no longer ended-and-unsettled).
    assert await store.list_unsettled_ended_sessions() == []
    second = await store.sweep_settle_session(
        session_id=sid, now=NOW + timedelta(minutes=1)
    )
    assert second is None
    assert store._sessions[sid]["xp_awarded"] == 60  # not double-banked
    # First Steps + First Century (the +50 cascade), banked exactly once.
    assert len([k for k in store._achievements if k[0] == "s1"]) == 2
