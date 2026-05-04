"""Pydantic entity and relationship schema for the Graphiti student model.

FEAT-1773 / TASK-GSM-001 — declarative type definitions consumed by every
downstream slice of the student model (episode types, async write helper,
query helpers, seeding script). This module is intentionally stack-agnostic:
it does **not** import ``graphiti-core``. It only defines the seven entity
classes, six relationship-name constants, three group-id constants, and the
``confidence_band_for`` helper.

Entities (per ``phase-1-scope.md §FEAT-PH1-001`` table):

- ``Student`` — single learner identity (Phase 1 ships with Lilymay only).
- ``Subject`` — GCSE subject, e.g. AQA 8702 English Literature.
- ``Text`` — a literary text (primary, secondary, or context source).
- ``Topic`` — a revisable unit within a subject or text; carries AO refs.
- ``AssessmentObjective`` — AO1..AO6 with per-exam-board descriptions.
- ``Misconception`` — a documented misunderstanding observed in a session.
- ``TopicConfidence`` — per-student, per-topic confidence level + band.

Relationships (``Source RELATIONSHIP Target`` semantics):

- ``Student STUDIES Subject``
- ``Student WORKING_ON Text``
- ``Subject HAS_TEXT Text``
- ``Text COVERS Topic``
- ``Topic ASSESSED_BY AssessmentObjective``
- ``Student HAS_CONFIDENCE TopicConfidence`` — carries percentage + band.

Group-id conventions (per ``phase-1-scope.md §FEAT-PH1-001`` "Group IDs",
adapted for graphiti-core 0.29's ``[A-Za-z0-9_-]``-only validator):

- ``student-<student_id>`` — student-specific episodes/entities.
- ``subject-<subject_slug>`` — curriculum-level (not per-student).
- ``fleet-appmilla`` — fleet-wide knowledge scope (rare writes from tutor).

Cross-repo divergence (per ASSUM-008):
    study-tutor's scope doc originally specified ``fleet:appmilla``
    (colon-separated). graphiti-core 0.29's ``GroupIdValidationError``
    rejects colons so the runtime constant migrated to
    ``fleet-appmilla``. The sibling specialist-agent repo uses
    ``appmilla-fleet`` (different word order). The split is intentional
    and documented here so future cross-repo features that share group
    identifiers know they must reconcile the convention. Do not
    "harmonise" silently.

Confidence bands (per ASSUM-001, confirmed):
    0–39 struggling · 40–69 developing · 70–89 secure · 90–100 mastered.
    See :func:`confidence_band_for` for the boundary-correct mapping.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Group-id constants
# ---------------------------------------------------------------------------

#: Prefix for per-student group identifiers, producing
#: ``student-<student_id>``. graphiti-core 0.29's
#: ``GroupIdValidationError`` rejects any character outside
#: ``[A-Za-z0-9_-]``, so the original ``phase-1-scope.md`` ``student:``
#: convention had to drop the colon at integration time. The dash form
#: keeps the "namespace then payload" readability the colon gave us.
STUDENT_GROUP_PREFIX: str = "student-"

#: Prefix for per-subject (curriculum-level) group identifiers, producing
#: ``subject-<subject_slug>``. Same dash-vs-colon constraint as
#: ``STUDENT_GROUP_PREFIX``.
SUBJECT_GROUP_PREFIX: str = "subject-"

#: Fleet-wide knowledge scope used for cross-product/cross-role writes.
#:
#: NOTE — cross-repo divergence: specialist-agent uses ``appmilla-fleet``
#: (no colon). study-tutor's ``phase-1-scope.md`` originally specified
#: ``fleet:appmilla`` but graphiti-core 0.29's group-id validator rejects
#: colons (``[A-Za-z0-9_-]`` only) so the runtime constant is the
#: dash-form ``fleet-appmilla``. See the module docstring and ASSUM-008.
FLEET_GROUP_ID: str = "fleet-appmilla"


# ---------------------------------------------------------------------------
# Relationship name constants
# ---------------------------------------------------------------------------

#: Student STUDIES Subject — Lilymay's enrolled subjects.
STUDIES: str = "STUDIES"

#: Student WORKING_ON Text — the text currently being revised.
WORKING_ON: str = "WORKING_ON"

#: Subject HAS_TEXT Text — texts that fall under a subject's curriculum.
HAS_TEXT: str = "HAS_TEXT"

#: Text COVERS Topic — topics revisable from a given text.
COVERS: str = "COVERS"

#: Topic ASSESSED_BY AssessmentObjective — which AOs a topic exercises.
ASSESSED_BY: str = "ASSESSED_BY"

#: Student HAS_CONFIDENCE TopicConfidence — per-topic mastery state.
HAS_CONFIDENCE: str = "HAS_CONFIDENCE"


# ---------------------------------------------------------------------------
# Sentinel timestamps (ADR-ARCH-021 §G3)
# ---------------------------------------------------------------------------

#: Sentinel timestamp for ``TopicConfidence.last_revised_at`` baseline writes.
#:
#: A baseline TopicConfidence has, by construction, never been revised — but
#: the field is non-Optional and the planner cooldown logic compares it
#: against ``now()``. Writing ``now()`` would put every baseline topic
#: inside the 24h cooldown and break TASK-GSM-009 AC-03 (planner must have
#: bands to plan against on day 1). The far-past sentinel keeps the topic
#: comfortably outside the 48h stale-bonus boundary forever (until a real
#: revision overwrites this value with the actual revised-at timestamp).
#:
#: Anyone reading ``last_revised_at = 1970-01-01`` in raw graph queries
#: should follow this constant back to ADR-ARCH-021 §G3.
EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Confidence-band thresholds and helper (ASSUM-001)
# ---------------------------------------------------------------------------

ConfidenceBand = Literal["struggling", "developing", "secure", "mastered"]

# Band thresholds inclusive of the lower bound, per ASSUM-001:
#   0–39 struggling, 40–69 developing, 70–89 secure, 90–100 mastered.
_BAND_THRESHOLDS: tuple[tuple[int, ConfidenceBand], ...] = (
    (90, "mastered"),
    (70, "secure"),
    (40, "developing"),
    (0, "struggling"),
)


def confidence_band_for(percentage: int) -> ConfidenceBand:
    """Map an integer percentage (0–100) to its confidence band.

    Boundaries (per ASSUM-001):

    - ``0..39``  → ``"struggling"``
    - ``40..69`` → ``"developing"``
    - ``70..89`` → ``"secure"``
    - ``90..100`` → ``"mastered"``

    Args:
        percentage: An integer percentage in the inclusive range ``[0, 100]``.

    Returns:
        The confidence-band literal for the supplied percentage.

    Raises:
        ValueError: If ``percentage`` is outside ``[0, 100]``.
    """
    if not 0 <= percentage <= 100:
        raise ValueError(
            f"percentage must be in [0, 100]; got {percentage!r}",
        )
    for threshold, band in _BAND_THRESHOLDS:
        if percentage >= threshold:
            return band
    # Unreachable: the final threshold (0) always matches a non-negative int.
    raise AssertionError("confidence_band_for: unreachable branch")


# ---------------------------------------------------------------------------
# Entity classes (Pydantic v2 BaseModel subclasses)
# ---------------------------------------------------------------------------

#: ``Text.kind`` discriminator: which corpus tier a text belongs to. Mirrors
#: the source-typed corpus layout from FEAT-PH1-004 (primary / secondary /
#: context).
TextKind = Literal["primary", "secondary", "context"]


class _StudentModelBase(BaseModel):
    """Shared Pydantic configuration for all student-model entities.

    Forbidding extras keeps Graphiti episode payloads strictly typed; mutating
    instances after construction is fine for in-process aggregation but the
    serialised form is what reaches Graphiti.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)


class Student(_StudentModelBase):
    """A single learner enrolled against an exam specification."""

    student_id: str = Field(..., description="Stable slug, e.g. 'lilymay'.")
    name: str = Field(..., description="Display name.")
    year_group: int = Field(
        ...,
        ge=7,
        le=13,
        description="UK secondary year group (7–13).",
    )
    target_grade: str = Field(
        ...,
        description="GCSE target grade (e.g. '7', '8', '9').",
    )
    created_at: datetime = Field(
        ...,
        description="When this student record was created (UTC).",
    )


class Subject(_StudentModelBase):
    """A GCSE subject keyed by exam board + spec code."""

    name: str = Field(
        ...,
        description="Human-readable subject name, e.g. 'English Literature'.",
    )
    exam_board: str = Field(
        ...,
        description="Exam board, e.g. 'AQA', 'Edexcel', 'OCR'.",
    )
    spec_code: str = Field(
        ...,
        description="Specification code, e.g. '8700' (Lang) or '8702' (Lit).",
    )


class Text(_StudentModelBase):
    """A specific literary or context text used in study."""

    name: str = Field(..., description="Title, e.g. 'Macbeth'.")
    kind: TextKind = Field(
        ...,
        description="Corpus tier: primary / secondary / context.",
    )
    source_path: str = Field(
        ...,
        description=(
            "Filesystem-relative path under ``domains/<subject>/sources/`` "
            "or other locator."
        ),
    )


class Topic(_StudentModelBase):
    """A revisable unit within a subject or text."""

    name: str = Field(..., description="Topic name, e.g. 'Witches Act 1'.")
    subject_ref: str = Field(
        ...,
        description="Reference to the parent Subject's spec_code or slug.",
    )
    ao_refs: list[str] = Field(
        default_factory=list,
        description=(
            "Codes of AssessmentObjective entities this topic exercises "
            "(e.g. ['AO1', 'AO2'])."
        ),
    )


class AssessmentObjective(_StudentModelBase):
    """An AQA/Edexcel/OCR Assessment Objective (AO1..AO6)."""

    code: str = Field(
        ...,
        pattern=r"^AO[1-6]$",
        description="AO code in the form 'AO1'..'AO6'.",
    )
    description: str = Field(
        ...,
        description="What the AO assesses on this exam board.",
    )
    exam_board: str = Field(
        ...,
        description="Exam board, e.g. 'AQA' (weightings differ across boards).",
    )


class Misconception(_StudentModelBase):
    """A documented misunderstanding observed in past sessions."""

    text: str = Field(
        ...,
        description="Free-text description of the misconception.",
    )
    topic_ref: str = Field(
        ...,
        description="Topic name or slug this misconception attaches to.",
    )
    observed_at: datetime = Field(
        ...,
        description="When the misconception was observed (UTC).",
    )
    confidence_band_at_observation: ConfidenceBand = Field(
        ...,
        description=(
            "The student's confidence band on this topic at the moment the "
            "misconception was observed."
        ),
    )


class TopicConfidence(_StudentModelBase):
    """Per-student, per-topic confidence percentage + band."""

    student_ref: str = Field(
        ...,
        description="Student id this confidence belongs to.",
    )
    topic_ref: str = Field(
        ...,
        description="Topic name or slug this confidence applies to.",
    )
    percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence as an integer percentage in [0, 100].",
    )
    band: ConfidenceBand = Field(
        ...,
        description=(
            "Pre-computed band; should match ``confidence_band_for(percentage)``."
        ),
    )
    last_revised_at: datetime = Field(
        ...,
        description="When the topic was most recently revised (UTC).",
    )


__all__ = [
    # Entities
    "Student",
    "Subject",
    "Text",
    "Topic",
    "AssessmentObjective",
    "Misconception",
    "TopicConfidence",
    # Relationship constants
    "STUDIES",
    "WORKING_ON",
    "HAS_TEXT",
    "COVERS",
    "ASSESSED_BY",
    "HAS_CONFIDENCE",
    # Group-id constants
    "STUDENT_GROUP_PREFIX",
    "SUBJECT_GROUP_PREFIX",
    "FLEET_GROUP_ID",
    # Confidence helper
    "ConfidenceBand",
    "confidence_band_for",
    # Sentinel timestamps
    "EPOCH_NEVER_REVISED",
    # Other type aliases
    "TextKind",
]
