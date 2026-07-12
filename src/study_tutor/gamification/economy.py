"""Ratified gamification economy — the single source of truth (spec §4.4).

This module owns the **economy contract** the Phase-E engine
(:mod:`study_tutor.gamification.engine`), the settlement transaction
(``finalize_session``), the sweep CLI, and the read-side projection all share:
the XP bands, the 15 level thresholds, the streak milestones, and the shared
London-day helpers. Every value here equals ``docs/gamification/design.md`` §13.1
(the ratified economy patch) **verbatim** — do NOT change a value without the
matching ``design.md`` edit in the same commit (a divergence is a contract
breach, spec non-negotiable rule 4).

The values previously lived inline in the R05 read-side projection
(``study_tutor.gamification.__init__``), whose docstring declares itself
superseded; they are **moved here** so there is exactly one home. The projection
re-exports them for its existing callers.

- **XP bands (design §13.1 D5).** Engagement duration = ``max(ts) − min(ts)``
  over a session's ``session_turn`` rows; sub-2-min (``< 120 s``) settles at 0 XP.
  Cutoffs 120/900/1500 s; awards 0/60/120/180.
- **Level thresholds (design §3.1 / §13.1).** The 15 named tiers and their
  cumulative XP floors, verbatim and re-affirmed by the §13.1 patch.
- **Streak milestones (design §4.2 / §13.1).** 3/7/14/30/60/100 days.
- **Europe/London (design §13.1 D6).** All day/week/cutoff arithmetic; the
  helpers are re-exported from :mod:`study_tutor.gamification.constants`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from study_tutor.gamification.constants import (
    CONFIDENCE_BASELINE_PERCENTAGE,
    LONDON_TZ,
    london_date,
)

__all__ = [
    "CONFIDENCE_BASELINE_PERCENTAGE",
    "LEVEL_THRESHOLDS",
    "LEVEL_UNLOCKS",
    "LONDON_TZ",
    "LONG_SESSION_XP",
    "MAX_LEVEL",
    "MIN_SESSION_SECONDS",
    "RECENT_XP_WINDOW_DAYS",
    "SHORT_SESSION_SECONDS",
    "SHORT_SESSION_XP",
    "STANDARD_SESSION_SECONDS",
    "STANDARD_SESSION_XP",
    "STREAK_MILESTONES",
    "MORNING_STAR_BEFORE_HOUR",
    "EVENING_SCHOLAR_AFTER_HOUR",
    "level_number_for_total_xp",
    "level_progress",
    "level_title_for_total_xp",
    "london_date",
    "london_datetime",
    "next_unlock_for_level",
    "session_xp",
    "started_before_morning",
    "started_after_evening",
]


# -- Session XP bands (design §13.1 D5) -------------------------------------

#: A session shorter than this settles at 0 XP and does not extend a streak
#: (design §13.1 D5 "< 120 s → 0"; §4.1 "not an abandoned one"). This is also
#: the R4 First-Steps eligibility floor (a qualifying session earns XP > 0).
MIN_SESSION_SECONDS: int = 120
#: Upper bound (exclusive) of the +60 band — under 15 minutes of engagement.
SHORT_SESSION_SECONDS: int = 900
#: Upper bound (exclusive) of the +120 band — under 25 minutes of engagement.
STANDARD_SESSION_SECONDS: int = 1500

SHORT_SESSION_XP: int = 60
STANDARD_SESSION_XP: int = 120
LONG_SESSION_XP: int = 180

#: Window (days, inclusive of today) over which ``recent_xp`` is summed —
#: design §9.1's "XP earned this week". Read-side projection constant.
RECENT_XP_WINDOW_DAYS: int = 7


def session_xp(engagement_seconds: float) -> int:
    """XP for one settled session by engagement duration (design §13.1 D5).

    Returns 0 for a sub-2-min (abandoned) or zero-turn session — it neither
    banks XP nor counts toward a streak, First Steps, or Morning/Evening Star.
    """
    if engagement_seconds < MIN_SESSION_SECONDS:
        return 0
    if engagement_seconds < SHORT_SESSION_SECONDS:
        return SHORT_SESSION_XP
    if engagement_seconds < STANDARD_SESSION_SECONDS:
        return STANDARD_SESSION_XP
    return LONG_SESSION_XP


# -- Level thresholds (design §3.1 / §13.1, verbatim) -----------------------

#: (cumulative XP floor to reach, title) for the 15 tiers, ascending. The floors
#: are the §3.1 / §13.1 verbatim list; index + 1 is the level number.
LEVEL_THRESHOLDS: Sequence[tuple[int, str]] = (
    (0, "Beginner"),
    (100, "Novice"),
    (300, "Apprentice"),
    (600, "Student"),
    (1000, "Learner"),
    (1500, "Scholar"),
    (2200, "Academic"),
    (3100, "Intellectual"),
    (4200, "Expert"),
    (5600, "Master"),
    (7300, "Sage"),
    (9400, "Virtuoso"),
    (11900, "Luminary"),
    (14900, "Prodigy"),
    (18500, "Grandmaster"),
)

#: The terminal level number (Grandmaster).
MAX_LEVEL: int = len(LEVEL_THRESHOLDS)


def level_number_for_total_xp(total_xp: int) -> int:
    """The 1-based level number for a cumulative XP total (design §3.1).

    Level 1 (Beginner) at 0 XP; the highest tier whose floor is met wins.
    """
    level = 1
    for index, (threshold, _name) in enumerate(LEVEL_THRESHOLDS):
        if total_xp >= threshold:
            level = index + 1
        else:
            break
    return level


def level_title_for_total_xp(total_xp: int) -> str:
    """The named tier for a cumulative XP total (design §3.1).

    Returns the highest tier whose floor is met; ``Beginner`` at 0 XP.
    """
    return LEVEL_THRESHOLDS[level_number_for_total_xp(total_xp) - 1][1]


def level_progress(total_xp: int) -> tuple[int, int, int]:
    """``(level_number, xp_into_level, xp_to_next_level)`` for a total (design §3.1).

    ``xp_into_level`` is the XP accumulated within the current tier (``total_xp``
    minus the tier floor); ``xp_to_next_level`` is the XP still owed to reach the
    next tier's floor, and is ``0`` at the terminal Level 15 (no next threshold).
    Drives the ``GET /api/student-model`` enrichment (contract §2.2.1).
    """
    level = level_number_for_total_xp(total_xp)
    floor = LEVEL_THRESHOLDS[level - 1][0]
    xp_into = total_xp - floor
    if level >= MAX_LEVEL:
        return level, xp_into, 0
    return level, xp_into, LEVEL_THRESHOLDS[level][0] - total_xp


# -- Level unlock gates (design §3.2) ---------------------------------------

#: The feature each level unlocks (design §3.2 table, verbatim key phrase). Level
#: 1 is base tutoring (no "unlock"); levels 2–15 gate a named feature. Drives the
#: ``next_unlock`` field of the student-model enrichment (contract §2.2.1).
LEVEL_UNLOCKS: dict[int, str] = {
    2: "Daily challenges panel",
    3: "Topic mastery dashboard",
    4: "Quest system",
    5: "Per-AO progress breakdown",
    6: "Exam-style practice questions",
    7: "Comparative-essay scaffold mode",
    8: "Boss Battle mode",
    9: "Two concurrent quests",
    10: "Teaching Mode",
    11: "Cross-text comparison mode",
    12: "Custom practice builder",
    13: "Boss Battle Hard",
    14: "Companion voice",
    15: "Grandmaster status",
}


def next_unlock_for_level(level_number: int) -> tuple[int, str] | None:
    """The next level-gated feature above ``level_number`` (design §3.2).

    Returns ``(level, feature)`` for the next tier, or ``None`` at Level 15
    (terminal — nothing further to unlock).
    """
    next_level = level_number + 1
    feature = LEVEL_UNLOCKS.get(next_level)
    if feature is None:
        return None
    return next_level, feature


# -- Streak milestones (design §4.2 / §13.1) --------------------------------

#: Streak-length day counts that unlock a Consistency achievement (design §4.2 /
#: §13.1, re-affirmed): Three Day Run … Century.
STREAK_MILESTONES: tuple[int, ...] = (3, 7, 14, 30, 60, 100)


# -- Shared London-day helpers (design §13.1 D6) ----------------------------


#: Morning Star counts sessions *started* before this London hour (R3).
MORNING_STAR_BEFORE_HOUR: int = 9
#: Evening Scholar counts sessions *started* strictly after this London hour (R3).
EVENING_SCHOLAR_AFTER_HOUR: int = 19


def london_datetime(moment: datetime) -> datetime:
    """Return ``moment`` in Europe/London local time (design §13.1 D6).

    A naive ``datetime`` is interpreted as UTC (the store persists UTC-aware
    everywhere, but callers may defensively hand a naive value). Used for the
    Morning Star / Evening Scholar 09:00 / 19:00 start-time cutoffs; the
    date-only helper :func:`london_date` (re-exported) governs streak credit
    days and week windows.
    """
    from datetime import timezone

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LONDON_TZ)


def started_before_morning(started_at: datetime) -> bool:
    """Whether ``started_at`` is before 09:00 London — Morning Star (R3)."""
    return london_datetime(started_at).hour < MORNING_STAR_BEFORE_HOUR


def started_after_evening(started_at: datetime) -> bool:
    """Whether ``started_at`` is strictly after 19:00 London — Evening Scholar (R3)."""
    local = london_datetime(started_at)
    if local.hour > EVENING_SCHOLAR_AFTER_HOUR:
        return True
    return local.hour == EVENING_SCHOLAR_AFTER_HOUR and (
        local.minute > 0 or local.second > 0 or local.microsecond > 0
    )
