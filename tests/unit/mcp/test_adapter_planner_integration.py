"""Planning-hoist integration tests (S-R3 §2.1 / D14).

Planning moved out of ``mcp/adapter.py`` and into
:meth:`study_tutor.session.service.SessionService.start_session` (the reference
2.0s budget/degrade implementation was relocated there and the per-adapter
``_plan_sessions`` cache deleted). These tests therefore exercise the graceful
-degradation boundary at the **service** layer, plus the thin MCP skin that
projects the service's plan into ``plan_summary``.

Covered:

* session_id minted even when the planner fails (never blocks creation)
* planner-internal-error / timeout → baseline-degraded plan on the result
* the outer budget reads ``PLANNER_HANDLER_BUDGET_SEC`` (now on the service)
* a slow planner is abandoned within budget and degrades
* the MCP ``plan_summary`` is sourced from the service plan (AC-003)
* the inner student-model read timeout still lives on the planner pipeline
"""
from __future__ import annotations

import asyncio
import inspect
import time
from pathlib import Path
from typing import Any

import pytest

from study_tutor.mcp.adapter import (
    MCPAdapter,
    _plan_summary,
)
from study_tutor.planner import pipeline as pipeline_module
from study_tutor.planner.pipeline import (
    _student_model_read_timeout_sec,
    plan_session,
)
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session import service as service_module
from study_tutor.session.service import (
    SessionService,
    _planner_handler_budget_sec,
)
from tests.unit.knowledge.store.fakes import FakeStudentStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a tutor.")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="planner-integration test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


@pytest.fixture
def store() -> FakeStudentStore:
    s = FakeStudentStore()
    s.add_student(student_id="lilymay", year_group=9)
    return s


@pytest.fixture
def service(store: FakeStudentStore) -> SessionService:
    return SessionService(store=store)


@pytest.fixture
def adapter(role_config: RoleConfig, service: SessionService) -> MCPAdapter:
    return MCPAdapter(role_config=role_config, session_service=service)


async def _drain_warmups(adapter: MCPAdapter) -> None:
    tasks = list(adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Seam test — plan_session contract (unchanged by the hoist)
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("plan_session")
def test_plan_session_signature_and_async() -> None:
    """``plan_session`` is async and accepts ``student_id`` + ``topic_override``.

    The service wraps it in ``asyncio.wait_for`` with a 2s outer guard.
    """
    sig = inspect.signature(plan_session)
    params = list(sig.parameters)
    assert "student_id" in params
    assert "topic_override" in params
    assert inspect.iscoroutinefunction(plan_session)


# ---------------------------------------------------------------------------
# Planner failure must not block session creation (service layer)
# ---------------------------------------------------------------------------


async def test_planner_internal_error_returns_baseline_plan_and_session_id(
    service: SessionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``RuntimeError`` from ``plan_session`` degrades to a baseline plan and
    still yields a durable session (creation is never blocked)."""

    async def boom(*_a: Any, **_kw: Any) -> SessionPlan:
        raise RuntimeError("simulated planner explosion")

    monkeypatch.setattr(service_module, "plan_session", boom)

    result = await service.start_session(
        student_id="lilymay", subject="lilymay", topic=None
    )

    assert result.session_id
    assert result.plan is not None
    assert result.plan.rule_selected == "baseline"
    assert result.plan.fallback_used == "baseline"
    assert result.plan.learner_state_available is False


async def test_session_created_before_plan_when_planner_raises_on_entry(
    service: SessionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even a ``TimeoutError`` raised the moment ``plan_session`` is entered
    still yields a session with a (degraded) plan."""
    captured: dict[str, str] = {}

    async def raise_immediately(
        student_id: str, topic_override: str | None, **_kw: Any
    ) -> SessionPlan:
        captured["student_id"] = student_id
        raise asyncio.TimeoutError("entry-point raise")

    monkeypatch.setattr(service_module, "plan_session", raise_immediately)

    result = await service.start_session(
        student_id="ada-lovelace", subject="ada-lovelace"
    )

    assert captured["student_id"] == "ada-lovelace"
    assert result.session_id
    assert result.plan is not None
    assert result.plan.learner_state_available is False


# ---------------------------------------------------------------------------
# MCP plan_summary is sourced from the service plan
# ---------------------------------------------------------------------------


async def test_plan_summary_includes_topic_name_and_rule_selected(
    adapter: MCPAdapter,
) -> None:
    """AC-003: the MCP ``plan_summary`` (projected from the service plan) carries
    the observability keys a client needs."""
    result = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    await _drain_warmups(adapter)

    summary = result["plan_summary"]
    assert "topic_name" in summary
    assert "rule_selected" in summary
    assert summary["topic_name"]  # non-empty
    # Rule 1 (override) selects the requested topic.
    assert summary["topic_name"] == "Macbeth"


def test_plan_summary_helper_projects_all_fields() -> None:
    """``_plan_summary`` projects every observability field a client needs."""
    plan = _baseline_plan(learner_state_available=False)
    summary = _plan_summary(plan)
    expected_keys = {
        "topic_name",
        "rule_selected",
        "fallback_used",
        "focus_aos",
        "opening_prompt",
        "suggested_duration_minutes",
        "rationale",
        "related_misconceptions",
        "ao_mapping_found",
        "learner_state_available",
    }
    assert expected_keys <= set(summary)


# ---------------------------------------------------------------------------
# Outer budget configuration (now on the service)
# ---------------------------------------------------------------------------


def test_planner_handler_budget_default_and_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The outer guard reads ``PLANNER_HANDLER_BUDGET_SEC``, default 2.0."""
    monkeypatch.delenv("PLANNER_HANDLER_BUDGET_SEC", raising=False)
    assert _planner_handler_budget_sec() == pytest.approx(2.0)

    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "0.5")
    assert _planner_handler_budget_sec() == pytest.approx(0.5)

    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "10")
    assert _planner_handler_budget_sec() == pytest.approx(10.0)


def test_planner_handler_budget_unparseable_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unparseable env value must not crash callers — fall back gracefully."""
    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "not-a-float")
    assert _planner_handler_budget_sec() == pytest.approx(2.0)


def test_student_model_read_timeout_default_and_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The inner read timeout still reads its env var, default 5.0."""
    monkeypatch.delenv("STUDENT_MODEL_READ_TIMEOUT_SEC", raising=False)
    assert _student_model_read_timeout_sec() == pytest.approx(5.0)

    monkeypatch.setenv("STUDENT_MODEL_READ_TIMEOUT_SEC", "0.25")
    assert _student_model_read_timeout_sec() == pytest.approx(0.25)


def test_two_timeouts_are_independently_configurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both env vars patch independently — neither leaks into the other."""
    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "0.1")
    monkeypatch.setenv("STUDENT_MODEL_READ_TIMEOUT_SEC", "9.9")
    assert _planner_handler_budget_sec() == pytest.approx(0.1)
    assert _student_model_read_timeout_sec() == pytest.approx(9.9)


# ---------------------------------------------------------------------------
# Slow-read scenario: outer guard fires within budget (service layer)
# ---------------------------------------------------------------------------


async def test_slow_plan_abandoned_within_outer_budget(
    service: SessionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 4s planner is abandoned by the 0.5s outer guard and degrades to
    baseline well within ``0.5 + 0.1`` seconds."""
    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "0.5")

    async def slow_plan(
        student_id: str, topic_override: str | None, **_kw: Any
    ) -> SessionPlan:
        await asyncio.sleep(4.0)
        return _baseline_plan(learner_state_available=True)

    monkeypatch.setattr(service_module, "plan_session", slow_plan)

    started = time.monotonic()
    result = await service.start_session(
        student_id="lilymay", subject="lilymay"
    )
    elapsed = time.monotonic() - started

    assert elapsed < 0.6, f"outer guard did not fire within budget: {elapsed:.3f}s"
    assert result.plan is not None
    assert result.plan.rule_selected == "baseline"
    assert result.plan.learner_state_available is False


# ---------------------------------------------------------------------------
# Concurrent invocations converge on the one active session
# ---------------------------------------------------------------------------


async def test_concurrent_invocations_converge_on_one_active_session(
    adapter: MCPAdapter,
) -> None:
    """Two concurrent ``tutor_start_session`` calls for the same learner
    complete without corrupting each other and converge on the ONE active
    ``(student, subject)`` session — the door resumes (ruled (b)
    follow-through, 2026-08-04), so distinct-id minting per call is no
    longer the invariant; one-active is."""
    a, b = await asyncio.gather(
        adapter.tutor_start_session(student_id="lilymay"),
        adapter.tutor_start_session(student_id="lilymay"),
    )
    await _drain_warmups(adapter)

    assert a["session_id"] and b["session_id"]
    assert a["session_id"] == b["session_id"]


# ---------------------------------------------------------------------------
# Unknown learner: no exception, learner_state_available=False
# ---------------------------------------------------------------------------


async def test_unknown_learner_returns_baseline_plan_without_exception(
    role_config: RoleConfig,
) -> None:
    """An unseeded learner degrades to a baseline-False plan without raising."""
    adapter = MCPAdapter(
        role_config=role_config,
        session_service=SessionService(store=FakeStudentStore()),
    )
    result = await adapter.tutor_start_session(
        student_id="learner-never-seen-before"
    )
    await _drain_warmups(adapter)

    summary = result["plan_summary"]
    assert result["session_id"]
    assert summary["learner_state_available"] is False


# ---------------------------------------------------------------------------
# Inner timeout coverage — only fires when outer is enlarged (pipeline)
# ---------------------------------------------------------------------------


async def test_inner_timeout_fires_when_outer_is_enlarged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With ``STUDENT_MODEL_READ_TIMEOUT_SEC=0.1`` a slow ``load_planner_inputs``
    trips the inner timeout and the pipeline routes to ``_baseline_plan(False)``."""
    monkeypatch.setenv("STUDENT_MODEL_READ_TIMEOUT_SEC", "0.1")

    async def slow_load_planner_inputs(student_id: str, **kwargs: Any) -> Any:
        await asyncio.sleep(0.5)
        return None  # never reached

    monkeypatch.setattr(
        pipeline_module, "load_planner_inputs", slow_load_planner_inputs
    )

    plan = await plan_session("lilymay", topic_override=None, client=object())
    assert plan.rule_selected == "baseline"
    assert plan.learner_state_available is False
