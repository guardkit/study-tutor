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

**What this is NOT.** This is a read-time derivation of streak/level/recent-XP,
not the Phase-E gamification *engine* (``study_tutor.gamification.engine`` /
``finalize_session``; spec §4, ADR-ARCH-030). It banks nothing and models no
achievements — so ``near_achievements`` is always ``[]`` here. The banked-facts
projection swap (spec §5 / B3) supersedes the duration-derivation below; until
then this remains the ``GET /api/student-model`` read.

**Superseded numbers moved out.** The XP bands, the 15 level thresholds, and the
level-title helper now live in :mod:`study_tutor.gamification.economy` (the
single ratified source of truth, spec §4.4); this module **re-exports** them for
its existing callers rather than redefining them. The bands are numerically
identical to what lived here (design §13.1 D5: 120/900/1500 s → 0/60/120/180).

Everything here is a pure function of its inputs (``today`` is injected, never
read from the clock) so the arithmetic is exhaustively unit-testable without a
database or a wall clock.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from study_tutor.gamification.constants import (
    CONFIDENCE_BASELINE_PERCENTAGE,
    LONDON_TZ,
    london_date,
)
from study_tutor.gamification.economy import (
    LEVEL_THRESHOLDS,
    MIN_SESSION_SECONDS,
    RECENT_XP_WINDOW_DAYS,
    level_title_for_total_xp,
    session_xp,
)
from study_tutor.knowledge.store.entities import GamificationState
from study_tutor.knowledge.student_model import TopicConfidence


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
    "CONFIDENCE_BASELINE_PERCENTAGE",
    "LEVEL_THRESHOLDS",
    "LONDON_TZ",
    "MIN_SESSION_SECONDS",
    "RECENT_XP_WINDOW_DAYS",
    "build_gamification_state",
    "london_date",
    "build_student_model_response",
    "compute_streak_days",
    "level_title_for_total_xp",
    "project_session_metrics",
    "session_xp",
]
