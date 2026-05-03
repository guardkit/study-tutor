"""Lilymay baseline seeding script (TASK-GSM-006).

One-off scaffolding script that populates Lilymay's baseline learner profile
into the Synology FalkorDB so the Phase-1 tutor stack has a real student to
plan against on day 1. Per ``phase-1-scope.md §FEAT-PH1-001`` (Lilymay
seeding) and the build plan's Saturday-evening steps 9–11, running this
script end-to-end is the integration gate that closes FEAT-1773.

Usage
-----

::

    python scripts/seed_student_model.py [--config-path PATH]

When ``--config-path`` is omitted the script falls back to the canonical
Phase-1 Synology defaults (whitestocks FalkorDB + GB10 vLLM embedder).
A YAML config may override any field of
:class:`~study_tutor.knowledge.graphiti_client.GraphitiConnectionConfig`.

Exit-code contract
------------------

- ``0`` — fresh seed succeeded **or** pre-flight detected an existing
  baseline and skipped (idempotent re-run).
- ``2`` — Graphiti / FalkorDB unreachable (``get_client`` returned ``None``).
  Seeding is **not** a degradation path: it requires a live store. A
  structured log line ``event=seeding_failed, reason=client_unavailable``
  is emitted before exit.
- ``3`` — at least one in-flight write was abandoned at shutdown grace.
  The structured log line includes the abandoned count.

Architectural invariants honoured
---------------------------------

- **CC-13 single-call-site**: every seed write is dispatched through
  :meth:`~study_tutor.knowledge.async_write.GraphitiWriteHelper.schedule_write`
  with ``flush_id="SEED"``. The script never calls ``add_episode`` directly.
- **Group-id discipline**: every write uses constants from
  :mod:`study_tutor.knowledge.student_model` (``student:lilymay``,
  ``subject:<slug>``, ``fleet:appmilla``) — never bare string literals.
- **Idempotency**: pre-flight ``get_student_state(client, "lilymay")``
  short-circuits on a non-empty existing baseline.
- **Verification gate**: post-write, the same ``get_student_state`` call is
  used to confirm the seed actually landed. The script logs a one-line
  summary of what was seeded.

Manual verification
-------------------

After running, drop into Claude Desktop with the Graphiti MCP wired up and
issue::

    search_nodes(query="Lilymay", group_ids=["student-lilymay"])

The Student entity should be returned with the attributes seeded below.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from study_tutor.knowledge.async_write import GraphitiWriteHelper
from study_tutor.knowledge.episodes import (
    SeedBaselineEpisode,
    TopicConfidenceUpdatedEpisode,
)
from study_tutor.knowledge.graphiti_client import (
    DEFAULT_GRAPHITI_YAML_PATH,
    GraphitiClient,
    GraphitiConnectionConfig,
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.queries import get_student_state
from study_tutor.knowledge.student_model import (
    FLEET_GROUP_ID,
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
EXIT_PENDING_WRITES_ABANDONED: int = 3


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
            "Graphiti / FalkorDB store. Idempotent on re-run."
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
# Per-entity seed writers — every one routes through helper.schedule_write
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    """Return the current UTC instant. Hoisted so tests can monkeypatch."""
    return datetime.now(timezone.utc)


def _student_group(student_id: str) -> str:
    return f"{STUDENT_GROUP_PREFIX}{student_id}"


def _subject_group(slug: str) -> str:
    return f"{SUBJECT_GROUP_PREFIX}{slug}"


def _seed_student(helper: GraphitiWriteHelper, *, now: datetime) -> None:
    """Schedule the Student entity (Lilymay) baseline write."""
    helper.schedule_write(
        group_ids=[_student_group(STUDENT_ID)],
        episode=SeedBaselineEpisode(
            entity_kind="student",
            entity_name=STUDENT_NAME,
            description=(
                f"Student {STUDENT_NAME} (id={STUDENT_ID}), Year "
                f"{STUDENT_YEAR_GROUP}, target grade "
                f"{STUDENT_TARGET_GRADE}. Baseline created at "
                f"{now.isoformat()}."
            ),
        ),
        flush_id="SEED",
    )


def _seed_subjects(helper: GraphitiWriteHelper) -> None:
    """Schedule a Subject baseline write per enrolled subject."""
    for subject in SUBJECTS:
        helper.schedule_write(
            group_ids=[_subject_group(subject["slug"])],
            episode=SeedBaselineEpisode(
                entity_kind="subject",
                entity_name=subject["name"],
                description=(
                    f"Subject {subject['name']} ({subject['exam_board']} "
                    f"spec {subject['spec_code']})."
                ),
            ),
            flush_id="SEED",
        )


def _seed_texts(helper: GraphitiWriteHelper) -> None:
    """Schedule a Text baseline write per curriculum text."""
    for text in TEXTS:
        helper.schedule_write(
            group_ids=[_subject_group(text["subject_slug"])],
            episode=SeedBaselineEpisode(
                entity_kind="text",
                entity_name=text["name"],
                description=(
                    f"Text '{text['name']}' ({text['kind']}) under subject "
                    f"{text['subject_slug']}; source path "
                    f"{text['source_path']}."
                ),
            ),
            flush_id="SEED",
        )


def _seed_assessment_objectives(helper: GraphitiWriteHelper) -> None:
    """Schedule a SeedBaselineEpisode for each AQA AO (AC-008)."""
    for ao in AOS:
        helper.schedule_write(
            # AOs are curriculum-level, not per-student — write under the
            # fleet group so they're shared across all future students.
            group_ids=[FLEET_GROUP_ID],
            episode=SeedBaselineEpisode(
                entity_kind="assessment_objective",
                entity_name=ao["code"],
                description=(
                    f"{ao['code']} ({ao['exam_board']}): {ao['description']}"
                ),
            ),
            flush_id="SEED",
        )


def _seed_topics(helper: GraphitiWriteHelper) -> None:
    """Schedule a Topic baseline write per Phase-1 topic."""
    for topic in TOPICS:
        helper.schedule_write(
            group_ids=[_subject_group(topic["subject_slug"])],
            episode=SeedBaselineEpisode(
                entity_kind="topic",
                entity_name=topic["name"],
                description=(
                    f"Topic '{topic['name']}' under subject "
                    f"{topic['subject_slug']}; AO refs: "
                    f"{', '.join(topic['ao_refs'])}."
                ),
            ),
            flush_id="SEED",
        )


def _seed_initial_topic_confidences(
    helper: GraphitiWriteHelper, *, now: datetime
) -> None:
    """Emit one ``TopicConfidenceUpdatedEpisode`` per topic (AC-006, AC-007).

    Every initial confidence is committed via the shared async helper with
    ``flush_id="SEED"`` — never a raw ``add_episode`` call.
    """
    for topic in TOPICS:
        new_band = confidence_band_for(int(topic["initial_percentage"]))
        helper.schedule_write(
            group_ids=[_student_group(STUDENT_ID)],
            episode=TopicConfidenceUpdatedEpisode(
                student_id=STUDENT_ID,
                topic_name=topic["name"],
                # Baseline transition: from "no observation" (modelled as
                # the same band at 0%) into the human-estimated value.
                previous_band=new_band,
                new_band=new_band,
                previous_percentage=0,
                new_percentage=int(topic["initial_percentage"]),
                observed_at=now,
                triggering_session_id=None,
            ),
            flush_id="SEED",
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


#: Env var override for the per-batch drain budget used by
#: :func:`seed_lilymay`. Sized for seed-time bulk loads (one-off, ~25
#: writes) rather than the 30s handler-tear-down grace exposed by
#: :data:`async_write.DEFAULT_SHUTDOWN_GRACE_SEC`.
_SEED_BATCH_DRAIN_ENV: str = "GRAPHITI_SEED_BATCH_DRAIN_SEC"

#: Default seed-time drain budget per entity-type batch (seconds).
#: 600s comfortably covers a 6-episode batch at vLLM extraction
#: wall-time of ~30-90s per episode.
DEFAULT_SEED_BATCH_DRAIN_SEC: int = 600


def _resolve_seed_batch_drain_sec() -> int:
    """Resolve the per-batch drain budget from env or default.

    Mirrors the parse-and-warn shape of
    :func:`async_write._resolve_default_grace_sec`: a non-positive or
    non-integer value falls back to the default with a structured warning
    so misconfiguration is observable in production logs.
    """
    raw = os.environ.get(_SEED_BATCH_DRAIN_ENV)
    if raw is None:
        return DEFAULT_SEED_BATCH_DRAIN_SEC
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "ignoring non-integer %s=%r; using default %d",
            _SEED_BATCH_DRAIN_ENV,
            raw,
            DEFAULT_SEED_BATCH_DRAIN_SEC,
            extra={
                "event": "seeding_batch_drain_env_invalid",
                "raw_value": raw,
                "fallback": DEFAULT_SEED_BATCH_DRAIN_SEC,
            },
        )
        return DEFAULT_SEED_BATCH_DRAIN_SEC
    if value <= 0:
        logger.warning(
            "ignoring non-positive %s=%d; using default %d",
            _SEED_BATCH_DRAIN_ENV,
            value,
            DEFAULT_SEED_BATCH_DRAIN_SEC,
            extra={
                "event": "seeding_batch_drain_env_invalid",
                "raw_value": raw,
                "fallback": DEFAULT_SEED_BATCH_DRAIN_SEC,
            },
        )
        return DEFAULT_SEED_BATCH_DRAIN_SEC
    return value


def _is_already_seeded(state: Any) -> bool:
    """True iff a previous seed clearly landed for Lilymay.

    We check ``empty=False`` plus at least one observable trace of the
    seed (a subject, a confidence row, or a recorded year_group). Any of
    these is enough — re-running the script is a no-op once the baseline
    is detected.
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


async def seed_lilymay(
    client: GraphitiClient,
    helper: GraphitiWriteHelper,
) -> int:
    """Run the full seed flow against ``client`` via ``helper``.

    Returns:
        One of :data:`EXIT_OK` / :data:`EXIT_PENDING_WRITES_ABANDONED`.

    Pre-flight check (AC-003):
        If ``get_student_state`` already shows a non-empty baseline for
        Lilymay, log ``event=seeding_skipped`` and return :data:`EXIT_OK`
        without writing anything.
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

    # ---- Schedule every write through the shared helper ------------------
    #
    # TASK-GR-SEED (2026-05-02): drain between each entity-type batch, not
    # just at the end. Background: schedule_write is fire-and-forget by
    # design (CC-13 / ADR-ARCH-019 handler-budget contract), so calling all
    # six batch helpers without intermediate drains dispatches all ~25
    # episodes concurrently. Each episode in turn triggers ~3-4 internal
    # graphiti-core LLM extraction calls — multiplied across 25 in-flight
    # episodes that's ~75-100 concurrent vLLM requests, which exceeds the
    # GB10 vLLM queue cap and 429-rate-limits every write. Draining between
    # batches keeps the in-flight count to one batch's worth at a time
    # (≤6 episodes), which fits comfortably inside vLLM's queue while
    # preserving the seed's existing CC-13 invariants — every write still
    # routes through helper.schedule_write under flush_id="SEED", and the
    # final drain still runs as the catch-all.
    #
    # The intermediate drains use a generous per-batch timeout (the
    # GRAPHITI_SEED_BATCH_DRAIN_SEC env var, default 600s) because vLLM
    # extraction wall-time per episode is highly variable (5-90s) and the
    # 30s default shutdown_grace is sized for handler-budget tear-down,
    # not seed-time bulk loads.
    now = _now_utc()
    batch_drain_sec = _resolve_seed_batch_drain_sec()

    async def _drain_batch(label: str) -> None:
        succeeded, abandoned = await helper.drain(timeout_sec=batch_drain_sec)
        logger.info(
            "seeding batch drained",
            extra={
                "event": "seeding_batch_drained",
                "batch": label,
                "succeeded": succeeded,
                "abandoned": abandoned,
            },
        )
        if abandoned > 0:
            # Surface a hard-fail on the first batch that loses writes
            # rather than soldiering on through five more batches that
            # will drop the same way.
            raise RuntimeError(
                f"seeding batch {label!r} abandoned {abandoned} of "
                f"{succeeded + abandoned} writes after {batch_drain_sec}s "
                "drain — investigate vLLM queue saturation before retrying"
            )

    _seed_student(helper, now=now)
    await _drain_batch("student")
    _seed_subjects(helper)
    await _drain_batch("subjects")
    _seed_texts(helper)
    await _drain_batch("texts")
    _seed_assessment_objectives(helper)
    await _drain_batch("assessment_objectives")
    _seed_topics(helper)
    await _drain_batch("topics")
    _seed_initial_topic_confidences(helper, now=now)

    # ---- Drain in-flight tasks before exit -------------------------------
    succeeded, abandoned = await helper.drain(timeout_sec=batch_drain_sec)
    if abandoned > 0:
        logger.error(
            "seeding pending writes abandoned at shutdown",
            extra={
                "event": "seeding_pending_writes_abandoned",
                "abandoned": abandoned,
                "succeeded": succeeded,
            },
        )
        return EXIT_PENDING_WRITES_ABANDONED

    # ---- Verification gate (build-plan step 10) --------------------------
    final_state = await get_student_state(client, STUDENT_ID)
    if final_state is None or getattr(final_state, "empty", True):
        # The store accepted writes but the verification read couldn't see
        # them — this is unusual and worth flagging, but we still exit 0
        # because the writes themselves succeeded (drain reported zero
        # abandoned). Operators can re-run get_student_state manually.
        logger.warning(
            "post-seed verification did not observe baseline state",
            extra={
                "event": "seeding_verification_warning",
                "student_id": STUDENT_ID,
            },
        )
    else:
        logger.info(
            "seeded Lilymay baseline (subjects=%d, confidences=%d, "
            "succeeded_writes=%d)",
            len(final_state.subjects),
            len(final_state.topic_confidences),
            succeeded,
            extra={
                "event": "seeding_completed",
                "student_id": STUDENT_ID,
                "subjects": len(final_state.subjects),
                "topic_confidences": len(final_state.topic_confidences),
                "succeeded_writes": succeeded,
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

    helper = GraphitiWriteHelper(client.client_or_none)
    try:
        return await seed_lilymay(client, helper)
    finally:
        # Defensive: even if seed_lilymay returned early or raised, drain
        # any tasks the helper might still be tracking before we close the
        # underlying client. Idempotent — drain on an empty helper is a
        # cheap no-op tuple ``(0, 0)``.
        await helper.drain()
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
