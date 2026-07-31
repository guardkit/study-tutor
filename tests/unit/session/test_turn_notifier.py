"""Stage 2 — :class:`TurnNotifier`, the mirror's in-process change signal.

Hermetic by construction: the notifier is pure ``asyncio`` — no broker, no
threads, no external anything. These tests pin the contract the SSE mirror
stream leans on: a notify wakes every parked waiter, a timeout returns normally
(it is the stream's tick, not an error), a notify with nobody listening is a
harmless no-op, and per-session state does not accumulate.
"""

from __future__ import annotations

import asyncio

from study_tutor.session.notifier import TurnNotifier

SESSION_ID = "sess-mirror-1"


async def test_notify_wakes_a_waiter() -> None:
    """The whole point: a persisted row wakes the watcher immediately."""
    notifier = TurnNotifier()
    woke = asyncio.Event()

    async def watcher() -> None:
        # A timeout far beyond the test's patience — if this returns promptly it
        # can only be because notify() woke it.
        await notifier.wait_for_change(SESSION_ID, timeout=30.0)
        woke.set()

    task = asyncio.create_task(watcher())
    await asyncio.sleep(0)  # let the watcher park
    notifier.notify(SESSION_ID)

    await asyncio.wait_for(task, timeout=1.0)
    assert woke.is_set()


async def test_timeout_returns_normally_when_unsignalled() -> None:
    """A timeout is NOT an error — it is the stream's regular re-read tick."""
    notifier = TurnNotifier()

    result = await notifier.wait_for_change(SESSION_ID, timeout=0.01)

    assert result is None


async def test_multiple_waiters_all_wake_on_one_notify() -> None:
    """Two phones watching the same session both see the turn."""
    notifier = TurnNotifier()

    tasks = [
        asyncio.create_task(notifier.wait_for_change(SESSION_ID, timeout=30.0))
        for _ in range(3)
    ]
    await asyncio.sleep(0)
    notifier.notify(SESSION_ID)

    done, pending = await asyncio.wait(tasks, timeout=1.0)
    assert not pending
    assert len(done) == 3


async def test_notify_with_no_waiters_is_a_no_op() -> None:
    """Every persisted row pings the notifier; nearly none are being watched."""
    notifier = TurnNotifier()

    notifier.notify(SESSION_ID)
    notifier.notify(SESSION_ID)

    # No state created, and a waiter arriving afterwards does NOT return on the
    # stale signal — it parks and times out like any other first watcher.
    assert notifier._signals == {}
    await asyncio.wait_for(
        notifier.wait_for_change(SESSION_ID, timeout=0.01), timeout=1.0
    )


async def test_notify_for_another_session_does_not_wake_this_waiter() -> None:
    """The signal is per session — the robot's other subject must not leak in."""
    notifier = TurnNotifier()
    task = asyncio.create_task(notifier.wait_for_change(SESSION_ID, timeout=0.05))
    await asyncio.sleep(0)

    notifier.notify("sess-someone-else")

    # It still had to wait out its timeout rather than returning on the signal.
    await asyncio.wait_for(task, timeout=1.0)


async def test_per_session_state_is_cleaned_up_after_the_last_waiter_leaves() -> None:
    """A long-lived server must not accumulate one entry per session ever seen."""
    notifier = TurnNotifier()

    tasks = [
        asyncio.create_task(notifier.wait_for_change(SESSION_ID, timeout=30.0))
        for _ in range(2)
    ]
    await asyncio.sleep(0)
    assert SESSION_ID in notifier._signals

    notifier.notify(SESSION_ID)
    await asyncio.wait(tasks, timeout=1.0)

    assert notifier._signals == {}


async def test_state_is_cleaned_up_after_a_timeout_too() -> None:
    notifier = TurnNotifier()

    await notifier.wait_for_change(SESSION_ID, timeout=0.01)

    assert notifier._signals == {}


async def test_a_waiter_can_re_arm_and_be_woken_again() -> None:
    """The stream loops: wake, re-read, park again — the signal must re-arm."""
    notifier = TurnNotifier()
    wakes = 0

    async def watcher() -> None:
        nonlocal wakes
        for _ in range(2):
            await notifier.wait_for_change(SESSION_ID, timeout=30.0)
            wakes += 1

    task = asyncio.create_task(watcher())
    await asyncio.sleep(0)
    notifier.notify(SESSION_ID)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    notifier.notify(SESSION_ID)

    await asyncio.wait_for(task, timeout=1.0)
    assert wakes == 2
