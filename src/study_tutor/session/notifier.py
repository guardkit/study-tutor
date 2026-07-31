"""In-process per-session change signal for the live robot-session mirror (Stage 2).

The phone's read-only mirror watches the session the Reachy Mini robot is
driving. Stage 1 gave it a delta *read* (``GET …/turns?since=``); this module
gives the SSE stream route (:mod:`study_tutor.http.turn_stream_sse`) a way to
wake the instant a row is persisted, instead of waiting out its poll tick.

Deliberately tiny and deliberately local:

* **Two methods only** — :meth:`TurnNotifier.notify` (sync, never raises, never
  blocks) and :meth:`TurnNotifier.wait_for_change` (async, returns on signal
  *or* timeout; a timeout is NOT an error).
* **No broker, no threads.** This is an ``asyncio`` primitive in one process —
  no NATS, no external queue, no background task. Cross-process writes are not
  this module's job: the stream route re-reads on every timeout tick, so a write
  from another worker still surfaces within ~one poll interval.
* **Self-cleaning.** Per-session state exists only while someone is waiting on
  it; the last waiter to leave removes it, so a long-lived process does not
  accumulate one entry per session it has ever served.

The signal carries **no payload** — a waiter is told only "something changed",
and re-reads the transcript through the service (which is where ownership and
the row projection live). That keeps the notifier out of the ownership path.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class TurnNotifierPort(Protocol):
    """The shape :class:`~study_tutor.session.service.SessionService` depends on.

    Lets the service take a fake (or ``None``) without importing the concrete
    notifier's machinery — the same duck-typed seam the store/provider pairs use.
    """

    def notify(self, session_id: str) -> None:  # pragma: no cover - protocol
        ...

    async def wait_for_change(
        self, session_id: str, *, timeout: float
    ) -> None:  # pragma: no cover - protocol
        ...


class _SessionSignal:
    """Per-session waiters + the event they are parked on.

    ``version`` counts signals for this session. Each :meth:`TurnNotifier.notify`
    bumps it and *replaces* the event, waking everyone parked on the old one —
    the swap is what makes the signal edge-triggered and re-armable, so a waiter
    that arrives after a notify parks fresh rather than returning immediately on
    a stale set flag.
    """

    __slots__ = ("event", "version", "waiters")

    def __init__(self) -> None:
        self.event = asyncio.Event()
        self.version = 0
        self.waiters = 0


class TurnNotifier:
    """In-process change signal, one logical channel per ``session_id``."""

    def __init__(self) -> None:
        self._signals: dict[str, _SessionSignal] = {}

    def notify(self, session_id: str) -> None:
        """Signal that ``session_id``'s transcript changed.

        Sync, non-blocking and **never raises**: it is called from the request
        path right after a row is persisted, and a notification failure must
        never turn a successful write into a failed turn. With no waiters it is
        a no-op (there is no state to keep and nothing to deliver to).
        """
        try:
            signal = self._signals.get(session_id)
            if signal is None:
                # Nobody is watching this session — nothing to wake, and no
                # state worth creating (see the self-cleaning note above).
                return
            signal.version += 1
            waiting, signal.event = signal.event, asyncio.Event()
            waiting.set()
        except Exception:  # pragma: no cover - defensive; notify never raises
            logger.debug(
                "event=turn_notify_failed session_id=%s", session_id, exc_info=True
            )

    async def wait_for_change(self, session_id: str, *, timeout: float) -> None:
        """Park until ``session_id`` changes or ``timeout`` seconds elapse.

        Returns ``None`` either way — **a timeout is not an error**, it is the
        stream route's regular tick (and the fallback that surfaces writes made
        by another process). Multiple waiters on the same session all wake on
        one :meth:`notify`.
        """
        signal = self._signals.get(session_id)
        if signal is None:
            signal = _SessionSignal()
            self._signals[session_id] = signal

        signal.waiters += 1
        waiting = signal.event
        try:
            await asyncio.wait_for(waiting.wait(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            # The tick, not a failure.
            return
        finally:
            signal.waiters -= 1
            if signal.waiters <= 0 and self._signals.get(session_id) is signal:
                del self._signals[session_id]


__all__ = ["TurnNotifier", "TurnNotifierPort"]
