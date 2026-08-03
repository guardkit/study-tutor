"""Sentence-boundary release logic for verified streaming (ADR-ARCH-027).

The ratified decision: the streamed turn buffers Player tokens into
sentence chunks, and each chunk passes quote verification (scoped to the
text accumulated so far) BEFORE its tokens are emitted to the client and
before the chunk is synthesized. This module owns the pure boundary
mechanics; the orchestrator composes them with the per-turn verifier
(``PlayerCoachOrchestrator.run_turn_stream_verified``).

The ADR names one implementation obligation explicitly: a quote span
straddling a chunk boundary must be handled — "the verifier sees
accumulated text, not the isolated chunk". :func:`releasable_prefix_len`
solves it structurally: a prefix is only releasable at a sentence
terminator with BALANCED quotation marks, so an open quotation holds the
whole span back until it closes and the verifier always sees complete
spans. That also makes per-boundary verification prefix-stable: verifying
a longer accumulation never rewrites text before an earlier release
point, because released prefixes never end inside a quote span.
"""

from __future__ import annotations

#: Sentence terminators (mirrors ``voice.service._SENTENCE_BOUNDARY`` —
#: the TTS split — plus the streaming path treats a terminator followed
#: by whitespace-or-end as a boundary).
_TERMINATORS = ".!?…"

#: Quotation marks that open/close a quoted span. Straight double quotes
#: toggle; curly quotes pair. Apostrophes are NOT tracked — single quotes
#: double as contractions in tutoring prose and the corpus texts.
_STRAIGHT_QUOTE = '"'
_OPEN_QUOTES = "“"  # “
_CLOSE_QUOTES = "”"  # ”


def _quotes_balanced(text: str) -> bool:
    """True when no quoted span is open at the end of ``text``."""
    if text.count(_STRAIGHT_QUOTE) % 2 != 0:
        return False
    if text.count(_OPEN_QUOTES) != text.count(_CLOSE_QUOTES):
        return False
    return True


def releasable_prefix_len(text: str) -> int:
    """Length of the longest releasable prefix of ``text``.

    A prefix is releasable when it ends at a sentence terminator (the
    terminator itself plus any immediately-following whitespace) AND the
    prefix's quotation marks are balanced (the ADR's straddle guard).
    Returns 0 when nothing is releasable yet.
    """
    best = 0
    for index, char in enumerate(text):
        if char not in _TERMINATORS:
            continue
        end = index + 1
        # A terminator is commonly followed by the closing quote of the
        # span it ends ('...here." That') — absorb closing quotes into
        # the sentence before requiring the boundary whitespace.
        while end < len(text) and text[end] in (
            _STRAIGHT_QUOTE + _CLOSE_QUOTES
        ):
            end += 1
        # A terminator mid-word (e.g. "3.14") is not a boundary: require
        # whitespace or end-of-buffer after it (and any absorbed quotes).
        if end < len(text) and not text[end].isspace():
            continue
        # Include trailing whitespace in the released prefix so deltas
        # concatenate byte-identically to the accumulated text.
        while end < len(text) and text[end].isspace():
            end += 1
        if _quotes_balanced(text[:end]):
            best = end
    return best


__all__ = ["releasable_prefix_len"]
