"""Source-typed quote verifier (TASK-PRV-005, FEAT-PRV4 / FEAT-PH1-004).

This module is the load-bearing safety surface of the primary-text-RAG
pipeline. It ingests a Player response, finds every quoted span,
classifies each into one of four match types using a strict precedence
ordering, rewrites the response in place, and emits a
:class:`VerifierMetadata` payload for the Coach.

Precedence ordering (Open Question 3 closure)
---------------------------------------------
1. Exact match against any ``PRIMARY_TEXT`` chunk for the *session* text
   → :class:`PrimaryMatch` (annotated with ``chunk.citation_anchor``).
2. Exact match against any ``PRIMARY_TEXT`` chunk for a *different* text
   → :class:`CrossTextEvent` (paraphrase rewrite — never annotated with
   the wrong citation).
3. Exact match against any ``SECONDARY_*`` chunk →
   :class:`SecondaryRewrite` (quotes stripped, deterministic attribution
   from :data:`SECONDARY_ATTRIBUTION_TEMPLATES`).
4. Fuzzy match (≤3 edits) against a ``PRIMARY_TEXT`` chunk for the
   session text → :class:`FuzzyCorrection`.
5. No match → :class:`NoMatchStrip` (quotes removed, certainty softened).

**Fuzzy correction is restricted to the primary-text source.** This is
the load-bearing invariant that prevents secondary phrasings from being
"corrected" into a misattributed primary citation: a study-guide phrase
that happens to be ≤3 edits from a Shakespeare line is caught at step 3
(exact secondary match) before the fuzzy primary check at step 4 ever
runs, and even if it weren't, fuzzy never inspects secondary chunks.

Why match types are Pydantic models (not enums + dicts)
-------------------------------------------------------
The Coach's ``score_rubric.quote_fidelity`` criterion derives its score
by counting match-type instances. Type-safe attribute access
(``metadata.secondary_rewrites``) is much harder to misuse than dict
lookup, and Pydantic ``extra="forbid"`` makes accidental shape drift a
parse-time failure rather than a silent payload mismatch.

Concurrency
-----------
:func:`verify_quotes` is a pure function: no shared mutable state.
Two concurrent calls produce independent results. The corpus chunks
are treated as data only — instruction-like text inside a chunk does
not steer the verifier (the chunk content is searched, not executed).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from study_tutor.knowledge.corpus_models import (
    CitationAnchor,
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants (ASSUM-002, ASSUM-003, ASSUM-010, ASSUM-011)
# ---------------------------------------------------------------------------

#: Spans below this many words are not inspected (ASSUM-002).
MIN_QUOTE_WORDS: int = 4

#: Maximum Levenshtein edit distance for a fuzzy primary correction
#: (ASSUM-003). Anything beyond this falls through to ``NoMatchStrip``.
FUZZY_MAX_EDIT_DISTANCE: int = 3

#: A primary-match span longer than this many words is shortened
#: (ASSUM-011) — copyright-safety + readability.
LONG_PASSAGE_WORD_THRESHOLD: int = 30

#: Cap on the post-shortening span length (ASSUM-011).
SHORT_QUOTE_MAX_WORDS: int = 12

#: Deterministic attribution templates for secondary rewrites (ASSUM-010).
#: Selection is by ``hash(normalised_phrase) % len(...)`` so test fixtures
#: are stable. Production-time variety can be layered later by mixing in
#: a turn ID; out of scope for this task.
SECONDARY_ATTRIBUTION_TEMPLATES: tuple[str, ...] = (
    "as one critic observes",
    "as one study guide notes",
    "as one commentator suggests",
)


# ---------------------------------------------------------------------------
# Pydantic models — VerifierMetadata contract (consumed by TASK-PRV-006 +
# TASK-DTL-002). ``extra="forbid"`` so accidental shape drift fails loudly.
# ---------------------------------------------------------------------------


class _StrictModel(BaseModel):
    """Shared base — enforces ``extra="forbid"`` once."""

    model_config = ConfigDict(extra="forbid")


class PrimaryMatch(_StrictModel):
    """A quoted span verified as a verbatim primary-text citation.

    The ``citation_anchor`` is read directly from the matching chunk —
    it is never re-derived by parsing chunk text (covered by the
    ``@citation`` AC).
    """

    original_span: str
    citation_anchor: CitationAnchor
    chunk_index: int
    text_name: str


class SecondaryRewrite(_StrictModel):
    """A quoted span found verbatim only in a secondary / context chunk.

    The verifier strips the quote marks and rewrites with one of the
    deterministic attribution templates so the span never reaches the
    student framed as the primary author's words.
    """

    original_span: str
    attribution: str
    source_type: SourceType
    chunk_index: int


class FuzzyCorrection(_StrictModel):
    """A near-verbatim primary span (≤3 edits) substituted for the canonical wording.

    Restricted to primary-text source — see module docstring for the
    invariant.
    """

    original_span: str
    corrected_span: str
    edit_distance: int
    citation_anchor: CitationAnchor
    chunk_index: int
    text_name: str


class NoMatchStrip(_StrictModel):
    """A quoted span that matched no corpus chunk; quotes stripped, certainty softened."""

    original_span: str
    softened: bool = True


class CrossTextEvent(_StrictModel):
    """A quoted span matching primary text from a *different* work than the session.

    Rewritten as a paraphrase; **never** annotated with the session
    text's citation (the @cross-text @security AC).
    """

    original_span: str
    foreign_text_name: str
    paraphrase: str


class Shortening(_StrictModel):
    """Long-passage shortening event for a primary match.

    Recorded so the Coach can see the original length and the truncated
    rendering separately.
    """

    original_span: str
    shortened_span: str
    original_word_count: int


class VerifierMetadata(_StrictModel):
    """Structured handover from verifier → Coach.

    Field semantics:
      * The four core match-type lists capture every span the verifier
        encountered.
      * ``cross_text_events`` is broken out separately because it is a
        *security* event (cross-text-misattribution) rather than a
        normal verification outcome.
      * ``shortenings`` records long-passage truncations applied after
        match resolution (see :func:`verify_quotes`).
      * ``retrieval_skipped_reason`` is forwarded from the upstream
        retrieval-decision step (TASK-PRV-003) for the Coach's
        analysis-mode handling; ``None`` when retrieval ran normally.
    """

    primary_matches: list[PrimaryMatch] = Field(default_factory=list)
    secondary_rewrites: list[SecondaryRewrite] = Field(default_factory=list)
    fuzzy_corrections: list[FuzzyCorrection] = Field(default_factory=list)
    no_match_strips: list[NoMatchStrip] = Field(default_factory=list)
    cross_text_events: list[CrossTextEvent] = Field(default_factory=list)
    shortenings: list[Shortening] = Field(default_factory=list)
    retrieval_skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Internal Quote dataclass — used only inside this module.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Quote:
    """A quoted span extracted from a Player response.

    Attributes
    ----------
    text : str
        The text *between* the quote marks (no marks themselves).
    start, end : int
        Byte offsets into the original response, *including* the marks.
        Used by the rewriter to splice replacements back in.
    raw : str
        The slice ``response[start:end]`` — i.e. ``"..."`` (incl. marks).
    word_count : int
        Pre-computed for the ``MIN_QUOTE_WORDS`` filter.
    """

    text: str
    start: int
    end: int
    raw: str
    word_count: int


# Match either a typographic ("curly") or straight double-quote pair.
# Single quotes intentionally excluded — apostrophes (it's, Macbeth's)
# would create too many false positives for the 4-word minimum to
# reliably filter out.
_QUOTE_PATTERN = re.compile(r'"([^"]+)"|“([^”]+)”')


def _normalise(text: str) -> str:
    """Collapse whitespace, equate curly/straight quotes, lower-case.

    Used for both quote-text and chunk-text comparison so cosmetic
    differences (a curly apostrophe vs. straight, a stray newline,
    trailing punctuation) don't defeat exact matching.
    """
    # Equate curly and straight quotes (both directions of each pair).
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    # Collapse all whitespace runs (newlines, tabs, multiple spaces) to one.
    text = re.sub(r"\s+", " ", text).strip()
    # Strip surrounding punctuation that exact-substring matching would trip on.
    text = text.strip(".,;:!?\"' ")
    return text.lower()


def extract_quotes(response_text: str) -> list[Quote]:
    """Find every quoted span in ``response_text`` of ≥ ``MIN_QUOTE_WORDS`` words.

    Spans below the threshold are silently dropped (covered by the
    @boundary AC: 3 words → ignored, 4 words → inspected). Matches both
    typographic and straight double-quote pairs.
    """
    quotes: list[Quote] = []
    for match in _QUOTE_PATTERN.finditer(response_text):
        # The pattern has two alternatives — pick whichever group matched.
        inner = match.group(1) if match.group(1) is not None else match.group(2)
        if inner is None:
            continue
        word_count = len(inner.split())
        if word_count < MIN_QUOTE_WORDS:
            continue
        quotes.append(
            Quote(
                text=inner,
                start=match.start(),
                end=match.end(),
                raw=match.group(0),
                word_count=word_count,
            )
        )
    return quotes


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings (iterative two-row DP).

    Pure stdlib — no external dependency. Hot enough that we avoid the
    full ``len(a) * len(b)`` matrix allocation, but small enough at our
    scales (≤30-word spans) that a vectorised library would be overkill.
    """
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if ca == cb else 1)
            current[j] = min(insert_cost, delete_cost, replace_cost)
        previous = current
    return previous[-1]


def _best_fuzzy_window(
    normalised_quote: str, normalised_chunk: str, target_word_count: int
) -> tuple[int, str]:
    """Find the chunk-window with the smallest edit distance to the quote.

    Returns ``(distance, window_text)``. Searches windows of word count
    in ``[target - 2, target + 2]`` to absorb word-boundary edits while
    keeping the search bounded.
    """
    chunk_words = normalised_chunk.split()
    if not chunk_words:
        return (len(normalised_quote), "")

    best_distance = len(normalised_quote)  # worst case: delete every char
    best_window = ""
    # Bound window sizes so a malformed quote can't blow up the search.
    min_size = max(1, target_word_count - 2)
    max_size = min(len(chunk_words), target_word_count + 2)
    for size in range(min_size, max_size + 1):
        for start in range(0, len(chunk_words) - size + 1):
            candidate = " ".join(chunk_words[start : start + size])
            distance = _edit_distance(normalised_quote, candidate)
            if distance < best_distance:
                best_distance = distance
                best_window = candidate
                if best_distance == 0:
                    return (0, candidate)
    return (best_distance, best_window)


# ---------------------------------------------------------------------------
# Match resolution — discriminated outcome.
# ---------------------------------------------------------------------------


# Anything ``verify_quote`` can return; ``Shortening`` is layered on later.
MatchResult = (
    PrimaryMatch | SecondaryRewrite | FuzzyCorrection | NoMatchStrip | CrossTextEvent
)


def verify_quote(
    quote: Quote,
    corpus_chunks: Sequence[CorpusChunk],
    session_text_name: str,
) -> MatchResult:
    """Classify a single ``Quote`` against the corpus using the precedence ordering.

    Order of operations is the load-bearing piece — see module docstring.
    """
    normalised_quote = _normalise(quote.text)

    # Step 1: exact match against PRIMARY_TEXT for the session text.
    for chunk in corpus_chunks:
        if (
            chunk.source_type == SourceType.PRIMARY_TEXT
            and chunk.text_name == session_text_name
            and normalised_quote in _normalise(chunk.text)
        ):
            if chunk.citation_anchor is None:
                # Defence-in-depth: a primary chunk with no anchor is a
                # corpus-loader bug, not a verifier bug — fail loudly so
                # the Coach doesn't see a silently citation-less primary.
                raise ValueError(
                    "PRIMARY_TEXT chunk for "
                    f"{chunk.text_name!r} (chunk_index={chunk.chunk_index}) "
                    "has no citation_anchor; corpus loader contract broken"
                )
            return PrimaryMatch(
                original_span=quote.text,
                citation_anchor=chunk.citation_anchor,
                chunk_index=chunk.chunk_index,
                text_name=chunk.text_name,
            )

    # Step 2: exact match against PRIMARY_TEXT for a *different* text.
    for chunk in corpus_chunks:
        if (
            chunk.source_type == SourceType.PRIMARY_TEXT
            and chunk.text_name != session_text_name
            and normalised_quote in _normalise(chunk.text)
        ):
            return CrossTextEvent(
                original_span=quote.text,
                foreign_text_name=chunk.text_name,
                paraphrase=_paraphrase_cross_text(chunk.text_name),
            )

    # Step 3: exact match against any SECONDARY_* chunk. Runs *before*
    # the fuzzy primary check — this is Open Question 3's closure.
    for chunk in corpus_chunks:
        if (
            chunk.source_type
            in (SourceType.SECONDARY_STUDY_GUIDE, SourceType.SECONDARY_CRITICAL)
            and normalised_quote in _normalise(chunk.text)
        ):
            return SecondaryRewrite(
                original_span=quote.text,
                attribution=_pick_secondary_attribution(normalised_quote),
                source_type=chunk.source_type,
                chunk_index=chunk.chunk_index,
            )

    # Step 4: fuzzy match against PRIMARY_TEXT for the session text.
    # Restricted to primary source — never inspects secondary chunks.
    best_distance = FUZZY_MAX_EDIT_DISTANCE + 1
    best_chunk: CorpusChunk | None = None
    best_window = ""
    target_words = quote.word_count
    for chunk in corpus_chunks:
        if (
            chunk.source_type != SourceType.PRIMARY_TEXT
            or chunk.text_name != session_text_name
        ):
            continue
        distance, window = _best_fuzzy_window(
            normalised_quote, _normalise(chunk.text), target_words
        )
        if distance < best_distance:
            best_distance = distance
            best_chunk = chunk
            best_window = window
    if (
        best_chunk is not None
        and best_distance <= FUZZY_MAX_EDIT_DISTANCE
        and best_chunk.citation_anchor is not None
    ):
        return FuzzyCorrection(
            original_span=quote.text,
            corrected_span=best_window,
            edit_distance=best_distance,
            citation_anchor=best_chunk.citation_anchor,
            chunk_index=best_chunk.chunk_index,
            text_name=best_chunk.text_name,
        )

    # Step 5: no match.
    return NoMatchStrip(original_span=quote.text)


def _pick_secondary_attribution(normalised_phrase: str) -> str:
    """Deterministic attribution-template pick (ASSUM-010).

    ``hash`` is randomised per-process under PYTHONHASHSEED, so use a
    stable digest derived from the phrase content. Tests assert
    determinism on a fixed phrase.
    """
    # Cheap stable digest — sum of code points mod template count.
    digest = sum(ord(c) for c in normalised_phrase)
    return SECONDARY_ATTRIBUTION_TEMPLATES[digest % len(SECONDARY_ATTRIBUTION_TEMPLATES)]


def _paraphrase_cross_text(foreign_text_name: str) -> str:
    """Generic safe paraphrase for cross-text events.

    Deliberately content-free: the verifier's job is to *prevent*
    misattribution, not to invent a re-attributed sentence. The Coach
    can ask the Player to redo the analysis with the right text.
    """
    return f"a similar idea is discussed in {foreign_text_name}"


# ---------------------------------------------------------------------------
# Citation rendering — pure formatting from the discriminated anchor.
# ---------------------------------------------------------------------------


def _render_citation(anchor: CitationAnchor) -> str:
    """Render a citation anchor as ``(act.scene.line)`` or ``(Chapter X, Para Y)``.

    Uses ``isinstance`` against the discriminated union members rather
    than poking at fields directly — the corpus-models module docstring
    calls out that this is the type-safe way to dispatch on anchor kind.
    """
    if isinstance(anchor, PlayCitationAnchor):
        return f"({anchor.act}.{anchor.scene}.{anchor.line})"
    if isinstance(anchor, NovelCitationAnchor):
        return f"(Chapter {anchor.chapter}, Paragraph {anchor.paragraph})"
    # Defence-in-depth: a new anchor kind without a render arm is a bug.
    raise TypeError(f"unhandled CitationAnchor variant: {type(anchor).__name__}")


# ---------------------------------------------------------------------------
# Long-passage shortening (ASSUM-011)
# ---------------------------------------------------------------------------


def _shorten_span(span: str) -> tuple[str, int]:
    """Pick the first ``SHORT_QUOTE_MAX_WORDS`` words as the densest analytical span.

    Returns ``(shortened_span, original_word_count)``. The "densest
    analytical span" picker is intentionally simple: the IMPLEMENTATION-
    GUIDE notes a more sophisticated picker is downstream work — what
    matters here is that ≤12 words make it to the student.
    """
    words = span.split()
    return (" ".join(words[:SHORT_QUOTE_MAX_WORDS]), len(words))


# ---------------------------------------------------------------------------
# Rewriting — splice match-type-specific replacements back into the response.
# ---------------------------------------------------------------------------


def _soften_certainty_prefix(response_before: str) -> str:
    """Insert a softening hedge before a stripped span if missing.

    Naive rule: if the byte immediately before the span ends with a
    space, insert ``"perhaps "``; otherwise leave as-is. Good enough for
    the AC ("certainty softened"); a richer NLP softener is downstream.
    """
    if response_before.endswith((" ", "\n", "\t")):
        return response_before + "perhaps "
    return response_before


def _build_replacement(
    result: MatchResult,
    quote: Quote,
    shortenings: list[Shortening],
) -> str:
    """Render the replacement text for one quote based on its match result.

    Side effect: appends to ``shortenings`` if a long primary match is
    truncated. This keeps the rewriter's per-quote loop linear.
    """
    if isinstance(result, PrimaryMatch):
        span = result.original_span
        word_count = len(span.split())
        if word_count > LONG_PASSAGE_WORD_THRESHOLD:
            shortened, _ = _shorten_span(span)
            shortenings.append(
                Shortening(
                    original_span=span,
                    shortened_span=shortened,
                    original_word_count=word_count,
                )
            )
            span = shortened
        return f'"{span}" {_render_citation(result.citation_anchor)}'

    if isinstance(result, FuzzyCorrection):
        return (
            f'"{result.corrected_span}" {_render_citation(result.citation_anchor)}'
        )

    if isinstance(result, SecondaryRewrite):
        # Quotes stripped — span is rendered as paraphrased text with
        # the deterministic attribution template prefixing.
        return f"{result.attribution}, {result.original_span}"

    if isinstance(result, CrossTextEvent):
        # Quotes stripped — replace with a content-free safe paraphrase.
        return result.paraphrase

    if isinstance(result, NoMatchStrip):
        # Quotes stripped, span content kept (so the response still
        # makes sense to the student) but not framed as a citation.
        return result.original_span

    raise TypeError(f"unhandled MatchResult variant: {type(result).__name__}")


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def verify_quotes(
    response_text: str,
    corpus_chunks: Sequence[CorpusChunk],
    session_text_name: str,
    retrieval_skipped_reason: str | None = None,
) -> tuple[str, VerifierMetadata]:
    """Verify every quoted span in ``response_text`` against the corpus.

    Returns ``(rewritten_response, metadata)``. The rewritten response is
    what should reach the student; ``metadata`` is what reaches the
    Coach. This function is pure — no module-level state, no I/O — so
    concurrent invocations are independent (the @concurrency AC).

    Parameters
    ----------
    response_text
        The Player's raw response. Quoted spans are extracted and
        classified; non-quoted text passes through verbatim.
    corpus_chunks
        The retrieved (or full) corpus to verify against. The verifier
        treats the chunk content as data only — instruction-like text
        inside a chunk does not steer matching (the @prompt-injection
        AC). The verifier reads ``chunk.citation_anchor`` directly and
        never re-derives a citation by parsing chunk text.
    session_text_name
        The work the session is on (e.g. ``"Macbeth"``). Used to
        distinguish a session-text primary match from a cross-text one.
    retrieval_skipped_reason
        Forwarded from the retrieval-decision step (TASK-PRV-003). The
        verifier doesn't act on it; the Coach uses it for analysis-mode
        scoring posture.
    """
    if not isinstance(response_text, str):
        # Boundary guard — pydantic-typed callers can't trip this, but
        # ad-hoc callers (tests, REPL, future MCP wiring) might.
        raise TypeError(
            f"response_text must be str, got {type(response_text).__name__}"
        )

    quotes = extract_quotes(response_text)
    metadata = VerifierMetadata(retrieval_skipped_reason=retrieval_skipped_reason)

    # Walk quotes in source order so splicing offsets stay valid as we
    # build the rewritten response. We accumulate the rewritten text in
    # a list-of-segments to avoid repeated O(n) string concatenation.
    output_segments: list[str] = []
    cursor = 0
    for quote in quotes:
        result = verify_quote(quote, corpus_chunks, session_text_name)

        # Emit the response slice between the previous quote (or start)
        # and this quote, applying the no-match softener if needed.
        before = response_text[cursor : quote.start]
        if isinstance(result, NoMatchStrip):
            before = _soften_certainty_prefix(before)
        output_segments.append(before)

        replacement = _build_replacement(result, quote, metadata.shortenings)
        output_segments.append(replacement)

        # Bucket the result into the correct metadata list.
        if isinstance(result, PrimaryMatch):
            metadata.primary_matches.append(result)
        elif isinstance(result, SecondaryRewrite):
            metadata.secondary_rewrites.append(result)
        elif isinstance(result, FuzzyCorrection):
            metadata.fuzzy_corrections.append(result)
        elif isinstance(result, CrossTextEvent):
            metadata.cross_text_events.append(result)
        elif isinstance(result, NoMatchStrip):
            metadata.no_match_strips.append(result)
        else:  # pragma: no cover — defence-in-depth
            raise TypeError(
                f"unexpected MatchResult variant: {type(result).__name__}"
            )

        cursor = quote.end

    # Tail of the response after the last quote.
    output_segments.append(response_text[cursor:])
    rewritten = "".join(output_segments)
    return (rewritten, metadata)


__all__ = [
    "MIN_QUOTE_WORDS",
    "FUZZY_MAX_EDIT_DISTANCE",
    "LONG_PASSAGE_WORD_THRESHOLD",
    "SHORT_QUOTE_MAX_WORDS",
    "SECONDARY_ATTRIBUTION_TEMPLATES",
    "Quote",
    "PrimaryMatch",
    "SecondaryRewrite",
    "FuzzyCorrection",
    "NoMatchStrip",
    "CrossTextEvent",
    "Shortening",
    "VerifierMetadata",
    "extract_quotes",
    "verify_quote",
    "verify_quotes",
]
