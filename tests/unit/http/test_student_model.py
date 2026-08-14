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
    from study_tutor.http.auth import TableTokenResolver

    # token-ghost resolves to a student that is never seeded (ASSUM-001 case).
    token_to_student = {"test-token-student-a": "lilymay", "token-ghost": "ghost"}
    return HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
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
        headers={"Authorization": "Bearer test-token-student-a"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
    assert "error_type" not in body  # transport-level (§4.2)


def test_wrong_method_is_405(client: TestClient) -> None:
    resp = client.post(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer test-token-student-a"},
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
        headers={"Authorization": "Bearer test-token-student-a"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Original R05 fields — byte-identical names/semantics.
    assert body["student_name"] == "Lily May"
    assert body["streak_days"] == 1
    assert body["level_name"] == "Novice"  # 120 XP ≥ 100
    assert body["recent_xp"] == 120
    assert body["topic_confidence"] == {"macbeth": 0.7}
    assert body["data_available"] is True
    # Enrichment (§2.2.1) — banked total, level progress, achievement views.
    assert body["total_xp"] == 120
    assert body["level_number"] == 2
    assert body["xp_into_level"] == 20  # 120 − 100 (Novice floor)
    assert body["xp_to_next_level"] == 180  # 300 (Apprentice) − 120
    assert body["longest_streak"] == 1
    assert body["recent_achievements"] == []  # fake stages no banked achievements
    assert body["next_unlock"] == {"level": 3, "feature": "Topic mastery dashboard"}
    # near_achievements grew from the R05 hardwired [] to in-progress objects.
    assert isinstance(body["near_achievements"], list)
    assert body["near_achievements"], "a 1/3 streak should surface near-misses"
    near_ids = {n["id"] for n in body["near_achievements"]}
    assert "three_day_run" in near_ids
    for near in body["near_achievements"]:
        assert set(near.keys()) == {
            "id",
            "name",
            "description",
            "progress",
            "target",
            "hint",
        }


def test_seeded_but_empty_is_data_available_false(client: TestClient) -> None:
    # lilymay is seeded but has no sessions and no confidence.
    resp = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer test-token-student-a"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_available"] is False
    assert body["topic_confidence"] == {}
    assert body["near_achievements"] == []
    assert body["streak_days"] == 0


def test_subject_param_filters_the_mastery_read(
    client: TestClient, store: FakeStudentStore
) -> None:
    """ADR-ARCH-032 / study-room §14: the required subject param now filters
    topic_confidence server-side; whole-student gamification stays unscoped."""
    now = datetime.now(UTC)
    store.add_ended_session(
        "lilymay", started_at=now - timedelta(minutes=20), last_activity=now
    )
    store.add_topic_confidence("lilymay", "macbeth", 70)
    store.add_topic_confidence("lilymay", "subjonctif", 40, subject="french")

    english = client.get(
        "/api/student-model?subject=english",
        headers={"Authorization": "Bearer test-token-student-a"},
    )
    french = client.get(
        "/api/student-model?subject=french",
        headers={"Authorization": "Bearer test-token-student-a"},
    )
    chemistry = client.get(
        "/api/student-model?subject=chemistry",
        headers={"Authorization": "Bearer test-token-student-a"},
    )

    assert english.status_code == french.status_code == chemistry.status_code == 200
    assert english.json()["topic_confidence"] == {"macbeth": 0.7}
    assert french.json()["topic_confidence"] == {"subjonctif": 0.4}
    assert chemistry.json()["topic_confidence"] == {}
    # Whole-student surfaces are identical across subjects (unscoped by design).
    assert english.json()["total_xp"] == french.json()["total_xp"] == 120
