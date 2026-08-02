"""Service-boundary subject normalisation (ADR-ARCH-032 D4).

An omitted/empty ``subject`` on ``start_session`` normalises to the
shared default — the row never persists ``''``, so ``(student, subject)``
resume keying and subject-scoped retrieval always see a real subject.
"""

from study_tutor.session.service import SUBJECT_DEFAULT, SessionService
from tests.unit.knowledge.store.fakes import FakeStudentStore


def _service() -> tuple[SessionService, FakeStudentStore]:
    store = FakeStudentStore()
    store.add_student(student_id="lilymay", year_group=11)
    return SessionService(store=store), store


def test_subject_default_constant_is_the_contract_value() -> None:
    assert SUBJECT_DEFAULT == "english"


async def test_empty_subject_normalises_to_default_on_start() -> None:
    svc, store = _service()

    result = await svc.start_session(student_id="lilymay", subject="")

    assert result.subject == SUBJECT_DEFAULT
    record = await store.get_session(result.session_id)
    assert record is not None
    assert record.subject == SUBJECT_DEFAULT


async def test_explicit_subject_is_preserved() -> None:
    svc, store = _service()

    result = await svc.start_session(student_id="lilymay", subject="french")

    assert result.subject == "french"
    record = await store.get_session(result.session_id)
    assert record is not None
    assert record.subject == "french"


async def test_normalised_subject_shares_the_resume_key() -> None:
    """A ''-started session and an 'english'-started resume are ONE session."""
    svc, _ = _service()

    first = await svc.start_session(student_id="lilymay", subject="")
    second = await svc.start_session(
        student_id="lilymay",
        subject=SUBJECT_DEFAULT,
        resume_if_active=True,
    )

    assert second.resumed
    assert second.session_id == first.session_id
