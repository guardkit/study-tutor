"""Pydantic episode types for student-model write paths.

These episodes are the data contract between the runtime (Tutor handler and
Coach AsyncSubAgent) and Graphiti. The serialised body each one produces is
what Graphiti's extraction LLM sees, so the shape and the natural-language
projection are a public surface — not an internal detail of the helper.

This module is intentionally stack-agnostic: it does not import anything from
``graphiti-core`` or any other graph backend. Sanitisation (e.g. capping the
``misconception_text`` length, neutralising prompt-injection attempts) is the
responsibility of the write helper (TASK-GSM-004), not these types.

See ``tasks/backlog/graphiti-student-model/TASK-GSM-002-episode-types.md``
and ``phase-1-scope.md §FEAT-PH1-001`` for the full specification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Discriminator literals used across all concrete episode classes.
# Names must match the scope-doc spec exactly (see TASK-GSM-002).
#
# Note (ADR-ARCH-021 / TASK-GSM-009): the historical ``"seed_baseline"``
# literal and its companion ``SeedBaselineEpisode`` class were removed when
# the Lilymay seed migrated to typed-entity writes (``EntityNode.save`` /
# ``EntityEdge.save``). The seed no longer routes through the shared
# write helper, so there is no ``add_episode``-shaped payload to discriminate.
# CC-13 narrowed accordingly: ``schedule_write`` is the single call site for
# **live tutor session** ``add_episode`` writes only.
EpisodeKind = Literal[
    "session_completed",
    "topic_confidence_updated",
    "misconception_observed",
]


class EpisodeBase(BaseModel):
    """Shared base for all student-model episodes.

    Concrete subclasses pin ``episode_kind`` to a single literal and implement
    :meth:`to_graphiti_episode_body` to project the payload into the
    natural-language string Graphiti's ``add_episode`` ingests.
    """

    # ``extra="forbid"`` keeps the contract tight: typos in caller code surface
    # as validation errors rather than silently dropped fields. Episodes are
    # the integration contract with Graphiti, so strictness here is desirable.
    model_config = ConfigDict(extra="forbid")

    episode_kind: EpisodeKind

    def to_graphiti_episode_body(self) -> str:
        """Produce the natural-language body sent to Graphiti's ``add_episode``.

        The returned string MUST be deterministic: the same payload always
        produces the same string, so downstream caching and idempotency keys
        can rely on it.
        """
        raise NotImplementedError(
            "Concrete episode subclasses must implement to_graphiti_episode_body()."
        )


class SessionCompletedEpisode(EpisodeBase):
    """Flush point F3 — Tutor handler on ``active → ended`` state transition.

    Emitted once per completed tutoring session; carries the session-level
    summary that downstream extraction turns into Topic / AssessmentObjective
    relationships for the Student.
    """

    episode_kind: Literal["session_completed"] = "session_completed"
    session_id: str
    student_id: str
    subject_slug: str
    text_name: str
    topics_covered: list[str]
    aos_exercised: list[str]
    narrative_summary: str
    started_at: datetime
    ended_at: datetime

    def to_graphiti_episode_body(self) -> str:
        topics = ", ".join(self.topics_covered) if self.topics_covered else "none"
        aos = ", ".join(self.aos_exercised) if self.aos_exercised else "none"
        return (
            f"Student {self.student_id} completed session {self.session_id} "
            f"on subject {self.subject_slug} (text: {self.text_name}) "
            f"from {self.started_at.isoformat()} to {self.ended_at.isoformat()}. "
            f"Topics covered: {topics}. "
            f"Assessment objectives exercised: {aos}. "
            f"Summary: {self.narrative_summary}"
        )


class TopicConfidenceUpdatedEpisode(EpisodeBase):
    """Flush point F2 — Tutor handler when planner produces a confidence delta.

    Captures a transition in the student's :class:`TopicConfidence` relationship
    so Graphiti can record the temporal change.
    """

    episode_kind: Literal["topic_confidence_updated"] = "topic_confidence_updated"
    student_id: str
    topic_name: str
    previous_band: str
    new_band: str
    previous_percentage: int
    new_percentage: int
    observed_at: datetime
    triggering_session_id: str | None = None
    # AC-CONF-07 (TASK-GR-CONF): identifier of the policy that produced the
    # delta. Phase-1 stub sets ``"phase1_minimal_policy"``; FEAT-PH2-001 sets
    # a different value. Lets future analytics filter heuristic-era data
    # (``confidence_source == "phase1_minimal_policy"``) from real-signal
    # data. ``min_length=1`` prevents empty strings — the field is required
    # because ``extra="forbid"`` makes adding it a deliberate contract change.
    confidence_source: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifier of the policy that produced the delta. Phase-1 stub "
            "sets 'phase1_minimal_policy'; FEAT-PH2-001 sets a different "
            "value. Lets future analytics distinguish heuristic-era data "
            "from real-signal data."
        ),
    )

    def to_graphiti_episode_body(self) -> str:
        triggering = (
            self.triggering_session_id
            if self.triggering_session_id is not None
            else "none"
        )
        return (
            f"Student {self.student_id} confidence on topic '{self.topic_name}' "
            f"updated from band {self.previous_band} ({self.previous_percentage}%) "
            f"to band {self.new_band} ({self.new_percentage}%) "
            f"at {self.observed_at.isoformat()}. "
            f"Triggering session: {triggering}. "
            f"Source: {self.confidence_source}."
        )


class MisconceptionObservedEpisode(EpisodeBase):
    """Flush point F1 — Coach AsyncSubAgent identifies a misconception.

    ``misconception_text`` is intentionally uncapped at this layer. The write
    helper (TASK-GSM-004) is responsible for length capping and any sanitisation
    needed to mitigate prompt-injection through adversarial student input.
    """

    episode_kind: Literal["misconception_observed"] = "misconception_observed"
    student_id: str
    topic_name: str
    misconception_text: str
    observed_at: datetime
    triggering_session_id: str
    confidence_band_at_observation: str

    def to_graphiti_episode_body(self) -> str:
        return (
            f"Student {self.student_id} exhibited a misconception on topic "
            f"'{self.topic_name}' "
            f"(confidence band at observation: {self.confidence_band_at_observation}) "
            f"during session {self.triggering_session_id} "
            f"at {self.observed_at.isoformat()}. "
            f"Misconception: {self.misconception_text}"
        )


__all__ = [
    "EpisodeKind",
    "EpisodeBase",
    "SessionCompletedEpisode",
    "TopicConfidenceUpdatedEpisode",
    "MisconceptionObservedEpisode",
]
