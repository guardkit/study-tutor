"""Unit tests for the surviving session-end helpers.

After the Postgres store migration removed the deferred graph-store
write path, this module covers only the backend-neutral session-end
building blocks that
remain in :mod:`study_tutor.tutoring.session_end`:

* narrative-summary projection (1 or 2 sentences, ASSUM-010),
* the summary-only misconception aggregator (DDR-002),
* the decoupled event bus (subscriber error isolation, DDR-003), and
* the F4 in-flight ``tutor_turn`` lifecycle-race resolution (complete
  within the timeout OR discard with no append).
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from study_tutor.tutoring.session_end import (
    SESSION_END_INFLIGHT_TIMEOUT_SEC,
    EventBus,
    MisconceptionAggregator,
    build_narrative_summary,
    resolve_inflight_turn,
)


# ---------------------------------------------------------------------------
# Narrative summary is 1 or 2 sentences (boundary)
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
# F4 lifecycle race: timeout, then discard
# ---------------------------------------------------------------------------


class TestLifecycleRace:
    """Lifecycle race rule: complete-and-append within the timeout OR discard."""

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
        # An in-flight turn that won't land within the window.
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
# SESSION_END_INFLIGHT_TIMEOUT_SEC default sanity
# ---------------------------------------------------------------------------


def test_inflight_timeout_default_is_3_seconds() -> None:
    """F4 lifecycle race resolution constant pins to 3 s per task spec."""
    assert SESSION_END_INFLIGHT_TIMEOUT_SEC == 3.0
