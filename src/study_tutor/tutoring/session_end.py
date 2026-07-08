"""Session-end support types for the Tutor handler.

The durable session-end write path now lives in
:meth:`study_tutor.session.service.SessionService.end_session` (Postgres,
ADR-ARCH-023). This module retains the transport-agnostic pieces the MCP
adapter still composes around that write:

* :class:`EventBus` — the in-process bus on which the adapter emits
  ``session.completed`` (design-review #5; emit-before-write per DDR-003).
* :class:`MisconceptionAggregator` — the per-session, **summary-only**
  in-memory misconception list (DDR-002); it never drives a write.
* :func:`build_narrative_summary` — the deterministic 1-2 sentence
  session summary (ASSUM-010; no LLM call).
* :func:`resolve_inflight_turn` — the F4 lifecycle-race resolver that
  discards a ``tutor_turn`` still in flight when session-end arrives.

Design notes (cross-references):

* DDR-002: the misconception aggregator is summary-only; F1 misconception
  writes are dispatched per-observation by the Coach.
* I-T6: the zero-turn invariant lives at the handler boundary, not on the
  bus, so the bus stays dumb and the handler decides whether to emit.
* The 3 s in-flight-turn timeout (F4 lifecycle race) is a defensible
  upper bound: turns about to complete will land within it; turns that
  won't, won't land within any reasonable session-end budget anyway.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: F4 lifecycle-race resolution: maximum time the session-end handler
#: waits for an in-flight ``tutor_turn`` to complete before discarding it.
#: Discarded turns are cancelled so they never append to
#: :attr:`TutorSession.turns` after the session has been marked ``ended``.
SESSION_END_INFLIGHT_TIMEOUT_SEC: float = 3.0

#: ASSUM-004 — caller-facing session-end budget. The handler's wall-clock
#: target for returning the acknowledgement to the MCP caller. The 3 s
#: in-flight-turn wait is the main consumer of this budget, so the
#: post-resolution work (state transition + bus emit + create_task +
#: ack) must remain trivially synchronous-equivalent.
SESSION_END_BUDGET_SEC: float = 2.0

#: Bus event name. Kept as a literal so subscribers can match exactly.
SESSION_COMPLETED_EVENT: str = "session.completed"


# ---------------------------------------------------------------------------
# Events bus
# ---------------------------------------------------------------------------

#: Subscriber callable shape. Sync subscribers return ``None``; async
#: subscribers return an awaitable. The bus tolerates both.
SubscriberFn = Callable[[str, dict[str, Any]], Any]


class EventBus:
    """Minimal in-process events bus for FEAT-PH1-003.

    Subscribers are invoked in registration order. A failing subscriber
    does **not** suppress later subscribers and does **not** propagate to
    the emitter — observability sinks must never crash the caller-facing
    path (DDR-003: events are decoupled from durability).
    """

    def __init__(self) -> None:
        self._subscribers: list[SubscriberFn] = []

    def subscribe(self, handler: SubscriberFn) -> None:
        """Register ``handler`` for every subsequent emit.

        Subscribers are stored in registration order so deterministic
        replay (e.g. snapshot tests) is straightforward.
        """
        self._subscribers.append(handler)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """Dispatch ``event_name`` to every subscriber.

        Async subscribers are awaited so emit order is causal: by the
        time :meth:`emit` returns, every subscriber has either completed
        or its callback has been scheduled. Errors inside subscribers
        are logged with structured fields and suppressed.
        """
        # Snapshot so a subscriber that subscribes during dispatch does
        # not get this same emit (avoids a class of self-recursion bugs).
        for handler in list(self._subscribers):
            try:
                result = handler(event_name, payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # noqa: BLE001 — observability boundary
                logger.warning(
                    "event subscriber raised; suppressed",
                    extra={
                        "event": "event_subscriber_error",
                        "event_name": event_name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )


# ---------------------------------------------------------------------------
# Per-session misconception aggregator (summary-only)
# ---------------------------------------------------------------------------


@dataclass
class MisconceptionAggregator:
    """Per-session in-memory misconception list — summary-only (DDR-002).

    The Coach AsyncSubAgent already dispatches F1 misconception writes
    per-observation (TASK-DTL-004). This aggregator is **read-only for
    the session-end summary field** — it never drives a deferred write
    and never replaces the per-observation F1 path.
    """

    # session_id -> list of misconception text snippets observed
    _by_session: dict[str, list[str]] = field(default_factory=dict)

    def record(self, session_id: str, misconception_text: str) -> None:
        """Record a misconception observation for this session.

        Empty / whitespace-only text is ignored so accidental empty
        observations don't pollute the summary.
        """
        text = (misconception_text or "").strip()
        if not text:
            return
        self._by_session.setdefault(session_id, []).append(text)

    def snapshot(self, session_id: str) -> list[str]:
        """Return a defensive copy of the misconception list for ``session_id``."""
        return list(self._by_session.get(session_id, ()))

    def clear(self, session_id: str) -> None:
        """Drop the per-session list once the summary has been built."""
        self._by_session.pop(session_id, None)


# ---------------------------------------------------------------------------
# Summary builders
# ---------------------------------------------------------------------------


def build_narrative_summary(
    *,
    turn_count: int,
    topics_covered: list[str],
    misconceptions: list[str],
    duration_minutes: int,
) -> str:
    """Build a 1-2 sentence narrative summary (ASSUM-010).

    Uses a deterministic template (no LLM call) so the summary is fast,
    free, and unit-testable. The output is always 1 sentence when there
    are no misconceptions, 2 sentences otherwise — both shapes are
    permitted by the boundary scenario outline in the .feature file.
    """
    topic_phrase = (
        ", ".join(topics_covered) if topics_covered else "no specific topic"
    )
    sentence_one = (
        f"Session covered {topic_phrase} across {turn_count} turn"
        f"{'s' if turn_count != 1 else ''} over {duration_minutes} minute"
        f"{'s' if duration_minutes != 1 else ''}."
    )
    if not misconceptions:
        return sentence_one
    # Cap the misconception phrase so the summary stays short.
    surfaced = "; ".join(misconceptions[:3])
    if len(misconceptions) > 3:
        surfaced = f"{surfaced} (+{len(misconceptions) - 3} more)"
    sentence_two = f"Misconceptions surfaced: {surfaced}."
    return f"{sentence_one} {sentence_two}"


# ---------------------------------------------------------------------------
# In-flight turn resolution (F4 lifecycle race)
# ---------------------------------------------------------------------------


async def resolve_inflight_turn(
    inflight_task: asyncio.Task[Any] | None,
    timeout_sec: float = SESSION_END_INFLIGHT_TIMEOUT_SEC,
) -> bool:
    """Resolve any in-flight ``tutor_turn`` task within ``timeout_sec``.

    Returns ``True`` if the task completed within the budget (its append
    to ``TutorSession.turns`` will already have happened), ``False`` if
    we timed out and cancelled the task (the discard branch — no append).

    ``asyncio.shield`` prevents :func:`asyncio.wait_for` from cancelling
    the underlying task on timeout; we cancel explicitly afterwards so
    the discard semantic is uniform regardless of whether the task is
    still doing IO or already past the append site.
    """
    if inflight_task is None or inflight_task.done():
        return True
    try:
        await asyncio.wait_for(
            asyncio.shield(inflight_task), timeout=timeout_sec
        )
        return True
    except asyncio.TimeoutError:
        logger.info(
            "in-flight tutor_turn discarded at session-end (F4 lifecycle race)",
            extra={
                "event": "session_end_inflight_turn_discarded",
                "timeout_sec": timeout_sec,
            },
        )
        # Discard: cancel so the task cannot append after state flips.
        # We do NOT await the cancellation — the session-end budget is
        # already at risk and the cancelled task's logging is best-effort.
        inflight_task.cancel()
        return False
    except Exception as exc:  # noqa: BLE001 — boundary catch
        # The in-flight turn raised; treat as "resolved with no append"
        # so we can still complete the session-end path.
        logger.warning(
            "in-flight tutor_turn raised at session-end; treating as resolved",
            extra={
                "event": "session_end_inflight_turn_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return True


__all__ = [
    "SESSION_END_INFLIGHT_TIMEOUT_SEC",
    "SESSION_END_BUDGET_SEC",
    "SESSION_COMPLETED_EVENT",
    "EventBus",
    "MisconceptionAggregator",
    "build_narrative_summary",
    "resolve_inflight_turn",
]
