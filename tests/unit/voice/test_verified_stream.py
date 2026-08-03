"""Sentence-boundary release rules (ADR-ARCH-027 — voice/verified_stream.py).

Pins the pure mechanics the verified streaming path stands on: release
only at a sentence terminator, never mid-number, and never inside an
open quotation span (the ADR's named straddle obligation).
"""

from study_tutor.voice.verified_stream import releasable_prefix_len


def test_no_release_before_a_terminator() -> None:
    assert releasable_prefix_len("A metaphor compares") == 0


def test_release_at_terminator_followed_by_space() -> None:
    text = "A metaphor compares two things. It does not use like"
    assert releasable_prefix_len(text) == len("A metaphor compares two things. ")


def test_release_at_terminator_at_end_of_buffer() -> None:
    text = "It does not use like or as."
    assert releasable_prefix_len(text) == len(text)


def test_multiple_sentences_release_through_the_last_boundary() -> None:
    text = "First point. Second point! Third trail"
    assert releasable_prefix_len(text) == len("First point. Second point! ")


def test_decimal_point_is_not_a_boundary() -> None:
    assert releasable_prefix_len("Pi is 3.14 and rises") == 0


def test_open_straight_quote_holds_release() -> None:
    # The quotation opens before the terminator and has not closed —
    # the ADR's straddle case. Nothing releases yet.
    text = 'Lady Macbeth says "unsex me here. And fill me'
    assert releasable_prefix_len(text) == 0


def test_closed_straight_quote_releases_through_the_span() -> None:
    text = 'She says "unsex me here." That line shows'
    assert releasable_prefix_len(text) == len('She says "unsex me here." ')


def test_open_curly_quote_holds_release() -> None:
    text = "He begins “Is this a dagger. Which I see"
    assert releasable_prefix_len(text) == 0


def test_closed_curly_quote_releases() -> None:
    text = "He begins “Is this a dagger?” and hesitates. Then"
    assert releasable_prefix_len(text) == len(
        "He begins “Is this a dagger?” and hesitates. "
    )


def test_released_prefixes_concatenate_byte_identically() -> None:
    """Deltas cut at releasable boundaries must rebuild the exact text."""
    text = "One. Two! Three? Trailing"
    boundary = releasable_prefix_len(text)
    assert text[:boundary] + text[boundary:] == text
    assert boundary == len("One. Two! Three? ")
