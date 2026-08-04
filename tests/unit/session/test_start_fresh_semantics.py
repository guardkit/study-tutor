"""Server half of the ruled (b) start-fresh semantics (Rich, 2026-08-04).

``start_session(resume_if_active=False)`` against an active
``(student, subject)`` match ENDS it and creates fresh — never a second
active — so one-active holds by construction (the invariant D8 cross-device
pickup relies on). The implicit end rides the real ``end_session`` path, so
the abandoned session SETTLES rather than losing its XP to a bare status
flip. Mirrors the app fake's two pins
(``app/test/unit/fake_start_fresh_semantics_test.dart``) at the service
level — fake and server agree by test, not by hope. The store-level
backstop is the partial unique index (rev 346cd366b66e).
"""

from study_tutor.session.service import SessionService
from tests.unit.knowledge.store.fakes import FakeStudentStore


def _service() -> tuple[SessionService, FakeStudentStore]:
    store = FakeStudentStore()
    store.add_student(student_id="lilymay", year_group=11)
    return SessionService(store=store), store


async def test_start_fresh_against_active_match_ends_it_and_creates_fresh() -> None:
    svc, store = _service()
    first = await svc.start_session(
        student_id="lilymay", subject="english", topic="macbeth"
    )
    await store.append_turn(
        session_id=first.session_id, role="user", content="what is a metaphor?"
    )
    await store.append_turn(
        session_id=first.session_id, role="tutor", content="A comparison..."
    )

    second = await svc.start_session(student_id="lilymay", subject="english")

    assert second.resumed is False
    assert second.session_id != first.session_id

    active = await store.list_sessions("lilymay", status="active")
    assert len(active) == 1, (
        "one-active by construction — the invariant D8 cross-device pickup"
        " relies on"
    )
    assert active[0].session_id == second.session_id

    old = await store.get_session(first.session_id)
    assert old is not None
    assert old.status == "ended", "the previous active was ENDED, not orphaned"


async def test_start_fresh_implicit_end_settles() -> None:
    """The implicit end rides the real end path: ``settled_at`` is stamped by
    the finalize transaction (a bare status flip would leave it NULL and the
    abandoned session's XP unbanked until the sweep)."""
    svc, store = _service()
    first = await svc.start_session(student_id="lilymay", subject="english")

    await svc.start_session(student_id="lilymay", subject="english")

    assert store._sessions[first.session_id]["settled_at"] is not None


async def test_start_fresh_other_subject_untouched() -> None:
    svc, store = _service()
    english = await svc.start_session(
        student_id="lilymay", subject="english", topic="macbeth"
    )

    await svc.start_session(student_id="lilymay", subject="french")

    active = await store.list_sessions("lilymay", status="active")
    assert len(active) == 2, (
        "the one-active invariant is per (student, subject)"
    )
    assert english.session_id in {s.session_id for s in active}


async def test_start_fresh_other_student_untouched() -> None:
    svc, store = _service()
    store.add_student(student_id="alex", year_group=9)
    lilymay = await svc.start_session(student_id="lilymay", subject="english")

    await svc.start_session(student_id="alex", subject="english")

    active = await store.list_sessions("lilymay", status="active")
    assert [s.session_id for s in active] == [lilymay.session_id]


async def test_start_fresh_with_no_active_match_is_a_plain_create() -> None:
    svc, store = _service()

    result = await svc.start_session(student_id="lilymay", subject="english")

    assert result.resumed is False
    active = await store.list_sessions("lilymay", status="active")
    assert [s.session_id for s in active] == [result.session_id]


async def test_start_fresh_sweeps_all_stray_actives_not_just_the_newest() -> None:
    """Pre-index strays: TWO active same-key rows (seeded at the store,
    below the service's normalisation) are BOTH ended by one fresh start —
    ending only the newest would leave a stray the backstop index can't
    exist to catch during the pre-migration window."""
    svc, store = _service()
    stray_a, _ = await store.create_session(
        student_id="lilymay", subject="english"
    )
    stray_b, _ = await store.create_session(
        student_id="lilymay", subject="english"
    )

    result = await svc.start_session(student_id="lilymay", subject="english")

    active = await store.list_sessions("lilymay", status="active")
    assert [s.session_id for s in active] == [result.session_id]
    for stray in (stray_a, stray_b):
        record = await store.get_session(stray.session_id)
        assert record is not None and record.status == "ended"


async def test_start_fresh_ends_legacy_empty_subject_active_row() -> None:
    """Pre-ADR-032 rows can carry subject='' (semantically english). The
    sweep matches on the normalised key, so a default-subject fresh start
    ends such a row rather than leaving a logical double-active the
    partial index (keyed on the raw column) can never fire on."""
    svc, store = _service()
    legacy, _ = await store.create_session(student_id="lilymay", subject="")

    result = await svc.start_session(student_id="lilymay", subject="")

    active = await store.list_sessions("lilymay", status="active")
    assert [s.session_id for s in active] == [result.session_id]
    record = await store.get_session(legacy.session_id)
    assert record is not None and record.status == "ended"
