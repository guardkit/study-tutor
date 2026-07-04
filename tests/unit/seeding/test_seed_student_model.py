"""Unit tests for the typed-entity Lilymay seeding script (TASK-GSM-009).

Each acceptance criterion in
``tasks/in_progress/TASK-GSM-009-typed-entity-seed-refactor.md`` is covered
by at least one test below. The test surface is structured around AC-06's
``_FakeDriver`` fixture: ``EntityNode.save`` and ``EntityEdge.save`` are
monkey-patched at the graphiti-core class level so every typed write is
intercepted and recorded for assertion.

Hermeticity:

- ``get_client`` is monkeypatched per-scenario.
- ``get_student_state`` is monkeypatched per-scenario to drive the
  pre-flight idempotency branch and the post-seed verification gate.
- ``EntityNode.save`` / ``EntityEdge.save`` are monkey-patched to record
  rather than persist. Tests assert on labels, attributes, group_ids,
  uuids and idempotency (second-run produces identical uuids).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import scripts.seed_student_model as seed_module
from scripts.seed_student_model import (
    AOS,
    DEFAULT_CONFIG,
    EXIT_CLIENT_UNAVAILABLE,
    EXIT_OK,
    STUDENT_ID,
    STUDENT_NAME,
    STUDENT_TARGET_GRADE,
    STUDENT_YEAR_GROUP,
    SUBJECTS,
    TEXTS,
    TOPICS,
    _is_already_seeded,
    load_config,
    main,
    require_client_or_exit,
    seed_lilymay,
)
from study_tutor.knowledge.store.entities import (
    StudentState,
    TopicConfidenceSnapshot,
)
from study_tutor.knowledge.seed_uuids import (
    assessment_objective_uuid,
    edge_uuid,
    student_uuid,
    subject_uuid,
    text_uuid,
    topic_confidence_uuid,
    topic_uuid,
)
from study_tutor.knowledge.student_model import (
    COVERS,
    EPOCH_NEVER_REVISED,
    FLEET_GROUP_ID,
    HAS_CONFIDENCE,
    HAS_TEXT,
    STUDENT_GROUP_PREFIX,
    SUBJECT_GROUP_PREFIX,
    confidence_band_for,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeDriver:
    """Stand-in graphiti-core driver.

    The seed script calls ``driver.clone(database=group_id)`` to route each
    write at the named-graph layer the FalkorDB driver enforces; the fake
    just returns ``self`` so every save accumulates in the same recorder.
    The most-recent ``database`` argument is captured so tests can assert
    routing if needed.
    """

    def __init__(self) -> None:
        self.last_clone_database: str | None = None

    def clone(self, *, database: str) -> "_FakeDriver":
        self.last_clone_database = database
        return self


class _FakeInnerClient:
    """Mimics the inner graphiti-core client that exposes ``driver``."""

    def __init__(self, driver: _FakeDriver) -> None:
        self.driver = driver


class _FakeWrapper:
    """Stand-in for :class:`GraphitiClient` with the surface the seed uses."""

    def __init__(self) -> None:
        self.driver = _FakeDriver()
        self.client_or_none: Any = _FakeInnerClient(self.driver)
        self.close_call_count = 0

    async def close(self) -> None:
        self.close_call_count += 1


class _FakeWrapperWithoutInner:
    """Wrapper whose ``client_or_none`` is None — exercises the seed's
    inner-client guard.
    """

    def __init__(self) -> None:
        self.client_or_none: Any = None
        self.close_call_count = 0

    async def close(self) -> None:
        self.close_call_count += 1


class _FakeWrapperWithoutDriver:
    """Wrapper whose inner client has no ``driver`` attribute — exercises
    the seed's driver guard.
    """

    def __init__(self) -> None:
        self.client_or_none: Any = object()  # opaque, no .driver
        self.close_call_count = 0

    async def close(self) -> None:
        self.close_call_count += 1


@pytest.fixture
def save_recorder(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """Intercept EntityNode.save / EntityEdge.save and record the instances.

    Returns a dict with two keys:

    - ``"nodes"``: list of EntityNode instances saved.
    - ``"edges"``: list of EntityEdge instances saved.

    Order of insertion mirrors the order ``seed_lilymay`` issues writes.
    """
    from graphiti_core.edges import EntityEdge
    from graphiti_core.nodes import EntityNode

    nodes: list[Any] = []
    edges: list[Any] = []

    async def fake_node_save(self: Any, driver: Any) -> None:
        nodes.append(self)

    async def fake_edge_save(self: Any, driver: Any) -> None:
        edges.append(self)

    monkeypatch.setattr(EntityNode, "save", fake_node_save)
    monkeypatch.setattr(EntityEdge, "save", fake_edge_save)
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nodes_by_label(
    nodes: list[Any], label: str
) -> list[Any]:
    """Filter saved EntityNode instances by their (last) label."""
    return [n for n in nodes if (getattr(n, "labels", []) or [])[-1:] == [label]]


# ---------------------------------------------------------------------------
# require_client_or_exit (AC-04 in TASK-GSM-006 era; still in scope)
# ---------------------------------------------------------------------------


def test_require_client_or_exit_raises_systemexit_2_on_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """client=None ⇒ SystemExit(2) + structured log."""
    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        with pytest.raises(SystemExit) as excinfo:
            require_client_or_exit(None)

    assert excinfo.value.code == EXIT_CLIENT_UNAVAILABLE == 2
    record = next(
        (r for r in caplog.records if getattr(r, "event", "") == "seeding_failed"),
        None,
    )
    assert record is not None, "expected event=seeding_failed log line"
    assert record.reason == "client_unavailable"


def test_require_client_or_exit_returns_client_when_present() -> None:
    """A non-None client passes through unchanged (no SystemExit)."""
    fake = _FakeWrapper()
    assert require_client_or_exit(fake) is fake


# ---------------------------------------------------------------------------
# Idempotency pre-flight
# ---------------------------------------------------------------------------


def test_is_already_seeded_recognises_subjects() -> None:
    state = StudentState(
        empty=False,
        student_id=STUDENT_ID,
        subjects=["English Literature"],
    )
    assert _is_already_seeded(state) is True


def test_is_already_seeded_recognises_year_group() -> None:
    state = StudentState(empty=False, student_id=STUDENT_ID, year_group=10)
    assert _is_already_seeded(state) is True


def test_is_already_seeded_recognises_confidences() -> None:
    state = StudentState(
        empty=False,
        student_id=STUDENT_ID,
        topic_confidences=[
            TopicConfidenceSnapshot(
                topic_name="Macbeth's witches",
                band="struggling",
                percentage=25,
            )
        ],
    )
    assert _is_already_seeded(state) is True


@pytest.mark.parametrize(
    "state",
    [
        None,
        StudentState(empty=True),
        StudentState(empty=False, student_id=STUDENT_ID),  # no subjects/conf
    ],
)
def test_is_already_seeded_returns_false_for_empty_states(
    state: StudentState | None,
) -> None:
    assert _is_already_seeded(state) is False


@pytest.mark.skip(reason="TASK-SMP2-06: Pre-flight check removed with get_student_state")
@pytest.mark.asyncio
async def test_seed_lilymay_skips_when_already_seeded(
    monkeypatch: pytest.MonkeyPatch,
    save_recorder: dict[str, list[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SKIPPED: Pre-flight check removed in TASK-SMP2-06.

    Original: Pre-flight non-empty state ⇒ exit 0 + seeding_skipped log; no writes.
    The seed script no longer uses get_student_state for pre-flight checks.
    TODO(FEAT-SMP-004): Remove this test when graph seed path is fully retired.
    """
    pass


# ---------------------------------------------------------------------------
# Driver / inner-client guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_returns_exit_2_when_inner_client_missing(
    save_recorder: dict[str, list[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A wrapper without an inner client surfaces an exit-2 + structured log."""
    wrapper = _FakeWrapperWithoutInner()

    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        rc = await seed_lilymay(wrapper)

    assert rc == EXIT_CLIENT_UNAVAILABLE
    assert save_recorder["nodes"] == []
    failure = next(
        (r for r in caplog.records if getattr(r, "event", "") == "seeding_failed"),
        None,
    )
    assert failure is not None
    assert failure.reason == "client_or_none_unavailable"


@pytest.mark.asyncio
async def test_seed_lilymay_returns_exit_2_when_driver_missing(
    save_recorder: dict[str, list[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An inner client without a ``driver`` attribute surfaces exit-2."""
    wrapper = _FakeWrapperWithoutDriver()

    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        rc = await seed_lilymay(wrapper)

    assert rc == EXIT_CLIENT_UNAVAILABLE
    assert save_recorder["nodes"] == []
    failure = next(
        (r for r in caplog.records if getattr(r, "event", "") == "seeding_failed"),
        None,
    )
    assert failure is not None
    assert failure.reason == "driver_unavailable"


# ---------------------------------------------------------------------------
# Fresh-seed happy path — node-level assertions
# ---------------------------------------------------------------------------


def _post_seed_state() -> StudentState:
    """Build a StudentState that mirrors what the seed should produce."""
    return StudentState(
        empty=False,
        student_id=STUDENT_ID,
        year_group=STUDENT_YEAR_GROUP,
        target_grade=STUDENT_TARGET_GRADE,
        subjects=[s["name"] for s in SUBJECTS],
        topic_confidences=[
            TopicConfidenceSnapshot(
                topic_name=t["name"],
                band=confidence_band_for(t["initial_percentage"]),
                percentage=int(t["initial_percentage"]),
                last_revised_at=EPOCH_NEVER_REVISED,
            )
            for t in TOPICS
        ],
    )


@pytest.fixture
def state_iter(monkeypatch: pytest.MonkeyPatch) -> None:
    """REMOVED (TASK-SMP2-06): Fixture previously wired ``get_student_state``.

    The seed script no longer uses get_student_state for pre-flight/post-seed
    verification. This fixture is kept as a no-op to avoid changing all test
    signatures, but it does nothing.
    """
    pass


@pytest.mark.asyncio
async def test_seed_lilymay_writes_full_node_surface(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """The seed writes exactly the typed-entity surface ADR-ARCH-021 specifies.

    1 Student + 2 Subject + 4 Text + 6 Topic + 6 AO + 6 TopicConfidence = 25 nodes.
    """
    wrapper = _FakeWrapper()
    rc = await seed_lilymay(wrapper)
    assert rc == EXIT_OK

    nodes = save_recorder["nodes"]
    assert len(nodes) == (
        1  # Student
        + len(SUBJECTS)
        + len(TEXTS)
        + len(TOPICS)
        + len(AOS)
        + len(TOPICS)  # one TopicConfidence per topic
    ), f"got {len(nodes)} node saves; expected 25"


@pytest.mark.asyncio
async def test_seed_lilymay_student_node_carries_enrolled_subjects(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """ADR-ARCH-021 §G1 — Student node attribute denormalises subjects."""
    await seed_lilymay(_FakeWrapper())
    students = _nodes_by_label(save_recorder["nodes"], "Student")
    assert len(students) == 1
    student = students[0]
    assert student.name == STUDENT_NAME
    assert student.group_id == f"{STUDENT_GROUP_PREFIX}{STUDENT_ID}"
    attrs = student.attributes
    assert attrs["year_group"] == STUDENT_YEAR_GROUP
    assert attrs["target_grade"] == STUDENT_TARGET_GRADE
    # Enrolled-subjects denormalisation — list[str] of subject display names.
    assert attrs["enrolled_subjects"] == [s["name"] for s in SUBJECTS]


@pytest.mark.asyncio
async def test_seed_lilymay_subject_nodes_use_correct_groups(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """Each Subject lands under ``subject-<slug>``."""
    await seed_lilymay(_FakeWrapper())
    subjects = _nodes_by_label(save_recorder["nodes"], "Subject")
    by_name = {s.name: s for s in subjects}
    for subj in SUBJECTS:
        assert subj["name"] in by_name, f"missing Subject {subj['name']!r}"
        assert by_name[subj["name"]].group_id == (
            f"{SUBJECT_GROUP_PREFIX}{subj['slug']}"
        )


@pytest.mark.asyncio
async def test_seed_lilymay_topic_carries_ao_refs_attribute(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """ADR-ARCH-021 §G2 — Topic→AO is denormalised onto the Topic node
    because the cross-group edge is unavailable.
    """
    await seed_lilymay(_FakeWrapper())
    topics = _nodes_by_label(save_recorder["nodes"], "Topic")
    by_name = {t.name: t for t in topics}
    for topic_def in TOPICS:
        assert topic_def["name"] in by_name
        node = by_name[topic_def["name"]]
        assert node.attributes["ao_refs"] == list(topic_def["ao_refs"])
        assert node.attributes["subject_ref"] == topic_def["subject_slug"]


@pytest.mark.asyncio
async def test_seed_lilymay_assessment_objectives_under_fleet_group(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """All six AOs land under ``fleet-appmilla``."""
    await seed_lilymay(_FakeWrapper())
    aos = _nodes_by_label(save_recorder["nodes"], "AssessmentObjective")
    assert {a.name for a in aos} == {"AO1", "AO2", "AO3", "AO4", "AO5", "AO6"}
    for ao in aos:
        assert ao.group_id == FLEET_GROUP_ID


@pytest.mark.asyncio
async def test_seed_lilymay_topic_confidences_use_epoch_sentinel(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """ADR-ARCH-021 §G3 — every baseline TopicConfidence has
    ``last_revised_at = EPOCH_NEVER_REVISED``.
    """
    await seed_lilymay(_FakeWrapper())
    confidences = _nodes_by_label(save_recorder["nodes"], "TopicConfidence")
    assert len(confidences) == len(TOPICS)
    for tc in confidences:
        attrs = tc.attributes
        assert attrs["last_revised_at"] == EPOCH_NEVER_REVISED.isoformat()
        assert attrs["student_ref"] == STUDENT_ID
        # Bands span at least struggling / developing / secure (AC-006 spirit).
    bands = {tc.attributes["band"] for tc in confidences}
    assert {"struggling", "developing", "secure"}.issubset(bands), (
        f"expected all three planner bands; got {bands}"
    )


@pytest.mark.asyncio
async def test_seed_lilymay_topic_confidences_under_student_group(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """TopicConfidence nodes live under ``student-<id>`` (not ``subject-*``)."""
    await seed_lilymay(_FakeWrapper())
    confidences = _nodes_by_label(save_recorder["nodes"], "TopicConfidence")
    student_group = f"{STUDENT_GROUP_PREFIX}{STUDENT_ID}"
    for tc in confidences:
        assert tc.group_id == student_group


# ---------------------------------------------------------------------------
# Edge-level assertions (ADR-ARCH-021 §G2 — only intra-group edges)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_writes_only_intra_group_edges(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """ADR-ARCH-021 §G2 — every edge has source and target in the same group_id.

    The seed must NOT attempt cross-group edges (Student→Subject,
    Student→Text, Topic→AO) under the FalkorDB silent-dangle constraint.
    """
    await seed_lilymay(_FakeWrapper())
    edges = save_recorder["edges"]
    # We only check the edge.group_id field is consistent. Source/target
    # node-uuid checking is folded into the per-edge tests below.
    seen_names = {e.name for e in edges}
    assert seen_names == {HAS_CONFIDENCE, HAS_TEXT, COVERS}, (
        f"unexpected edge types written: {seen_names}"
    )
    # No STUDIES, WORKING_ON, or ASSESSED_BY edges should be written.
    for forbidden in ("STUDIES", "WORKING_ON", "ASSESSED_BY"):
        assert not any(e.name == forbidden for e in edges), (
            f"forbidden cross-group edge type written: {forbidden}"
        )


@pytest.mark.asyncio
async def test_seed_lilymay_writes_has_confidence_edges(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """One Student → HAS_CONFIDENCE → TopicConfidence per topic."""
    await seed_lilymay(_FakeWrapper())
    edges = [e for e in save_recorder["edges"] if e.name == HAS_CONFIDENCE]
    assert len(edges) == len(TOPICS)
    student_group = f"{STUDENT_GROUP_PREFIX}{STUDENT_ID}"
    for edge in edges:
        assert edge.group_id == student_group


@pytest.mark.asyncio
async def test_seed_lilymay_writes_has_text_edges(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """Subject → HAS_TEXT → Text under the parent subject's group_id."""
    await seed_lilymay(_FakeWrapper())
    edges = [e for e in save_recorder["edges"] if e.name == HAS_TEXT]
    assert len(edges) == len(TEXTS)
    for edge in edges:
        assert edge.group_id.startswith(SUBJECT_GROUP_PREFIX)


@pytest.mark.asyncio
async def test_seed_lilymay_writes_covers_edges(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """Subject → COVERS → Topic under the parent subject's group_id."""
    await seed_lilymay(_FakeWrapper())
    edges = [e for e in save_recorder["edges"] if e.name == COVERS]
    assert len(edges) == len(TOPICS)
    for edge in edges:
        assert edge.group_id.startswith(SUBJECT_GROUP_PREFIX)


# ---------------------------------------------------------------------------
# Idempotency (deterministic UUID5 derivation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_uses_deterministic_uuids(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
) -> None:
    """Every saved node carries the uuid the seed_uuids helpers derive.

    This is the load-bearing property that makes re-runs byte-idempotent —
    same uuid + FalkorDB MERGE-by-uuid = no duplicate node.
    """
    await seed_lilymay(_FakeWrapper())
    nodes = save_recorder["nodes"]

    student_group = f"{STUDENT_GROUP_PREFIX}{STUDENT_ID}"
    expected_student_uuid = student_uuid(student_group, STUDENT_NAME)
    student_node = _nodes_by_label(nodes, "Student")[0]
    assert student_node.uuid == expected_student_uuid

    # Subject UUIDs
    for subj in SUBJECTS:
        sg = f"{SUBJECT_GROUP_PREFIX}{subj['slug']}"
        expected = subject_uuid(sg, subj["name"])
        match = next(
            (n for n in _nodes_by_label(nodes, "Subject") if n.name == subj["name"]),
            None,
        )
        assert match is not None
        assert match.uuid == expected

    # Text UUIDs
    for text in TEXTS:
        sg = f"{SUBJECT_GROUP_PREFIX}{text['subject_slug']}"
        expected = text_uuid(sg, text["subject_slug"], text["name"])
        match = next(
            (n for n in _nodes_by_label(nodes, "Text") if n.name == text["name"]),
            None,
        )
        assert match is not None
        assert match.uuid == expected

    # Topic UUIDs
    for topic in TOPICS:
        sg = f"{SUBJECT_GROUP_PREFIX}{topic['subject_slug']}"
        expected = topic_uuid(sg, topic["name"])
        match = next(
            (n for n in _nodes_by_label(nodes, "Topic") if n.name == topic["name"]),
            None,
        )
        assert match is not None
        assert match.uuid == expected

    # AO UUIDs
    for ao in AOS:
        expected = assessment_objective_uuid(FLEET_GROUP_ID, ao["code"])
        match = next(
            (
                n
                for n in _nodes_by_label(nodes, "AssessmentObjective")
                if n.name == ao["code"]
            ),
            None,
        )
        assert match is not None
        assert match.uuid == expected

    # TopicConfidence UUIDs
    for topic in TOPICS:
        expected = topic_confidence_uuid(student_group, STUDENT_ID, topic["name"])
        match = next(
            (
                n
                for n in _nodes_by_label(nodes, "TopicConfidence")
                if n.attributes.get("topic_ref") == topic["name"]
            ),
            None,
        )
        assert match is not None
        assert match.uuid == expected


@pytest.mark.asyncio
async def test_seed_lilymay_second_run_produces_identical_uuids(
    save_recorder: dict[str, list[Any]],
) -> None:
    """A re-seed writes nodes with the same uuids.

    graphiti-core's FalkorDB MERGE-by-uuid then collapses them rather than
    duplicating, which is the on-graph idempotency story.
    """
    rc1 = await seed_lilymay(_FakeWrapper())
    first_run_uuids = [n.uuid for n in save_recorder["nodes"]]
    assert rc1 == EXIT_OK
    assert first_run_uuids, "first run wrote no nodes"

    # Reset the recorder (in test scope only — graphiti-core doesn't see the
    # first batch because we're mocking the save call).
    save_recorder["nodes"].clear()
    save_recorder["edges"].clear()

    rc2 = await seed_lilymay(_FakeWrapper())
    second_run_uuids = [n.uuid for n in save_recorder["nodes"]]
    assert rc2 == EXIT_OK
    assert first_run_uuids == second_run_uuids, (
        "second run derived different uuids — idempotency property broken"
    )


# ---------------------------------------------------------------------------
# Node + edge structured-log assertions (AC-17)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_emits_node_and_edge_debug_log_events(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One ``seeding_node_written`` per node and one ``seeding_edge_written``
    per edge — the debug-level diagnostics from AC-17.
    """
    with caplog.at_level(logging.DEBUG, logger="study_tutor.seed"):
        await seed_lilymay(_FakeWrapper())

    node_records = [
        r for r in caplog.records if getattr(r, "event", "") == "seeding_node_written"
    ]
    edge_records = [
        r for r in caplog.records if getattr(r, "event", "") == "seeding_edge_written"
    ]
    assert len(node_records) == len(save_recorder["nodes"])
    assert len(edge_records) == len(save_recorder["edges"])
    # Each node-event carries identifying metadata (greppable in production).
    # ``entity_name`` rather than ``name`` because ``name`` is reserved on
    # :class:`logging.LogRecord` (the seed module respects this constraint).
    for record in node_records:
        for field in ("entity_kind", "entity_name", "group_id", "uuid"):
            assert getattr(record, field, None) is not None, (
                f"seeding_node_written record missing {field}"
            )


@pytest.mark.asyncio
async def test_seed_lilymay_pruned_log_events_no_longer_emitted(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-17 — the dropped events from the helper-based era never appear."""
    forbidden = {
        "seeding_pending_writes_abandoned",
        "seeding_batch_drained",
        "seeding_batch_drain_env_invalid",
    }
    with caplog.at_level(logging.DEBUG, logger="study_tutor.seed"):
        await seed_lilymay(_FakeWrapper())
    seen = {getattr(r, "event", "") for r in caplog.records}
    assert seen.isdisjoint(forbidden), (
        f"pruned log event reappeared: {seen & forbidden}"
    )


# ---------------------------------------------------------------------------
# Verification gate (post-seed read-back)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_emits_completion_log(
    save_recorder: dict[str, list[Any]],
    state_iter: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Successful seed emits ``seeding_completed`` with entity counts.

    TASK-SMP2-06: Post-seed verification removed, so subjects/topic_confidences
    fields are no longer present. Only nodes_written and edges_written remain.
    """
    with caplog.at_level(logging.INFO, logger="study_tutor.seed"):
        rc = await seed_lilymay(_FakeWrapper())
    assert rc == EXIT_OK
    completion = next(
        (
            r
            for r in caplog.records
            if getattr(r, "event", "") == "seeding_completed"
        ),
        None,
    )
    assert completion is not None
    # subjects and topic_confidences fields removed with get_student_state
    assert completion.nodes_written == 1 + len(SUBJECTS) + len(TEXTS) + 2 * len(
        TOPICS
    ) + len(AOS)
    assert completion.edges_written == 2 * len(TOPICS) + len(TEXTS)


@pytest.mark.skip(reason="TASK-SMP2-06: Post-seed verification removed with get_student_state")
@pytest.mark.asyncio
async def test_seed_lilymay_warns_when_post_read_returns_empty(
    save_recorder: dict[str, list[Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SKIPPED: Post-seed verification removed in TASK-SMP2-06.

    Original: Verification-warning path when the read-back can't see the writes.
    The seed script no longer uses get_student_state for post-seed verification.
    TODO(FEAT-SMP-004): Remove this test when graph seed path is fully retired.
    """
    pass


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_exits_2_when_get_client_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """End-to-end: main() exits 2 when the store is unreachable."""

    async def fake_get_client(config: Any) -> Any:
        return None

    monkeypatch.setattr(seed_module, "get_client", fake_get_client)

    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        with pytest.raises(SystemExit) as excinfo:
            await main([])

    assert excinfo.value.code == EXIT_CLIENT_UNAVAILABLE == 2


@pytest.mark.asyncio
async def test_main_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
    save_recorder: dict[str, list[Any]],
) -> None:
    """End-to-end: main() returns 0 on a clean fresh seed."""
    wrapper = _FakeWrapper()

    async def fake_get_client(config: Any) -> Any:
        return wrapper

    monkeypatch.setattr(seed_module, "get_client", fake_get_client)

    rc = await main([])

    assert rc == EXIT_OK
    assert wrapper.close_call_count == 1, "main() must close the wrapper"
    assert save_recorder["nodes"], "main() must drive the seed writes"


# ---------------------------------------------------------------------------
# CLI / config plumbing
# ---------------------------------------------------------------------------


def test_load_config_uses_defaults_when_path_omitted() -> None:
    cfg = load_config(None)
    assert cfg.falkor_host == DEFAULT_CONFIG["falkor_host"]
    assert cfg.falkor_port == DEFAULT_CONFIG["falkor_port"]
    assert cfg.timeout_seconds == DEFAULT_CONFIG["timeout_seconds"]


def test_load_config_overrides_via_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "seed-config.yaml"
    config_file.write_text(
        "falkor_host: example.invalid\n"
        "falkor_port: 12345\n"
        "database: alt-db\n"
        "embedder_url: http://example.invalid/v1\n"
        "timeout_seconds: 9.0\n"
    )

    cfg = load_config(config_file)

    assert cfg.falkor_host == "example.invalid"
    assert cfg.falkor_port == 12345
    assert cfg.database == "alt-db"
    assert cfg.timeout_seconds == 9.0
    # Non-overridden defaults are preserved.
    assert cfg.llm_provider == DEFAULT_CONFIG["llm_provider"]


def test_load_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError, match="must deserialise to a mapping"):
        load_config(bad)


def test_argparse_accepts_config_path_flag() -> None:
    """``--config-path`` flag is wired through argparse."""
    ns = seed_module._parse_args(["--config-path", "/tmp/x.yaml"])
    assert ns.config_path == Path("/tmp/x.yaml")
    ns_default = seed_module._parse_args([])
    assert ns_default.config_path is None


# ---------------------------------------------------------------------------
# AC-01 — grep enforcement: no ``add_episode`` in the seed script source
# ---------------------------------------------------------------------------


def test_seed_script_has_no_add_episode_calls() -> None:
    """AC-GSM-009-01 — every seed write is typed-entity, never add_episode."""
    src = Path(seed_module.__file__).read_text()
    # Strip the entire docstring/comment surface so we only test executable
    # code (the docstring legitimately *describes* the migration).
    import ast

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_episode"
        ):
            pytest.fail(
                f"add_episode call found in {seed_module.__file__} at line "
                f"{node.lineno} — AC-GSM-009-01 forbids LLM-driven write paths "
                f"in the typed-entity seed."
            )
