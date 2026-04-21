"""SR-01 stdio-discipline tests.

Spawns the real ``study-tutor serve --role tutor --transport stdio`` process
with stdin closed and asserts that stdout stays completely silent for the
first few seconds. Any byte on stdout before the MCP client sends an
``initialize`` JSON-RPC frame would corrupt the protocol handshake.

Banner/log output (the ``[study-tutor]`` echo in ``cli/main.py`` plus the
``logging.basicConfig(stream=sys.stderr, ...)`` stream) must land on stderr.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
STARTUP_WINDOW_SECONDS = 3.0
TERMINATE_GRACE_SECONDS = 5.0


def _spawn_serve() -> subprocess.Popen[bytes]:
    """Start ``study-tutor serve`` with stdin closed. Caller must clean up."""
    env = os.environ.copy()
    # Keep Phase-0 default; don't let operator-shell env leak a surprise provider.
    env.setdefault("AGENT_MODELS__REASONING_MODEL", "local")
    env["PYTHONUNBUFFERED"] = "1"

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "study_tutor.cli.main",
            "serve",
            "--role",
            "tutor",
            "--transport",
            "stdio",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT),
        env=env,
    )


def _terminate(proc: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    """Terminate the process and return (stdout, stderr) bytes."""
    if proc.poll() is None:
        proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    return stdout, stderr


@pytest.mark.seam
@pytest.mark.integration_contract("SR-01-stdio-discipline")
def test_serve_writes_zero_bytes_to_stdout_during_idle_startup() -> None:
    """SR-01: stdout must stay empty until MCP client initiates the handshake.

    Allows an idle server up to ``STARTUP_WINDOW_SECONDS`` of warm-up. If any
    byte lands on stdout in that window, a log line / banner / print()
    statement has leaked into the JSON-RPC channel.
    """
    proc = _spawn_serve()
    try:
        # The FastMCP stdio loop may EOF-exit cleanly once stdin is closed;
        # that's fine — the SR-01 contract is about stdout silence within
        # the startup window, not liveness.
        time.sleep(STARTUP_WINDOW_SECONDS)
    finally:
        stdout, stderr = _terminate(proc)

    rc = proc.returncode
    assert rc in (0, -15, None), (
        f"serve exited with unexpected rc={rc}. stderr-tail={stderr[-400:]!r}"
    )
    assert stdout == b"", (
        f"SR-01 violation: {len(stdout)} bytes on stdout during startup.\n"
        f"stdout={stdout!r}\nstderr-tail={stderr[-400:]!r}"
    )


@pytest.mark.seam
@pytest.mark.integration_contract("SR-01-stdio-discipline")
def test_serve_emits_banner_on_stderr() -> None:
    """Diagnostic banner/log output must travel on stderr, not stdout.

    Pairs with the stdout-silence test: *some* output is expected (banner +
    ``MCP server '<role>-agent' ready`` info log); it just has to land on
    the right stream.
    """
    proc = _spawn_serve()
    try:
        time.sleep(STARTUP_WINDOW_SECONDS)
    finally:
        stdout, stderr = _terminate(proc)

    assert stdout == b"", f"stdout must stay silent; got {stdout!r}"
    assert b"study-tutor" in stderr.lower() or b"[study-tutor]" in stderr, (
        f"Expected banner on stderr; got {stderr!r}"
    )
