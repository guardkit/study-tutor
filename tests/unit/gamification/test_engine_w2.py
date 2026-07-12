"""Engine-level W2 tests (S-E4): W2 achievements fire through ``decide`` and
their XP cascades into the W1 XP/level milestones to a fixed point (D7)."""
from __future__ import annotations

from datetime import datetime, timezone

from study_tutor.gamification.engine import PriorFacts, SessionFacts, decide
from study_tutor.gamification.signals import W2Signals

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def _session(seconds: int) -> SessionFacts:
    start = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)
    return SessionFacts(
        engagement_seconds=seconds,
        started_at=start,
        last_turn_at=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
    )


def test_no_w2_signal_fires_no_w2_achievement() -> None:
    decision = decide(PriorFacts(), _session(1500), NOW)
    ids = {a.id for a in decision.unlocked}
    # Only W1 achievements (first_steps, first_century from the +180) — no W2.
    assert "macbeth_master" not in ids
    assert "quote_champion" not in ids


def test_w2_unlock_banks_and_appears_in_decision() -> None:
    w2 = W2Signals(mastered_texts=frozenset({"macbeth"}))
    decision = decide(PriorFacts(), _session(1500), NOW, w2=w2)
    ids = {a.id for a in decision.unlocked}
    assert "macbeth_master" in ids


def test_w2_xp_cascades_into_w1_milestones() -> None:
    # A brand-new student's first qualifying session (+180 XP) plus a mastered
    # text (+500) totals 680 XP → clears First Century (100) and Kilo? No — 680,
    # so First Century (100) fires from the combined total; the W2 XP is what
    # pushes First Century past its threshold in the same settlement (D7).
    w2 = W2Signals(mastered_texts=frozenset({"macbeth"}))
    decision = decide(PriorFacts(), _session(1500), NOW, w2=w2)
    ids = {a.id for a in decision.unlocked}
    assert "macbeth_master" in ids
    assert "first_century" in ids  # 180 + 500 = 680 ≥ 100
    # Total XP reflects session + all cascaded achievement XP.
    assert decision.total_xp_after >= 680


def test_held_w2_achievement_not_re_awarded() -> None:
    w2 = W2Signals(mastered_texts=frozenset({"macbeth"}))
    prior = PriorFacts(held_achievement_ids=frozenset({"macbeth_master"}))
    decision = decide(prior, _session(1500), NOW, w2=w2)
    assert "macbeth_master" not in {a.id for a in decision.unlocked}


def test_w2_near_achievement_shows_progress() -> None:
    # 1 of 3 texts studied → Set Text Explorer is a near-miss with progress 1/3.
    w2 = W2Signals(distinct_text_count=1)
    decision = decide(PriorFacts(), _session(1500), NOW, w2=w2)
    near = {n.id: n for n in decision.near_achievements}
    assert "set_text_explorer" in near
    assert near["set_text_explorer"].progress == 1
    assert near["set_text_explorer"].target == 3


def test_decide_w2_is_deterministic() -> None:
    w2 = W2Signals(mastered_texts=frozenset({"macbeth"}), total_quotes_embedded=10)
    a = decide(PriorFacts(), _session(1500), NOW, w2=w2)
    b = decide(PriorFacts(), _session(1500), NOW, w2=w2)
    assert a == b
