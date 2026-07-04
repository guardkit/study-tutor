"""TASK-DSP-006 — MCP adapter ↔ ``plan_session`` integration tests.

Covers the graceful-degradation boundary between
:meth:`study_tutor.mcp.adapter.MCPAdapter.tutor_start_session` and
:func:`study_tutor.planner.pipeline.plan_session`. Each test maps back to
a single acceptance criterion in the task file so a coverage audit can
trace test → criterion in one hop.

The full set of ACs covered here:

* AC-001 — planner-internal-error → baseline-degraded plan
* AC-002 — ``session_id`` minted *before* ``plan_session``
* AC-003 — ``plan_summary`` includes ``topic_name`` and ``rule_selected``
* AC-004 — ``_plan_sessions[session_id]`` holds the full plan
* AC-005 — outer guard reads from ``PLANNER_HANDLER_BUDGET_SEC`` env var
* AC-006 — inner timeout reads from ``STUDENT_MODEL_READ_TIMEOUT_SEC``
* AC-007 — slow-read scenario: returns within budget + 0.1s
* AC-008 — concurrent invocations produce distinct plans
* AC-009 — async post-write does not block ``tutor_start_session``
* AC-010 — unknown learner → ``learner_state_available=False``

Plus the TASK-REV-DA72 §3 seam test verifying the ``plan_session``
contract (signature + async).
"""
from __future__ import annotations

import asyncio
import inspect
import time
from pathlib import Path
from typing import Any

import pytest

from study_tutor.mcp import adapter as adapter_module
from study_tutor.mcp.adapter import (
    MCPAdapter,
    _plan_summary,
    _planner_handler_budget_sec,
)
from study_tutor.planner import pipeline as pipeline_module
from study_tutor.planner.pipeline import (
    _student_model_read_timeout_sec,
    plan_session,
)
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.tutor_session import SessionStore


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
def adapter(role_config: RoleConfig) -> MCPAdapter:
    return MCPAdapter(role_config=role_config, store=SessionStore())


async def _drain_warmups(adapter: MCPAdapter) -> None:
    """Cancel any fire-and-forget warm-up tasks so pytest doesn't warn."""
    tasks = list(adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Seam test (TASK-REV-DA72 §3) — plan_session contract from TASK-DSP-005
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("plan_session")
def test_plan_session_signature_and_async() -> None:
    """Verify ``plan_session`` is awaitable and accepts the wired args.

    Contract (TASK-REV-DA72 §3): ``plan_session`` is async, takes
    ``student_id: str`` and ``topic_override: str | None``, and returns a
    :class:`SessionPlan`. The MCP adapter wraps it in
    ``asyncio.wait_for`` with a 2s outer guard.
    """
    sig = inspect.signature(plan_session)
    params = list(sig.parameters)

    assert "student_id" in params, "plan_session must accept student_id"
    assert "topic_override" in params, (
        "plan_session must accept topic_override"
    )
    assert inspect.iscoroutinefunction(plan_session), (
        "plan_session must be async (the adapter wraps it in await)"
    )


# ---------------------------------------------------------------------------
# AC-001 / AC-002 — planner failure must not block session creation
# ---------------------------------------------------------------------------


async def test_planner_internal_error_returns_baseline_plan_and_session_id(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-001 + AC-002: planner ``RuntimeError`` → baseline plan, with id.

    Verifies the @negative planner-internal-error path: a ``RuntimeError``
    raised by ``plan_session`` is caught at the adapter boundary, the
    session_id (minted *before* plan_session was awaited) still flows
    back to the caller, and the response's ``plan_summary`` is the
    baseline-degraded shape.
    """
    async def boom(*_a: Any, **_kw: Any) -> SessionPlan:
        raise RuntimeError("simulated planner explosion")

    monkeypatch.setattr(adapter_module, "plan_session", boom)

    result = await adapter.tutor_start_session(
        student_id="lilymay", topic_override=None
    )
    await _drain_warmups(adapter)

    # AC-002: session_id is present despite the RuntimeError.
    assert "session_id" in result
    assert result["session_id"]  # non-empty

    # AC-001 + AC-010: degrades to baseline-False (learner state lost).
    summary = result["plan_summary"]
    assert summary["rule_selected"] == "baseline"
    assert summary["fallback_used"] == "baseline"
    assert summary["learner_state_available"] is False


async def test_session_id_minted_before_plan_session_invocation(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-002 strict: ``plan_session`` raising on entry still yields id.

    The spec requires session_id minting to happen *before* the planner
    is awaited. The strongest test of this is to make ``plan_session``
    raise the moment it's called and assert the response still contains
    a session_id — proving the id existed before the await even started.
    """
    captured: dict[str, str] = {}

    async def raise_immediately(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        captured["student_id"] = student_id
        raise asyncio.TimeoutError("entry-point raise simulating any failure")

    monkeypatch.setattr(adapter_module, "plan_session", raise_immediately)

    result = await adapter.tutor_start_session(student_id="ada-lovelace")
    await _drain_warmups(adapter)

    assert captured["student_id"] == "ada-lovelace"
    assert result["session_id"]
    # Even on TimeoutError raised from entry, the adapter must degrade.
    assert result["plan_summary"]["learner_state_available"] is False


# ---------------------------------------------------------------------------
# AC-003 — plan_summary includes topic_name + rule_selected
# ---------------------------------------------------------------------------


async def test_plan_summary_includes_topic_name_and_rule_selected(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-003: required keys are present in ``plan_summary``."""
    async def fake_plan(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        # Use the baseline helper to get a valid SessionPlan without
        # invoking the rule pipeline or curriculum YAML.
        return _baseline_plan(learner_state_available=False)

    monkeypatch.setattr(adapter_module, "plan_session", fake_plan)

    result = await adapter.tutor_start_session(student_id="lilymay")
    await _drain_warmups(adapter)

    summary = result["plan_summary"]
    assert "topic_name" in summary
    assert "rule_selected" in summary
    assert summary["topic_name"]  # non-empty
    assert summary["rule_selected"]  # non-empty


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
# AC-004 — _plan_sessions[session_id] holds the full SessionPlan
# ---------------------------------------------------------------------------


async def test_plan_sessions_stores_full_session_plan(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-004 (@key-example @mcp-integration): full plan persisted."""
    expected_plan = _baseline_plan(learner_state_available=False)

    async def fake_plan(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        return expected_plan

    monkeypatch.setattr(adapter_module, "plan_session", fake_plan)

    result = await adapter.tutor_start_session(student_id="lilymay")
    await _drain_warmups(adapter)

    sid = result["session_id"]
    assert sid in adapter._plan_sessions
    assert adapter._plan_sessions[sid] is expected_plan
    assert isinstance(adapter._plan_sessions[sid], SessionPlan)


# ---------------------------------------------------------------------------
# AC-005 / AC-006 — env-var configuration of both timeouts
# ---------------------------------------------------------------------------


def test_planner_handler_budget_default_and_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-005 (@edge-case @latency): outer guard reads env var, default 2.0."""
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
    """AC-006: inner read timeout reads env var, default 5.0."""
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
# AC-007 — slow-read scenario: outer guard fires within budget
# ---------------------------------------------------------------------------


async def test_slow_read_returns_within_outer_budget(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-007 (@edge-case @latency): 4s sleep aborted by 0.5s outer guard.

    The slow read inside ``_build_planner_context`` is simulated by
    making ``plan_session`` itself sleep for 4 seconds. With
    ``PLANNER_HANDLER_BUDGET_SEC=0.5``, the outer ``asyncio.wait_for``
    must abandon the slow coroutine and degrade to ``baseline(False)``
    well within ``0.5 + 0.1 == 0.6`` seconds.

    We use 0.5s instead of the spec's 2.0s purely to keep the test fast;
    the boundary mechanic is identical.
    """
    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "0.5")

    async def slow_plan(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        await asyncio.sleep(4.0)
        # Should never reach here — wait_for aborts at 0.5s.
        return _baseline_plan(learner_state_available=True)

    monkeypatch.setattr(adapter_module, "plan_session", slow_plan)

    started = time.monotonic()
    result = await adapter.tutor_start_session(student_id="lilymay")
    elapsed = time.monotonic() - started
    await _drain_warmups(adapter)

    assert elapsed < 0.6, (
        f"outer guard did not fire within budget+0.1s: elapsed={elapsed:.3f}s"
    )
    summary = result["plan_summary"]
    assert summary["rule_selected"] == "baseline"
    assert summary["learner_state_available"] is False


# ---------------------------------------------------------------------------
# AC-008 — concurrent invocations produce distinct session_ids and plans
# ---------------------------------------------------------------------------


async def test_concurrent_invocations_produce_distinct_session_ids(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-008 (@edge-case @concurrency): two concurrent calls don't collide.

    Two concurrent ``tutor_start_session`` invocations for the same
    learner must each get a distinct session_id, each holding its own
    ``SessionPlan`` in ``_plan_sessions``. UUID4 collision probability
    is effectively zero (no lock required); ``SessionPlan`` is frozen,
    so neither plan can quietly overwrite the other.
    """
    plan_a = _baseline_plan(learner_state_available=False)
    plan_b = _baseline_plan(learner_state_available=False)
    plans = iter([plan_a, plan_b])
    plans_lock = asyncio.Lock()

    async def fake_plan(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        async with plans_lock:
            return next(plans)

    monkeypatch.setattr(adapter_module, "plan_session", fake_plan)

    a, b = await asyncio.gather(
        adapter.tutor_start_session(student_id="lilymay"),
        adapter.tutor_start_session(student_id="lilymay"),
    )
    await _drain_warmups(adapter)

    assert a["session_id"] != b["session_id"]
    assert adapter._plan_sessions[a["session_id"]] is not (
        adapter._plan_sessions[b["session_id"]]
    )
    # Neither plan was overwritten — both still in the store.
    assert {a["session_id"], b["session_id"]} <= set(adapter._plan_sessions)


# ---------------------------------------------------------------------------
# AC-009 — async post-write doesn't block tutor_start_session
# ---------------------------------------------------------------------------


async def test_pending_async_post_write_does_not_block_start_session(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-009 (@edge-case @concurrency @async): TASK-REV-DA72 §5 Gap 2.

    A fire-and-forget session-completion write is in flight when a new
    ``tutor_start_session`` arrives. The new call must complete within
    the outer budget without waiting for the dispatched write — i.e.
    the planner does not gather/await any pending background tasks.
    """
    monkeypatch.setenv("PLANNER_HANDLER_BUDGET_SEC", "0.5")
    started_event = asyncio.Event()
    abandoned_event = asyncio.Event()

    async def slow_post_write() -> None:
        try:
            started_event.set()
            await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            abandoned_event.set()
            raise

    pending = asyncio.create_task(slow_post_write(), name="post-write")
    await started_event.wait()  # ensure the write task is actually running

    async def fast_plan(
        student_id: str, topic_override: str | None
    ) -> SessionPlan:
        return _baseline_plan(learner_state_available=False)

    monkeypatch.setattr(adapter_module, "plan_session", fast_plan)

    started = time.monotonic()
    result = await adapter.tutor_start_session(student_id="lilymay")
    elapsed = time.monotonic() - started

    assert elapsed < 0.6, (
        f"start_session blocked on background write: elapsed={elapsed:.3f}s"
    )
    assert result["session_id"]

    # Cleanup the background write so pytest doesn't warn.
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await _drain_warmups(adapter)
    assert abandoned_event.is_set()


# ---------------------------------------------------------------------------
# AC-010 — unknown learner: no exception, learner_state_available=False
# ---------------------------------------------------------------------------


async def test_unknown_learner_returns_baseline_plan_without_exception(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-010 (@negative): unseeded learner → baseline-False, no raise.

    When ``plan_session`` is called against an unseeded learner the
    pipeline should produce a baseline-False plan via the empty-state
    branch. The adapter must surface this without re-raising. We exercise
    the real pipeline (no mock) with ``client=None`` simulating "no
    Graphiti available" — the canonical unknown-learner case at this
    layer.
    """
    # Default plan_session signature passes client=None, so the pipeline
    # already routes through the empty-state branch. We run it for real.
    result = await adapter.tutor_start_session(
        student_id="learner-never-seen-before"
    )
    await _drain_warmups(adapter)

    summary = result["plan_summary"]
    # No exception was raised (we got here).
    assert result["session_id"]
    # learner_state_available=False because get_student_state returned
    # StudentState(empty=True) for client=None, which the pipeline now
    # routes to the baseline-False branch (TASK-DSP-006).
    assert summary["learner_state_available"] is False


# ---------------------------------------------------------------------------
# Inner timeout coverage — only fires when outer is enlarged
# ---------------------------------------------------------------------------


async def test_inner_timeout_fires_when_outer_is_enlarged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ASSUM-007 inner timeout: 0.1s inner trips before 10s outer.

    With ``STUDENT_MODEL_READ_TIMEOUT_SEC=0.1`` and the outer set to 10s,
    a slow ``load_planner_inputs`` (0.5s) trips the inner timeout. The
    pipeline then routes to ``_baseline_plan(False)`` per TASK-DSP-006.
    """
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
