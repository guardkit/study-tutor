"""Unit tests for TASK-DTL-005 — session-end orchestration, F3 dispatch,
``session.completed`` emit, lifecycle race resolution, and shutdown drain.

Each acceptance criterion in
``tasks/.../TASK-DTL-005-session-end-summary-f3-emit-lifecycle.md`` maps
to one or more tests here:

AC-001 ``tutor_session_end`` emits ``session.completed`` BEFORE the F3
       Graphiti write task is scheduled.
AC-002 Subscribers observe ``session.completed`` regardless of whether
       the F3 write succeeds.
AC-003 Zero-turn session does NOT emit ``session.completed`` and does
       NOT schedule the F3 write (I-T6 invariant).
AC-004 :class:`SessionCompletedEpisode` records topics, AOs, turn count,
       duration, narrative summary, and misconceptions surfaced.
AC-005 Narrative summary is 1 or 2 sentences (boundary scenario).
AC-006 Caller-facing ack returns within the 2 s session-end budget even
       when the helper is slow.
AC-007 F3 write failure → structured log; ``session.completed`` already
       emitted; caller observes session as ``ended``.
AC-008 In-flight misconception write coexists with new F3 write — both
       run independently to completion.
AC-009 In-flight tutor_turn at session-end resolves via the F4 lifecycle
       rule — complete-and-append within 3 s OR discard with no append.
AC-010 Shutdown hook awaits ``write_helper.drain(...)``; in-flight
       writes finish within the window or are logged.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.episodes import (
    MisconceptionObservedEpisode,
    SessionCompletedEpisode,
)
from study_tutor.session.tutor_session import TutorSession, TutorTurn
from study_tutor.tutoring.session_end import (
    GRAPHITI_DRAIN_WINDOW,
    SESSION_COMPLETED_EVENT,
    SESSION_END_BUDGET_SEC,
    SESSION_END_INFLIGHT_TIMEOUT_SEC,
    EventBus,
    MisconceptionAggregator,
    build_narrative_summary,
    build_session_completed_episode,
    perform_session_end,
    resolve_inflight_turn,
    runtime_shutdown,
)


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


def _make_session(
    *,
    session_id: str = "sess-1",
    subject: str = "literature",
    topic: str | None = "macbeth",
    turn_count: int = 1,
    started_at: datetime | None = None,
) -> TutorSession:
    started_at = started_at or datetime.now(timezone.utc) - timedelta(minutes=12)
    session = TutorSession(
        session_id=session_id,
        subject=subject,
        topic=topic,
        started_at=started_at,
    )
    for i in range(turn_count):
        session.turns.append(
            TutorTurn(
                role="user" if i % 2 == 0 else "tutor",
                content=f"turn {i}",
                timestamp=started_at + timedelta(minutes=i),
            )
        )
    return session


def _slow_async_client() -> AsyncMock:
    """Return a graphiti-core-shaped mock whose ``add_episode`` is slow.

    Used to verify the caller-facing ack returns within the session-end
    budget while the underlying write is still pending.
    """
    client = MagicMock()
    client.add_episode = AsyncMock()

    async def _slow(*_: Any, **__: Any) -> None:
        await asyncio.sleep(5.0)  # well past the 2s session-end budget

    client.add_episode.side_effect = _slow
    return client


# ---------------------------------------------------------------------------
# AC-005 — narrative summary is 1 or 2 sentences (boundary)
# ---------------------------------------------------------------------------


class TestNarrativeSummary:
    """Cover ASSUM-010: 1 or 2 sentences, both acceptable."""

    def test_one_sentence_when_no_misconceptions(self) -> None:
        summary = build_narrative_summary(
            turn_count=4,
            topics_covered=["Macbeth — Act 1"],
            misconceptions=[],
            duration_minutes=12,
        )
        # Exactly one sentence: ends with single trailing period and has no
        # second period mid-string before the final character.
        assert summary.count(".") == 1
        assert summary.endswith(".")
        assert "Macbeth — Act 1" in summary
        assert "4 turns" in summary

    def test_two_sentences_when_misconceptions_present(self) -> None:
        summary = build_narrative_summary(
            turn_count=2,
            topics_covered=["Macbeth"],
            misconceptions=["confused fate with ambition"],
            duration_minutes=8,
        )
        # Two sentences => exactly two periods (no abbreviations in inputs).
        assert summary.count(".") == 2
        assert "Misconceptions surfaced" in summary
        assert "confused fate with ambition" in summary

    def test_singular_turn_phrasing(self) -> None:
        summary = build_narrative_summary(
            turn_count=1,
            topics_covered=["Macbeth"],
            misconceptions=[],
            duration_minutes=1,
        )
        assert "1 turn " in summary  # singular "turn" not "turns"
        assert "1 minute" in summary  # singular "minute"

    def test_misconceptions_capped_to_three_with_overflow_marker(self) -> None:
        misconceptions = [f"miss-{i}" for i in range(5)]
        summary = build_narrative_summary(
            turn_count=10,
            topics_covered=["x"],
            misconceptions=misconceptions,
            duration_minutes=20,
        )
        # First three appear; the rest collapse into a "+N more" marker.
        assert "miss-0" in summary
        assert "miss-2" in summary
        assert "+2 more" in summary
        assert "miss-4" not in summary  # not in the surfaced list


# ---------------------------------------------------------------------------
# AC-004 — SessionCompletedEpisode records all required fields
# ---------------------------------------------------------------------------


class TestEpisodeBuilder:
    """The F3 episode payload must carry every field listed in AC-004."""

    def test_episode_records_topics_aos_turns_duration_summary_misconceptions(
        self,
    ) -> None:
        started_at = datetime(2026, 4, 30, 10, 0, 0, tzinfo=timezone.utc)
        ended_at = started_at + timedelta(minutes=15)
        session = _make_session(
            session_id="s-1",
            subject="literature",
            topic="macbeth",
            turn_count=3,
            started_at=started_at,
        )

        episode = build_session_completed_episode(
            session=session,
            student_id="lilymay",
            misconceptions=["mixed up Macbeth and Banquo"],
            topics_covered=["Macbeth — Act 1", "Macbeth — Act 2"],
            aos_exercised=["AO1", "AO3"],
            ended_at=ended_at,
        )

        assert isinstance(episode, SessionCompletedEpisode)
        assert episode.session_id == "s-1"
        assert episode.student_id == "lilymay"
        assert episode.subject_slug == "literature"
        assert episode.topics_covered == ["Macbeth — Act 1", "Macbeth — Act 2"]
        assert episode.aos_exercised == ["AO1", "AO3"]
        assert episode.started_at == started_at
        assert episode.ended_at == ended_at
        # Narrative summary references all required projection inputs.
        assert "3 turns" in episode.narrative_summary
        assert "15 minute" in episode.narrative_summary
        assert "mixed up Macbeth and Banquo" in episode.narrative_summary
        # Default text_name falls back to session.topic when set.
        assert episode.text_name == "macbeth"


# ---------------------------------------------------------------------------
# AC-001 — emit BEFORE create_task; AC-007 — F3 failure isolation
# ---------------------------------------------------------------------------


class TestEmitBeforeCreateTask:
    """The bus emit MUST precede the F3 ``create_task`` call (DDR-003)."""

    async def test_emit_happens_before_f3_create_task(self) -> None:
        bus = EventBus()
        events: list[str] = []

        # Subscriber records the emit ordering.
        async def _record(event_name: str, _payload: dict[str, Any]) -> None:
            events.append(f"emit:{event_name}")

        bus.subscribe(_record)

        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.schedule_write = MagicMock()

        # ``create_task_fn`` is the seam test's hook — capture order.
        def _capturing_create_task(coro: Any) -> Any:
            events.append("create_task")
            # Drain the coro so it runs (and triggers schedule_write).
            asyncio.get_event_loop()
            return asyncio.ensure_future(coro)

        session = _make_session(turn_count=2)

        result = await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            misconceptions=[],
            topics_covered=["Macbeth"],
            aos_exercised=["AO1"],
            create_task_fn=_capturing_create_task,
        )

        # Drain pending tasks so schedule_write actually runs.
        await asyncio.sleep(0)

        assert result == {"session_id": session.session_id, "status": "ended"}
        # AC-001: the emit ordering was recorded before the create_task hook.
        assert events.index(f"emit:{SESSION_COMPLETED_EVENT}") < events.index(
            "create_task"
        )
        # F3 went through schedule_write exactly once.
        helper.schedule_write.assert_called_once()
        kwargs = helper.schedule_write.call_args.kwargs
        assert kwargs["flush_id"] == "F3"
        assert kwargs["group_ids"] == ["student-lilymay"]
        assert isinstance(kwargs["episode"], SessionCompletedEpisode)

    async def test_session_completed_emitted_even_when_f3_write_fails(self) -> None:
        bus = EventBus()
        observed: list[dict[str, Any]] = []

        async def _record(event_name: str, payload: dict[str, Any]) -> None:
            if event_name == SESSION_COMPLETED_EVENT:
                observed.append(payload)

        bus.subscribe(_record)

        # Helper.schedule_write raises; per AC-007 the failure must be
        # isolated and the bus emit must still have happened.
        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.schedule_write = MagicMock(
            side_effect=RuntimeError("graphiti unreachable")
        )

        session = _make_session(turn_count=2)

        result = await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            misconceptions=[],
            topics_covered=["Macbeth"],
            aos_exercised=["AO1"],
        )

        # Drain so the F3 coroutine runs and the side_effect fires.
        await asyncio.sleep(0)

        # AC-007: caller-facing path is unaffected.
        assert result["status"] == "ended"
        # AC-002: bus subscriber saw the event regardless of write failure.
        assert len(observed) == 1
        assert observed[0]["session_id"] == session.session_id


# ---------------------------------------------------------------------------
# AC-003 — I-T6 zero-turn invariant
# ---------------------------------------------------------------------------


class TestZeroTurnGuard:
    """Sessions abandoned before any tutor turn must not emit nor schedule F3."""

    async def test_zero_turn_session_does_not_emit_session_completed(self) -> None:
        bus = EventBus()
        observed: list[str] = []
        bus.subscribe(
            lambda name, _payload: observed.append(name)
        )

        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.schedule_write = MagicMock()

        session = _make_session(turn_count=0)
        create_task_calls: list[Any] = []

        result = await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            create_task_fn=lambda coro: create_task_calls.append(coro)
            or asyncio.ensure_future(coro),
        )

        # Status flipped — the session is observably ended …
        assert result == {"session_id": session.session_id, "status": "ended"}
        assert session.status == "ended"
        # … but no event was emitted and no F3 task was scheduled.
        assert observed == []
        helper.schedule_write.assert_not_called()
        assert create_task_calls == []


# ---------------------------------------------------------------------------
# AC-006 — caller-facing ack returns within 2 s with a slow helper
# ---------------------------------------------------------------------------


class TestLatencyBudget:
    """Caller-facing ack must return well under ASSUM-004's 2 s budget."""

    async def test_ack_returns_within_session_end_budget_with_slow_helper(
        self,
    ) -> None:
        # Real GraphitiWriteHelper around a slow client — schedule_write
        # is synchronous and dispatches via asyncio.create_task, so a
        # 5 s ``add_episode`` cannot block the caller-facing path.
        slow_client = _slow_async_client()
        helper = GraphitiWriteHelper(client=slow_client, shutdown_grace_sec=30)

        bus = EventBus()
        session = _make_session(turn_count=3)

        start = time.monotonic()
        result = await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            topics_covered=["Macbeth"],
            aos_exercised=["AO1"],
        )
        duration = time.monotonic() - start

        assert result["status"] == "ended"
        # Generous absolute tolerance — we are demonstrating the
        # fire-and-forget property, not benchmarking the runtime.
        assert duration < SESSION_END_BUDGET_SEC, (
            f"session-end took {duration:.4f}s; ASSUM-004 budget is "
            f"{SESSION_END_BUDGET_SEC}s"
        )

        # The slow write is in-flight, not yet completed. Drain it so
        # asyncio doesn't warn about a pending task on teardown.
        await helper.drain(timeout_sec=10)


# ---------------------------------------------------------------------------
# AC-008 — concurrent F1 misconception + F3 writes coexist
# ---------------------------------------------------------------------------


class TestConcurrencyCoexistence:
    """An in-flight F1 write at session-end coexists with the F3 write."""

    async def test_misconception_write_and_f3_run_independently(self) -> None:
        client = MagicMock()
        client.add_episode = AsyncMock()
        helper = GraphitiWriteHelper(client=client, shutdown_grace_sec=30)

        # Schedule an F1 misconception write BEFORE session-end.
        f1_episode = MisconceptionObservedEpisode(
            student_id="lilymay",
            topic_name="Macbeth",
            misconception_text="confused fate vs. ambition",
            observed_at=datetime.now(timezone.utc),
            triggering_session_id="sess-1",
            confidence_band_at_observation="developing",
        )
        f1_task = helper.schedule_write(
            group_ids=["student-lilymay"],
            episode=f1_episode,
            flush_id="F1",
        )
        assert f1_task is not None

        bus = EventBus()
        session = _make_session(session_id="sess-1", turn_count=2)
        await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            topics_covered=["Macbeth"],
            aos_exercised=["AO1"],
        )
        # Yield so the F3 dispatch coroutine actually runs schedule_write.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        # Both writes must have been dispatched to the underlying client.
        # Drain them both before asserting against the call count.
        await helper.drain(timeout_sec=5)

        kinds_called = [
            call.kwargs.get("name") for call in client.add_episode.call_args_list
        ]
        assert "misconception_observed" in kinds_called
        assert "session_completed" in kinds_called


# ---------------------------------------------------------------------------
# AC-009 — F4 lifecycle race: 3 s timeout, then discard
# ---------------------------------------------------------------------------


class TestLifecycleRace:
    """Lifecycle race rule: complete-and-append within 3 s OR discard."""

    async def test_inflight_turn_completes_within_timeout_appends(self) -> None:
        # Simulate an in-flight ``tutor_turn`` task that finishes quickly.
        completed = asyncio.Event()

        async def _quick_turn() -> None:
            await asyncio.sleep(0.05)
            completed.set()

        task = asyncio.create_task(_quick_turn())
        result = await resolve_inflight_turn(task, timeout_sec=1.0)
        assert result is True
        assert completed.is_set()

    async def test_inflight_turn_exceeds_timeout_is_discarded(self) -> None:
        # An in-flight turn that won't land within the 3 s window.
        appended: list[str] = []

        async def _stuck_turn() -> None:
            try:
                await asyncio.sleep(10.0)
                appended.append("turn")  # would be the "append" path
            except asyncio.CancelledError:
                # Cancellation is the discard branch — must not append.
                raise

        task = asyncio.create_task(_stuck_turn())
        # Use a very short timeout so the test is fast.
        result = await resolve_inflight_turn(task, timeout_sec=0.1)
        assert result is False
        # Drain the cancellation so the task transitions to done.
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert task.cancelled() or task.done()
        # Critical assertion: the discarded turn never reached the append.
        assert appended == []

    async def test_session_completed_not_emitted_before_inflight_resolves(
        self,
    ) -> None:
        """Per AC-009: session.completed is only emitted AFTER the
        in-flight turn has been resolved one way or the other."""
        bus = EventBus()
        order: list[str] = []

        async def _record_emit(event_name: str, _payload: dict[str, Any]) -> None:
            order.append(f"emit:{event_name}")

        bus.subscribe(_record_emit)

        # In-flight turn signals when it finishes.
        finished = asyncio.Event()

        async def _slow_turn() -> None:
            await asyncio.sleep(0.05)
            order.append("turn_finished")
            finished.set()

        inflight = asyncio.create_task(_slow_turn())

        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.schedule_write = MagicMock()

        session = _make_session(turn_count=1)
        await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            inflight_task=inflight,
            inflight_timeout_sec=1.0,
            topics_covered=["Macbeth"],
        )

        # The in-flight turn must have finished BEFORE the bus emit.
        assert finished.is_set()
        emit_index = next(
            i for i, x in enumerate(order) if x.startswith("emit:")
        )
        finished_index = order.index("turn_finished")
        assert finished_index < emit_index


# ---------------------------------------------------------------------------
# AC-010 — shutdown drain wiring
# ---------------------------------------------------------------------------


class TestShutdownDrain:
    """``runtime_shutdown`` awaits ``drain()`` with the helper-default window."""

    async def test_shutdown_calls_drain_without_per_call_timeout(self) -> None:
        # Per ASSUM-011 the drain window is helper-side. The shutdown
        # hook MUST NOT pass a per-call timeout argument.
        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.drain = AsyncMock(return_value=(0, 0))

        await runtime_shutdown(helper)

        helper.drain.assert_awaited_once()
        args, kwargs = helper.drain.call_args
        # Seam-test contract from TASK-DTL-005: no positional timeout,
        # and either no kwarg or one named ``timeout`` set to 5.0.
        assert args == ()
        if "timeout" in kwargs:
            assert kwargs["timeout"] == GRAPHITI_DRAIN_WINDOW

    async def test_drain_with_three_in_flight_writes_within_window(self) -> None:
        # Real helper with a fast client — three in-flight writes must
        # all complete inside the drain window.
        client = MagicMock()

        async def _fast_write(*_: Any, **__: Any) -> None:
            await asyncio.sleep(0.01)

        client.add_episode = AsyncMock(side_effect=_fast_write)
        helper = GraphitiWriteHelper(
            client=client, shutdown_grace_sec=int(GRAPHITI_DRAIN_WINDOW)
        )

        for i in range(3):
            episode = MisconceptionObservedEpisode(
                student_id="lilymay",
                topic_name="Macbeth",
                misconception_text=f"miss {i}",
                observed_at=datetime.now(timezone.utc),
                triggering_session_id=f"sess-{i}",
                confidence_band_at_observation="developing",
            )
            helper.schedule_write(
                group_ids=["student-lilymay"], episode=episode, flush_id="F1"
            )
        assert helper.in_flight_count == 3

        succeeded, abandoned = await helper.drain(timeout_sec=5)
        assert succeeded == 3
        assert abandoned == 0

    async def test_drain_logs_abandoned_writes_after_window(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A write that won't finish within the drain window must be
        # logged with structured fields and reported as abandoned.
        client = MagicMock()

        async def _slow(*_: Any, **__: Any) -> None:
            await asyncio.sleep(2.0)

        client.add_episode = AsyncMock(side_effect=_slow)
        helper = GraphitiWriteHelper(client=client, shutdown_grace_sec=1)

        episode = MisconceptionObservedEpisode(
            student_id="lilymay",
            topic_name="Macbeth",
            misconception_text="will not finish in time",
            observed_at=datetime.now(timezone.utc),
            triggering_session_id="sess-x",
            confidence_band_at_observation="developing",
        )
        helper.schedule_write(
            group_ids=["student-lilymay"], episode=episode, flush_id="F1"
        )

        with caplog.at_level("WARNING"):
            succeeded, abandoned = await helper.drain(timeout_sec=0.1)

        assert abandoned == 1
        assert any(
            "graphiti write abandoned at shutdown" in rec.message
            or rec.message == "graphiti write abandoned at shutdown"
            for rec in caplog.records
        )

    async def test_runtime_shutdown_suppresses_drain_failure(self) -> None:
        # Drain must never raise out of the shutdown hook — process exit
        # must proceed regardless. Failure path is logged.
        helper = MagicMock(spec=GraphitiWriteHelper)
        helper.drain = AsyncMock(side_effect=RuntimeError("boom"))

        # Should not raise.
        await runtime_shutdown(helper)
        helper.drain.assert_awaited_once()


# ---------------------------------------------------------------------------
# Misconception aggregator — DDR-002 summary-only invariant
# ---------------------------------------------------------------------------


class TestMisconceptionAggregator:
    """The aggregator is summary-only and never drives a deferred write."""

    def test_record_then_snapshot_returns_observations(self) -> None:
        agg = MisconceptionAggregator()
        agg.record("s1", "confused fate vs. ambition")
        agg.record("s1", "missed the dramatic irony")
        agg.record("s2", "different session entirely")

        snap_s1 = agg.snapshot("s1")
        assert snap_s1 == [
            "confused fate vs. ambition",
            "missed the dramatic irony",
        ]
        # snapshot returns a defensive copy
        snap_s1.append("mutated")
        assert agg.snapshot("s1") == [
            "confused fate vs. ambition",
            "missed the dramatic irony",
        ]
        # cross-session isolation
        assert agg.snapshot("s2") == ["different session entirely"]

    def test_record_ignores_empty_or_whitespace_text(self) -> None:
        agg = MisconceptionAggregator()
        agg.record("s1", "")
        agg.record("s1", "   ")
        agg.record("s1", "\n\t")
        assert agg.snapshot("s1") == []

    def test_clear_drops_session(self) -> None:
        agg = MisconceptionAggregator()
        agg.record("s1", "one")
        agg.clear("s1")
        assert agg.snapshot("s1") == []


# ---------------------------------------------------------------------------
# Event bus — error isolation
# ---------------------------------------------------------------------------


class TestEventBus:
    """Subscriber failures must not crash the emitter (DDR-003 decoupling)."""

    async def test_subscriber_error_does_not_propagate(self) -> None:
        bus = EventBus()
        succeeded: list[str] = []

        def _bad(_n: str, _p: dict[str, Any]) -> None:
            raise RuntimeError("subscriber boom")

        async def _good(name: str, _p: dict[str, Any]) -> None:
            succeeded.append(name)

        bus.subscribe(_bad)
        bus.subscribe(_good)

        # Must not raise.
        await bus.emit("session.completed", {"k": "v"})
        # Subsequent subscribers ran despite the bad one.
        assert succeeded == ["session.completed"]

    async def test_async_and_sync_subscribers_both_supported(self) -> None:
        bus = EventBus()
        sync_calls: list[str] = []
        async_calls: list[str] = []

        def _sync(name: str, _p: dict[str, Any]) -> None:
            sync_calls.append(name)

        async def _async(name: str, _p: dict[str, Any]) -> None:
            async_calls.append(name)

        bus.subscribe(_sync)
        bus.subscribe(_async)
        await bus.emit("e", {})
        assert sync_calls == ["e"]
        assert async_calls == ["e"]


# ---------------------------------------------------------------------------
# Seam test alignment — emit-before-create_task using patched create_task
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_seam_session_end_emits_event_before_f3_create_task() -> None:
    """Mirror the seam test scaffold from the task spec: emit < create_task."""
    bus = EventBus()
    helper = MagicMock(spec=GraphitiWriteHelper)
    helper.schedule_write = MagicMock()

    call_log: list[str] = []
    bus.subscribe(
        lambda _n, _p: call_log.append("emit")
    )

    def _patched_create_task(coro: Any) -> Any:
        call_log.append("create_task")
        # Close the coro so we don't get an unawaited-coro warning.
        coro.close()
        return MagicMock()

    with patch("asyncio.create_task", side_effect=_patched_create_task):
        session = _make_session(turn_count=1)
        await perform_session_end(
            session=session,
            student_id="lilymay",
            write_helper=helper,
            event_bus=bus,
            topics_covered=["Macbeth"],
            create_task_fn=_patched_create_task,
        )

    # DDR-003 conformance: emit happened first.
    assert call_log.index("emit") < call_log.index("create_task")


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_seam_shutdown_drain_uses_graphiti_drain_window_default() -> None:
    """Mirror the seam test from the task spec: drain called with no timeout."""
    helper = MagicMock(spec=GraphitiWriteHelper)
    helper.drain = AsyncMock()

    await runtime_shutdown(helper)

    helper.drain.assert_awaited_once()
    args, kwargs = helper.drain.call_args
    assert args == ()
    assert "timeout" not in kwargs or kwargs["timeout"] == GRAPHITI_DRAIN_WINDOW


# ---------------------------------------------------------------------------
# SESSION_END_INFLIGHT_TIMEOUT_SEC default sanity
# ---------------------------------------------------------------------------


def test_inflight_timeout_default_is_3_seconds() -> None:
    """F4 lifecycle race resolution constant pins to 3 s per task spec."""
    assert SESSION_END_INFLIGHT_TIMEOUT_SEC == 3.0


def test_graphiti_drain_window_default_is_5_seconds() -> None:
    """ASSUM-011 resolution constant pins to 5 s per task spec."""
    assert GRAPHITI_DRAIN_WINDOW == 5.0
