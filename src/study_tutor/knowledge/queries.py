"""Student-model query helpers (TASK-GSM-005).

Phase-1 read-side helpers and F3 write owner for FEAT-1773. This module
holds the only call sites in Phase 1 that enumerate the student-partition
of the graph. Every read call constructs ``group_ids`` from the constants
in :mod:`study_tutor.knowledge.student_model` — never as bare string
literals. The Group-id discipline AST lint in ``test_queries.py`` enforces
that invariant.

The read path uses graphiti-core 0.29's class-method enumerators
(``EntityNode.get_by_group_ids`` / ``EntityEdge.get_by_group_ids``) which
accept a driver and a list of group ids and return every node/edge in
that partition — the right primitive for "give me everything for this
student" rather than the relevance-ranked ``Graphiti.search`` API. The
single seam :func:`_read_student_partition` wraps both calls so tests can
monkeypatch one function rather than two unbound class methods.

Load-bearing properties:

- **Read-path timeout** (ASSUM-005): :func:`get_student_state` returns
  ``None`` and logs ``event=student_state_read_timeout`` if the underlying
  search exceeds :data:`READ_TIMEOUT_SEC`.
- **Stale-fact flag** (ASSUM-006): facts older than ``stale_threshold_days``
  are returned with ``stale=True`` rather than dropped.
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
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.episodes import SessionCompletedEpisode
from study_tutor.knowledge.student_model import (
    STUDENT_GROUP_PREFIX,
    ConfidenceBand,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Read-path budget per ASSUM-005.
READ_TIMEOUT_SEC: float = 5.0

#: Stale-fact threshold per ASSUM-006 (days).
DEFAULT_STALE_THRESHOLD_DAYS: int = 180

#: Topic-revision cooldown per ASSUM-003 (hours).
DEFAULT_COOLDOWN_HOURS: int = 48

#: Default recommendation count per ASSUM-002.
DEFAULT_RECOMMENDATION_COUNT: int = 3

#: Trailing window over which recent misconceptions count (days).
MISCONCEPTION_WINDOW_DAYS: int = 30

#: Cap on rows returned by :func:`_read_student_partition`. The Phase 1
#: Lilymay seed is ~30 nodes/edges; 500 is a generous ceiling that bounds
#: read latency without truncating any plausible single-student profile.
PARTITION_READ_LIMIT: int = 500


RecommendationReason = Literal[
    "struggling_stale",
    "developing_misconception",
    "developing_stale",
]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class TopicConfidenceSnapshot(BaseModel):
    """In-memory projection of a TopicConfidence node returned by Graphiti."""

    model_config = ConfigDict(extra="forbid")

    topic_name: str
    band: ConfidenceBand
    percentage: int = Field(ge=0, le=100)
    last_revised_at: datetime | None = None


class MisconceptionSnapshot(BaseModel):
    """In-memory projection of a Misconception node returned by Graphiti."""

    model_config = ConfigDict(extra="forbid")

    topic_name: str
    text: str
    observed_at: datetime


class StudentState(BaseModel):
    """Aggregated student-model snapshot returned by :func:`get_student_state`.

    ``empty=True`` is the explicit "graphiti unavailable" sentinel — callers
    can branch on it without inspecting other fields. ``stale=True`` flags
    that at least one underlying fact is older than the configured stale
    threshold (per ASSUM-006); the fact is still returned.
    """

    model_config = ConfigDict(extra="forbid")

    empty: bool = False
    stale: bool = False
    student_id: str | None = None
    year_group: int | None = None
    target_grade: str | None = None
    subjects: list[str] = Field(default_factory=list)
    current_texts: list[str] = Field(default_factory=list)
    topic_confidences: list[TopicConfidenceSnapshot] = Field(default_factory=list)
    recent_misconceptions: list[MisconceptionSnapshot] = Field(default_factory=list)
    most_recent_session_id: str | None = None


class TopicRecommendation(BaseModel):
    """A single ranked topic recommendation for the planner/handler."""

    model_config = ConfigDict(extra="forbid")

    topic_name: str
    reason: RecommendationReason
    confidence_band: ConfidenceBand
    last_revised_at: datetime | None = None


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


async def _read_student_partition(
    inner: Any,
    group_ids: list[str],
    limit: int = PARTITION_READ_LIMIT,
) -> tuple[list[Any], list[Any]]:
    """Enumerate every node + edge in the given group-id partition.

    Wraps graphiti-core 0.29's ``EntityNode.get_by_group_ids`` /
    ``EntityEdge.get_by_group_ids`` class-method enumerators. ``inner``
    must expose ``inner.driver`` (the graphiti-core ``Graphiti`` instance
    convention). Returns ``(nodes, edges)``. This is the single seam
    tests monkeypatch rather than mocking two unbound class methods.

    A duck-typed shortcut is honoured for legacy test doubles: if
    ``inner`` exposes ``read_partition`` or the historical
    ``search_nodes``/``search_memory_facts`` pair, those are used instead.
    The shortcut keeps existing fixtures working without forcing every
    test to construct a fake graphiti-core driver.
    """
    if hasattr(inner, "read_partition"):
        return await inner.read_partition(group_ids)  # type: ignore[no-any-return]
    if hasattr(inner, "search_nodes") and hasattr(inner, "search_memory_facts"):
        nodes, facts = await asyncio.gather(
            inner.search_nodes(group_ids, ""),
            inner.search_memory_facts(group_ids, ""),
        )
        return list(nodes), list(facts)

    from graphiti_core.driver.driver import GraphProvider
    from graphiti_core.edges import EntityEdge
    from graphiti_core.errors import (
        GroupsEdgesNotFoundError,
        GroupsNodesNotFoundError,
    )
    from graphiti_core.nodes import EntityNode

    driver = getattr(inner, "driver", None)
    if driver is None:
        return [], []

    # The guardkit graphiti fork (TASK-FORK-PATCH bug #8) isolates each
    # group_id into its own FalkorDB named graph (graph name == group_id).
    # The high-level Graphiti search/retrieve methods auto-clone via the
    # ``handle_multiple_group_ids`` decorator, but the static enumerators
    # ``EntityNode.get_by_group_ids`` / ``EntityEdge.get_by_group_ids``
    # take a raw driver and run on whatever database that driver was last
    # pointed at — typically the default ``study_tutor`` graph, which is
    # empty under the per-group isolation. Mirror the writer-side decorator
    # by cloning the driver per group_id and aggregating.
    is_falkordb = (
        getattr(driver, "provider", None) == GraphProvider.FALKORDB
    )

    async def _safe_nodes(target_driver: Any, gids: list[str]) -> list[Any]:
        try:
            result = await EntityNode.get_by_group_ids(
                target_driver, gids, limit=limit
            )
        except GroupsNodesNotFoundError:
            # graphiti-core 0.29 raises rather than returning ``[]`` for
            # empty partitions — the bootstrap case (e.g. pre-seed Lilymay)
            # is not an error condition for our read path.
            return []
        return list(result)

    async def _safe_edges(target_driver: Any, gids: list[str]) -> list[Any]:
        try:
            result = await EntityEdge.get_by_group_ids(
                target_driver, gids, limit=limit
            )
        except GroupsEdgesNotFoundError:
            return []
        return list(result)

    if not is_falkordb:
        nodes, edges = await asyncio.gather(
            _safe_nodes(driver, group_ids),
            _safe_edges(driver, group_ids),
        )
        return nodes, edges

    async def _read_one_group(gid: str) -> tuple[list[Any], list[Any]]:
        cloned = driver.clone(database=gid)
        nodes_one, edges_one = await asyncio.gather(
            _safe_nodes(cloned, [gid]),
            _safe_edges(cloned, [gid]),
        )
        return nodes_one, edges_one

    per_group = await asyncio.gather(
        *(_read_one_group(gid) for gid in group_ids)
    )
    aggregated_nodes = [n for nodes_one, _ in per_group for n in nodes_one]
    aggregated_edges = [e for _, edges_one in per_group for e in edges_one]
    return aggregated_nodes, aggregated_edges


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    """Lookup ``name`` on ``obj`` with dict-or-attribute support."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _entity_type(node: Any) -> str:
    """Return a node's entity-type discriminator (best-effort, lowercase).

    graphiti-core's ``EntityNode`` exposes the entity class via ``labels``
    (a list of strings — the primary kind plus any auxiliary tags such as
    ``"Entity"``). The first non-``Entity`` label wins. Falls back to the
    legacy duck-typed attributes (``entity_type``, ``type``, ``label``,
    ``kind``) so test doubles built before the graphiti-core 0.29 read
    path landed continue to project correctly.
    """
    labels = _attr(node, "labels")
    if isinstance(labels, list):
        for label in labels:
            if label and str(label).lower() != "entity":
                return str(label).lower()
    for key in ("entity_type", "type", "label", "kind"):
        value = _attr(node, key)
        if value is not None:
            return str(value).lower()
    return ""


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


def _build_student_state(
    student_id: str,
    nodes: Any,
    facts: Any,
    stale_threshold_days: int,
) -> StudentState:
    """Project raw nodes/facts into a :class:`StudentState`.

    The projection is duck-typed: each node is inspected for an
    ``entity_type``-like attribute and an ``attributes`` dict. Unknown node
    kinds are skipped silently — Graphiti returns a wider universe than
    Phase 1 consumes, and ignoring extras keeps this helper forward-
    compatible.
    """
    state = StudentState(student_id=student_id)
    now = _now_utc()
    misconception_cutoff = now - timedelta(days=MISCONCEPTION_WINDOW_DAYS)
    stale_cutoff = now - timedelta(days=stale_threshold_days)
    most_recent_session_at: datetime | None = None

    for node in nodes or []:
        kind = _entity_type(node)
        attrs = _attr(node, "attributes", {}) or {}

        if kind == "student":
            year_group = _attr(attrs, "year_group", _attr(node, "year_group"))
            target_grade = _attr(attrs, "target_grade", _attr(node, "target_grade"))
            if year_group is not None and state.year_group is None:
                state.year_group = int(year_group)
            if target_grade is not None and state.target_grade is None:
                state.target_grade = str(target_grade)
            # ADR-ARCH-021 §G1: subjects are denormalised onto the Student node
            # as ``enrolled_subjects: list[str]`` because cross-group edge
            # traversal (Student → STUDIES → Subject across student-/subject-
            # named graphs) is functionally broken on the FalkorDB driver
            # (silent dangle; see G2 probe outcome). The Subject nodes still
            # exist under ``subject-<slug>`` for curriculum-level structure,
            # but the planner-level "what is this student enrolled in" answer
            # comes from this attribute, not edge traversal.
            enrolled = _attr(
                attrs, "enrolled_subjects", _attr(node, "enrolled_subjects")
            )
            if isinstance(enrolled, list):
                for subject in enrolled:
                    if subject:
                        state.subjects.append(str(subject))

        elif kind == "subject":
            name = _attr(attrs, "name", _attr(node, "name"))
            if name:
                state.subjects.append(str(name))

        elif kind == "text":
            name = _attr(attrs, "name", _attr(node, "name"))
            if name:
                state.current_texts.append(str(name))

        elif kind == "topicconfidence":
            topic_name = _attr(attrs, "topic_ref", _attr(node, "topic_ref"))
            band = _attr(attrs, "band", _attr(node, "band"))
            percentage = _attr(attrs, "percentage", _attr(node, "percentage"))
            last_revised = _coerce_datetime(
                _attr(attrs, "last_revised_at", _attr(node, "last_revised_at"))
            )
            if topic_name and band is not None and percentage is not None:
                state.topic_confidences.append(
                    TopicConfidenceSnapshot(
                        topic_name=str(topic_name),
                        band=band,
                        percentage=int(percentage),
                        last_revised_at=last_revised,
                    )
                )
                if last_revised is not None and last_revised < stale_cutoff:
                    state.stale = True

        elif kind == "misconception":
            topic_name = _attr(attrs, "topic_ref", _attr(node, "topic_ref"))
            text = _attr(attrs, "text", _attr(node, "text"))
            observed_at = _coerce_datetime(
                _attr(attrs, "observed_at", _attr(node, "observed_at"))
            )
            if (
                topic_name
                and text
                and observed_at is not None
                and observed_at >= misconception_cutoff
            ):
                state.recent_misconceptions.append(
                    MisconceptionSnapshot(
                        topic_name=str(topic_name),
                        text=str(text),
                        observed_at=observed_at,
                    )
                )

    for fact in facts or []:
        fact_type = (
            _attr(fact, "fact_type")
            or _attr(fact, "kind")
            or _attr(fact, "name")
            or ""
        )
        if str(fact_type).lower() not in {"session_completed", "session.completed"}:
            continue
        ended_at = _coerce_datetime(
            _attr(fact, "ended_at")
            or _attr(fact, "observed_at")
            or _attr(fact, "created_at")
        )
        session_id = _attr(fact, "session_id") or _attr(fact, "id")
        if session_id and ended_at is not None:
            if most_recent_session_at is None or ended_at > most_recent_session_at:
                most_recent_session_at = ended_at
                state.most_recent_session_id = str(session_id)

    return state


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_student_state(
    client: Any | None,
    student_id: str,
    *,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
) -> StudentState | None:
    """Return the full :class:`StudentState` for a student.

    Args:
        client: A :class:`GraphitiClient` wrapper (or duck-typed inner
            graphiti-core client). When ``None``, the helper returns an
            empty state without contacting Graphiti.
        student_id: The student's stable slug, e.g. ``"lilymay"``.
        stale_threshold_days: Facts older than this are flagged via
            ``StudentState.stale=True`` (per ASSUM-006). Default 180.

    Returns:
        - :class:`StudentState` populated from the graph on success.
        - ``StudentState(empty=True)`` when ``client`` is ``None`` or the
          wrapper has no live inner client.
        - ``None`` when the underlying search exceeds
          :data:`READ_TIMEOUT_SEC`. A structured warning record with
          ``event=student_state_read_timeout`` is emitted in that path.
    """
    if client is None:
        return StudentState(empty=True)

    inner = _inner_client(client)
    if inner is None:
        return StudentState(empty=True)

    group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]

    try:
        nodes, facts = await asyncio.wait_for(
            _read_student_partition(inner, group_ids),
            timeout=READ_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "student state read timed out after %.1fs",
            READ_TIMEOUT_SEC,
            extra={
                "event": "student_state_read_timeout",
                "student_id": student_id,
                "timeout_sec": READ_TIMEOUT_SEC,
            },
        )
        return None

    return _build_student_state(student_id, nodes, facts, stale_threshold_days)


async def get_topic_recommendations(
    client: Any | None,
    student_id: str,
    count: int = DEFAULT_RECOMMENDATION_COUNT,
    cooldown_hours: int = DEFAULT_COOLDOWN_HOURS,
) -> list[TopicRecommendation]:
    """Return up to ``count`` ranked topic recommendations.

    Priority (highest first, per ASSUM-002 / ASSUM-003):

    1. Struggling-band topics not revised in the last ``cooldown_hours``.
    2. Developing-band topics with a misconception in the last
       :data:`MISCONCEPTION_WINDOW_DAYS` days.
    3. Developing-band topics not revised in the last ``cooldown_hours``.
    4. Random developing-band fallback — currently unimplemented.

    Topics revised within ``cooldown_hours`` are excluded from the head of
    the list per the ``@boundary`` scenario.

    Returns ``[]`` (not ``None``) when no candidates are available or when
    ``client`` is ``None``.
    """
    if client is None:
        return []

    state = await get_student_state(client, student_id)
    if state is None or state.empty:
        return []

    now = _now_utc()
    cooldown_cutoff = now - timedelta(hours=cooldown_hours)
    misconception_topics = {m.topic_name for m in state.recent_misconceptions}

    struggling_stale: list[TopicRecommendation] = []
    developing_misconception: list[TopicRecommendation] = []
    developing_stale: list[TopicRecommendation] = []

    for tc in state.topic_confidences:
        in_cooldown = (
            tc.last_revised_at is not None and tc.last_revised_at >= cooldown_cutoff
        )
        if in_cooldown:
            # Cooldown excludes from the head of the list per @boundary.
            continue

        if tc.band == "struggling":
            struggling_stale.append(
                TopicRecommendation(
                    topic_name=tc.topic_name,
                    reason="struggling_stale",
                    confidence_band=tc.band,
                    last_revised_at=tc.last_revised_at,
                )
            )
        elif tc.band == "developing":
            if tc.topic_name in misconception_topics:
                developing_misconception.append(
                    TopicRecommendation(
                        topic_name=tc.topic_name,
                        reason="developing_misconception",
                        confidence_band=tc.band,
                        last_revised_at=tc.last_revised_at,
                    )
                )
            else:
                developing_stale.append(
                    TopicRecommendation(
                        topic_name=tc.topic_name,
                        reason="developing_stale",
                        confidence_band=tc.band,
                        last_revised_at=tc.last_revised_at,
                    )
                )
        # TODO(phase-2): rule 5 — random developing-band fallback when no
        # other candidate qualifies.

    ranked = struggling_stale + developing_misconception + developing_stale
    return ranked[:count]


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


__all__ = [
    "DEFAULT_COOLDOWN_HOURS",
    "DEFAULT_RECOMMENDATION_COUNT",
    "DEFAULT_STALE_THRESHOLD_DAYS",
    "MISCONCEPTION_WINDOW_DAYS",
    "READ_TIMEOUT_SEC",
    "MisconceptionSnapshot",
    "RecommendationReason",
    "StudentState",
    "TopicConfidenceSnapshot",
    "TopicRecommendation",
    "get_student_state",
    "get_topic_recommendations",
    "record_session_completion",
]
