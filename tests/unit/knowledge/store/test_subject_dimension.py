"""The subject dimension on mastery surfaces (ADR-ARCH-032 / study-room §14).

Pins, against the fake store (whose behaviour mirrors PostgresStudentStore):

* settlement banks confidence/history/misconception writes under the
  SESSION row's subject — the session is authoritative;
* the same topic name carries an independent confidence per subject
  (the widened (student, subject, topic) key);
* ``get_topic_confidences`` filters by subject when asked and returns
  everything when not (whole-student consumers unchanged);
* a session row carrying a pre-normalisation ``''`` subject banks its
  mastery writes under the default, never under ``''``.
"""

from datetime import datetime, timedelta, timezone

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from tests.unit.knowledge.store.fakes import FakeStudentStore


def _store() -> FakeStudentStore:
    store = FakeStudentStore()
    store.add_student(student_id="lilymay", year_group=11)
    return store


def _add_active_session(
    store: FakeStudentStore, session_id: str, subject: str
) -> None:
    started = datetime.now(timezone.utc) - timedelta(minutes=30)
    store._sessions[session_id] = {
        "student_id": "lilymay",
        "subject": subject,
        "topic": "Macbeth",
        "status": "active",
        "started_at": started,
        "last_activity": started,
        "turn_count": 2,
        "aos_scaffolded": ["AO1"],
    }


async def test_finalize_banks_mastery_writes_under_the_sessions_subject() -> None:
    store = _store()
    _add_active_session(store, "s-french", "french")

    await store.finalize_session(
        student_id="lilymay",
        session_id="s-french",
        now=datetime.now(timezone.utc),
        confidence_updates=[
            ConfidenceUpdate(topic_name="Subjonctif", percentage=60)
        ],
        misconceptions=[],
        aos_scaffolded=["AO1"],
        topic="Subjonctif",
    )

    assert ("lilymay", "french", "Subjonctif") in store._confidences
    assert store._confidences[("lilymay", "french", "Subjonctif")]["subject"] == "french"
    history = [h for h in store._confidence_history if h["session_id"] == "s-french"]
    assert history and all(h["subject"] == "french" for h in history)


async def test_same_topic_name_is_independent_per_subject() -> None:
    store = _store()
    await store.apply_confidence_update(
        student_id="lilymay",
        update=ConfidenceUpdate(topic_name="Context", percentage=80),
    )
    await store.apply_confidence_update(
        student_id="lilymay",
        update=ConfidenceUpdate(
            topic_name="Context", percentage=30, subject="history"
        ),
    )

    english = await store.get_topic_confidences("lilymay", subject="english")
    history_subject = await store.get_topic_confidences("lilymay", subject="history")
    everything = await store.get_topic_confidences("lilymay")

    assert [(c.topic_ref, c.percentage) for c in english] == [("Context", 80)]
    assert [(c.topic_ref, c.percentage) for c in history_subject] == [("Context", 30)]
    assert len(everything) == 2  # None = whole-student, both subjects


async def test_unfiltered_read_is_the_whole_student_default() -> None:
    store = _store()
    store.add_topic_confidence("lilymay", "Macbeth", 70)
    store.add_topic_confidence("lilymay", "Subjonctif", 40, subject="french")

    assert len(await store.get_topic_confidences("lilymay")) == 2
    assert len(await store.get_topic_confidences("lilymay", subject="french")) == 1
    assert len(await store.get_topic_confidences("lilymay", subject="chemistry")) == 0


async def test_empty_subject_session_banks_under_the_default() -> None:
    """A pre-normalisation '' session row never banks mastery rows under ''."""
    store = _store()
    _add_active_session(store, "s-legacy", "")

    await store.finalize_session(
        student_id="lilymay",
        session_id="s-legacy",
        now=datetime.now(timezone.utc),
        confidence_updates=[
            ConfidenceUpdate(topic_name="Macbeth", percentage=55)
        ],
        misconceptions=[],
        aos_scaffolded=["AO1"],
        topic="Macbeth",
    )

    assert ("lilymay", "english", "Macbeth") in store._confidences
    assert not any(key[1] == "" for key in store._confidences)
