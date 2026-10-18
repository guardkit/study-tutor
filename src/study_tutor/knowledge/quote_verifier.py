"""Source-typed quote verifier (TASK-PRV-005, FEAT-PRV4 / FEAT-PH1-004).

This module is the load-bearing safety surface of the primary-text-RAG
pipeline. It ingests a Player response, finds every quoted span,
classifies each into one of four match types using a strict precedence
ordering, rewrites the response in place, and emits a
:class:`VerifierMetadata` payload for the Coach.

Precedence ordering (Open Question 3 closure)
---------------------------------------------
1. Exact match against any ``PRIMARY_TEXT`` chunk for the *session* text
   → :class:`PrimaryMatch` (annotated with ``chunk.citation_anchor``;
   when the matching chunk carries no anchor — an ingest-side inference
   gap, e.g. the 2026-05-10 docling re-ingest — the match DEGRADES to an
   uncited quotation instead of failing the verifier; see
   ``VerifierMetadata.anchorless_primary_matches``).
2. Exact match against any ``PRIMARY_TEXT`` chunk for a *different* text
   → :class:`CrossTextEvent` (paraphrase rewrite — never annotated with
   the wrong citation).
3. Exact match against any ``SECONDARY_*`` chunk →
   :class:`SecondaryRewrite` (quotes stripped, deterministic attribution
   from :data:`SECONDARY_ATTRIBUTION_TEMPLATES`).
4. Fuzzy match (≤3 edits) against a ``PRIMARY_TEXT`` chunk for the
   session text → :class:`FuzzyCorrection`.
5. No match → :class:`NoMatchStrip` (quotes removed, certainty softened;
   or, in strict mode, the whole span replaced by
   :data:`UNVERIFIED_QUOTE_TEXT` — see below).

Strict mode (``redact_unmatched=True``) — mission law 3
-------------------------------------------------------
"Never an unverified quote." Both production call sites
(``cli/main.py``) verify in strict mode, which changes three things:

* a ``NoMatch`` span (marks and words) is **replaced** by the fixed
  neutral :data:`UNVERIFIED_QUOTE_TEXT`, with no "perhaps" — on the voice
  path quote marks are inaudible, so a kept span is heard as quotation;
* every non-empty double-quoted span is checked whatever its length: a
  span under ``MIN_QUOTE_WORDS`` passes only on an exact (case-,
  whitespace- and punctuation-normalised, word-aligned) match in a chunk;
  fuzzy correction stays for spans of ``MIN_QUOTE_WORDS`` or more;
* an opening double quote with no closing quote is redacted from the
  opening mark to the end of the response.

An empty ``session_text_name`` (a session with no set text) puts every
``PRIMARY_TEXT`` chunk in scope for the exact and fuzzy primary steps and
turns the cross-text step off — no text is "the session's" text, and the
citation comes from the matched chunk either way.

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

Quote-anchored lookup (strict mode only)
----------------------------------------
docs/design/quote-lookup-by-span-2026-10-18.md. The session's chunks are
retrieved with the learner's message as the query, so a correct quote of
a line far from the question's wording can be missing from them. With a
``lookup`` (a :class:`QuoteLookup`), a span the matcher leaves unmatched
is looked up by its own words and re-matched by the SAME matcher against
the session's chunks plus that span's own lookup chunks (never another
span's). Lookups are reply-scoped and memoised — every outcome (chunks,
empty, exception, over budget) is cached, at most
:data:`MAX_QUOTE_LOOKUPS_PER_REPLY` per reply — so a span's decision is
identical on every streaming pass. Still unmatched ⇒ redacted as before.

Concurrency
-----------
:func:`verify_quotes` is a pure function: no shared mutable state (the
only state it touches is the caller-owned, reply-scoped ``lookup``).
Two concurrent calls produce independent results. The corpus chunks
are treated as data only — instruction-like text inside a chunk does
not steer the verifier (the chunk content is searched, not executed).
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Callable, Sequence

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

#: Spans below this many words are not inspected (ASSUM-002) — except in
#: strict mode, where they are checked by exact match only (no fuzzy).
MIN_QUOTE_WORDS: int = 4

#: Strict-mode replacement for a quoted span that matched nothing (mission
#: law 3). Deliberately neutral: it presents nothing as quotation, so it is
#: safe to show AND to speak.
UNVERIFIED_QUOTE_TEXT: str = (
    "a line I'd want you to check in your own copy of the text"
)

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


#: Strict mode: at most this many quote-anchored lookups per reply (one
#: :class:`QuoteLookup`). Any further unmatched span is redacted without a
#: lookup — bounded latency (quote-lookup design).
MAX_QUOTE_LOOKUPS_PER_REPLY: int = 4


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
    ``@citation`` AC). ``None`` means the chunk itself carried no anchor
    (ingest-side inference gap): the span is still VERIFIED verbatim
    primary text, but it renders as a degraded citation — kept in quote
    marks with no trailing ``(a.s.l)`` annotation.
    """

    original_span: str
    citation_anchor: CitationAnchor | None
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
    invariant. ``citation_anchor`` is ``None`` when the matched chunk
    carries no anchor (same degraded-citation semantics as
    :class:`PrimaryMatch`).
    """

    original_span: str
    corrected_span: str
    edit_distance: int
    citation_anchor: CitationAnchor | None
    chunk_index: int
    text_name: str


class NoMatchStrip(_StrictModel):
    """A quoted span that matched no corpus chunk; quotes stripped, certainty softened.

    ``redacted`` (ADDITIVE, defaulted) is ``True`` when strict mode replaced
    the whole span with :data:`UNVERIFIED_QUOTE_TEXT` instead of keeping
    its words; ``softened`` is then ``False`` (no hedge is inserted).
    """

    original_span: str
    softened: bool = True
    redacted: bool = False


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
    #: ADDITIVE counters (Lane 2 step 3, Track A). How many of the
    #: ``primary_matches`` / ``fuzzy_corrections`` above matched a chunk
    #: whose ``citation_anchor`` was ``None`` and therefore rendered as a
    #: DEGRADED citation (quoted span, no trailing annotation). Keeps
    #: citation coverage measurable for the golden-quote eval harness:
    #: anchored count = ``len(list) - anchorless count``. Never mutate the
    #: existing fields' semantics — count-only consumers
    #: (``tutoring/coach/rubric.py``, ``tutoring/turn_capture.py``) are
    #: unaffected by these additions.
    anchorless_primary_matches: int = 0
    anchorless_fuzzy_corrections: int = 0
    #: Set to ``True`` by the coach-handover seam (TASK-PRV-006) when
    #: :func:`verify_quotes` raised and the orchestrator fell back to
    #: passing the unannotated Player response to the Coach. Defaults to
    #: ``False`` so existing callers (verify_quotes itself, fixtures)
    #: never need to set it explicitly. The Coach's ``quote_fidelity``
    #: criterion suppresses its down-rank when this flag is set, mirroring
    #: the suppression policy already specified for
    #: ``retrieval_skipped_reason``.
    verifier_exception: bool = False


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

# Strict mode pairs marks the same way but also pairs an EMPTY span (``""``)
# so it is never mistaken for an unterminated quote. Used for both span
# extraction and the unterminated-quote scan, so the two always agree on
# which marks are paired.
_STRICT_QUOTE_PATTERN = re.compile(r'"([^"]*)"|“([^”]*)”')


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
    return _extract(response_text, _QUOTE_PATTERN, MIN_QUOTE_WORDS)


def _extract(
    response_text: str, pattern: re.Pattern[str], min_words: int
) -> list[Quote]:
    """Shared extraction loop behind :func:`extract_quotes`.

    Strict mode calls it with ``_STRICT_QUOTE_PATTERN`` and
    ``min_words=1`` so every non-empty span is inspected whatever its
    length (an empty or whitespace-only pair presents nothing as quotation
    and is left alone).
    """
    quotes: list[Quote] = []
    for match in pattern.finditer(response_text):
        # The pattern has two alternatives — pick whichever group matched.
        inner = match.group(1) if match.group(1) is not None else match.group(2)
        if inner is None:
            continue
        word_count = len(inner.split())
        if word_count < min_words:
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


def _unterminated_quote_start(response_text: str) -> int | None:
    """Offset of the first opening double quote that no closing quote pairs.

    Strict mode only. Every straight ``"`` or curly ``“`` outside a paired
    span (as :data:`_STRICT_QUOTE_PATTERN` pairs them) opens a quotation that
    never closes before the end of the response; the earliest such mark is
    where the redaction to end-of-text starts. ``None`` when every opening
    mark is paired.
    """
    covered_until = 0
    for match in _STRICT_QUOTE_PATTERN.finditer(response_text):
        stray = _first_opening_mark(response_text, covered_until, match.start())
        if stray is not None:
            return stray
        covered_until = match.end()
    return _first_opening_mark(response_text, covered_until, len(response_text))


def _first_opening_mark(text: str, start: int, end: int) -> int | None:
    """Offset of the first ``"`` / ``“`` in ``text[start:end]``, or ``None``."""
    for index in range(start, end):
        if text[index] in '"“':
            return index
    return None


def _words(normalised: str) -> list[str]:
    """Split normalised text into words, dropping all punctuation but apostrophes."""
    return re.findall(r"[\w']+", normalised)


def _contains_word_sequence(quote_words: list[str], chunk_words: list[str]) -> bool:
    """``True`` when ``quote_words`` occurs contiguously in ``chunk_words``.

    The strict-mode exact match for spans under ``MIN_QUOTE_WORDS``: word-
    aligned (so ``"art"`` never matches inside "heart") with case,
    whitespace and punctuation normalised away.
    """
    if not quote_words:
        return False
    width = len(quote_words)
    return any(
        chunk_words[start : start + width] == quote_words
        for start in range(0, len(chunk_words) - width + 1)
    )


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
    An empty ``session_text_name`` (no set text) makes every primary chunk
    the session's for steps 1 and 4 and skips step 2 (Q2 of the law-3
    design). A span under ``MIN_QUOTE_WORDS`` (only ever passed in strict
    mode) is matched word-aligned and exactly, and never fuzzily.
    """
    normalised_quote = _normalise(quote.text)
    short_span = quote.word_count < MIN_QUOTE_WORDS
    quote_words = _words(normalised_quote)

    def _exact_in(chunk: CorpusChunk) -> bool:
        if short_span:
            return _contains_word_sequence(
                quote_words, _words(_normalise(chunk.text))
            )
        return normalised_quote in _normalise(chunk.text)

    def _session_text(chunk: CorpusChunk) -> bool:
        return not session_text_name or chunk.text_name == session_text_name

    # Step 1: exact match against PRIMARY_TEXT for the session text.
    for chunk in corpus_chunks:
        if (
            chunk.source_type == SourceType.PRIMARY_TEXT
            and _session_text(chunk)
            and _exact_in(chunk)
        ):
            # An anchorless primary chunk (ingest-side inference gap —
            # e.g. the 2026-05-10 store: 581/581 anchorless) is a
            # DEGRADED CITATION, not an exception: the span IS verified
            # verbatim primary text, so raising here would abort the
            # whole response and fail the safety gate open at the
            # coach-handover broad-except (the Lane 2 step 3 regression).
            # ``citation_anchor=None`` flows through and the rewriter
            # keeps the quoted span with no trailing annotation.
            return PrimaryMatch(
                original_span=quote.text,
                citation_anchor=chunk.citation_anchor,
                chunk_index=chunk.chunk_index,
                text_name=chunk.text_name,
            )

    # Step 2: exact match against PRIMARY_TEXT for a *different* text.
    # Off when the session has no set text (every primary is in scope).
    for chunk in corpus_chunks if session_text_name else ():
        if (
            chunk.source_type == SourceType.PRIMARY_TEXT
            and chunk.text_name != session_text_name
            and _exact_in(chunk)
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
            and _exact_in(chunk)
        ):
            return SecondaryRewrite(
                original_span=quote.text,
                attribution=_pick_secondary_attribution(normalised_quote),
                source_type=chunk.source_type,
                chunk_index=chunk.chunk_index,
            )

    # Step 4: fuzzy match against PRIMARY_TEXT for the session text.
    # Restricted to primary source — never inspects secondary chunks —
    # and to spans of MIN_QUOTE_WORDS or more (a 1-3 word span is too
    # short for a 3-edit window to mean "the same line").
    best_distance = FUZZY_MAX_EDIT_DISTANCE + 1
    best_chunk: CorpusChunk | None = None
    best_window = ""
    target_words = quote.word_count
    for chunk in corpus_chunks if not short_span else ():
        if chunk.source_type != SourceType.PRIMARY_TEXT or not _session_text(
            chunk
        ):
            continue
        distance, window = _best_fuzzy_window(
            normalised_quote, _normalise(chunk.text), target_words
        )
        if distance < best_distance:
            best_distance = distance
            best_chunk = chunk
            best_window = window
    # An anchorless best chunk still corrects (degraded citation — same
    # posture as the exact-primary arm above); requiring an anchor here
    # made fuzzy correction structurally dead against anchorless stores.
    if best_chunk is not None and best_distance <= FUZZY_MAX_EDIT_DISTANCE:
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
        if result.citation_anchor is None:
            # Degraded citation: verified span, nothing to cite.
            return f'"{span}"'
        return f'"{span}" {_render_citation(result.citation_anchor)}'

    if isinstance(result, FuzzyCorrection):
        if result.citation_anchor is None:
            # Degraded citation (see PrimaryMatch arm above).
            return f'"{result.corrected_span}"'
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
        if result.redacted:
            # Strict mode (law 3): marks AND words go — an unverified line
            # must not be shown or heard as if it were the text.
            return UNVERIFIED_QUOTE_TEXT
        # Quotes stripped, span content kept (so the response still
        # makes sense to the student) but not framed as a citation.
        return result.original_span

    raise TypeError(f"unhandled MatchResult variant: {type(result).__name__}")


# ---------------------------------------------------------------------------
# Quote-anchored lookup — reply-scoped, memoised, budgeted.
# ---------------------------------------------------------------------------


class QuoteLookup:
    """Reply-scoped, memoised ``span → chunks`` lookup (strict mode only).

    Build ONE per reply (per streaming verifier, per non-streaming Player
    attempt) around ``fetch`` (production: :func:`retrieve` with the span as
    the query). Each distinct span is fetched at most once; the result is
    cached whatever it is — chunks, an empty result, an exception (logged,
    cached as empty) or "over budget" (the budget of ``max_lookups``
    fetches is spent; cached as empty) — so a span's outcome never changes
    between passes over a growing reply.
    """

    def __init__(
        self,
        fetch: Callable[[str], Sequence[CorpusChunk]],
        max_lookups: int = MAX_QUOTE_LOOKUPS_PER_REPLY,
    ) -> None:
        self._fetch = fetch
        self._max_lookups = max_lookups
        self._cache: dict[str, tuple[CorpusChunk, ...]] = {}
        self._lock = threading.Lock()
        #: Number of times ``fetch`` has been called (budget spent).
        self.lookups = 0

    def __call__(self, span: str) -> tuple[CorpusChunk, ...]:
        with self._lock:
            cached = self._cache.get(span)
            if cached is not None:
                return cached
            if self.lookups >= self._max_lookups:
                logger.info(
                    "quote_lookup.over_budget",
                    extra={"max_lookups": self._max_lookups},
                )
                chunks: tuple[CorpusChunk, ...] = ()
            else:
                self.lookups += 1
                try:
                    chunks = tuple(self._fetch(span))
                except Exception as exc:  # noqa: BLE001 — fail closed: span stays unmatched
                    logger.warning(
                        "quote_lookup.failed",
                        extra={"detail": f"{type(exc).__name__}: {exc}"},
                    )
                    chunks = ()
            self._cache[span] = chunks
            return chunks


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def verify_quotes(
    response_text: str,
    corpus_chunks: Sequence[CorpusChunk],
    session_text_name: str,
    retrieval_skipped_reason: str | None = None,
    *,
    redact_unmatched: bool = False,
    lookup: Callable[[str], Sequence[CorpusChunk]] | None = None,
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
        Empty means no set text: every primary chunk is in scope.
    retrieval_skipped_reason
        Forwarded from the retrieval-decision step (TASK-PRV-003). The
        verifier doesn't act on it; the Coach uses it for analysis-mode
        scoring posture.
    redact_unmatched
        Strict mode (mission law 3; see module docstring). ``False``
        keeps the original contract: spans under ``MIN_QUOTE_WORDS`` pass
        untouched, an unmatched span keeps its words with a softener, and
        an unterminated quote is left alone.
    lookup
        Strict mode only (ignored otherwise); ``None`` keeps today's
        behaviour exactly. A span left unmatched is re-matched against
        ``corpus_chunks`` plus ``lookup(span)`` — that span's chunks only.
        Pass a reply-scoped :class:`QuoteLookup`; any other callable is
        wrapped in one for this call (memoised, budgeted).
    """
    if not isinstance(response_text, str):
        # Boundary guard — pydantic-typed callers can't trip this, but
        # ad-hoc callers (tests, REPL, future MCP wiring) might.
        raise TypeError(
            f"response_text must be str, got {type(response_text).__name__}"
        )

    quotes = (
        _extract(response_text, _STRICT_QUOTE_PATTERN, 1)
        if redact_unmatched
        else extract_quotes(response_text)
    )
    metadata = VerifierMetadata(retrieval_skipped_reason=retrieval_skipped_reason)

    # Strict mode: an opening quote that never closes is redacted from the
    # mark to the end, swallowing any paired span after it.
    unterminated_at = (
        _unterminated_quote_start(response_text) if redact_unmatched else None
    )
    if unterminated_at is not None:
        quotes = [quote for quote in quotes if quote.end <= unterminated_at]

    # Walk quotes in source order so splicing offsets stay valid as we
    # build the rewritten response. We accumulate the rewritten text in
    # a list-of-segments to avoid repeated O(n) string concatenation.
    if not redact_unmatched:
        lookup = None
    elif lookup is not None and not isinstance(lookup, QuoteLookup):
        lookup = QuoteLookup(lookup)

    output_segments: list[str] = []
    cursor = 0
    for quote in quotes:
        result = verify_quote(quote, corpus_chunks, session_text_name)
        if isinstance(result, NoMatchStrip) and lookup is not None:
            # Same matcher, session chunks + this span's own lookup chunks.
            own_chunks = lookup(quote.text)
            if own_chunks:
                result = verify_quote(
                    quote, [*corpus_chunks, *own_chunks], session_text_name
                )
        if isinstance(result, NoMatchStrip) and redact_unmatched:
            result = NoMatchStrip(
                original_span=result.original_span, softened=False, redacted=True
            )

        # Emit the response slice between the previous quote (or start)
        # and this quote, applying the no-match softener if needed.
        before = response_text[cursor : quote.start]
        if isinstance(result, NoMatchStrip) and result.softened:
            before = _soften_certainty_prefix(before)
        output_segments.append(before)

        replacement = _build_replacement(result, quote, metadata.shortenings)
        output_segments.append(replacement)

        # Bucket the result into the correct metadata list.
        if isinstance(result, PrimaryMatch):
            metadata.primary_matches.append(result)
            if result.citation_anchor is None:
                metadata.anchorless_primary_matches += 1
        elif isinstance(result, SecondaryRewrite):
            metadata.secondary_rewrites.append(result)
        elif isinstance(result, FuzzyCorrection):
            metadata.fuzzy_corrections.append(result)
            if result.citation_anchor is None:
                metadata.anchorless_fuzzy_corrections += 1
        elif isinstance(result, CrossTextEvent):
            metadata.cross_text_events.append(result)
        elif isinstance(result, NoMatchStrip):
            metadata.no_match_strips.append(result)
        else:  # pragma: no cover — defence-in-depth
            raise TypeError(
                f"unexpected MatchResult variant: {type(result).__name__}"
            )

        cursor = quote.end

    if unterminated_at is not None:
        # Everything from the unclosed opening mark onward was presented
        # as quotation and can never be verified as a whole span.
        output_segments.append(response_text[cursor:unterminated_at])
        output_segments.append(UNVERIFIED_QUOTE_TEXT)
        metadata.no_match_strips.append(
            NoMatchStrip(
                original_span=response_text[unterminated_at + 1 :],
                softened=False,
                redacted=True,
            )
        )
        cursor = len(response_text)

    # Tail of the response after the last quote.
    output_segments.append(response_text[cursor:])
    rewritten = "".join(output_segments)
    return (rewritten, metadata)


__all__ = [
    "MIN_QUOTE_WORDS",
    "MAX_QUOTE_LOOKUPS_PER_REPLY",
    "QuoteLookup",
    "FUZZY_MAX_EDIT_DISTANCE",
    "LONG_PASSAGE_WORD_THRESHOLD",
    "SHORT_QUOTE_MAX_WORDS",
    "SECONDARY_ATTRIBUTION_TEMPLATES",
    "UNVERIFIED_QUOTE_TEXT",
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
