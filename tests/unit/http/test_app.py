"""Unit tests for HTTP app routes (TASK-APP1-03).

Tests the six session endpoints with starlette TestClient over a fake SessionService.
Verifies route paths/methods, error mapping, guard order, and DTO projection.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from starlette.testclient import TestClient

from study_tutor.session.errors import (
    SessionNotFoundError,
    SessionEnded,
    SessionForbidden,
)
from study_tutor.session.service import (
    StartSessionResult,
    ResumeResult,
    TurnResult,
    SessionStatusView,
    EndSessionResult,
)
from study_tutor.knowledge.store.entities import SessionRecord, SessionTurn

# -------------------- Fixtures --------------------


@pytest.fixture
def fake_service():
    """Mock SessionService for testing route logic without DB."""
    return AsyncMock()


@pytest.fixture
def fake_reply_fn():
    """Mock reply_fn for turn endpoint."""
    return AsyncMock()


@pytest.fixture
def fake_auth_config():
    """Mock HTTPAuthConfig with test token."""
    from study_tutor.http.auth import HTTPAuthConfig

    return HTTPAuthConfig(
        token_to_student={"token-test": "test-student"},
        dev_reset=False,
    )


@pytest.fixture
def fake_student_store():
    """Mock StudentStore for auth layer."""
    store = AsyncMock()
    store.student_exists.return_value = True
    return store


@pytest.fixture
def test_client(fake_service, fake_reply_fn, fake_auth_config, fake_student_store):
    """TestClient with injected fake dependencies."""
    from study_tutor.http.app import create_app

    app = create_app(
        service=fake_service,
        reply_fn=fake_reply_fn,
        auth_config=fake_auth_config,
        student_store=fake_student_store,
    )
    return TestClient(app)


# -------------------- start_session tests --------------------


def test_start_session_happy_path(test_client, fake_service):
    """AC-001: POST /api/sessions/start creates new session."""
    fake_service.start_session.return_value = StartSessionResult(
        session_id="sess-123",
        student_id="test-student",
        subject="English",
        topic="Macbeth",
        resumed=False,
        turns=None,
    )

    response = test_client.post(
        "/api/sessions/start",
        json={"subject": "English", "topic": "Macbeth"},
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-123"
    assert data["student_id"] == "test-student"
    assert data["resumed"] is False
    assert data.get("turns") is None


def test_start_session_resume_if_active(test_client, fake_service):
    """AC-005: start_session with resume_if_active returns existing session + turns."""
    fake_service.start_session.return_value = StartSessionResult(
        session_id="sess-old",
        student_id="test-student",
        subject="English",
        topic="Macbeth",
        resumed=True,
        turns=(
            SessionTurn(
                session_id="sess-old",
                role="user",
                content="Hello",
                ts=datetime.now(),
                turn_index=0,
            ),
            SessionTurn(
                session_id="sess-old",
                role="tutor",
                content="Hi!",
                ts=datetime.now(),
                turn_index=1,
            ),
        ),
    )

    response = test_client.post(
        "/api/sessions/start",
        json={"subject": "English", "resume_if_active": True},
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["resumed"] is True
    assert data["turns"] is not None
    assert len(data["turns"]) == 2


def test_start_session_missing_auth(test_client):
    """AC-002: Missing Authorization header → 401 Unauthenticated."""
    response = test_client.post(
        "/api/sessions/start",
        json={"subject": "English"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["error_type"] == "Unauthenticated"
    assert "error" in data


def test_start_session_malformed_body(test_client):
    """AC-004: Malformed request body → 400 validation error (no error_type)."""
    response = test_client.post(
        "/api/sessions/start",
        json="not-a-dict",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "error_type" not in data  # Transport-level error, not domain error


# -------------------- list_sessions tests --------------------


def test_list_sessions_happy_path(test_client, fake_service):
    """AC-001: GET /api/sessions lists caller's sessions."""
    fake_service.list_sessions.return_value = [
        SessionRecord(
            session_id="sess-1",
            student_id="test-student",
            subject="English",
            topic="Macbeth",
            status="active",
            turn_count=5,
            started_at=datetime(2026, 7, 5, 10, 0, 0),
            last_activity=datetime(2026, 7, 5, 10, 30, 0),
        ),
    ]

    response = test_client.get(
        "/api/sessions",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["session_id"] == "sess-1"
    assert data[0]["status"] == "active"
    assert data[0]["turn_count"] == 5


def test_list_sessions_with_filters(test_client, fake_service):
    """AC-001: list_sessions accepts status filter and limit."""
    fake_service.list_sessions.return_value = []

    response = test_client.get(
        "/api/sessions?status=active&limit=10",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    fake_service.list_sessions.assert_called_once_with(
        student_id="test-student",
        status="active",
        limit=10,
    )


# -------------------- resume_session tests --------------------


def test_resume_session_happy_path(test_client, fake_service):
    """AC-001: GET /api/sessions/{id}/resume returns session + transcript."""
    fake_service.resume_session.return_value = ResumeResult(
        session_id="sess-123",
        student_id="test-student",
        status="active",
        turns=(
            SessionTurn(
                session_id="sess-123",
                role="user",
                content="Hello",
                ts=datetime.now(),
                turn_index=0,
            ),
        ),
    )

    response = test_client.get(
        "/api/sessions/sess-123/resume",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-123"
    assert len(data["turns"]) == 1


def test_resume_session_not_found(test_client, fake_service):
    """AC-002: SessionNotFoundError → 404."""
    fake_service.resume_session.side_effect = SessionNotFoundError("sess-999")

    response = test_client.get(
        "/api/sessions/sess-999/resume",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error_type"] == "SessionNotFoundError"


def test_resume_session_forbidden(test_client, fake_service):
    """AC-002: SessionForbidden → 403."""
    fake_service.resume_session.side_effect = SessionForbidden("Not your session")

    response = test_client.get(
        "/api/sessions/sess-other/resume",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error_type"] == "SessionForbidden"


def test_resume_session_ended(test_client, fake_service):
    """AC-002: SessionEnded → 410."""
    fake_service.resume_session.side_effect = SessionEnded("Session has ended")

    response = test_client.get(
        "/api/sessions/sess-ended/resume",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 410
    data = response.json()
    assert data["error_type"] == "SessionEnded"


# -------------------- turn tests --------------------


def test_turn_happy_path(test_client, fake_service):
    """AC-001: POST /api/sessions/{id}/turn processes turn and returns tutor response."""
    fake_service.turn.return_value = TurnResult(
        tutor_response="That's a great question!",
        turn_index=2,
    )

    response = test_client.post(
        "/api/sessions/sess-123/turn",
        json={"user_message": "What is Macbeth about?"},
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tutor_response"] == "That's a great question!"


def test_turn_session_ended(test_client, fake_service):
    """AC-002: Turn on ended session → 410."""
    fake_service.turn.side_effect = SessionEnded("Cannot turn on ended session")

    response = test_client.post(
        "/api/sessions/sess-ended/turn",
        json={"user_message": "Hello"},
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 410
    data = response.json()
    assert data["error_type"] == "SessionEnded"


# -------------------- session_status tests --------------------


def test_session_status_happy_path(test_client, fake_service):
    """AC-001: GET /api/sessions/{id}/status returns session metadata."""
    fake_service.session_status.return_value = SessionStatusView(
        session_id="sess-123",
        student_id="test-student",
        status="active",
        turn_count=5,
        started_at=datetime(2026, 7, 5, 10, 0, 0),
        last_activity=datetime(2026, 7, 5, 10, 30, 0),
        resumable=True,
    )

    response = test_client.get(
        "/api/sessions/sess-123/status",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-123"
    assert data["status"] == "active"
    assert data["resumable"] is True


def test_session_status_allows_ended(test_client, fake_service):
    """AC-002: session_status reads ended sessions (unlike other verbs)."""
    fake_service.session_status.return_value = SessionStatusView(
        session_id="sess-ended",
        student_id="test-student",
        status="ended",
        turn_count=10,
        started_at=datetime(2026, 7, 5, 10, 0, 0),
        last_activity=datetime(2026, 7, 5, 11, 0, 0),
        resumable=False,
    )

    response = test_client.get(
        "/api/sessions/sess-ended/status",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ended"
    assert data["resumable"] is False


# -------------------- end_session tests --------------------


def test_end_session_happy_path(test_client, fake_service):
    """AC-001: POST /api/sessions/{id}/end transitions to ended."""
    fake_service.end_session.return_value = EndSessionResult(
        session_id="sess-123",
        status="ended",
    )

    response = test_client.post(
        "/api/sessions/sess-123/end",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-123"
    assert data["status"] == "ended"


def test_end_session_already_ended(test_client, fake_service):
    """AC-002: Ending an already-ended session → 410."""
    fake_service.end_session.side_effect = SessionEnded("Already ended")

    response = test_client.post(
        "/api/sessions/sess-ended/end",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 410


# -------------------- Guard order tests --------------------


def test_forbidden_wins_over_ended(test_client, fake_service):
    """AC-003: Ownership refusal (403) wins over ended-state (410) for other student's ended session."""
    # This tests the guard order: the service checks ownership first, so SessionForbidden
    # is raised before checking if the session is ended.
    fake_service.session_status.side_effect = SessionForbidden("Not your session")

    response = test_client.get(
        "/api/sessions/sess-other-ended/status",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error_type"] == "SessionForbidden"


# -------------------- Error handling tests --------------------


def test_unexpected_exception_500(test_client, fake_service):
    """AC-004: Unexpected exception → 500 with generic error (no error_type)."""
    fake_service.start_session.side_effect = RuntimeError("Database explosion")

    response = test_client.post(
        "/api/sessions/start",
        json={"subject": "English"},
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"] == "Internal server error"
    assert "error_type" not in data  # Not a domain error


# -------------------- Seam test --------------------


@pytest.mark.seam
@pytest.mark.integration_contract("API-session-http-binding.md")
def test_api_session_http_binding_md_format():
    """Verify served routes match the binding doc.

    Contract: every route path, method, and status-per-error_type is fixed by
    docs/design/contracts/API-session-http-binding.md.
    Producer: TASK-APP1-01
    """
    from pathlib import Path

    doc = Path("docs/design/contracts/API-session-http-binding.md").read_text()
    assert doc, "binding doc must exist and be non-empty"

    # Verify expected route paths are documented
    assert "/api/sessions/start" in doc
    assert "/api/sessions" in doc
    assert "/api/sessions/{session_id}/resume" in doc
    assert "/api/sessions/{session_id}/turn" in doc
    assert "/api/sessions/{session_id}/status" in doc
    assert "/api/sessions/{session_id}/end" in doc

    # Verify error status codes are documented
    assert "404" in doc  # SessionNotFoundError
    assert "410" in doc  # SessionEnded
    assert "403" in doc  # SessionForbidden
    assert "401" in doc  # Unauthenticated
