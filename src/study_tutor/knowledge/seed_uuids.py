"""Deterministic UUID derivation helpers for the typed-entity seed.

TASK-GSM-009 / ADR-ARCH-021 — every entity the seed writes has its UUID
derived deterministically from ``(group_id, label, identity)``. That makes
re-runs byte-idempotent: ``EntityNode.save`` MERGEs by uuid in the FalkorDB
driver, so writing a node twice with the same uuid produces a single graph
node, not a duplicate.

Per-class identity keys (per task AC-GSM-009-12 / R4):

- **Student / Subject / Topic / AssessmentObjective** — identity is
  ``name`` (entity has a stable, human-readable name).
- **Text** — Text names may collide across subjects (e.g. a generic study
  guide could appear under both English Lit and English Lang), so the
  identity key includes ``subject_slug`` to disambiguate.
- **TopicConfidence** — has no ``name`` field; identity is the composite
  ``(student_ref, topic_ref)`` pair (one TopicConfidence per student per
  topic).
- **Misconception** — identity is ``(topic_ref, observed_at_iso)``. Not
  emitted by the Phase-1 baseline seed, but the helper is in place so a
  future seed extension or a hand-curated misconception migration can
  reuse the same derivation pattern.
- **Edges** — identity is ``(relationship_name, source_uuid, target_uuid)``.
  An edge between the same two nodes with the same relationship type
  always derives to the same uuid.

The helpers all return ``str`` (the UUID5 hex form) because graphiti-core's
``EntityNode(uuid=...)`` / ``EntityEdge(uuid=...)`` constructors take
strings. The ``NAMESPACE_OID`` namespace is used uniformly so every helper
draws from the same UUIDv5 namespace and collision-freedom is just a
function of the identity-key uniqueness.

Cross-references:

- `ADR-ARCH-021 §G2 / §"Implementation surface"`
- `tasks/in_progress/TASK-GSM-009-typed-entity-seed-refactor.md` AC-12 (R4)
- :mod:`scripts.seed_student_model` (the only intended caller)
"""
from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_OID, uuid5


def student_uuid(group_id: str, name: str) -> str:
    """Derive the deterministic UUID for a Student entity."""
    return str(uuid5(NAMESPACE_OID, f"{group_id}:Student:{name}"))


def subject_uuid(group_id: str, name: str) -> str:
    """Derive the deterministic UUID for a Subject entity."""
    return str(uuid5(NAMESPACE_OID, f"{group_id}:Subject:{name}"))


def text_uuid(group_id: str, subject_slug: str, name: str) -> str:
    """Derive the deterministic UUID for a Text entity.

    The ``subject_slug`` is part of the identity key because Text names can
    collide across subjects (e.g. a generic study-guide title could appear
    under more than one Subject). The seed currently writes every Text under
    a single ``subject-<slug>`` group_id, so the slug-in-key is belt-and-
    braces against future seeds that route Texts under cross-subject
    partitions.
    """
    return str(uuid5(NAMESPACE_OID, f"{group_id}:Text:{subject_slug}:{name}"))


def topic_uuid(group_id: str, name: str) -> str:
    """Derive the deterministic UUID for a Topic entity."""
    return str(uuid5(NAMESPACE_OID, f"{group_id}:Topic:{name}"))


def assessment_objective_uuid(group_id: str, name: str) -> str:
    """Derive the deterministic UUID for an AssessmentObjective entity."""
    return str(uuid5(NAMESPACE_OID, f"{group_id}:AssessmentObjective:{name}"))


def topic_confidence_uuid(
    group_id: str, student_ref: str, topic_ref: str
) -> str:
    """Derive the deterministic UUID for a TopicConfidence entity.

    Identity key is ``(student_ref, topic_ref)`` because a TopicConfidence
    has no ``name`` field — there is exactly one TopicConfidence per student
    per topic, and that pair is the natural composite key.
    """
    return str(
        uuid5(
            NAMESPACE_OID,
            f"{group_id}:TopicConfidence:{student_ref}:{topic_ref}",
        )
    )


def misconception_uuid(
    group_id: str, topic_ref: str, observed_at: datetime
) -> str:
    """Derive the deterministic UUID for a Misconception entity.

    Not used by the Phase-1 baseline seed (the seed writes no
    misconceptions), but kept in the helper module so a future hand-curated
    misconception import can reuse the same derivation pattern as the rest
    of the typed-entity write surface.
    """
    return str(
        uuid5(
            NAMESPACE_OID,
            f"{group_id}:Misconception:{topic_ref}:{observed_at.isoformat()}",
        )
    )


def edge_uuid(name: str, source_uuid: str, target_uuid: str) -> str:
    """Derive the deterministic UUID for a typed Edge.

    Identity key is ``(relationship_name, source_uuid, target_uuid)``, so
    two writes of e.g. ``Student → HAS_CONFIDENCE → TopicConfidence``
    between the same source/target pair will always derive to the same
    uuid and MERGE rather than duplicate.

    Note that the ``group_id`` is *not* in the edge identity key. Edges are
    written under a single named graph (per ADR-ARCH-021 §G2: only
    intra-group edges in Phase 1), and the source/target node uuids
    already encode their respective group_ids — so adding ``group_id`` here
    would just be redundant.
    """
    return str(uuid5(NAMESPACE_OID, f"{name}:{source_uuid}:{target_uuid}"))


__all__ = [
    "assessment_objective_uuid",
    "edge_uuid",
    "misconception_uuid",
    "student_uuid",
    "subject_uuid",
    "text_uuid",
    "topic_confidence_uuid",
    "topic_uuid",
]
