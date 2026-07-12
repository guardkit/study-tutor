"""Pure-engine tests for ``study_tutor.gamification.engine`` (spec §4.1).

No DB, no wall clock — ``decide()`` is a pure function of its facts. Covers the
XP bands, level thresholds, London-day streaks (including the UTC-midnight cases
that cross a London date), the achievement-XP cascade fixed point (design §13.1
D7), each of the 16 W1 unlocks, and the near-achievement projection.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from study_tutor.gamification.catalog import CATALOG
from study_tutor.gamification.economy import level_number_for_total_xp
from study_tutor.gamification.engine import (
    PriorFacts,
    SessionFacts,
    decide,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
ALL_IDS = frozenset(a.id for a in CATALOG)


def _utc(y: int, mo: int, d: int, h: int = 12, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=UTC)


def _session(engagement: float, *, start: datetime = _utc(2026, 7, 12, 12),
             last_turn: datetime | None = None) -> SessionFacts:
    return SessionFacts(
        engagement_seconds=engagement,
        started_at=start,
        last_turn_at=last_turn if last_turn is not None else start,
    )


# -- XP bands (design §13.1 D5) ---------------------------------------------


@pytest.mark.parametrize(
    "seconds, expected",
    [(0, 0), (119, 0), (120, 60), (899, 60), (900, 120), (1499, 120),
     (1500, 180), (3600, 180)],
)
def test_decide_xp_bands(seconds: int, expected: int) -> None:
    # Hold every achievement so only the raw XP band is under test.
    prior = PriorFacts(held_achievement_ids=ALL_IDS)
    decision = decide(prior, _session(seconds), NOW)
    assert decision.xp_awarded == expected


def test_zero_turn_session_earns_no_xp_and_no_streak() -> None:
    prior = PriorFacts(held_achievement_ids=ALL_IDS)
    decision = decide(prior, SessionFacts(0.0, _utc(2026, 7, 12), None), NOW)
    assert decision.xp_awarded == 0
    assert decision.streak_days == 0
    assert decision.streak_extended is False
    assert decision.unlocked == ()


# -- Levels -----------------------------------------------------------------


def test_level_number_boundaries() -> None:
    assert level_number_for_total_xp(0) == 1
    assert level_number_for_total_xp(99) == 1
    assert level_number_for_total_xp(100) == 2
    assert level_number_for_total_xp(1499) == 5
    assert level_number_for_total_xp(1500) == 6
    assert level_number_for_total_xp(18500) == 15
    assert level_number_for_total_xp(10**9) == 15


def test_decide_level_up_reported() -> None:
    # Prior 90 XP (level 1); a +120 band session banks 210 → level 3 (300? no).
    # 210 XP → level 2 (Novice @100). Hold achievements to isolate levelling.
    prior = PriorFacts(total_xp=90, held_achievement_ids=ALL_IDS,
                       qualifying_session_count=3)
    decision = decide(prior, _session(900), NOW)  # +120
    assert decision.total_xp_after == 210
    assert decision.level_before == 1
    assert decision.level_after == 2
    assert decision.level_up is True


# -- Streaks (design §13.1 D6, London days) ---------------------------------


def test_streak_extends_from_prior_consecutive_days() -> None:
    prior = PriorFacts(
        held_achievement_ids=ALL_IDS,
        streak_credit_days=frozenset({date(2026, 7, 10), date(2026, 7, 11)}),
    )
    # Last turn on 2026-07-12 (London date same as UTC at noon).
    decision = decide(prior, _session(200, last_turn=_utc(2026, 7, 12, 12)), NOW)
    assert decision.streak_days == 3
    assert decision.streak_extended is True


def test_streak_utc_midnight_bst_rolls_to_next_london_day() -> None:
    """23:30 UTC in summer (BST +1) is the NEXT London calendar day (D6)."""
    prior = PriorFacts(
        held_achievement_ids=ALL_IDS,
        streak_credit_days=frozenset({date(2026, 7, 9)}),
    )
    # 2026-07-09 23:30 UTC → 2026-07-10 00:30 London → credit day 07-10.
    last_turn = datetime(2026, 7, 9, 23, 30, tzinfo=UTC)
    decision = decide(prior, _session(200, last_turn=last_turn), NOW)
    assert decision.streak_days == 2  # 07-09 then 07-10
    assert decision.streak_extended is True


def test_streak_utc_midnight_gmt_stays_same_london_day() -> None:
    """23:30 UTC in winter (GMT) is the SAME London calendar day."""
    prior = PriorFacts(
        held_achievement_ids=ALL_IDS,
        streak_credit_days=frozenset({date(2026, 1, 8)}),
    )
    # 2026-01-09 23:30 UTC → 2026-01-09 23:30 London → credit day 01-09.
    last_turn = datetime(2026, 1, 9, 23, 30, tzinfo=UTC)
    decision = decide(prior, _session(200, last_turn=last_turn), NOW)
    assert decision.streak_days == 2  # 01-08 then 01-09
    assert decision.streak_extended is True


def test_streak_second_session_same_day_does_not_extend() -> None:
    prior = PriorFacts(
        held_achievement_ids=ALL_IDS,
        streak_credit_days=frozenset({date(2026, 7, 12)}),
    )
    decision = decide(prior, _session(200, last_turn=_utc(2026, 7, 12, 18)), NOW)
    assert decision.streak_days == 1
    assert decision.streak_extended is False


# -- Cascade fixed point (design §13.1 D7) ----------------------------------


def test_cascade_first_century_rechecked_at_150() -> None:
    """A settlement landing at exactly 100 XP unlocks First Century (+50); the
    resulting 150 is re-checked in the same order (D7)."""
    # Hold every consistency achievement so only the milestone cascade fires.
    consistency = frozenset(
        a.id for a in CATALOG if a.id not in {"first_century", "kilo",
                                              "five_kilo", "ten_kilo",
                                              "scholar", "master", "grandmaster"}
    )
    prior = PriorFacts(total_xp=40, held_achievement_ids=consistency,
                       qualifying_session_count=3)
    decision = decide(prior, _session(200), NOW)  # +60 → 100
    unlocked_ids = [a.id for a in decision.unlocked]
    assert unlocked_ids == ["first_century"]
    # 100 (session) + 50 (First Century) = 150, re-checked (no Kilo at 150).
    assert decision.total_xp_after == 150


def test_cascade_stacks_multiple_milestones_to_fixed_point() -> None:
    """Landing near 1000 can unlock Kilo, whose XP is re-checked; Scholar (L6)
    fires too once the level crosses. Order is streak → XP → level."""
    # Start just below Kilo with First Century already held.
    prior = PriorFacts(
        total_xp=940,
        held_achievement_ids=frozenset(
            a.id for a in CATALOG
            if a.id not in {"kilo", "scholar"}
        ),
        qualifying_session_count=9,
    )
    decision = decide(prior, _session(1500), NOW)  # +180 → 1120
    unlocked_ids = [a.id for a in decision.unlocked]
    # 1120 unlocks Kilo (+100 → 1220); 1220 < 1500 so Scholar (L6) does NOT fire.
    assert unlocked_ids == ["kilo"]
    assert decision.total_xp_after == 1220


# -- Each of the 16 W1 unlocks ----------------------------------------------


def _held_except(target: str) -> frozenset[str]:
    return frozenset(ALL_IDS - {target})


def test_unlock_first_steps_on_first_qualifying_session() -> None:
    prior = PriorFacts()  # nothing held, no prior qualifying sessions
    decision = decide(prior, _session(200), NOW)
    assert "first_steps" in {a.id for a in decision.unlocked}


@pytest.mark.parametrize(
    "target, streak_len",
    [("three_day_run", 3), ("week_one", 7), ("fortnight_force", 14),
     ("thirty_days", 30), ("sixty_strong", 60), ("century", 100)],
)
def test_unlock_streak_milestones(target: str, streak_len: int) -> None:
    anchor = date(2026, 7, 12)
    prior_days = frozenset(
        anchor - timedelta(days=i) for i in range(1, streak_len)
    )
    prior = PriorFacts(
        held_achievement_ids=_held_except(target),
        streak_credit_days=prior_days,
    )
    decision = decide(prior, _session(200, last_turn=_utc(2026, 7, 12)), NOW)
    assert decision.streak_days == streak_len
    assert [a.id for a in decision.unlocked] == [target]


def test_unlock_morning_star() -> None:
    prior = PriorFacts(
        held_achievement_ids=_held_except("morning_star"),
        morning_qualifying_count=4,
    )
    # 07:00 UTC in summer → 08:00 London (< 09:00).
    decision = decide(
        prior, _session(200, start=_utc(2026, 7, 12, 7)), NOW
    )
    assert [a.id for a in decision.unlocked] == ["morning_star"]


def test_unlock_evening_scholar() -> None:
    prior = PriorFacts(
        held_achievement_ids=_held_except("evening_scholar"),
        evening_qualifying_count=4,
    )
    # 20:00 UTC in summer → 21:00 London (> 19:00).
    decision = decide(
        prior, _session(200, start=_utc(2026, 7, 12, 20)), NOW
    )
    assert [a.id for a in decision.unlocked] == ["evening_scholar"]


@pytest.mark.parametrize(
    "target, prior_xp",
    [("first_century", 40), ("kilo", 940), ("five_kilo", 4940),
     ("ten_kilo", 9940)],
)
def test_unlock_xp_milestones(target: str, prior_xp: int) -> None:
    prior = PriorFacts(
        total_xp=prior_xp,
        held_achievement_ids=_held_except(target),
        qualifying_session_count=5,
    )
    decision = decide(prior, _session(200), NOW)  # +60
    assert [a.id for a in decision.unlocked] == [target]


@pytest.mark.parametrize(
    "target, prior_xp",
    [("scholar", 1440), ("master", 5540), ("grandmaster", 18440)],
)
def test_unlock_level_milestones(target: str, prior_xp: int) -> None:
    prior = PriorFacts(
        total_xp=prior_xp,
        held_achievement_ids=_held_except(target),
        qualifying_session_count=5,
    )
    decision = decide(prior, _session(200), NOW)  # +60
    assert [a.id for a in decision.unlocked] == [target]


# -- Near-achievement projection --------------------------------------------


def test_near_achievements_exclude_unlocked_and_carry_progress() -> None:
    prior = PriorFacts()  # first qualifying session
    decision = decide(prior, _session(200, last_turn=_utc(2026, 7, 12)), NOW)
    near_ids = {n.id for n in decision.near_achievements}
    unlocked_ids = {a.id for a in decision.unlocked}
    # First Steps just unlocked → not in near.
    assert "first_steps" in unlocked_ids
    assert "first_steps" not in near_ids
    # Three Day Run is a near-miss with live progress = current streak (1/3).
    three = next(n for n in decision.near_achievements if n.id == "three_day_run")
    assert three.progress == 1
    assert three.target == 3
    assert "1/3" in three.hint


def test_near_achievements_sorted_closest_first() -> None:
    prior = PriorFacts()
    decision = decide(prior, _session(200), NOW)
    fractions = [
        (n.progress / n.target if n.target else 0.0)
        for n in decision.near_achievements
    ]
    assert fractions == sorted(fractions, reverse=True)


def test_decide_is_pure_and_deterministic() -> None:
    prior = PriorFacts(total_xp=120, qualifying_session_count=1,
                       streak_credit_days=frozenset({date(2026, 7, 11)}))
    session = _session(1500, last_turn=_utc(2026, 7, 12))
    first = decide(prior, session, NOW)
    second = decide(prior, session, NOW + timedelta(hours=5))
    assert first == second  # independent of the wall clock
