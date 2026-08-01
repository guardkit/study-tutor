"""Unit tests for GET /api/version (TASK-STV1-001).

Covers: auth (401 unseeded / rejected bearer / missing), happy 200 + shape,
version matches package metadata, wrong method → 405.
"""

from __future__ import annotations

from importlib import metadata
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig


@pytest.fixture
def auth_config() -> HTTPAuthConfig:
    from study_tutor.http.auth import TableTokenResolver

    token_to_student = {"token-test": "test-student"}
    return HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
    )


@pytest.fixture
def store() -> AsyncMock:
    s = AsyncMock()
    s.student_exists.return_value = True
    return s


@pytest.fixture
def client(
    auth_config: HTTPAuthConfig, store: AsyncMock
) -> TestClient:
    app = create_app(
        service=AsyncMock(),
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=store,
    )
    return TestClient(app)


# -- Auth --------------------------------------------------------------------


def test_missing_authorization_is_401(client: TestClient) -> None:
    resp = client.get("/api/version")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_rejected_bearer_is_401(client: TestClient) -> None:
    resp = client.get(
        "/api/version",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


# -- Happy path --------------------------------------------------------------


def test_version_returns_200_with_correct_shape(client: TestClient) -> None:
    resp = client.get(
        "/api/version",
        headers={"Authorization": "Bearer token-test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "study-tutor"
    assert "version" in data


def test_version_matches_package_metadata(client: TestClient) -> None:
    resp = client.get(
        "/api/version",
        headers={"Authorization": "Bearer token-test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    expected = metadata.version("study-tutor")
    assert data["version"] == expected


# -- Wrong method ------------------------------------------------------------


def test_wrong_method_is_405(client: TestClient) -> None:
    resp = client.post(
        "/api/version",
        headers={"Authorization": "Bearer token-test"},
    )
    assert resp.status_code == 405
