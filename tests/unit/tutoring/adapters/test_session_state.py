"""Unit tests for the typed ``SessionState`` boundary object (TASK-LCA-003).

Covers the §4 SessionState integration contract:

* Field shape (required vs optional, types) per AC-LCA-003.
* ``@dataclass(frozen=True)`` invariants — mutation rejection and hashability,
  which together underwrite the per-turn factory isolation guarantee
  (AC-LCA-01).
* MCP-adapter construction-site behaviour: when an ``orchestrator_factory``
  is wired, ``MCPAdapter.tutor_turn`` builds a ``SessionState`` from the
  cached ``SessionPlan`` + ``TutorSession`` and passes it through to
  ``orchestrator.run_turn(session_state=..., learner_message=...)``.

Marked with ``@pytest.mark.feat_lca`` so the FEAT-6CC5 smoke gate picks
them up.
"""
from __future__ import annotations

import asyncio
import dataclasses
from pathlib import Path
from typing import Any

import pytest

from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.service import SessionService
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.orchestrator import TurnResult
from tests.unit.knowledge.store.fakes import FakeStudentStore


pytestmark = pytest.mark.feat_lca


# ---------------------------------------------------------------------------
# SessionState dataclass — field shape, defaults, and frozen invariants
# ---------------------------------------------------------------------------


class TestSessionStateDataclass:
    """Field-shape and frozen-invariant tests for ``SessionState``."""

    def test_required_fields_construct_with_minimum_arguments(self) -> None:
        state = SessionState(session_id="sess-1", student_id="stu-1")

        assert state.session_id == "sess-1"
        assert state.student_id == "stu-1"

    def test_optional_fields_default_per_assum_lca_007(self) -> None:
        """ASSUM-LCA-007: optional fields default to ``None`` / ``()`` /
        ``"tutor"`` so the MCP construction site can build a minimal
        ``SessionState`` even when ``SessionPlan.text_name`` /
        ``focus_aos`` are absent (baseline-degraded plan).
        """
        state = SessionState(session_id="sess-1", student_id="stu-1")

        assert state.text_name is None
        assert state.topic is None
        assert state.focus_aos == ()
        assert state.mode == "tutor"

    def test_required_fields_raise_when_missing(self) -> None:
        with pytest.raises(TypeError):
            SessionState()  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            SessionState(session_id="sess-1")  # type: ignore[call-arg]

    def test_focus_aos_default_is_empty_tuple_not_shared(self) -> None:
        """``field(default_factory=tuple)`` produces a fresh empty tuple
        per instance — guard against accidental ``default=()`` aliasing if
        someone refactors the field declaration.
        """
        a = SessionState(session_id="a", student_id="x")
        b = SessionState(session_id="b", student_id="y")

        assert a.focus_aos == ()
        assert b.focus_aos == ()
        # Tuples are immutable so identity-vs-value is moot for safety,
        # but a fresh instance per construct is what the contract promises.
        assert a.focus_aos == b.focus_aos

    def test_frozen_dataclass_rejects_attribute_assignment(self) -> None:
        """``@dataclass(frozen=True)`` raises ``FrozenInstanceError`` on
        any attribute write. Per-turn factory isolation (AC-LCA-01)
        depends on this — a Coach observation must not be able to write
        back into the SessionState and contaminate another session.
        """
        state = SessionState(session_id="sess-1", student_id="stu-1")

        with pytest.raises(dataclasses.FrozenInstanceError):
            state.session_id = "mutated"  # type: ignore[misc]

        with pytest.raises(dataclasses.FrozenInstanceError):
            state.topic = "mutated"  # type: ignore[misc]

    def test_session_state_is_hashable(self) -> None:
        """Frozen dataclasses get a value-based ``__hash__`` for free.
        Adapters can rely on this to key per-turn caches by SessionState.
        """
        state = SessionState(
            session_id="sess-1",
            student_id="stu-1",
            text_name="Macbeth",
            topic="Themes",
            focus_aos=("AO1", "AO2"),
            mode="tutor",
        )
        # Sets exercise __hash__ + __eq__ together; succeeding here proves
        # the dataclass produced both correctly.
        bucket = {state}
        assert state in bucket

        # Equal-by-value instances hash the same.
        twin = SessionState(
            session_id="sess-1",
            student_id="stu-1",
            text_name="Macbeth",
            topic="Themes",
            focus_aos=("AO1", "AO2"),
            mode="tutor",
        )
        assert hash(state) == hash(twin)
        assert state == twin

    def test_focus_aos_accepts_tuple_of_strings(self) -> None:
        """The contract is ``tuple[str, ...]``; verify the typed field
        round-trips a non-empty tuple unchanged.
        """
        state = SessionState(
            session_id="sess-1",
            student_id="stu-1",
            focus_aos=("AO1", "AO3"),
        )
        assert state.focus_aos == ("AO1", "AO3")


# ---------------------------------------------------------------------------
# MCP adapter construction-site integration (AC: tutor_turn passes
# SessionState through to orchestrator.run_turn)
# ---------------------------------------------------------------------------


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a tutor.")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


async def _drain_warmups(adapter: MCPAdapter) -> None:
    tasks = list(adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


class _StubOrchestrator:
    """Records the kwargs handed to ``run_turn`` and returns a static
    ``TurnResult`` so ``MCPAdapter.tutor_turn`` can complete its happy
    path. The full orchestrator wiring is exercised by
    ``tests/unit/tutoring/test_orchestrator.py`` — this stub is just the
    receiving end of the SessionState boundary.
    """

    def __init__(self) -> None:
        self.received: dict[str, Any] = {}

    async def run_turn(self, **kwargs: Any) -> TurnResult:
        self.received = kwargs
        return TurnResult(
            response="ok",
            decision="accept",
            verdict=None,
            attempts=1,
            flagged_for_review=False,
            flag_reason=None,
            duration_seconds=0.01,
        )


async def test_tutor_turn_passes_session_state_to_orchestrator(
    role_config: RoleConfig,
) -> None:
    """AC: ``MCPAdapter.tutor_turn`` constructs a ``SessionState`` from
    the cached ``SessionPlan`` + ``TutorSession`` and passes it as the
    ``session_state`` kwarg to ``orchestrator.run_turn``.

    The factory is invoked at boot (smoke check) and again per-turn
    (per-session isolation). We track only the per-turn invocation by
    reading the *last* stub created.
    """
    stubs: list[_StubOrchestrator] = []

    def factory() -> _StubOrchestrator:
        stub = _StubOrchestrator()
        stubs.append(stub)
        return stub

    session_service = SessionService(store=FakeStudentStore())
    adapter = MCPAdapter(
        role_config=role_config,
        session_service=session_service,
        orchestrator_factory=factory,
    )

    # Boot smoke check (TASK-LCA-004) calls the factory once already; the
    # next factory call belongs to ``tutor_turn``.
    boot_invocations = len(stubs)
    assert boot_invocations == 1

    started = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    # Sanity-check the cached plan exists so the construction-site path
    # runs against a real SessionPlan rather than the ``plan is None``
    # branch.
    assert session_id in adapter._plan_sessions

    result = await adapter.tutor_turn(
        session_id=session_id, user_message="Tell me about Act 1"
    )

    # tutor_turn returned the orchestrator's response shape, not the
    # Phase-0 single-LLM shape — confirms the factory branch executed.
    assert result["tutor_response"] == "ok"
    assert result["decision"] == "accept"
    assert result["attempts"] == 1

    # Exactly one new stub was produced for the turn (per-turn factory
    # invocation invariant).
    assert len(stubs) == boot_invocations + 1
    turn_stub = stubs[-1]

    # Orchestrator received a typed SessionState — not a dict.
    state = turn_stub.received["session_state"]
    assert isinstance(state, SessionState)
    assert turn_stub.received["learner_message"] == "Tell me about Act 1"

    # Required fields are populated from the live TutorSession + cached plan.
    assert state.session_id == session_id
    assert state.student_id == "lilymay"
    assert state.mode == "tutor"

    # ``topic`` and ``focus_aos`` come from the cached SessionPlan; we
    # don't assert exact values because the deterministic planner may
    # baseline-degrade for a brand-new fixture, but the types must hold.
    assert state.topic is None or isinstance(state.topic, str)
    assert isinstance(state.focus_aos, tuple)
    assert all(isinstance(ao, str) for ao in state.focus_aos)

    # text_name reads from SessionPlan when present, else None
    # (ASSUM-LCA-007). Either is contract-compliant.
    assert state.text_name is None or isinstance(state.text_name, str)


async def test_tutor_turn_phase_zero_path_unchanged_when_factory_is_none(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: existing ``tutor_turn`` Phase-0 path (no orchestrator factory)
    is unchanged — it must NOT construct a SessionState or invoke any
    orchestrator. We assert the response shape collapses back to the
    single-LLM ``{"tutor_response": ...}`` form.
    """
    from study_tutor.llm import client as llm_client

    def fake_generate(self: Any, prompt: str, system: str | None = None) -> str:
        assert system == "You are a tutor."
        return f"tutor-reply:{prompt}"

    monkeypatch.setattr(llm_client.LLMClient, "generate", fake_generate)

    adapter = MCPAdapter(
        role_config=role_config,
        session_service=SessionService(store=FakeStudentStore()),
    )
    assert adapter._orchestrator_factory is None

    started = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    result = await adapter.tutor_turn(
        session_id=session_id, user_message="hello"
    )

    # Phase-0 shape: only ``tutor_response`` — no decision/attempts keys
    # (those are produced exclusively by the orchestrator branch).
    assert result == {"tutor_response": "tutor-reply:hello"}
