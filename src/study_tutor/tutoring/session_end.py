"""Session-end orchestration for the Tutor handler (TASK-DTL-005).

This module implements the end-to-end ``tutor_session_end`` workflow:

1. Resolve any in-flight ``tutor_turn`` for this session within a 3 s
   inner timeout (the F4 lifecycle race resolution).
2. Generate the session-end summary (topics, AOs, turn count, duration,
   1-2 sentence narrative, misconceptions surfaced).
3. Apply the I-T6 zero-turn invariant guard — sessions abandoned before
   any tutor turn do **not** emit ``session.completed`` and do **not**
   schedule the F3 Graphiti write.
4. Transition session state ``active → ended``.
5. Emit ``session.completed`` on the in-process events bus, **before**
   the F3 Graphiti write task is scheduled (DDR-003).
6. Schedule the F3 write via :class:`asyncio.create_task` — fire-and-
   forget; the handler never awaits the write.
7. Return ``{ session_id, status: "ended" }`` to the MCP caller within
   the 2 s session-end latency budget (ASSUM-004).

A separate :func:`runtime_shutdown` helper wires
:meth:`GraphitiWriteHelper.drain` into the runtime shutdown hook so
in-flight writes get :data:`GRAPHITI_DRAIN_WINDOW` seconds to finish
before being abandoned (ASSUM-011 resolution).

Design notes (cross-references):

* DDR-002: the in-memory misconception aggregator is **summary-only**.
  F1 misconception writes are dispatched per-observation by the Coach
  AsyncSubAgent (TASK-DTL-004). We never double-write.
* DDR-003: the events bus is decoupled from Graphiti durability — a
  failure inside the F3 write task never suppresses ``session.completed``.
* I-T6: the zero-turn invariant lives at the handler boundary, not at
  the bus, so the bus stays dumb and the handler decides whether to emit.
* The 3 s in-flight-turn timeout (F4 lifecycle race) is a defensible
  upper bound: turns about to complete will land within it; turns that
  won't, won't land within any reasonable session-end budget anyway.
* ``GRAPHITI_DRAIN_WINDOW`` is defined here as the consumer-side
  default. Per ASSUM-011 the helper itself owns the drain default; the
  shutdown hook calls :meth:`GraphitiWriteHelper.drain` with no per-call
  argument so the helper's own default wins.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.episodes import SessionCompletedEpisode
from study_tutor.knowledge.student_model import STUDENT_GROUP_PREFIX
from study_tutor.session.tutor_session import TutorSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: ASSUM-011 resolution. Default shutdown drain window (seconds).
#:
#: The helper itself (:class:`GraphitiWriteHelper`) owns the canonical
#: default at construction time; this constant is the consumer-side mirror
#: so the runtime shutdown hook has a documented number to log against.
#: Per the integration contract with TASK-GSM-004 the shutdown hook calls
#: ``drain()`` with no per-call timeout argument and lets the helper's
#: default apply (so ``GRAPHITI_DRAIN_WINDOW`` is informational on this
#: side, not authoritative — the helper is the source of truth).
GRAPHITI_DRAIN_WINDOW: float = 5.0

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


def _format_duration_minutes(started_at: datetime, ended_at: datetime) -> int:
    """Return the elapsed minutes between two timestamps, never negative."""
    delta = (ended_at - started_at).total_seconds() / 60.0
    if delta < 0:
        return 0
    return int(round(delta))


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


def build_session_completed_episode(
    *,
    session: TutorSession,
    student_id: str,
    misconceptions: list[str],
    topics_covered: list[str] | None = None,
    aos_exercised: list[str] | None = None,
    ended_at: datetime | None = None,
) -> SessionCompletedEpisode:
    """Project a :class:`TutorSession` into a :class:`SessionCompletedEpisode`.

    The episode carries: topics covered, AOs exercised, turn count,
    duration, narrative summary (1-2 sentences), and misconceptions
    surfaced. ``topics_covered`` and ``aos_exercised`` are caller-supplied
    because Phase-1 ``TutorSession`` does not yet track them; production
    wiring will pass the planner-derived values, tests pass mocks.
    """
    if ended_at is None:
        ended_at = datetime.now(timezone.utc)
    topics = list(topics_covered or ([session.topic] if session.topic else []))
    aos = list(aos_exercised or [])
    duration_minutes = _format_duration_minutes(session.started_at, ended_at)
    narrative = build_narrative_summary(
        turn_count=len(session.turns),
        topics_covered=topics,
        misconceptions=misconceptions,
        duration_minutes=duration_minutes,
    )
    return SessionCompletedEpisode(
        session_id=session.session_id,
        student_id=student_id,
        subject_slug=session.subject,
        text_name=session.topic or session.subject,
        topics_covered=topics,
        aos_exercised=aos,
        narrative_summary=narrative,
        started_at=session.started_at,
        ended_at=ended_at,
    )


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


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


async def perform_session_end(
    *,
    session: TutorSession,
    student_id: str,
    write_helper: GraphitiWriteHelper | None,
    event_bus: EventBus,
    misconceptions: list[str] | None = None,
    topics_covered: list[str] | None = None,
    aos_exercised: list[str] | None = None,
    inflight_task: asyncio.Task[Any] | None = None,
    inflight_timeout_sec: float = SESSION_END_INFLIGHT_TIMEOUT_SEC,
    transition_state: Callable[[], None] | None = None,
    create_task_fn: Callable[[Awaitable[Any]], asyncio.Task[Any]] | None = None,
) -> dict[str, Any]:
    """Drive the full session-end workflow on the same code path.

    The strict ordering inside the handler is, after the in-flight turn
    has been resolved (per AC-009 / .feature line 452-457):

    1. Apply the I-T6 zero-turn guard. If ``len(session.turns) == 0``,
       transition state to ``ended`` and return WITHOUT emitting
       ``session.completed`` and WITHOUT scheduling the F3 write.
    2. Otherwise:
       a. Build the :class:`SessionCompletedEpisode` payload.
       b. Transition state ``active → ended``.
       c. ``await event_bus.emit("session.completed", payload)`` —
          this MUST happen before the F3 task is scheduled (DDR-003).
       d. Call ``create_task_fn(write_helper_coro)`` to schedule the
          F3 write fire-and-forget. We do not await the returned task.
       e. Return ``{session_id, status: "ended"}`` to the caller.

    Args:
        session: The live :class:`TutorSession` to end.
        student_id: Stable learner slug — drives the group_ids list.
        write_helper: Shared write helper, or ``None`` (graceful no-op).
        event_bus: In-process bus on which to emit ``session.completed``.
        misconceptions: Per-session aggregator snapshot (summary-only).
        topics_covered: Topics drawn from the session plan.
        aos_exercised: Assessment objectives drawn from the session plan.
        inflight_task: Optional in-flight ``tutor_turn`` task to resolve.
        inflight_timeout_sec: 3 s default per F4 lifecycle race rule.
        transition_state: Callable that flips ``session.status`` to
            ``"ended"`` (typically ``store.end``). Must be supplied so
            the test can verify ordering vs. the bus emit; in production
            the adapter passes a closure over the store.
        create_task_fn: Indirection over :func:`asyncio.create_task` so
            tests can assert the F3 write is scheduled via create_task
            and that the bus emit happens *before* the create_task call
            (the AC-001 ordering assertion).

    Returns:
        ``{"session_id": <id>, "status": "ended"}`` — even on the
        zero-turn branch (status is still ``"ended"`` because we did
        flip the state).
    """
    start = time.monotonic()
    misc_list = list(misconceptions or [])
    if create_task_fn is None:
        create_task_fn = asyncio.create_task

    # 1. F4 lifecycle race resolution: resolve any in-flight turn first.
    #    On timeout we cancel; the cancelled turn never appends.
    await resolve_inflight_turn(inflight_task, timeout_sec=inflight_timeout_sec)

    # 2. I-T6 zero-turn guard. Inspected AFTER in-flight resolution so a
    #    turn that completed within the timeout counts toward the guard.
    turn_count = len(session.turns)
    if turn_count == 0:
        logger.info(
            "session ended with zero turns; suppressing session.completed and F3",
            extra={
                "event": "session_end_zero_turn_guard",
                "session_id": session.session_id,
            },
        )
        if transition_state is not None:
            transition_state()
        else:
            session.status = "ended"
        return {"session_id": session.session_id, "status": "ended"}

    # 3. Build the F3 episode payload up-front so any validation error
    #    surfaces before we mutate state. SessionCompletedEpisode uses
    #    ``extra="forbid"`` and pydantic validation — a bad payload here
    #    would otherwise leak into a state where the bus had emitted but
    #    the F3 write could not be constructed.
    ended_at = datetime.now(timezone.utc)
    episode = build_session_completed_episode(
        session=session,
        student_id=student_id,
        misconceptions=misc_list,
        topics_covered=topics_covered,
        aos_exercised=aos_exercised,
        ended_at=ended_at,
    )

    # 4. State transition. After this line, ``tutor_turn`` will reject
    #    any further user messages (it checks ``session.status``).
    if transition_state is not None:
        transition_state()
    else:
        session.status = "ended"

    # 5. Emit BEFORE scheduling the F3 write task. DDR-003: subscribers
    #    observe ``session.completed`` regardless of whether the
    #    Graphiti write succeeds.
    payload: dict[str, Any] = {
        "session_id": session.session_id,
        "student_id": student_id,
        "subject_slug": session.subject,
        "topics_covered": list(episode.topics_covered),
        "aos_exercised": list(episode.aos_exercised),
        "turn_count": turn_count,
        "narrative_summary": episode.narrative_summary,
        "started_at": session.started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
    }
    await event_bus.emit(SESSION_COMPLETED_EVENT, payload)

    # 6. Fire-and-forget F3 write. We pass through ``create_task_fn`` so
    #    tests can assert the order ``emit → create_task`` (AC-001).
    #    A failure inside the write task is logged with structured fields
    #    by the helper; ``session.completed`` was already on the bus.
    if write_helper is not None:
        coro = _f3_write_coroutine(
            write_helper=write_helper,
            student_id=student_id,
            episode=episode,
        )
        try:
            create_task_fn(coro)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            # ``asyncio.create_task`` can only fail when there's no
            # running loop; in that case the F3 write is dropped with a
            # log line — the session is still observably ``ended``.
            logger.warning(
                "F3 create_task failed; session.completed already emitted",
                extra={
                    "event": "session_end_f3_dispatch_failed",
                    "session_id": session.session_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            # Close the unawaited coroutine so we don't get a warning.
            coro.close()

    duration = time.monotonic() - start
    if duration > SESSION_END_BUDGET_SEC:
        logger.warning(
            "session-end exceeded ASSUM-004 budget",
            extra={
                "event": "session_end_budget_exceeded",
                "session_id": session.session_id,
                "duration_seconds": duration,
                "budget_seconds": SESSION_END_BUDGET_SEC,
            },
        )

    return {"session_id": session.session_id, "status": "ended"}


async def _f3_write_coroutine(
    *,
    write_helper: GraphitiWriteHelper,
    student_id: str,
    episode: SessionCompletedEpisode,
) -> None:
    """Inner coroutine wrapping the helper's F3 dispatch.

    Exists so :func:`perform_session_end` has a single :class:`Awaitable`
    to hand to ``create_task_fn`` (the indirection over
    :func:`asyncio.create_task`). The helper's
    :meth:`schedule_write` is itself synchronous and internally uses
    ``asyncio.create_task``; wrapping here keeps a single fire-and-forget
    site for the F3 path so ordering tests have one stable hook.

    Failures inside this coroutine are caught here and logged — never
    re-raised — so an exception escaping into ``create_task`` doesn't
    crash the event loop with an unhandled-task warning.
    """
    try:
        group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
        write_helper.schedule_write(
            group_ids=group_ids,
            episode=episode,
            flush_id="F3",
        )
    except Exception as exc:  # noqa: BLE001 — structured-log failure isolation
        logger.warning(
            "F3 session-completed write failed",
            extra={
                "event": "session_end_f3_write_failed",
                "session_id": episode.session_id,
                "student_id": student_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )


# ---------------------------------------------------------------------------
# Shutdown drain wiring (ASSUM-011)
# ---------------------------------------------------------------------------


async def runtime_shutdown(write_helper: GraphitiWriteHelper) -> None:
    """Await ``write_helper.drain()`` from the runtime shutdown hook.

    ASSUM-011 resolution: the drain timeout lives on the helper, not on
    the caller. We deliberately call :meth:`GraphitiWriteHelper.drain`
    with **no** per-call argument so the helper's own
    ``GRAPHITI_DRAIN_WINDOW`` default (5 s) applies — passing a timeout
    here would re-introduce the per-flush-site shape this assumption
    explicitly closed.

    A failure inside :meth:`drain` is logged with structured fields and
    suppressed: the runtime is shutting down regardless, and a drain
    failure must never block process exit.
    """
    try:
        await write_helper.drain()
    except Exception as exc:  # noqa: BLE001 — shutdown must never raise
        logger.warning(
            "graphiti drain failed during shutdown",
            extra={
                "event": "graphiti_drain_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "drain_window_sec": GRAPHITI_DRAIN_WINDOW,
            },
        )


__all__ = [
    "GRAPHITI_DRAIN_WINDOW",
    "SESSION_END_INFLIGHT_TIMEOUT_SEC",
    "SESSION_END_BUDGET_SEC",
    "SESSION_COMPLETED_EVENT",
    "EventBus",
    "MisconceptionAggregator",
    "build_narrative_summary",
    "build_session_completed_episode",
    "resolve_inflight_turn",
    "perform_session_end",
    "runtime_shutdown",
]
