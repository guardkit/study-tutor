"""Quote-anchored lookup in the verifier (strict mode only).

docs/design/quote-lookup-by-span-2026-10-18.md — :class:`QuoteLookup` is
reply-scoped and memoised (every outcome cached, budgeted), and
:func:`verify_quotes` re-matches an unmatched span against the session's
chunks plus ONLY that span's own lookup chunks.
"""

from __future__ import annotations

import logging

import pytest

from study_tutor.knowledge.coach_handover import apply_quote_verification
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.quote_verifier import (
    MAX_QUOTE_LOOKUPS_PER_REPLY,
    UNVERIFIED_QUOTE_TEXT,
    QuoteLookup,
    verify_quotes,
)

N = UNVERIFIED_QUOTE_TEXT


def _chunk(text: str, act: int, scene: int, line: int, index: int) -> CorpusChunk:
    return CorpusChunk(
        text=text,
        source_type=SourceType.PRIMARY_TEXT,
        source_path=f"/corpus/macbeth/{index}.txt",
        text_name="macbeth",
        citation_anchor=PlayCitationAnchor(act=act, scene=scene, line=line),
        chunk_index=index,
    )


NO_SPUR = _chunk(
    "I have no spur To prick the sides of my intent, but only Vaulting "
    "ambition, which o'erleaps itself And falls on the other.",
    1,
    7,
    25,
    7,
)
DAGGER = _chunk(
    "Is this a dagger which I see before me, The handle toward my hand?",
    2,
    1,
    33,
    21,
)
SPOT = _chunk("Out, damned spot! out, I say! One: two: why, then.", 5, 1, 35, 51)

SPUR_SPAN = "I have no spur To prick the sides of my intent"
DAGGER_SPAN = "Is this a dagger which I see before me"


class _Fetch:
    """Recording fetch: ``routes`` maps a substring of the span to chunks."""

    def __init__(self, routes: dict[str, list[CorpusChunk]] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[str] = []

    def __call__(self, span: str) -> list[CorpusChunk]:
        self.calls.append(span)
        for needle, chunks in self.routes.items():
            if needle in span:
                return chunks
        return []


# ---------------------------------------------------------------------------
# QuoteLookup — memoised, budgeted, every outcome cached
# ---------------------------------------------------------------------------


def test_quote_lookup_fetches_each_span_once() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})
    lookup = QuoteLookup(fetch)

    assert lookup(SPUR_SPAN) == (NO_SPUR,)
    assert lookup(SPUR_SPAN) == (NO_SPUR,)
    assert lookup("nothing here") == ()
    assert lookup("nothing here") == ()
    assert fetch.calls == [SPUR_SPAN, "nothing here"]
    assert lookup.lookups == 2


def test_quote_lookup_exception_is_cached_as_empty_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[str] = []

    def boom(span: str) -> list[CorpusChunk]:
        calls.append(span)
        raise RuntimeError("embedder down")

    lookup = QuoteLookup(boom)
    caplog.set_level(logging.WARNING, logger="study_tutor.knowledge.quote_verifier")

    assert lookup(SPUR_SPAN) == ()
    assert lookup(SPUR_SPAN) == ()
    assert calls == [SPUR_SPAN]
    assert any(r.getMessage() == "quote_lookup.failed" for r in caplog.records)


def test_quote_lookup_over_budget_is_cached_as_empty() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})
    lookup = QuoteLookup(fetch)
    spans = [f"invented line number {i}" for i in range(MAX_QUOTE_LOOKUPS_PER_REPLY)]
    for span in spans:
        lookup(span)

    # Budget spent: the genuine span is never fetched, now or later.
    assert lookup(SPUR_SPAN) == ()
    assert lookup(SPUR_SPAN) == ()
    assert fetch.calls == spans
    assert lookup.lookups == MAX_QUOTE_LOOKUPS_PER_REPLY == 4


# ---------------------------------------------------------------------------
# verify_quotes(lookup=...)
# ---------------------------------------------------------------------------


def test_strict_unmatched_span_found_by_lookup_survives_with_citation() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})
    reply = f'He admits "{SPUR_SPAN}" here.'

    rewritten, meta = verify_quotes(
        reply, [SPOT], "", redact_unmatched=True, lookup=QuoteLookup(fetch)
    )

    assert rewritten == f'He admits "{SPUR_SPAN}" (1.7.25) here.'
    assert len(meta.primary_matches) == 1
    assert meta.no_match_strips == []
    assert fetch.calls == [SPUR_SPAN]


def test_matched_span_is_never_looked_up() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})

    rewritten, _ = verify_quotes(
        f'He admits "{SPUR_SPAN}".', [NO_SPUR], "", redact_unmatched=True,
        lookup=QuoteLookup(fetch),
    )

    assert "(1.7.25)" in rewritten
    assert fetch.calls == []


def test_lookup_none_is_todays_strict_behaviour() -> None:
    reply = f'He admits "{SPUR_SPAN}" here.'

    assert verify_quotes(reply, [SPOT], "", redact_unmatched=True) == verify_quotes(
        reply, [SPOT], "", redact_unmatched=True, lookup=None
    )
    rewritten, _ = verify_quotes(reply, [SPOT], "", redact_unmatched=True)
    assert rewritten == f"He admits {N} here."


def test_lookup_is_ignored_outside_strict_mode() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})
    reply = f'He admits "{SPUR_SPAN}" here.'

    with_lookup = verify_quotes(reply, [SPOT], "macbeth", lookup=fetch)

    assert with_lookup == verify_quotes(reply, [SPOT], "macbeth")
    assert fetch.calls == []


def test_fabricated_span_with_lookup_returning_real_chunk_is_still_redacted() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})
    span = "I have no spur To prick the sides of Remorse, that when this deed"

    rewritten, meta = verify_quotes(
        f'He says "{span}".', [SPOT], "", redact_unmatched=True, lookup=fetch
    )

    assert rewritten == f"He says {N}."
    assert meta.no_match_strips[0].redacted is True
    assert fetch.calls == [span]


def test_each_span_matches_only_its_own_lookup_chunks() -> None:
    # The dagger span's own lookup misses; the spur span's lookup happens to
    # return the dagger chunk too. The dagger span must stay redacted — its
    # outcome may depend only on (span, session chunks, its own lookup).
    fetch = _Fetch({"dagger": [SPOT], "spur": [NO_SPUR, DAGGER]})
    lookup = QuoteLookup(fetch)
    reply = f'He asks "{DAGGER_SPAN}" first. Then "{SPUR_SPAN}" later.'

    rewritten, _ = verify_quotes(reply, [SPOT], "", redact_unmatched=True, lookup=lookup)

    assert rewritten == f'He asks {N} first. Then "{SPUR_SPAN}" (1.7.25) later.'
    # Re-verifying (a later streaming pass) changes nothing and fetches nothing.
    again, _ = verify_quotes(reply, [SPOT], "", redact_unmatched=True, lookup=lookup)
    assert again == rewritten
    assert fetch.calls == [DAGGER_SPAN, SPUR_SPAN]


def test_plain_callable_is_budgeted_per_call() -> None:
    fetch = _Fetch()
    spans = [f"invented line number {i}" for i in range(6)]
    reply = " ".join(f'"{span}"' for span in spans)

    rewritten, meta = verify_quotes(reply, [SPOT], "", redact_unmatched=True, lookup=fetch)

    assert rewritten == " ".join([N] * 6)
    assert len(meta.no_match_strips) == 6
    assert fetch.calls == spans[:MAX_QUOTE_LOOKUPS_PER_REPLY]


def test_short_span_lookup_needs_an_exact_match() -> None:
    fetch = _Fetch({"Vaulting": [NO_SPUR], "Vaulted": [NO_SPUR]})

    rewritten, _ = verify_quotes(
        'He fears "Vaulting ambition" and "Vaulted ambitions".',
        [SPOT],
        "",
        redact_unmatched=True,
        lookup=fetch,
    )

    assert rewritten == f'He fears "Vaulting ambition" (1.7.25) and {N}.'


def test_apply_quote_verification_forwards_lookup() -> None:
    fetch = _Fetch({"spur": [NO_SPUR]})

    rewritten, meta = apply_quote_verification(
        f'He admits "{SPUR_SPAN}".', [], "", redact_unmatched=True, lookup=fetch
    )

    assert rewritten == f'He admits "{SPUR_SPAN}" (1.7.25).'
    assert meta.verifier_exception is False
