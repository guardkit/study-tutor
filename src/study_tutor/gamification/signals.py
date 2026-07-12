"""W2 capture-wave signals (scope §3 W2 row / §4) — the derived facts the W2
achievement tranche reads (spec §2.3 note).

:class:`W2Signals` is the bundle the W2 catalog
(:mod:`study_tutor.gamification.catalog_w2`) evaluates against — the Mastery /
Exploration / Growth signals the store assembles at settlement from the durable
capture surface (canonical ``session.text_name``, ``session.quotes_embedded``,
per-turn ``session_turn.ao_scaffolded``, and ``topic_confidence`` +
``topic_confidence_history``). Every field defaults to empty / zero so a settlement
with no capture state fires **nothing** (the vacuous-fire guard — spec test
requirement).

The pure derivation helpers here (``compute_mastered_texts``,
``genre_week_achieved``, …) hold the binding rulings so they can be unit-tested
without a database:

* **R1** — a text is *mastered* when the **mean** confidence over its studied
  topics is ≥ 80, gated on **≥ 3** distinct studied topics for that text.
* **R5** — No Weak Spots only evaluates once **≥ 5** distinct topics are studied.
* **R6** — Climbing / Breakthrough measure percentage-**points** gained over a
  rolling **7-day** window (cumulative across the window, so 25 points needs
  several capped sessions — intentionally slow).
* **R7** — the Genre Gatherer week is a **Monday–Sunday London** calendar week.
* **R8** — quotes are corpus-hit counts from the deterministic quote verifier
  (assembled upstream; this module only sums/compares).
* **R9** — Six-AO Sampler reads Coach-observed per-turn AOs captured on
  ``session_turn.ao_scaffolded``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

from study_tutor.gamification.texts import Era, Genre, genre_for, era_for

#: The six GCSE English Literature Assessment Objectives — Six-AO Sampler needs a
#: single session that scaffolded all of them (design §5.4, R9).
ALL_ASSESSMENT_OBJECTIVES: frozenset[str] = frozenset(
    {"AO1", "AO2", "AO3", "AO4", "AO5", "AO6"}
)

#: A text is "mastered" (R1) at this mean confidence over its studied topics.
TEXT_MASTERY_THRESHOLD: int = 80
#: R1 breadth gate — a text needs at least this many distinct studied topics
#: before its mean counts, so one strong topic can't award text mastery.
TEXT_MASTERY_MIN_TOPICS: int = 3
#: R5 — No Weak Spots needs at least this many distinct studied topics.
NO_WEAK_SPOTS_MIN_TOPICS: int = 5
#: design §6.1 — Developing floor; No Weak Spots requires every studied topic
#: to be at or above it.
DEVELOPING_FLOOR: int = 40
#: R6 rolling window (days) for the Climbing / Breakthrough confidence gains.
GROWTH_WINDOW_DAYS: int = 7


@dataclass(frozen=True)
class W2Signals:
    """Derived W2 capture-wave signals for one settlement (all counts include the
    session being settled, mirroring the W1 :class:`AchievementContext` posture).

    Every field is default-empty so an empty/sparse state fires no W2 achievement.
    """

    #: Canonical text slugs whose mean confidence ≥ 80 over ≥ 3 studied topics (R1).
    mastered_texts: frozenset[str] = frozenset()
    #: Settled sessions on the Power & Conflict poetry cluster (Poetry Pioneer).
    poetry_pioneer_sessions: int = 0
    #: Latest confidence on the unseen-poetry approach topic (Unseen Ready).
    unseen_confidence: int = 0
    #: Content-gated (R10): the Power & Conflict 15-poem manifest is not in the
    #: repo, so this never becomes True — Poetry Progenitor cannot fire.
    poetry_progenitor_ready: bool = False
    #: Distinct canonical set texts studied (Set Text Explorer).
    distinct_text_count: int = 0
    #: A Monday–Sunday London week covered poetry + drama + prose (Genre Gatherer, R7).
    genre_week_achieved: bool = False
    #: Distinct eras studied (Historical Horizon needs Shakespeare + 19th-C novel
    #: + modern drama).
    eras_covered: frozenset[Era] = field(default_factory=frozenset)
    #: A single session scaffolded all of AO1–AO6 (Six-AO Sampler, R9).
    six_ao_session: bool = False
    #: Max confidence points gained on any topic over a rolling 7-day window (R6).
    max_confidence_gain_7d: int = 0
    #: Cumulative corpus-hit quotes embedded across sessions (Quote Champion/Master, R8).
    total_quotes_embedded: int = 0
    #: Signal-gated: no comparative-writing rating is captured this wave, so this
    #: never becomes True — Comparative Climber cannot fire.
    comparative_climber_ready: bool = False
    #: Distinct studied topics (the R5 gate for No Weak Spots).
    studied_topic_count: int = 0
    #: Minimum confidence over the studied topics (No Weak Spots needs ≥ 40).
    min_topic_confidence: int = 0


# ---------------------------------------------------------------------------
# Pure derivation helpers (the binding rulings — unit-tested without a DB)
# ---------------------------------------------------------------------------


def compute_mastered_texts(
    topic_text_confidences: Iterable[tuple[str, str, int]],
    *,
    threshold: int = TEXT_MASTERY_THRESHOLD,
    min_topics: int = TEXT_MASTERY_MIN_TOPICS,
) -> frozenset[str]:
    """Canonical slugs a student has *mastered* the text of (R1).

    ``topic_text_confidences`` is an iterable of ``(topic_name, text_slug,
    latest_percentage)`` — one per distinct studied topic associated with a text.
    A text is mastered when the **mean** latest confidence over its studied topics
    is ≥ ``threshold`` **and** it has ≥ ``min_topics`` distinct studied topics.

    The breadth gate is what stops a single strong topic ("Lady Macbeth's
    ambition" at 90) awarding "Macbeth Master" — mastery means breadth, not one
    peak (scope §8 R1(a)).
    """
    by_text: dict[str, dict[str, int]] = {}
    for topic_name, text_slug, percentage in topic_text_confidences:
        if not text_slug:
            continue
        by_text.setdefault(text_slug, {})[topic_name] = percentage

    mastered: set[str] = set()
    for text_slug, topic_pcts in by_text.items():
        if len(topic_pcts) < min_topics:
            continue
        mean = sum(topic_pcts.values()) / len(topic_pcts)
        if mean >= threshold:
            mastered.add(text_slug)
    return frozenset(mastered)


def london_iso_week(day: date) -> tuple[int, int]:
    """The ISO ``(year, week)`` a London calendar date falls in — a Mon–Sun week
    key (R7). ``day`` must already be a London-local date."""
    iso = day.isocalendar()
    return (iso[0], iso[1])


def genre_week_achieved(
    session_dates_and_texts: Iterable[tuple[date, str | None]],
) -> bool:
    """Whether any Monday–Sunday London week covers poetry + drama + prose (R7).

    ``session_dates_and_texts`` is ``(london_credit_date, text_slug)`` per settled
    session. Sessions whose text has no known genre are ignored.
    """
    weeks: dict[tuple[int, int], set[Genre]] = {}
    for day, text_slug in session_dates_and_texts:
        genre = genre_for(text_slug)
        if genre is None:
            continue
        weeks.setdefault(london_iso_week(day), set()).add(genre)
    required = {Genre.POETRY, Genre.DRAMA, Genre.PROSE}
    return any(required <= genres for genres in weeks.values())


def eras_covered(text_slugs: Iterable[str | None]) -> frozenset[Era]:
    """The distinct :class:`Era` values studied across ``text_slugs`` (Historical
    Horizon reads this; a slug with no known era is ignored)."""
    covered = {era for slug in text_slugs if (era := era_for(slug)) is not None}
    return frozenset(covered)


def max_confidence_gain_over_window(
    history: Iterable[tuple[str, date, int]],
    *,
    window_days: int = GROWTH_WINDOW_DAYS,
) -> int:
    """Max confidence **points** gained on any one topic within a rolling window (R6).

    ``history`` is ``(topic_name, recorded_date, percentage)`` rows (the
    ``topic_confidence_history`` audit trail). For each topic the entries are
    sorted by date and every ordered pair within ``window_days`` is measured; the
    largest later-minus-earlier gain across all topics is returned (0 when no
    positive gain exists). The gain is cumulative across the window, so a 25-point
    Breakthrough legitimately needs several capped sessions inside 7 days.
    """
    by_topic: dict[str, list[tuple[date, int]]] = {}
    for topic_name, recorded_date, percentage in history:
        by_topic.setdefault(topic_name, []).append((recorded_date, percentage))

    best = 0
    span = timedelta(days=window_days)
    for entries in by_topic.values():
        entries.sort(key=lambda item: item[0])
        for i, (start_date, start_pct) in enumerate(entries):
            for later_date, later_pct in entries[i + 1 :]:
                if later_date - start_date > span:
                    break
                best = max(best, later_pct - start_pct)
    return best


def any_six_ao_session(session_ao_sets: Iterable[Iterable[str]]) -> bool:
    """Whether any single session scaffolded all six AOs (Six-AO Sampler, R9).

    ``session_ao_sets`` is one iterable of observed AO codes per session (the
    distinct non-null ``session_turn.ao_scaffolded`` values for that session).
    """
    return any(
        ALL_ASSESSMENT_OBJECTIVES <= {ao for ao in aos if ao}
        for aos in session_ao_sets
    )


__all__ = [
    "ALL_ASSESSMENT_OBJECTIVES",
    "DEVELOPING_FLOOR",
    "GROWTH_WINDOW_DAYS",
    "NO_WEAK_SPOTS_MIN_TOPICS",
    "TEXT_MASTERY_MIN_TOPICS",
    "TEXT_MASTERY_THRESHOLD",
    "W2Signals",
    "any_six_ao_session",
    "compute_mastered_texts",
    "eras_covered",
    "genre_week_achieved",
    "london_iso_week",
    "max_confidence_gain_over_window",
]
