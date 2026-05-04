"""Unit tests for :mod:`study_tutor.knowledge.seed_uuids` (TASK-GSM-009 AC-12).

The helpers derive deterministic UUID5s for every entity class the typed-
entity seed writes. These tests pin two properties:

1. **Determinism** — same inputs always produce the same UUID across runs,
   which is what makes the seed byte-idempotent (graphiti-core's FalkorDB
   driver MERGEs by uuid in ``EntityNode.save``).
2. **Collision-freedom** — across the entity types the Phase-1 seed
   actually writes today, no two distinct identity keys collapse to the
   same UUID.

The UUID5 + ``NAMESPACE_OID`` choice is itself enough to make collisions
astronomically unlikely; these tests are about catching helper-side bugs
(e.g. a missing prefix, a swapped argument order) rather than birthday-
problem statistics.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from study_tutor.knowledge.seed_uuids import (
    assessment_objective_uuid,
    edge_uuid,
    misconception_uuid,
    student_uuid,
    subject_uuid,
    text_uuid,
    topic_confidence_uuid,
    topic_uuid,
)


# ---------------------------------------------------------------------------
# Determinism — same inputs → same UUID across calls
# ---------------------------------------------------------------------------


def test_student_uuid_is_deterministic() -> None:
    a = student_uuid("student-lilymay", "Lilymay")
    b = student_uuid("student-lilymay", "Lilymay")
    assert a == b


def test_subject_uuid_is_deterministic() -> None:
    a = subject_uuid("subject-english-literature", "English Literature")
    b = subject_uuid("subject-english-literature", "English Literature")
    assert a == b


def test_text_uuid_is_deterministic() -> None:
    a = text_uuid("subject-english-literature", "english-literature", "Macbeth")
    b = text_uuid("subject-english-literature", "english-literature", "Macbeth")
    assert a == b


def test_topic_uuid_is_deterministic() -> None:
    a = topic_uuid("subject-english-literature", "Macbeth's witches")
    b = topic_uuid("subject-english-literature", "Macbeth's witches")
    assert a == b


def test_assessment_objective_uuid_is_deterministic() -> None:
    a = assessment_objective_uuid("fleet-appmilla", "AO1")
    b = assessment_objective_uuid("fleet-appmilla", "AO1")
    assert a == b


def test_topic_confidence_uuid_is_deterministic() -> None:
    a = topic_confidence_uuid(
        "student-lilymay", "lilymay", "Macbeth's witches"
    )
    b = topic_confidence_uuid(
        "student-lilymay", "lilymay", "Macbeth's witches"
    )
    assert a == b


def test_misconception_uuid_is_deterministic() -> None:
    observed_at = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
    a = misconception_uuid("student-lilymay", "Macbeth's witches", observed_at)
    b = misconception_uuid("student-lilymay", "Macbeth's witches", observed_at)
    assert a == b


def test_edge_uuid_is_deterministic() -> None:
    a = edge_uuid("HAS_CONFIDENCE", "src-uuid", "tgt-uuid")
    b = edge_uuid("HAS_CONFIDENCE", "src-uuid", "tgt-uuid")
    assert a == b


# ---------------------------------------------------------------------------
# Collision-freedom across the seeded entity surface
# ---------------------------------------------------------------------------


def test_distinct_entity_types_with_same_name_do_not_collide() -> None:
    """A Subject and a Topic with the same ``name`` must not collide.

    The class-name prefix in the identity key (``Subject:`` vs ``Topic:``)
    is what guarantees this; the test guards against someone refactoring
    the prefix away.
    """
    same_name = "English Literature"
    s = subject_uuid("subject-english-literature", same_name)
    t = topic_uuid("subject-english-literature", same_name)
    assert s != t


def test_distinct_groups_for_same_entity_do_not_collide() -> None:
    """Two Students with the same display name in different groups differ."""
    a = student_uuid("student-lilymay", "Lilymay")
    b = student_uuid("student-other", "Lilymay")
    assert a != b


def test_text_uuid_disambiguates_by_subject_slug() -> None:
    """Same text name under two subjects must not collide (the reason
    the Text key includes ``subject_slug``).
    """
    a = text_uuid("subject-english-literature", "english-literature", "Notes")
    b = text_uuid("subject-english-language", "english-language", "Notes")
    assert a != b


def test_topic_confidence_uuid_per_student_per_topic() -> None:
    """Two students with confidence on the same topic must not collide."""
    a = topic_confidence_uuid(
        "student-lilymay", "lilymay", "Macbeth's witches"
    )
    b = topic_confidence_uuid(
        "student-other", "other", "Macbeth's witches"
    )
    assert a != b


def test_edge_uuid_distinguishes_source_target_pairs() -> None:
    """Edges between different (source, target) pairs must not collide."""
    a = edge_uuid("HAS_CONFIDENCE", "src-1", "tgt-1")
    b = edge_uuid("HAS_CONFIDENCE", "src-1", "tgt-2")
    c = edge_uuid("HAS_CONFIDENCE", "src-2", "tgt-1")
    d = edge_uuid("COVERS", "src-1", "tgt-1")
    assert len({a, b, c, d}) == 4


def test_full_phase_1_seed_surface_collision_free() -> None:
    """Generate the full Phase-1 seed UUID surface and assert no collisions.

    Mirrors the entity set the typed-entity seed actually writes in the
    Lilymay baseline (one Student, two Subjects, four Texts, six Topics,
    six AOs, six TopicConfidences, plus the intra-group edges
    HAS_CONFIDENCE / COVERS / HAS_TEXT). If any helper accidentally
    derives a duplicate uuid, this test catches it.
    """
    student_group = "student-lilymay"
    fleet_group = "fleet-appmilla"
    lit_group = "subject-english-literature"
    lang_group = "subject-english-language"

    uuids: list[str] = []

    # 1 Student
    student = student_uuid(student_group, "Lilymay")
    uuids.append(student)

    # 2 Subjects
    lit_subject = subject_uuid(lit_group, "English Literature")
    lang_subject = subject_uuid(lang_group, "English Language")
    uuids += [lit_subject, lang_subject]

    # 4 Texts (all under English Lit in Phase 1)
    text_names = [
        "Macbeth",
        "A Christmas Carol",
        "Power and Conflict poetry cluster",
        "York Notes: Macbeth (study guide)",
    ]
    text_ids = [
        text_uuid(lit_group, "english-literature", n) for n in text_names
    ]
    uuids += text_ids

    # 6 Topics (5 under Lit + 1 under Lang)
    lit_topic_names = [
        "Macbeth's witches",
        "Power and Conflict: Ozymandias themes",
        "Lady Macbeth's ambition",
        "Scrooge's redemption arc",
        "Macbeth: ambition and guilt",
    ]
    lit_topics = [topic_uuid(lit_group, n) for n in lit_topic_names]
    lang_topics = [topic_uuid(lang_group, "Metaphor identification")]
    uuids += lit_topics + lang_topics

    # 6 AOs (AO1..AO6)
    ao_codes = ["AO1", "AO2", "AO3", "AO4", "AO5", "AO6"]
    ao_ids = [assessment_objective_uuid(fleet_group, c) for c in ao_codes]
    uuids += ao_ids

    # 6 TopicConfidences (one per topic, all under student-lilymay)
    confidences = [
        topic_confidence_uuid(student_group, "lilymay", n)
        for n in lit_topic_names + ["Metaphor identification"]
    ]
    uuids += confidences

    # Edges: 6 HAS_CONFIDENCE (Student → TopicConfidence)
    has_confidence_edges = [edge_uuid("HAS_CONFIDENCE", student, c) for c in confidences]
    uuids += has_confidence_edges

    # Edges: HAS_TEXT (Subject → Text), 4 of them under Lit
    has_text_edges = [edge_uuid("HAS_TEXT", lit_subject, t) for t in text_ids]
    uuids += has_text_edges

    # Edges: COVERS (Subject → Topic) — 5 lit + 1 lang
    covers_edges = [edge_uuid("COVERS", lit_subject, t) for t in lit_topics]
    covers_edges += [edge_uuid("COVERS", lang_subject, t) for t in lang_topics]
    uuids += covers_edges

    # Collision check
    assert len(set(uuids)) == len(uuids), (
        f"UUID collision detected: {len(uuids) - len(set(uuids))} duplicates"
    )


# ---------------------------------------------------------------------------
# Regression: helpers always produce a UUID-shaped string
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        lambda: student_uuid("student-x", "X"),
        lambda: subject_uuid("subject-x", "X"),
        lambda: text_uuid("subject-x", "x", "X"),
        lambda: topic_uuid("subject-x", "X"),
        lambda: assessment_objective_uuid("fleet-appmilla", "AO1"),
        lambda: topic_confidence_uuid("student-x", "x", "X"),
        lambda: misconception_uuid(
            "student-x",
            "X",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        lambda: edge_uuid("REL", "a", "b"),
    ],
)
def test_helper_returns_uuid_shaped_string(factory: object) -> None:
    """The helpers produce a 36-char UUID (8-4-4-4-12 hex with hyphens)."""
    value: str = factory()  # type: ignore[operator]
    assert isinstance(value, str)
    assert len(value) == 36
    parts = value.split("-")
    assert len(parts) == 5
    assert [len(p) for p in parts] == [8, 4, 4, 4, 12]
