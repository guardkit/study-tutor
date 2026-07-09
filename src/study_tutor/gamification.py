"""Read-side gamification projection — a *minimal real* slice of the design.

This module is the honest, dependency-free heart of the ``GET /api/student-model``
read (the Reachy ``query_student_model`` progress-report path, fleet-gateway
FEAT-VOICE-004 R05). It derives **real** streak / level / recent-XP from the
durable ``session`` rows already in the Postgres student store, using a
defensible subset of ``docs/gamification/design.md``:

- **Session XP** — the base duration bands of design §2.1 (short/standard/long).
  The stacking bonuses (§2.1 quotation/review) and the ×1.25 Grade 8–9 difficulty
  multiplier are **deliberately not applied** here: they need per-session signals
  the store does not yet capture. Duration is ``last_activity - started_at``.
- **Levels** — the 15 named tiers + total-XP thresholds of design §3.1, verbatim.
- **Streaks** — consecutive-calendar-day completions per design §4.1, with the
  standard "alive until midnight" grace (a run ending *yesterday* still counts
  until today's midnight; a gap of a full day resets it to 0).

**What this is NOT.** This is a read-time derivation, not the Phase-2 gamification
*state engine* (``FEAT-PO-007``; design §12, ADR-ARCH-013). It writes nothing,
banks nothing, and models no achievements/quests/daily-challenges — so
``near_achievements`` is always ``[]`` here. When FEAT-PO-007 ships the real
engine (persisted total_xp/streak, the §5 achievement catalog, near-miss
tracking), it supersedes this module and the endpoint's projection swaps to it.

Everything here is a pure function of its inputs (``today`` is injected, never
read from the clock) so the arithmetic is exhaustively unit-testable without a
database or a wall clock.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, Sequence

from study_tutor.knowledge.store.entities import GamificationState
from study_tutor.knowledge.student_model import TopicConfidence

# -- Session XP (design §2.1 — base duration bands only) --------------------

#: A session shorter than this is "abandoned" — 0 XP and it does not extend a
#: streak (design §2.1 "< 2 min → 0"; §4.1 "not an abandoned one").
MIN_SESSION_SECONDS: int = 2 * 60
#: Upper bound (exclusive) of a "short ~10 min" session → +60 XP.
SHORT_SESSION_SECONDS: int = 15 * 60
#: Upper bound (exclusive) of a "standard ~20 min" session → +120 XP.
STANDARD_SESSION_SECONDS: int = 25 * 60

SHORT_SESSION_XP: int = 60
STANDARD_SESSION_XP: int = 120
LONG_SESSION_XP: int = 180

#: Window (days, inclusive of today) over which ``recent_xp`` is summed —
#: design §9.1's "XP earned this week".
RECENT_XP_WINDOW_DAYS: int = 7

#: (minimum total XP to reach, title) for the 15 tiers of design §3.1, ascending.
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


def session_xp(duration_seconds: float) -> int:
    """XP for one completed session by duration (design §2.1 base bands).

    Returns 0 for an abandoned (< 2 min) session so it neither banks XP nor
    counts toward a streak.
    """
    if duration_seconds < MIN_SESSION_SECONDS:
        return 0
    if duration_seconds < SHORT_SESSION_SECONDS:
        return SHORT_SESSION_XP
    if duration_seconds < STANDARD_SESSION_SECONDS:
        return STANDARD_SESSION_XP
    return LONG_SESSION_XP


def level_title_for_total_xp(total_xp: int) -> str:
    """The named tier for a cumulative XP total (design §3.1).

    Returns the highest tier whose threshold is met; ``Beginner`` at 0 XP.
    """
    title = LEVEL_THRESHOLDS[0][1]
    for threshold, name in LEVEL_THRESHOLDS:
        if total_xp >= threshold:
            title = name
        else:
            break
    return title


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


def project_session_metrics(
    ended_sessions: Iterable[tuple[datetime, datetime]],
    *,
    today: date,
) -> tuple[int, int, int]:
    """Fold ended-session ``(started_at, last_activity)`` pairs into gamification.

    Returns ``(total_xp, recent_xp, streak_days)``. Only *qualifying* sessions
    (XP > 0, i.e. ≥ 2 min) bank XP or extend the streak. ``recent_xp`` sums the
    last ``RECENT_XP_WINDOW_DAYS`` (inclusive of ``today``).
    """
    recent_cutoff = today - timedelta(days=RECENT_XP_WINDOW_DAYS - 1)
    total_xp = 0
    recent_xp = 0
    completion_dates: list[date] = []

    for started_at, last_activity in ended_sessions:
        xp = session_xp((last_activity - started_at).total_seconds())
        if xp <= 0:
            continue
        total_xp += xp
        completion_day = last_activity.date()
        completion_dates.append(completion_day)
        if completion_day >= recent_cutoff:
            recent_xp += xp

    streak_days = compute_streak_days(completion_dates, today)
    return total_xp, recent_xp, streak_days


def build_gamification_state(
    *,
    student_name: str,
    ended_sessions: Iterable[tuple[datetime, datetime]],
    today: date,
) -> GamificationState:
    """Assemble the store's ``GamificationState`` for a seeded student."""
    total_xp, recent_xp, streak_days = project_session_metrics(
        ended_sessions, today=today
    )
    return GamificationState(
        exists=True,
        student_name=student_name,
        streak_days=streak_days,
        level_name=level_title_for_total_xp(total_xp),
        total_xp=total_xp,
        recent_xp=recent_xp,
    )


def build_student_model_response(
    gamification: GamificationState,
    topic_confidences: Iterable[TopicConfidence],
    *,
    fallback_student_id: str,
) -> dict[str, object]:
    """Project store state to the ``GET /api/student-model`` wire body.

    Mirrors the old ``GraphitiClient.search_student_progress`` shape the robot
    narrates. ``near_achievements`` is ``[]`` (deferred to FEAT-PO-007).
    ``data_available`` is False for a seeded-but-empty record (no banked XP and
    no topic confidence) — the robot renders an honest "no data yet".
    """
    confidence_map = {
        tc.topic_ref: round(tc.percentage / 100, 2) for tc in topic_confidences
    }
    return {
        "student_name": gamification.student_name or fallback_student_id,
        "streak_days": gamification.streak_days,
        "level_name": gamification.level_name,
        "recent_xp": gamification.recent_xp,
        "near_achievements": [],
        "topic_confidence": confidence_map,
        "data_available": gamification.total_xp > 0 or bool(confidence_map),
    }


__all__ = [
    "LEVEL_THRESHOLDS",
    "MIN_SESSION_SECONDS",
    "RECENT_XP_WINDOW_DAYS",
    "build_gamification_state",
    "build_student_model_response",
    "compute_streak_days",
    "level_title_for_total_xp",
    "project_session_metrics",
    "session_xp",
]
