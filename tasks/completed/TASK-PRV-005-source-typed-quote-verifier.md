---
complexity: 6
consumer_context:
- consumes: SourceTypedCorpus
  driver: pydantic
  format_note: Reads CorpusChunk.citation_anchor directly from chunk metadata; never
    re-parses chunk text to construct citations
  framework: Pydantic v2 (BaseModel + discriminated union)
  task: TASK-PRV-002
dependencies:
- TASK-PRV-002
estimated_minutes: 100
feature_id: FEAT-PRV4
id: TASK-PRV-005
implementation_mode: task-work
parent_review: TASK-REV-PRV4
priority: high
related_features:
- FEAT-PH1-004
- FEAT-PH1-003
status: completed
updated: '2026-04-30T22:20:00Z'
tags:
- feat-ph1-004
- verifier
- quote
- source-typed
- safety
- fuzzy-correction
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: Source-typed quote verifier with four match types
wave: 3
---

# Task: Source-typed quote verifier with four match types

## Description

Implement `src/study_tutor/knowledge/quote_verifier.py` — the
load-bearing safety surface. Extracts quoted spans from a Player
response, classifies each into one of four match types using strict
precedence ordering (which closes Open Question 3 from the 23-Apr
empirical findings), rewrites the response in place, and emits
structured `VerifierMetadata` for the Coach.

## Scope

### Constants

- `MIN_QUOTE_WORDS = 4` (ASSUM-002)
- `FUZZY_MAX_EDIT_DISTANCE = 3` (ASSUM-003)
- `LONG_PASSAGE_WORD_THRESHOLD = 30`, `SHORT_QUOTE_MAX_WORDS = 12`
  (ASSUM-011)
- `SECONDARY_ATTRIBUTION_TEMPLATES = ("as one critic observes",
  "as one study guide notes", "as one commentator suggests")`
  (ASSUM-010)

### Pydantic models (co-located in this module)

- `PrimaryMatch`, `SecondaryRewrite`, `FuzzyCorrection`,
  `NoMatchStrip`, `CrossTextEvent`, `Shortening`, `VerifierMetadata`
  (per IMPLEMENTATION-GUIDE §4 contract)

### Functions

- `extract_quotes(response_text: str) -> list[Quote]` — finds
  typographic and straight-quote spans; ignores spans below 4 words
- `_normalise(text: str) -> str` — collapses whitespace, strips
  surrounding punctuation, equates curly/straight quotes, lowercases
- `verify_quote(quote: Quote, corpus_chunks: list[CorpusChunk],
  session_text_name: str) -> MatchResult` — applies the precedence
  ordering
- `verify_quotes(response_text: str, corpus_chunks: list[CorpusChunk],
  session_text_name: str, retrieval_skipped_reason: str | None =
  None) -> tuple[str, VerifierMetadata]` — the public entry point;
  returns the rewritten response and metadata

### Match precedence (Open Question 3 closure)

Per the §4 contract:

1. Exact match against any `PRIMARY_TEXT` chunk for `session_text_name`
   → `PrimaryMatch` (annotate with `chunk.citation_anchor`)
2. Exact match against any `PRIMARY_TEXT` chunk for a **different**
   text → `CrossTextEvent` (paraphrase rewrite; never annotate with
   wrong citation)
3. Exact match against any `SECONDARY_*` chunk → `SecondaryRewrite`
   (strip quotes; deterministic attribution from
   `SECONDARY_ATTRIBUTION_TEMPLATES`)
4. Fuzzy match (≤3 edits) against a `PRIMARY_TEXT` chunk for
   `session_text_name` → `FuzzyCorrection`
5. No match → `NoMatchStrip` (strip quotes + soften certainty)

**Fuzzy correction is restricted to primary-text source.** This is
the load-bearing invariant that prevents secondary phrasings from
being "corrected" into misattributed primary citations.

### Long-passage shortening

Runs after match resolution. `PrimaryMatch` whose `original_span`
exceeds `LONG_PASSAGE_WORD_THRESHOLD` words → reduce to the
densest analytical span (`SHORT_QUOTE_MAX_WORDS` cap), emit
`Shortening` event, replace the span in the rewritten response.

### Citation reading

Reads `chunk.citation_anchor` directly. Never re-parses chunk text
to construct citations. Covers @edge-case @verify @integration
@citation scenario.

### Concurrency

Pure function: no shared mutable state. Two concurrent
`verify_quotes` calls produce independent results. Covered by
@edge-case @verify @concurrency scenario.

## Out of Scope

- Coach handover wiring (TASK-PRV-006 — wires this verifier into
  the orchestrator)
- The Coach's `score_rubric.quote_fidelity` mapping (downstream
  TASK-DTL-002)
- Embedding-based pre-generation grounding (Phase B / Phase 2)

## Acceptance Criteria

- [ ] Verbatim primary quote → `PrimaryMatch` with citation
      annotation; original span retained as author's words
      (covers @key-example @smoke @verify @primary scenario)
- [ ] Secondary-only phrase → quotes stripped, paraphrase with
      attribution from `SECONDARY_ATTRIBUTION_TEMPLATES`; never
      returned as author's words (covers @key-example @smoke
      @verify @secondary @safety scenario)
- [ ] Near-verbatim primary (≤3 edits) → `FuzzyCorrection` with
      canonical wording substituted (covers @key-example @verify
      @fuzzy scenario)
- [ ] Fabricated quote with no near-match → `NoMatchStrip` (quotes
      removed, certainty softened) (covers @key-example @verify
      @fabrication @safety scenario)
- [ ] Spans below 4 words ignored; 4+ words inspected (covers
      @boundary @verify Scenario Outline)
- [ ] Edit-distance boundary: 0/1/2/3 → corrected; 4+ → stripped
      (covers @boundary @verify @fuzzy Scenario Outline)
- [ ] **Open Question 3 closure** — span matching both primary and
      secondary chunks resolves to `PrimaryMatch` (covers
      @edge-case @verify @primary-wins scenario)
- [ ] Span matching only a different primary text → `CrossTextEvent`
      with paraphrase rewrite, never annotated with the session
      text's citation (covers @edge-case @verify @security
      @cross-text scenario)
- [ ] Whitespace/punctuation differences normalised — span matching
      primary in word sequence but differing in formatting still
      matches (covers @edge-case @verify @whitespace scenario)
- [ ] Multiple secondary-only quotes in one response are all
      rewritten (covers @negative @verify @safety scenario)
- [ ] Long verbatim passage → `Shortening` to ≤12 words (covers
      @edge-case @verify @safety @copyright scenario)
- [ ] Concurrent calls produce independent results — no shared
      state (covers @edge-case @verify @concurrency scenario)
- [ ] Instruction-like text in chunk content does not steer the
      verifier — chunk content treated as data only (covers
      @edge-case @verify @security @prompt-injection scenario)
- [ ] Citation derived from `chunk.citation_anchor`, not re-parsed
      from chunk text (covers @edge-case @verify @integration
      @citation scenario)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test per match type (5 cases: primary, secondary,
      cross-text, fuzzy, no-match)
- [ ] Parametrised test: minimum-span boundary (3/4/5 words)
- [ ] Parametrised test: edit-distance boundary (0/1/2/3/4 edits)
- [ ] **Open Question 3 test:** quote that matches both primary
      and secondary corpus chunks → resolves to PrimaryMatch
- [ ] Cross-text mismatch test: span from text A in a session on
      text B → CrossTextEvent
- [ ] Whitespace-normalisation test
- [ ] Long-passage shortening test (>30 words → ≤12)
- [ ] Concurrency test: two parallel `verify_quotes` calls produce
      independent results
- [ ] Prompt-injection test: chunk containing "ignore previous
      instructions" treated as data
- [ ] Citation-anchor pass-through test: verifier asserts
      `chunk.citation_anchor` is read directly, not via regex on
      `chunk.text`

## Seam Tests

```python
"""Seam test: verify the VerifierMetadata contract consumed by the
Coach handover (TASK-PRV-006) and downstream by TASK-DTL-002."""
import pytest
from study_tutor.knowledge.quote_verifier import (
    verify_quotes, VerifierMetadata, PrimaryMatch, SecondaryRewrite,
)


@pytest.mark.seam
@pytest.mark.integration_contract("VerifierMetadata")
def test_verify_quotes_returns_rewritten_response_and_metadata(macbeth_corpus):
    """Verify verify_quotes returns (rewritten_response,
    VerifierMetadata) and the rewritten response (not the original)
    is what reaches the Coach.

    Contract: VerifierMetadata is the structured handover the
    Coach's score_rubric.quote_fidelity criterion derives its
    score from.
    Producer: this task
    Consumer: TASK-PRV-006 (handover wiring), TASK-DTL-002
    (Coach criterion).
    """
    response = (
        'Lady Macbeth says "Out, damned spot! out, I say!" — '
        'a famous line. As one critic notes, this shows guilt.'
    )
    rewritten, metadata = verify_quotes(
        response, macbeth_corpus, session_text_name="macbeth",
    )

    assert isinstance(metadata, VerifierMetadata)
    assert metadata.primary_matches, "expected one primary match"
    assert metadata.primary_matches[0].citation_anchor is not None

    # Rewritten response carries the citation annotation
    assert "(5.1" in rewritten or "Act 5" in rewritten, \
        "rewritten response must include the citation annotation"
```

## Implementation Notes

**Why precedence ordering is the closure for Open Question 3:**
the empirical risk was that a study-guide phrase ≤3 edits from a
Shakespeare line could be "corrected" into a misattributed primary
citation. The closure: secondary-verbatim (precedence step 3)
fires *before* fuzzy-primary (step 4), so a secondary match always
wins over a fuzzy primary match. Combined with restricting fuzzy
correction to primary-text source only, no secondary phrase can
ever emerge as a primary annotation. Tested explicitly.

**Why match types are Pydantic models, not enums + dicts:** the
Coach's `score_rubric` derives the criterion score by counting
match-type instances; type-safe attribute access (`metadata.
secondary_rewrites`) is much harder to misuse than dict lookup.

**Why long-passage shortening runs after match resolution:** we
need to know the chunk and citation anchor before we can pick the
densest analytical span — that selection depends on chunk
boundaries and the matched text.

**Why deterministic secondary-attribution pick (hash of phrase):**
makes test fixtures stable. Production-time variety can be added
later by hashing on phrase + turn ID — out of scope here.

## Test Execution Log

[Populated by /task-work]