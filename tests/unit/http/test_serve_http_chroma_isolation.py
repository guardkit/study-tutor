"""Regression pin for the T2 store-isolation leak (known-issues, 2026-08-07).

The leak: ``build_rag_providers`` defaults its persist dir to the RELATIVE
path ``data/chroma`` when ``CHROMA_PERSIST_DIR`` is unset. Once the ``[rag]``
extra makes ``chromadb`` importable, every serve boot reached by the hermetic
suite — the subprocess boots in ``test_serve_http.py`` (keycloak/auth-mode
fail-fast quartet) and ``test_stdio_discipline.py``, plus the in-process
``CliRunner().invoke(cli, ["serve"])`` in
``test_serve_student_store_wiring.py`` — opened the checkout's REAL baked
store and appended one row to chroma's internal ``acquire_write`` bookkeeping
table per fresh-process open (+7 rows per full hermetic run, measured
2026-08-07 against a scratch copy; content untouched, bytes changed).

The fix is the root ``conftest.py`` guard: an unset ``CHROMA_PERSIST_DIR`` is
pointed at a guaranteed-nonexistent path before any test runs, so the wiring
takes its documented ``rag_disabled reason=persist_dir_missing`` graceful
branch instead of opening a store. Subprocess-spawning tests inherit the
guard because they build their env from ``os.environ.copy()``.

Pins here (copy-based per the ledgered exit — the store under test is a
scratch store in ``tmp_path``, NEVER the real ``data/chroma``):

1. The guard is present for the session (cheap, runs without chromadb).
2. A serve-http boot that demonstrably REACHES the RAG wiring leaves a store
   sitting at ``<cwd>/data/chroma`` untouched — ``acquire_write`` row count
   stable. Remove the conftest guard and this fails with a +1 row delta.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _acquire_write_rows(db: Path) -> int:
    """Count acquire_write rows via sqlite ``immutable=1`` (write-free read)."""
    con = sqlite3.connect(f"file:{db}?immutable=1", uri=True)
    try:
        return con.execute("select count(*) from acquire_write").fetchone()[0]
    finally:
        con.close()


def test_chroma_persist_dir_guard_is_active() -> None:
    """The root-conftest guard must hold for the whole session.

    An unset ``CHROMA_PERSIST_DIR`` is the exact leak vector (relative
    ``data/chroma`` default), so the hermetic suite must never run with it
    empty. When the operator exported their own value we respect it and
    skip — the guard only backfills absent config.
    """
    value = os.environ.get("CHROMA_PERSIST_DIR")
    assert value, (
        "CHROMA_PERSIST_DIR is unset under pytest — the root conftest.py "
        "chroma guard is missing; serve boots will open the real data/chroma "
        "store (T2 store-isolation leak, known-issues 2026-08-07)"
    )
    if "chroma-test-guard-" not in value:
        pytest.skip("operator exported an explicit CHROMA_PERSIST_DIR")
    assert not Path(value).exists(), (
        "the conftest guard path must not exist — an existing dir would be "
        "opened by build_rag_providers"
    )


def test_serve_http_boot_leaves_cwd_chroma_store_untouched(
    tmp_path: Path,
) -> None:
    """acquire_write row-count stability across a serve-http boot (the pin).

    Builds a scratch chroma store at ``<tmp cwd>/data/chroma`` — the exact
    relative location the unguarded default would open — then boots
    ``serve-http`` with that cwd using the same env-inheritance shape as the
    leaking tests (``os.environ.copy()``). The boot must reach the RAG
    wiring (proven via its ``event=rag_wiring_resolved`` log line) and the
    store's ``acquire_write`` count must not move.
    """
    chromadb = pytest.importorskip(
        "chromadb", reason="[rag] extra not installed — leak vector absent"
    )

    boot_cwd = tmp_path / "cwd"
    store_dir = boot_cwd / "data" / "chroma"
    store_dir.mkdir(parents=True)
    # ``load_role`` resolves ``roles/`` against cwd (SR-02), so give the
    # scratch cwd a read-only view of the real manifests. The symlink adds
    # no write path back into the repo — the boot only reads role.yaml and
    # the prompt files.
    (boot_cwd / "roles").symlink_to(REPO_ROOT / "roles")
    # A bare persistent store is enough: the leak's row growth happens on
    # client OPEN, before any collection is touched.
    chromadb.PersistentClient(path=str(store_dir))
    db = store_dir / "chroma.sqlite3"
    assert db.exists()
    rows_before = _acquire_write_rows(db)

    env = os.environ.copy()  # same inheritance shape as the leaking tests
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    # Lazy DSN gets past the fail-fast check without a connection; the
    # unknown auth mode then exits 1 AFTER the RAG wiring has run — the
    # cheapest boot that reaches build_rag_providers.
    env["STUDY_TUTOR_PG_DSN"] = "postgresql://localhost/testdb"
    env["STUDY_TUTOR_HTTP_TOKENS"] = '{"test": "test"}'
    env["STUDY_TUTOR_AUTH_MODE"] = "unknown_mode"

    proc = subprocess.Popen(
        [sys.executable, "-m", "study_tutor.cli.main", "serve-http"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(boot_cwd),
    )
    try:
        returncode = proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    stderr = proc.stderr.read().decode() if proc.stderr else ""

    assert returncode != 0, "unknown auth mode must fail the boot"
    assert "event=rag_wiring_resolved" in stderr, (
        "boot never reached the RAG wiring — this pin proves nothing unless "
        f"build_rag_providers ran. stderr:\n{stderr}"
    )

    rows_after = _acquire_write_rows(db)
    assert rows_after == rows_before, (
        f"acquire_write grew {rows_before} -> {rows_after}: the serve boot "
        "opened <cwd>/data/chroma — the CHROMA_PERSIST_DIR conftest guard "
        "has regressed (T2 store-isolation leak, known-issues 2026-08-07)"
    )
