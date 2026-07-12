"""Unit tests for the canonical set-text taxonomy (S-E4 / scope §4.2)."""
from __future__ import annotations

import pytest

from study_tutor.gamification.texts import (
    Era,
    Genre,
    POWER_AND_CONFLICT_SLUG,
    UNSEEN_POETRY_SLUG,
    derive_text_name,
    era_for,
    genre_for,
    normalise_slug,
)


@pytest.mark.parametrize(
    "topic,expected",
    [
        ("dramatic irony in Macbeth", "macbeth"),
        ("Lady Macbeth's ambition", "macbeth"),
        ("An Inspector Calls — Mr Birling", "an_inspector_calls"),
        ("inspector calls responsibility", "an_inspector_calls"),
        ("A Christmas Carol: Scrooge's redemption", "a_christmas_carol"),
        ("Jekyll and Hyde duality", "jekyll_and_hyde"),
        ("Power and Conflict — Ozymandias", POWER_AND_CONFLICT_SLUG),
        ("unseen poetry approach", UNSEEN_POETRY_SLUG),
    ],
)
def test_derive_text_name_from_topic_phrase(topic: str, expected: str) -> None:
    assert derive_text_name(topic=topic) == expected


def test_derive_prefers_longest_keyword() -> None:
    # "an inspector calls" must win over the shorter "inspector calls".
    assert derive_text_name(topic="An Inspector Calls") == "an_inspector_calls"


def test_derive_text_name_hint_takes_priority() -> None:
    # A slug-form hint resolves even when the topic mentions another text.
    assert (
        derive_text_name(topic="metaphor identification", text_hint="an-inspector-calls")
        == "an_inspector_calls"
    )


def test_derive_text_name_unknown_topic_returns_none() -> None:
    # A free-topic session that names no known set text carries no text_name.
    assert derive_text_name(topic="metaphor identification") is None
    assert derive_text_name(topic=None) is None


def test_derive_text_name_ignores_unknown_hint() -> None:
    assert derive_text_name(topic=None, text_hint="not-a-real-text") is None


def test_normalise_slug_matches_corpus_normalisation() -> None:
    assert normalise_slug("An Inspector Calls") == "an_inspector_calls"
    assert normalise_slug("inspector-calls") == "inspector_calls"


def test_genre_and_era_lookups() -> None:
    assert genre_for("macbeth") is Genre.DRAMA
    assert era_for("macbeth") is Era.SHAKESPEARE
    assert genre_for("a_christmas_carol") is Genre.PROSE
    assert era_for("a_christmas_carol") is Era.NINETEENTH_CENTURY_NOVEL
    assert genre_for("an_inspector_calls") is Genre.DRAMA
    assert era_for("an_inspector_calls") is Era.MODERN_DRAMA
    assert genre_for(POWER_AND_CONFLICT_SLUG) is Genre.POETRY


def test_genre_and_era_unknown_slug_is_none() -> None:
    assert genre_for(None) is None
    assert era_for("mystery_text") is None
