"""Canonical set-text taxonomy for the W2 capture wave (scope §4.2, R1/R7).

The store keys confidence and topics by *free phrase* ("dramatic irony in
Macbeth"); text-level Mastery achievements and the genre/era Exploration
achievements are impossible without a **canonical text identity** per session.
This module owns that taxonomy:

* :data:`TEXT_TAXONOMY` — the canonical set-text slugs the corpus loader uses
  (underscore-normalised, e.g. ``macbeth`` / ``an_inspector_calls``), each mapped
  to its :class:`Genre` (poetry / drama / prose — the Genre Gatherer axis, R7)
  and :class:`Era` (the Historical Horizon axis: Shakespeare / 19th-century novel
  / modern drama, §5.4).
* :func:`derive_text_name` — the START-time capture (scope §4.2): resolve a
  planner topic phrase (± an explicit hint / subject) to a canonical slug, so the
  session row carries a stable ``text_name`` the Mastery/Exploration signals group
  by. Returns ``None`` when no known set text is recognised (a free-topic session
  is not force-fitted to a text — the achievements simply don't count it).

Slugs are the **corpus** slugs (``knowledge.corpus._derive_text_name`` normalises
file stems the same way: lower-case, ``[-\\s.]+`` → ``_``) so a session's
``text_name`` matches the primary-text chunks the quote verifier reads.

This is a *mechanism*, not a content manifest: the Power & Conflict cluster's
15-poem breakdown (Poetry Progenitor, R10) is NOT here — that is content the repo
does not carry, so Poetry Progenitor stays content-gated (see
:mod:`study_tutor.gamification.catalog_w2`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Genre(str, Enum):
    """The three GCSE English Literature genres — the Genre Gatherer axis (R7)."""

    POETRY = "poetry"
    DRAMA = "drama"
    PROSE = "prose"


class Era(str, Enum):
    """Historical/period grouping — the Historical Horizon axis (design §5.4).

    Historical Horizon requires one session each on a 19th-century novel, a
    Shakespeare text, and a modern drama; the other eras exist so genre/era
    grouping stays honest for texts outside that trio.
    """

    SHAKESPEARE = "shakespeare"
    NINETEENTH_CENTURY_NOVEL = "nineteenth_century_novel"
    MODERN_DRAMA = "modern_drama"
    MODERN_PROSE = "modern_prose"
    POETRY_ANTHOLOGY = "poetry_anthology"
    UNSEEN = "unseen"


@dataclass(frozen=True)
class TextMeta:
    """Canonical metadata for one set text: its display name, genre, and era."""

    slug: str
    display_name: str
    genre: Genre
    era: Era


#: The three eras Historical Horizon requires all of (design §5.4).
HISTORICAL_HORIZON_ERAS: frozenset[Era] = frozenset(
    {Era.SHAKESPEARE, Era.NINETEENTH_CENTURY_NOVEL, Era.MODERN_DRAMA}
)

#: The three genres Genre Gatherer requires all of in one London week (R7).
GENRE_GATHERER_GENRES: frozenset[Genre] = frozenset(
    {Genre.POETRY, Genre.DRAMA, Genre.PROSE}
)

#: The Power & Conflict poetry cluster slug — Poetry Pioneer counts sessions on
#: it (design §5.2). Its 15-poem manifest (Poetry Progenitor, R10) is content the
#: repo does not carry, so that one achievement stays content-gated.
POWER_AND_CONFLICT_SLUG: str = "power_and_conflict"

#: The unseen-poetry approach slug — Unseen Ready reads its confidence (§5.2).
UNSEEN_POETRY_SLUG: str = "unseen_poetry"


#: Canonical set-text taxonomy. Slugs are corpus slugs (underscore-normalised);
#: the common United Learning / AQA 8702 choices, each tagged genre + era. This
#: is a real-but-modest starter set — adding a text here is safe.
TEXT_TAXONOMY: dict[str, TextMeta] = {
    meta.slug: meta
    for meta in (
        # -- Shakespeare (drama) -------------------------------------------
        TextMeta("macbeth", "Macbeth", Genre.DRAMA, Era.SHAKESPEARE),
        TextMeta("romeo_and_juliet", "Romeo and Juliet", Genre.DRAMA, Era.SHAKESPEARE),
        TextMeta("othello", "Othello", Genre.DRAMA, Era.SHAKESPEARE),
        TextMeta("the_tempest", "The Tempest", Genre.DRAMA, Era.SHAKESPEARE),
        # -- 19th-century novels (prose) -----------------------------------
        TextMeta(
            "a_christmas_carol", "A Christmas Carol",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        TextMeta(
            "jekyll_and_hyde", "Jekyll and Hyde",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        TextMeta(
            "great_expectations", "Great Expectations",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        TextMeta(
            "frankenstein", "Frankenstein",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        TextMeta(
            "pride_and_prejudice", "Pride and Prejudice",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        TextMeta(
            "jane_eyre", "Jane Eyre",
            Genre.PROSE, Era.NINETEENTH_CENTURY_NOVEL,
        ),
        # -- Modern drama --------------------------------------------------
        TextMeta(
            "an_inspector_calls", "An Inspector Calls",
            Genre.DRAMA, Era.MODERN_DRAMA,
        ),
        TextMeta("blood_brothers", "Blood Brothers", Genre.DRAMA, Era.MODERN_DRAMA),
        # -- Modern prose --------------------------------------------------
        TextMeta(
            "lord_of_the_flies", "Lord of the Flies",
            Genre.PROSE, Era.MODERN_PROSE,
        ),
        TextMeta("animal_farm", "Animal Farm", Genre.PROSE, Era.MODERN_PROSE),
        # -- Poetry --------------------------------------------------------
        TextMeta(
            POWER_AND_CONFLICT_SLUG, "Power and Conflict",
            Genre.POETRY, Era.POETRY_ANTHOLOGY,
        ),
        TextMeta(
            "love_and_relationships", "Love and Relationships",
            Genre.POETRY, Era.POETRY_ANTHOLOGY,
        ),
        TextMeta(UNSEEN_POETRY_SLUG, "Unseen Poetry", Genre.POETRY, Era.UNSEEN),
    )
}


#: Keyword phrases → canonical slug, matched (longest-first) against a normalised
#: topic phrase. Aliases cover the natural ways a planner topic names a text
#: ("dramatic irony in Macbeth", "An Inspector Calls", "Christmas Carol").
_KEYWORD_TO_SLUG: dict[str, str] = {
    "macbeth": "macbeth",
    "romeo and juliet": "romeo_and_juliet",
    "othello": "othello",
    "the tempest": "the_tempest",
    "tempest": "the_tempest",
    "a christmas carol": "a_christmas_carol",
    "christmas carol": "a_christmas_carol",
    "scrooge": "a_christmas_carol",
    "jekyll and hyde": "jekyll_and_hyde",
    "jekyll": "jekyll_and_hyde",
    "dr jekyll": "jekyll_and_hyde",
    "great expectations": "great_expectations",
    "frankenstein": "frankenstein",
    "pride and prejudice": "pride_and_prejudice",
    "jane eyre": "jane_eyre",
    "an inspector calls": "an_inspector_calls",
    "inspector calls": "an_inspector_calls",
    "blood brothers": "blood_brothers",
    "lord of the flies": "lord_of_the_flies",
    "animal farm": "animal_farm",
    "power and conflict": POWER_AND_CONFLICT_SLUG,
    "love and relationships": "love_and_relationships",
    "unseen poetry": UNSEEN_POETRY_SLUG,
    "unseen poem": UNSEEN_POETRY_SLUG,
}

#: Keyword phrases pre-sorted longest-first so "an inspector calls" wins over
#: "inspector calls" and a specific text beats a shorter substring.
_KEYWORDS_LONGEST_FIRST: tuple[str, ...] = tuple(
    sorted(_KEYWORD_TO_SLUG, key=len, reverse=True)
)


def _normalise_phrase(text: str) -> str:
    """Lower-case and collapse separators so keyword matching is punctuation-safe."""
    lowered = text.lower().strip()
    # Equate hyphen/underscore/dot separators with spaces for phrase matching.
    return re.sub(r"[-_.\s]+", " ", lowered).strip()


def normalise_slug(raw: str) -> str:
    """Normalise a raw text name to a corpus slug (lower-case, separators → ``_``).

    Mirrors ``knowledge.corpus._derive_text_name`` so a hint already in slug form
    (``"an-inspector-calls"``) and a display form (``"An Inspector Calls"``)
    resolve to the same canonical ``an_inspector_calls``.
    """
    return re.sub(r"[-\s.]+", "_", raw.strip().lower())


def derive_text_name(
    *, topic: str | None, subject: str | None = None, text_hint: str | None = None
) -> str | None:
    """Resolve a canonical set-text slug for a session at START (scope §4.2).

    Resolution order, first hit wins:

    1. ``text_hint`` — an explicit text the caller already knows: normalised to a
       slug and accepted if it is a known taxonomy slug.
    2. ``topic`` — the planner's chosen topic phrase, scanned (longest keyword
       first) for a recognised set text.
    3. ``subject`` — a last-chance scan (a subject slug is rarely a text, but a
       caller may pass one).

    Returns ``None`` when nothing recognises a known set text — a free-topic
    session simply carries no ``text_name`` and is not counted toward text-level
    achievements (honest under-count, never a wrong attribution).
    """
    if text_hint:
        slug = normalise_slug(text_hint)
        if slug in TEXT_TAXONOMY:
            return slug

    for candidate in (topic, subject):
        if not candidate:
            continue
        phrase = _normalise_phrase(candidate)
        # Direct slug match (a caller passing a slug as the topic).
        direct = normalise_slug(candidate)
        if direct in TEXT_TAXONOMY:
            return direct
        for keyword in _KEYWORDS_LONGEST_FIRST:
            if keyword in phrase:
                return _KEYWORD_TO_SLUG[keyword]
    return None


def genre_for(slug: str | None) -> Genre | None:
    """The :class:`Genre` of a canonical slug, or ``None`` if unknown."""
    meta = TEXT_TAXONOMY.get(slug) if slug else None
    return meta.genre if meta is not None else None


def era_for(slug: str | None) -> Era | None:
    """The :class:`Era` of a canonical slug, or ``None`` if unknown."""
    meta = TEXT_TAXONOMY.get(slug) if slug else None
    return meta.era if meta is not None else None


def display_name_for(slug: str | None) -> str | None:
    """The human display name of a canonical slug, or ``None`` if unknown."""
    meta = TEXT_TAXONOMY.get(slug) if slug else None
    return meta.display_name if meta is not None else None


__all__ = [
    "Era",
    "GENRE_GATHERER_GENRES",
    "Genre",
    "HISTORICAL_HORIZON_ERAS",
    "POWER_AND_CONFLICT_SLUG",
    "TEXT_TAXONOMY",
    "TextMeta",
    "UNSEEN_POETRY_SLUG",
    "derive_text_name",
    "display_name_for",
    "era_for",
    "genre_for",
    "normalise_slug",
]
