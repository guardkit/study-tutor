"""Session completion producer — pure store-backed confidence updates (TASK-SMP3-05).

This module provides the producer that converts a completed session into a
``SessionCompletion`` by reading current confidence from the store and applying
the Phase1MinimalDeltaPolicy heuristic. This replaces the prior graph-coupled
confidence-update path with W2 store reads.
"""

from __future__ import annotations

from typing import Any, Protocol

from study_tutor.gamification.constants import CONFIDENCE_BASELINE_PERCENTAGE
from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.store.port import StudentStore
from study_tutor.session.service import SessionCompletion


class ConfidenceDeltaPolicyLike(Protocol):
    """Protocol for confidence delta policies."""

    name: str

    def compute(
        self,
        *,
        student_id: str,
        topic_ref: str,
        session_summary: dict[str, Any],
    ) -> int:
        """Compute the delta to apply to a topic's confidence.

        Args:
            student_id: Student identifier
            topic_ref: Topic name or slug
            session_summary: Session metadata including turn count and misconceptions

        Returns:
            Delta value (typically clamped to [-10, 10])
        """
        ...


class Phase1MinimalDeltaPolicy:
    """Phase-1 expedient confidence delta policy.

    NOT a real model of confidence change. Owned by FEAT-PH2-001 for replacement.
    This policy was lifted from the prior graph query layer to survive the
    FEAT-SMP-004 store teardown.

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
        """Compute the delta for a topic based on session activity.

        Args:
            student_id: Student identifier (unused by current heuristic)
            topic_ref: Topic name or slug
            session_summary: Must contain:
                - ``student_turn_count`` (int): Number of turns in session
                - ``misconceptions_per_topic`` (dict): Map of topic → count

        Returns:
            Delta value in [-10, 10]
        """
        misc = int(
            session_summary.get("misconceptions_per_topic", {}).get(topic_ref, 0)
        )
        turns = int(session_summary.get("student_turn_count", 0))
        delta = -3 * misc
        if turns >= 5 and misc == 0:
            delta += 1
        return max(-10, min(10, delta))


async def build_session_completion(
    *,
    store: StudentStore,
    student_id: str,
    topic: str,
    student_turn_count: int,
    aos_scaffolded: list[str],
    misconceptions_per_topic: dict[str, int],
) -> SessionCompletion:
    """Build a SessionCompletion by reading current confidence and applying policy.

    This is the pure, store-backed producer that TASK-SMP3-06's adapter cutover
    calls at ``end_session``.

    Args:
        store: Student store for reading current confidence
        student_id: Student identifier
        topic: Topic covered in the session
        student_turn_count: Number of student turns in the session
        aos_scaffolded: List of areas of study scaffolded during the session
        misconceptions_per_topic: Map of topic → misconception count (empty this wave)

    Returns:
        SessionCompletion with:
        - ``confidence_updates``: For the covered topic, resolved post-session value
        - ``xp_awarded``: 0 (ASSUM-006 placeholder)
        - ``misconceptions``: [] (ASSUM-007 placeholder)
        - ``topic``, ``aos_scaffolded``: Passed through

    Note:
        Zero-turn guard belongs to the caller (SMP3-06). This producer assumes
        it is called only for ``turn_count > 0``.
    """
    policy = Phase1MinimalDeltaPolicy()

    # Read current confidence for the student
    topic_confidences = await store.get_topic_confidences(student_id)

    # Find the current confidence for the covered topic
    current_confidence = next(
        (tc for tc in topic_confidences if tc.topic_ref == topic), None
    )

    # S-R3 §2.3 / R12 confidence bootstrap: a first-seen topic (no row yet) is
    # created at the mid-Developing baseline (``CONFIDENCE_BASELINE_PERCENTAGE``)
    # BEFORE the session delta is applied — the guard that used to skip
    # unknown-topic writes is dropped so ``topic_confidence`` rows are actually
    # created, not only updated (design §13.1 R12). The store write is an upsert
    # that derives the band + ``last_revised_at``.
    base_percentage = (
        current_confidence.percentage
        if current_confidence is not None
        else CONFIDENCE_BASELINE_PERCENTAGE
    )

    session_summary = {
        "student_turn_count": student_turn_count,
        "misconceptions_per_topic": misconceptions_per_topic,
    }
    delta = policy.compute(
        student_id=student_id,
        topic_ref=topic,
        session_summary=session_summary,
    )

    # Calculate new confidence and clamp to [0, 100]
    new_percentage = max(0, min(100, base_percentage + delta))

    confidence_updates: list[ConfidenceUpdate] = [
        ConfidenceUpdate(topic_name=topic, percentage=new_percentage)
    ]

    # Return the completion with placeholders for xp and misconceptions
    return SessionCompletion(
        topic=topic,
        aos_scaffolded=aos_scaffolded,
        xp_awarded=0,  # ASSUM-006 placeholder
        confidence_updates=confidence_updates,
        misconceptions=[],  # ASSUM-007 placeholder
    )


__all__ = [
    "ConfidenceDeltaPolicyLike",
    "Phase1MinimalDeltaPolicy",
    "build_session_completion",
]
