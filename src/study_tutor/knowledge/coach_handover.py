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
5. **Strict mode fails closed** (``redact_unmatched=True``, mission law
   3 — both production call sites). The verifier runs in strict mode, and
   on a verifier exception the fallback text is the Player's response with
   EVERY double-quoted span (closed or unterminated) replaced by
   :data:`~study_tutor.knowledge.quote_verifier.UNVERIFIED_QUOTE_TEXT` —
   a plain regex pass that does not depend on the verifier — still flagged
   ``verifier_exception=True``. The text returned is what the learner
   receives and what the Coach evaluates, so nothing unverified is
   released on the first attempt or on a revision.

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
import re
from typing import Callable, Sequence

from study_tutor.knowledge.corpus_models import CorpusChunk
from study_tutor.knowledge.quote_verifier import (
    UNVERIFIED_QUOTE_TEXT,
    VerifierMetadata,
    verify_quotes,
)

logger = logging.getLogger(__name__)

# Every double-quoted span, closed or not: a straight pair, a curly pair,
# or an opening mark (straight or curly) with no close, through to the
# end. Deliberately independent of the verifier's own extraction — this
# runs precisely when the verifier has failed.
_ANY_QUOTED_SPAN = re.compile(r'"[^"]*"|“[^”]*”|["“].*\Z', re.DOTALL)


def redact_every_quoted_span(text: str) -> str:
    """Replace every double-quoted span in ``text`` with the neutral text.

    The strict-mode fail-closed fallback (law 3): used when the verifier
    raised, so no span can be told verified from invented.
    """
    return _ANY_QUOTED_SPAN.sub(UNVERIFIED_QUOTE_TEXT, text)


def apply_quote_verification(
    player_response: str,
    corpus_chunks: Sequence[CorpusChunk],
    session_text_name: str,
    retrieval_skipped_reason: str | None = None,
    *,
    redact_unmatched: bool = False,
    lookup: Callable[[str], Sequence[CorpusChunk]] | None = None,
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
    redact_unmatched
        Strict mode (mission law 3), forwarded to :func:`verify_quotes`.
        Also makes the exception fallback fail CLOSED: every quoted span
        is redacted instead of the raw response being returned.
    lookup
        Strict mode's quote-anchored lookup, forwarded to
        :func:`verify_quotes` (a reply-scoped
        :class:`~study_tutor.knowledge.quote_verifier.QuoteLookup`).
        ``None`` keeps today's behaviour exactly.

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
            redact_unmatched=redact_unmatched,
            lookup=lookup,
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
                "redact_unmatched": redact_unmatched,
            },
        )
        fallback_metadata = VerifierMetadata(
            retrieval_skipped_reason=retrieval_skipped_reason,
            verifier_exception=True,
        )
        if redact_unmatched:
            # Fail closed (law 3): nothing quoted survives an unverified turn.
            return (redact_every_quoted_span(player_response), fallback_metadata)
        return (player_response, fallback_metadata)

    return (rewritten, metadata)


__all__ = ["apply_quote_verification", "redact_every_quoted_span"]
