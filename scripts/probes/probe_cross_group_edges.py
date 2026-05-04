"""TASK-GSM-008 G2 probe — cross-group-graph edge writes against live FalkorDB.

Background
----------

The ``graphiti-core`` fork pinned at ``v0.29.5-guardkit.2[falkordb]`` ships
the bug-#8 fix that isolates each ``group_id`` into its own FalkorDB named
graph. ``EntityEdge`` carries a single ``group_id`` field, but the typed-entity
seed under TASK-GSM-007/-009 needs to draw relationships **across**
partitions — e.g. ``Student`` (in ``student-lilymay``) → ``Subject``
(in ``subject-english-literature``). The behaviour of ``EntityEdge.save()``
when its source and target nodes live in different named graphs is **not
documented** by the upstream library and is not obvious from a code read.

This probe answers the question empirically against the canonical Phase-1
stack (whitestocks FalkorDB) and persists its outcome as a JSON dict so it
can be pasted verbatim into ``ADR-ARCH-021`` (or whichever ADR this resolves
into). The decision tree from the TASK-GSM-008 spec:

- ``edge_outcomes.save == "ok"`` and ``edge_outcomes.read_count >= 1``:
  **G2 is solvable**. Cross-group edges work; pick G1 option (a)
  (multi-group read via STUDIES traversal).
- ``edge_outcomes.save`` is an error: **G2 forces G1 fallback**. Pick G1
  option (b) (denormalise) or (c) (co-locate). Cross-group edges deferred.
- ``edge_outcomes.save == "ok"`` but ``read_count == 0`` (silent dangle):
  **also forces G1 fallback**. Document the silent-failure mode.

Usage
-----

::

    /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python \\
      scripts/probes/probe_cross_group_edges.py

Exit codes:

- ``0`` — probe ran end-to-end; outcome dict printed as JSON to stdout.
  This includes the silent-dangle and save-error cases — they are valid
  outcomes for the design question, not script failures.
- ``2`` — graphiti client unavailable (FalkorDB unreachable, library
  missing, healthcheck timed out). Probe could not run.
- ``3`` — unexpected exception outside the probe's instrumented try/except
  envelope. Stack trace on stderr.

Self-cleanup
------------

The probe deletes its ``student-probetest`` and ``subject-probetest`` named
graphs on both success and failure paths via ``GRAPH.DELETE`` Cypher
(FalkorDB-specific). If cleanup itself fails the partitions are logged so
they can be cleared manually with::

    redis-cli -h whitestocks -p 6379 GRAPH.DELETE student-probetest
    redis-cli -h whitestocks -p 6379 GRAPH.DELETE subject-probetest

This is a one-off design probe; do not import it from production code.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from study_tutor.knowledge.graphiti_client import (
    DEFAULT_GRAPHITI_YAML_PATH,
    get_client,
    load_graphiti_config_from_yaml,
)


GROUP_STUDENT: str = "student-probetest"
GROUP_SUBJECT: str = "subject-probetest"
EDGE_NAME: str = "STUDIES"

EXIT_OK: int = 0
EXIT_CLIENT_UNAVAILABLE: int = 2
EXIT_UNEXPECTED: int = 3


# Quiet noisy modules so the JSON outcome is the only thing on stdout.
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
for noisy in (
    "study_tutor",
    "graphiti_core",
    "httpx",
    "openai",
):
    logging.getLogger(noisy).setLevel(logging.ERROR)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _err(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _clone_or_same(driver: Any, database: str) -> Any:
    """Return ``driver.clone(database)`` if available, else ``driver``.

    The FalkorDB driver exposes ``clone(database=...)`` (per fork v0.29.5).
    Other drivers (Neo4j, Kuzu) don't partition by database in the same way
    so the probe falls back to the original driver. Phase-1 always uses
    FalkorDB so the fallback is dead-code under the canonical stack but
    keeps the probe runnable on a developer laptop with a different driver.
    """
    clone_fn = getattr(driver, "clone", None)
    if clone_fn is None:
        return driver
    try:
        return clone_fn(database=database)
    except TypeError:
        # Some drivers expose ``clone()`` with different signatures; if our
        # call shape doesn't match we'd rather degrade to the parent driver
        # than crash the probe before it produces any data.
        return driver


async def _run_probe(driver: Any) -> dict[str, Any]:
    """Execute the cross-group-edge probe against ``driver``.

    Returns a dict with these keys:

    - ``provider`` — the driver's provider enum value (``falkordb`` etc.).
    - ``student_uuid`` / ``subject_uuid`` — the UUIDs of the probe nodes.
    - ``student_save`` / ``subject_save`` — node-write outcomes.
    - ``edge_save`` — edge-save outcome (``"ok"`` or an exception summary).
    - ``edge_read_in_student_graph`` — count + first-edge details when
      reading edges back via ``EntityEdge.get_by_group_ids`` against the
      student-graph driver.
    - ``traversal`` — outcome of a Cypher MATCH from Student to Subject in
      the student-graph (which would only succeed if the named-graph
      isolation allows cross-group-traversal — which it almost certainly
      doesn't, but we measure rather than guess).
    """
    # graphiti-core EntityNode/Edge are imported lazily so `--help`-style
    # usage doesn't pull the whole graph stack into the import.
    from graphiti_core.edges import EntityEdge
    from graphiti_core.nodes import EntityNode

    outcome: dict[str, Any] = {
        "provider": getattr(getattr(driver, "provider", None), "value", str(getattr(driver, "provider", "unknown"))),
        "captured_at": _now_utc().isoformat(),
    }

    student_uuid = str(uuid.uuid4())
    subject_uuid = str(uuid.uuid4())
    outcome["student_uuid"] = student_uuid
    outcome["subject_uuid"] = subject_uuid

    student_driver = _clone_or_same(driver, GROUP_STUDENT)
    subject_driver = _clone_or_same(driver, GROUP_SUBJECT)

    # ----------------------------------------------------------------- Step 1
    # Write nodes into separate named graphs.
    try:
        await EntityNode(
            uuid=student_uuid,
            name="ProbeStudent",
            labels=["Entity", "Student"],
            group_id=GROUP_STUDENT,
            attributes={},
        ).save(student_driver)
        outcome["student_save"] = "ok"
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        outcome["student_save"] = _err(exc)

    try:
        await EntityNode(
            uuid=subject_uuid,
            name="ProbeSubject",
            labels=["Entity", "Subject"],
            group_id=GROUP_SUBJECT,
            attributes={},
        ).save(subject_driver)
        outcome["subject_save"] = "ok"
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        outcome["subject_save"] = _err(exc)

    # ----------------------------------------------------------------- Step 2
    # Attempt to write a STUDIES edge from Student → Subject with
    # ``group_id = GROUP_STUDENT`` (i.e. the edge "lives" in the student
    # graph but its target node lives in the subject graph).
    try:
        edge = EntityEdge(
            source_node_uuid=student_uuid,
            target_node_uuid=subject_uuid,
            name=EDGE_NAME,
            fact="probe: ProbeStudent STUDIES ProbeSubject",
            group_id=GROUP_STUDENT,
            created_at=_now_utc(),
            attributes={},
        )
        await edge.save(student_driver)
        outcome["edge_save"] = "ok"
        outcome["edge_uuid"] = edge.uuid
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        outcome["edge_save"] = _err(exc)
        outcome["edge_uuid"] = None

    # ----------------------------------------------------------------- Step 3
    # Read edges back via the typed API. This is what the seed-side code
    # would do at AC-006 verification time. We deliberately query the
    # student-graph driver — the edge was written with
    # ``group_id=GROUP_STUDENT`` so this is the natural lookup surface.
    try:
        edges = await EntityEdge.get_by_group_ids(student_driver, [GROUP_STUDENT])
        edges_list = list(edges or [])
        outcome["edge_read_in_student_graph"] = {
            "count": len(edges_list),
            "first_source_uuid": edges_list[0].source_node_uuid if edges_list else None,
            "first_target_uuid": edges_list[0].target_node_uuid if edges_list else None,
            "first_name": edges_list[0].name if edges_list else None,
        }
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        outcome["edge_read_in_student_graph"] = {"error": _err(exc)}

    # ----------------------------------------------------------------- Step 4
    # Try a Cypher traversal from the Student node to a Subject node,
    # executed against the student-graph driver. If the named-graph fix
    # isolates each group_id into its own FalkorDB graph (which it does),
    # the Subject node simply isn't visible in the student graph — so this
    # MATCH should return zero rows even if the edge "save" reported ok.
    try:
        cypher = (
            "MATCH (s:Entity {uuid: $student_uuid})-[r]->(t) "
            "RETURN type(r) AS rel_type, t.uuid AS target_uuid, t.name AS target_name"
        )
        result = student_driver.execute_query(cypher, student_uuid=student_uuid)
        if asyncio.iscoroutine(result):
            result = await result
        # graphiti-core's execute_query returns a tuple (records, summary,
        # keys) or similar. Normalise to a list of dict rows.
        rows: list[Any]
        if isinstance(result, tuple) and result:
            rows = list(result[0]) if result[0] is not None else []
        elif result is None:
            rows = []
        else:
            rows = list(result) if hasattr(result, "__iter__") else []

        outcome["traversal_in_student_graph"] = {
            "count": len(rows),
            "rows_repr": [repr(r) for r in rows[:3]],  # first 3 for context
        }
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        outcome["traversal_in_student_graph"] = {"error": _err(exc)}

    return outcome


async def _cleanup(driver: Any, outcome: dict[str, Any]) -> None:
    """Delete the probe's ``*-probetest`` named graphs.

    FalkorDB-specific: ``GRAPH.DELETE`` is a Redis-module command. We issue
    it via the driver's underlying connection where possible. If cleanup
    fails the partitions are logged to stderr so they can be cleared
    manually — we never raise out of cleanup because the probe's design
    outcome is already in hand and the script must exit cleanly.
    """
    cleanup_outcome: dict[str, str] = {}
    for graph_name in (GROUP_STUDENT, GROUP_SUBJECT):
        graph_driver = _clone_or_same(driver, graph_name)
        try:
            # Two strategies: prefer GRAPH.DELETE via the driver's
            # underlying Redis client; fall back to a Cypher MATCH ... DELETE
            # against every node (works on Neo4j/Kuzu too if a developer
            # ever points the probe at a non-FalkorDB stack).
            inner = getattr(graph_driver, "client", None) or getattr(graph_driver, "_driver", None)
            redis_conn = getattr(inner, "connection_pool", None)
            if redis_conn is not None:
                # FalkorDB exposes the Redis client directly; the named-graph
                # delete is a single-key DEL on the graph key.
                try:
                    await asyncio.to_thread(
                        inner.execute_command, "GRAPH.DELETE", graph_name
                    )
                    cleanup_outcome[graph_name] = "ok (GRAPH.DELETE)"
                    continue
                except Exception:  # noqa: BLE001
                    # Fall through to the Cypher path below — the FalkorDB
                    # client API has shifted between releases and this
                    # is purely a cleanup nicety.
                    pass

            # Fallback: delete every node + relationship in the graph.
            cypher = "MATCH (n) DETACH DELETE n"
            result = graph_driver.execute_query(cypher)
            if asyncio.iscoroutine(result):
                await result
            cleanup_outcome[graph_name] = "ok (DETACH DELETE)"
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            cleanup_outcome[graph_name] = _err(exc)
            print(
                f"WARNING: cleanup failed for {graph_name!r}: {_err(exc)}\n"
                f"  Manual cleanup: redis-cli -h whitestocks -p 6379 "
                f"GRAPH.DELETE {graph_name}",
                file=sys.stderr,
            )
    outcome["cleanup"] = cleanup_outcome


async def main() -> int:
    """Async entry point — returns the script's exit code."""
    config = load_graphiti_config_from_yaml(DEFAULT_GRAPHITI_YAML_PATH)
    wrapper = await get_client(config)
    if wrapper is None:
        print(
            json.dumps(
                {"error": "graphiti client unavailable — see stderr logs"},
                indent=2,
            )
        )
        return EXIT_CLIENT_UNAVAILABLE

    inner = wrapper.client_or_none
    driver = getattr(inner, "driver", None)
    if driver is None:
        print(
            json.dumps({"error": "graphiti client missing 'driver' attribute"}, indent=2)
        )
        await wrapper.close()
        return EXIT_CLIENT_UNAVAILABLE

    outcome: dict[str, Any] = {}
    try:
        outcome = await _run_probe(driver)
    finally:
        try:
            await _cleanup(driver, outcome)
        finally:
            await wrapper.close()

    print(json.dumps(outcome, indent=2, default=str))
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - direct invocation only
    try:
        sys.exit(asyncio.run(main()))
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — top-level safety net
        traceback.print_exc()
        sys.exit(EXIT_UNEXPECTED)
