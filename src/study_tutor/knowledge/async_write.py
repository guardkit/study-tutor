"""Shared async fire-and-forget Graphiti write helper (TASK-GSM-004).

This module is the **single** Graphiti write surface used by all flush points
in study-tutor (F1 misconception via Coach AsyncSubAgent, F2 confidence-delta
via Tutor handler, F3 session-end episode via Tutor handler) per **DDR-002**.

Load-bearing properties (per ADR-ARCH-019 + CC-13 + ASSUM-007):

- **Fire-and-forget**: every write is dispatched through ``asyncio.create_task``;
  the caller-facing ``schedule_write`` never awaits the eventual write to
  Graphiti. The handler/Coach budget is therefore independent of FalkorDB
  latency.
- **Log-only failure**: a failed call to the underlying ``add_episode`` emits a
  structured log line and never raises to the caller (writes are best-effort).
- **Process-shutdown grace**: in-flight tasks are awaited up to
  ``GRAPHITI_SHUTDOWN_GRACE_SEC`` (default 30s, env-var configurable) on
  graceful shutdown; tasks that don't complete in time are logged as abandoned.
- **Input sanitisation**: misconception text passes through
  :func:`sanitise_misconception_text`, which strips control characters,
  truncates to 500 chars, and rejects coarse prompt-injection patterns
  (defence-in-depth against attacks on Graphiti's extraction LLM).
- **Auditable single call site**: the lone underlying-write call in the whole
  codebase lives in :meth:`GraphitiWriteHelper._perform_write`. CC-13
  conformance asserts this by AST/grep audit; protect it.

Cross-references:
    - phase-1-scope.md §FEAT-PH1-001 (architectural shape)
    - DDR-002 (Coach AsyncSubAgent owns Graphiti writes)
    - ADR-ARCH-019 (async write-back at every flush point)
    - ASSUM-007 (shutdown grace ≤ 30s)
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal

from study_tutor.knowledge.episodes import EpisodeBase
from study_tutor.knowledge.student_model import (
    FLEET_GROUP_ID,
    STUDENT_GROUP_PREFIX,
    SUBJECT_GROUP_PREFIX,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Environment variable name for overriding the default shutdown grace period.
GRAPHITI_SHUTDOWN_GRACE_ENV_VAR: str = "GRAPHITI_SHUTDOWN_GRACE_SEC"

#: Default shutdown grace period (seconds). Per ASSUM-007.
DEFAULT_SHUTDOWN_GRACE_SEC: int = 30

#: Maximum length (characters) of sanitised misconception text.
MAX_MISCONCEPTION_TEXT_LENGTH: int = 500

#: Suffix appended to truncated misconception text.
TRUNCATION_SUFFIX: str = "[…truncated]"

#: Allowed flush-id literals. Kept as a frozenset for fast membership checks.
FlushId = Literal["F1", "F2", "F3", "SEED"]
_VALID_FLUSH_IDS: frozenset[str] = frozenset({"F1", "F2", "F3", "SEED"})


# ---------------------------------------------------------------------------
# Sanitisation primitives
# ---------------------------------------------------------------------------

# Coarse prompt-injection patterns. Intentionally conservative; the goal is
# defence-in-depth, not perfect classification. False positives are acceptable
# (we drop the write and log it) — false negatives are what we cannot afford.
_INJECTION_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(ignore previous|system:|<\|.*\|>|\[INST\])"
)

# ASCII control characters except tab (\t = 0x09) and newline (\n = 0x0A).
# Stripping these neutralises a class of LLM-prompt smuggling tricks while
# preserving legitimate formatting whitespace.
_CONTROL_CHARS_PATTERN: re.Pattern[str] = re.compile(
    r"[\x00-\x08\x0B-\x0C\x0E-\x1F]"
)


def sanitise_misconception_text(text: str) -> str:
    """Sanitise free-text misconception content before scheduling a write.

    Order of operations:

    1. Strip ASCII control characters (except ``\\n`` and ``\\t``).
    2. Reject any text matching a coarse prompt-injection pattern by raising
       :class:`ValueError` (the caller in :meth:`GraphitiWriteHelper.schedule_write`
       converts this into a ``graphiti_write_dropped_injection`` log line).
    3. Truncate to :data:`MAX_MISCONCEPTION_TEXT_LENGTH` characters with the
       :data:`TRUNCATION_SUFFIX` appended (the resulting string never exceeds
       :data:`MAX_MISCONCEPTION_TEXT_LENGTH`).

    Args:
        text: The raw misconception text observed by the Coach.

    Returns:
        The sanitised text, length-capped at
        :data:`MAX_MISCONCEPTION_TEXT_LENGTH` characters.

    Raises:
        ValueError: If the text matches a coarse prompt-injection pattern.
            Callers convert this to a ``graphiti_write_dropped_injection`` log
            line; never propagated to user-facing code paths.
    """
    cleaned = _CONTROL_CHARS_PATTERN.sub("", text)
    if _INJECTION_PATTERN.search(cleaned):
        raise ValueError("misconception text matches a coarse injection pattern")
    if len(cleaned) > MAX_MISCONCEPTION_TEXT_LENGTH:
        keep = MAX_MISCONCEPTION_TEXT_LENGTH - len(TRUNCATION_SUFFIX)
        # Defensive: if someone sets a perversely long suffix > cap, just
        # return the suffix itself capped.
        if keep < 0:
            return TRUNCATION_SUFFIX[:MAX_MISCONCEPTION_TEXT_LENGTH]
        cleaned = cleaned[:keep] + TRUNCATION_SUFFIX
    return cleaned


# ---------------------------------------------------------------------------
# Validation primitives
# ---------------------------------------------------------------------------


def _validate_group_ids(group_ids: list[str]) -> None:
    """Validate the group-id discipline (per TASK-GSM-001).

    Each id must be either ``student:<id>``, ``subject:<slug>``, or exactly the
    fleet-wide constant ``fleet:appmilla``.
    """
    if not group_ids:
        raise ValueError("group_ids must be a non-empty list")
    for gid in group_ids:
        if (
            not gid.startswith(STUDENT_GROUP_PREFIX)
            and not gid.startswith(SUBJECT_GROUP_PREFIX)
            and gid != FLEET_GROUP_ID
        ):
            raise ValueError(
                f"group_id {gid!r} does not match the prefix discipline "
                f"(student:/subject:/fleet:appmilla)"
            )


def _add_episode_kwargs(
    *,
    name: str,
    episode_body: str,
    flush_id: str,
    group_id: str | None,
) -> dict[str, Any]:
    """Build the kwargs dict for graphiti-core 0.29's ``add_episode``.

    Hoisted out so :meth:`GraphitiWriteHelper._perform_write` stays
    auditable (CC-13: a single ``add_episode`` call site in src/)
    and so tests can assert on the call shape without instantiating a
    helper. ``flush_id`` rides in ``source_description`` rather than as
    a first-class parameter because graphiti-core has no flush-id slot;
    keeping it greppable here preserves the audit-trail property the
    structured logs already rely on.
    """
    from graphiti_core.nodes import EpisodeType

    return {
        "name": name,
        "episode_body": episode_body,
        "source": EpisodeType.json,
        "source_description": f"flush:{flush_id}:{name}",
        "reference_time": datetime.now(timezone.utc),
        "group_id": group_id,
    }


def _resolve_default_grace_sec(default: int = DEFAULT_SHUTDOWN_GRACE_SEC) -> int:
    """Resolve the shutdown-grace-sec default from the environment.

    Returns ``default`` if the env var is unset, blank, non-integer, or
    non-positive — invalid configurations should never silently produce a
    zero-second grace.
    """
    raw = os.environ.get(GRAPHITI_SHUTDOWN_GRACE_ENV_VAR)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except (ValueError, TypeError):
        logger.warning(
            "graphiti shutdown grace env var is not an int; using default",
            extra={
                "event": "graphiti_shutdown_grace_invalid",
                "raw_value": raw,
                "default": default,
            },
        )
        return default
    if value <= 0:
        return default
    return value


# ---------------------------------------------------------------------------
# Client type
# ---------------------------------------------------------------------------

# We deliberately avoid declaring a Protocol with the underlying-write method
# name so the CC-13 single-call-site audit (``git grep -nE 'add_episode\s*\('
# src/``) returns exactly one match. The client is duck-typed at the call site.
GraphitiClientLike = Any


# ---------------------------------------------------------------------------
# The helper itself
# ---------------------------------------------------------------------------


class GraphitiWriteHelper:
    """Shared async fire-and-forget write surface for Graphiti.

    All four flush points (F1, F2, F3, SEED) dispatch through one instance of
    this class. The single :meth:`_perform_write` method is the **only** call
    site of the underlying graphiti-core write API anywhere in the codebase
    (CC-13 conformance: enforced by AST/grep audit).
    """

    def __init__(
        self,
        client: GraphitiClientLike | None,
        shutdown_grace_sec: int | None = None,
    ) -> None:
        """Construct a helper around an optional Graphiti client.

        Args:
            client: A graphiti-core-compatible client exposing an awaitable
                ``add_episode``. May be ``None`` — in which case
                :meth:`schedule_write` becomes a graceful no-op (callers never
                need to special-case the "graphiti unavailable" path).
            shutdown_grace_sec: Process-shutdown grace period in seconds. If
                ``None``, the default is read from the environment variable
                ``GRAPHITI_SHUTDOWN_GRACE_SEC`` (falling back to
                :data:`DEFAULT_SHUTDOWN_GRACE_SEC`). An explicitly-passed value
                always wins over the env var.
        """
        self._client = client
        if shutdown_grace_sec is None:
            shutdown_grace_sec = _resolve_default_grace_sec()
        self._shutdown_grace_sec = shutdown_grace_sec
        # Track in-flight tasks alongside their dispatch metadata so drain()
        # can produce per-task abandoned log lines without inspecting coroutine
        # internals.
        self._in_flight: dict[asyncio.Task[None], dict[str, Any]] = {}

    @property
    def shutdown_grace_sec(self) -> int:
        """Effective shutdown grace period (seconds)."""
        return self._shutdown_grace_sec

    @property
    def in_flight_count(self) -> int:
        """Number of currently-tracked in-flight write tasks."""
        return len(self._in_flight)

    # ------------------------------------------------------------------
    # Caller-facing dispatcher
    # ------------------------------------------------------------------

    def schedule_write(
        self,
        group_ids: list[str],
        episode: EpisodeBase,
        flush_id: FlushId,
    ) -> asyncio.Task[None] | None:
        """Schedule a fire-and-forget Graphiti write.

        The dispatcher returns a task (or ``None``) **synchronously** —
        critically, it never ``await``\\ s the eventual ``add_episode`` call.
        Per ADR-ARCH-019 the caller-facing path must return in well under the
        2s handler budget regardless of how slow Graphiti is on the wire.

        Args:
            group_ids: Non-empty list of validated group ids.
            episode: A :class:`EpisodeBase` subclass instance. Misconception
                episodes have their ``misconception_text`` sanitised before
                dispatch.
            flush_id: One of ``"F1"`` / ``"F2"`` / ``"F3"`` / ``"SEED"``.

        Returns:
            The :class:`asyncio.Task` wrapping the in-flight write, or ``None``
            if the helper has no client (graceful no-op) or input validation
            dropped the write.
        """
        episode_kind = getattr(episode, "episode_kind", "unknown")

        # Graceful no-op when graphiti-core is unavailable. Per the CC-13/
        # DDR-002 contract callers must not have to special-case this.
        if self._client is None:
            return None

        # Cheap synchronous validation ahead of asyncio.create_task. Each
        # rejection path emits a structured log and returns None so the
        # caller can simply ignore the return value.
        if flush_id not in _VALID_FLUSH_IDS:
            self._log_dropped_invalid(
                reason=f"flush_id {flush_id!r} not one of {sorted(_VALID_FLUSH_IDS)}",
                flush_id=str(flush_id),
                episode_kind=episode_kind,
                group_ids=list(group_ids) if group_ids else [],
                error_class="ValueError",
            )
            return None

        try:
            _validate_group_ids(list(group_ids))
        except ValueError as exc:
            self._log_dropped_invalid(
                reason=str(exc),
                flush_id=flush_id,
                episode_kind=episode_kind,
                group_ids=list(group_ids) if group_ids else [],
                error_class=exc.__class__.__name__,
            )
            return None

        # Misconception text is the only free-form attacker-controlled field
        # that flows into the extraction LLM. Sanitise it before scheduling.
        if episode_kind == "misconception_observed":
            raw_text = getattr(episode, "misconception_text", "")
            try:
                sanitised = sanitise_misconception_text(raw_text)
            except ValueError as exc:
                logger.warning(
                    "graphiti write dropped (prompt-injection pattern detected)",
                    extra={
                        "event": "graphiti_write_dropped_injection",
                        "flush_id": flush_id,
                        "episode_kind": episode_kind,
                        "group_ids": list(group_ids),
                        "error_class": exc.__class__.__name__,
                    },
                )
                return None
            if sanitised != raw_text:
                # model_copy on Pydantic v2 produces a validated shallow copy.
                episode = episode.model_copy(
                    update={"misconception_text": sanitised}
                )

        # Audit / observability log line: the dispatcher commits to scheduling.
        groups_snapshot = list(group_ids)
        logger.info(
            "graphiti write scheduled",
            extra={
                "event": "graphiti_write_scheduled",
                "flush_id": flush_id,
                "episode_kind": episode_kind,
                "group_ids": groups_snapshot,
            },
        )

        task: asyncio.Task[None] = asyncio.create_task(
            self._perform_write(
                group_ids=groups_snapshot,
                episode=episode,
                episode_kind=episode_kind,
                flush_id=flush_id,
            )
        )
        self._in_flight[task] = {
            "flush_id": flush_id,
            "episode_kind": episode_kind,
            "group_ids": groups_snapshot,
        }
        task.add_done_callback(self._on_task_done)
        return task

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_task_done(self, task: asyncio.Task[None]) -> None:
        """Done-callback: drop completed tasks from the in-flight registry."""
        self._in_flight.pop(task, None)

    async def _perform_write(
        self,
        *,
        group_ids: list[str],
        episode: EpisodeBase,
        episode_kind: str,
        flush_id: str,
    ) -> None:
        """Internal write coroutine. Catches BaseException; never raises.

        This is the **only** place ``add_episode`` is called anywhere in
        ``src/`` (CC-13). If you find yourself wanting to add a second call
        site, route it through this method instead.
        """
        start = time.monotonic()
        try:
            body = episode.to_graphiti_episode_body()
            assert self._client is not None  # narrowed by schedule_write
            # graphiti-core 0.29 takes a single ``group_id``; Phase 1 only
            # ever writes one partition per call site (per-student or
            # subject-scoped), so the first entry is canonical. The full
            # validated list is preserved in the structured log below for
            # auditability. ``flush_id`` is folded into ``source_description``
            # since the API has no first-class flush-id parameter — that
            # keeps CC-13 audit logs trivially greppable.
            primary_group_id = group_ids[0] if group_ids else None
            kwargs = _add_episode_kwargs(
                name=episode_kind,
                episode_body=body,
                flush_id=flush_id,
                group_id=primary_group_id,
            )
            # === The single CC-13-protected call site ===
            await self._client.add_episode(**kwargs)
        except BaseException as exc:  # noqa: BLE001 -- log-only failure required by ADR-ARCH-019
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "graphiti write failed",
                extra={
                    "event": "graphiti_write_failed",
                    "flush_id": flush_id,
                    "episode_kind": episode_kind,
                    "group_ids": group_ids,
                    "error_class": exc.__class__.__name__,
                    "latency_ms": latency_ms,
                },
            )
            return None
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "graphiti write succeeded",
            extra={
                "event": "graphiti_write_succeeded",
                "flush_id": flush_id,
                "episode_kind": episode_kind,
                "group_ids": group_ids,
                "latency_ms": latency_ms,
            },
        )
        return None

    # ------------------------------------------------------------------
    # Shutdown helper
    # ------------------------------------------------------------------

    async def drain(self, timeout_sec: int | None = None) -> tuple[int, int]:
        """Await all in-flight writes up to a budget; return per-task tally.

        Args:
            timeout_sec: Optional explicit budget (seconds). Falls back to
                :attr:`shutdown_grace_sec`.

        Returns:
            A 2-tuple ``(succeeded, abandoned)``:

            - ``succeeded`` — number of in-flight tasks that completed within
              the budget (regardless of whether the underlying write logged
              ``graphiti_write_failed`` — the dispatch finished).
            - ``abandoned`` — number of tasks still pending at timeout. Each
              gets a ``graphiti_write_abandoned_at_shutdown`` log line and is
              cancelled.
        """
        budget = (
            timeout_sec if timeout_sec is not None else self._shutdown_grace_sec
        )
        snapshot: dict[asyncio.Task[None], dict[str, Any]] = dict(self._in_flight)
        if not snapshot:
            return (0, 0)

        done, pending = await asyncio.wait(
            list(snapshot.keys()), timeout=float(budget)
        )
        succeeded = len(done)
        abandoned = len(pending)
        for task in pending:
            meta = snapshot.get(task, {})
            logger.warning(
                "graphiti write abandoned at shutdown",
                extra={
                    "event": "graphiti_write_abandoned_at_shutdown",
                    "flush_id": meta.get("flush_id", "unknown"),
                    "episode_kind": meta.get("episode_kind", "unknown"),
                    "group_ids": meta.get("group_ids", []),
                },
            )
            task.cancel()
        return (succeeded, abandoned)

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------

    def _log_dropped_invalid(
        self,
        *,
        reason: str,
        flush_id: str,
        episode_kind: str,
        group_ids: list[str],
        error_class: str,
    ) -> None:
        """Emit a structured ``graphiti_write_dropped_invalid`` warning."""
        logger.warning(
            "graphiti write dropped (invalid input): %s",
            reason,
            extra={
                "event": "graphiti_write_dropped_invalid",
                "flush_id": flush_id,
                "episode_kind": episode_kind,
                "group_ids": group_ids,
                "error_class": error_class,
            },
        )


__all__ = [
    "DEFAULT_SHUTDOWN_GRACE_SEC",
    "FlushId",
    "GRAPHITI_SHUTDOWN_GRACE_ENV_VAR",
    "GraphitiWriteHelper",
    "MAX_MISCONCEPTION_TEXT_LENGTH",
    "TRUNCATION_SUFFIX",
    "sanitise_misconception_text",
]
