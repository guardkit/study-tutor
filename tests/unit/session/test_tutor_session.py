import pytest

from study_tutor.session.tutor_session import (
    SessionNotFoundError,
    SessionStore,
    TutorSession,
    TutorTurn,
    get_default_store,
)


def test_create_append_get_end_roundtrip() -> None:
    store = SessionStore()

    session = store.create(subject="English Literature", topic="Macbeth")
    assert isinstance(session, TutorSession)
    assert session.subject == "English Literature"
    assert session.topic == "Macbeth"
    assert session.status == "active"
    assert session.turns == []
    # UUID4 string (36 chars with dashes)
    assert len(session.session_id) == 36 and session.session_id.count("-") == 4

    store.append_turn(session.session_id, "user", "What is the dagger speech?")
    store.append_turn(session.session_id, "tutor", "Act 2, Scene 1 — Macbeth hallucinates a dagger.")

    fetched = store.get(session.session_id)
    assert fetched is session
    assert len(fetched.turns) == 2
    assert fetched.turns[0] == TutorTurn(
        role="user",
        content="What is the dagger speech?",
        timestamp=fetched.turns[0].timestamp,
    )
    assert fetched.turns[1].role == "tutor"

    assert store.list_active() == [session.session_id]

    store.end(session.session_id)
    assert store.get(session.session_id).status == "ended"
    assert store.list_active() == []


def test_get_missing_session_raises() -> None:
    store = SessionStore()
    with pytest.raises(SessionNotFoundError):
        store.get("does-not-exist")


def test_append_turn_on_missing_session_raises() -> None:
    store = SessionStore()
    with pytest.raises(SessionNotFoundError):
        store.append_turn("nope", "user", "hi")


def test_default_store_is_singleton() -> None:
    assert get_default_store() is get_default_store()


def test_unique_session_ids() -> None:
    store = SessionStore()
    ids = {store.create("English", None).session_id for _ in range(5)}
    assert len(ids) == 5
