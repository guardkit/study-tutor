"""Coach-handover seam — verifier → orchestrator → Coach (TASK-PRV-006).

This module owns the thin handover between the quote-verifier
(TASK-PRV-005) and the :class:`PlayerCoachOrchestrator`'s Coach call
(FEAT-PH1-003). It exists as a separate module — rather than living
inside ``orchestrator.py`` — so the FEAT-PH1-003 module keeps its
single responsibility (Player-Coach loop policy) and the verifier
boundary is testable in isolation.

What this seam guarantees
-------------------------
1. The Coach evaluates the **rewritten** Player response, not the raw
   one. ``verify_quotes`` annotates verbatim primary citations, strips
   no-match quotes, and rewrites secondary phrasings; the rewritten
   string is what reaches the learner *and* the Coach.
2. :class:`VerifierMetadata` is forwarded so the Coach's
   ``quote_fidelity`` criterion (TASK-DTL-002) can score against
   structured match-type counts rather than re-parsing prose.
3. ``retrieval_skipped_reason`` (from TASK-PRV-003's
   :class:`RetrievalDecision`) is surfaced into metadata so the Coach
   suppresses its ``quote_fidelity`` down-rank in AnalysisMode (no
   primary-text corpus → fabricated quotes are not the Player's fault
   in the same way they are when a primary corpus was available).
4. **Verifier exception → graceful degradation.** If
   :func:`verify_quotes` raises, this seam returns the original Player
   response unannotated together with an empty
   :class:`VerifierMetadata` whose ``verifier_exception`` flag is set;
   the Coach then skips the ``quote_fidelity`` down-rank for the turn.
   Failing the entire turn on a verifier hiccup would surface as a
   worse learner experience than continuing with an unannotated reply.

Why a tuple return rather than raising
--------------------------------------
The orchestrator catches a separate set of failure modes (Coach
unreachable, Player unavailable mid-revision) under the unevaluated-turn
fallback policy already specified by TASK-DTL-002. Surfacing the
verifier-exception case as part of the normal return value keeps the
orchestrator's control flow linear: it always gets back a
``(response_for_coach, metadata)`` pair and never has to interleave
verifier-specific exception handling with its existing fallback
branches.

Concurrency
-----------
:func:`apply_quote_verification` is a pure wrapper around
:func:`verify_quotes`, which the verifier module documents as pure.
Two concurrent invocations are independent.
"""

from __future__ import annotations

import logging
from typing import Sequence

from study_tutor.knowledge.corpus_models import CorpusChunk
from study_tutor.knowledge.quote_verifier import VerifierMetadata, verify_quotes

logger = logging.getLogger(__name__)


def apply_quote_verification(
    player_response: str,
    corpus_chunks: Sequence[CorpusChunk],
    session_text_name: str,
    retrieval_skipped_reason: str | None = None,
) -> tuple[str, VerifierMetadata]:
    """Run the verifier and return the Coach-ready ``(response, metadata)`` pair.

    On the success path this is a thin wrapper around
    :func:`study_tutor.knowledge.quote_verifier.verify_quotes`. On the
    failure path (any exception raised by the verifier) it returns the
    *original* response unannotated together with an empty
    :class:`VerifierMetadata` whose ``verifier_exception`` flag is set.
    The Coach uses that flag to suppress its ``quote_fidelity`` down-rank
    for the turn (per TASK-DTL-002 acceptance criterion
    "verifier-exception → unannotated to Coach").

    Parameters
    ----------
    player_response
        The Player's raw response text. Quoted spans inside it will be
        verified against ``corpus_chunks``; non-quoted text passes
        through verbatim.
    corpus_chunks
        The retrieved (or full) corpus to verify against. May be empty
        — an empty corpus simply means every quote will fall through to
        :class:`~study_tutor.knowledge.quote_verifier.NoMatchStrip`.
    session_text_name
        The literary work the session is on (e.g. ``"Macbeth"``). Used
        by the verifier to distinguish session-text matches from
        cross-text matches.
    retrieval_skipped_reason
        Forwarded from the upstream retrieval-decision step (TASK-PRV-003).
        ``None`` when retrieval ran normally; one of the ``REASON_*``
        constants from :mod:`study_tutor.knowledge.retrieval` when the
        decision tree skipped retrieval (AnalysisMode, AO3-only,
        embedder-timeout). Forwarded into
        :class:`VerifierMetadata.retrieval_skipped_reason` so the Coach
        can apply analysis-mode scoring posture without re-deriving the
        decision.

    Returns
    -------
    tuple[str, VerifierMetadata]
        ``(response_for_coach, metadata)``. The first element is the
        text the orchestrator should pass to ``Coach.evaluate`` (and
        that the learner will see). The second is the structured
        verifier output the Coach consumes for its
        ``quote_fidelity`` criterion.
    """
    try:
        rewritten, metadata = verify_quotes(
            player_response,
            corpus_chunks,
            session_text_name,
            retrieval_skipped_reason=retrieval_skipped_reason,
        )
    except Exception as exc:  # noqa: BLE001 — graceful-degradation boundary
        # Log with structured context so session-end review can spot
        # repeated verifier failures without the failure crashing the
        # turn. This is the only place a broad ``except`` is justified
        # — the contract here is "the verifier never fails the turn".
        logger.warning(
            "coach_handover.verifier_exception",
            extra={
                "event": "coach_handover_verifier_exception",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "session_text_name": session_text_name,
            },
        )
        fallback_metadata = VerifierMetadata(
            retrieval_skipped_reason=retrieval_skipped_reason,
            verifier_exception=True,
        )
        return (player_response, fallback_metadata)

    return (rewritten, metadata)


__all__ = ["apply_quote_verification"]
