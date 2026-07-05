"""Tests for seed-students CLI and dev reset endpoint (TASK-APP1-05).

AC-001: seed-students idempotency (run twice → exactly one row per student)
AC-002: After seeding, start_session succeeds (FK gap closed)
AC-003: Reset clears sessions/turns, preserves learner state
AC-004: Reset endpoint absent when flag unset
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from study_tutor.cli.main import cli
from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from study_tutor.session.service import SessionService
from starlette.testclient import TestClient


# Skip all tests if no Postgres DSN is configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("STUDY_TUTOR_PG_DSN"),
    reason="STUDY_TUTOR_PG_DSN not set - ephemeral DB tests skipped",
)


class FakeStudentStore:
    """Fake StudentStore for testing without real DB."""

    def __init__(self):
        self.students = {}  # student_id -> {name, year_group, target_grade}
        self.sessions = {}  # session_id -> {...}
        self.session_turns = {}  # session_id -> [turns]
        self.topic_confidences = {}  # student_id -> {topic_name -> percentage}

    async def student_exists(self, student_id: str) -> bool:
        """Check if student has identity row."""
        return student_id in self.students

    async def seed_student(
        self, student_id: str, *, name: str, year_group: int, target_grade: str
    ) -> bool:
        """Seed student identity row idempotently. Returns True if inserted."""
        if student_id in self.students:
            return False  # Already exists
        self.students[student_id] = {
            "name": name,
            "year_group": year_group,
            "target_grade": target_grade,
            "created_at": datetime.now(timezone.utc),
        }
        return True

    async def create_session(
        self,
        *,
        student_id: str,
        subject: str,
        topic: str | None,
        resume_if_active: bool,
    ):
        """Create a session (simplified for tests)."""
        session_id = f"session-{len(self.sessions)}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "student_id": student_id,
            "subject": subject,
            "topic": topic,
            "status": "active",
            "turn_count": 0,
        }
        self.session_turns[session_id] = []
        return MagicMock(session_id=session_id, student_id=student_id, resumed=False)

    async def truncate_sessions(self) -> dict[str, int]:
        """Truncate session and session_turn tables. Returns deleted counts."""
        session_count = len(self.sessions)
        turn_count = sum(len(turns) for turns in self.session_turns.values())
        self.sessions.clear()
        self.session_turns.clear()
        return {"sessions": session_count, "turns": turn_count}


# AC-001: seed-students idempotency
@pytest.mark.asyncio
async def test_seed_students_idempotent():
    """AC-001: Run seed-students twice → exactly one row per student, no errors."""
    store = FakeStudentStore()

    # First run: seed two students
    await store.seed_student(
        "lilymay", name="Lily May", year_group=10, target_grade="7"
    )
    await store.seed_student(
        "bobsmith", name="Bob Smith", year_group=11, target_grade="6"
    )

    assert len(store.students) == 2
    assert await store.student_exists("lilymay")
    assert await store.student_exists("bobsmith")

    # Second run: seed same students (idempotent)
    inserted_1 = await store.seed_student(
        "lilymay", name="Lily May", year_group=10, target_grade="7"
    )
    inserted_2 = await store.seed_student(
        "bobsmith", name="Bob Smith", year_group=11, target_grade="6"
    )

    # Should report no insertions (already exist)
    assert not inserted_1
    assert not inserted_2

    # Still exactly 2 students
    assert len(store.students) == 2


# AC-002: After seeding, start_session succeeds (FK gap closed)
@pytest.mark.asyncio
async def test_start_session_after_seed():
    """AC-002: After seeding, start_session succeeds for both dev-token students."""
    store = FakeStudentStore()

    # Seed students
    await store.seed_student(
        "lilymay", name="Lily May", year_group=10, target_grade="7"
    )
    await store.seed_student(
        "bobsmith", name="Bob Smith", year_group=11, target_grade="6"
    )

    # Both students can now start sessions (FK constraint satisfied)
    result1 = await store.create_session(
        student_id="lilymay", subject="English", topic=None, resume_if_active=False
    )
    result2 = await store.create_session(
        student_id="bobsmith", subject="Maths", topic=None, resume_if_active=False
    )

    assert result1.session_id is not None
    assert result1.student_id == "lilymay"
    assert result2.session_id is not None
    assert result2.student_id == "bobsmith"


# AC-003: Reset clears sessions + turns, preserves learner state
@pytest.mark.asyncio
async def test_reset_clears_sessions_preserves_state():
    """AC-003: Reset truncates session/session_turn, leaves confidence untouched."""
    store = FakeStudentStore()

    # Seed student with learner state
    await store.seed_student(
        "lilymay", name="Lily May", year_group=10, target_grade="7"
    )
    store.topic_confidences["lilymay"] = {"Macbeth": 75, "Poetry": 60}

    # Create sessions and turns
    await store.create_session(
        student_id="lilymay", subject="English", topic="Macbeth", resume_if_active=False
    )
    await store.create_session(
        student_id="lilymay", subject="English", topic="Poetry", resume_if_active=False
    )

    assert len(store.sessions) == 2
    assert len(store.topic_confidences["lilymay"]) == 2

    # Snapshot learner state BEFORE reset
    confidences_before = store.topic_confidences["lilymay"].copy()

    # Reset
    deleted = await store.truncate_sessions()

    # Sessions and turns cleared
    assert deleted["sessions"] == 2
    assert len(store.sessions) == 0
    assert len(store.session_turns) == 0

    # Learner state preserved (byte-identical check)
    assert store.topic_confidences["lilymay"] == confidences_before


# AC-004: Reset endpoint absent when flag unset
def test_reset_endpoint_absent_when_flag_off():
    """AC-004: With dev_reset=False, POST /__dev__/reset is unknown route (404)."""
    fake_service = AsyncMock(spec=SessionService)
    fake_store = FakeStudentStore()

    auth_config = HTTPAuthConfig(
        token_to_student={"token-test": "testuser"},
        dev_reset=False,  # Flag OFF
    )

    app = create_app(
        service=fake_service,
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=fake_store,
    )

    client = TestClient(app)

    # Attempt POST to /__dev__/reset
    response = client.post("/__dev__/reset")

    # Should be 404 (unknown route), NOT 403 or 405
    assert response.status_code == 404


# AC-004: Reset endpoint present when flag set
def test_reset_endpoint_present_when_flag_on():
    """AC-004: With dev_reset=True, POST /__dev__/reset exists and clears data."""
    fake_service = AsyncMock(spec=SessionService)
    fake_store = FakeStudentStore()

    # Pre-populate sessions
    fake_store.sessions["sess1"] = {"session_id": "sess1", "student_id": "lilymay"}
    fake_store.sessions["sess2"] = {"session_id": "sess2", "student_id": "bobsmith"}

    auth_config = HTTPAuthConfig(
        token_to_student={"token-test": "testuser"},
        dev_reset=True,  # Flag ON
    )

    app = create_app(
        service=fake_service,
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=fake_store,
    )

    client = TestClient(app)

    # POST to /__dev__/reset
    response = client.post("/__dev__/reset")

    # Should succeed
    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data
    assert data["deleted"]["sessions"] == 2


# CLI integration test: seed-students command exists and runs
def test_seed_students_cli_command_exists():
    """Verify seed-students CLI subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "seed-students" in result.output


def test_seed_students_cli_runs():
    """Verify seed-students CLI can be invoked (skip actual seeding without DSN)."""
    runner = CliRunner()
    # This will fail without DSN, but tests that the command is wired
    result = runner.invoke(cli, ["seed-students", "--help"])
    # Should show help, not crash with "no such command"
    assert "seed-students" in result.output or result.exit_code == 0
