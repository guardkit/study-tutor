"""Unit tests for the W2 pure signal derivations (S-E4 rulings R1/R6/R7/R9)."""
from __future__ import annotations

from datetime import date

from study_tutor.gamification.signals import (
    W2Signals,
    any_six_ao_session,
    compute_mastered_texts,
    eras_covered,
    genre_week_achieved,
    max_confidence_gain_over_window,
)
from study_tutor.gamification.texts import Era


# -- R1: text mastery = mean over ≥3 studied topics ≥ 80 --------------------


def test_mastered_text_needs_three_topics_at_mean_80() -> None:
    topics = [
        ("ambition", "macbeth", 85),
        ("guilt", "macbeth", 80),
        ("kingship", "macbeth", 78),  # mean = 81 over 3 topics → mastered
    ]
    assert compute_mastered_texts(topics) == frozenset({"macbeth"})


def test_mastered_text_gated_on_three_distinct_topics() -> None:
    # Two very strong topics do NOT master the text (breadth gate, R1).
    topics = [("ambition", "macbeth", 95), ("guilt", "macbeth", 95)]
    assert compute_mastered_texts(topics) == frozenset()


def test_mastered_text_mean_below_threshold_does_not_fire() -> None:
    topics = [
        ("a", "macbeth", 85),
        ("b", "macbeth", 85),
        ("c", "macbeth", 40),  # mean = 70 < 80
    ]
    assert compute_mastered_texts(topics) == frozenset()


def test_mastered_text_ignores_topics_without_text() -> None:
    topics = [("free", None, 100), ("free2", "", 100)]
    assert compute_mastered_texts(topics) == frozenset()


def test_compute_mastered_texts_empty_is_empty() -> None:
    assert compute_mastered_texts([]) == frozenset()


# -- R6: rolling 7-day confidence gain (cumulative) -------------------------


def test_confidence_gain_within_window_is_cumulative() -> None:
    history = [
        ("macbeth ambition", date(2026, 7, 1), 50),
        ("macbeth ambition", date(2026, 7, 3), 60),
        ("macbeth ambition", date(2026, 7, 6), 70),  # +20 over 5 days
    ]
    assert max_confidence_gain_over_window(history) == 20


def test_confidence_gain_excludes_points_outside_window() -> None:
    history = [
        ("t", date(2026, 7, 1), 50),
        ("t", date(2026, 7, 12), 90),  # 11 days apart → outside 7-day window
    ]
    assert max_confidence_gain_over_window(history) == 0


def test_confidence_gain_zero_when_no_increase() -> None:
    history = [("t", date(2026, 7, 1), 60), ("t", date(2026, 7, 2), 55)]
    assert max_confidence_gain_over_window(history) == 0


def test_confidence_gain_empty_history_is_zero() -> None:
    assert max_confidence_gain_over_window([]) == 0


# -- R7: Genre Gatherer — poetry + drama + prose in one Mon–Sun week ---------


def test_genre_week_all_three_genres_same_week() -> None:
    # 2026-07-06 is a Monday; all three within Mon–Sun.
    sessions = [
        (date(2026, 7, 6), "macbeth"),  # drama
        (date(2026, 7, 8), "a_christmas_carol"),  # prose
        (date(2026, 7, 12), "power_and_conflict"),  # poetry (Sun)
    ]
    assert genre_week_achieved(sessions) is True


def test_genre_week_spanning_two_weeks_does_not_fire() -> None:
    sessions = [
        (date(2026, 7, 5), "power_and_conflict"),  # Sunday (prev week)
        (date(2026, 7, 6), "macbeth"),  # Monday (new week)
        (date(2026, 7, 7), "a_christmas_carol"),
    ]
    assert genre_week_achieved(sessions) is False


def test_genre_week_missing_a_genre_does_not_fire() -> None:
    sessions = [
        (date(2026, 7, 6), "macbeth"),  # drama
        (date(2026, 7, 7), "an_inspector_calls"),  # drama
    ]
    assert genre_week_achieved(sessions) is False


# -- Historical Horizon eras ------------------------------------------------


def test_eras_covered_distinct() -> None:
    covered = eras_covered(
        ["macbeth", "a_christmas_carol", "an_inspector_calls", "unknown"]
    )
    assert covered == frozenset(
        {Era.SHAKESPEARE, Era.NINETEENTH_CENTURY_NOVEL, Era.MODERN_DRAMA}
    )


# -- R9: Six-AO Sampler = a single session covering AO1–AO6 ------------------


def test_six_ao_session_fires_when_one_session_covers_all() -> None:
    sessions = [{"AO1", "AO2", "AO3", "AO4", "AO5", "AO6"}]
    assert any_six_ao_session(sessions) is True


def test_six_ao_session_needs_all_in_the_same_session() -> None:
    # Two sessions that together cover six AOs do NOT count (R9).
    sessions = [{"AO1", "AO2", "AO3"}, {"AO4", "AO5", "AO6"}]
    assert any_six_ao_session(sessions) is False


def test_six_ao_session_empty_is_false() -> None:
    assert any_six_ao_session([]) is False
    assert any_six_ao_session([set()]) is False


# -- Vacuous default ---------------------------------------------------------


def test_default_w2signals_is_empty() -> None:
    w2 = W2Signals()
    assert w2.mastered_texts == frozenset()
    assert w2.total_quotes_embedded == 0
    assert w2.studied_topic_count == 0
    assert w2.six_ao_session is False
