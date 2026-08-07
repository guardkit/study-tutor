"""Hermetic tests for the golden-quote fabrication harness (Lane 2 step 3).

Covers the four surfaces the build order names:

1. Independent quote extraction — straight + curly double quotes, markdown
   block-quote runs, the '/' verse-linebreak convention, min-words filter.
2. Fuzzy-metric + scorer maths — windowed SequenceMatcher ratio semantics,
   aggregation, citation coverage, bar verdicts, markdown rendering.
3. Golden-set schema validation — the shipped ``golden_quotes.jsonl``
   parses, is >= 24 items across all three texts, carries the four spec
   seed cases verbatim, and the validator rejects malformed items.
4. T1 end-to-end — the hermetic tier drives the production closure
   (fake collection provider + ImportError reranker, the
   ``test_cli_rag_wiring.py`` pattern) and produces the right verdicts for
   a known-good verbatim quote (anchorless primary match, NO citation, no
   strip, no exception) and a known fabrication (strip + fabricated).

Hermeticity: no network, no real ChromaDB, no model server, no filesystem
writes outside pytest tmp facilities.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Iterator

import pytest

from scripts.eval.run_fabrication_eval import (
    EVAL_MIN_QUOTE_WORDS,
    GOLDEN_PATH_DEFAULT,
    MATCH_THRESHOLD,
    best_corpus_match,
    best_window_ratio,
    build_t1_closure,
    evaluate_item,
    extract_quoted_spans,
    load_golden,
    normalise_for_match,
    validate_golden_item,
)
from scripts.eval.score_fabrication import (
    PHASE_A_BAR,
    PHASE_B_BAR,
    _bar_verdict,
    aggregate,
    render_markdown,
)
from study_tutor.knowledge.retrieval import (
    clear_primary_text_index,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
)


@pytest.fixture(autouse=True)
def _isolate_retrieval_state() -> Iterator[None]:
    """Module-level retrieval state isolation (test_cli_rag_wiring pattern)."""
    clear_primary_text_index()
    reset_collection_provider()
    reset_reranker_factory()
    reset_embedder_probe()
    yield
    clear_primary_text_index()
    reset_collection_provider()
    reset_reranker_factory()
    reset_embedder_probe()


# ---------------------------------------------------------------------------
# 1. Extraction
# ---------------------------------------------------------------------------


def test_extract_straight_double_quotes() -> None:
    spans = extract_quoted_spans(
        'He says "Is this a dagger which I see before me" in Act 2.'
    )
    assert spans == ["Is this a dagger which I see before me"]


def test_extract_curly_double_quotes() -> None:
    spans = extract_quoted_spans(
        "Lady Macbeth hears “The raven himself is hoarse tonight” here."
    )
    assert spans == ["The raven himself is hoarse tonight"]


def test_extract_block_quote_run_joins_lines() -> None:
    response = (
        "Consider the soliloquy:\n"
        "> To-morrow, and to-morrow, and to-morrow,\n"
        "> Creeps in this petty pace from day to day\n"
        "which shows despair."
    )
    spans = extract_quoted_spans(response)
    assert spans == [
        "To-morrow, and to-morrow, and to-morrow, / "
        "Creeps in this petty pace from day to day"
    ]


def test_extract_min_words_filter() -> None:
    # 3 words -> dropped; 4 words -> kept (EVAL_MIN_QUOTE_WORDS boundary).
    assert extract_quoted_spans('She said "out damned spot" then.') == []
    assert extract_quoted_spans('She said "out out damned spot" then.') == [
        "out out damned spot"
    ]
    assert EVAL_MIN_QUOTE_WORDS == 4


def test_extract_preserves_slash_convention() -> None:
    spans = extract_quoted_spans(
        '"Stars, hide your fires; / Let not light see my black and deep desires"'
    )
    assert spans == [
        "Stars, hide your fires; / Let not light see my black and deep desires"
    ]
    # ...and normalisation neutralises the slash for matching.
    assert (
        normalise_for_match(spans[0])
        == "stars, hide your fires; let not light see my black and deep desires"
    )


# ---------------------------------------------------------------------------
# 2. Fuzzy metric + scorer maths
# ---------------------------------------------------------------------------


def test_normalise_for_match_curly_and_whitespace() -> None:
    assert (
        normalise_for_match("  “Fair   is foul, /\nand foul is fair.”  ")
        == "fair is foul, and foul is fair"
    )


def test_best_window_ratio_exact_substring_is_one() -> None:
    chunk = normalise_for_match(
        "Give him tending; he brings great news. The raven himself is hoarse "
        "that croaks the fatal entrance of Duncan under my battlements."
    )
    quote = normalise_for_match(
        "The raven himself is hoarse / That croaks the fatal entrance of Duncan"
    )
    assert best_window_ratio(quote, chunk) == 1.0


def test_best_window_ratio_near_miss_and_fabrication() -> None:
    chunk = normalise_for_match(
        "To-morrow, and to-morrow, and to-morrow, creeps in this petty pace "
        "from day to day to the last syllable of recorded time."
    )
    near_miss = normalise_for_match("creeps in this petty place from day to day")
    fabricated = normalise_for_match(
        "unmaculate me from the deed of mortal coats tonight"
    )
    assert best_window_ratio(near_miss, chunk) >= MATCH_THRESHOLD
    assert best_window_ratio(fabricated, chunk) < MATCH_THRESHOLD


def test_best_corpus_match_picks_best_chunk() -> None:
    chunks = [
        {"text": "Completely unrelated prose about photosynthesis.", "chunk_index": 0},
        {"text": "Is this a dagger which I see before me, the handle", "chunk_index": 1},
    ]
    ratio, idx = best_corpus_match("Is this a dagger which I see before me", chunks)
    assert ratio == 1.0
    assert idx == 1


def test_scorer_aggregation_and_verdicts() -> None:
    records = [
        {
            "item_id": "a",
            "text_name": "macbeth",
            "quotes": [
                {"fabricated": False},
                {"fabricated": True},
            ],
            "verifier": {
                "primary_matches": 1,
                "fuzzy_corrections": 0,
                "anchorless_primary_matches": 1,
                "anchorless_fuzzy_corrections": 0,
                "no_match_strips": 1,
                "verifier_exception": False,
            },
            "false_correction_flags": [],
        },
        {
            "item_id": "b",
            "text_name": "an_inspector_calls",
            "quotes": [{"fabricated": False}, {"fabricated": False}],
            "verifier": {
                "primary_matches": 2,
                "fuzzy_corrections": 0,
                "anchorless_primary_matches": 1,
                "anchorless_fuzzy_corrections": 0,
                "no_match_strips": 0,
                "verifier_exception": False,
            },
            "false_correction_flags": [{"kind": "no_match_strip"}],
        },
    ]
    buckets = aggregate(records)
    overall = buckets["overall"]
    assert overall.quotes == 4
    assert overall.fabricated == 1
    assert overall.fabrication_rate == 0.25
    # 3 verified matches, 2 anchorless -> coverage 1/3.
    assert overall.verified_matches == 3
    assert overall.citation_coverage == pytest.approx(1 / 3)
    assert overall.false_correction_flags == 1
    assert buckets["macbeth"].fabrication_rate == 0.5
    assert buckets["an_inspector_calls"].fabrication_rate == 0.0

    report = render_markdown(buckets, "test.jsonl")
    assert "< 5% (Phase A)" in report
    assert "< 1% (Phase B)" in report
    assert "| macbeth |" in report
    assert "**overall**" in report
    assert "`a`" in report  # fabrication-flagged item named


def test_bar_verdict_thresholds() -> None:
    assert PHASE_A_BAR == 0.05 and PHASE_B_BAR == 0.01  # frozen
    assert _bar_verdict(None) == "no quotes"
    assert _bar_verdict(0.0) == "PASS (Phase B)"
    assert _bar_verdict(0.009) == "PASS (Phase B)"
    assert _bar_verdict(0.04) == "PASS (Phase A)"
    assert _bar_verdict(0.05) == "FAIL"
    assert _bar_verdict(0.25) == "FAIL"


# ---------------------------------------------------------------------------
# 3. Golden-set schema
# ---------------------------------------------------------------------------


def test_shipped_golden_set_is_valid_and_covers_all_texts() -> None:
    items = load_golden(GOLDEN_PATH_DEFAULT)
    assert len(items) >= 24
    texts = {i["text_name"] for i in items}
    assert texts == {"macbeth", "an_inspector_calls", "power_and_conflict_poems"}
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids))


def test_shipped_golden_set_carries_spec_seeds_verbatim() -> None:
    """The four rag-grounding-design §4 seed cases, expected_exact verbatim."""
    by_id = {i["id"]: i for i in load_golden(GOLDEN_PATH_DEFAULT)}
    seeds = {
        "qf-macbeth-unsex": (
            "Come, you spirits / That tend on mortal thoughts, unsex me here"
        ),
        "qf-macbeth-raven": (
            "The raven himself is hoarse / That croaks the fatal entrance of Duncan"
        ),
        "qf-macbeth-dagger": "Is this a dagger which I see before me",
        "qf-macbeth-innocent-flower": (
            "Look like the innocent flower, / But be the serpent under 't"
        ),
    }
    for seed_id, expected in seeds.items():
        assert seed_id in by_id, f"missing seed {seed_id}"
        assert by_id[seed_id]["expected_exact"] == expected
        assert by_id[seed_id]["text_name"] == "macbeth"
    assert by_id["qf-macbeth-unsex"]["known_fabrications"] == [
        "That tend on mortal coats… unmaculate me from the deed"
    ]


def test_validator_rejects_malformed_items() -> None:
    good = {
        "id": "x",
        "text_name": "macbeth",
        "prompt": "Quote the dagger line.",
        "expected_exact": "Is this a dagger which I see before me",
        "canonical_citation": "Macbeth 2.1.33",
        "category": "recall",
        "source_check": "PRESENT chunk 68",
    }
    assert validate_golden_item(good) == []

    assert validate_golden_item({**good, "text_name": "Macbeth"})  # not slug
    assert validate_golden_item({**good, "category": "vibes"})
    assert validate_golden_item({**good, "expected_exact": "too short"})
    assert validate_golden_item({**good, "canonical_citation": ""})
    assert validate_golden_item({**good, "known_fabrications": "not-a-list"})
    # Law 4: AQA assessment-material markers are rejected.
    assert validate_golden_item(
        {**good, "prompt": "Answer this past paper question."}
    )


# ---------------------------------------------------------------------------
# 4. T1 end-to-end (hermetic tier through the production closure)
# ---------------------------------------------------------------------------


def _t1_items() -> list[dict]:
    by_id = {i["id"]: i for i in load_golden(GOLDEN_PATH_DEFAULT)}
    return [by_id["qf-macbeth-dagger"], by_id["qf-macbeth-unsex"]]


def test_t1_known_good_quote_is_anchorless_primary_without_citation() -> None:
    items = _t1_items()
    closure, metric_corpus = build_t1_closure(items)
    dagger = items[0]
    response = (
        'Macbeth hallucinates: "Is this a dagger which I see before me" — '
        "the vision externalises his guilt."
    )
    result = evaluate_item(dagger, response, "supplied", closure, metric_corpus)

    # Harness metric: the quote is real -> not fabricated.
    assert len(result.quotes) == 1
    assert result.quotes[0].fabricated is False
    assert result.quotes[0].best_ratio == 1.0
    assert result.expected_quoted is True

    # Verifier verdict: anchorless primary match (the Track A fix) — not a
    # strip, not an exception, and NO trailing citation annotation.
    assert result.verifier["verifier_exception"] is False
    assert result.verifier["primary_matches"] == 1
    assert result.verifier["anchorless_primary_matches"] == 1
    assert result.verifier["no_match_strips"] == 0
    assert '"Is this a dagger which I see before me"' in result.rewritten_response
    assert "(2.1" not in result.rewritten_response  # degraded citation: none


def test_t1_known_fabrication_is_stripped_and_counted() -> None:
    items = _t1_items()
    closure, metric_corpus = build_t1_closure(items)
    unsex = items[1]
    fabrication = unsex["known_fabrications"][0]
    response = f'Lady Macbeth cries "{fabrication}" as she rejects femininity.'
    result = evaluate_item(unsex, response, "supplied", closure, metric_corpus)

    assert len(result.quotes) == 1
    assert result.quotes[0].fabricated is True
    assert result.quotes[0].best_ratio < MATCH_THRESHOLD
    assert result.expected_quoted is False

    assert result.verifier["verifier_exception"] is False
    assert result.verifier["no_match_strips"] == 1
    assert result.verifier["primary_matches"] == 0
    # Quote marks stripped from the rewritten response.
    assert f'"{fabrication}"' not in result.rewritten_response
    # A genuinely fabricated span matches nothing -> no false-correction flag.
    assert result.false_correction_flags == []


def test_t1_end_to_end_scoreboard() -> None:
    """Compose runner verdicts into the scorer: 1 fabricated / 2 quotes."""
    items = _t1_items()
    closure, metric_corpus = build_t1_closure(items)
    records = []
    responses = {
        "qf-macbeth-dagger": (
            'See "Is this a dagger which I see before me" (Act 2).'
        ),
        "qf-macbeth-unsex": (
            'She cries "That tend on mortal coats… unmaculate me from the '
            'deed" here.'
        ),
    }
    for item in items:
        records.append(
            evaluate_item(
                item, responses[item["id"]], "supplied", closure, metric_corpus
            ).to_json()
        )
    buckets = aggregate(records)
    assert buckets["overall"].quotes == 2
    assert buckets["overall"].fabricated == 1
    assert buckets["overall"].fabrication_rate == 0.5
    # All verified matches are anchorless against the T1 (store-mirroring)
    # corpus -> citation coverage 0%.
    assert buckets["overall"].citation_coverage == 0.0
    report = render_markdown(buckets, "t1.jsonl")
    assert "FAIL" in report  # 50% is far above the frozen 5% bar
