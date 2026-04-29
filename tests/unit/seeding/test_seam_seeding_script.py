"""Seam tests for the Lilymay baseline seeding script (TASK-GSM-006).

Lifted verbatim from
``tasks/backlog/graphiti-student-model/TASK-GSM-006-seeding-script.md``
(``## Seam Tests``) so the upstream contracts from TASK-GSM-003,
TASK-GSM-004, and TASK-GSM-005 are pinned at this boundary:

- :class:`GraphitiClient` (TASK-GSM-003): seeding requires a live client.
- :class:`SharedAsyncWriteHelper` (TASK-GSM-004): every seed write uses
  ``flush_id="SEED"``.
- :class:`StudentModelQueries` (TASK-GSM-005): post-seed verification uses
  :func:`get_student_state`.
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


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiClient")
def test_graphiti_client_required_at_seed_time() -> None:
    """Verify GraphitiClient contract is honoured by the seeding script.

    Contract: Script obtains a real client via get_client(config) and exits
              non-zero if client is None (seeding is NOT a degradation path).
    Producer: TASK-GSM-003
    """
    # Format assertion: a script-level helper that branches on client=None and
    # raises SystemExit(2) is the contract. Verify by importing the helper.
    from scripts.seed_student_model import require_client_or_exit

    with pytest.raises(SystemExit) as exc_info:
        require_client_or_exit(client=None)
    assert exc_info.value.code == 2  # store unreachable per @seeding scenario


@pytest.mark.seam
@pytest.mark.integration_contract("SharedAsyncWriteHelper")
def test_seed_writes_use_seed_flush_id() -> None:
    """Verify SharedAsyncWriteHelper contract is honoured by the seeding script.

    Contract: Seed writes use helper.schedule_write(..., flush_id='SEED');
              script awaits helper.drain() before exit.
    Producer: TASK-GSM-004
    """
    src = _SCRIPT_PATH.read_text()
    tree = ast.parse(src)

    seen_flush_ids: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "schedule_write"
        ):
            for kw in node.keywords:
                if kw.arg == "flush_id" and isinstance(kw.value, ast.Constant):
                    seen_flush_ids.append(kw.value.value)

    assert (
        len(seen_flush_ids) > 0
    ), "seeding script must call helper.schedule_write at least once"
    assert all(fid == "SEED" for fid in seen_flush_ids), (
        f"All seed writes must use flush_id='SEED', got: {seen_flush_ids}"
    )


@pytest.mark.seam
@pytest.mark.integration_contract("StudentModelQueries")
def test_post_seed_verification_gate() -> None:
    """Verify StudentModelQueries contract is honoured as the post-seed gate.

    Contract: After seeding, script calls get_student_state(client, 'lilymay')
              as a verification gate; non-empty StudentState confirms seed landed.
    Producer: TASK-GSM-005
    """
    src = _SCRIPT_PATH.read_text()
    tree = ast.parse(src)

    found_query_import = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", "") or ""
            names = [n.name for n in node.names]
            if "queries" in module and "get_student_state" in names:
                found_query_import = True
                break

    assert found_query_import, (
        "Seeding script must import get_student_state from "
        "study_tutor.knowledge.queries to act as the post-seed verification gate"
    )
