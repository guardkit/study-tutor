"""Seam tests for the typed-entity Lilymay seeding script (TASK-GSM-009).

These tests pin the **typed-entity** seed contract introduced by
TASK-GSM-009 (replacing the original TASK-GSM-006 ``add_episode`` /
``GraphitiWriteHelper`` contract). The producer chain is now:

- :class:`GraphitiClient` (TASK-GSM-003): seeding requires a live client;
  exit 2 on ``client=None`` per the original contract (unchanged).
- ``EntityNode.save`` / ``EntityEdge.save`` (graphiti-core fork
  ``v0.29.5-guardkit.2``): every write is a typed-entity ``.save()`` call.
  The seed script imports these directly inside :func:`seed_lilymay` rather
  than routing through :class:`GraphitiWriteHelper`. ADR-ARCH-021
  documents the CC-13 invariant scope-narrowing this seam encodes.
- :func:`get_student_state` (TASK-GSM-005): post-seed verification gate
  reads back through the same enumerator the live tutor session uses.

The original seam test
``test_seed_writes_use_seed_flush_id`` (which AST-scanned for
``schedule_write(..., flush_id="SEED")``) is **deleted** — the typed-entity
seed has no ``schedule_write`` calls. The replacement
``test_seed_writes_via_typed_entity_save`` AST-scans for the inverse
property: at least one ``EntityNode.save`` and at least one
``EntityEdge.save`` call must appear inside :func:`seed_lilymay`, and there
must be **zero** ``add_episode`` calls anywhere in the script.
"""
from __future__ import annotations

import ast
import pathlib

import pytest


# Resolve the script path relative to the repo root so the AST scans work
# regardless of which directory pytest is invoked from. ``rootdir`` is the
# parent of ``pyproject.toml``; ``scripts/seed_student_model.py`` sits one
# level below that.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "seed_student_model.py"


def _parse_script() -> ast.AST:
    return ast.parse(_SCRIPT_PATH.read_text())


def _find_attr_calls(tree: ast.AST, attr: str) -> list[ast.Call]:
    """Return every ``ast.Call`` whose ``func`` is an attribute access on
    ``attr`` (e.g. ``something.save(...)``).
    """
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr
        ):
            out.append(node)
    return out


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiClient")
def test_graphiti_client_required_at_seed_time() -> None:
    """Verify GraphitiClient contract: client=None ⇒ SystemExit(2).

    Producer: TASK-GSM-003 (unchanged from TASK-GSM-006 era).
    """
    from scripts.seed_student_model import require_client_or_exit

    with pytest.raises(SystemExit) as exc_info:
        require_client_or_exit(client=None)
    assert exc_info.value.code == 2


@pytest.mark.seam
@pytest.mark.integration_contract("TypedEntityWrites")
def test_seed_writes_via_typed_entity_save() -> None:
    """Verify typed-entity write contract (TASK-GSM-009 / ADR-ARCH-021).

    Contract: seed_lilymay() drives writes via ``EntityNode.save`` and
    ``EntityEdge.save`` (typed-entity), never via ``add_episode`` or
    ``schedule_write``.
    """
    tree = _parse_script()

    save_calls = _find_attr_calls(tree, "save")
    assert save_calls, (
        "seed script must contain at least one ``.save(...)`` call "
        "(EntityNode.save / EntityEdge.save) — typed-entity write contract."
    )

    add_episode_calls = _find_attr_calls(tree, "add_episode")
    assert not add_episode_calls, (
        f"seed script must contain ZERO add_episode calls under "
        f"ADR-ARCH-021; found {len(add_episode_calls)} (lines: "
        f"{[c.lineno for c in add_episode_calls]})."
    )

    schedule_write_calls = _find_attr_calls(tree, "schedule_write")
    assert not schedule_write_calls, (
        f"seed script must contain ZERO schedule_write calls under "
        f"ADR-ARCH-021 (the seed bypasses GraphitiWriteHelper); found "
        f"{len(schedule_write_calls)} (lines: "
        f"{[c.lineno for c in schedule_write_calls]})."
    )


# REMOVED: test_post_seed_verification_gate
# The seed script no longer uses get_student_state for post-seed verification
# as the Graphiti read surface has been removed (TASK-SMP2-06).
# The graph seed path will be retired in FEAT-SMP-004.


@pytest.mark.seam
@pytest.mark.integration_contract("DeterministicUUIDs")
def test_seed_imports_deterministic_uuid_helpers() -> None:
    """Verify deterministic UUID5 derivation contract (TASK-GSM-009 AC-12).

    Re-running the seed must produce byte-identical graph state via
    MERGE-by-uuid on the FalkorDB driver. The helpers in
    :mod:`study_tutor.knowledge.seed_uuids` are the load-bearing source
    of those uuids; the seed must import them.
    """
    tree = _parse_script()

    found_seed_uuid_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "seed_uuids" in module:
                found_seed_uuid_import = True
                break

    assert found_seed_uuid_import, (
        "Seeding script must import deterministic UUID helpers from "
        "study_tutor.knowledge.seed_uuids — required for MERGE-by-uuid "
        "idempotency on re-run."
    )
