"""Stage 1 — ``GET /api/sessions/{id}/turns?since=`` route (binding §2.4).

Starlette TestClient over a fake SessionService (the ``test_app.py`` pattern) —
hermetic: no DB, no live model, no broker. Pins the envelope, the row shape's
byte-identity with ``resume_session``, the ``since`` semantics (row offset,
default 0, empty past the end), ownership/auth mapping, the ended-session
carve-out (never 410), and that the route is mounted unconditionally.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from study_tutor.knowledge.store.entities import SessionTurn
from study_tutor.session.errors import SessionForbidden, SessionNotFoundError
from study_tutor.session.service import ResumeResult, TurnsSinceResult

SESSION_ID = "sess-mirror-1"
STUDENT_ID = "test-student"
AUTH = {"Authorization": "Bearer token-test"}
# Deliberately microsecond-bearing + tz-aware: isoformat() must round-trip the
# same way on both routes.
T0 = datetime(2026, 7, 31, 10, 15, 0, 123456, tzinfo=timezone.utc)


# -------------------- Fixtures --------------------


@pytest.fixture
def fake_service():
    return AsyncMock()


@pytest.fixture
def fake_auth_config():
    from study_tutor.http.auth import HTTPAuthConfig, TableTokenResolver

    token_to_student = {"token-test": STUDENT_ID}
    return HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
    )


@pytest.fixture
def fake_student_store():
    store = AsyncMock()
    store.student_exists.return_value = True
    return store


@pytest.fixture
def test_client(fake_service, fake_auth_config, fake_student_store):
    """TestClient with NO voice config and NO dev flags — proving the route is
    always mounted, never feature-flagged."""
    from study_tutor.http.app import create_app

    app = create_app(
        service=fake_service,
        reply_fn=AsyncMock(),
        auth_config=fake_auth_config,
        student_store=fake_student_store,
    )
    return TestClient(app)


def _turns(count: int, start: int = 0) -> tuple[SessionTurn, ...]:
    return tuple(
        SessionTurn(
            session_id=SESSION_ID,
            turn_index=i,
            role="user" if i % 2 == 0 else "tutor",
            content=f"row-{i}",
            ts=T0 + timedelta(seconds=i),
        )
        for i in range(start, start + count)
    )


def _result(
    turns: tuple[SessionTurn, ...], total: int, status: str = "active"
) -> TurnsSinceResult:
    return TurnsSinceResult(
        session_id=SESSION_ID,
        student_id=STUDENT_ID,
        status=status,  # type: ignore[arg-type]
        turns=turns,
        total=total,
    )


# -------------------- Envelope + row shape --------------------


def test_envelope_is_exactly_the_four_bound_fields(test_client, fake_service):
    """200 body keys are exactly {session_id, status, turns, next} (§2.4)."""
    fake_service.turns_since.return_value = _result(_turns(2, start=2), total=4)

    response = test_client.get(
        f"/api/sessions/{SESSION_ID}/turns?since=2", headers=AUTH
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"session_id", "status", "turns", "next"}
    assert data["session_id"] == SESSION_ID
    assert data["status"] == "active"
    assert data["next"] == 4
    assert [t["content"] for t in data["turns"]] == ["row-2", "row-3"]


def test_row_keys_are_exactly_role_content_ts(test_client, fake_service):
    fake_service.turns_since.return_value = _result(_turns(2), total=2)

    data = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH).json()

    assert data["turns"]
    for row in data["turns"]:
        assert set(row) == {"role", "content", "ts"}


def test_ts_formatting_is_byte_identical_to_resume(
    test_client, fake_service
):
    """The app reuses its resume parser: same datetime ⇒ same ``ts`` string."""
    rows = _turns(2)
    fake_service.turns_since.return_value = _result(rows, total=2)
    fake_service.resume_session.return_value = ResumeResult(
        session_id=SESSION_ID,
        student_id=STUDENT_ID,
        status="active",
        turns=rows,
    )

    turns_rows = test_client.get(
        f"/api/sessions/{SESSION_ID}/turns", headers=AUTH
    ).json()["turns"]
    resume_rows = test_client.get(
        f"/api/sessions/{SESSION_ID}/resume", headers=AUTH
    ).json()["turns"]

    assert turns_rows == resume_rows


# -------------------- since semantics --------------------


def test_since_defaults_to_zero(test_client, fake_service):
    """No query param ⇒ the service is asked for the whole transcript."""
    fake_service.turns_since.return_value = _result(_turns(4), total=4)

    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH)

    assert response.status_code == 200
    assert len(response.json()["turns"]) == 4
    assert fake_service.turns_since.await_args.kwargs["since"] == 0


def test_since_is_passed_through_as_an_int_row_offset(test_client, fake_service):
    fake_service.turns_since.return_value = _result(_turns(1, start=5), total=6)

    test_client.get(f"/api/sessions/{SESSION_ID}/turns?since=5", headers=AUTH)

    kwargs = fake_service.turns_since.await_args.kwargs
    assert kwargs["since"] == 5
    assert kwargs["session_id"] == SESSION_ID
    # Ownership is the token-resolved id, never client-asserted.
    assert kwargs["student_id"] == STUDENT_ID


def test_since_equal_to_total_returns_empty_list_not_an_error(
    test_client, fake_service
):
    fake_service.turns_since.return_value = _result((), total=4)

    response = test_client.get(
        f"/api/sessions/{SESSION_ID}/turns?since=4", headers=AUTH
    )

    assert response.status_code == 200
    data = response.json()
    assert data["turns"] == []
    assert data["next"] == 4


def test_next_is_the_raw_row_count_not_pairs(test_client, fake_service):
    """``next`` feeds the next poll's ``since`` — it must be raw rows, never the
    ``turn_count // 2`` pairs number ``status``/``list`` project."""
    fake_service.turns_since.return_value = _result(_turns(6), total=6)

    data = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH).json()

    assert data["next"] == 6
    assert len(data["turns"]) == 6


# -------------------- Validation (§4.2 — no error_type) --------------------


@pytest.mark.parametrize("bad", ["abc", "-1", "1.5", ""])
def test_bad_since_is_400_without_error_type(test_client, fake_service, bad):
    response = test_client.get(
        f"/api/sessions/{SESSION_ID}/turns?since={bad}", headers=AUTH
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"].startswith("Validation failed: ")
    assert "error_type" not in data
    fake_service.turns_since.assert_not_awaited()


# -------------------- Auth / ownership --------------------


def test_missing_token_is_401(test_client, fake_service):
    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns")

    assert response.status_code == 401
    assert response.json()["error_type"] == "Unauthenticated"
    fake_service.turns_since.assert_not_awaited()


def test_invalid_token_is_401(test_client, fake_service):
    response = test_client.get(
        f"/api/sessions/{SESSION_ID}/turns",
        headers={"Authorization": "Bearer token-bogus"},
    )

    assert response.status_code == 401
    assert response.json()["error_type"] == "Unauthenticated"


def test_non_owner_is_403(test_client, fake_service):
    fake_service.turns_since.side_effect = SessionForbidden("not yours")

    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH)

    assert response.status_code == 403
    assert response.json()["error_type"] == "SessionForbidden"


def test_unknown_session_is_404(test_client, fake_service):
    fake_service.turns_since.side_effect = SessionNotFoundError(SESSION_ID)

    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH)

    assert response.status_code == 404
    assert response.json()["error_type"] == "SessionNotFoundError"


# -------------------- Ended sessions + mounting --------------------


def test_ended_session_returns_200_with_rows_never_410(test_client, fake_service):
    """The poll survives the active→ended transition — 410 is impossible here."""
    fake_service.turns_since.return_value = _result(
        _turns(4), total=4, status="ended"
    )

    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"
    assert len(data["turns"]) == 4
    assert data["next"] == 4


def test_route_is_mounted_without_any_feature_flag(test_client, fake_service):
    """The app under test has no voice config and no dev_reset — the route must
    still exist (a flag-gated route would 404 here)."""
    fake_service.turns_since.return_value = _result((), total=0)

    response = test_client.get(f"/api/sessions/{SESSION_ID}/turns", headers=AUTH)

    assert response.status_code == 200
