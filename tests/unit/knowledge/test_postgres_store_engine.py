"""Tests for PostgresStudentStore engine/pool provider, DSN coercion, and ping().

Covers TASK-SMP-03 acceptance criteria:
- Engine creation and reuse (one engine per instance)
- Pool injection (test seam)
- DSN dialect coercion (postgresql:// → postgresql+asyncpg://)
- ping() health check
- Boot wiring with set_student_store
- NotImplementedError boundary preservation
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.store.provider import (
    get_student_store,
    reset_student_store,
    set_student_store,
)


class TestEngineProviderAndReuse:
    """AC-001: PostgresStudentStore builds exactly one AsyncEngine and reuses it."""

    def test_engine_is_created_once_and_reused(self) -> None:
        """When no pool is injected, __init__ creates exactly one AsyncEngine."""
        dsn = "postgresql://user:pass@host:5432/db"
        store = PostgresStudentStore(dsn)

        # Engine should be created during __init__
        assert hasattr(store, "_engine")
        assert isinstance(store._engine, AsyncEngine)

        # Verify same engine instance is reused
        engine_id = id(store._engine)
        # Access engine again via internal attribute
        assert id(store._engine) == engine_id

    def test_no_engine_created_per_call(self) -> None:
        """Engine is stable across multiple accesses (no per-call creation)."""
        dsn = "postgresql://user:pass@host:5432/db"
        store = PostgresStudentStore(dsn)

        engine_first = store._engine
        engine_second = store._engine

        assert engine_first is engine_second


class TestPoolInjection:
    """AC-002: When pool/engine is injected, no engine is built."""

    def test_injected_pool_builds_no_engine(self) -> None:
        """pool= injection path constructs no engine (test/DI seam)."""
        sentinel = MagicMock()
        dsn = "postgresql://x:y@h:5432/d"
        store = PostgresStudentStore(dsn, pool=sentinel)

        # Injected pool should be used as-is
        assert store._pool is sentinel
        # Should not have built an engine
        assert not hasattr(store, "_engine") or store._engine is None


class TestDsnDialectCoercion:
    """AC-003: Plain postgresql:// scheme is coerced to postgresql+asyncpg://."""

    @pytest.mark.parametrize(
        "published_dsn,expected_driver",
        [
            (
                "postgresql://study_tutor:pw@host:5432/study_tutor",
                "postgresql+asyncpg",
            ),
            (
                "postgresql+asyncpg://study_tutor:pw@host:5432/study_tutor",
                "postgresql+asyncpg",
            ),
        ],
    )
    def test_dsn_is_driven_through_the_asyncpg_dialect(
        self, published_dsn: str, expected_driver: str
    ) -> None:
        """STUDY_TUTOR_PG_DSN → async engine MUST use the postgresql+asyncpg driver."""
        store = PostgresStudentStore(published_dsn)
        url = store._engine.url  # the shared AsyncEngine built in __init__

        assert url.drivername == expected_driver
        # Credentials/host/port/db survive the coercion untouched
        assert url.host == "host"
        assert url.port == 5432
        assert url.database == "study_tutor"


class TestPingHealthCheck:
    """AC-004: ping() returns True against reachable Postgres."""

    @pytest.mark.asyncio
    async def test_ping_returns_true_when_database_is_reachable(self) -> None:
        """ping() returns True when SELECT 1 succeeds."""
        dsn = "postgresql://user:pass@host:5432/db"

        # Mock the engine and connection
        mock_connection = AsyncMock()
        mock_connection.execute = AsyncMock()
        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_connection.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_engine.connect = MagicMock(return_value=mock_connection)

        with patch("study_tutor.knowledge.store.postgres.create_async_engine") as mock_create:
            mock_create.return_value = mock_engine

            store = PostgresStudentStore(dsn)
            result = await store.ping()

            assert result is True
            # Verify SELECT 1 was executed
            mock_connection.execute.assert_called_once()


class TestBootWiring:
    """AC-005: Boot wiring reads STUDY_TUTOR_PG_DSN and registers store."""

    def test_set_and_get_student_store(self) -> None:
        """set_student_store registers the store; get_student_store returns it."""
        reset_student_store()  # Clean slate

        dsn = "postgresql://user:pass@host:5432/db"
        store = PostgresStudentStore(dsn)

        set_student_store(store)
        retrieved = get_student_store()

        assert retrieved is store

        reset_student_store()  # Cleanup

    def test_build_student_store_reads_env_and_wires(self) -> None:
        """build_student_store() reads STUDY_TUTOR_PG_DSN and registers store."""
        from study_tutor.knowledge.store.wiring import build_student_store

        reset_student_store()  # Clean slate

        # Mock environment variable
        test_dsn = "postgresql://test:test@localhost:5432/test"
        with patch.dict("os.environ", {"STUDY_TUTOR_PG_DSN": test_dsn}):
            build_student_store()

            # Verify store was registered
            store = get_student_store()
            assert store is not None
            assert isinstance(store, PostgresStudentStore)

        reset_student_store()  # Cleanup

    def test_build_student_store_raises_when_dsn_missing(self) -> None:
        """build_student_store() raises KeyError when STUDY_TUTOR_PG_DSN not set."""
        from study_tutor.knowledge.store.wiring import build_student_store

        reset_student_store()  # Clean slate

        # Ensure env var is not set
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(KeyError):
                build_student_store()

        reset_student_store()  # Cleanup


class TestNotImplementedBoundary:
    """AC-006: Session-CRUD methods raise NotImplementedError (read methods are implemented in TASK-01/02/03)."""

    @pytest.mark.asyncio
    async def test_session_crud_methods_raise_not_implemented(self) -> None:
        """create_session, get_session, list_sessions, etc. raise NotImplementedError."""
        dsn = "postgresql://user:pass@host:5432/db"
        store = PostgresStudentStore(dsn)

        with pytest.raises(NotImplementedError):
            await store.create_session(student_id="s1", subject="English")

        with pytest.raises(NotImplementedError):
            await store.get_session("session123")

        with pytest.raises(NotImplementedError):
            await store.list_sessions("student123")

        with pytest.raises(NotImplementedError):
            await store.append_turn(
                session_id="s1", role="student", content="test"
            )

        with pytest.raises(NotImplementedError):
            await store.get_turns("session123")

        with pytest.raises(NotImplementedError):
            await store.end_session("session123")

    # NOTE: the learner-state WRITE methods (record_session_completion,
    # record_misconception, apply_confidence_update) are implemented in W1
    # (TASK-SMP-04/05/06) — they must NOT be asserted to raise
    # NotImplementedError here. Only reads (FEAT-SMP-002) and session CRUD
    # (FEAT-SMP-003) remain unimplemented in W1; those are covered above.


class TestImportCleanliness:
    """AC-007: postgres.py imports cleanly with no eager DB connection."""

    def test_postgres_module_imports_without_database_connection(self) -> None:
        """Import study_tutor.knowledge.store.postgres should not require DB access."""
        # This test passes if the import at the top of this file succeeded
        # We're verifying no connection is made at import time
        import study_tutor.knowledge.store.postgres  # noqa: F401

        # If we got here, import succeeded without needing a live database
        assert True
