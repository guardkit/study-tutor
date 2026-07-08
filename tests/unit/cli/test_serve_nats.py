"""Tests for the ``serve-nats`` CLI subcommand (TASK-NATS-PH1-006).

These tests pin the four acceptance criteria from
``TASK-NATS-PH1-006-serve-nats-cli-subcommand.md``:

* AC-001 — ``serve-nats --help`` advertises ``--nats``, ``--agent-id``,
  ``--log-level``.
* AC-002/AC-003 — SIGTERM (or any caller setting the shared shutdown
  event) drives the adapter through ``start()`` → ``stop()`` and the
  process exits with code 0 within the drain window.
* AC-004 — ``AgentConfig`` validation failure exits 1 with a clear,
  prefixed error message.

The CLI body lazy-imports ``study_tutor.adapters.command_router`` and
``study_tutor.adapters.nats_adapter``; those modules are produced by
TASK-NATS-PH1-004 / TASK-NATS-PH1-005 (both ``pending`` at the time of
this task). The unit tests therefore mock at the *function* seam
(``_build_nats_runtime``, ``_load_agent_config``, ``_serve_adapter``)
rather than at module-import time so this test file does not depend on
those downstream modules existing.
"""

from __future__ import annotations

import asyncio
import signal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from study_tutor.cli import main as cli_main
from study_tutor.cli.main import (
    _AgentConfigValidationError,
    _serve_adapter,
    cli,
)


# ---------------------------------------------------------------------------
# AC-001 — flag surface
# ---------------------------------------------------------------------------


def test_serve_nats_help_lists_required_flags() -> None:
    """AC-001: ``--help`` advertises ``--nats``, ``--agent-id``, ``--log-level``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["serve-nats", "--help"])

    assert result.exit_code == 0, result.output
    assert "--nats" in result.output
    assert "--agent-id" in result.output
    assert "--log-level" in result.output


# ---------------------------------------------------------------------------
# AC-004 — AgentConfig validation failure → exit 1 with a clear message
# ---------------------------------------------------------------------------


def test_serve_nats_exits_1_when_agent_config_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-004: A bad ``AgentConfig`` surfaces as a non-zero exit.

    The CLI must print a ``[study-tutor] Error: AgentConfig validation
    failed`` banner that includes the underlying pydantic message so an
    operator can find the missing env var without re-reading source.
    """
    cause = ValueError("Field required: AGENT_MODELS__REASONING_MODEL")

    def _raise() -> None:
        raise _AgentConfigValidationError(cause)

    monkeypatch.setattr(cli_main, "_load_agent_config", _raise)

    runner = CliRunner()
    result = runner.invoke(cli, ["serve-nats", "--nats", "nats://localhost:4222"])

    assert result.exit_code == 1
    assert "AgentConfig validation failed" in result.output
    assert "AGENT_MODELS__REASONING_MODEL" in result.output


# ---------------------------------------------------------------------------
# Flag wiring — --nats overrides config.nats.url
# ---------------------------------------------------------------------------


def test_serve_nats_flag_overrides_config_nats_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--nats`` must overwrite ``config.nats.url`` before the adapter is built."""
    fake_config = SimpleNamespace(nats=SimpleNamespace(url="nats://default:4222"))

    captured: dict[str, object] = {}

    def _capture_runtime(config: object, agent_id: str) -> MagicMock:
        captured["config"] = config
        captured["agent_id"] = agent_id
        return MagicMock()

    async def _capture_serve(*args: object, **kwargs: object) -> None:
        captured["serve_args"] = args
        captured["serve_kwargs"] = kwargs

    monkeypatch.setattr(cli_main, "_load_agent_config", lambda: fake_config)
    monkeypatch.setattr(cli_main, "_build_nats_runtime", _capture_runtime)
    monkeypatch.setattr(cli_main, "_serve_adapter", _capture_serve)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["serve-nats", "--nats", "nats://override:4222", "--agent-id", "tutor-x"],
    )

    assert result.exit_code == 0, result.output
    assert fake_config.nats.url == "nats://override:4222"
    assert captured["agent_id"] == "tutor-x"


# ---------------------------------------------------------------------------
# AC-002 / AC-003 — adapter lifecycle and SIGTERM-driven shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_adapter_starts_then_stops_when_shutdown_event_is_set() -> None:
    """AC-002/AC-003: setting the shutdown event drives ``start → stop``.

    Equivalent to a SIGTERM arriving after boot — the adapter is given a
    chance to ``start()`` and then ``stop()`` when the event fires. We
    drive the event manually here rather than via ``os.kill`` to avoid
    racing pytest's own signal handling.
    """
    adapter = MagicMock()
    adapter.start = AsyncMock()
    adapter.stop = AsyncMock()
    # TASK-NATS-FIX-006: ``_serve_adapter`` now races shutdown_event vs
    # ``adapter.terminal_close_event`` so the latter must be a real
    # ``asyncio.Event`` (MagicMock.wait() is not a coroutine).
    adapter.terminal_close_event = asyncio.Event()

    shutdown_event = asyncio.Event()

    async def _trigger_shutdown_after_start() -> None:
        # Yield once so ``_serve_adapter`` reaches its ``await
        # shutdown_event.wait()`` step before we set the event.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        shutdown_event.set()

    trigger = asyncio.create_task(_trigger_shutdown_after_start())
    try:
        await _serve_adapter(
            adapter,
            agent_id="gcse-tutor",
            nats_url="nats://localhost:4222",
            shutdown_event=shutdown_event,
        )
    finally:
        await trigger

    adapter.start.assert_awaited_once()
    adapter.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_serve_adapter_registers_sigterm_and_sigint_handlers() -> None:
    """AC-002/AC-003: ``SIGTERM`` and ``SIGINT`` both wired to ``shutdown_event``.

    We capture the calls to ``loop.add_signal_handler`` rather than
    sending real signals so this test is hermetic on Linux *and* on
    platforms where ``add_signal_handler`` raises ``NotImplementedError``
    (we still expect both signals to be *attempted*).
    """
    adapter = MagicMock()
    adapter.start = AsyncMock()
    adapter.stop = AsyncMock()
    # TASK-NATS-FIX-006: see comment in the lifecycle test above.
    adapter.terminal_close_event = asyncio.Event()

    shutdown_event = asyncio.Event()
    captured_signals: list[int] = []

    loop = asyncio.get_running_loop()
    original_add = loop.add_signal_handler

    def _capture(sig: int, callback: object, *args: object) -> None:
        captured_signals.append(sig)
        try:
            original_add(sig, callback, *args)
        except NotImplementedError:
            # Match the production ``except NotImplementedError`` branch
            # so this test runs on every platform.
            pass

    loop.add_signal_handler = _capture  # type: ignore[method-assign]
    try:
        async def _trigger() -> None:
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            shutdown_event.set()

        trigger = asyncio.create_task(_trigger())
        try:
            await _serve_adapter(
                adapter,
                agent_id="gcse-tutor",
                nats_url="nats://localhost:4222",
                shutdown_event=shutdown_event,
            )
        finally:
            await trigger
    finally:
        loop.add_signal_handler = original_add  # type: ignore[method-assign]

    assert signal.SIGTERM in captured_signals
    assert signal.SIGINT in captured_signals


@pytest.mark.asyncio
async def test_serve_adapter_exits_1_when_start_raises() -> None:
    """A failure on ``adapter.start()`` exits 1 and still attempts ``stop()``.

    Mirrors specialist-agent's pattern: the operator sees a clear
    ``Failed to start NATSAdapter`` banner, the adapter still gets a
    ``stop()`` to release any partial connection, and the process exits
    non-zero so a supervisor (Docker, systemd) can restart cleanly.
    """
    adapter = MagicMock()
    adapter.start = AsyncMock(side_effect=ConnectionError("NATS unreachable"))
    adapter.stop = AsyncMock()
    # `start` raises before the lifecycle race is reached, but pin a
    # real event anyway so a future change cannot regress this test
    # silently if the race is moved earlier.
    adapter.terminal_close_event = asyncio.Event()

    with pytest.raises(SystemExit) as excinfo:
        await _serve_adapter(
            adapter,
            agent_id="gcse-tutor",
            nats_url="nats://localhost:4222",
            shutdown_event=asyncio.Event(),
        )

    assert excinfo.value.code == 1
    adapter.start.assert_awaited_once()
    adapter.stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# TASK-NATS-FIX-006 / AC-05 — terminal_close_event drives non-zero exit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serve_adapter_exits_1_when_terminal_close_event_fires() -> None:
    """AC-05: terminal-close (nats reconnect budget exhausted) → ``SystemExit(1)``.

    The CLI must propagate a non-zero exit so Docker's restart policy
    (or systemd's ``Restart=`` directive) recovers the container after
    a prolonged broker outage — the demo-blocker scenario the task
    targets.
    """
    adapter = MagicMock()
    adapter.start = AsyncMock()
    adapter.stop = AsyncMock()
    adapter.terminal_close_event = asyncio.Event()

    shutdown_event = asyncio.Event()

    async def _trigger_terminal_close() -> None:
        # Yield twice so ``_serve_adapter`` reaches the
        # ``asyncio.wait({...}, FIRST_COMPLETED)`` race before we fire
        # the terminal-close event.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        adapter.terminal_close_event.set()

    trigger = asyncio.create_task(_trigger_terminal_close())
    try:
        with pytest.raises(SystemExit) as excinfo:
            await _serve_adapter(
                adapter,
                agent_id="gcse-tutor",
                nats_url="nats://localhost:4222",
                shutdown_event=shutdown_event,
            )
    finally:
        await trigger

    assert excinfo.value.code == 1
    adapter.start.assert_awaited_once()
    # ``stop()`` must still run on the terminal-close path so any
    # half-connected state is released before the process exits.
    adapter.stop.assert_awaited_once()
    # The shutdown_event must NOT have been the trigger.
    assert not shutdown_event.is_set()


@pytest.mark.asyncio
async def test_serve_adapter_exits_0_when_shutdown_event_fires_first() -> None:
    """AC-05 negative path: a normal SIGTERM-driven shutdown still exits 0.

    Regression guard for the lifecycle race — when both events are
    pending and ``shutdown_event`` wins, ``terminal_close_event`` stays
    clear and ``_serve_adapter`` returns normally without raising
    ``SystemExit``.
    """
    adapter = MagicMock()
    adapter.start = AsyncMock()
    adapter.stop = AsyncMock()
    adapter.terminal_close_event = asyncio.Event()

    shutdown_event = asyncio.Event()

    async def _trigger_shutdown() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        shutdown_event.set()

    trigger = asyncio.create_task(_trigger_shutdown())
    try:
        # Must NOT raise SystemExit — the function should return normally.
        await _serve_adapter(
            adapter,
            agent_id="gcse-tutor",
            nats_url="nats://localhost:4222",
            shutdown_event=shutdown_event,
        )
    finally:
        await trigger

    adapter.start.assert_awaited_once()
    adapter.stop.assert_awaited_once()
    assert not adapter.terminal_close_event.is_set()
