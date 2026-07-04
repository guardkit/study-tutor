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
# REMOVED: get_student_state import (TASK-SMP2-06)
# This test is skipped as the Graphiti read surface has been removed.
# TODO(FEAT-SMP-004): Remove this test entirely when graph seed path is retired.


@pytest.mark.seam
@pytest.mark.integration_contract("LilymaySeed")
@pytest.mark.skip(reason="TASK-SMP2-06: get_student_state removed, graph read surface retired. TODO(FEAT-SMP-004): Remove test entirely.")
@pytest.mark.asyncio
async def test_lilymay_seed_reachable_via_wired_client() -> None:
    """SKIPPED: Graphiti read surface removed in TASK-SMP2-06.

    Original contract: ``get_student_state(client, 'lilymay')`` returns a
    non-empty :class:`StudentState` after Wave 4 has run.
    Producer chain: TASK-GR-WIRE → TASK-GR-SEED → consumed here.

    TODO(FEAT-SMP-004): Remove this test when graph seed path is fully retired.
    """
    pass
