"""Unit tests for the read-side gamification projection (``study_tutor.gamification``).

Pure arithmetic — no DB, no wall clock (``today`` is injected). Covers the honest
subset of the gamification design the minimal-real slice implements: session XP
(§2.1 base bands), level tiers (§3.1), streak grace/reset (§4.1), and the
student-model wire projection.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from study_tutor.gamification import (
    LEVEL_THRESHOLDS,
    build_gamification_state,
    build_student_model_response,
    compute_streak_days,
    level_title_for_total_xp,
    project_session_metrics,
    session_xp,
)
from study_tutor.knowledge.store.entities import GamificationState
from study_tutor.knowledge.student_model import TopicConfidence, confidence_band_for

UTC = timezone.utc


def _dt(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# -- session_xp (design §2.1 base bands) ------------------------------------


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, 0),
        (119, 0),  # < 2 min → abandoned, no XP
        (120, 60),  # 2 min → short
        (899, 60),  # < 15 min → short
        (900, 120),  # 15 min → standard
        (1499, 120),
        (1500, 180),  # 25 min → long
        (3600, 180),
    ],
)
def test_session_xp_bands(seconds: int, expected: int) -> None:
    assert session_xp(seconds) == expected


# -- level tiers (design §3.1) ----------------------------------------------


@pytest.mark.parametrize(
    "total_xp, title",
    [
        (0, "Beginner"),
        (99, "Beginner"),
        (100, "Novice"),
        (299, "Novice"),
        (300, "Apprentice"),
        (1000, "Learner"),
        (1500, "Scholar"),
        (14899, "Luminary"),
        (18500, "Grandmaster"),
        (999_999, "Grandmaster"),
    ],
)
def test_level_title_thresholds(total_xp: int, title: str) -> None:
    assert level_title_for_total_xp(total_xp) == title


def test_level_thresholds_ascending_and_complete() -> None:
    thresholds = [t for t, _ in LEVEL_THRESHOLDS]
    assert thresholds == sorted(thresholds)
    assert len(LEVEL_THRESHOLDS) == 15
    assert LEVEL_THRESHOLDS[0] == (0, "Beginner")
    assert LEVEL_THRESHOLDS[-1][1] == "Grandmaster"


# -- streaks (design §4.1) --------------------------------------------------


def test_streak_empty_is_zero() -> None:
    assert compute_streak_days([], date(2026, 7, 9)) == 0


def test_streak_today_only() -> None:
    assert compute_streak_days([date(2026, 7, 9)], date(2026, 7, 9)) == 1


def test_streak_consecutive_run() -> None:
    dates = [date(2026, 7, 9), date(2026, 7, 8), date(2026, 7, 7)]
    assert compute_streak_days(dates, date(2026, 7, 9)) == 3


def test_streak_yesterday_grace_still_live() -> None:
    # Studied yesterday, nothing today yet → run stays live until midnight.
    dates = [date(2026, 7, 8), date(2026, 7, 7)]
    assert compute_streak_days(dates, date(2026, 7, 9)) == 2


def test_streak_two_days_ago_is_broken() -> None:
    assert compute_streak_days([date(2026, 7, 7)], date(2026, 7, 9)) == 0


def test_streak_gap_counts_only_recent_run() -> None:
    # Today + a stale island several days back → only today's run counts.
    dates = [date(2026, 7, 9), date(2026, 7, 5), date(2026, 7, 4)]
    assert compute_streak_days(dates, date(2026, 7, 9)) == 1


def test_streak_duplicate_dates_do_not_inflate() -> None:
    dates = [date(2026, 7, 9), date(2026, 7, 9), date(2026, 7, 8)]
    assert compute_streak_days(dates, date(2026, 7, 9)) == 2


# -- project_session_metrics -------------------------------------------------


def test_project_metrics_mixed_sessions() -> None:
    today = date(2026, 7, 9)
    sessions = [
        (_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 20)),  # 20 min → 120, today
        (_dt(2026, 7, 8, 9, 0), _dt(2026, 7, 8, 9, 40)),  # 40 min → 180, yesterday
        (_dt(2026, 7, 9, 10, 0), _dt(2026, 7, 9, 10, 1)),  # 1 min → 0, abandoned
    ]
    total, recent, streak = project_session_metrics(sessions, today=today)
    assert total == 300  # 120 + 180; abandoned ignored
    assert recent == 300  # both within the 7-day window
    assert streak == 2  # 7/9 and 7/8


def test_project_metrics_recent_window_excludes_old_xp() -> None:
    today = date(2026, 7, 9)
    sessions = [
        (_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 20)),  # 120, today (recent)
        (_dt(2026, 7, 1, 9, 0), _dt(2026, 7, 1, 9, 40)),  # 180, 8 days ago (not recent)
    ]
    total, recent, streak = project_session_metrics(sessions, today=today)
    assert total == 300  # banked lifetime XP includes the old session
    assert recent == 120  # only today's is inside the 7-day window
    assert streak == 1  # the old session does not chain to today


def test_project_metrics_empty() -> None:
    assert project_session_metrics([], today=date(2026, 7, 9)) == (0, 0, 0)


# -- build_gamification_state ------------------------------------------------


def test_build_gamification_state_levels_up_from_sessions() -> None:
    today = date(2026, 7, 9)
    # Six long (40-min) sessions on consecutive days → 6 × 180 = 1080 XP.
    sessions = [(_dt(2026, 7, d, 9, 0), _dt(2026, 7, d, 9, 40)) for d in range(4, 10)]
    state = build_gamification_state(
        student_name="lilymay", ended_sessions=sessions, today=today
    )
    assert state.exists is True
    assert state.student_name == "lilymay"
    assert state.total_xp == 1080
    assert state.level_name == "Learner"  # ≥ 1000
    assert state.streak_days == 6


# -- build_student_model_response --------------------------------------------


def _conf(topic: str, pct: int) -> TopicConfidence:
    return TopicConfidence(
        student_ref="lilymay",
        topic_ref=topic,
        percentage=pct,
        band=confidence_band_for(pct),
        last_revised_at=_dt(2026, 7, 8),
    )


def test_response_happy_shape() -> None:
    gam = GamificationState(
        exists=True,
        student_name="lilymay",
        streak_days=5,
        level_name="Learner",
        total_xp=1080,
        recent_xp=240,
    )
    resp = build_student_model_response(
        gam, [_conf("macbeth", 70), _conf("poetry", 55)], fallback_student_id="lilymay"
    )
    assert resp == {
        "student_name": "lilymay",
        "streak_days": 5,
        "level_name": "Learner",
        "recent_xp": 240,
        "near_achievements": [],
        "topic_confidence": {"macbeth": 0.7, "poetry": 0.55},
        "data_available": True,
    }


def test_response_data_available_false_when_empty() -> None:
    gam = GamificationState(
        exists=True,
        student_name="lilymay",
        streak_days=0,
        level_name="Beginner",
        total_xp=0,
        recent_xp=0,
    )
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")
    assert resp["data_available"] is False
    assert resp["topic_confidence"] == {}
    assert resp["near_achievements"] == []


def test_response_data_available_true_on_confidence_only() -> None:
    gam = GamificationState(
        exists=True,
        student_name="lilymay",
        streak_days=0,
        level_name="Beginner",
        total_xp=0,
        recent_xp=0,
    )
    resp = build_student_model_response(
        gam, [_conf("macbeth", 40)], fallback_student_id="lilymay"
    )
    assert resp["data_available"] is True
    assert resp["topic_confidence"] == {"macbeth": 0.4}


def test_response_name_falls_back_to_student_id() -> None:
    gam = GamificationState(exists=True, student_name=None)
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")
    assert resp["student_name"] == "lilymay"
