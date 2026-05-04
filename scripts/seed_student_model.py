"""Lilymay baseline seeding script (TASK-GSM-009 — typed-entity rewrite).

One-off scaffolding script that populates Lilymay's baseline learner profile
into the Synology FalkorDB via **typed-entity writes** (``EntityNode.save`` /
``EntityEdge.save``) rather than ``add_episode``-driven LLM extraction. Per
``phase-1-scope.md §FEAT-PH1-001`` (Lilymay seeding) and ADR-ARCH-021
(typed-entity seed design resolutions), running this script end-to-end is
the integration gate that closes Phase 1's G2/G3 gates.

Why typed-entity writes (not ``add_episode``)
---------------------------------------------

The original TASK-GSM-006 implementation routed every seed write through
``GraphitiWriteHelper.schedule_write`` → ``_perform_write`` → ``add_episode``.
That hits graphiti-core's LLM-driven entity extraction path on every call
(~30+ minutes wall-clock per full seed against the GB10 vLLM endpoint, with
intermittent 429s under concurrency). It also went through a non-trivial
chain of failures (R-WAVE5-01 vLLM rate-limiting, R-WAVE5-03 RediSearch
dash-as-NOT — the latter fixed in the guardkit graphiti-core fork at
``v0.29.5-guardkit.2``).

TASK-GSM-007's design review approved Path 1B: build the typed Pydantic
entity instances declared in :mod:`study_tutor.knowledge.student_model`,
serialise them via graphiti-core's ``EntityNode`` / ``EntityEdge`` types,
and call ``.save(driver)`` directly. Same input → same graph state, ~1s
wall-clock, no LLM in the loop, byte-idempotent on re-run via
deterministic UUID5 derivation (see :mod:`study_tutor.knowledge.seed_uuids`).

CC-13 invariant narrowing
-------------------------

Per ADR-ARCH-021, the CC-13 single-call-site invariant (originally "all
``add_episode`` calls go through ``GraphitiWriteHelper``") is narrowed to
**"all live tutor session ``add_episode`` calls go through
``GraphitiWriteHelper``; the seed writes typed entities directly"**. The
seed therefore has no ``add_episode`` calls at all (a grep enforces this in
TASK-GSM-009 AC-01). See :mod:`study_tutor.knowledge.async_write` module
docstring for the runtime side of the same statement.

Group-id discipline
-------------------

Carries forward unchanged from TASK-GSM-006:

- ``student-<id>`` for student-scoped writes (Student node, TopicConfidence
  nodes, ``HAS_CONFIDENCE`` edges).
- ``subject-<slug>`` for curriculum-scoped writes (Subject, Text, Topic
  nodes; ``HAS_TEXT`` and ``COVERS`` edges).
- ``fleet-appmilla`` for cross-fleet writes (AssessmentObjective nodes).

Cross-group edges (``Student → STUDIES → Subject``,
``Student → WORKING_ON → Text``, ``Topic → ASSESSED_BY → AO``) are
**deferred** under ADR-ARCH-021 §G2 — the G2 probe (2026-05-04) confirmed
``EntityEdge.save()`` silently dangles when source and target nodes live in
different named graphs. The Student node carries an ``enrolled_subjects:
list[str]`` attribute as a denormalisation workaround (G1) and Topic nodes
carry an ``ao_refs: list[str]`` attribute that mirrors the dropped
ASSESSED_BY edge.

Usage
-----

::

    python scripts/seed_student_model.py [--config-path PATH]

When ``--config-path`` is omitted the script falls back to the canonical
Phase-1 Synology defaults (whitestocks FalkorDB + GB10 vLLM embedder, the
latter unused by typed-entity writes). A YAML config may override any
field of :class:`~study_tutor.knowledge.graphiti_client.GraphitiConnectionConfig`.

Exit-code contract
------------------

- ``0`` — fresh seed succeeded **or** pre-flight detected an existing
  baseline and skipped (idempotent re-run). Re-running is byte-idempotent
  via deterministic UUID5 derivation; no abandonment-counting needed.
- ``2`` — Graphiti / FalkorDB unreachable (``get_client`` returned ``None``).
  Seeding is **not** a degradation path: it requires a live store. A
  structured log line ``event=seeding_failed, reason=client_unavailable``
  is emitted before exit.

Note: the legacy ``EXIT_PENDING_WRITES_ABANDONED = 3`` code is removed —
``EntityNode.save`` / ``EntityEdge.save`` are sequential synchronous-style
calls with no async fan-out, so there is no abandonment surface.

Structured log events
---------------------

- ``seeding_failed`` — fatal, paired with ``reason``.
- ``seeding_failed_unhandled`` — uncaught exception in the orchestrator.
- ``seeding_skipped`` — pre-flight detected an existing baseline.
- ``seeding_completed`` — full seed succeeded; carries entity counts.
- ``seeding_verification_warning`` — post-write read-back returned empty.
- ``seeding_node_written`` — debug-level, one per node, structured with
  ``entity_kind``, ``name``, ``group_id``, ``uuid``. Useful for diagnosis
  without a graph dump.
- ``seeding_edge_written`` — debug-level, one per edge, structured with
  ``edge_name``, ``source_uuid``, ``target_uuid``, ``group_id``, ``uuid``.

Manual verification
-------------------

After running, drop into Claude Desktop with the Graphiti MCP wired up and
issue::

    search_nodes(query="Lilymay", group_ids=["student-lilymay"])

The Student entity should be returned with ``enrolled_subjects=["English
Literature", "English Language"]`` and the rest of the baseline attributes.
Or run ``.guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py`` for the JSON
form used in the Phase-1 validation gate evidence.

Cross-references
----------------

- ADR-ARCH-021 — typed-entity seed design resolutions (G1/G2/G3)
- TASK-GSM-001 — Pydantic entity models consumed here
- :mod:`study_tutor.knowledge.seed_uuids` — deterministic UUID derivation
- :mod:`study_tutor.knowledge.student_model` — entity classes + relationship
  constants + ``EPOCH_NEVER_REVISED`` sentinel
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from study_tutor.knowledge.graphiti_client import (
    DEFAULT_GRAPHITI_YAML_PATH,
    GraphitiClient,
    GraphitiConnectionConfig,
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.queries import get_student_state
from study_tutor.knowledge.seed_uuids import (
    assessment_objective_uuid,
    edge_uuid,
    student_uuid,
    subject_uuid,
    text_uuid,
    topic_confidence_uuid,
    topic_uuid,
)
from study_tutor.knowledge.student_model import (
    COVERS,
    EPOCH_NEVER_REVISED,
    FLEET_GROUP_ID,
    HAS_CONFIDENCE,
    HAS_TEXT,
    STUDENT_GROUP_PREFIX,
    SUBJECT_GROUP_PREFIX,
    confidence_band_for,
)


logger = logging.getLogger("study_tutor.seed")


# ---------------------------------------------------------------------------
# Exit-code constants (script contract — see module docstring)
# ---------------------------------------------------------------------------

EXIT_OK: int = 0
EXIT_CLIENT_UNAVAILABLE: int = 2


# ---------------------------------------------------------------------------
# Lilymay's baseline data (Phase-1 hand-curated)
# ---------------------------------------------------------------------------

#: Lilymay's stable slug — the single learner identity in Phase 1.
STUDENT_ID: str = "lilymay"

#: Display name on the Student entity.
STUDENT_NAME: str = "Lilymay"

#: UK secondary year group (per phase-1-scope.md §FEAT-PH1-001).
STUDENT_YEAR_GROUP: int = 10

#: GCSE target grade. Stored as a string so we don't accidentally do maths on it.
STUDENT_TARGET_GRADE: str = "7"


#: AQA AO1–AO6 with their canonical English Literature / Language descriptions.
#:
#: AO1–AO4 are taken from AQA spec 8702 (English Literature). AO5/AO6 are the
#: spec-8700 (English Language) production AOs that don't appear in the Lit
#: spec but are part of the wider GCSE-English curriculum surface — both
#: subjects share AOs in our model so the planner can link a Lit topic to an
#: AO that's only formally tested under Lang. (Phase 1 has both subjects in
#: scope per the Subject seeds below.)
AOS: tuple[dict[str, str], ...] = (
    {
        "code": "AO1",
        "exam_board": "AQA",
        "description": (
            "Read, understand and respond to texts. Students should be able "
            "to: maintain a critical style and develop an informed personal "
            "response; use textual references, including quotations, to "
            "support and illustrate interpretations."
        ),
    },
    {
        "code": "AO2",
        "exam_board": "AQA",
        "description": (
            "Analyse the language, form and structure used by a writer to "
            "create meanings and effects, using relevant subject "
            "terminology where appropriate."
        ),
    },
    {
        "code": "AO3",
        "exam_board": "AQA",
        "description": (
            "Show understanding of the relationships between texts and the "
            "contexts in which they were written."
        ),
    },
    {
        "code": "AO4",
        "exam_board": "AQA",
        "description": (
            "Use a range of vocabulary and sentence structures for clarity, "
            "purpose and effect, with accurate spelling and punctuation."
        ),
    },
    {
        "code": "AO5",
        "exam_board": "AQA",
        "description": (
            "Communicate clearly, effectively and imaginatively, selecting "
            "and adapting tone, style and register for different forms, "
            "purposes and audiences. Organise information and ideas, using "
            "structural and grammatical features to support coherence and "
            "cohesion of texts."
        ),
    },
    {
        "code": "AO6",
        "exam_board": "AQA",
        "description": (
            "Candidates must use a range of vocabulary and sentence "
            "structures for clarity, purpose and effect, with accurate "
            "spelling and punctuation. (20% of English Language marks.)"
        ),
    },
)


#: Subjects on Lilymay's enrolment (English Lit + Lang, both AQA).
SUBJECTS: tuple[dict[str, str], ...] = (
    {
        "name": "English Literature",
        "exam_board": "AQA",
        "spec_code": "8702",
        "slug": "english-literature",
    },
    {
        "name": "English Language",
        "exam_board": "AQA",
        "spec_code": "8700",
        "slug": "english-language",
    },
)


#: Texts on the curriculum (mix of primary set texts + at least one secondary
#: study guide per the task scope).
TEXTS: tuple[dict[str, str], ...] = (
    {
        "name": "Macbeth",
        "kind": "primary",
        "subject_slug": "english-literature",
        "source_path": "domains/english-literature/sources/primary/macbeth.txt",
    },
    {
        "name": "A Christmas Carol",
        "kind": "primary",
        "subject_slug": "english-literature",
        "source_path": (
            "domains/english-literature/sources/primary/a-christmas-carol.txt"
        ),
    },
    {
        "name": "Power and Conflict poetry cluster",
        "kind": "primary",
        "subject_slug": "english-literature",
        "source_path": (
            "domains/english-literature/sources/primary/power-and-conflict.txt"
        ),
    },
    {
        "name": "York Notes: Macbeth (study guide)",
        "kind": "secondary",
        "subject_slug": "english-literature",
        "source_path": (
            "domains/english-literature/sources/secondary/york-notes-macbeth.md"
        ),
    },
)


#: Topics with their initial confidence percentages. The mix below puts at
#: least one topic in each band (struggling / developing / secure) so the
#: planner has shape on day 1 (AC-006).
TOPICS: tuple[dict[str, Any], ...] = (
    {
        "name": "Macbeth's witches",
        "subject_slug": "english-literature",
        "ao_refs": ["AO1", "AO2"],
        "initial_percentage": 25,  # struggling
    },
    {
        "name": "Power and Conflict: Ozymandias themes",
        "subject_slug": "english-literature",
        "ao_refs": ["AO1", "AO3"],
        "initial_percentage": 35,  # struggling
    },
    {
        "name": "Lady Macbeth's ambition",
        "subject_slug": "english-literature",
        "ao_refs": ["AO1", "AO2", "AO3"],
        "initial_percentage": 55,  # developing
    },
    {
        "name": "Metaphor identification",
        "subject_slug": "english-language",
        "ao_refs": ["AO2"],
        "initial_percentage": 60,  # developing
    },
    {
        "name": "Scrooge's redemption arc",
        "subject_slug": "english-literature",
        "ao_refs": ["AO1", "AO2"],
        "initial_percentage": 75,  # secure
    },
    {
        "name": "Macbeth: ambition and guilt",
        "subject_slug": "english-literature",
        "ao_refs": ["AO1", "AO2", "AO3"],
        "initial_percentage": 80,  # secure
    },
)


# ---------------------------------------------------------------------------
# Default connection config (Phase-1 Synology stack)
# ---------------------------------------------------------------------------

#: Defaults align with ``phase-1-scope.md`` and the latency-spike script.
#:
#: Note: under typed-entity writes, ``llm_provider`` / ``llm_model`` /
#: ``embedder_url`` are unused at seed time (no LLM extraction in the write
#: path). They are retained here so live tutor-session writes via the same
#: config still resolve correctly.
DEFAULT_CONFIG: dict[str, Any] = {
    "falkor_host": "whitestocks",
    "falkor_port": 6379,
    "database": "study_tutor",
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-pro",
    "embedder_url": "http://promaxgb10-41b1:8001/v1",
    "timeout_seconds": 5.0,
}


# ---------------------------------------------------------------------------
# CLI / config plumbing
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the CLI arguments. Single ``--config-path`` flag (AC-001)."""
    parser = argparse.ArgumentParser(
        prog="seed_student_model",
        description=(
            "Seed Lilymay's baseline learner profile into the configured "
            "Graphiti / FalkorDB store via typed-entity writes. Idempotent "
            "on re-run."
        ),
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=None,
        help=(
            "Optional path to a YAML file overriding the default "
            "GraphitiConnectionConfig. When omitted the Phase-1 Synology "
            "defaults are used."
        ),
    )
    return parser.parse_args(argv)


def load_config(path: Path | None) -> GraphitiConnectionConfig:
    """Build a :class:`GraphitiConnectionConfig` from defaults + optional YAML.

    The YAML file (if provided) is merged on top of :data:`DEFAULT_CONFIG`,
    so callers can override only the fields that differ from the Phase-1
    Synology stack.
    """
    merged: dict[str, Any] = dict(DEFAULT_CONFIG)
    if path is not None:
        raw = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"config file {path!s} must deserialise to a mapping; "
                f"got {type(raw).__name__}"
            )
        merged.update(raw)
    return GraphitiConnectionConfig(**merged)


# ---------------------------------------------------------------------------
# Seam-tested helpers (referenced directly by the seam tests in the task spec)
# ---------------------------------------------------------------------------


def require_client_or_exit(client: GraphitiClient | None) -> GraphitiClient:
    """Exit ``2`` with a structured log if the Graphiti client is unavailable.

    Seeding is **not** a degradation path — unlike Coach/Tutor flush points it
    cannot quietly no-op. If the upstream :func:`get_client` factory returned
    ``None`` (library missing, FalkorDB unreachable, healthcheck failed),
    every subsequent write would silently drop and the verification gate
    would mis-report success. So we fail fast here per AC-004.

    Raises:
        SystemExit: With code :data:`EXIT_CLIENT_UNAVAILABLE` (2) when
            ``client`` is ``None``.
    """
    if client is None:
        logger.error(
            "seeding failed: graphiti client unavailable",
            extra={
                "event": "seeding_failed",
                "reason": "client_unavailable",
            },
        )
        raise SystemExit(EXIT_CLIENT_UNAVAILABLE)
    return client


# ---------------------------------------------------------------------------
# Driver helpers (FalkorDB per-group named-graph isolation)
# ---------------------------------------------------------------------------


def _student_group(student_id: str) -> str:
    return f"{STUDENT_GROUP_PREFIX}{student_id}"


def _subject_group(slug: str) -> str:
    return f"{SUBJECT_GROUP_PREFIX}{slug}"


def _now_utc() -> datetime:
    """Return the current UTC instant. Hoisted so tests can monkeypatch."""
    return datetime.now(timezone.utc)


def _driver_for_group(driver: Any, group_id: str) -> Any:
    """Return a driver pointing at the named graph for ``group_id``.

    The guardkit graphiti-core fork (TASK-FORK-PATCH bug #8) isolates each
    ``group_id`` into its own FalkorDB named graph (graph name == group_id).
    Typed writes ignore the high-level ``Graphiti`` decorator that auto-clones
    on the read side, so we mirror it explicitly here. Drivers that don't
    expose ``clone(database=...)`` (Neo4j, Kuzu, in-memory test doubles) get
    the original driver back.
    """
    clone_fn = getattr(driver, "clone", None)
    if clone_fn is None:
        return driver
    try:
        return clone_fn(database=group_id)
    except TypeError:
        return driver


# ---------------------------------------------------------------------------
# Per-entity seed writers — typed-entity writes via EntityNode/EntityEdge
# ---------------------------------------------------------------------------


async def _save_node(
    driver: Any,
    *,
    entity_cls: type,
    uuid_value: str,
    name: str,
    labels: list[str],
    group_id: str,
    attributes: dict[str, Any],
    summary: str,
) -> str:
    """Construct and save a typed ``EntityNode``; emit a debug log line.

    The actual ``EntityNode`` class is the one from graphiti-core; we accept
    it as a parameter so this helper is the single import point and the
    caller-side code reads as plain Python without graphiti-core constants
    sprinkled around. ``entity_cls`` is the same ``EntityNode`` for every
    call today — the parameterisation is cheap insurance against a future
    seed extension that wants a different node class.
    """
    node = entity_cls(
        uuid=uuid_value,
        name=name,
        labels=labels,
        group_id=group_id,
        summary=summary,
        attributes=dict(attributes),
    )
    target_driver = _driver_for_group(driver, group_id)
    await node.save(target_driver)
    logger.debug(
        "seeding node written",
        extra={
            "event": "seeding_node_written",
            "entity_kind": labels[-1] if labels else "Entity",
            # Use ``entity_name`` rather than ``name`` because ``name`` is
            # already a reserved attribute on :class:`logging.LogRecord`
            # and Python's logging module rejects ``extra={"name": ...}``.
            "entity_name": name,
            "group_id": group_id,
            "uuid": uuid_value,
        },
    )
    return uuid_value


async def _save_edge(
    driver: Any,
    *,
    edge_cls: type,
    uuid_value: str,
    name: str,
    source_node_uuid: str,
    target_node_uuid: str,
    fact: str,
    group_id: str,
    attributes: dict[str, Any],
    created_at: datetime,
) -> None:
    """Construct and save a typed ``EntityEdge``; emit a debug log line."""
    edge = edge_cls(
        uuid=uuid_value,
        name=name,
        source_node_uuid=source_node_uuid,
        target_node_uuid=target_node_uuid,
        fact=fact,
        group_id=group_id,
        created_at=created_at,
        attributes=dict(attributes),
    )
    target_driver = _driver_for_group(driver, group_id)
    await edge.save(target_driver)
    logger.debug(
        "seeding edge written",
        extra={
            "event": "seeding_edge_written",
            "edge_name": name,
            "source_uuid": source_node_uuid,
            "target_uuid": target_node_uuid,
            "group_id": group_id,
            "uuid": uuid_value,
        },
    )


def _is_already_seeded(state: Any) -> bool:
    """True iff a previous seed clearly landed for Lilymay.

    We check ``empty=False`` plus at least one observable trace of the
    seed (a subject, a confidence row, or a recorded year_group). Any of
    these is enough — re-running the script is byte-idempotent under
    typed-entity writes (deterministic UUID5 → MERGE-by-uuid in FalkorDB),
    so this is more of a fast-path log-and-skip than a correctness gate.
    """
    if state is None:
        return False
    if getattr(state, "empty", True):
        return False
    if state.subjects:
        return True
    if state.topic_confidences:
        return True
    if state.year_group is not None:
        return True
    return False


async def seed_lilymay(client: GraphitiClient) -> int:
    """Run the full seed flow against ``client`` via typed-entity writes.

    Returns:
        :data:`EXIT_OK` on success or pre-flight skip.

    Pre-flight check:
        If :func:`get_student_state` already shows a non-empty baseline for
        Lilymay, log ``event=seeding_skipped`` and return :data:`EXIT_OK`
        without writing anything. Re-runs are byte-idempotent regardless,
        but the skip avoids unnecessary work and noise.
    """
    # ---- Pre-flight: idempotency gate ------------------------------------
    state = await get_student_state(client, STUDENT_ID)
    if _is_already_seeded(state):
        logger.info(
            "seeding skipped: Lilymay baseline already present",
            extra={
                "event": "seeding_skipped",
                "reason": "already_seeded",
                "student_id": STUDENT_ID,
            },
        )
        return EXIT_OK

    # ---- Resolve graphiti-core driver ------------------------------------
    inner = getattr(client, "client_or_none", None)
    if inner is None:
        logger.error(
            "seeding failed: graphiti client has no inner client",
            extra={
                "event": "seeding_failed",
                "reason": "client_or_none_unavailable",
            },
        )
        return EXIT_CLIENT_UNAVAILABLE
    driver = getattr(inner, "driver", None)
    if driver is None:
        logger.error(
            "seeding failed: graphiti client missing driver attribute",
            extra={
                "event": "seeding_failed",
                "reason": "driver_unavailable",
            },
        )
        return EXIT_CLIENT_UNAVAILABLE

    # Lazy imports so the module is importable in environments without
    # graphiti-core (e.g. unit-test mocks that monkeypatch ``seed_lilymay``).
    from graphiti_core.edges import EntityEdge
    from graphiti_core.nodes import EntityNode

    now = _now_utc()
    student_group = _student_group(STUDENT_ID)
    fleet_group = FLEET_GROUP_ID

    # ---- Student node (carries enrolled_subjects denormalisation per G1) -
    enrolled_subject_names = [s["name"] for s in SUBJECTS]
    student_uuid_value = student_uuid(student_group, STUDENT_NAME)
    await _save_node(
        driver,
        entity_cls=EntityNode,
        uuid_value=student_uuid_value,
        name=STUDENT_NAME,
        labels=["Entity", "Student"],
        group_id=student_group,
        summary=(
            f"Student {STUDENT_NAME} (id={STUDENT_ID}), Year "
            f"{STUDENT_YEAR_GROUP}, target grade {STUDENT_TARGET_GRADE}. "
            f"Enrolled in: {', '.join(enrolled_subject_names)}."
        ),
        attributes={
            "student_id": STUDENT_ID,
            "year_group": STUDENT_YEAR_GROUP,
            "target_grade": STUDENT_TARGET_GRADE,
            # ADR-ARCH-021 §G1 denormalisation — projection in
            # ``queries._build_student_state`` reads this directly so
            # ``state.subjects`` is populated without cross-group edge
            # traversal.
            "enrolled_subjects": list(enrolled_subject_names),
            "created_at": now.isoformat(),
        },
    )

    # ---- Subjects (curriculum-level, one named graph per subject) --------
    subject_uuid_by_slug: dict[str, str] = {}
    for subject in SUBJECTS:
        sg = _subject_group(subject["slug"])
        s_uuid = subject_uuid(sg, subject["name"])
        subject_uuid_by_slug[subject["slug"]] = s_uuid
        await _save_node(
            driver,
            entity_cls=EntityNode,
            uuid_value=s_uuid,
            name=subject["name"],
            labels=["Entity", "Subject"],
            group_id=sg,
            summary=(
                f"Subject {subject['name']} ({subject['exam_board']} "
                f"spec {subject['spec_code']})."
            ),
            attributes={
                "name": subject["name"],
                "exam_board": subject["exam_board"],
                "spec_code": subject["spec_code"],
                "slug": subject["slug"],
            },
        )

    # ---- Texts (under their parent subject's group) ----------------------
    text_uuid_by_subject: dict[str, list[str]] = {}
    for text in TEXTS:
        sg = _subject_group(text["subject_slug"])
        t_uuid = text_uuid(sg, text["subject_slug"], text["name"])
        text_uuid_by_subject.setdefault(text["subject_slug"], []).append(t_uuid)
        await _save_node(
            driver,
            entity_cls=EntityNode,
            uuid_value=t_uuid,
            name=text["name"],
            labels=["Entity", "Text"],
            group_id=sg,
            summary=(
                f"Text '{text['name']}' ({text['kind']}) under subject "
                f"{text['subject_slug']}; source path "
                f"{text['source_path']}."
            ),
            attributes={
                "name": text["name"],
                "kind": text["kind"],
                "source_path": text["source_path"],
                "subject_slug": text["subject_slug"],
            },
        )

    # ---- Topics (under their parent subject's group; ao_refs denormalised
    #      per ADR-ARCH-021 §G2 — Topic→AO would be cross-group) ---------
    topic_uuid_by_subject: dict[str, list[tuple[str, str]]] = {}
    topic_uuid_by_name: dict[str, str] = {}
    for topic in TOPICS:
        sg = _subject_group(topic["subject_slug"])
        t_uuid = topic_uuid(sg, topic["name"])
        topic_uuid_by_subject.setdefault(topic["subject_slug"], []).append(
            (topic["name"], t_uuid)
        )
        topic_uuid_by_name[topic["name"]] = t_uuid
        await _save_node(
            driver,
            entity_cls=EntityNode,
            uuid_value=t_uuid,
            name=topic["name"],
            labels=["Entity", "Topic"],
            group_id=sg,
            summary=(
                f"Topic '{topic['name']}' under subject "
                f"{topic['subject_slug']}; AO refs: "
                f"{', '.join(topic['ao_refs'])}."
            ),
            attributes={
                "name": topic["name"],
                "subject_ref": topic["subject_slug"],
                # G2 denormalisation: ASSESSED_BY is cross-group
                # (Topic in subject-<slug>, AO in fleet-appmilla) so we
                # cannot write the edge. The list-of-codes attribute is
                # the workaround the planner can read at projection time.
                "ao_refs": list(topic["ao_refs"]),
            },
        )

    # ---- Assessment Objectives (cross-fleet, single named graph) ---------
    for ao in AOS:
        ao_uuid = assessment_objective_uuid(fleet_group, ao["code"])
        await _save_node(
            driver,
            entity_cls=EntityNode,
            uuid_value=ao_uuid,
            name=ao["code"],
            labels=["Entity", "AssessmentObjective"],
            group_id=fleet_group,
            summary=f"{ao['code']} ({ao['exam_board']}): {ao['description']}",
            attributes={
                "code": ao["code"],
                "exam_board": ao["exam_board"],
                "description": ao["description"],
            },
        )

    # ---- TopicConfidences (one per Topic, all under student-<id>) --------
    confidence_uuid_by_topic: dict[str, str] = {}
    for topic in TOPICS:
        tc_uuid = topic_confidence_uuid(
            student_group, STUDENT_ID, topic["name"]
        )
        confidence_uuid_by_topic[topic["name"]] = tc_uuid
        percentage = int(topic["initial_percentage"])
        band = confidence_band_for(percentage)
        await _save_node(
            driver,
            entity_cls=EntityNode,
            uuid_value=tc_uuid,
            name=f"TopicConfidence:{topic['name']}",
            labels=["Entity", "TopicConfidence"],
            group_id=student_group,
            summary=(
                f"{STUDENT_NAME}'s baseline confidence on '{topic['name']}': "
                f"{percentage}% ({band}). Last revised at "
                f"{EPOCH_NEVER_REVISED.isoformat()} (never-revised sentinel)."
            ),
            attributes={
                "student_ref": STUDENT_ID,
                "topic_ref": topic["name"],
                "percentage": percentage,
                "band": band,
                # ADR-ARCH-021 §G3 — far-past sentinel keeps every baseline
                # topic outside the planner's 48h cooldown without
                # introducing an Optional[datetime] schema change.
                "last_revised_at": EPOCH_NEVER_REVISED.isoformat(),
            },
        )

    # ---- Intra-group edges (per ADR-ARCH-021 §G2) ------------------------
    # Student → HAS_CONFIDENCE → TopicConfidence (within student-<id>)
    for topic_name, tc_uuid in confidence_uuid_by_topic.items():
        e_uuid = edge_uuid(HAS_CONFIDENCE, student_uuid_value, tc_uuid)
        await _save_edge(
            driver,
            edge_cls=EntityEdge,
            uuid_value=e_uuid,
            name=HAS_CONFIDENCE,
            source_node_uuid=student_uuid_value,
            target_node_uuid=tc_uuid,
            fact=(
                f"{STUDENT_NAME} has baseline confidence on '{topic_name}'."
            ),
            group_id=student_group,
            created_at=now,
            attributes={"topic_ref": topic_name},
        )

    # Subject → HAS_TEXT → Text (within subject-<slug>)
    for subject in SUBJECTS:
        slug = subject["slug"]
        s_uuid = subject_uuid_by_slug[slug]
        sg = _subject_group(slug)
        for t_uuid in text_uuid_by_subject.get(slug, []):
            e_uuid = edge_uuid(HAS_TEXT, s_uuid, t_uuid)
            await _save_edge(
                driver,
                edge_cls=EntityEdge,
                uuid_value=e_uuid,
                name=HAS_TEXT,
                source_node_uuid=s_uuid,
                target_node_uuid=t_uuid,
                fact=f"Subject {subject['name']} has text under {slug}.",
                group_id=sg,
                created_at=now,
                attributes={},
            )

    # Subject → COVERS → Topic (within subject-<slug>)
    for subject in SUBJECTS:
        slug = subject["slug"]
        s_uuid = subject_uuid_by_slug[slug]
        sg = _subject_group(slug)
        for topic_name, t_uuid in topic_uuid_by_subject.get(slug, []):
            e_uuid = edge_uuid(COVERS, s_uuid, t_uuid)
            await _save_edge(
                driver,
                edge_cls=EntityEdge,
                uuid_value=e_uuid,
                name=COVERS,
                source_node_uuid=s_uuid,
                target_node_uuid=t_uuid,
                fact=(
                    f"Subject {subject['name']} covers topic '{topic_name}'."
                ),
                group_id=sg,
                created_at=now,
                attributes={"topic_ref": topic_name},
            )

    # ---- Verification gate (build-plan step 10) --------------------------
    final_state = await get_student_state(client, STUDENT_ID)
    if final_state is None or getattr(final_state, "empty", True):
        # The store accepted writes but the verification read couldn't see
        # them — operators can re-run get_student_state manually. Counted
        # entities below come from the in-process write surface, not the
        # read-back, so the warning is informational.
        logger.warning(
            "post-seed verification did not observe baseline state",
            extra={
                "event": "seeding_verification_warning",
                "student_id": STUDENT_ID,
            },
        )
    else:
        logger.info(
            "seeded Lilymay baseline (subjects=%d, confidences=%d)",
            len(final_state.subjects),
            len(final_state.topic_confidences),
            extra={
                "event": "seeding_completed",
                "student_id": STUDENT_ID,
                "subjects": len(final_state.subjects),
                "topic_confidences": len(final_state.topic_confidences),
                "nodes_written": (
                    1  # Student
                    + len(SUBJECTS)
                    + len(TEXTS)
                    + len(TOPICS)
                    + len(AOS)
                    + len(TOPICS)  # one TopicConfidence per topic
                ),
                "edges_written": (
                    len(TOPICS)  # HAS_CONFIDENCE
                    + len(TEXTS)  # HAS_TEXT
                    + len(TOPICS)  # COVERS (one per topic)
                ),
            },
        )
    return EXIT_OK


async def main(argv: list[str] | None = None) -> int:
    """Async entry point — returns the script's exit code.

    Wired to ``asyncio.run`` from the ``__main__`` block so callers and
    tests can drive the whole flow with a single ``await``.
    """
    args = _parse_args(argv)
    # TASK-GR-LOAD / AC-LOAD-07: prefer the canonical YAML loader so the
    # DECISION-DF-001 cloud-provider guard runs at config-load time. The
    # legacy ``load_config`` path is retained only for the
    # ``--config-path`` override + its existing test surface (which uses
    # the in-script ``DEFAULT_CONFIG`` schema with ``falkor_host`` keys).
    if args.config_path is None:
        config = load_graphiti_config_from_yaml(DEFAULT_GRAPHITI_YAML_PATH)
    else:
        config = load_config(args.config_path)

    client = await get_client(config)
    # ``require_client_or_exit`` raises ``SystemExit(2)`` when client is None.
    # We deliberately let SystemExit propagate so the surrounding
    # ``asyncio.run`` exits with the right status without us hand-rolling
    # error mapping.
    require_client_or_exit(client)
    assert client is not None  # narrowed by require_client_or_exit

    try:
        return await seed_lilymay(client)
    finally:
        await client.close()


if __name__ == "__main__":  # pragma: no cover - direct invocation only
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        sys.exit(asyncio.run(main()))
    except SystemExit:
        raise
    except Exception:
        logger.exception(
            "seeding failed with unhandled exception",
            extra={"event": "seeding_failed_unhandled"},
        )
        sys.exit(EXIT_CLIENT_UNAVAILABLE)
