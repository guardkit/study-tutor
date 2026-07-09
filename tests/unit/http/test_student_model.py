"""Unit tests for GET /api/student-model (FEAT-VOICE-004 R05).

Drives the real ``FakeStudentStore`` through the auth layer via Starlette's
TestClient, so the handler, auth guard, store read, and projection are exercised
end-to-end. Covers: auth (401 unseeded / rejected bearer), happy real
projection, seeded-but-empty → data_available:false, malformed → 400.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from tests.unit.knowledge.store.fakes import FakeStudentStore

UTC = timezone.utc


@pytest.fixture
def auth_config() -> HTTPAuthConfig:
    # token-ghost resolves to a student that is never seeded (ASSUM-001 case).
    return HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay", "token-ghost": "ghost"},
        dev_reset=False,
    )


@pytest.fixture
def store() -> FakeStudentStore:
    s = FakeStudentStore()
    s.add_student("lilymay", name="Lily May", year_group=10, target_grade="7")
    return s


@pytest.fixture
def client(auth_config: HTTPAuthConfig, store: FakeStudentStore) -> TestClient:
    app = create_app(
        service=AsyncMock(),
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=store,
    )
    return TestClient(app)


# -- Auth --------------------------------------------------------------------


def test_missing_authorization_is_401(client: TestClient) -> None:
    resp = client.get("/api/student-model?subject=english")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_rejected_bearer_is_401(client: TestClient) -> None:
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_unseeded_student_is_401_not_500(client: TestClient) -> None:
    # Valid token, but 'ghost' has no StudentStore identity row (ASSUM-001).
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer token-ghost"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


# -- Malformed ---------------------------------------------------------------


def test_missing_subject_is_400_without_error_type(client: TestClient) -> None:
    resp = client.get(
        "/api/student-model",
        headers={"Authorization": "Bearer token-lilymay"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
    assert "error_type" not in body  # transport-level (§4.2)


def test_wrong_method_is_405(client: TestClient) -> None:
    resp = client.post(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer token-lilymay"},
    )
    assert resp.status_code == 405


# -- Happy projection --------------------------------------------------------


def test_happy_projection_returns_real_gamification(
    client: TestClient, store: FakeStudentStore
) -> None:
    now = datetime.now(UTC)
    # One completed 20-min session today → 120 XP (Novice), streak 1.
    store.add_ended_session(
        "lilymay", started_at=now - timedelta(minutes=20), last_activity=now
    )
    # Topic confidence for the projection's topic_confidence map.
    store.add_topic_confidence("lilymay", "macbeth", 70)

    resp = client.get(
        "/api/student-model?subject=english&student_name=lilymay",
        headers={"Authorization": "Bearer token-lilymay"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["student_name"] == "Lily May"
    assert body["streak_days"] == 1
    assert body["level_name"] == "Novice"  # 120 XP ≥ 100
    assert body["recent_xp"] == 120
    assert body["near_achievements"] == []
    assert body["topic_confidence"] == {"macbeth": 0.7}
    assert body["data_available"] is True


def test_seeded_but_empty_is_data_available_false(client: TestClient) -> None:
    # lilymay is seeded but has no sessions and no confidence.
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer token-lilymay"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_available"] is False
    assert body["topic_confidence"] == {}
    assert body["near_achievements"] == []
    assert body["streak_days"] == 0
