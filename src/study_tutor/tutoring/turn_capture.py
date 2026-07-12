"""Per-turn capture-signal derivation (S-E4 / scope §4.3–§4.4).

Two pure functions turn the orchestrator's per-turn output into the capture
signals the session service persists on ``session_turn`` / the session counter:

* :func:`embedded_quote_count` — R8: the count of **corpus-hit** quotations the
  deterministic quote verifier confirmed (verbatim ``primary_matches`` +
  near-verbatim ``fuzzy_corrections`` against the session text). This is the
  arbiter for Quote Champion / Quote Master — never Coach judgment.
* :func:`observed_ao_scaffolded` — R9: the Coach-**observed** AO scaffolded this
  turn. The plan's primary focus AO, credited only when the Coach's
  ``ao_alignment`` criterion confirms the turn actually aligned to it — so a turn
  that drifted off the planned AO records nothing rather than an unearned AO.

Kept out of the transport adapters (D14): the reply factory calls these and puts
the results on the reply metadata; the service reads the metadata generically.
"""
from __future__ import annotations

from typing import Any, Iterable

from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.tutoring.coach.rubric import CRITERION_AO_ALIGNMENT

#: The ``ao_alignment`` score at/above which the Coach is taken to have *observed*
#: the planned AO scaffolded this turn (R9). Below it the turn drifted and no AO
#: is credited — Six-AO Sampler stays honest.
AO_ALIGNMENT_OBSERVED_THRESHOLD: float = 0.5


def embedded_quote_count(metadata: VerifierMetadata | None) -> int:
    """Corpus-hit quotations the verifier confirmed this turn (R8).

    Counts verbatim primary-text matches plus near-verbatim fuzzy corrections
    (both are grounded in the session's primary text). Secondary rewrites,
    cross-text events, and no-match strips are NOT embedded quotations. ``None``
    (no verifier wired / a pre-response fallback) counts as 0.
    """
    if metadata is None:
        return 0
    return len(metadata.primary_matches) + len(metadata.fuzzy_corrections)


def _ao_alignment_score(verdict: Any) -> float | None:
    """The Coach's ``ao_alignment`` criterion score, or ``None`` if absent."""
    criterion_scores = getattr(verdict, "criterion_scores", None) or ()
    for score in criterion_scores:
        if getattr(score, "criterion_id", None) == CRITERION_AO_ALIGNMENT:
            return float(getattr(score, "score", 0.0))
    return None


def observed_ao_scaffolded(
    verdict: Any, focus_aos: Iterable[str] | None
) -> str | None:
    """The Coach-observed AO scaffolded this turn (R9), or ``None``.

    Returns the plan's primary focus AO only when the Coach's ``ao_alignment``
    score confirms the turn met the alignment bar; otherwise ``None`` (no focus
    AO, no verdict, or the turn drifted off the planned objective).
    """
    focus = tuple(focus_aos or ())
    if not focus:
        return None
    score = _ao_alignment_score(verdict)
    if score is None or score < AO_ALIGNMENT_OBSERVED_THRESHOLD:
        return None
    return focus[0]


__all__ = [
    "AO_ALIGNMENT_OBSERVED_THRESHOLD",
    "embedded_quote_count",
    "observed_ao_scaffolded",
]
