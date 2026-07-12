"""Unit tests for per-turn capture-signal derivation (S-E4 §4.3/§4.4, R8/R9)."""
from __future__ import annotations

from study_tutor.knowledge.corpus_models import PlayCitationAnchor
from study_tutor.knowledge.quote_verifier import (
    FuzzyCorrection,
    NoMatchStrip,
    PrimaryMatch,
    SecondaryRewrite,
    VerifierMetadata,
)
from study_tutor.knowledge.corpus_models import SourceType
from study_tutor.tutoring.coach.factory import CoachVerdict, CriterionScore
from study_tutor.tutoring.coach.rubric import CRITERION_AO_ALIGNMENT
from study_tutor.tutoring.turn_capture import (
    embedded_quote_count,
    observed_ao_scaffolded,
)

_ANCHOR = PlayCitationAnchor(act=1, scene=7, line=1)


def _primary() -> PrimaryMatch:
    return PrimaryMatch(
        original_span="is this a dagger which i see",
        citation_anchor=_ANCHOR,
        chunk_index=0,
        text_name="macbeth",
    )


def _fuzzy() -> FuzzyCorrection:
    return FuzzyCorrection(
        original_span="out out brief candle",
        corrected_span="out, out, brief candle",
        edit_distance=2,
        citation_anchor=_ANCHOR,
        chunk_index=1,
        text_name="macbeth",
    )


# -- R8: embedded-quote count = primary + fuzzy corpus hits ------------------


def test_embedded_quote_count_counts_primary_and_fuzzy() -> None:
    meta = VerifierMetadata(
        primary_matches=[_primary(), _primary()],
        fuzzy_corrections=[_fuzzy()],
    )
    assert embedded_quote_count(meta) == 3


def test_embedded_quote_count_ignores_secondary_and_nomatch() -> None:
    meta = VerifierMetadata(
        secondary_rewrites=[
            SecondaryRewrite(
                original_span="a critic once wrote something long",
                attribution="as one critic observes",
                source_type=SourceType.SECONDARY_CRITICAL,
                chunk_index=0,
            )
        ],
        no_match_strips=[NoMatchStrip(original_span="not a real quote at all")],
    )
    assert embedded_quote_count(meta) == 0


def test_embedded_quote_count_none_is_zero() -> None:
    assert embedded_quote_count(None) == 0


# -- R9: Coach-observed AO scaffolded this turn ------------------------------


def _verdict(ao_alignment: float) -> CoachVerdict:
    return CoachVerdict(
        weighted_total=0.8,
        decision="accept",
        criterion_scores=[
            CriterionScore(
                criterion_id=CRITERION_AO_ALIGNMENT,
                score=ao_alignment,
                evidence="aligned to the planned AO",
            )
        ],
    )


def test_observed_ao_returns_focus_ao_when_aligned() -> None:
    assert observed_ao_scaffolded(_verdict(0.9), ["AO2", "AO1"]) == "AO2"


def test_observed_ao_none_when_unaligned() -> None:
    assert observed_ao_scaffolded(_verdict(0.2), ["AO2"]) is None


def test_observed_ao_none_without_focus() -> None:
    assert observed_ao_scaffolded(_verdict(0.9), []) is None
    assert observed_ao_scaffolded(_verdict(0.9), None) is None


def test_observed_ao_none_when_no_alignment_criterion() -> None:
    verdict = CoachVerdict(weighted_total=0.8, decision="accept", criterion_scores=[])
    assert observed_ao_scaffolded(verdict, ["AO2"]) is None
