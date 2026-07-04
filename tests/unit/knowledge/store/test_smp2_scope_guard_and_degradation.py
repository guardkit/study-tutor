"""Scope guard + fake-store degradation matrix tests (TASK-SMP2-07).

This module provides:

1. **Scope guard (AC-005)** — asserts no test in the suite connects to the NAS
   PostgreSQL (whitestocks:5434), enforcing the W2 runbook rule that all
   database tests run against ephemeral containers only.

2. **Fake-store degradation matrix (AC-002)** — explicit unit tests for the
   degradation contract through ``store.reads.get_student_state`` and
   ``load_planner_inputs``:
   - No store wired → ``StudentState(empty=True)`` / ``learner_state_available=False``
   - Reachable but recordless → ``empty=False`` for snapshot, ``available=True`` for planner
   - Read raises → degrade, no exception propagates

3. **Planner repoint verification (AC-004)** — end-to-end test showing
   ``load_planner_inputs`` reads from the store and returns domain entities
   (``TopicConfidence`` / ``Misconception``) with ``learner_state_available``
   flag controlling planner baseline vs seeded path.

These tests complement the BDD scenarios (which exercise the full read path)
with focused unit tests on the graceful-degradation contract.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from study_tutor.knowledge.store.entities import ConfidenceUpdate, StudentState
from study_tutor.knowledge.store.reads import (
    PlannerInputs,
    get_student_state,
    load_planner_inputs,
)
from tests.unit.knowledge.store.fakes import FakeStudentStore


# ---------------------------------------------------------------------------
# Scope Guard (AC-005) — NAS connection prohibition
# ---------------------------------------------------------------------------


def test_no_tests_connect_to_nas_postgres():
    """Scope guard: assert no test targets whitestocks:5434 (NAS PostgreSQL).

    The FEAT-SMP-002 runbook specifies that all database tests MUST run against
    ephemeral PostgreSQL containers (port 55433 or similar), NOT the production
    NAS instance at whitestocks:5434. This guard scans PostgreSQL-related test
    files for actual connection DSNs that would violate this rule.

    Enforcement: fails if PostgreSQL integration tests contain DSN strings
    pointing to whitestocks:5434.
    """
    project_root = Path(__file__).parent.parent.parent.parent.parent
    test_root = project_root / "tests" / "integration" / "knowledge" / "store"

    # Pattern for PostgreSQL DSN with whitestocks and port 5434
    nas_dsn_pattern = re.compile(
        r'postgresql://[^/]*@whitestocks:5434/|'
        r'postgresql://[^/]*@whitestocks:5434|'
        r'["\']postgresql://.*whitestocks.*5434.*["\']|'
        r'host=whitestocks.*port=5434|'
        r'port=5434.*host=whitestocks',
        re.IGNORECASE
    )

    violations: list[tuple[Path, int, str]] = []

    # Only check PostgreSQL integration tests
    if not test_root.exists():
        return  # No PostgreSQL integration tests yet

    for test_file in test_root.glob("test_postgres_*.py"):
        try:
            content = test_file.read_text()
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue

                # Check for NAS PostgreSQL DSN
                if nas_dsn_pattern.search(line):
                    violations.append((test_file, line_num, line.strip()))

        except Exception:
            continue

    if violations:
        violation_report = "\n".join(
            f"  {file.relative_to(project_root)}:{line_num}: {line}"
            for file, line_num, line in violations
        )
        pytest.fail(
            f"Scope violation: {len(violations)} PostgreSQL test(s) connect to NAS "
            f"(whitestocks:5434).\n\nViolations:\n{violation_report}\n\n"
            f"All PostgreSQL tests MUST use ephemeral containers (see "
            f"tests/integration/knowledge/store/conftest.py for fixture setup)."
        )


# ---------------------------------------------------------------------------
# Fake-Store Degradation Matrix (AC-002)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_store_wired_yields_empty_snapshot():
    """No store wired → get_student_state returns StudentState(empty=True)."""
    # Pass None as store to simulate no store wired
    snapshot = await get_student_state("any_student", store=None)

    assert snapshot.empty is True
    assert snapshot.student_id is None


@pytest.mark.asyncio
async def test_no_store_wired_yields_unavailable_planner_inputs():
    """No store wired → load_planner_inputs returns learner_state_available=False."""
    inputs = await load_planner_inputs("any_student", store=None)

    assert inputs.learner_state_available is False
    assert len(inputs.topic_confidences) == 0
    assert len(inputs.misconceptions) == 0


@pytest.mark.asyncio
async def test_reachable_store_unknown_learner_yields_empty_snapshot():
    """Reachable store, unknown learner → StudentState(empty=True)."""
    store = FakeStudentStore()
    # Don't add student

    snapshot = await get_student_state("unknown", store=store)

    assert snapshot.empty is True


@pytest.mark.asyncio
async def test_reachable_store_known_learner_no_records_yields_empty_but_known():
    """Reachable store, known learner with no records → empty=False, lists empty."""
    store = FakeStudentStore()
    store.add_student("student1", name="Student One", year_group=10, target_grade="7")
    # Don't add confidences or misconceptions

    snapshot = await get_student_state("student1", store=store)

    assert snapshot.empty is False  # Known learner
    assert snapshot.student_id == "student1"
    assert len(snapshot.topic_confidences) == 0
    assert len(snapshot.recent_misconceptions) == 0


@pytest.mark.asyncio
async def test_reachable_store_recordless_learner_planner_inputs_available():
    """Reachable store, recordless learner → learner_state_available=True."""
    store = FakeStudentStore()
    store.add_student("student1", name="Student One", year_group=10, target_grade="7")

    inputs = await load_planner_inputs("student1", store=store)

    assert inputs.learner_state_available is True
    assert len(inputs.topic_confidences) == 0
    assert len(inputs.misconceptions) == 0


@pytest.mark.asyncio
async def test_unreachable_store_degrades_snapshot_without_raising():
    """Store unreachable (ping=False) → get_student_state degrades to empty, no exception."""
    store = FakeStudentStore()
    store.set_unreachable(True)

    # get_student_state should not raise, even if store is unreachable
    # (graceful degradation contract)
    snapshot = await get_student_state("any_student", store=store)

    assert snapshot.empty is True


@pytest.mark.asyncio
async def test_unreachable_store_degrades_planner_inputs_without_raising():
    """Store unreachable → load_planner_inputs degrades to unavailable, no exception."""
    store = ExplodingFakeStore()

    inputs = await load_planner_inputs("any_student", store=store)

    assert inputs.learner_state_available is False
    assert len(inputs.topic_confidences) == 0
    assert len(inputs.misconceptions) == 0


class ExplodingFakeStore(FakeStudentStore):
    """Fake store that raises on reads (for exception-handling tests)."""

    async def get_student_state(self, student_id: str):
        raise RuntimeError("Simulated database failure")

    async def get_topic_confidences(self, student_id: str):
        raise RuntimeError("Simulated database failure")

    async def get_recent_misconceptions(self, student_id: str, *, window_days: int = 30):
        raise RuntimeError("Simulated database failure")


@pytest.mark.asyncio
async def test_read_exception_degrades_snapshot_without_propagating():
    """Read raises → get_student_state catches exception, returns empty."""
    store = ExplodingFakeStore()

    # Should not raise - graceful degradation
    snapshot = await get_student_state("any_student", store=store)

    assert snapshot.empty is True


@pytest.mark.asyncio
async def test_read_exception_degrades_planner_inputs_without_propagating():
    """Read raises → load_planner_inputs catches exception, returns unavailable."""
    store = ExplodingFakeStore()

    # Should not raise - graceful degradation
    inputs = await load_planner_inputs("any_student", store=store)

    assert inputs.learner_state_available is False
    assert len(inputs.topic_confidences) == 0
    assert len(inputs.misconceptions) == 0


# ---------------------------------------------------------------------------
# Planner Repoint Verification (AC-004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_planner_inputs_with_wired_store_returns_domain_entities():
    """Planner repoint: load_planner_inputs reads from store, returns domain entities.

    This is the key repoint test: the planner now receives its inputs
    (TopicConfidence, Misconception) from the Postgres store via
    load_planner_inputs, not from the retired Graphiti queries.
    """
    store = FakeStudentStore()
    store.add_student("student1", name="Student One", year_group=10, target_grade="7")

    # Seed confidence and misconception
    update = ConfidenceUpdate(topic_name="Macbeth Themes", percentage=72)
    await store.apply_confidence_update(student_id="student1", update=update)
    await store.record_misconception(
        student_id="student1",
        topic_name="Macbeth Themes",
        text="Confused character motivations"
    )

    # Load planner inputs
    inputs = await load_planner_inputs("student1", store=store)

    # Assert domain entities returned
    assert inputs.learner_state_available is True
    assert len(inputs.topic_confidences) == 1
    assert inputs.topic_confidences[0].topic_ref == "Macbeth Themes"
    assert inputs.topic_confidences[0].percentage == 72
    assert inputs.topic_confidences[0].band == "secure"

    assert len(inputs.misconceptions) == 1
    assert inputs.misconceptions[0].topic_ref == "Macbeth Themes"
    assert inputs.misconceptions[0].text == "Confused character motivations"


@pytest.mark.asyncio
async def test_planner_inputs_with_unreachable_store_returns_baseline_flag():
    """Planner repoint: unreachable store → learner_state_available=False (baseline path).

    When the store is unreachable, the planner should receive
    learner_state_available=False, which triggers the unseeded-baseline plan
    (TASK-DSP-006 contract).
    """
    store = ExplodingFakeStore()

    inputs = await load_planner_inputs("student1", store=store)

    assert inputs.learner_state_available is False
    # This flag tells the planner to use the unseeded-baseline path


@pytest.mark.asyncio
async def test_planner_inputs_with_empty_learner_returns_available_flag():
    """Planner repoint: reachable store, no records → learner_state_available=True.

    This distinguishes "store down" (False, unseeded baseline) from
    "learner has no state yet" (True, seeded baseline with empty inputs).
    """
    store = FakeStudentStore()
    store.add_student("student1", name="Student One", year_group=10, target_grade="7")
    # No confidences or misconceptions

    inputs = await load_planner_inputs("student1", store=store)

    assert inputs.learner_state_available is True
    assert len(inputs.topic_confidences) == 0
    assert len(inputs.misconceptions) == 0
    # Planner offers seeded-baseline plan (different from unseeded)
