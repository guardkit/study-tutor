"""ADR-ARCH-027 verified streaming (PlayerCoachOrchestrator.run_turn_stream_verified).

Pins the ratified shape: Player tokens buffer to sentence boundaries,
every released delta has passed verification scoped to the accumulated
text, the turn performs exactly ONE verifier construction (= one
retrieval), quote spans straddling a boundary hold release, a
verifier-exception chunk fails closed, and the async Coach receives the
final verified text.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from unittest.mock import MagicMock

import pytest

from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.tutoring.orchestrator import (
    OrchestratorConfigurationError,
    PlayerCoachOrchestrator,
)


def _make_streaming_player(tokens: list[str]) -> Any:
    player = MagicMock()

    async def respond_stream(
        *, session_state: Any, learner_message: str
    ) -> AsyncIterator[str]:
        for token in tokens:
            yield token

    player.respond_stream = respond_stream
    return player


def _make_orchestrator(
    tokens: list[str], verifier_factory: Any
) -> tuple[PlayerCoachOrchestrator, MagicMock]:
    orch = PlayerCoachOrchestrator(
        player=_make_streaming_player(tokens),
        coach=MagicMock(),
        turn_verifier_factory=verifier_factory,
        coach_evaluation="async",
    )
    dispatched = MagicMock()
    orch._dispatch_async_coach = dispatched  # type: ignore[method-assign]
    return orch, dispatched


async def _collect(orch: PlayerCoachOrchestrator) -> list[str]:
    deltas = []
    async for delta in orch.run_turn_stream_verified(
        session_state=MagicMock(), learner_message="tell me about ambition"
    ):
        deltas.append(delta)
    # Let the hoisted verifier thread task settle.
    await asyncio.sleep(0)
    return deltas


def _recording_identity_factory(record: dict[str, Any]) -> Any:
    def factory(learner_message: str, session_state: Any) -> Any:
        record["constructions"] = record.get("constructions", 0) + 1

        def verify(text: str) -> tuple[str, VerifierMetadata]:
            record.setdefault("calls", []).append(text)
            return text, VerifierMetadata()

        return verify

    return factory


async def test_deltas_are_sentence_bounded_and_rebuild_the_full_text() -> None:
    record: dict[str, Any] = {}
    tokens = ["A metaphor ", "compares directly. ", "A simile ", "uses like."]
    orch, dispatched = _make_orchestrator(
        tokens, _recording_identity_factory(record)
    )

    deltas = await _collect(orch)

    assert "".join(deltas) == "".join(tokens)
    # First delta released at the first sentence boundary, not per-token.
    assert deltas[0] == "A metaphor compares directly. "
    # ONE verifier construction (= one retrieval) for the whole turn.
    assert record["constructions"] == 1
    # Verified per boundary plus the final full-text pass.
    assert record["calls"][-1] == "".join(tokens)
    # The async Coach got the final verified text.
    assert dispatched.call_count == 1
    assert dispatched.call_args.kwargs["player_response"] == "".join(tokens)


async def test_verifier_rewrites_flow_into_the_released_deltas() -> None:
    tokens = ["The stage is darkk. ", "Blood imagery follows."]

    def factory(learner_message: str, session_state: Any) -> Any:
        def verify(text: str) -> tuple[str, VerifierMetadata]:
            return text.replace("darkk", "dark"), VerifierMetadata()

        return verify

    orch, _ = _make_orchestrator(tokens, factory)
    deltas = await _collect(orch)

    assert deltas[0] == "The stage is dark. "
    assert "".join(deltas) == "The stage is dark. Blood imagery follows."


async def test_open_quote_holds_release_until_the_span_closes() -> None:
    record: dict[str, Any] = {}
    tokens = ['She says "unsex me here. ', 'And fill me." ', "That is AO2."]
    orch, _ = _make_orchestrator(tokens, _recording_identity_factory(record))

    deltas = await _collect(orch)

    # Nothing released at the terminator INSIDE the quotation — the first
    # delta spans the whole closed quote (the ADR straddle guard).
    assert deltas[0] == 'She says "unsex me here. And fill me." '
    assert "".join(deltas) == "".join(tokens)


async def test_verifier_exception_fails_closed_for_the_chunk() -> None:
    calls = {"n": 0}

    def factory(learner_message: str, session_state: Any) -> Any:
        def verify(text: str) -> tuple[str, VerifierMetadata]:
            calls["n"] += 1
            if calls["n"] == 1:
                return text, VerifierMetadata(verifier_exception=True)
            return text, VerifierMetadata()

        return verify

    tokens = ["First sentence. ", "Second sentence."]
    orch, _ = _make_orchestrator(tokens, factory)
    deltas = await _collect(orch)

    # The excepted boundary released nothing; the final pass (matching
    # the batch path's absorb-and-continue contract) released the whole
    # verified text in one delta.
    assert deltas == ["First sentence. Second sentence."]


async def test_missing_factory_refuses_rather_than_degrading_to_raw() -> None:
    orch = PlayerCoachOrchestrator(
        player=_make_streaming_player(["hi."]),
        coach=MagicMock(),
        coach_evaluation="async",
    )
    stream = orch.run_turn_stream_verified(
        session_state=MagicMock(), learner_message="hi"
    )
    with pytest.raises(OrchestratorConfigurationError):
        await anext(stream)


# ---------------------------------------------------------------------------
# Track A / A2 — the FINAL pass must fail CLOSED on verifier_exception
# (Lane 2 step 3 regression pins, 2026-08-07).
#
# Observed HEAD behaviour BEFORE the fix: per-chunk verification correctly
# held release on verifier_exception, but the end-of-stream final pass did
# NOT re-check the flag. With everything held,
# verified_full[:released_verified_len] was "" and "".startswith("") is
# True, so tail = the ENTIRE raw response — the stream yielded raw
# unverified text (fail-OPEN) and SessionService.turn_stream persisted it.
# These tests assert the FIXED behaviour: on a final-pass
# verifier_exception nothing raw is ever released; the learner gets the
# already-verified prefix plus an honest fallback notice, and the async
# Coach sees exactly what was shown with the exception flag intact.
# ---------------------------------------------------------------------------


async def test_final_pass_verifier_exception_fails_closed_releases_no_raw_text() -> None:
    def factory(learner_message: str, session_state: Any) -> Any:
        def verify(text: str) -> tuple[str, VerifierMetadata]:
            return text, VerifierMetadata(verifier_exception=True)

        return verify

    tokens = ['She says "unsex me here and fill me". ', "More raw text follows."]
    orch, dispatched = _make_orchestrator(tokens, factory)

    deltas = await _collect(orch)

    from study_tutor.tutoring.orchestrator import FINAL_VERIFICATION_FALLBACK

    joined = "".join(deltas)
    # No fragment of the unverified raw response reaches the learner.
    assert "unsex me here" not in joined
    assert "More raw text" not in joined
    # The learner gets the honest fallback, alone.
    assert joined == FINAL_VERIFICATION_FALLBACK
    # The async Coach sees exactly what was shown + the exception flag.
    assert dispatched.call_count == 1
    kwargs = dispatched.call_args.kwargs
    assert kwargs["player_response"] == FINAL_VERIFICATION_FALLBACK
    assert kwargs["verifier_metadata"].verifier_exception is True


async def test_final_pass_exception_keeps_released_prefix_and_appends_fallback() -> None:
    calls = {"n": 0}

    def factory(learner_message: str, session_state: Any) -> Any:
        def verify(text: str) -> tuple[str, VerifierMetadata]:
            calls["n"] += 1
            if calls["n"] == 1:
                return text, VerifierMetadata()
            return text, VerifierMetadata(verifier_exception=True)

        return verify

    tokens = ["A metaphor compares directly. ", 'Then "a fabricated line" follows.']
    orch, dispatched = _make_orchestrator(tokens, factory)

    deltas = await _collect(orch)

    from study_tutor.tutoring.orchestrator import FINAL_VERIFICATION_FALLBACK

    # The verified first sentence was released and is never retracted.
    assert deltas[0] == "A metaphor compares directly. "
    joined = "".join(deltas)
    # The unverified tail is held back entirely.
    assert "fabricated line" not in joined
    assert joined == "A metaphor compares directly. " + FINAL_VERIFICATION_FALLBACK
    kwargs = dispatched.call_args.kwargs
    assert kwargs["player_response"] == joined
    assert kwargs["verifier_metadata"].verifier_exception is True
