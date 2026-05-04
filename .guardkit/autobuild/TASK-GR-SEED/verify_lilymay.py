"""Verify Lilymay baseline persisted (TASK-GR-SEED AC-SEED-02 / AC-SEED-03).

Run after seed_student_model.py. Captures evidence for player_turn_*.json.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.queries import get_student_state


async def main() -> int:
    """Capture AC-SEED-02 and AC-SEED-03 evidence as one JSON document."""
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    if wrapper is None:
        print(json.dumps({"error": "graphiti client unavailable"}))
        return 2
    inner = wrapper.client_or_none
    try:
        # AC-SEED-03: get_student_state returns populated StudentState
        state = await get_student_state(inner, "lilymay")
        state_payload: dict[str, Any] = {}
        if state is not None:
            for field in (
                "empty",
                "year_group",
                "target_grade",
                "subjects",
                "topic_confidences",
            ):
                value = getattr(state, field, None)
                # Coerce to JSON-friendly forms.
                if isinstance(value, dict):
                    state_payload[field] = {k: str(v) for k, v in value.items()}
                elif isinstance(value, (list, tuple)):
                    state_payload[field] = [str(v) for v in value]
                else:
                    state_payload[field] = value

        # AC-SEED-02: search_nodes-equivalent against student-lilymay group.
        #
        # MCP graphiti tools require permissions not granted in this Player
        # runtime, so go via study_tutor's read seam to produce equivalent
        # evidence. ``_read_student_partition`` mirrors the guardkit graphiti
        # fork's per-group driver-clone decorator on writes (TASK-FORK-PATCH
        # bug #8) — the writer isolates each group_id into its own FalkorDB
        # named graph, so a direct ``EntityNode.get_by_group_ids(driver, [...])``
        # against the default graph would return ``[]`` even when writes
        # succeeded.
        from study_tutor.knowledge.queries import _read_student_partition
        nodes_payload: list[dict[str, Any]] = []
        try:
            entity_nodes, _entity_edges = await _read_student_partition(
                inner, ["student-lilymay"], limit=20
            )
            for node in entity_nodes:
                nodes_payload.append(
                    {
                        "name": getattr(node, "name", None),
                        "labels": list(getattr(node, "labels", []) or []),
                        "summary": getattr(node, "summary", None),
                        "group_id": getattr(node, "group_id", None),
                        "attributes_keys": sorted(
                            (getattr(node, "attributes", {}) or {}).keys()
                        ),
                    }
                )
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            nodes_payload = [{"error": f"{type(exc).__name__}: {exc}"}]

        evidence = {
            "ac_seed_03_get_student_state": state_payload,
            "ac_seed_02_student_lilymay_nodes": nodes_payload,
        }
        print(json.dumps(evidence, indent=2, default=str))
    finally:
        await wrapper.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
