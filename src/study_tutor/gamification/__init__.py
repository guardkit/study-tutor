"""Read-side gamification projection over **banked** settlement facts (spec §5).

This module assembles the ``GET /api/student-model`` read (the Reachy
``query_student_model`` progress-report path, fleet-gateway FEAT-VOICE-004 R05)
from the durable rows the Phase-E engine banks at settlement — it no longer
re-derives XP from session durations. The projection reads:

- **Banked XP** — ``total_xp = SUM(session.xp_awarded) + SUM(achievement.xp_awarded)``
  (ADR-ARCH-030 D2). Each ended session carries the XP the engine already awarded
  it; the read simply sums, so the student-model and the ``end_session`` block can
  never disagree.
- **Streaks** — consecutive Europe/London calendar days on which a *qualifying*
  (``xp_awarded > 0``) session completed (design §4.1 / §13.1 D6). ``streak_days``
  is the live run (alive until midnight); ``longest_streak`` is the longest run
  ever. Both fold ``london_date(last_activity)`` of the qualifying sessions.
- **Achievements** — the banked ``achievement`` rows give ``recent_achievements``
  (last 5 by unlock time); the un-held catalog gives ``near_achievements`` (top 3
  by the *same* ranking the engine uses, via
  :func:`study_tutor.gamification.engine.compute_near_achievements`).

**Duration-derivation is gone.** The old ``(started_at, last_activity) →
session_xp(duration)`` read (superseded by the banked-facts swap, spec §5 / B3)
is deleted; ``xp_awarded`` is read straight off the row.

**Superseded numbers moved out.** The XP bands, the 15 level thresholds, the
level-title helper, and the London-day helpers live in
:mod:`study_tutor.gamification.economy` / ``.constants`` (the single ratified
source of truth, spec §4.4); this module **re-exports** them for existing callers
rather than redefining them.

Everything here is a pure function of its inputs (``today`` is injected, never
read from the clock) so the arithmetic is exhaustively unit-testable without a
database or a wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from study_tutor.gamification.catalog import CATALOG_BY_ID
from study_tutor.gamification.constants import (
    CONFIDENCE_BASELINE_PERCENTAGE,
    LONDON_TZ,
    london_date,
)
from study_tutor.gamification.economy import (
    LEVEL_THRESHOLDS,
    MIN_SESSION_SECONDS,
    RECENT_XP_WINDOW_DAYS,
    level_progress,
    level_title_for_total_xp,
    next_unlock_for_level,
    session_xp,
)
from study_tutor.gamification.engine import compute_near_achievements
from study_tutor.knowledge.store.entities import (
    GamificationState,
    NearAchievementView,
    NextUnlockView,
    RecentAchievementView,
)
from study_tutor.knowledge.student_model import TopicConfidence

#: How many top near-achievements the student-model enrichment surfaces (§2.2.1).
NEAR_ACHIEVEMENT_LIMIT: int = 3
#: How many recent achievements the enrichment surfaces (§2.2.1, newest first).
RECENT_ACHIEVEMENT_LIMIT: int = 5


@dataclass(frozen=True)
class EndedSessionFact:
    """One ended session's banked facts, as the projection reads them (spec §5).

    ``xp_awarded`` is the XP the engine banked for this session (0 for a
    sub-2-min / zero-turn session — never re-derived here). ``last_activity`` is
    the session's completion moment; its London date is the streak credit day.
    ``started_at`` drives the Morning Star / Evening Scholar start-window counts.
    """

    started_at: datetime
    last_activity: datetime
    xp_awarded: int


@dataclass(frozen=True)
class HeldAchievementFact:
    """One banked achievement row, as the projection reads it (spec §5)."""

    id: str
    unlocked_at: datetime
    xp_awarded: int


def compute_streak_days(completion_dates: Iterable[date], today: date) -> int:
    """Consecutive-calendar-day streak ending on/just-before ``today`` (§4.1).

    A run that ends *today* or *yesterday* is still live (the "alive until
    midnight" grace); a full missed day resets it to 0. ``completion_dates`` may
    contain duplicates and be unordered.
    """
    days = set(completion_dates)
    if not days:
        return 0

    yesterday = today - timedelta(days=1)
    if today in days:
        anchor = today
    elif yesterday in days:
        anchor = yesterday
    else:
        return 0

    streak = 0
    cursor = anchor
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak_days(completion_dates: Iterable[date]) -> int:
    """The longest consecutive-calendar-day run ever in ``completion_dates`` (§4.1).

    Independent of ``today`` — a completed 30-day run months ago still counts as
    the longest streak. Scans each run once from its start (a day whose
    predecessor is absent).
    """
    days = set(completion_dates)
    if not days:
        return 0

    best = 0
    for day in days:
        if (day - timedelta(days=1)) in days:
            continue  # not a run start — counted from its earliest day
        length = 0
        cursor = day
        while cursor in days:
            length += 1
            cursor += timedelta(days=1)
        best = max(best, length)
    return best


def project_session_metrics(
    ended_sessions: Iterable[EndedSessionFact],
    *,
    today: date,
) -> tuple[int, int, int, int]:
    """Fold banked ended-session facts into ``(total_xp, recent_xp, streak_days,
    longest_streak)`` (spec §5).

    ``total_xp`` is the sum of banked ``xp_awarded`` (achievement XP is added by
    the caller). Only *qualifying* sessions (``xp_awarded > 0``) contribute a
    streak credit day. ``recent_xp`` sums the last ``RECENT_XP_WINDOW_DAYS``
    (inclusive of ``today``) on the Europe/London calendar.
    """
    recent_cutoff = today - timedelta(days=RECENT_XP_WINDOW_DAYS - 1)
    session_xp_total = 0
    recent_xp = 0
    credit_days: list[date] = []

    for fact in ended_sessions:
        session_xp_total += fact.xp_awarded
        completion_day = london_date(fact.last_activity)
        if completion_day >= recent_cutoff:
            recent_xp += fact.xp_awarded
        if fact.xp_awarded > 0:
            credit_days.append(completion_day)

    streak_days = compute_streak_days(credit_days, today)
    longest = longest_streak_days(credit_days)
    return session_xp_total, recent_xp, streak_days, longest


def _reconstruct_context(
    ended_sessions: Iterable[EndedSessionFact],
) -> tuple[set[date], int, int, int]:
    """``(credit_days, morning_count, evening_count, qualifying_count)`` over the
    *qualifying* ended sessions — the banked-fact inputs the near-achievement
    ranking needs (spec §5). Mirrors the engine's ``PriorFacts`` reconstruction so
    live and read-side near-miss state agree."""
    from study_tutor.gamification.economy import (
        started_after_evening,
        started_before_morning,
    )

    credit_days: set[date] = set()
    morning = evening = qualifying = 0
    for fact in ended_sessions:
        if fact.xp_awarded <= 0:
            continue
        qualifying += 1
        credit_days.add(london_date(fact.last_activity))
        if started_before_morning(fact.started_at):
            morning += 1
        if started_after_evening(fact.started_at):
            evening += 1
    return credit_days, morning, evening, qualifying


def _recent_achievement_views(
    achievements: Iterable[HeldAchievementFact],
) -> list[RecentAchievementView]:
    """The last :data:`RECENT_ACHIEVEMENT_LIMIT` unlocks, newest first (§2.2.1).

    Display names are looked up in the catalog; a legacy/unknown id degrades to
    its own id as the name rather than raising.
    """
    ordered = sorted(achievements, key=lambda a: a.unlocked_at, reverse=True)
    views: list[RecentAchievementView] = []
    for held in ordered[:RECENT_ACHIEVEMENT_LIMIT]:
        definition = CATALOG_BY_ID.get(held.id)
        name = definition.name if definition is not None else held.id
        views.append(
            RecentAchievementView(
                id=held.id,
                name=name,
                unlocked_at=held.unlocked_at,
                xp_awarded=held.xp_awarded,
            )
        )
    return views


def _near_achievement_views(
    *,
    held_ids: set[str],
    total_xp: int,
    streak_days: int,
    level_number: int,
    morning_count: int,
    evening_count: int,
    qualifying_count: int,
) -> list[NearAchievementView]:
    """The top :data:`NEAR_ACHIEVEMENT_LIMIT` genuinely-in-progress achievements,
    closest first (§2.2.1), decorated with the catalog ``description`` string.

    Only achievements the learner has *started but not yet earned*
    (``0 < progress < target``) are "near": a met one (``progress ≥ target``) is
    earned-pending-banking, not near — this keeps the read honest even under a
    partial-settlement state where a met achievement's row has not been written
    yet. A learner with no banked activity (``total_xp == 0``) surfaces nothing
    (the contract's "empty array while nothing is close"); this also suppresses
    the LEVEL-kind achievements, whose progress reads the Level-1 baseline of 1
    for a brand-new student.
    """
    if total_xp <= 0:
        return []
    near = compute_near_achievements(
        held=set(held_ids),
        total_xp=total_xp,
        streak_days=streak_days,
        level=level_number,
        morning_count=morning_count,
        evening_count=evening_count,
        qualifying_sessions=qualifying_count,
    )
    in_progress = [n for n in near if 0 < n.progress < n.target]
    views: list[NearAchievementView] = []
    for item in in_progress[:NEAR_ACHIEVEMENT_LIMIT]:
        definition = CATALOG_BY_ID.get(item.id)
        description = definition.description if definition is not None else item.name
        views.append(
            NearAchievementView(
                id=item.id,
                name=item.name,
                description=description,
                progress=item.progress,
                target=item.target,
                hint=item.hint,
            )
        )
    return views


def build_gamification_state(
    *,
    student_name: str,
    ended_sessions: Iterable[EndedSessionFact],
    achievements: Iterable[HeldAchievementFact],
    today: date,
) -> GamificationState:
    """Assemble the enriched ``GamificationState`` from banked facts (spec §5).

    ``total_xp`` sums banked session + achievement XP (ADR-ARCH-030 D2); streaks
    fold the qualifying sessions' London credit days; the achievement views come
    from the banked ``achievement`` rows and the catalog. Pure — ``today`` is
    injected.
    """
    sessions = list(ended_sessions)
    held = list(achievements)

    session_xp_total, recent_xp, streak_days, longest = project_session_metrics(
        sessions, today=today
    )
    achievement_xp_total = sum(a.xp_awarded for a in held)
    total_xp = session_xp_total + achievement_xp_total

    level_number, xp_into_level, xp_to_next_level = level_progress(total_xp)
    _credit_days, morning, evening, qualifying = _reconstruct_context(sessions)

    recent_achievements = _recent_achievement_views(held)
    near_achievements = _near_achievement_views(
        held_ids={a.id for a in held},
        total_xp=total_xp,
        streak_days=streak_days,
        level_number=level_number,
        morning_count=morning,
        evening_count=evening,
        qualifying_count=qualifying,
    )
    next_unlock_tuple = next_unlock_for_level(level_number)
    next_unlock = (
        NextUnlockView(level=next_unlock_tuple[0], feature=next_unlock_tuple[1])
        if next_unlock_tuple is not None
        else None
    )

    return GamificationState(
        exists=True,
        student_name=student_name,
        streak_days=streak_days,
        level_name=level_title_for_total_xp(total_xp),
        total_xp=total_xp,
        recent_xp=recent_xp,
        longest_streak=longest,
        level_number=level_number,
        xp_into_level=xp_into_level,
        xp_to_next_level=xp_to_next_level,
        recent_achievements=recent_achievements,
        near_achievements=near_achievements,
        next_unlock=next_unlock,
    )


def build_student_model_response(
    gamification: GamificationState,
    topic_confidences: Iterable[TopicConfidence],
    *,
    fallback_student_id: str,
) -> dict[str, object]:
    """Project store state to the ``GET /api/student-model`` wire body (§2.2 + §2.2.1).

    The original R05 fields (``student_name`` … ``data_available``) keep their
    exact names and semantics; the §2.2.1 enrichment is additive. ``near_achievements``
    grows from the R05 hardwired ``[]`` to top-3 objects. ``data_available`` is
    unchanged: False for a seeded-but-empty record (no banked XP and no topic
    confidence) so the robot renders an honest "no data yet".
    """
    confidence_map = {
        tc.topic_ref: round(tc.percentage / 100, 2) for tc in topic_confidences
    }
    return {
        # -- Original R05 fields (byte-identical names/semantics) ----------
        "student_name": gamification.student_name or fallback_student_id,
        "streak_days": gamification.streak_days,
        "level_name": gamification.level_name,
        "recent_xp": gamification.recent_xp,
        "near_achievements": [
            {
                "id": near.id,
                "name": near.name,
                "description": near.description,
                "progress": near.progress,
                "target": near.target,
                "hint": near.hint,
            }
            for near in gamification.near_achievements
        ],
        "topic_confidence": confidence_map,
        "data_available": gamification.total_xp > 0 or bool(confidence_map),
        # -- Enrichment (contract §2.2.1) ----------------------------------
        "total_xp": gamification.total_xp,
        "level_number": gamification.level_number,
        "xp_into_level": gamification.xp_into_level,
        "xp_to_next_level": gamification.xp_to_next_level,
        "longest_streak": gamification.longest_streak,
        "recent_achievements": [
            {
                "id": recent.id,
                "name": recent.name,
                "unlocked_at": recent.unlocked_at.isoformat(),
                "xp_awarded": recent.xp_awarded,
            }
            for recent in gamification.recent_achievements
        ],
        "next_unlock": (
            {
                "level": gamification.next_unlock.level,
                "feature": gamification.next_unlock.feature,
            }
            if gamification.next_unlock is not None
            else None
        ),
    }


__all__ = [
    "CONFIDENCE_BASELINE_PERCENTAGE",
    "LEVEL_THRESHOLDS",
    "LONDON_TZ",
    "MIN_SESSION_SECONDS",
    "NEAR_ACHIEVEMENT_LIMIT",
    "RECENT_ACHIEVEMENT_LIMIT",
    "RECENT_XP_WINDOW_DAYS",
    "EndedSessionFact",
    "HeldAchievementFact",
    "build_gamification_state",
    "build_student_model_response",
    "compute_streak_days",
    "london_date",
    "longest_streak_days",
    "level_title_for_total_xp",
    "project_session_metrics",
    "session_xp",
]
