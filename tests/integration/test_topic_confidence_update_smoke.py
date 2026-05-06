"""Live-FalkorDB integration smoke for ``record_topic_confidence_update``.

AC-CONF-11 (TASK-GR-CONF / BLOCK-3b). Verifies the typed-entity write
round-trip end-to-end against a live FalkorDB seeded with the Lilymay
baseline:

1. Load Lilymay's "Lady Macbeth's ambition" :class:`TopicConfidence`
   node (baseline ``percentage=55``, ``band="developing"``,
   ``last_revised_at = EPOCH_NEVER_REVISED``).
2. Run :func:`record_topic_confidence_update` with a fake policy
   returning ``+2``.
3. Drain the helper's in-flight tasks.
4. Re-load the node, assert ``percentage`` moved by ``+2`` and
   ``last_revised_at`` flipped from the epoch sentinel to a recent
   timestamp.

Mirrors the pattern of :mod:`tests.integration.test_typed_entity_writes`:
gated behind ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`` so the autobuild gate
runs hermetic and only operators conducting a live demo flip it on. The
seed must already be present (run ``scripts.seed_student_model`` once).

Cleanup is idempotent: the test reads-modifies-rereads the same UUID,
so the post-condition leaves the graph in a non-baseline state. A
follow-up reseed run restores it. We do not auto-reseed here because
the AC-CONF-09 demo evidence wants the post-update state visible in
``mcp__graphiti__search_nodes``.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import pytest


SMOKE_ENV_VAR: str = "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE"
LILYMAY_STUDENT_ID: str = "lilymay"
LILYMAY_TOPIC: str = "Lady Macbeth's ambition"


class _Plus2Policy:
    """Fake :class:`ConfidenceDeltaPolicyLike` returning a fixed +2."""

    name = "smoke_plus2_policy"

    def compute(
        self,
        *,
        student_id: str,
        topic_ref: str,
        session_summary: dict[str, Any],
    ) -> int:
        return 2


@pytest.mark.seam
@pytest.mark.integration_contract("TopicConfidenceUpdateRoundTrip")
@pytest.mark.skipif(
    SMOKE_ENV_VAR not in os.environ,
    reason=(
        "live FalkorDB required to verify TopicConfidence round-trip; "
        "set STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 to enable"
    ),
)
@pytest.mark.asyncio
async def test_record_topic_confidence_update_end_to_end_round_trip() -> None:
    """AC-CONF-11: live round-trip through ``EntityNode.save``.

    Pins the property AC-DEMO-03 depends on: a session-end-driven write
    via :func:`record_topic_confidence_update` flips the persisted
    ``last_revised_at`` and (when delta != 0) updates ``percentage`` /
    ``band`` in a way that ``mcp__graphiti__search_nodes`` confirms.
    """
    from graphiti_core.errors import NodeNotFoundError
    from graphiti_core.nodes import EntityNode

    from study_tutor.knowledge.async_write import GraphitiWriteHelper
    from study_tutor.knowledge.graphiti_client import (
        get_client,
        load_graphiti_config_from_yaml,
    )
    from study_tutor.knowledge.queries import (
        _driver_for_group_id,
        record_topic_confidence_update,
    )
    from study_tutor.knowledge.seed_uuids import topic_confidence_uuid
    from study_tutor.knowledge.student_model import (
        EPOCH_NEVER_REVISED,
        STUDENT_GROUP_PREFIX,
    )

    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    assert wrapper is not None, (
        "live FalkorDB unavailable; STUDY_TUTOR_LIVE_GRAPHITI_SMOKE was set "
        "but get_client() returned None — check the wired-client setup."
    )

    inner = wrapper.client_or_none
    assert inner is not None
    driver = getattr(inner, "driver", None)
    assert driver is not None

    group_id = f"{STUDENT_GROUP_PREFIX}{LILYMAY_STUDENT_ID}"
    tc_uuid = topic_confidence_uuid(
        group_id, LILYMAY_STUDENT_ID, LILYMAY_TOPIC
    )

    helper = GraphitiWriteHelper(client=inner)
    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        # ----- Read the seeded baseline -----------------------------------
        target_driver = _driver_for_group_id(driver, group_id)
        try:
            baseline_node = await EntityNode.get_by_uuid(target_driver, tc_uuid)
        except NodeNotFoundError:
            pytest.skip(
                f"baseline TopicConfidence not found for {LILYMAY_TOPIC!r}; "
                f"reseed via scripts.seed_student_model and retry"
            )

        baseline_attrs = dict(getattr(baseline_node, "attributes", {}) or {})
        baseline_percentage = int(baseline_attrs.get("percentage", 0))

        # ----- Run the helper with a fake +2 policy -----------------------
        ended_at = datetime.now(timezone.utc)
        await record_topic_confidence_update(
            client=wrapper,
            write_helper=helper,
            student_id=LILYMAY_STUDENT_ID,
            topic_ref=LILYMAY_TOPIC,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 6,
                "ended_at": ended_at,
                "triggering_session_id": "smoke-conf-1",
            },
            policy=_Plus2Policy(),
            create_task_fn=_capture_task,
        )

        # Drain in-flight save + helper writes so the re-read sees the
        # post-update state.
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)
        await helper.drain()

        # ----- Re-read and assert the post-condition ----------------------
        post_node = await EntityNode.get_by_uuid(target_driver, tc_uuid)
        post_attrs = dict(getattr(post_node, "attributes", {}) or {})
        post_percentage = int(post_attrs.get("percentage", 0))
        post_last_revised = post_attrs.get("last_revised_at")

        # Post-condition AC-CONF-11: percentage moved by +2 (clamped at 100).
        expected_percentage = min(baseline_percentage + 2, 100)
        assert post_percentage == expected_percentage, (
            f"percentage did not move by +2: "
            f"baseline={baseline_percentage}, post={post_percentage}"
        )

        # Post-condition: last_revised_at flipped away from epoch sentinel.
        assert post_last_revised is not None
        assert post_last_revised != EPOCH_NEVER_REVISED.isoformat(), (
            "last_revised_at still at EPOCH_NEVER_REVISED — entity update "
            "did not land"
        )
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()
        await wrapper.close()
