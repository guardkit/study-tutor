"""Capture round-trips + live W2 settlement against the fake store (S-E4).

These exercise the fake ``StudentStore`` (which mirrors the Postgres adapter's
S-E4 wiring): the canonical ``text_name`` captured at start, the per-session
``quotes_embedded`` counter, per-turn ``ao_scaffolded``, the confidence-history
write, and the W2 achievement tranche firing through ``finalize_session``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from tests.unit.knowledge.store.fakes import FakeStudentStore

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


async def _seed_active_session(store: FakeStudentStore, *, text_name=None) -> str:
    store.add_student("lilymay")
    record, _created = await store.create_session(
        student_id="lilymay", subject="english", topic="macbeth", text_name=text_name
    )
    return record.session_id


# -- Item 1: text_name captured at start round-trips ------------------------


@pytest.mark.asyncio
async def test_text_name_persists_at_start_and_reads_back() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    record = await store.get_session(sid)
    assert record is not None
    assert record.text_name == "macbeth"


@pytest.mark.asyncio
async def test_text_name_defaults_none_for_free_topic() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name=None)
    record = await store.get_session(sid)
    assert record is not None and record.text_name is None


# -- Item 2: quotes_embedded counter accumulates across turns ---------------


@pytest.mark.asyncio
async def test_quotes_embedded_accumulates_on_the_session() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(session_id=sid, role="user", content="q1")
    await store.append_turn(
        session_id=sid, role="tutor", content="a1", quotes_embedded=2
    )
    await store.append_turn(
        session_id=sid, role="tutor", content="a2", quotes_embedded=3
    )
    record = await store.get_session(sid)
    assert record is not None and record.quotes_embedded == 5


# -- Item 3: per-turn AO lands on the turn row ------------------------------


@pytest.mark.asyncio
async def test_per_turn_ao_lands_on_session_turn() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(
        session_id=sid, role="tutor", content="a", ao_scaffolded="AO2"
    )
    turns = await store.get_turns(sid)
    assert [t.ao_scaffolded for t in turns] == ["AO2"]


# -- Item 4: confidence-history captured at settlement with source ----------


@pytest.mark.asyncio
async def test_settlement_writes_confidence_history_with_source() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(session_id=sid, role="user", content="q")
    await store.append_turn(session_id=sid, role="tutor", content="a")
    await store.finalize_session(
        student_id="lilymay",
        session_id=sid,
        now=NOW,
        confidence_updates=[ConfidenceUpdate(topic_name="ambition", percentage=62)],
        misconceptions=[],
        aos_scaffolded=["AO2"],
        topic="ambition",
    )
    history = [h for h in store._confidence_history if h["student_id"] == "lilymay"]
    assert len(history) == 1
    assert history[0]["source"] == "session"
    assert history[0]["percentage"] == 62
    assert history[0]["session_id"] == sid


# -- Item 5: W2 achievements fire live through finalize_session -------------


@pytest.mark.asyncio
async def test_macbeth_master_banks_on_three_topics_at_80() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(session_id=sid, role="user", content="q")
    await store.append_turn(session_id=sid, role="tutor", content="a")
    result = await store.finalize_session(
        student_id="lilymay",
        session_id=sid,
        now=NOW,
        confidence_updates=[
            ConfidenceUpdate(topic_name="ambition", percentage=85),
            ConfidenceUpdate(topic_name="guilt", percentage=82),
            ConfidenceUpdate(topic_name="kingship", percentage=80),
        ],
        misconceptions=[],
        aos_scaffolded=["AO2"],
        topic="ambition",
    )
    unlocked = {a.id for a in result.decision.unlocked}
    assert "macbeth_master" in unlocked


@pytest.mark.asyncio
async def test_quote_champion_banks_on_ten_embedded_quotes() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(session_id=sid, role="user", content="q")
    await store.append_turn(
        session_id=sid, role="tutor", content="a", quotes_embedded=10
    )
    result = await store.finalize_session(
        student_id="lilymay",
        session_id=sid,
        now=NOW,
        confidence_updates=[],
        misconceptions=[],
        aos_scaffolded=[],
        topic="ambition",
    )
    assert "quote_champion" in {a.id for a in result.decision.unlocked}


@pytest.mark.asyncio
async def test_set_text_explorer_banks_on_three_distinct_texts() -> None:
    store = FakeStudentStore()
    store.add_student("lilymay")
    # Two prior ended sessions on distinct texts.
    store.add_ended_session(
        "lilymay", started_at=NOW - timedelta(days=2),
        last_activity=NOW - timedelta(days=2), text_name="a_christmas_carol",
    )
    store.add_ended_session(
        "lilymay", started_at=NOW - timedelta(days=1),
        last_activity=NOW - timedelta(days=1), text_name="an_inspector_calls",
    )
    record, _ = await store.create_session(
        student_id="lilymay", subject="english", topic="macbeth", text_name="macbeth"
    )
    await store.append_turn(session_id=record.session_id, role="user", content="q")
    result = await store.finalize_session(
        student_id="lilymay",
        session_id=record.session_id,
        now=NOW,
        confidence_updates=[],
        misconceptions=[],
        aos_scaffolded=[],
        topic="macbeth",
    )
    assert "set_text_explorer" in {a.id for a in result.decision.unlocked}


@pytest.mark.asyncio
async def test_six_ao_sampler_banks_when_one_session_covers_six_aos() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    for ao in ("AO1", "AO2", "AO3", "AO4", "AO5", "AO6"):
        await store.append_turn(
            session_id=sid, role="tutor", content=f"scaffold {ao}", ao_scaffolded=ao
        )
    result = await store.finalize_session(
        student_id="lilymay",
        session_id=sid,
        now=NOW,
        confidence_updates=[],
        misconceptions=[],
        aos_scaffolded=[],
        topic="macbeth",
    )
    assert "six_ao_sampler" in {a.id for a in result.decision.unlocked}


# -- Vacuous: a plain settlement banks no W2 achievement --------------------


@pytest.mark.asyncio
async def test_plain_settlement_banks_no_w2_achievement() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name=None)
    await store.append_turn(session_id=sid, role="user", content="q")
    await store.append_turn(session_id=sid, role="tutor", content="a")
    result = await store.finalize_session(
        student_id="lilymay",
        session_id=sid,
        now=NOW,
        confidence_updates=[ConfidenceUpdate(topic_name="ambition", percentage=55)],
        misconceptions=[],
        aos_scaffolded=[],
        topic="ambition",
    )
    w2_ids = {
        "macbeth_master", "poetry_pioneer", "poetry_progenitor",
        "christmas_carol_champion", "inspectors_apprentice", "jekyll_hyde_savant",
        "unseen_ready", "set_text_explorer", "genre_gatherer", "historical_horizon",
        "six_ao_sampler", "climbing", "breakthrough", "comparative_climber",
        "quote_champion", "quote_master", "no_weak_spots",
    }
    unlocked = {a.id for a in result.decision.unlocked}
    assert unlocked & w2_ids == set()


# -- Replay determinism with W2 signals -------------------------------------


@pytest.mark.asyncio
async def test_replay_reproduces_w2_unlocks() -> None:
    store = FakeStudentStore()
    sid = await _seed_active_session(store, text_name="macbeth")
    await store.append_turn(session_id=sid, role="user", content="q")
    await store.append_turn(
        session_id=sid, role="tutor", content="a", quotes_embedded=10
    )
    first = await store.finalize_session(
        student_id="lilymay", session_id=sid, now=NOW,
        confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="macbeth",
    )
    replay = await store.finalize_session(
        student_id="lilymay", session_id=sid, now=NOW + timedelta(minutes=5),
        confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="macbeth",
    )
    assert replay.replayed is True
    assert {a.id for a in first.decision.unlocked} == {
        a.id for a in replay.decision.unlocked
    }
