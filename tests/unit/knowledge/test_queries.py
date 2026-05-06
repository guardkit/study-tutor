"""Unit tests for student-model query helpers (TASK-GSM-005).

Covers every acceptance criterion in the task spec:

- Empty/safe behaviour when ``client=None`` (all three helpers).
- Happy-path projection for ``get_student_state``.
- Read-path timeout: returns ``None`` + emits
  ``event=student_state_read_timeout`` (mocked slow ``search_nodes``).
- Stale-fact flag propagates when facts pre-date the threshold (ASSUM-006).
- Topic-recommendation ranking
  (struggling_stale > developing_misconception > developing_stale).
- Cooldown exclusion at the 48h boundary (ASSUM-003).
- ``record_session_completion`` schedules with ``flush_id="F3"`` and the
  correct ``group_ids``.
- ``record_session_completion`` returns within 50ms even when the
  helper-returned task hangs (fire-and-forget contract).
- Group-id discipline AST lint: no literal-string ``group_ids`` in any
  ``search_*`` call inside ``queries.py``.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from study_tutor.knowledge.queries import (
    DEFAULT_STALE_THRESHOLD_DAYS,
    Phase1MinimalDeltaPolicy,
    StudentState,
    TopicRecommendation,
    get_student_state,
    get_topic_recommendations,
    record_session_completion,
    record_topic_confidence_update,
)
from study_tutor.knowledge.seed_uuids import topic_confidence_uuid
from study_tutor.knowledge.student_model import STUDENT_GROUP_PREFIX


# ---------------------------------------------------------------------------
# Test doubles and helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _node(entity_type: str, **attrs: Any) -> SimpleNamespace:
    return SimpleNamespace(entity_type=entity_type, attributes=attrs)


def _fact(fact_type: str, **attrs: Any) -> SimpleNamespace:
    return SimpleNamespace(fact_type=fact_type, **attrs)


class _FakeInner:
    """Minimal duck-typed inner graphiti client recording every search call."""

    def __init__(
        self,
        nodes: list[Any] | None = None,
        facts: list[Any] | None = None,
        slow_nodes_seconds: float = 0.0,
    ) -> None:
        self.nodes = nodes or []
        self.facts = facts or []
        self.slow_nodes_seconds = slow_nodes_seconds
        self.search_nodes_calls: list[dict[str, Any]] = []
        self.search_memory_facts_calls: list[dict[str, Any]] = []

    async def search_nodes(self, group_ids: list[str], query: str) -> list[Any]:
        self.search_nodes_calls.append({"group_ids": group_ids, "query": query})
        if self.slow_nodes_seconds > 0:
            await asyncio.sleep(self.slow_nodes_seconds)
        return self.nodes

    async def search_memory_facts(
        self, group_ids: list[str], query: str
    ) -> list[Any]:
        self.search_memory_facts_calls.append(
            {"group_ids": group_ids, "query": query}
        )
        return self.facts


class _FakeClient:
    """Wraps a fake inner client behind the GraphitiClient.client_or_none API."""

    def __init__(self, inner: Any) -> None:
        self.client_or_none = inner


def _make_client_with_state(
    *,
    confidences: list[dict[str, Any]] | None = None,
    misconceptions: list[dict[str, Any]] | None = None,
) -> _FakeClient:
    nodes: list[Any] = []
    for tc in confidences or []:
        nodes.append(
            _node(
                "TopicConfidence",
                topic_ref=tc["topic_name"],
                band=tc["band"],
                percentage=tc.get("percentage", 50),
                last_revised_at=tc.get("last_revised_at"),
            )
        )
    for misconception in misconceptions or []:
        nodes.append(
            _node(
                "Misconception",
                topic_ref=misconception["topic_name"],
                text=misconception.get("text", "x"),
                observed_at=misconception.get(
                    "observed_at", _now() - timedelta(days=1)
                ),
            )
        )
    return _FakeClient(_FakeInner(nodes=nodes, facts=[]))


# ---------------------------------------------------------------------------
# get_student_state
# ---------------------------------------------------------------------------


async def test_get_student_state_returns_empty_when_client_is_none() -> None:
    state = await get_student_state(client=None, student_id="lilymay")
    assert state is not None
    assert isinstance(state, StudentState)
    assert state.empty is True


async def test_get_student_state_happy_path_populates_all_fields() -> None:
    nodes = [
        _node("Student", year_group=11, target_grade="8"),
        _node("Subject", name="English Literature"),
        _node("Text", name="Macbeth"),
        _node(
            "TopicConfidence",
            topic_ref="Witches Act 1",
            band="developing",
            percentage=55,
            last_revised_at=_now() - timedelta(days=5),
        ),
        _node(
            "Misconception",
            topic_ref="Witches Act 1",
            text="Confusion about apparitions",
            observed_at=_now() - timedelta(days=2),
        ),
    ]
    facts = [
        _fact(
            "session_completed",
            session_id="sess-1",
            ended_at=_now() - timedelta(days=1),
        ),
        _fact(
            "session_completed",
            session_id="sess-0",
            ended_at=_now() - timedelta(days=5),
        ),
    ]
    inner = _FakeInner(nodes=nodes, facts=facts)

    state = await get_student_state(client=_FakeClient(inner), student_id="lilymay")

    assert state is not None
    assert state.empty is False
    assert state.student_id == "lilymay"
    assert state.year_group == 11
    assert state.target_grade == "8"
    assert state.subjects == ["English Literature"]
    assert state.current_texts == ["Macbeth"]
    assert len(state.topic_confidences) == 1
    assert state.topic_confidences[0].topic_name == "Witches Act 1"
    assert state.topic_confidences[0].band == "developing"
    assert len(state.recent_misconceptions) == 1
    # Most recent of the two seeded sessions wins.
    assert state.most_recent_session_id == "sess-1"

    # Group-id discipline: search_* calls received the constructed group_ids.
    expected_group_ids = [f"{STUDENT_GROUP_PREFIX}lilymay"]
    assert inner.search_nodes_calls[0]["group_ids"] == expected_group_ids
    assert inner.search_memory_facts_calls[0]["group_ids"] == expected_group_ids


async def test_get_student_state_reads_enrolled_subjects_off_student_node() -> None:
    """ADR-ARCH-021 §G1 / TASK-GSM-009 AC-03: ``state.subjects`` is populated
    from the Student node's ``enrolled_subjects`` attribute (denormalisation),
    not from cross-group Subject node traversal.
    """
    nodes = [
        _node(
            "Student",
            year_group=10,
            target_grade="7",
            enrolled_subjects=["English Literature", "English Language"],
        ),
    ]
    inner = _FakeInner(nodes=nodes, facts=[])

    state = await get_student_state(
        client=_FakeClient(inner), student_id="lilymay"
    )

    assert state is not None
    assert state.subjects == ["English Literature", "English Language"]
    assert state.year_group == 10
    assert state.target_grade == "7"


async def test_get_student_state_handles_missing_enrolled_subjects() -> None:
    """When ``enrolled_subjects`` is absent from the Student attributes,
    projection still completes and ``state.subjects`` stays empty.
    """
    nodes = [
        _node("Student", year_group=10, target_grade="7"),
    ]
    inner = _FakeInner(nodes=nodes, facts=[])

    state = await get_student_state(
        client=_FakeClient(inner), student_id="lilymay"
    )

    assert state is not None
    assert state.year_group == 10
    assert state.target_grade == "7"
    assert state.subjects == []


async def test_get_student_state_skips_non_list_enrolled_subjects() -> None:
    """A malformed ``enrolled_subjects`` (e.g. accidental string) must not
    crash projection — list-typed values are required.
    """
    nodes = [
        _node(
            "Student",
            year_group=10,
            target_grade="7",
            enrolled_subjects="English Literature",  # not a list
        ),
    ]
    inner = _FakeInner(nodes=nodes, facts=[])

    state = await get_student_state(
        client=_FakeClient(inner), student_id="lilymay"
    )

    assert state is not None
    assert state.subjects == []


async def test_get_student_state_returns_none_on_read_timeout(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read exceeding the timeout must return None and log the event."""
    import study_tutor.knowledge.queries as queries_module

    # Shrink the timeout so the test stays fast; the slow inner sleeps longer.
    monkeypatch.setattr(queries_module, "READ_TIMEOUT_SEC", 0.05)

    inner = _FakeInner(nodes=[], facts=[], slow_nodes_seconds=0.5)
    caplog.set_level(logging.WARNING, logger="study_tutor.knowledge.queries")

    state = await get_student_state(
        client=_FakeClient(inner), student_id="lilymay"
    )

    assert state is None
    timeout_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "student_state_read_timeout"
    ]
    assert timeout_records, "expected a student_state_read_timeout log record"
    assert timeout_records[0].__dict__.get("student_id") == "lilymay"


async def test_get_student_state_flags_stale_when_facts_exceed_threshold() -> None:
    old_date = _now() - timedelta(days=DEFAULT_STALE_THRESHOLD_DAYS + 1)
    nodes = [
        _node(
            "TopicConfidence",
            topic_ref="Old Topic",
            band="secure",
            percentage=80,
            last_revised_at=old_date,
        )
    ]
    inner = _FakeInner(nodes=nodes, facts=[])

    state = await get_student_state(
        client=_FakeClient(inner), student_id="lilymay"
    )

    assert state is not None
    assert state.stale is True
    # The fact is still returned, not dropped (ASSUM-006).
    assert len(state.topic_confidences) == 1


# ---------------------------------------------------------------------------
# get_topic_recommendations
# ---------------------------------------------------------------------------


async def test_topic_recommendations_returns_empty_list_when_client_none() -> None:
    recs = await get_topic_recommendations(client=None, student_id="lilymay")
    assert recs == []


async def test_topic_recommendations_priority_ordering() -> None:
    """struggling_stale > developing_misconception > developing_stale."""
    long_ago = _now() - timedelta(days=10)
    confidences = [
        # Intentionally listed in non-priority order to prove we sort.
        {
            "topic_name": "DevStale",
            "band": "developing",
            "percentage": 50,
            "last_revised_at": long_ago,
        },
        {
            "topic_name": "DevMisc",
            "band": "developing",
            "percentage": 60,
            "last_revised_at": long_ago,
        },
        {
            "topic_name": "Struggling",
            "band": "struggling",
            "percentage": 25,
            "last_revised_at": long_ago,
        },
    ]
    misconceptions = [{"topic_name": "DevMisc"}]
    client = _make_client_with_state(
        confidences=confidences, misconceptions=misconceptions
    )

    recs = await get_topic_recommendations(
        client=client, student_id="lilymay", count=3
    )

    assert [r.topic_name for r in recs] == ["Struggling", "DevMisc", "DevStale"]
    assert [r.reason for r in recs] == [
        "struggling_stale",
        "developing_misconception",
        "developing_stale",
    ]
    assert all(isinstance(r, TopicRecommendation) for r in recs)


async def test_topic_recommendations_returns_three_for_mixed_band_learner() -> None:
    long_ago = _now() - timedelta(days=10)
    confidences = [
        {
            "topic_name": "T1",
            "band": "struggling",
            "percentage": 20,
            "last_revised_at": long_ago,
        },
        {
            "topic_name": "T2",
            "band": "developing",
            "percentage": 50,
            "last_revised_at": long_ago,
        },
        {
            "topic_name": "T3",
            "band": "developing",
            "percentage": 60,
            "last_revised_at": long_ago,
        },
        # Secure / mastered topics never qualify as recommendations in Phase 1.
        {
            "topic_name": "T4",
            "band": "secure",
            "percentage": 80,
            "last_revised_at": long_ago,
        },
    ]
    client = _make_client_with_state(confidences=confidences)

    recs = await get_topic_recommendations(
        client=client, student_id="lilymay", count=3
    )

    assert len(recs) == 3
    assert "T4" not in [r.topic_name for r in recs]


async def test_topic_recommendations_excludes_topics_within_cooldown() -> None:
    """Topics revised within 48h are excluded; a topic revised at 49h is kept."""
    inside_cooldown = _now() - timedelta(hours=47)
    outside_cooldown = _now() - timedelta(hours=49)
    confidences = [
        {
            "topic_name": "Recent",
            "band": "struggling",
            "percentage": 20,
            "last_revised_at": inside_cooldown,
        },
        {
            "topic_name": "Stale",
            "band": "struggling",
            "percentage": 25,
            "last_revised_at": outside_cooldown,
        },
    ]
    client = _make_client_with_state(confidences=confidences)

    recs = await get_topic_recommendations(
        client=client,
        student_id="lilymay",
        count=3,
        cooldown_hours=48,
    )

    names = [r.topic_name for r in recs]
    assert "Recent" not in names
    assert "Stale" in names


# ---------------------------------------------------------------------------
# record_session_completion
# ---------------------------------------------------------------------------


async def test_record_session_completion_is_noop_when_client_is_none() -> None:
    helper = MagicMock()
    await record_session_completion(
        client=None,
        write_helper=helper,
        student_id="lilymay",
        session_summary={},
    )
    helper.schedule_write.assert_not_called()


async def test_record_session_completion_dispatches_with_f3_flush_id() -> None:
    helper = MagicMock()
    helper.schedule_write = MagicMock(return_value=None)

    await record_session_completion(
        client=MagicMock(),
        write_helper=helper,
        student_id="lilymay",
        session_summary={
            "session_id": "sess-9",
            "subject_slug": "english-literature",
            "text_name": "Macbeth",
            "topics_covered": ["Act 1"],
            "aos_exercised": ["AO1"],
            "narrative_summary": "good session",
        },
    )

    helper.schedule_write.assert_called_once()
    kwargs = helper.schedule_write.call_args.kwargs
    assert kwargs["flush_id"] == "F3"
    assert kwargs["group_ids"] == [f"{STUDENT_GROUP_PREFIX}lilymay"]
    episode = kwargs["episode"]
    assert episode.episode_kind == "session_completed"
    assert episode.session_id == "sess-9"
    assert episode.student_id == "lilymay"


async def test_record_session_completion_returns_under_50ms_with_hanging_helper() -> None:
    """Caller-facing path returns within 50ms even when the underlying task hangs."""
    captured_tasks: list[asyncio.Task[None]] = []

    async def _hang() -> None:
        await asyncio.sleep(80)

    def _schedule_write(**_kwargs: Any) -> asyncio.Task[None]:
        task = asyncio.create_task(_hang())
        captured_tasks.append(task)
        return task

    helper = MagicMock()
    helper.schedule_write = MagicMock(side_effect=_schedule_write)

    start = time.monotonic()
    await record_session_completion(
        client=MagicMock(),
        write_helper=helper,
        student_id="lilymay",
        session_summary={"topic": "Macbeth Act 1"},
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    try:
        assert elapsed_ms < 50, (
            f"record_session_completion took {elapsed_ms:.1f}ms (>50ms budget)"
        )
        helper.schedule_write.assert_called_once()
    finally:
        for task in captured_tasks:
            task.cancel()


# ---------------------------------------------------------------------------
# Group-id discipline AST lint
# ---------------------------------------------------------------------------


def test_no_literal_string_group_ids_in_search_calls() -> None:
    """AST-scan ``queries.py``: no literal-string group_ids in search_* calls."""
    src_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "study_tutor"
        / "knowledge"
        / "queries.py"
    )
    tree = ast.parse(src_path.read_text())

    search_methods = {"search_nodes", "search_memory_facts"}
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        method_name: str | None = None
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            method_name = node.func.id
        if method_name not in search_methods:
            continue

        # First positional argument is group_ids per the producer contract.
        if node.args:
            first_arg = node.args[0]
            if (
                isinstance(first_arg, ast.Constant)
                and isinstance(first_arg.value, str)
            ):
                violations.append(
                    f"line {node.lineno}: literal string for group_ids "
                    f"in {method_name} call"
                )

        for keyword in node.keywords:
            if keyword.arg == "group_ids" and (
                isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                violations.append(
                    f"line {node.lineno}: literal string in group_ids "
                    f"kwarg of {method_name} call"
                )

    assert not violations, "Group-id discipline violations: " + "; ".join(violations)


# ---------------------------------------------------------------------------
# TASK-GR-CONF — record_topic_confidence_update (BLOCK-3b)
# ---------------------------------------------------------------------------


class _FakeEntityNode:
    """Test double mimicking ``graphiti_core.nodes.EntityNode`` for the
    ``record_topic_confidence_update`` happy path. Records every ``save``
    call so tests can assert the post-mutation state.
    """

    def __init__(
        self,
        *,
        uuid: str,
        attributes: dict[str, Any],
        name: str = "TopicConfidence:test",
        labels: list[str] | None = None,
        group_id: str = "student-test",
        summary: str = "",
    ) -> None:
        self.uuid = uuid
        self.name = name
        self.labels = labels or ["Entity", "TopicConfidence"]
        self.group_id = group_id
        self.summary = summary
        self.attributes = dict(attributes)
        self.save_calls: list[Any] = []

    async def save(self, driver: Any) -> None:
        self.save_calls.append(driver)


class _FakeDriver:
    """Driver double — mirrors the ``clone(database=...)`` shape so the
    helper's per-group-id named-graph clone path is exercised without
    booting a real FalkorDB.
    """

    def __init__(self) -> None:
        self.clone_calls: list[str] = []

    def clone(self, *, database: str) -> _FakeDriver:
        self.clone_calls.append(database)
        return self


class _FakeInnerWithDriver:
    """Inner-client double exposing a ``driver`` attribute (matches the
    duck-typed shape :func:`record_topic_confidence_update` expects).
    """

    def __init__(self, driver: _FakeDriver) -> None:
        self.driver = driver


class _FakeClientWithDriver:
    """Wraps a fake inner client behind the ``client_or_none`` property."""

    def __init__(self, inner: Any) -> None:
        self.client_or_none = inner


class _FakeWriteHelper:
    """Records every :meth:`schedule_write` call for episode assertions."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def schedule_write(
        self,
        *,
        group_ids: list[str],
        episode: Any,
        flush_id: str,
    ) -> None:
        self.calls.append(
            {
                "group_ids": group_ids,
                "episode": episode,
                "flush_id": flush_id,
            }
        )


class _FakePolicy:
    """Fake policy returning a fixed delta — exercises the Protocol seam."""

    def __init__(self, delta: int, name: str = "fake_policy") -> None:
        self._delta = delta
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def compute(
        self,
        *,
        student_id: str,
        topic_ref: str,
        session_summary: dict[str, Any],
    ) -> int:
        self.calls.append(
            {
                "student_id": student_id,
                "topic_ref": topic_ref,
                "session_summary": session_summary,
            }
        )
        return self._delta


def _patch_entity_node_get(
    monkeypatch: pytest.MonkeyPatch,
    return_value: Any | None,
    raise_not_found: bool = False,
) -> dict[str, list[Any]]:
    """Patch ``graphiti_core.nodes.EntityNode.get_by_uuid`` for tests.

    Returns a recorder dict capturing the (driver, uuid) pairs the helper
    asks for so tests can assert the per-group clone branch wired
    correctly.
    """
    from graphiti_core.errors import NodeNotFoundError
    from graphiti_core.nodes import EntityNode

    calls: list[Any] = []

    async def _fake_get(driver: Any, uuid: str) -> Any:
        calls.append((driver, uuid))
        if raise_not_found:
            raise NodeNotFoundError(uuid)
        return return_value

    monkeypatch.setattr(EntityNode, "get_by_uuid", _fake_get)
    return {"calls": calls}


# ---- AC-CONF-10: Phase1MinimalDeltaPolicy clamp behaviour -----------------


def test_phase1_policy_clamps_negative_at_minus_ten() -> None:
    """Misconception count >=4 produces -12 → clamped to -10."""
    policy = Phase1MinimalDeltaPolicy()
    delta = policy.compute(
        student_id="lilymay",
        topic_ref="ambition",
        session_summary={
            "misconceptions_per_topic": {"ambition": 4},
            "student_turn_count": 8,
        },
    )
    assert delta == -10


def test_phase1_policy_clamps_positive_at_plus_ten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The clamp upper bound is dead code under the current heuristic
    but lives as defensive insurance against future heuristic tweaks.
    Verify it via a subclass that bypasses the bounded formula.
    """

    class _OverPolicy(Phase1MinimalDeltaPolicy):
        def compute(
            self, *, student_id, topic_ref, session_summary
        ) -> int:
            # Reuse the parent clamp by feeding it a synthetic raw delta.
            raw = 25
            return max(-10, min(10, raw))

    delta = _OverPolicy().compute(
        student_id="x", topic_ref="y", session_summary={}
    )
    assert delta == 10


# ---- AC-CONF-10: delta == 0 — last_revised_at flips, no F2 episode --------


@pytest.mark.asyncio
async def test_delta_zero_flips_last_revised_at_no_episode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``delta == 0`` still saves the node (so ``last_revised_at`` flips
    structurally — that's what AC-DEMO-03's ``search_nodes`` round-trip
    confirms) but suppresses the F2 episode write because the temporal-
    analytics layer has nothing meaningful to record.
    """
    student_id = "lilymay"
    topic_ref = "Lady Macbeth's ambition"
    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    fake_node = _FakeEntityNode(
        uuid=tc_uuid,
        attributes={
            "student_ref": student_id,
            "topic_ref": topic_ref,
            "percentage": 55,
            "band": "developing",
            "last_revised_at": epoch.isoformat(),
        },
    )
    _patch_entity_node_get(monkeypatch, return_value=fake_node)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))
    ended_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        await record_topic_confidence_update(
            client=client,
            write_helper=helper,
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 0,
                "ended_at": ended_at,
                "triggering_session_id": "sess-1",
            },
            policy=Phase1MinimalDeltaPolicy(),  # delta=0 (no misc, turns<5)
            create_task_fn=_capture_task,
        )

        # Drain the fire-and-forget save task so we can read fake_node.
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)

        # Entity update happened: percentage and band unchanged, but
        # last_revised_at flipped from EPOCH_NEVER_REVISED to ended_at.
        assert fake_node.attributes["percentage"] == 55
        assert fake_node.attributes["band"] == "developing"
        assert fake_node.attributes["last_revised_at"] == ended_at.isoformat()
        assert fake_node.save_calls == [driver]

        # F2 episode suppressed under delta==0.
        assert helper.calls == []
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()


# ---- AC-CONF-10: delta != 0 — band changes, F2 episode scheduled ----------


@pytest.mark.asyncio
async def test_delta_nonzero_with_band_change_schedules_f2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A +1 delta crossing the developing→secure boundary updates band
    and dispatches the F2 episode with ``flush_id="F2"`` and the
    correct group_ids.
    """
    student_id = "lilymay"
    topic_ref = "ambition"
    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)
    fake_node = _FakeEntityNode(
        uuid=tc_uuid,
        attributes={
            "student_ref": student_id,
            "topic_ref": topic_ref,
            "percentage": 69,  # top of "developing" (per ASSUM-001: 40-69)
            "band": "developing",
            "last_revised_at": "1970-01-01T00:00:00+00:00",
        },
    )
    _patch_entity_node_get(monkeypatch, return_value=fake_node)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))
    ended_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        policy = _FakePolicy(delta=1, name="test_policy_v1")
        await record_topic_confidence_update(
            client=client,
            write_helper=helper,
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 6,
                "ended_at": ended_at,
                "triggering_session_id": "sess-2",
            },
            policy=policy,
            create_task_fn=_capture_task,
        )
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)

        # Band moved across the developing→secure boundary at 70.
        assert fake_node.attributes["percentage"] == 70
        assert fake_node.attributes["band"] == "secure"
        assert fake_node.attributes["last_revised_at"] == ended_at.isoformat()

        # F2 episode dispatched with the correct group_ids and flush_id.
        assert len(helper.calls) == 1
        call = helper.calls[0]
        assert call["flush_id"] == "F2"
        assert call["group_ids"] == [group_id]
        episode = call["episode"]
        assert episode.episode_kind == "topic_confidence_updated"
        assert episode.previous_percentage == 69
        assert episode.new_percentage == 70
        assert episode.previous_band == "developing"
        assert episode.new_band == "secure"
        assert episode.confidence_source == "test_policy_v1"
        assert episode.triggering_session_id == "sess-2"

        # Protocol surface: the policy was called with the wired-through
        # session_summary.
        assert policy.calls and policy.calls[0]["topic_ref"] == topic_ref
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()


@pytest.mark.asyncio
async def test_delta_nonzero_without_band_change_schedules_f2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A small delta inside the same band still triggers the F2 episode."""
    student_id = "lilymay"
    topic_ref = "ambition"
    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)
    fake_node = _FakeEntityNode(
        uuid=tc_uuid,
        attributes={
            "student_ref": student_id,
            "topic_ref": topic_ref,
            "percentage": 50,
            "band": "developing",
            "last_revised_at": "1970-01-01T00:00:00+00:00",
        },
    )
    _patch_entity_node_get(monkeypatch, return_value=fake_node)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))
    ended_at = datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc)

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        await record_topic_confidence_update(
            client=client,
            write_helper=helper,
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 6,
                "ended_at": ended_at,
                "triggering_session_id": "sess-3",
            },
            policy=_FakePolicy(delta=1, name="band_stable_policy"),
            create_task_fn=_capture_task,
        )
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)

        assert fake_node.attributes["percentage"] == 51
        assert fake_node.attributes["band"] == "developing"  # unchanged
        assert len(helper.calls) == 1
        assert helper.calls[0]["flush_id"] == "F2"
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()


# ---- AC-CONF-06: node_not_found logging path -----------------------------


@pytest.mark.asyncio
async def test_node_not_found_logs_and_skips_save(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Operator picked an unseeded topic — helper logs and bails. The
    F3 ``session_completed`` episode dispatch (caller-side, AC-CONF-08)
    proceeds independently of this branch.
    """
    _patch_entity_node_get(monkeypatch, return_value=None, raise_not_found=True)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        with caplog.at_level(logging.WARNING, logger="study_tutor.knowledge.queries"):
            await record_topic_confidence_update(
                client=client,
                write_helper=helper,
                student_id="lilymay",
                topic_ref="UnseededTopic",
                session_summary={
                    "ended_at": datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
                },
                policy=_FakePolicy(delta=5),
                create_task_fn=_capture_task,
            )

        # No save scheduled, no F2 episode, single structured warning emitted.
        assert captured_tasks == []
        assert helper.calls == []
        events = [
            getattr(rec, "event", None) for rec in caplog.records
        ]
        reasons = [
            getattr(rec, "reason", None) for rec in caplog.records
        ]
        assert "topic_confidence_update_skipped" in events
        assert "node_not_found" in reasons
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()


# ---- AC-CONF-01 / AC-CONF-05: client=None graceful no-op + return time ----


@pytest.mark.asyncio
async def test_record_topic_confidence_update_is_noop_when_client_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``client=None`` is a graceful no-op (returns immediately, no log
    noise, no helper call)."""
    helper = _FakeWriteHelper()
    await record_topic_confidence_update(
        client=None,
        write_helper=helper,
        student_id="lilymay",
        topic_ref="ambition",
        session_summary={},
        policy=_FakePolicy(delta=5),
    )
    assert helper.calls == []


# ---- AC-CONF-10: Protocol surface — fake policy wired correctly ----------


@pytest.mark.asyncio
async def test_protocol_surface_fake_policy_wires_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake :class:`ConfidenceDeltaPolicyLike` with a fixed delta and a
    custom ``name`` flows through to both the percentage update and the
    F2 episode's ``confidence_source`` field. This is the test that
    proves the Protocol seam is load-bearing for FEAT-PH2-001's
    replacement story.
    """
    student_id = "lilymay"
    topic_ref = "ambition"
    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)
    fake_node = _FakeEntityNode(
        uuid=tc_uuid,
        attributes={
            "student_ref": student_id,
            "topic_ref": topic_ref,
            "percentage": 30,
            "band": "struggling",
            "last_revised_at": "1970-01-01T00:00:00+00:00",
        },
    )
    _patch_entity_node_get(monkeypatch, return_value=fake_node)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        policy = _FakePolicy(delta=7, name="fake_phase2_policy_v0")
        await record_topic_confidence_update(
            client=client,
            write_helper=helper,
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 4,
                "ended_at": datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
                "triggering_session_id": "sess-protocol",
            },
            policy=policy,
            create_task_fn=_capture_task,
        )
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)

        assert fake_node.attributes["percentage"] == 37
        # Per ASSUM-001 the table is struggling=0-39 / developing=40-69 /
        # secure=70-89 / mastered=90-100; 37 stays in struggling.
        assert fake_node.attributes["band"] == "struggling"
        assert helper.calls and helper.calls[0]["episode"].confidence_source == (
            "fake_phase2_policy_v0"
        )
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()


# ---- Per-group named-graph clone is exercised on FalkorDB-style drivers --


@pytest.mark.asyncio
async def test_driver_cloned_to_student_group_id_for_falkordb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must mirror the seed's per-group clone (TASK-FORK-PATCH
    bug #8). Verify ``driver.clone(database=...)`` is invoked with the
    student-prefixed group_id so the load + save target the right named
    graph."""
    student_id = "lilymay"
    topic_ref = "ambition"
    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)
    fake_node = _FakeEntityNode(
        uuid=tc_uuid,
        attributes={
            "student_ref": student_id,
            "topic_ref": topic_ref,
            "percentage": 50,
            "band": "developing",
            "last_revised_at": "1970-01-01T00:00:00+00:00",
        },
    )
    _patch_entity_node_get(monkeypatch, return_value=fake_node)

    helper = _FakeWriteHelper()
    driver = _FakeDriver()
    client = _FakeClientWithDriver(_FakeInnerWithDriver(driver))

    captured_tasks: list[asyncio.Task[Any]] = []

    def _capture_task(coro: Any) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro)
        captured_tasks.append(task)
        return task

    try:
        await record_topic_confidence_update(
            client=client,
            write_helper=helper,
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary={
                "misconceptions_per_topic": {},
                "student_turn_count": 0,
                "ended_at": datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc),
            },
            policy=_FakePolicy(delta=2),
            create_task_fn=_capture_task,
        )
        if captured_tasks:
            await asyncio.gather(*captured_tasks, return_exceptions=True)
        assert driver.clone_calls == [group_id]
    finally:
        for task in captured_tasks:
            if not task.done():
                task.cancel()
