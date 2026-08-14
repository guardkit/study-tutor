"""Scoped ``POST /__dev__/reset`` (suite isolation, 2026-08-04).

Receipt: the live suite, signed in as the real primary student, reset the
WHOLE store on 2026-08-03 — every student's transcripts. The route now
authenticates like every verb and deletes only the CALLER's sessions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock

from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from tests.unit.knowledge.store.fakes import FakeStudentStore


@pytest.fixture
def store() -> FakeStudentStore:
    fake = FakeStudentStore()
    fake.add_student(student_id="lilymay", year_group=11)
    fake.add_student(student_id="suite-runner", year_group=11)
    now = datetime.now(timezone.utc)
    for owner, sid in (
        ("lilymay", "s-lily-1"),
        ("lilymay", "s-lily-2"),
        ("suite-runner", "s-suite-1"),
    ):
        fake._sessions[sid] = {
            "student_id": owner,
            "subject": "english",
            "topic": "Macbeth",
            "status": "ended",
            "started_at": now - timedelta(minutes=30),
            "last_activity": now,
            "turn_count": 1,
            "aos_scaffolded": [],
        }
        fake._turns[sid] = [{"role": "user", "content": "hi"}]
    return fake


@pytest.fixture
def client(store: FakeStudentStore) -> TestClient:
    auth = HTTPAuthConfig.from_env(
        tokens_json='{"test-token-student-a": "lilymay", "test-bearer-suite": "suite-runner"}',
        dev_reset="true",
    )
    app = create_app(
        auth_config=auth,
        student_store=store,
        service=AsyncMock(),
        reply_fn_factory=lambda **kwargs: AsyncMock(),
    )
    return TestClient(app)


def test_reset_without_token_is_401(client: TestClient) -> None:
    resp = client.post("/__dev__/reset")
    assert resp.status_code == 401


def test_reset_deletes_only_the_callers_sessions(
    client: TestClient, store: FakeStudentStore
) -> None:
    resp = client.post(
        "/__dev__/reset", headers={"Authorization": "Bearer test-bearer-suite"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": {"sessions": 1, "turns": 1}}
    # The suite's rows are gone; the real student's rows are untouched.
    assert "s-suite-1" not in store._sessions
    assert "s-lily-1" in store._sessions
    assert "s-lily-2" in store._sessions


def test_reset_as_primary_touches_only_their_own(
    client: TestClient, store: FakeStudentStore
) -> None:
    resp = client.post(
        "/__dev__/reset", headers={"Authorization": "Bearer test-token-student-a"}
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"]["sessions"] == 2
    assert "s-suite-1" in store._sessions
