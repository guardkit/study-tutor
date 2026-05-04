"""Seam tests for Wave 5 — End-to-end MCP tutor session (TASK-GR-DEMO).

This module pins the *runtime* contract that Wave 5's live MCP demo
depends on: that the Wave-4 Lilymay seed is reachable through the
Wave-2 wired Graphiti client, end-to-end, against a live FalkorDB +
LLM stack. It exists for traceability and as the "closest pytest-style
stub that would mock the human-in-the-loop"; the real Wave-5 acceptance
(`AC-DEMO-01..06`) is operational, conducted via Claude Desktop, and is
recorded as evidence in
``docs/research/ideas/phase-1-validation.md`` and
``docs/research/ideas/graphiti-latency-spike-results.md``.

Lifted verbatim from
``tasks/design_approved/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md``
(``## Seam Tests``) so the upstream contracts from TASK-GR-WIRE
(Wave 2) and TASK-GR-SEED (Wave 4) are pinned at this boundary:

- :class:`GraphitiClient` (TASK-GR-WIRE): the demo handlers obtain a
  live, fully-wired client via
  :func:`load_graphiti_config_from_yaml` + :func:`get_client`.
- :class:`LilymaySeed` (TASK-GR-SEED → TASK-GSM-009): post-seed
  :func:`get_student_state` returns a non-empty :class:`StudentState`
  with the year-10 / target-grade-7 baseline (drift correction per
  TASK-GSM-009 AC-14 / R7 — the spec values were always 10/"7"; the
  earlier seam-test constants drifted).

The test is gated behind ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`` so that
the autobuild gate (which runs without a live FalkorDB / Gemini /
GB10-embedder stack) skips it cleanly. Operators conducting the
live demo flip the env var on, run the seam, then proceed to the
Claude-Desktop session that records ``AC-DEMO-01..06`` evidence.
"""
from __future__ import annotations

import os

import pytest

from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.queries import get_student_state


@pytest.mark.seam
@pytest.mark.integration_contract("LilymaySeed")
@pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE" not in os.environ,
    reason="live FalkorDB + post-Wave-4 Lilymay seed required",
)
@pytest.mark.asyncio
async def test_lilymay_seed_reachable_via_wired_client() -> None:
    """Verify the wired client + Wave-4 seed compose end-to-end.

    Contract: ``get_student_state(client, 'lilymay')`` returns a
              non-empty :class:`StudentState` after Wave 4 has run.
    Producer chain: TASK-GR-WIRE → TASK-GR-SEED → consumed here.
    """
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    assert wrapper is not None, (
        "get_client() returned None; the Wave-2 wiring (TASK-GR-WIRE) "
        "must succeed before Wave 5 can demo. Check graphiti.yaml + "
        "FalkorDB / Gemini / GB10 embedder reachability."
    )

    try:
        state = await get_student_state(wrapper.client_or_none, "lilymay")
        assert state is not None, (
            "get_student_state(..., 'lilymay') returned None; "
            "Wave-4 seed (TASK-GR-SEED) has not landed in this "
            "FalkorDB partition."
        )
        assert state.year_group == 10, (
            f"Lilymay year_group expected 10, got {state.year_group!r}; "
            "Wave-4 seed schema drifted."
        )
        assert state.target_grade == "7", (
            f"Lilymay target_grade expected '7', got {state.target_grade!r}; "
            "Wave-4 seed schema drifted."
        )
        assert len(state.subjects) > 0, (
            "Lilymay subjects empty; Wave-4 seed did not persist subject rows."
        )
        assert len(state.topic_confidences) > 0, (
            "Lilymay topic_confidences empty; Wave-4 seed did not persist "
            "topic-confidence rows. AC-DEMO-03 (post-session confidence "
            "delta) cannot be observed without a non-empty baseline."
        )
    finally:
        # Always close the wrapper, even on assertion failure, so the
        # FalkorDB connection isn't leaked across pytest invocations.
        await wrapper.close()
