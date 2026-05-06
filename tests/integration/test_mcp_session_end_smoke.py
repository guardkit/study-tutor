"""Integration smoke for the MCP session-end Graphiti writeback (TASK-GR-WIRE BLOCK-3a).

Boots :class:`MCPAdapter` end-to-end with a real Graphiti client + write
helper + event bus, runs a 2-turn session, calls ``tutor_session_end``,
drains the helper, and asserts the F3 ``session_completed`` episode is
queryable. Mirrors the gating + cleanup pattern of
:mod:`tests.integration.test_typed_entity_writes`.

Skip behaviour
--------------

Gated behind ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`` (same env-var convention
as the sibling integration smokes) so the autobuild pytest run stays
hermetic. Operators flip it on for the live demo capture.

Why this test exists
--------------------

The unit tests in ``tests/unit/mcp/test_adapter.py`` mock
``perform_session_end`` to assert the delegation contract; they do not
prove that the MCP adapter, the F3 write helper, the in-process event
bus, and the live FalkorDB driver all line up end-to-end. This test
closes that gap by:

1. Building a ``GraphitiClient`` from the canonical
   ``.guardkit/graphiti.yaml``.
2. Wiring ``GraphitiWriteHelper(client=inner)`` and a fresh
   ``EventBus`` into ``MCPAdapter``.
3. Starting a session, appending two turns, calling
   ``tutor_session_end``.
4. Draining the helper to wait for the F3 task to land.
5. Querying Graphiti for the ``session_completed`` episode in the
   ``student-{slug}`` group_id and asserting it is present.

The 2 s caller-facing budget (ASSUM-004 / ADR-ARCH-019) is asserted
indirectly: ``tutor_session_end`` is awaited with no Graphiti
``await`` on the caller path, so wall-clock under 2 s is the property
of ``perform_session_end`` itself (which is unit-tested in
``tests/unit/tutoring/test_session_end.py``). Re-asserting it here
would be belt-and-braces; we focus on the load-bearing claim that the
F3 episode actually reaches the graph.

Self-cleanup
------------

The smoke uses a per-test student slug suffix so the writes land in a
disposable group_id. Cleanup is best-effort — the helper's drain
already swallows write failures, and the test's group_id is
distinguishable enough that an operator can reap it manually if needed.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE" not in os.environ,
    reason=(
        "live FalkorDB required to verify F3 session_completed write; "
        "set STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 to enable"
    ),
)


@pytest.mark.seam
@pytest.mark.integration_contract("MCPAdapterSessionEndF3Write")
@pytest.mark.asyncio
async def test_mcp_session_end_writes_session_completed_episode(
    tmp_path: object,
) -> None:
    """End-to-end: tutor_session_end → F3 fire-and-forget → episode in graph."""
    from pathlib import Path

    from study_tutor.knowledge.async_write import GraphitiWriteHelper
    from study_tutor.knowledge.graphiti_client import (
        get_client,
        load_graphiti_config_from_yaml,
    )
    from study_tutor.knowledge.student_model import STUDENT_GROUP_PREFIX
    from study_tutor.mcp.adapter import MCPAdapter
    from study_tutor.roles.loader import RoleConfig
    from study_tutor.session.tutor_session import SessionStore
    from study_tutor.tutoring.session_end import EventBus

    # ------------------------------------------------------------------
    # Construct the live client + helper + bus.
    # ------------------------------------------------------------------
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    assert wrapper is not None, (
        "live FalkorDB unavailable; STUDY_TUTOR_LIVE_GRAPHITI_SMOKE was "
        "set but get_client() returned None — check the wired-client setup."
    )
    inner = wrapper.client_or_none
    assert inner is not None

    write_helper = GraphitiWriteHelper(client=inner)
    event_bus = EventBus()

    # Per-run student slug so cleanup is mechanically distinguishable
    # from the seeded learner data the rest of the project relies on.
    student_slug = f"smoketest-{uuid.uuid4().hex[:8]}"
    expected_group_id = f"{STUDENT_GROUP_PREFIX}{student_slug}"

    # Minimal RoleConfig with a stub player prompt so MCPAdapter
    # construction does not depend on the production roles/ tree.
    prompt_path = Path(tmp_path) / "player.md"  # type: ignore[arg-type]
    prompt_path.write_text("You are a tutor.")
    role_config = RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="smoke",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )

    store = SessionStore()
    adapter = MCPAdapter(
        role_config=role_config,
        store=store,
        write_helper=write_helper,
        event_bus=event_bus,
        graphiti_client=wrapper,
    )

    # ------------------------------------------------------------------
    # Drive a 2-turn session.
    # ------------------------------------------------------------------
    started = await adapter.tutor_start_session(
        student_id=student_slug, topic_override="Macbeth"
    )
    session_id = started["session_id"]

    # Cancel the warm-up task so it does not race the test cleanup. We
    # do not need a live LLM here — we drive the turns through the
    # store directly so the I-T6 zero-turn guard does NOT fire.
    for warmup in list(adapter._warmup_tasks):
        warmup.cancel()
    await asyncio.gather(*adapter._warmup_tasks, return_exceptions=True)

    store.append_turn(session_id, "user", "What drives Macbeth's ambition?")
    store.append_turn(
        session_id,
        "tutor",
        "Let's start by considering the witches' prophecy in Act 1.",
    )

    # ------------------------------------------------------------------
    # End the session — this is the load-bearing call.
    # ------------------------------------------------------------------
    end_result = await adapter.tutor_session_end(session_id=session_id)
    assert end_result["session_id"] == session_id
    assert end_result["status"] == "ended"

    # ------------------------------------------------------------------
    # Drain the helper so the F3 task lands before we query.
    # ------------------------------------------------------------------
    await write_helper.drain()

    # ------------------------------------------------------------------
    # Query Graphiti for the session_completed episode.
    # ``add_episode`` median is ~80s on the project FalkorDB topology,
    # but ``drain()`` waited for the in-flight task to complete, so by
    # this point the episode should already be queryable. We poll
    # briefly as a defensive measure — if the helper says the task
    # finished but the graph has not yet committed, the test is
    # reporting a real driver-side bug, not a timing flake.
    # ------------------------------------------------------------------
    found_episode = None
    for _attempt in range(10):
        episodes = await inner.retrieve_episodes(
            reference_time=None,
            last_n=20,
            group_ids=[expected_group_id],
        )
        for ep in episodes:
            name = getattr(ep, "name", "") or ""
            if "session_completed" in name.lower() or session_id in str(
                getattr(ep, "content", "")
            ):
                found_episode = ep
                break
        if found_episode is not None:
            break
        await asyncio.sleep(1.0)

    assert found_episode is not None, (
        f"session_completed episode for session_id={session_id!r} not found "
        f"in group_id={expected_group_id!r} after drain + 10s poll."
    )

    # Best-effort close — graphiti-core's close API is loop-bound, so
    # we let any cleanup error fall through to the helper's drain
    # logging rather than propagate.
    try:
        await wrapper.close()
    except Exception:  # noqa: BLE001 — cleanup must never fail the test
        pass
