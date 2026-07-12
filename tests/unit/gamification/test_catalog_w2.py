"""Unit tests for the W2 achievement catalog (S-E4 / design §5 verbatim).

Each of the 17 W2 achievements is tested to fire under the right signals and —
critically — the vacuous-fire guard: with empty/sparse ``W2Signals`` NOTHING
unlocks. The two gated-OFF achievements (Poetry Progenitor, Comparative Climber)
never fire even under otherwise-rich state.
"""
from __future__ import annotations

from study_tutor.gamification.catalog import AchievementContext
from study_tutor.gamification.catalog_w2 import W2_CATALOG, W2_CATALOG_BY_ID
from study_tutor.gamification.signals import W2Signals
from study_tutor.gamification.texts import Era


def _ctx(w2: W2Signals) -> AchievementContext:
    """A W1-empty context carrying the given W2 signals."""
    return AchievementContext(
        streak_days=0,
        total_xp=0,
        level=1,
        morning_count=0,
        evening_count=0,
        qualifying_sessions=0,
        w2=w2,
    )


def _unlocked_ids(w2: W2Signals) -> set[str]:
    ctx = _ctx(w2)
    return {a.id for a in W2_CATALOG if a.is_unlocked(ctx)}


# -- Vacuous-fire guard: empty/sparse state fires nothing -------------------


def test_no_w2_achievement_fires_on_empty_signals() -> None:
    assert _unlocked_ids(W2Signals()) == set()


def test_sparse_signals_below_thresholds_fire_nothing() -> None:
    w2 = W2Signals(
        poetry_pioneer_sessions=1,
        unseen_confidence=79,
        distinct_text_count=2,
        max_confidence_gain_7d=9,
        total_quotes_embedded=9,
        studied_topic_count=4,
        min_topic_confidence=90,
    )
    assert _unlocked_ids(w2) == set()


# -- Catalog completeness ----------------------------------------------------


def test_w2_catalog_has_17_entries_with_design_names_and_xp() -> None:
    assert len(W2_CATALOG) == 17
    expected = {
        "macbeth_master": ("Macbeth Master", 500),
        "poetry_pioneer": ("Poetry Pioneer", 300),
        "poetry_progenitor": ("Poetry Progenitor", 700),
        "christmas_carol_champion": ("Christmas Carol Champion", 500),
        "inspectors_apprentice": ("Inspector's Apprentice", 500),
        "jekyll_hyde_savant": ("Jekyll & Hyde Savant", 500),
        "unseen_ready": ("Unseen Ready", 500),
        "set_text_explorer": ("Set Text Explorer", 200),
        "genre_gatherer": ("Genre Gatherer", 300),
        "historical_horizon": ("Historical Horizon", 400),
        "six_ao_sampler": ("Six-AO Sampler", 500),
        "climbing": ("Climbing", 200),
        "breakthrough": ("Breakthrough", 500),
        "comparative_climber": ("Comparative Climber", 300),
        "quote_champion": ("Quote Champion", 250),
        "quote_master": ("Quote Master", 600),
        "no_weak_spots": ("No Weak Spots", 600),
    }
    actual = {a.id: (a.name, a.xp) for a in W2_CATALOG}
    assert actual == expected


# -- Mastery ----------------------------------------------------------------


def test_macbeth_master_fires_on_mastered_text() -> None:
    assert _unlocked_ids(W2Signals(mastered_texts=frozenset({"macbeth"}))) == {
        "macbeth_master"
    }


def test_named_text_masters_fire_independently() -> None:
    assert "christmas_carol_champion" in _unlocked_ids(
        W2Signals(mastered_texts=frozenset({"a_christmas_carol"}))
    )
    assert "inspectors_apprentice" in _unlocked_ids(
        W2Signals(mastered_texts=frozenset({"an_inspector_calls"}))
    )
    assert "jekyll_hyde_savant" in _unlocked_ids(
        W2Signals(mastered_texts=frozenset({"jekyll_and_hyde"}))
    )


def test_poetry_pioneer_needs_two_sessions() -> None:
    assert _unlocked_ids(W2Signals(poetry_pioneer_sessions=2)) == {"poetry_pioneer"}
    assert "poetry_pioneer" not in _unlocked_ids(
        W2Signals(poetry_pioneer_sessions=1)
    )


def test_unseen_ready_needs_80() -> None:
    assert _unlocked_ids(W2Signals(unseen_confidence=80)) == {"unseen_ready"}
    assert "unseen_ready" not in _unlocked_ids(W2Signals(unseen_confidence=79))


# -- Exploration ------------------------------------------------------------


def test_set_text_explorer_needs_three_texts() -> None:
    assert _unlocked_ids(W2Signals(distinct_text_count=3)) == {"set_text_explorer"}
    assert "set_text_explorer" not in _unlocked_ids(W2Signals(distinct_text_count=2))


def test_genre_gatherer_fires_on_genre_week() -> None:
    assert _unlocked_ids(W2Signals(genre_week_achieved=True)) == {"genre_gatherer"}


def test_historical_horizon_needs_all_three_eras() -> None:
    all_three = frozenset(
        {Era.SHAKESPEARE, Era.NINETEENTH_CENTURY_NOVEL, Era.MODERN_DRAMA}
    )
    assert _unlocked_ids(W2Signals(eras_covered=all_three)) == {"historical_horizon"}
    two = frozenset({Era.SHAKESPEARE, Era.NINETEENTH_CENTURY_NOVEL})
    assert "historical_horizon" not in _unlocked_ids(W2Signals(eras_covered=two))


def test_six_ao_sampler_fires() -> None:
    assert _unlocked_ids(W2Signals(six_ao_session=True)) == {"six_ao_sampler"}


# -- Growth -----------------------------------------------------------------


def test_climbing_and_breakthrough_thresholds() -> None:
    assert _unlocked_ids(W2Signals(max_confidence_gain_7d=10)) == {"climbing"}
    # 25 points clears both Climbing (10) and Breakthrough (25).
    assert _unlocked_ids(W2Signals(max_confidence_gain_7d=25)) == {
        "climbing",
        "breakthrough",
    }


def test_quote_champion_and_master_thresholds() -> None:
    assert _unlocked_ids(W2Signals(total_quotes_embedded=10)) == {"quote_champion"}
    assert _unlocked_ids(W2Signals(total_quotes_embedded=50)) == {
        "quote_champion",
        "quote_master",
    }


# -- No Weak Spots (R5) -----------------------------------------------------


def test_no_weak_spots_needs_five_topics_all_above_developing() -> None:
    assert _unlocked_ids(
        W2Signals(studied_topic_count=5, min_topic_confidence=40)
    ) == {"no_weak_spots"}


def test_no_weak_spots_r5_guard_under_five_topics() -> None:
    # Four topics all high — must NOT fire (R5 ≥5-topics guard).
    assert "no_weak_spots" not in _unlocked_ids(
        W2Signals(studied_topic_count=4, min_topic_confidence=100)
    )


def test_no_weak_spots_blocked_by_one_weak_topic() -> None:
    assert "no_weak_spots" not in _unlocked_ids(
        W2Signals(studied_topic_count=6, min_topic_confidence=39)
    )


# -- Gated-OFF achievements never fire --------------------------------------


def test_poetry_progenitor_is_content_gated_and_never_fires() -> None:
    # Even with the flag mechanism present, it stays False (no manifest).
    rich = W2Signals(
        mastered_texts=frozenset({"power_and_conflict"}),
        poetry_pioneer_sessions=99,
    )
    assert "poetry_progenitor" not in _unlocked_ids(rich)
    # The mechanism exists in the catalog (R10 — implement, don't invent content).
    assert "poetry_progenitor" in W2_CATALOG_BY_ID


def test_comparative_climber_is_signal_gated_and_never_fires() -> None:
    assert "comparative_climber" not in _unlocked_ids(
        W2Signals(comparative_climber_ready=False)
    )
    assert "comparative_climber" in W2_CATALOG_BY_ID
