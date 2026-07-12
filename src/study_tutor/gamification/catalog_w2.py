"""W2 achievement tranche (scope §3 W2 row; design §5 names/XP verbatim).

The 17 capture-wave achievements — 7 Mastery, 4 Exploration, 5 Growth, plus
``no_weak_spots`` — evaluated against the :class:`~study_tutor.gamification.signals.W2Signals`
the store assembles at settlement. Each name and XP value is
``docs/gamification/design.md`` §5 **verbatim** (spec non-negotiable rule 4).

Duck-typed to the W1 :class:`~study_tutor.gamification.catalog.AchievementDef`
interface (``id`` / ``name`` / ``xp`` / ``target`` / ``description`` / ``hint`` /
``is_unlocked(ctx)`` / ``progress(ctx)`` / ``rendered_hint(ctx)``) so the engine's
one cascade iterates W1 + W2 uniformly to a fixed point (design §13.1 D7): a W2
unlock's XP re-triggers the W1 XP/level milestones in the same settlement.

Binding rulings live in :mod:`study_tutor.gamification.signals`: R1 (text
mean-over-≥3-topics), R5 (No Weak Spots ≥5 topics), R6 (Climbing/Breakthrough
7-day points), R7 (Genre Gatherer Mon–Sun week), R8 (Quote Champion/Master =
verifier corpus hits), R9 (Six-AO Sampler = Coach-observed per-turn AOs).

Two achievements are **gated OFF** this wave and can never fire — a dated builder
note records why (see below):

* **Poetry Progenitor (R10)** — content-gated. It needs a Power & Conflict
  15-poem manifest to decide "mastered the full cluster"; that content is not in
  the repo, so the mechanism is present but ``poetry_progenitor_ready`` is never
  set True. No content is invented.
* **Comparative Climber** — signal-gated. Its criterion ("a first comparative
  paragraph rated ≥ the student's baseline analytical writing") needs a
  comparative-writing quality rating that this wave captures no signal for
  (the ×1.25 / per-turn-rating tranche is out of scope). Mechanism present;
  ``comparative_climber_ready`` never set True.

> **Builder note — 2026-07-13 (S-E4, two W2 achievements gated OFF).** Poetry
> Progenitor and Comparative Climber ship as catalog entries with live
> progress/near-miss mechanisms but predicates that read flags this wave never
> raises: Poetry Progenitor needs a Power & Conflict poem manifest the repo does
> not carry (R10 — no content invented), and Comparative Climber needs a
> comparative-writing rating no capture signal exists for yet. Both fire the day
> their gating fact is captured (a manifest module for the first; a per-turn
> writing-rating signal for the second) with **no economy change** — the names
> and +700 / +300 XP are design §5 verbatim and unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from study_tutor.gamification.catalog import AchievementContext
from study_tutor.gamification.signals import (
    NO_WEAK_SPOTS_MIN_TOPICS,
    TEXT_MASTERY_THRESHOLD,
    W2Signals,
)
from study_tutor.gamification.texts import (
    HISTORICAL_HORIZON_ERAS,
    POWER_AND_CONFLICT_SLUG,
)

# Canonical text slugs the named Mastery achievements key on.
_MACBETH = "macbeth"
_CHRISTMAS_CAROL = "a_christmas_carol"
_INSPECTOR_CALLS = "an_inspector_calls"
_JEKYLL_HYDE = "jekyll_and_hyde"


@dataclass(frozen=True)
class W2AchievementDef:
    """One W2 catalog entry — a predicate + progress read over :class:`W2Signals`.

    Duck-types the W1 ``AchievementDef`` surface the engine cascade/near-projection
    call. ``predicate`` decides the unlock; ``progress_fn`` gives current progress
    toward :attr:`target` (capped at target so the interpolated hint reads sanely).
    """

    id: str
    name: str
    xp: int
    target: int
    description: str
    hint: str
    predicate: Callable[[W2Signals], bool]
    progress_fn: Callable[[W2Signals], int]

    def is_unlocked(self, ctx: AchievementContext) -> bool:
        """Whether this session's W2 signals satisfy the criterion."""
        return self.predicate(ctx.w2)

    def progress(self, ctx: AchievementContext) -> int:
        """Current progress toward :attr:`target` (never above it)."""
        return min(self.progress_fn(ctx.w2), self.target)

    def rendered_hint(self, ctx: AchievementContext) -> str:
        """The static hint with live ``{progress}`` / ``{target}`` interpolation."""
        return self.hint.format(progress=self.progress(ctx), target=self.target)


def _mastered(slug: str) -> Callable[[W2Signals], bool]:
    """Predicate: the given canonical text slug is in ``mastered_texts`` (R1)."""
    return lambda w2: slug in w2.mastered_texts


def _mastered_progress(slug: str) -> Callable[[W2Signals], int]:
    """Progress: 1 once the text is mastered, else 0 (boolean mastery)."""
    return lambda w2: 1 if slug in w2.mastered_texts else 0


def _never(_w2: W2Signals) -> bool:
    """Gated-OFF predicate — never fires (content/signal-gated achievements)."""
    return False


def _zero(_w2: W2Signals) -> int:
    """Gated-OFF progress — always 0 (a gated achievement is never 'near')."""
    return 0


def _historical_horizon_progress(w2: W2Signals) -> int:
    """How many of the three Historical Horizon eras are covered (design §5.4)."""
    return len(HISTORICAL_HORIZON_ERAS & w2.eras_covered)


def _no_weak_spots_unlocked(w2: W2Signals) -> bool:
    """R5: ≥5 studied topics AND none below the Developing floor (design §5.3)."""
    return (
        w2.studied_topic_count >= NO_WEAK_SPOTS_MIN_TOPICS
        and w2.min_topic_confidence >= 40
    )


#: The W2 catalog, in category order (Mastery → Exploration → Growth →
#: No Weak Spots). Placed AFTER the W1 catalog in the engine's cascade so a W2
#: unlock's XP re-checks the W1 XP/level milestones to a fixed point (D7).
W2_CATALOG: tuple[W2AchievementDef, ...] = (
    # -- Mastery (design §5.2) --------------------------------------------
    W2AchievementDef(
        "macbeth_master", "Macbeth Master", 500, 1,
        "Reach 80% average confidence across your studied Macbeth topics.",
        "Master Macbeth by averaging 80% across at least 3 studied topics.",
        _mastered(_MACBETH), _mastered_progress(_MACBETH),
    ),
    W2AchievementDef(
        "poetry_pioneer", "Poetry Pioneer", 300, 2,
        "Complete 2 sessions on Power & Conflict poetry.",
        "Study Power & Conflict poetry {progress}/{target} times.",
        lambda w2: w2.poetry_pioneer_sessions >= 2,
        lambda w2: w2.poetry_pioneer_sessions,
    ),
    W2AchievementDef(
        "poetry_progenitor", "Poetry Progenitor", 700, 1,
        "Reach 80% confidence across the full Power & Conflict cluster.",
        "Master the whole Power & Conflict cluster.",
        _never, _zero,  # content-gated (R10) — no 15-poem manifest in the repo.
    ),
    W2AchievementDef(
        "christmas_carol_champion", "Christmas Carol Champion", 500, 1,
        "Reach 80% average confidence across your studied A Christmas Carol topics.",
        "Master A Christmas Carol by averaging 80% across at least 3 studied topics.",
        _mastered(_CHRISTMAS_CAROL), _mastered_progress(_CHRISTMAS_CAROL),
    ),
    W2AchievementDef(
        "inspectors_apprentice", "Inspector's Apprentice", 500, 1,
        "Reach 80% average confidence across your studied An Inspector Calls topics.",
        "Master An Inspector Calls by averaging 80% across at least 3 studied topics.",
        _mastered(_INSPECTOR_CALLS), _mastered_progress(_INSPECTOR_CALLS),
    ),
    W2AchievementDef(
        "jekyll_hyde_savant", "Jekyll & Hyde Savant", 500, 1,
        "Reach 80% average confidence across your studied Jekyll and Hyde topics.",
        "Master Jekyll and Hyde by averaging 80% across at least 3 studied topics.",
        _mastered(_JEKYLL_HYDE), _mastered_progress(_JEKYLL_HYDE),
    ),
    W2AchievementDef(
        "unseen_ready", "Unseen Ready", 500, TEXT_MASTERY_THRESHOLD,
        "Reach 80% confidence on the unseen-poetry approach.",
        "Build unseen-poetry confidence to {progress}/{target}%.",
        lambda w2: w2.unseen_confidence >= TEXT_MASTERY_THRESHOLD,
        lambda w2: w2.unseen_confidence,
    ),
    # -- Exploration (design §5.4) ----------------------------------------
    W2AchievementDef(
        "set_text_explorer", "Set Text Explorer", 200, 3,
        "Study sessions on 3 different set texts.",
        "Study {progress}/{target} different set texts.",
        lambda w2: w2.distinct_text_count >= 3,
        lambda w2: w2.distinct_text_count,
    ),
    W2AchievementDef(
        "genre_gatherer", "Genre Gatherer", 300, 1,
        "Study poetry, drama and prose in the same week.",
        "Cover poetry, drama and prose within one Monday–Sunday week.",
        lambda w2: w2.genre_week_achieved,
        lambda w2: 1 if w2.genre_week_achieved else 0,
    ),
    W2AchievementDef(
        "historical_horizon", "Historical Horizon", 400, 3,
        "Complete sessions on a 19th-century novel, a Shakespeare text, and a "
        "modern drama.",
        "Cover {progress}/{target} of: 19th-century novel, Shakespeare, modern drama.",
        lambda w2: HISTORICAL_HORIZON_ERAS <= w2.eras_covered,
        _historical_horizon_progress,
    ),
    W2AchievementDef(
        "six_ao_sampler", "Six-AO Sampler", 500, 1,
        "Have a session where each of AO1–AO6 was scaffolded.",
        "Scaffold all six AOs in a single session.",
        lambda w2: w2.six_ao_session,
        lambda w2: 1 if w2.six_ao_session else 0,
    ),
    # -- Growth (design §5.3) ---------------------------------------------
    W2AchievementDef(
        "climbing", "Climbing", 200, 10,
        "Gain 10 percentage points on a topic within a week.",
        "Gain {progress}/{target} confidence points on a topic in one week.",
        lambda w2: w2.max_confidence_gain_7d >= 10,
        lambda w2: w2.max_confidence_gain_7d,
    ),
    W2AchievementDef(
        "breakthrough", "Breakthrough", 500, 25,
        "Gain 25 percentage points on a topic within a week.",
        "Gain {progress}/{target} confidence points on a topic in one week.",
        lambda w2: w2.max_confidence_gain_7d >= 25,
        lambda w2: w2.max_confidence_gain_7d,
    ),
    W2AchievementDef(
        "comparative_climber", "Comparative Climber", 300, 1,
        "Write a first comparative paragraph rated at or above your baseline.",
        "Write a comparative paragraph that meets your analytical baseline.",
        _never, _zero,  # signal-gated — no comparative-writing rating captured yet.
    ),
    W2AchievementDef(
        "quote_champion", "Quote Champion", 250, 10,
        "Use 10 embedded quotations across sessions.",
        "Embed {progress}/{target} verified quotations across your sessions.",
        lambda w2: w2.total_quotes_embedded >= 10,
        lambda w2: w2.total_quotes_embedded,
    ),
    W2AchievementDef(
        "quote_master", "Quote Master", 600, 50,
        "Use 50 embedded quotations across sessions.",
        "Embed {progress}/{target} verified quotations across your sessions.",
        lambda w2: w2.total_quotes_embedded >= 50,
        lambda w2: w2.total_quotes_embedded,
    ),
    # -- No Weak Spots (design §5.3 Growth; broken out with its ≥5 guard, R5) --
    W2AchievementDef(
        "no_weak_spots", "No Weak Spots", 600, NO_WEAK_SPOTS_MIN_TOPICS,
        "Keep every studied topic at or above Developing (40%), across at least "
        "5 studied topics.",
        "Study {progress}/{target} topics with none below 40%.",
        _no_weak_spots_unlocked,
        lambda w2: w2.studied_topic_count,
    ),
)

#: Fast lookup by id (replay reads banked achievement rows → catalog name/xp).
W2_CATALOG_BY_ID: dict[str, W2AchievementDef] = {a.id: a for a in W2_CATALOG}

#: The Power & Conflict slug the assembler counts Poetry Pioneer sessions on,
#: re-exported for the store's convenience.
POETRY_PIONEER_SLUG: str = POWER_AND_CONFLICT_SLUG


__all__ = [
    "POETRY_PIONEER_SLUG",
    "W2_CATALOG",
    "W2_CATALOG_BY_ID",
    "W2AchievementDef",
]
