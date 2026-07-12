"""Unit tests for the read-side gamification projection (``study_tutor.gamification``).

Pure arithmetic — no DB, no wall clock (``today`` is injected). Covers the
banked-facts projection swap (spec §5 / B3): banked XP folds (``xp_awarded`` read
straight off the row, never re-derived from duration), London-calendar streak /
longest-streak (design §4.1 / §13.1 D6, including UTC-midnight crossings), and
the enriched student-model wire projection (contract §2.2.1).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from study_tutor.gamification import (
    LEVEL_THRESHOLDS,
    EndedSessionFact,
    HeldAchievementFact,
    build_gamification_state,
    build_student_model_response,
    compute_streak_days,
    level_title_for_total_xp,
    longest_streak_days,
    project_session_metrics,
    session_xp,
)
from study_tutor.knowledge.store.entities import GamificationState
from study_tutor.knowledge.student_model import TopicConfidence, confidence_band_for

UTC = timezone.utc


def _dt(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _session(
    started_at: datetime, last_activity: datetime, xp_awarded: int
) -> EndedSessionFact:
    return EndedSessionFact(
        started_at=started_at, last_activity=last_activity, xp_awarded=xp_awarded
    )


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


# -- longest_streak_days (design §4.1) --------------------------------------


def test_longest_streak_empty_is_zero() -> None:
    assert longest_streak_days([]) == 0


def test_longest_streak_ignores_today_grace() -> None:
    # A completed 4-day island months ago is the longest run, though it is
    # nowhere near "today" — longest_streak is independent of the current date.
    dates = [
        date(2026, 3, 1),
        date(2026, 3, 2),
        date(2026, 3, 3),
        date(2026, 3, 4),
        date(2026, 7, 9),  # a lone recent day
    ]
    assert longest_streak_days(dates) == 4


def test_longest_streak_takes_the_max_of_two_runs() -> None:
    dates = [
        date(2026, 7, 1),
        date(2026, 7, 2),  # run of 2
        date(2026, 7, 7),
        date(2026, 7, 8),
        date(2026, 7, 9),  # run of 3
    ]
    assert longest_streak_days(dates) == 3


# -- project_session_metrics (banked facts) ---------------------------------


def test_project_metrics_mixed_sessions() -> None:
    today = date(2026, 7, 9)
    sessions = [
        _session(_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 20), 120),  # today
        _session(_dt(2026, 7, 8, 9, 0), _dt(2026, 7, 8, 9, 40), 180),  # yesterday
        _session(_dt(2026, 7, 9, 10, 0), _dt(2026, 7, 9, 10, 1), 0),  # abandoned
    ]
    total, recent, streak, longest = project_session_metrics(sessions, today=today)
    assert total == 300  # 120 + 180; abandoned banks 0
    assert recent == 300  # both qualifying inside the 7-day window
    assert streak == 2  # 7/9 and 7/8
    assert longest == 2


def test_project_metrics_recent_window_excludes_old_xp() -> None:
    today = date(2026, 7, 9)
    sessions = [
        _session(_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 20), 120),  # today
        _session(_dt(2026, 7, 1, 9, 0), _dt(2026, 7, 1, 9, 40), 180),  # 8 days ago
    ]
    total, recent, streak, longest = project_session_metrics(sessions, today=today)
    assert total == 300  # banked lifetime XP includes the old session
    assert recent == 120  # only today's is inside the 7-day window
    assert streak == 1  # the old session does not chain to today
    assert longest == 1


def test_project_metrics_reads_banked_xp_not_duration() -> None:
    # A 1-minute session that nonetheless has banked 180 XP is read at 180 —
    # the projection trusts settlement, it does not recompute from duration.
    today = date(2026, 7, 9)
    sessions = [_session(_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 1), 180)]
    total, recent, streak, longest = project_session_metrics(sessions, today=today)
    assert total == 180
    assert recent == 180
    assert streak == 1  # xp_awarded > 0 → qualifying → credit day


def test_project_metrics_london_midnight_crossing() -> None:
    # 23:30 UTC on 2026-07-15 is 00:30 London (BST, +1) on 2026-07-16 — the
    # streak credit day is the *London* date, so this chains with a 07-16 day.
    today = date(2026, 7, 16)
    sessions = [
        _session(_dt(2026, 7, 15, 22, 30), _dt(2026, 7, 15, 23, 30), 120),  # → 07-16 London
        _session(_dt(2026, 7, 16, 9, 0), _dt(2026, 7, 16, 9, 40), 180),  # 07-16 London
    ]
    total, recent, streak, longest = project_session_metrics(sessions, today=today)
    assert total == 300
    # Both land on the London day 2026-07-16 → a single credit day, streak 1.
    assert streak == 1
    assert longest == 1


def test_project_metrics_empty() -> None:
    assert project_session_metrics([], today=date(2026, 7, 9)) == (0, 0, 0, 0)


# -- build_gamification_state -----------------------------------------------


def test_build_gamification_state_levels_up_from_banked_sessions() -> None:
    today = date(2026, 7, 9)
    # Six long sessions on consecutive days, each banked at 180 → 1080 XP.
    sessions = [
        _session(_dt(2026, 7, d, 9, 0), _dt(2026, 7, d, 9, 40), 180)
        for d in range(4, 10)
    ]
    state = build_gamification_state(
        student_name="lilymay",
        ended_sessions=sessions,
        achievements=[],
        today=today,
    )
    assert state.exists is True
    assert state.student_name == "lilymay"
    assert state.total_xp == 1080
    assert state.level_name == "Learner"  # ≥ 1000
    assert state.level_number == 5
    assert state.streak_days == 6
    assert state.longest_streak == 6
    # 1080 XP → Level 5 (Learner, floor 1000); next unlock is Level 6's feature.
    assert state.xp_into_level == 80
    assert state.next_unlock is not None
    assert state.next_unlock.level == 6
    assert state.next_unlock.feature == "Exam-style practice questions"


def test_build_gamification_state_banks_achievement_xp() -> None:
    today = date(2026, 7, 9)
    sessions = [_session(_dt(2026, 7, 9, 9, 0), _dt(2026, 7, 9, 9, 40), 180)]
    achievements = [
        HeldAchievementFact(id="first_steps", unlocked_at=_dt(2026, 7, 9), xp_awarded=50),
    ]
    state = build_gamification_state(
        student_name="lilymay",
        ended_sessions=sessions,
        achievements=achievements,
        today=today,
    )
    # total_xp = SUM(session.xp) + SUM(achievement.xp) = 180 + 50.
    assert state.total_xp == 230
    assert len(state.recent_achievements) == 1
    assert state.recent_achievements[0].id == "first_steps"
    assert state.recent_achievements[0].name == "First Steps"
    assert state.recent_achievements[0].xp_awarded == 50
    # first_steps is held → excluded from near; the near set is non-empty.
    assert all(n.id != "first_steps" for n in state.near_achievements)


def test_build_gamification_state_recent_achievements_last_five_newest_first() -> None:
    today = date(2026, 7, 9)
    ids = [
        "first_steps",
        "three_day_run",
        "week_one",
        "first_century",
        "kilo",
        "morning_star",
    ]
    achievements = [
        HeldAchievementFact(id=aid, unlocked_at=_dt(2026, 7, i + 1), xp_awarded=100)
        for i, aid in enumerate(ids)
    ]
    state = build_gamification_state(
        student_name="lilymay",
        ended_sessions=[],
        achievements=achievements,
        today=today,
    )
    # Last 5 by unlock time, newest first.
    assert [r.id for r in state.recent_achievements] == [
        "morning_star",
        "kilo",
        "first_century",
        "week_one",
        "three_day_run",
    ]


def test_build_gamification_state_near_top_three_have_descriptions() -> None:
    today = date(2026, 7, 9)
    # One qualifying morning session (180 XP) — consistent banked achievements:
    # first_steps (a qualifying session) and first_century (180 ≥ 100 XP) are
    # already banked, so near shows only genuinely-unmet criteria.
    sessions = [_session(_dt(2026, 7, 9, 7, 0), _dt(2026, 7, 9, 7, 40), 180)]
    achievements = [
        HeldAchievementFact(id="first_steps", unlocked_at=_dt(2026, 7, 9), xp_awarded=50),
        HeldAchievementFact(
            id="first_century", unlocked_at=_dt(2026, 7, 9), xp_awarded=50
        ),
    ]
    state = build_gamification_state(
        student_name="lilymay",
        ended_sessions=sessions,
        achievements=achievements,
        today=today,
    )
    assert len(state.near_achievements) == 3
    for near in state.near_achievements:
        assert near.description  # non-empty static criterion string
        assert 0 <= near.progress <= near.target
    # Closest-first: three_day_run (1/3) outranks morning_star (1/5).
    assert state.near_achievements[0].id == "three_day_run"
    fractions = [n.progress / n.target for n in state.near_achievements]
    assert fractions == sorted(fractions, reverse=True)


# -- build_student_model_response (enriched wire shape §2.2.1) ---------------


def _conf(topic: str, pct: int) -> TopicConfidence:
    return TopicConfidence(
        student_ref="lilymay",
        topic_ref=topic,
        percentage=pct,
        band=confidence_band_for(pct),
        last_revised_at=_dt(2026, 7, 8),
    )


def _enriched_state(**overrides: object) -> GamificationState:
    base: dict[str, object] = dict(
        exists=True,
        student_name="lilymay",
        streak_days=5,
        level_name="Learner",
        total_xp=1080,
        recent_xp=240,
        longest_streak=8,
        level_number=5,
        xp_into_level=80,
        xp_to_next_level=420,
    )
    base.update(overrides)
    return GamificationState(**base)  # type: ignore[arg-type]


def test_response_original_fields_are_byte_identical() -> None:
    gam = _enriched_state()
    resp = build_student_model_response(
        gam, [_conf("macbeth", 70), _conf("poetry", 55)], fallback_student_id="lilymay"
    )
    # The R05 fields keep their exact names and values (additive enrichment).
    assert resp["student_name"] == "lilymay"
    assert resp["streak_days"] == 5
    assert resp["level_name"] == "Learner"
    assert resp["recent_xp"] == 240
    assert resp["topic_confidence"] == {"macbeth": 0.7, "poetry": 0.55}
    assert resp["data_available"] is True


def test_response_enrichment_fields_present() -> None:
    gam = _enriched_state()
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")
    assert resp["total_xp"] == 1080
    assert resp["level_number"] == 5
    assert resp["xp_into_level"] == 80
    assert resp["xp_to_next_level"] == 420
    assert resp["longest_streak"] == 8
    assert resp["recent_achievements"] == []
    assert resp["near_achievements"] == []
    assert resp["next_unlock"] is None


def test_response_near_and_recent_achievements_are_objects() -> None:
    today = date(2026, 7, 9)
    sessions = [_session(_dt(2026, 7, 9, 7, 0), _dt(2026, 7, 9, 7, 40), 180)]
    gam = build_gamification_state(
        student_name="lilymay",
        ended_sessions=sessions,
        achievements=[
            HeldAchievementFact(
                id="first_steps", unlocked_at=_dt(2026, 7, 9), xp_awarded=50
            )
        ],
        today=today,
    )
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")

    near = resp["near_achievements"]
    assert isinstance(near, list) and near
    assert set(near[0].keys()) == {
        "id",
        "name",
        "description",
        "progress",
        "target",
        "hint",
    }

    recent = resp["recent_achievements"]
    assert isinstance(recent, list) and recent
    assert set(recent[0].keys()) == {"id", "name", "unlocked_at", "xp_awarded"}
    # unlocked_at serialises as an ISO-8601 string.
    assert recent[0]["unlocked_at"] == _dt(2026, 7, 9).isoformat()


def test_response_data_available_false_when_empty() -> None:
    gam = _enriched_state(
        streak_days=0,
        level_name="Beginner",
        total_xp=0,
        recent_xp=0,
        longest_streak=0,
        level_number=1,
        xp_into_level=0,
        xp_to_next_level=100,
    )
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")
    assert resp["data_available"] is False
    assert resp["topic_confidence"] == {}
    assert resp["near_achievements"] == []


def test_response_data_available_true_on_confidence_only() -> None:
    gam = _enriched_state(total_xp=0, recent_xp=0)
    resp = build_student_model_response(
        gam, [_conf("macbeth", 40)], fallback_student_id="lilymay"
    )
    assert resp["data_available"] is True
    assert resp["topic_confidence"] == {"macbeth": 0.4}


def test_response_name_falls_back_to_student_id() -> None:
    gam = GamificationState(exists=True, student_name=None)
    resp = build_student_model_response(gam, [], fallback_student_id="lilymay")
    assert resp["student_name"] == "lilymay"
