"""Smoke tests for FEAT-PH1-002 (Deterministic Session Planner).

These tests are wired to the autobuild smoke gate defined in
``.guardkit/features/FEAT-PH1-002.yaml`` (TASK-DSP-009 follow-up to the
TASK-DSP-008 post-mortem). Both tests carry ``@pytest.mark.smoke`` and
``@pytest.mark.feat_ph1_002`` so the gate's marker expression
``feat_ph1_002 and smoke`` selects them.

Note on the underscore marker: pytest's ``-m`` expression is a Python
expression, so the hyphenated form ``feat-ph1-002`` would be parsed as
``feat - ph1 - 002`` (three subtractions) and silently match nothing.
The marker is therefore registered and used as ``feat_ph1_002`` and the
gate command in ``FEAT-PH1-002.yaml`` is aligned to the same form.

Both tests exercise ``plan_session`` end-to-end with ``client=None``,
which routes through the production async pipeline, hits the
student-model read boundary safely (returns ``StudentState(empty=True)``
without contacting Graphiti), and exits in milliseconds. No external
service, MCP transport, or LLM call is involved.
"""
from __future__ import annotations

import random

import pytest

from study_tutor.planner import plan_session

pytestmark = [pytest.mark.smoke, pytest.mark.feat_ph1_002]


@pytest.mark.asyncio
async def test_smoke_rule_1_learner_override_short_circuits_pipeline() -> None:
    """Happy path: a learner-supplied override fires Rule 1.

    Rule 1 short-circuits the rule list whenever ``topic_override`` is a
    non-empty string, regardless of whether learner state is available.
    The plan must report ``rule_selected='rule-1'`` and carry the
    override topic verbatim.
    """
    plan = await plan_session(
        "smoke-test-learner",
        topic_override="Macbeth's ambition",
        rng=random.Random(42),
        client=None,
    )

    assert plan.rule_selected == "rule-1"
    assert plan.fallback_used is None
    assert plan.topic_name == "Macbeth's ambition"


@pytest.mark.asyncio
async def test_smoke_baseline_fallback_when_no_state_available() -> None:
    """Fallback path: no client + no override → baseline plan.

    With ``client=None`` the student-model read returns
    ``StudentState(empty=True)`` and the planner context is tagged
    ``learner_state_available=False``. With no override and no
    candidates from any rule, the pipeline must fall through to the
    baseline helper rather than raise.
    """
    plan = await plan_session(
        "smoke-test-learner",
        topic_override=None,
        rng=random.Random(42),
        client=None,
    )

    assert plan.fallback_used == "baseline"
    assert plan.rule_selected == "baseline"
    assert plan.learner_state_available is False
