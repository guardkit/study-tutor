"""Pure gamification decision core (spec §4.1 / ADR-ARCH-030 D1).

``decide(prior, session, now)`` is a **pure function** — no I/O, injected clock —
that turns the banked prior facts plus one session's facts into a
:class:`GamificationDecision` (XP, level, streak, unlocked achievements,
near-achievements). Purity is what makes settlement replayable, unit-testable
without a database, and byte-identical between the live ``finalize_session`` path
and the ``settle-sessions`` sweep (ADR-ARCH-030 D1/D5).

It shares its London-day helpers and its level/XP tables with the read-side
projection through :mod:`study_tutor.gamification.economy` (the single source of
truth), so live settlement and the read model can never disagree.

Design invariants:

* A **qualifying** session earns XP > 0, i.e. engagement ≥ 120 s (design §13.1
  D5). Only qualifying sessions extend a streak, count toward First Steps, or
  count toward Morning Star / Evening Scholar (R3/R4).
* The **streak credit day** is the London-local date of the session's last turn
  (design §13.1 D6). A qualifying session always has turns.
* Achievement XP **cascades** in the deterministic order streak → XP milestones
  → level milestones, iterated to a fixed point (design §13.1 D7): the catalog
  is authored in that order and the cascade restarts from the top after each
  unlock, so a milestone's own XP can unlock a further one (First Century's +50
  re-checked at 150).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from study_tutor.gamification.catalog import (
    CATALOG,
    CATALOG_BY_ID,
    CATALOG_ORDER,
    AchievementContext,
)
from study_tutor.gamification.economy import (
    level_number_for_total_xp,
    london_date,
    session_xp,
    started_after_evening,
    started_before_morning,
)


# ---------------------------------------------------------------------------
# Fact / decision DTOs (frozen — the pure engine's inputs and output)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriorFacts:
    """Banked learner state *before* the session being settled is counted.

    Assembled inside the settlement transaction (or the sweep) by reading the
    student's other rows, always **excluding** the session under settlement so
    the winner and a later replay reconstruct identical inputs (ADR-ARCH-030 D6).
    """

    #: SUM(session.xp_awarded) + SUM(achievement.xp_awarded) over all OTHER rows.
    total_xp: int = 0
    #: London credit days of the student's other qualifying ended sessions.
    streak_credit_days: frozenset[date] = field(default_factory=frozenset)
    #: Achievement ids the student already holds (excluding this session's).
    held_achievement_ids: frozenset[str] = field(default_factory=frozenset)
    #: Qualifying sessions started before 09:00 London (excluding this one).
    morning_qualifying_count: int = 0
    #: Qualifying sessions started after 19:00 London (excluding this one).
    evening_qualifying_count: int = 0
    #: Qualifying (XP > 0) sessions overall (excluding this one).
    qualifying_session_count: int = 0


@dataclass(frozen=True)
class SessionFacts:
    """The session being settled, in engine terms.

    ``engagement_seconds`` is ``max(ts) − min(ts)`` over the session's turns
    (0 for a zero-turn session, design §13.1 D5). ``last_turn_at`` is the
    session's most recent turn timestamp (the streak credit day derives from it);
    ``None`` for a zero-turn session, which never qualifies anyway.
    """

    engagement_seconds: float
    started_at: datetime
    last_turn_at: datetime | None = None


@dataclass(frozen=True)
class AchievementAward:
    """One newly-unlocked achievement (design §5)."""

    id: str
    name: str
    xp: int


@dataclass(frozen=True)
class NearAchievement:
    """A not-yet-unlocked achievement and how close the learner is (spec §4.1)."""

    id: str
    name: str
    progress: int
    target: int
    hint: str


@dataclass(frozen=True)
class GamificationDecision:
    """The pure settlement outcome (spec §4.1 / ADR-ARCH-030 D1)."""

    xp_awarded: int
    total_xp_after: int
    level_before: int
    level_after: int
    level_up: bool
    streak_days: int
    streak_extended: bool
    unlocked: tuple[AchievementAward, ...] = ()
    near_achievements: tuple[NearAchievement, ...] = ()


# ---------------------------------------------------------------------------
# Pure helpers (shared by decide() and by finalize_session's replay path)
# ---------------------------------------------------------------------------


def _run_length(days: frozenset[date] | set[date], anchor: date) -> int:
    """Consecutive-day run ending at ``anchor`` within ``days`` (design §4.1)."""
    if anchor not in days:
        return 0
    length = 0
    cursor = anchor
    while cursor in days:
        length += 1
        cursor -= timedelta(days=1)
    return length


def _cascade_unlocks(
    *,
    held: set[str],
    total_xp: int,
    streak_days: int,
    morning_count: int,
    evening_count: int,
    qualifying_sessions: int,
) -> tuple[list[AchievementAward], int]:
    """Iterate the catalog to a fixed point, banking each unlock's XP (design
    §13.1 D7). Returns ``(unlocked_in_catalog_order, total_xp_after)``.

    ``held`` is mutated to include the newly-unlocked ids. The scan restarts
    from the top after every unlock so an earlier-in-catalog achievement enabled
    by a later unlock's XP is still emitted in catalog order — making the live
    order and the replay reconstruction identical.
    """
    unlocked: list[AchievementAward] = []
    while True:
        progressed = False
        for ach in CATALOG:
            if ach.id in held:
                continue
            ctx = AchievementContext(
                streak_days=streak_days,
                total_xp=total_xp,
                level=level_number_for_total_xp(total_xp),
                morning_count=morning_count,
                evening_count=evening_count,
                qualifying_sessions=qualifying_sessions,
            )
            if ach.is_unlocked(ctx):
                held.add(ach.id)
                unlocked.append(AchievementAward(ach.id, ach.name, ach.xp))
                total_xp += ach.xp
                progressed = True
                break
        if not progressed:
            break
    unlocked.sort(key=lambda award: CATALOG_ORDER[award.id])
    return unlocked, total_xp


def _near_achievements(
    *,
    held: set[str],
    total_xp: int,
    streak_days: int,
    level: int,
    morning_count: int,
    evening_count: int,
    qualifying_sessions: int,
) -> tuple[NearAchievement, ...]:
    """Un-held achievements with progress, closest-first (spec §4.1).

    Sorted by completion fraction descending, tie-broken by catalog order, so
    the projection can take the top N deterministically.
    """
    ctx = AchievementContext(
        streak_days=streak_days,
        total_xp=total_xp,
        level=level,
        morning_count=morning_count,
        evening_count=evening_count,
        qualifying_sessions=qualifying_sessions,
    )
    near: list[NearAchievement] = []
    for ach in CATALOG:
        if ach.id in held:
            continue
        near.append(
            NearAchievement(
                id=ach.id,
                name=ach.name,
                progress=ach.progress(ctx),
                target=ach.target,
                hint=ach.rendered_hint(ctx),
            )
        )
    near.sort(
        key=lambda n: (-(n.progress / n.target if n.target else 0.0), CATALOG_ORDER[n.id])
    )
    return tuple(near)


# ---------------------------------------------------------------------------
# The pure decision function
# ---------------------------------------------------------------------------


def decide(
    prior: PriorFacts, session: SessionFacts, now: datetime
) -> GamificationDecision:
    """Settle one session against banked prior facts (spec §4.1).

    Pure and deterministic: identical inputs always yield an identical decision,
    which is what lets the live path and the sweep — and a winner and its replay
    — resolve the same XP, level, streak, and unlock set. ``now`` is accepted for
    interface stability (ADR-ARCH-030 D1) but the outcome depends only on the
    banked facts and the session, never on the wall clock.
    """
    del now  # decision is a pure function of prior + session facts

    xp_awarded = session_xp(session.engagement_seconds)
    qualifying = xp_awarded > 0

    # Streak (only a qualifying session earns a credit day, design §13.1 D5/D6).
    if qualifying:
        credit_source = session.last_turn_at or session.started_at
        credit_day = london_date(credit_source)
        all_days = set(prior.streak_credit_days)
        all_days.add(credit_day)
        streak_days = _run_length(all_days, credit_day)
        streak_extended = credit_day not in prior.streak_credit_days
    else:
        streak_days = 0
        streak_extended = False

    # Start-window counts (Morning Star / Evening Scholar, R3).
    in_morning = qualifying and started_before_morning(session.started_at)
    in_evening = qualifying and started_after_evening(session.started_at)
    morning_count = prior.morning_qualifying_count + (1 if in_morning else 0)
    evening_count = prior.evening_qualifying_count + (1 if in_evening else 0)
    qualifying_sessions = prior.qualifying_session_count + (1 if qualifying else 0)

    total_before = prior.total_xp + xp_awarded
    held = set(prior.held_achievement_ids)
    unlocked, total_after = _cascade_unlocks(
        held=held,
        total_xp=total_before,
        streak_days=streak_days,
        morning_count=morning_count,
        evening_count=evening_count,
        qualifying_sessions=qualifying_sessions,
    )

    level_before = level_number_for_total_xp(prior.total_xp)
    level_after = level_number_for_total_xp(total_after)

    near = _near_achievements(
        held=held,
        total_xp=total_after,
        streak_days=streak_days,
        level=level_after,
        morning_count=morning_count,
        evening_count=evening_count,
        qualifying_sessions=qualifying_sessions,
    )

    return GamificationDecision(
        xp_awarded=xp_awarded,
        total_xp_after=total_after,
        level_before=level_before,
        level_after=level_after,
        level_up=level_after > level_before,
        streak_days=streak_days,
        streak_extended=streak_extended,
        unlocked=tuple(unlocked),
        near_achievements=near,
    )


# ---------------------------------------------------------------------------
# Settlement result (the store's finalize_session return shape)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettlementResult:
    """What ``finalize_session`` returns to the service (spec §4.2).

    ``decision`` is ``None`` only when a settlement fault rolled back the
    savepoint (D4) — the session still ended, ``settled=False``, and the sweep
    will re-settle it. ``replayed`` marks the already-ended replay path (D6).
    The remaining fields carry the ``session.completed`` event facts the service
    emits post-commit (ADR-ARCH-030 D8).
    """

    decision: GamificationDecision | None
    settled: bool
    replayed: bool
    session_id: str
    subject: str
    topic: str | None
    aos_touched: tuple[str, ...]
    duration_seconds: int
    ended_at: datetime
    had_turns: bool


def award_from_banked(achievement_id: str, xp_awarded: int) -> AchievementAward:
    """Rebuild an :class:`AchievementAward` from a banked achievement row.

    The replay path reads ``achievement`` rows (id + banked XP) and looks the
    display name up in the catalog, so a legacy or unknown id degrades to its id
    as the name rather than raising.
    """
    definition = CATALOG_BY_ID.get(achievement_id)
    name = definition.name if definition is not None else achievement_id
    return AchievementAward(id=achievement_id, name=name, xp=xp_awarded)


__all__ = [
    "AchievementAward",
    "GamificationDecision",
    "NearAchievement",
    "PriorFacts",
    "SessionFacts",
    "SettlementResult",
    "award_from_banked",
    "decide",
]
