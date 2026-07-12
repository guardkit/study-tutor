"""TASK-DSP-007 — coverage-gap tests identified in TASK-REV-DA72 §5.

Two gaps were called out in the TASK-REV-DA72 review report for which the
existing scenario suite does not provide direct evidence; they are
implemented here as unit-level pytest tests so they execute as part of
the standard pytest run without depending on the BDD glue.

Gap 1: ``test_all_bands_empty_returns_baseline``
    The ``@boundary @rule-6 @fallback`` BDD scenario seeds at least one
    topic in the developing band, so it never exercises the inner
    fall-through where rules 1/3/4 *and* the developing band are all
    empty. This test covers that fall-through and asserts the planner
    routes to ``_baseline_plan(True)`` (seeded learner with no usable
    rule fit) — i.e. ``rule_selected="baseline"``,
    ``fallback_used="baseline"``, ``learner_state_available=True``, and
    no exception is raised.

Gap 2: ``test_post_write_read_consistency_does_not_block``
    The ``@edge-case @concurrency @async`` BDD scenario specifies the
    behaviour qualitatively but lacks a wall-clock latency assertion.
    This test makes the assertion concrete: with a fire-and-forget
    session-completion write task in flight, a new
    ``tutor_start_session`` invocation must return within 2.1 seconds
    (the 2s outer handler budget plus a 0.1s tolerance) and must NOT
    block waiting for the dispatched write to land.

Both tests target production code surfaces rather than re-running the
BDD glue:

* Gap 1 calls :func:`run_rule_pipeline` directly — the sync core that
  the full ``plan_session`` async wrapper composes — so we don't need a
  fake Graphiti client to exercise the fall-through.
* Gap 2 drives :meth:`MCPAdapter.tutor_start_session` end-to-end with
  ``plan_session`` patched to a fast no-op; the dispatched
  fire-and-forget write task is created on the same event loop so the
  test can prove the adapter does not gather/await it.
"""
from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from study_tutor.mcp import adapter as adapter_module
from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.planner.pipeline import run_rule_pipeline
from study_tutor.planner.protocols import PlannerContext
from study_tutor.planner.types import SessionPlan, _baseline_plan
from study_tutor.roles.loader import RoleConfig
from study_tutor.session import service as service_module
from study_tutor.session.service import SessionService
from tests.unit.knowledge.store.fakes import FakeStudentStore


# ---------------------------------------------------------------------------
# Gap 1 — all bands empty fall-through
# ---------------------------------------------------------------------------


def _frozen_clock() -> datetime:
    return datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)


def test_all_bands_empty_returns_baseline() -> None:
    """TASK-REV-DA72 §5 Gap 1: rules 1/3/4 None + developing empty.

    Constructs a :class:`PlannerContext` with no topics, no
    misconceptions, and no override, then dispatches the rule pipeline
    directly. With nothing to chew on, rules 1/3/4 all return ``None``,
    rule 6 sees an empty developing band and abstains, and the pipeline
    must fall through to :func:`_baseline_plan` rather than raising.

    The expected output is the seeded-but-empty branch
    (``learner_state_available=True``) — the test models the case where
    the read succeeded against a learner who has no usable confidence
    entries, *not* a read failure. That distinction is what discriminates
    this gap from the existing rule-6 boundary scenario.
    """
    context = PlannerContext.create(
        student_id="lilymay",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        topic_override=None,
        clock=_frozen_clock,
        rng=random.Random(0),
        learner_state_available=True,
    )

    plan = run_rule_pipeline(context)

    assert isinstance(plan, SessionPlan), (
        "rule pipeline must produce a SessionPlan even in the all-empty case"
    )
    assert plan.rule_selected == "baseline", (
        f"expected rule_selected='baseline', got {plan.rule_selected!r}"
    )
    assert plan.fallback_used == "baseline", (
        f"expected fallback_used='baseline', got {plan.fallback_used!r}"
    )
    assert plan.learner_state_available is True, (
        "seeded-but-empty branch must preserve learner_state_available=True"
    )
    # The seeded-empty branch sources its topic from curriculum_defaults.yaml
    # (AC-004 on TASK-DSP-001) — non-empty topic_name proves the YAML path
    # was taken rather than the no-state literal.
    assert plan.topic_name, "baseline plan must carry a topic name"
    assert plan.focus_aos, "seeded-empty baseline must populate focus_aos"
    assert plan.ao_mapping_found is True


# ---------------------------------------------------------------------------
# Gap 2 — post-write fire-and-forget does not block start_session
# ---------------------------------------------------------------------------


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a tutor.")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="post-write gap-test fixture",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


@pytest.fixture
def adapter(role_config: RoleConfig) -> MCPAdapter:
    return MCPAdapter(
        role_config=role_config,
        session_service=SessionService(store=FakeStudentStore()),
    )


async def _drain_warmups(mcp_adapter: MCPAdapter) -> None:
    """Cancel fire-and-forget warm-up tasks so pytest doesn't warn."""
    tasks = list(mcp_adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_post_write_read_consistency_does_not_block(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TASK-REV-DA72 §5 Gap 2: pending post-write must not block start.

    Models the ARCH-019 fire-and-forget contract: the previous session's
    completion write was dispatched and is still in flight when a new
    ``tutor_start_session`` arrives. The new call must return within the
    2s outer handler budget plus a 0.1s tolerance (i.e. <2.1s wall
    clock), measured via :func:`time.perf_counter` per the acceptance
    criterion, and must NOT block on the dispatched write.

    The dispatched write is simulated as a 5s ``asyncio.sleep`` task on
    the same event loop. ``plan_session`` is patched to a fast no-op so
    the only way ``tutor_start_session`` could exceed 2.1s would be if
    it gathered/awaited the dispatched write — which the AC forbids.
    """
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
    # Wait until the write is genuinely running on the loop — this is
    # the "in-flight" precondition the AC names. Without this barrier the
    # test could pass simply because the write hasn't started yet.
    await started_event.wait()

    async def fast_plan(
        student_id: str, topic_override: str | None, **_kw: object
    ) -> SessionPlan:
        return _baseline_plan(learner_state_available=False)

    # S-R3 §2.1: planning moved into SessionService.start_session, so the
    # planner entry point is now patched on the service module.
    monkeypatch.setattr(service_module, "plan_session", fast_plan)

    started = time.perf_counter()
    result = await adapter.tutor_start_session(student_id="lilymay")
    elapsed = time.perf_counter() - started

    # AC-2.1s tolerance: the spec budget is 2.0s outer + 0.1s headroom.
    assert elapsed < 2.1, (
        f"start_session blocked on dispatched write task: "
        f"elapsed={elapsed:.3f}s, budget=2.1s"
    )
    assert result["session_id"], "session_id must be returned"

    # Cleanup: cancel the simulated write and drain warm-ups so pytest
    # doesn't emit "task was destroyed" warnings.
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await _drain_warmups(adapter)

    # Sanity: the write was abandoned (cancelled) rather than completed —
    # proves it really was still running when start_session returned.
    assert abandoned_event.is_set(), (
        "the dispatched write was not in flight when start_session ran"
    )
