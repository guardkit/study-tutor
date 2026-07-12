"""Pydantic records for the Postgres StudentStore (FEAT-SMP-001 scaffolding).

This module is the **persistence-facing** record layer for the study-tutor
learner store, per [ADR-ARCH-023]. It is intentionally stack-agnostic — it
imports **no** database driver — mirroring the discipline already used by
``knowledge.student_model`` (which imports no database driver either).

What lives here:

- **Read models re-homed from the prior graph query layer** — ``StudentState``
  and its snapshots. FEAT-SMP-002 repoints ``get_student_state`` at the store
  and imports these from here (the old graph-coupled copies are then
  deleted). Kept byte-compatible with the current shapes so the swap is a
  drop-in for existing handler/planner callers.
- **New persistence records** the gamification §11 schema and the cross-device
  session contract need but the graph era never modelled as first-class rows:
  ``SessionRecord``, ``SessionTurn``, ``Achievement``, ``Quest``,
  ``ConfidenceUpdate``.

``ConfidenceBand`` and ``confidence_band_for`` are reused from
``student_model`` — the band taxonomy (ASSUM-001) does not change with the
store swap. ``TopicConfidence`` / ``Misconception`` (the domain entities the
planner consumes) also stay in ``student_model``; this module only adds the
records that were previously graph episodes.

Status: scaffolding for FEAT-SMP-001's ``/feature-spec`` to react to. Field
sets are the proposed contract; the build may refine.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from study_tutor.knowledge.student_model import ConfidenceBand

# ---------------------------------------------------------------------------
# Discriminators
# ---------------------------------------------------------------------------

#: Session lifecycle state (session contract §4). ``active`` is resumable from
#: any device authenticated as the owning student; ``ended`` is terminal.
SessionStatus = Literal["active", "ended"]

#: Author of a persisted turn.
TurnRole = Literal["user", "tutor"]

#: Quest lifecycle (gamification §2.3).
QuestStatus = Literal["active", "completed", "expired"]

#: Why the planner surfaced a topic — re-homed from ``queries.py`` unchanged.
RecommendationReason = Literal[
    "struggling_stale",
    "developing_misconception",
    "developing_stale",
]


class _Record(BaseModel):
    """Shared config: forbid extras so a schema drift surfaces at the boundary."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Read models (re-homed from knowledge.queries — keep shapes byte-compatible)
# ---------------------------------------------------------------------------


class TopicConfidenceSnapshot(_Record):
    """Read projection of a per-topic confidence row."""

    topic_name: str
    band: ConfidenceBand
    percentage: int = Field(ge=0, le=100)
    last_revised_at: datetime | None = None


class MisconceptionSnapshot(_Record):
    """Read projection of a misconception row."""

    topic_name: str
    text: str
    observed_at: datetime


class StudentState(_Record):
    """Aggregated student-model snapshot returned by ``get_student_state``.

    ``empty=True`` is the explicit "store unavailable / no such student"
    sentinel (the graph era used it for "backend unavailable"); callers branch
    on it without inspecting other fields. ``stale=True`` flags that at least
    one underlying fact is older than the configured stale threshold; the fact
    is still returned.
    """

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


class RecentAchievementView(_Record):
    """One recently-unlocked achievement for the student-model enrichment
    (contract §2.2.1 ``recent_achievements``)."""

    id: str
    name: str
    unlocked_at: datetime
    xp_awarded: int = Field(ge=0)


class NearAchievementView(_Record):
    """A not-yet-unlocked achievement and how close the learner is, for the
    student-model enrichment (contract §2.2.1 ``near_achievements``)."""

    id: str
    name: str
    description: str
    progress: int = Field(ge=0)
    target: int = Field(ge=0)
    hint: str


class NextUnlockView(_Record):
    """The next level-gated feature (contract §2.2.1 ``next_unlock``; design §3.2)."""

    level: int = Field(ge=1)
    feature: str


class GamificationState(_Record):
    """Read-side gamification snapshot for the student-model endpoint.

    A projection over the durable ``session`` + ``achievement`` rows at read time
    (``study_tutor.gamification``): banked XP (``SUM(session.xp_awarded) +
    SUM(achievement.xp_awarded)``, ADR-ARCH-030 D2), London-day streaks, and the
    achievement catalog's recent/near state. ``exists=False`` is the "no such
    student" sentinel; for a seeded student the fields carry real streak / level /
    XP, and ``total_xp == 0`` with no topic confidence means a seeded-but-empty
    record (``data_available: false`` on the wire).

    The enrichment fields (contract §2.2.1) are additive over the original R05
    snapshot: ``longest_streak``, ``level_number`` + within-level progress, and
    the recent/near achievement views the endpoint surfaces.
    """

    exists: bool
    student_name: str | None = None
    streak_days: int = Field(default=0, ge=0)
    level_name: str | None = None
    total_xp: int = Field(default=0, ge=0)
    recent_xp: int = Field(default=0, ge=0)
    # -- Enrichment (contract §2.2.1) --------------------------------------
    longest_streak: int = Field(default=0, ge=0)
    level_number: int = Field(default=1, ge=1)
    xp_into_level: int = Field(default=0, ge=0)
    xp_to_next_level: int = Field(default=0, ge=0)
    recent_achievements: list[RecentAchievementView] = Field(default_factory=list)
    near_achievements: list[NearAchievementView] = Field(default_factory=list)
    next_unlock: NextUnlockView | None = None


class TopicRecommendation(_Record):
    """A single ranked topic recommendation for the planner/handler."""

    topic_name: str
    reason: RecommendationReason
    confidence_band: ConfidenceBand
    last_revised_at: datetime | None = None


# ---------------------------------------------------------------------------
# New persistence records
# ---------------------------------------------------------------------------


class ConfidenceUpdate(_Record):
    """A proposed post-session confidence value for one topic.

    ``percentage`` is the NEW confidence after the Coach's per-session delta
    (capped ±10 points per gamification §6.2) has been applied — the store
    persists the resolved value, not the delta, so the write is idempotent on
    replay. The band is derived via ``confidence_band_for`` at write time.
    """

    topic_name: str
    percentage: int = Field(ge=0, le=100)


class SessionRecord(_Record):
    """A durable study session, keyed to a student (session contract §6)."""

    session_id: str
    student_id: str
    subject: str
    topic: str | None = None
    status: SessionStatus = "active"
    started_at: datetime
    last_activity: datetime
    turn_count: int = Field(default=0, ge=0)
    aos_scaffolded: list[str] = Field(default_factory=list)
    #: Canonical set-text slug captured at start (S-E4 / scope §4.2); ``None`` for
    #: a free-topic session no known set text was recognised for.
    text_name: str | None = None
    #: Cumulative corpus-hit quotations embedded across this session's turns
    #: (S-E4 / scope §4.3, R8); bumped per tutor turn by ``append_turn``.
    quotes_embedded: int = Field(default=0, ge=0)
    summary: str | None = None


class SessionTurn(_Record):
    """One persisted turn. Append-only within a session; per-turn durable so a
    mid-session device switch is lossless (session contract §4/§6)."""

    session_id: str
    turn_index: int = Field(ge=0)
    role: TurnRole
    content: str
    ts: datetime
    ao_scaffolded: str | None = None


class Achievement(_Record):
    """A first-unlock achievement award (gamification §5). Sticky — never revoked."""

    achievement_id: str
    student_id: str
    unlocked_at: datetime
    xp_awarded: int = Field(ge=0)


class Quest(_Record):
    """An active or historical quest (gamification §2.3)."""

    quest_id: str
    student_id: str
    shape: str
    status: QuestStatus = "active"
    started_at: datetime
    expires_at: datetime | None = None
    xp_reward: int = Field(ge=0)


__all__ = [
    "Achievement",
    "ConfidenceUpdate",
    "GamificationState",
    "MisconceptionSnapshot",
    "NearAchievementView",
    "NextUnlockView",
    "Quest",
    "QuestStatus",
    "RecentAchievementView",
    "RecommendationReason",
    "SessionRecord",
    "SessionStatus",
    "SessionTurn",
    "StudentState",
    "TopicConfidenceSnapshot",
    "TopicRecommendation",
    "TurnRole",
]
