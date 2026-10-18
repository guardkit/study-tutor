"""``SessionService`` maps a busy/refused tutor model to ``TutorBusy``.

Design ``docs/design/tutor-busy-and-history-repair-2026-10-18.md`` F2.2:
``turn`` raises ``TutorBusy`` (chained) when the reply raises an
``LLMProviderError`` with status 429/502/503 — also when it is wrapped —
and any other failure propagates unchanged. ``turn_stream`` yields the
in-band ``TutorBusy`` error event instead of ``generation_failed``. In both,
only the learner row is persisted.
"""
from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest

from study_tutor.llm.client import LLMProviderError
from study_tutor.session.errors import TutorBusy
from study_tutor.session.service import SessionService
from tests.unit.session.test_turn_stream import FakeStore


def _service() -> tuple[SessionService, FakeStore]:
    record = MagicMock(session_id="sess1", student_id="student1", status="active")
    store = FakeStore(calls=[], session_record=record)
    return SessionService(store=store), store


def _provider_error(status: int | None) -> LLMProviderError:
    return LLMProviderError(f"upstream {status}", status_code=status)


def _raising_reply(exc: BaseException):
    async def reply_fn(msg: str):
        raise exc

    return reply_fn


def _wrapped(status: int) -> RuntimeError:
    """A RuntimeError raised ``from`` the provider error (orchestrator wrap)."""
    try:
        try:
            raise _provider_error(status)
        except LLMProviderError as inner:
            raise RuntimeError("orchestrator wrapped it") from inner
    except RuntimeError as outer:
        return outer


async def _turn(service: SessionService, reply_fn) -> None:
    await service.turn(
        student_id="student1",
        session_id="sess1",
        user_message="hello",
        reply_fn=reply_fn,
    )


@pytest.mark.parametrize("status", [429, 502, 503])
async def test_turn_raises_tutor_busy_for_busy_status(status: int) -> None:
    service, store = _service()
    exc = _provider_error(status)

    with pytest.raises(TutorBusy) as exc_info:
        await _turn(service, _raising_reply(exc))

    assert str(exc_info.value) == TutorBusy.MESSAGE
    assert exc_info.value.__cause__ is exc
    assert store.calls == ["append_turn(user)"]


@pytest.mark.parametrize("status", [429, 502, 503])
async def test_turn_raises_tutor_busy_when_provider_error_is_wrapped(
    status: int,
) -> None:
    service, store = _service()

    with pytest.raises(TutorBusy):
        await _turn(service, _raising_reply(_wrapped(status)))

    assert store.calls == ["append_turn(user)"]


@pytest.mark.parametrize("status", [400, 500, None])
async def test_turn_propagates_non_busy_provider_error(status: int | None) -> None:
    service, store = _service()
    exc = _provider_error(status)

    with pytest.raises(LLMProviderError) as exc_info:
        await _turn(service, _raising_reply(exc))

    assert exc_info.value is exc
    assert not isinstance(exc_info.value, TutorBusy)
    assert store.calls == ["append_turn(user)"]


async def _collect_stream(service: SessionService, exc: BaseException) -> list:
    async def reply_stream_fn(msg: str) -> AsyncIterator[str]:
        raise exc
        yield  # pragma: no cover — makes this an async generator

    return [
        event
        async for event in service.turn_stream(
            student_id="student1",
            session_id="sess1",
            user_message="hello",
            reply_stream_fn=reply_stream_fn,
        )
    ]


@pytest.mark.parametrize("status", [429, 502, 503])
async def test_turn_stream_yields_tutor_busy_event(status: int) -> None:
    service, store = _service()

    events = await _collect_stream(service, _provider_error(status))

    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "TutorBusy"
    assert events[0].error == TutorBusy.MESSAGE
    assert store.calls == ["append_turn(user)"]


async def test_turn_stream_non_busy_status_is_generation_failed() -> None:
    service, store = _service()

    events = await _collect_stream(service, _provider_error(400))

    assert [e.type for e in events] == ["error"]
    assert events[0].error_type == "generation_failed"
    assert store.calls == ["append_turn(user)"]
