"""Service-level capture wiring (S-E4): start-time text_name + per-turn signals.

The service derives the canonical ``text_name`` at start and forwards the
per-turn capture signals (``ao_scaffolded`` / ``quotes_embedded``) off the reply
metadata into ``append_turn`` — the transport-neutral plumbing (D14).
"""
from __future__ import annotations

from study_tutor.session.service import SessionService, TutorReply
from tests.unit.knowledge.store.fakes import FakeStudentStore


def _store() -> FakeStudentStore:
    store = FakeStudentStore()
    store.add_student(student_id="lilymay", year_group=9)
    return store


async def test_start_session_derives_and_persists_text_name() -> None:
    store = _store()
    svc = SessionService(store=store)
    start = await svc.start_session(
        student_id="lilymay", subject="lilymay", topic="Macbeth"
    )
    record = await store.get_session(start.session_id)
    assert record is not None
    assert record.text_name == "macbeth"


async def test_start_session_no_known_text_leaves_text_name_none() -> None:
    store = _store()
    svc = SessionService(store=store)
    start = await svc.start_session(
        student_id="lilymay", subject="lilymay", topic="metaphor identification"
    )
    record = await store.get_session(start.session_id)
    assert record is not None and record.text_name is None


async def test_turn_forwards_per_turn_capture_signals() -> None:
    store = _store()
    svc = SessionService(store=store)
    start = await svc.start_session(
        student_id="lilymay", subject="lilymay", topic="Macbeth"
    )

    async def reply_fn(user_message: str) -> TutorReply:
        return TutorReply(
            response="tutor reply",
            metadata={"ao_scaffolded": "AO2", "quotes_embedded": 3},
        )

    await svc.turn(
        student_id="lilymay",
        session_id=start.session_id,
        user_message="Analyse the dagger soliloquy",
        reply_fn=reply_fn,
    )

    # The session counter accumulated the tutor turn's quotes.
    record = await store.get_session(start.session_id)
    assert record is not None and record.quotes_embedded == 3
    # The tutor turn carries the observed AO; the user turn carries none.
    turns = await store.get_turns(start.session_id)
    by_role = {t.role: t.ao_scaffolded for t in turns}
    assert by_role["tutor"] == "AO2"
    assert by_role["user"] is None


async def test_turn_without_metadata_persists_no_capture_signal() -> None:
    store = _store()
    svc = SessionService(store=store)
    start = await svc.start_session(
        student_id="lilymay", subject="lilymay", topic="Macbeth"
    )

    async def reply_fn(user_message: str) -> TutorReply:
        return TutorReply(response="tutor reply")  # no metadata

    await svc.turn(
        student_id="lilymay",
        session_id=start.session_id,
        user_message="hi",
        reply_fn=reply_fn,
    )
    record = await store.get_session(start.session_id)
    assert record is not None and record.quotes_embedded == 0
    turns = await store.get_turns(start.session_id)
    assert all(t.ao_scaffolded is None for t in turns)
