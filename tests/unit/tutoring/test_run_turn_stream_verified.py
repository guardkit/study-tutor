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
