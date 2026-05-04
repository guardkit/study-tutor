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
    StudentState,
    TopicRecommendation,
    get_student_state,
    get_topic_recommendations,
    record_session_completion,
)
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
