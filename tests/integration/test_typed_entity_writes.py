"""Integration smoke for typed-entity writes (TASK-GSM-009 AC-13 / R5).

Pins the load-bearing property the typed-entity seed depends on:
``EntityNode.save`` is **MERGE-by-uuid** in the guardkit graphiti-core
fork's FalkorDB driver. Two saves of a node with the same uuid must
collapse into a single node in the graph (not duplicate). This is what
makes :mod:`scripts.seed_student_model` byte-idempotent on re-run.

Why this test exists
--------------------

The seed's idempotency story is: every entity uuid is derived
deterministically from ``(group_id, label, identity)`` via
``uuid5(NAMESPACE_OID, ...)`` (see :mod:`study_tutor.knowledge.seed_uuids`).
So a re-run produces the same uuids → ``EntityNode.save`` MERGEs by uuid →
the graph state is byte-identical. If ``EntityNode.save`` ever stopped
MERGE-ing (e.g. an upstream graphiti-core change, a fork rebase that
loses the bug-#8 fix), the seed would silently start producing duplicate
nodes on every re-run. This smoke catches that drift.

Skip behaviour
--------------

Gated behind ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`` (same env-var convention
as :mod:`tests.integration.test_lilymay_seed_seam`) so the autobuild gate
runs hermetic and only operators conducting a live demo flip it on.

Self-cleanup
------------

The smoke writes its node into a dedicated ``mergebyuuid-probetest``
named graph and ``DETACH DELETE`` cleans it on both success and failure
paths. No production partition is touched.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest


GROUP_PROBE: str = "mergebyuuid-probetest"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.seam
@pytest.mark.integration_contract("EntityNodeMergeByUuid")
@pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE" not in os.environ,
    reason=(
        "live FalkorDB required to verify MERGE-by-uuid behaviour; "
        "set STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 to enable"
    ),
)
@pytest.mark.asyncio
async def test_entity_node_save_merges_by_uuid_on_falkordb() -> None:
    """Writing a typed EntityNode twice with the same uuid yields one node.

    AC-GSM-009-13 / R5: pins the fork-side behaviour the seed's
    idempotency property depends on.
    """
    from graphiti_core.driver.driver import GraphProvider
    from graphiti_core.nodes import EntityNode

    from study_tutor.knowledge.graphiti_client import (
        get_client,
        load_graphiti_config_from_yaml,
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

    is_falkordb = (
        getattr(driver, "provider", None) == GraphProvider.FALKORDB
    )
    if not is_falkordb:
        # Skip rather than fail — the contract is FalkorDB-specific (per the
        # bug-#8 fix in the guardkit fork). On Neo4j or Kuzu the assertion
        # would still likely hold but isn't part of this AC.
        await wrapper.close()
        pytest.skip(
            f"this smoke is FalkorDB-specific; got "
            f"{getattr(driver, 'provider', None)}"
        )

    # Use a per-test uuid so accidental cross-test contention doesn't mask
    # a real MERGE failure.
    fixed_uuid = str(uuid.uuid4())
    target_driver = driver.clone(database=GROUP_PROBE)

    try:
        # ----- First write -------------------------------------------------
        await EntityNode(
            uuid=fixed_uuid,
            name="MergeByUuidProbe",
            labels=["Entity", "ProbeNode"],
            group_id=GROUP_PROBE,
            summary="first save",
            attributes={"version": 1},
        ).save(target_driver)

        # ----- Second write (same uuid, different summary/attrs) ----------
        await EntityNode(
            uuid=fixed_uuid,
            name="MergeByUuidProbe",
            labels=["Entity", "ProbeNode"],
            group_id=GROUP_PROBE,
            summary="second save",
            attributes={"version": 2},
        ).save(target_driver)

        # ----- Count via Cypher: must be exactly 1 ------------------------
        cypher = (
            "MATCH (n {uuid: $uuid}) RETURN count(n) AS node_count"
        )
        result = target_driver.execute_query(cypher, uuid=fixed_uuid)
        if asyncio.iscoroutine(result):
            result = await result

        # graphiti-core's execute_query returns a tuple ``(records, summary,
        # keys)`` on FalkorDB. Tease out the row count defensively.
        rows: list = []
        if isinstance(result, tuple) and result:
            rows = list(result[0]) if result[0] is not None else []
        elif result is not None:
            rows = list(result) if hasattr(result, "__iter__") else []

        assert rows, "Cypher count query returned no rows"
        first_row = rows[0]
        node_count = (
            first_row.get("node_count")
            if isinstance(first_row, dict)
            else getattr(first_row, "node_count", None)
        )
        assert node_count == 1, (
            f"EntityNode.save did not MERGE by uuid — found {node_count} "
            f"nodes for uuid {fixed_uuid} after two saves. AC-GSM-009-13 "
            f"failure: the seed's idempotency property is broken until the "
            f"fork-side behaviour is restored."
        )
    finally:
        # Cleanup: drop the entire probe graph.
        try:
            cleanup_cypher = "MATCH (n) DETACH DELETE n"
            cleanup_result = target_driver.execute_query(cleanup_cypher)
            if asyncio.iscoroutine(cleanup_result):
                await cleanup_result
        except Exception:
            # Best-effort cleanup; don't shadow a more interesting test
            # failure with a cleanup error.
            pass
        await wrapper.close()
