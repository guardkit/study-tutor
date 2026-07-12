"""S-R3 §2.4 / D14 — HTTP and MCP produce IDENTICAL learner-state writes.

Completion assembly lives in ``SessionService.end_session`` for ALL transports
(the HTTP handler passes nothing; the MCP adapter passes only a topic hint), so
the two transports must bank byte-identical session + confidence rows for the
same scenario. This is the D14 fence made executable: the MCP adapter holds no
completion logic the HTTP path lacks.

Also pins the §2.3 / R12 confidence bootstrap end-to-end: a first-seen topic gets
a ``topic_confidence`` row *created* at the mid-Developing baseline (50) through
``end_session``, not skipped.
"""
from __future__ import annotations

import unittest.mock
from pathlib import Path

import pytest

from study_tutor.llm import client as llm_client
from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.service import SessionService, TutorReply
from tests.unit.knowledge.store.fakes import FakeStudentStore


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a tutor.")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="parity test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


def _seeded_store() -> FakeStudentStore:
    store = FakeStudentStore()
    # resolve_student_id() defaults to "lilymay" — the MCP ownership identity.
    store.add_student(student_id="lilymay", year_group=9)
    return store


def _session_facts(store: FakeStudentStore) -> dict:
    """Extract the single session's banked facts for comparison."""
    (sess,) = list(store._sessions.values())
    return {
        "topic": sess["topic"],
        "aos_scaffolded": sess["aos_scaffolded"],
        "xp_awarded": sess.get("xp_awarded"),
        "status": sess["status"],
    }


def _confidence_facts(store: FakeStudentStore) -> dict:
    return {
        topic: (row["percentage"], row["band"])
        for (_student, topic), row in store._confidences.items()
    }


async def _fake_reply(user_message: str) -> TutorReply:
    return TutorReply(response=f"tutor: {user_message}")


async def test_http_and_mcp_end_session_write_identically(
    role_config: RoleConfig,
) -> None:
    """Same scenario over the two transports ⇒ identical session + confidence
    rows (D14)."""
    # --- HTTP path: the service the HTTP handler drives directly. ---
    store_http = _seeded_store()
    svc_http = SessionService(store=store_http)
    start_http = await svc_http.start_session(
        student_id="lilymay", subject="lilymay", topic="Macbeth"
    )
    await svc_http.turn(
        student_id="lilymay",
        session_id=start_http.session_id,
        user_message="Tell me about ambition",
        reply_fn=_fake_reply,
    )
    # HTTP passes neither completion nor topic_hint (app.py end_session).
    await svc_http.end_session(
        student_id="lilymay", session_id=start_http.session_id
    )

    # --- MCP path: the adapter over its own service/store. ---
    store_mcp = _seeded_store()
    svc_mcp = SessionService(store=store_mcp)
    adapter = MCPAdapter(role_config=role_config, session_service=svc_mcp)

    def fake_generate(self, prompt, system=None):  # type: ignore[no-untyped-def]
        return f"tutor: {prompt}"

    with unittest.mock.patch.object(
        llm_client.LLMClient, "generate", fake_generate
    ):
        started = await adapter.tutor_start_session(
            student_id="lilymay", topic_override="Macbeth"
        )
        # Drain warm-up so no orphan task warning.
        for task in list(adapter._warmup_tasks):
            task.cancel()
        await adapter.tutor_turn(
            session_id=started["session_id"],
            user_message="Tell me about ambition",
        )
        await adapter.tutor_session_end(session_id=started["session_id"])

    # The banked session facts and confidence rows are byte-identical.
    assert _session_facts(store_http) == _session_facts(store_mcp)
    assert _confidence_facts(store_http) == _confidence_facts(store_mcp)

    # And both actually banked the plan facts: topic persisted, session ended.
    facts = _session_facts(store_http)
    assert facts["topic"] == "Macbeth"
    assert facts["status"] == "ended"


async def test_end_session_bootstraps_first_seen_topic_confidence_row() -> None:
    """§2.3 / R12 end-to-end: a first-seen topic's ``topic_confidence`` row is
    *created* (not skipped) at the mid-Developing baseline through end_session.

    With a single (user, tutor) turn the policy delta is 0, so the brand-new
    topic lands at exactly the baseline 50 (Developing band).
    """
    store = _seeded_store()
    svc = SessionService(store=store)

    start = await svc.start_session(
        student_id="lilymay", subject="lilymay", topic="Poetry"
    )
    await svc.turn(
        student_id="lilymay",
        session_id=start.session_id,
        user_message="Analyse this stanza",
        reply_fn=_fake_reply,
    )

    # No confidence row exists for "Poetry" before settlement.
    assert ("lilymay", "Poetry") not in store._confidences

    await svc.end_session(student_id="lilymay", session_id=start.session_id)

    # The row was created at the baseline (single turn ⇒ delta 0 ⇒ 50).
    row = store._confidences[("lilymay", "Poetry")]
    assert row["percentage"] == 50
    assert row["band"] == "developing"
