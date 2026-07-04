"""Student-model write helpers (TASK-GSM-005 / TASK-SMP2-06).

F3 write owner and TopicConfidence update path for FEAT-1773. The Graphiti
READ surface (get_student_state, get_topic_recommendations) was removed in
TASK-SMP2-06 and migrated to study_tutor.knowledge.store (Postgres). This
module now contains only the WRITE path, which will be removed in FEAT-SMP-004.

Load-bearing properties:

- **F3 fire-and-forget** (DDR-002 + ADR-ARCH-019):
  :func:`record_session_completion` dispatches via
  :meth:`GraphitiWriteHelper.schedule_write` with ``flush_id="F3"`` and
  returns within ~50ms regardless of underlying ``add_episode`` latency.
- **Graceful degradation**: every helper accepts ``client=None`` and
  produces an empty/safe result without raising.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.episodes import (
    SessionCompletedEpisode,
    TopicConfidenceUpdatedEpisode,
)
from study_tutor.knowledge.seed_uuids import topic_confidence_uuid
from study_tutor.knowledge.student_model import (
    STUDENT_GROUP_PREFIX,
    ConfidenceBand,
    confidence_band_for,
)

logger = logging.getLogger(__name__)


# REMOVED (TASK-SMP2-06): Read-only constants and models
# - READ_TIMEOUT_SEC, DEFAULT_STALE_THRESHOLD_DAYS, DEFAULT_COOLDOWN_HOURS,
#   DEFAULT_RECOMMENDATION_COUNT, MISCONCEPTION_WINDOW_DAYS, PARTITION_READ_LIMIT
# - RecommendationReason type
# - TopicConfidenceSnapshot, MisconceptionSnapshot, StudentState, TopicRecommendation classes
# These are now available in study_tutor.knowledge.store.entities


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    """Return current UTC time. Hoisted so tests can monkeypatch if needed."""
    return datetime.now(timezone.utc)


def _inner_client(client: Any) -> Any | None:
    """Resolve the underlying graphiti-core client.

    Accepts either a :class:`GraphitiClient` wrapper (exposing
    ``client_or_none``) or a duck-typed inner client directly. Returns
    ``None`` when no inner client is reachable.
    """
    if client is None:
        return None
    if hasattr(client, "client_or_none"):
        inner = client.client_or_none
        return inner
    return client



def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Lookup ``name`` on ``obj`` with dict-or-attribute support."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)



def _coerce_datetime(value: Any) -> datetime | None:
    """Best-effort datetime coercion from a Graphiti attribute payload."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None




# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------




async def record_session_completion(
    client: Any | None,
    write_helper: GraphitiWriteHelper,
    student_id: str,
    session_summary: dict[str, Any],
) -> None:
    """F3 flush owner — fire-and-forget session-completed dispatch.

    Per DDR-002/DDR-003 the session-end episode is dispatched via
    :meth:`GraphitiWriteHelper.schedule_write` with ``flush_id="F3"``.
    The call returns within ~50ms regardless of underlying write latency
    because :meth:`schedule_write` is itself synchronous and the eventual
    ``add_episode`` runs on a fire-and-forget task.

    No-op (returns immediately, no exception) when ``client`` is ``None``.

    Args:
        client: A :class:`GraphitiClient` wrapper or ``None``.
        write_helper: The shared :class:`GraphitiWriteHelper` instance.
        student_id: The student's stable slug.
        session_summary: A loose dict carrying the session attributes
            (``session_id``, ``subject_slug``, ``text_name`` /
            ``topic``, ``topics_covered``, ``aos_exercised``,
            ``narrative_summary`` / ``summary``, ``started_at``,
            ``ended_at``). Missing keys default sensibly so the caller
            never has to special-case partial summaries.
    """
    if client is None:
        return

    # TODO(FEAT-PH1-003): emit session.completed before schedule_write
    # (DDR-003 requires event-emit decoupled from write success; the
    # in-process bus is not yet wired in Phase 1).

    now = _now_utc()
    started_at = _coerce_datetime(session_summary.get("started_at")) or now
    ended_at = _coerce_datetime(session_summary.get("ended_at")) or now

    episode = SessionCompletedEpisode(
        session_id=str(
            session_summary.get("session_id") or f"sess-{int(now.timestamp())}"
        ),
        student_id=student_id,
        subject_slug=str(session_summary.get("subject_slug", "")),
        text_name=str(
            session_summary.get("text_name", session_summary.get("topic", ""))
        ),
        topics_covered=list(session_summary.get("topics_covered", [])),
        aos_exercised=list(session_summary.get("aos_exercised", [])),
        narrative_summary=str(
            session_summary.get(
                "narrative_summary", session_summary.get("summary", "")
            )
        ),
        started_at=started_at,
        ended_at=ended_at,
    )

    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]
    # Fire-and-forget: schedule_write returns synchronously; we never await
    # the returned task.
    write_helper.schedule_write(
        group_ids=group_ids,
        episode=episode,
        flush_id="F3",
    )


# ---------------------------------------------------------------------------
# TopicConfidence write path (TASK-GR-CONF / BLOCK-3b)
# ---------------------------------------------------------------------------
#
# AC-CONF-01..AC-CONF-08 / AC-DEMO-03. The confidence-update path is split
# into two layers per the TASK-REV-GRD5 §R1.3 deep-dive resolution:
#
# - **Infrastructure** (this helper): UUID derivation, EntityNode load /
#   mutate / save, ``last_revised_at`` flip, F2 episode dispatch,
#   fire-and-forget bookkeeping. Stable across phases.
# - **Policy** (:class:`ConfidenceDeltaPolicyLike`): how to compute the
#   integer percentage delta from session signals. Phase-1 ships a stub
#   (:class:`Phase1MinimalDeltaPolicy`) that FEAT-PH2-001 replaces via
#   Protocol substitution.
#
# The split exists because the Coach scores **the Player**, not the
# student, and mapping CoachVerdict.weighted_total directly to confidence
# delta is a category error. Locking that wiring in during Phase 1 would
# poison Phase-2 analytics; the policy seam forces FEAT-PH2-001 to design
# the policy contract explicitly.


class ConfidenceDeltaPolicyLike(Protocol):
    """Computes a TopicConfidence percentage delta for a completed session.

    Phase-1 ships :class:`Phase1MinimalDeltaPolicy`; FEAT-PH2-001 supplies
    the real one. Implementations MUST be deterministic given the same
    inputs (so two runs with identical session_summary produce the same
    delta) and SHOULD produce a value in ``[-10, 10]`` — implementations
    that return larger magnitudes are clamped at the helper boundary by
    the percentage clamp ``[0, 100]``, but the convention is for the
    policy itself to bound its own output.

    Implementations also expose a ``name: str`` attribute identifying the
    policy version. The helper passes that string through to
    :class:`TopicConfidenceUpdatedEpisode.confidence_source` so
    downstream analytics can filter heuristic-era from real-signal data.
    """

    name: str

    def compute(
        self,
        *,
        student_id: str,
        topic_ref: str,
        session_summary: dict[str, Any],
    ) -> int: ...


class Phase1MinimalDeltaPolicy:
    """Phase-1 expedient. NOT a real model of confidence change.

    Owned by FEAT-PH2-001 for replacement. See TASK-REV-GRD5 §R1.3 for
    the Coach-signal taxonomy and category-error analysis that drives
    this stub design — directly mapping ``CoachVerdict.weighted_total``
    to confidence delta is a category error (the Coach scores the
    Player, not the student), so Phase-1 deliberately ships a *weak*
    policy and pushes the policy contract into FEAT-PH2-001.

    Heuristic:

    * ``-3`` per misconception observed on this topic (penalty).
    * ``+1`` if the student took at least 5 turns and surfaced no
      misconceptions on the topic (engagement bonus).
    * Final value clamped to ``[-10, 10]``.

    The clamp is defensive: with the current heuristic the formula can
    only produce negative values below ``-10`` (when ``misc >= 4``); the
    upper clamp is dead code under the stub but kept so a future tweak to
    the heuristic can't accidentally produce a delta outside the policy-
    layer convention.
    """

    name: str = "phase1_minimal_policy"

    def compute(
        self,
        *,
        student_id: str,
        topic_ref: str,
        session_summary: dict[str, Any],
    ) -> int:
        misc = int(
            session_summary.get("misconceptions_per_topic", {}).get(
                topic_ref, 0
            )
        )
        turns = int(session_summary.get("student_turn_count", 0))
        delta = -3 * misc
        if turns >= 5 and misc == 0:
            delta += 1
        return max(-10, min(10, delta))


def _coerce_node_attribute(node: Any, key: str, default: Any = None) -> Any:
    """Return ``node.attributes[key]`` falling back to top-level ``node.key``."""
    attrs = _attr(node, "attributes", {}) or {}
    if isinstance(attrs, dict) and key in attrs:
        return attrs[key]
    return _attr(node, key, default)


async def record_topic_confidence_update(
    *,
    client: Any | None,
    write_helper: GraphitiWriteHelper,
    student_id: str,
    topic_ref: str,
    session_summary: dict[str, Any],
    policy: ConfidenceDeltaPolicyLike,
    create_task_fn: Callable[
        [Awaitable[Any]], asyncio.Task[Any]
    ] = asyncio.create_task,
) -> None:
    """Update a TopicConfidence node + dispatch the F2 episode (BLOCK-3b).

    Implements AC-CONF-01..AC-CONF-06 / AC-DEMO-03. The end-to-end shape:

    1. Derive the TopicConfidence node UUID via
       :func:`topic_confidence_uuid` — same UUID the seed uses, so the
       graphiti-core ``EntityNode.save`` is MERGE-by-uuid (not duplicate
       create).
    2. Load the existing node from the per-group named graph
       (``student-<id>``). FalkorDB drivers require ``clone(database=...)``
       to point at the right graph; non-FalkorDB drivers no-op the clone.
    3. Compute ``new_percentage = clamp(0, current + policy.compute(...), 100)``.
    4. Recompute ``band = confidence_band_for(new_percentage)``.
    5. Set ``last_revised_at = session_summary["ended_at"]``.
    6. Schedule ``EntityNode.save`` via :func:`asyncio.create_task` —
       fire-and-forget; the caller never awaits the typed-entity write.
    7. When ``delta != 0``, also schedule a
       :class:`TopicConfidenceUpdatedEpisode` via
       :meth:`GraphitiWriteHelper.schedule_write` with ``flush_id="F2"``.
       When ``delta == 0`` the entity update still happens (so
       ``last_revised_at`` flips and ``search_nodes`` confirms the
       round-trip per AC-DEMO-03), but the F2 episode is suppressed —
       the temporal-analytics layer has nothing to record.

    Failure handling (AC-CONF-06): every failure path is structured-log
    only. ``Node not found`` (operator picked an unseeded topic),
    ``EntityNode.get_by_uuid`` raise (R-WAVE5-04 connection drop, etc.),
    and episode-write failures all log and return — the caller never sees
    an exception. The session-end episode write proceeds independently.

    Args:
        client: A :class:`GraphitiClient` wrapper or ``None``. ``None`` is
            a graceful no-op (returns immediately, no log noise).
        write_helper: Shared :class:`GraphitiWriteHelper` instance — the
            sole F2 dispatch surface.
        student_id: Stable learner slug (drives the ``student-<id>``
            group_id).
        topic_ref: Topic name — typically the planner-resolved
            ``plan.topic_name`` from the cached :class:`SessionPlan`.
        session_summary: Loose dict carrying at minimum
            ``misconceptions_per_topic``, ``student_turn_count``,
            ``ended_at``, ``triggering_session_id`` (all used by the
            policy and the F2 episode body).
        policy: A :class:`ConfidenceDeltaPolicyLike` implementation. The
            Phase-1 caller passes :class:`Phase1MinimalDeltaPolicy()`;
            FEAT-PH2-001 swaps in the real policy.
        create_task_fn: Indirection over :func:`asyncio.create_task` so
            tests can assert ``EntityNode.save`` is wrapped in fire-and-
            forget rather than awaited inline (AC-CONF-05).
    """
    if client is None:
        return

    inner = _inner_client(client)
    if inner is None:
        return

    driver = getattr(inner, "driver", None)
    if driver is None:
        logger.warning(
            "topic confidence update skipped — no driver on inner client",
            extra={
                "event": "topic_confidence_update_skipped",
                "reason": "no_driver",
                "student_id": student_id,
                "topic_ref": topic_ref,
            },
        )
        return

    group_id = f"{STUDENT_GROUP_PREFIX}{student_id}"
    tc_uuid = topic_confidence_uuid(group_id, student_id, topic_ref)

    # Mirror the seed's per-group named-graph clone (TASK-FORK-PATCH bug
    # #8 isolates each group_id into its own FalkorDB graph). The seed
    # writes the TopicConfidence under student-<id>; we must read+save
    # against the same graph or graphiti-core MERGEs into the wrong
    # database.
    target_driver = _driver_for_group_id(driver, group_id)

    # Defer the graphiti-core import so the queries module stays
    # importable in environments that don't have graphiti-core wired
    # (matches the ``_read_student_partition`` pattern above).
    from graphiti_core.errors import NodeNotFoundError
    from graphiti_core.nodes import EntityNode

    try:
        existing = await EntityNode.get_by_uuid(target_driver, tc_uuid)
    except NodeNotFoundError:
        # AC-CONF-06: operator picked an unseeded topic. Log and bail —
        # the session_completed episode dispatch (AC-CONF-08 caller side)
        # proceeds independently of this branch.
        logger.warning(
            "topic confidence update skipped — node not found",
            extra={
                "event": "topic_confidence_update_skipped",
                "reason": "node_not_found",
                "student_id": student_id,
                "topic_ref": topic_ref,
                "uuid": tc_uuid,
            },
        )
        return
    except Exception as exc:  # noqa: BLE001 — boundary catch
        logger.warning(
            "topic confidence load failed",
            extra={
                "event": "topic_confidence_update_failed",
                "reason": "load_failed",
                "student_id": student_id,
                "topic_ref": topic_ref,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return

    delta = int(
        policy.compute(
            student_id=student_id,
            topic_ref=topic_ref,
            session_summary=session_summary,
        )
    )

    current_percentage = int(_coerce_node_attribute(existing, "percentage", 0))
    new_percentage = max(0, min(current_percentage + delta, 100))
    new_band: ConfidenceBand = confidence_band_for(new_percentage)
    previous_band = str(_coerce_node_attribute(existing, "band", new_band))

    ended_at = _coerce_datetime(session_summary.get("ended_at")) or _now_utc()

    # Mutate the loaded node in place. ``EntityNode.save`` is MERGE-by-
    # uuid in the FalkorDB driver, so writing back the same uuid with
    # updated attributes overwrites the persisted state without
    # duplicating.
    attrs = dict(_attr(existing, "attributes", {}) or {})
    attrs["percentage"] = new_percentage
    attrs["band"] = new_band
    attrs["last_revised_at"] = ended_at.isoformat()
    try:
        existing.attributes = attrs  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — duck-typed test doubles
        # Test fakes may not expose a settable ``attributes`` dict; fall
        # back to setattr-per-key so the production graphiti-core node
        # path and the test doubles both work.
        for key, value in attrs.items():
            try:
                setattr(existing, key, value)
            except Exception:  # noqa: BLE001
                pass

    # AC-CONF-05: fire-and-forget the typed-entity save. We never await
    # the returned task; the helper's caller (``tutor_session_end``)
    # must return within 2 s regardless of FalkorDB latency.
    try:
        save_coro = existing.save(target_driver)
        create_task_fn(save_coro)
    except Exception as exc:  # noqa: BLE001 — boundary catch
        logger.warning(
            "topic confidence save dispatch failed",
            extra={
                "event": "topic_confidence_update_failed",
                "reason": "save_dispatch_failed",
                "student_id": student_id,
                "topic_ref": topic_ref,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )

    # AC-CONF-04: F2 episode write only when the percentage actually
    # moved. Delta-zero updates still flip ``last_revised_at`` (entity
    # path above) — that's the structural change AC-DEMO-03 needs.
    if delta == 0:
        return

    confidence_source = getattr(policy, "name", "unknown_policy")
    episode = TopicConfidenceUpdatedEpisode(
        student_id=student_id,
        topic_name=topic_ref,
        previous_band=str(previous_band),
        new_band=str(new_band),
        previous_percentage=int(current_percentage),
        new_percentage=int(new_percentage),
        observed_at=ended_at,
        triggering_session_id=session_summary.get("triggering_session_id"),
        confidence_source=confidence_source,
    )
    write_helper.schedule_write(
        group_ids=[group_id],
        episode=episode,
        flush_id="F2",
    )


def _driver_for_group_id(driver: Any, group_id: str) -> Any:
    """Clone ``driver`` to point at the per-group named graph.

    Mirrors :func:`scripts.seed_student_model._driver_for_group` so the
    write-side path uses the same per-group isolation as the seed's
    typed-entity writes (TASK-FORK-PATCH bug #8). Drivers without a
    ``clone(database=...)`` shape (e.g. test doubles) get the original
    driver back.
    """
    clone_fn = getattr(driver, "clone", None)
    if clone_fn is None:
        return driver
    try:
        return clone_fn(database=group_id)
    except TypeError:
        return driver


__all__ = [
    "ConfidenceDeltaPolicyLike",
    "Phase1MinimalDeltaPolicy",
    "record_session_completion",
    "record_topic_confidence_update",
]
