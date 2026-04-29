"""Graphiti client wrapper with lazy import and graceful degradation.

FEAT-1773 / TASK-GSM-003 — owns the lifecycle of a ``graphiti-core`` client
talking to FalkorDB on the Synology NAS. The module has two load-bearing
properties:

1. **Lazy import** (LES1 §3 + Group D ``@module-load`` scenario in the
   feature spec) — the module loads successfully even when ``graphiti-core``
   is not installed. ``import graphiti_core`` happens *inside* the
   ``_load_graphiti_core`` helper, never at module top level. A top-level
   ``try: import graphiti_core`` would still execute at import time and
   could surface import-side-effect failures into every caller that just
   wanted to introspect ``GraphitiConnectionConfig``.

2. **Graceful degradation** — when the wrapped client cannot be constructed
   (library absent, FalkorDB unreachable, healthcheck times out, config
   rejected), :func:`get_client` returns ``None`` and emits a structured
   warning log with ``event=graphiti_client_degraded``. Callers MUST handle
   the ``None`` case without raising. This is the same shape used by the
   sibling ``specialist-agent`` repo's
   ``specialist_agent/tools/graphiti_client.py`` lazy-import pattern, which
   is the canonical reference for this module.

Scope (per task):

- :class:`GraphitiConnectionConfig` — Pydantic v2 config dataclass for
  FalkorDB host/port/database, LLM provider/model, embedder URL, and
  ``timeout_seconds`` (default ``5.0`` per ASSUM-005).
- :class:`GraphitiClient` — thin wrapper exposing only ``healthcheck()``,
  ``close()``, and the ``client_or_none`` property. Domain operations such
  as ``add_episode`` / ``search_*`` are deliberately **out of scope** —
  TASK-GSM-004 owns the write path and TASK-GSM-005 owns the query helpers.
- :func:`get_client` — async factory implementing the four-step degradation
  path: import → construct → healthcheck → return wrapper.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# Structured-log event identifiers. Kept as module constants so call sites
# (and downstream log-grepping) reference a single source of truth.
EVENT_DEGRADED = "graphiti_client_degraded"
EVENT_READY = "graphiti_client_ready"
EVENT_CLOSE_ERROR = "graphiti_client_close_error"


class GraphitiConnectionConfig(BaseModel):
    """Pydantic v2 config for the Graphiti/FalkorDB client.

    Strict (``extra="forbid"``) so that typos in caller code surface as
    ``ValidationError`` rather than silently dropped fields. Defaults for
    LLM provider/model/timeout encode the ASSUM-005 contract; callers may
    override but the canonical Phase-1 values live here.

    Fields:
        falkor_host: FalkorDB hostname (Synology NAS IP or DNS name).
        falkor_port: FalkorDB Redis-protocol port. Must be ``> 0``.
        database: FalkorDB graph name.
        llm_provider: Backing LLM provider for graphiti-core (default
            ``"gemini"``).
        llm_model: LLM model identifier (default ``"gemini-2.5-pro"``).
        embedder_url: HTTP URL of the local embedder service (GB10:8001).
        timeout_seconds: Healthcheck timeout in seconds. Default ``5.0``
            per ASSUM-005. Must be strictly positive.
    """

    model_config = ConfigDict(extra="forbid")

    falkor_host: str = Field(min_length=1)
    falkor_port: int = Field(gt=0)
    database: str = Field(min_length=1)
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-pro"
    embedder_url: str = Field(min_length=1)
    timeout_seconds: float = Field(default=5.0, gt=0)


def _log_degraded(
    error_class: str,
    host: str,
    *,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    """Emit the canonical ``graphiti_client_degraded`` warning record.

    All degradation paths in this module funnel through this helper so that
    log-line shape (``event``, ``error_class``, ``falkor_host``,
    ``degraded``, optional ``latency_ms``) stays uniform — that uniformity
    is what makes the Group-D ``@module-load`` scenario observable in
    production logs.
    """
    extra: dict[str, Any] = {
        "event": EVENT_DEGRADED,
        "error_class": error_class,
        "falkor_host": host,
        "degraded": True,
    }
    if latency_ms is not None:
        extra["latency_ms"] = latency_ms
    if error_message is not None:
        extra["error_message"] = error_message
    logger.warning("graphiti client degraded: %s", error_class, extra=extra)


def _load_graphiti_core() -> tuple[Any, Any]:
    """Lazy-import ``graphiti-core`` symbols at call time.

    Pulled out as a named helper so unit tests can patch it cleanly without
    monkey-patching ``builtins.__import__``. Returning a tuple keeps the
    factory's call site flat. A real call returns
    ``(Graphiti, FalkorDriver)``; tests may inject fakes with the same
    constructor signature.

    Raises:
        ImportError: When ``graphiti-core`` is not installed in the active
            interpreter, or when its falkordb driver path is unavailable.
    """
    from graphiti_core import Graphiti  # type: ignore[import-not-found]
    from graphiti_core.driver.falkordb_driver import (  # type: ignore[import-not-found]
        FalkorDriver,
    )

    return Graphiti, FalkorDriver


class GraphitiClient:
    """Thin lifecycle wrapper around a ``graphiti-core`` client.

    Intentionally narrow: this object owns construction, healthcheck, and
    close — nothing else. ``add_episode`` and search helpers are layered on
    top of ``client_or_none`` by sibling modules (TASK-GSM-004 /
    TASK-GSM-005) so the boundary between "the wrapper" and "the domain
    operations" stays auditable.
    """

    def __init__(
        self,
        inner: Any | None,
        config: GraphitiConnectionConfig,
    ) -> None:
        self._inner = inner
        self._config = config

    @property
    def client_or_none(self) -> Any | None:
        """The underlying ``graphiti-core`` client, or ``None`` after close."""
        return self._inner

    async def healthcheck(self) -> bool:
        """Cheap liveness probe against the wrapped driver.

        Honours :attr:`GraphitiConnectionConfig.timeout_seconds` (5s default
        per ASSUM-005) via :func:`asyncio.wait_for`. Never raises — any
        timeout, driver exception, or missing-driver state resolves to
        ``False`` plus a structured ``graphiti_client_degraded`` warning.
        """
        if self._inner is None:
            return False

        started = time.monotonic()
        try:
            await asyncio.wait_for(
                self._ping(),
                timeout=self._config.timeout_seconds,
            )
            return True
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _log_degraded(
                "TimeoutError",
                self._config.falkor_host,
                latency_ms=elapsed_ms,
                error_message=(f"healthcheck exceeded {self._config.timeout_seconds}s"),
            )
            return False
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _log_degraded(
                exc.__class__.__name__,
                self._config.falkor_host,
                latency_ms=elapsed_ms,
                error_message=str(exc),
            )
            return False

    async def _ping(self) -> None:
        """Run ``RETURN 1`` via the wrapped driver.

        graphiti-core exposes its underlying driver on the ``driver``
        attribute. Different driver implementations name the query method
        differently (``execute_query`` on the falkordb driver, ``query`` on
        some others) — we probe both rather than hard-coding so that a
        graphiti-core minor-version bump that renames the method doesn't
        silently turn every healthcheck into a hard failure.
        """
        driver = getattr(self._inner, "driver", None)
        if driver is None:
            raise RuntimeError(
                "graphiti client missing 'driver' attribute; cannot healthcheck"
            )

        for attr in ("execute_query", "query"):
            fn = getattr(driver, attr, None)
            if fn is None:
                continue
            result = fn("RETURN 1")
            if asyncio.iscoroutine(result):
                await result
            return

        raise RuntimeError(
            "graphiti driver exposes neither 'execute_query' nor 'query'"
        )

    async def close(self) -> None:
        """Idempotent close. Safe to call when the wrapper is already empty.

        After the first call ``client_or_none`` returns ``None`` and any
        further ``close()`` is a no-op — that property is what lets
        :func:`get_client`'s degradation path call ``close()`` on a
        partially-constructed wrapper without juggling try/finally.
        """
        if self._inner is None:
            return

        inner = self._inner
        # Zero state before awaiting so re-entrant or concurrent callers
        # can't race two close() awaits onto the same underlying driver.
        self._inner = None

        close_fn = getattr(inner, "close", None)
        if close_fn is None:
            return

        try:
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            logger.warning(
                "graphiti close raised: %s",
                exc.__class__.__name__,
                extra={
                    "event": EVENT_CLOSE_ERROR,
                    "error_class": exc.__class__.__name__,
                    "falkor_host": self._config.falkor_host,
                    "error_message": str(exc),
                },
            )


async def get_client(
    config: GraphitiConnectionConfig,
) -> GraphitiClient | None:
    """Construct a :class:`GraphitiClient` or return ``None`` on any failure.

    Degradation gates (each logs ``graphiti_client_degraded`` and returns
    ``None`` — no exception escapes):

    1. ``graphiti-core`` import fails (library not installed / broken).
    2. FalkorDB driver / Graphiti construction raises (host unreachable,
       auth rejected, invalid database name, etc.).
    3. :meth:`GraphitiClient.healthcheck` returns ``False`` (driver
       constructed but not actually serving queries within
       ``timeout_seconds``).

    On success the wrapper is returned and an ``graphiti_client_ready``
    info-level log records latency.
    """
    started = time.monotonic()

    try:
        graphiti_cls, driver_cls = _load_graphiti_core()
    except ImportError as exc:
        _log_degraded(
            "ImportError",
            config.falkor_host,
            error_message=str(exc),
        )
        return None
    except Exception as exc:  # noqa: BLE001 — graphiti-core import side effects
        _log_degraded(
            exc.__class__.__name__,
            config.falkor_host,
            error_message=str(exc),
        )
        return None

    try:
        driver = driver_cls(
            host=config.falkor_host,
            port=config.falkor_port,
            database=config.database,
        )
        inner = graphiti_cls(graph_driver=driver)
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        _log_degraded(
            exc.__class__.__name__,
            config.falkor_host,
            error_message=str(exc),
        )
        return None

    wrapper = GraphitiClient(inner=inner, config=config)

    healthy = await wrapper.healthcheck()
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if not healthy:
        # Healthcheck already logged the underlying cause; emit a second
        # ``HealthcheckFailed`` line so log readers can grep for the
        # gate-level outcome without having to correlate timestamps.
        _log_degraded(
            "HealthcheckFailed",
            config.falkor_host,
            latency_ms=elapsed_ms,
        )
        await wrapper.close()
        return None

    logger.info(
        "graphiti client ready in %dms",
        elapsed_ms,
        extra={
            "event": EVENT_READY,
            "falkor_host": config.falkor_host,
            "degraded": False,
            "latency_ms": elapsed_ms,
        },
    )
    return wrapper


__all__ = [
    "EVENT_CLOSE_ERROR",
    "EVENT_DEGRADED",
    "EVENT_READY",
    "GraphitiClient",
    "GraphitiConnectionConfig",
    "get_client",
]
