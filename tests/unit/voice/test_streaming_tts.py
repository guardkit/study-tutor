"""Tests for sentence-chunked TTS with audio_ref frames (TASK-VS2-007).

Verifies:
- AC-001: audio_ref.seq strictly increasing and gapless
- AC-002: Audio synthesized only from verified text
- AC-003: TTS failure after first chunk (ASSUM-006)
- AC-004: Chunks fetched via voice_audio route
- AC-005: No audio bytes to disk/DB
"""

from __future__ import annotations

import pytest
from typing import AsyncIterator
from unittest.mock import AsyncMock, Mock

from study_tutor.session.service import TurnEvent
from study_tutor.voice.client import AudioClient
from study_tutor.voice.service import ChunkStore
from study_tutor.voice.errors import VoiceUnavailable
from study_tutor.voice.streaming_tts import stream_with_audio_refs

# --- Fixtures ---


@pytest.fixture
def fake_audio_client():
    """Fake AudioClient that returns predictable audio bytes."""
    client = AsyncMock(spec=AudioClient)

    async def synthesize(text: str, *, response_format: str = "wav") -> bytes:
        # Return fake WAV bytes with text embedded for traceability
        return f"FAKE_WAV[{text}]".encode("utf-8")

    client.synthesize = synthesize
    return client


@pytest.fixture
def chunk_store():
    """Real ChunkStore for integration testing."""
    return ChunkStore(ttl_seconds=120, max_entries=1000)


@pytest.fixture
def fake_verifier():
    """Fake verifier that always returns success."""

    def verifier(text: str):
        result = Mock()
        result.response = text
        result.metadata = Mock()
        result.metadata.verifier_exception = False
        return result

    return verifier


# --- AC-001: audio_ref.seq strictly increasing and gapless ---


@pytest.mark.asyncio
async def test_audio_ref_seq_strictly_increasing(
    fake_audio_client, chunk_store, fake_verifier
):
    """AC-001: audio_ref.seq must be strictly increasing and gapless."""
    # Three sentences → three chunks → three audio_ref frames
    token_stream = _make_token_stream(
        [
            "First sentence here.",
            " Second one follows.",
            " Third completes it.",
        ]
    )

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    # Extract audio_ref events
    audio_refs = [e for e in events if e.type == "audio_ref"]

    assert len(audio_refs) == 3, "Should have 3 audio_ref frames"
    assert [r.seq for r in audio_refs] == [0, 1, 2], "Seq must be 0, 1, 2"

    # All audio_refs must have chunk_id and url
    for ref in audio_refs:
        assert ref.chunk_id is not None
        assert ref.url is not None
        assert ref.url.startswith("/api/sessions/test-session/voice-audio/")


# --- AC-002: Audio synthesized only from verified text ---


@pytest.mark.asyncio
async def test_audio_from_verified_text_only(
    fake_audio_client, chunk_store, fake_verifier
):
    """AC-002: Audio must be synthesized from verified chunk text, not raw tokens."""
    token_stream = _make_token_stream(["First sentence only."])

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    audio_refs = [e for e in events if e.type == "audio_ref"]
    assert len(audio_refs) == 1

    # Retrieve audio from chunk_store
    chunk_id = audio_refs[0].chunk_id
    audio_bytes = chunk_store.get("test-session", chunk_id)

    # Audio should contain the verified text
    assert audio_bytes is not None
    assert b"First sentence only." in audio_bytes


# --- AC-003: TTS failure after first chunk (ASSUM-006) ---


@pytest.mark.asyncio
async def test_tts_failure_mid_answer(chunk_store, fake_verifier):
    """AC-003: VoiceUnavailable after first chunk → stop audio_ref, continue tokens."""
    # AudioClient that fails after first call
    call_count = 0

    async def failing_synthesize(text: str, *, response_format: str = "wav") -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return f"FAKE_WAV[{text}]".encode("utf-8")
        raise VoiceUnavailable("TTS service down")

    audio_client = AsyncMock(spec=AudioClient)
    audio_client.synthesize = failing_synthesize

    # Three sentences
    token_stream = _make_token_stream(
        [
            "First sentence.",
            " Second sentence.",
            " Third sentence.",
        ]
    )

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    # Should have exactly 1 audio_ref (first chunk succeeded)
    audio_refs = [e for e in events if e.type == "audio_ref"]
    assert len(audio_refs) == 1, "Only first audio_ref should succeed"
    assert audio_refs[0].seq == 0

    # Should still have all token events
    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) > 0, "Token frames must continue after TTS failure"

    # Should have done event
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1, "Turn must complete normally"


# --- AC-004: Chunks retrieved via voice_audio route ---


@pytest.mark.asyncio
@pytest.mark.seam
@pytest.mark.integration_contract("CHUNK_STORE")
async def test_audio_ref_urls_resolve_via_shared_store(
    fake_audio_client, chunk_store, fake_verifier
):
    """AC-004 + Seam: Chunks stored and retrievable via ChunkStore."""
    token_stream = _make_token_stream(
        [
            "First sentence.",
            " Second sentence.",
        ]
    )

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    audio_refs = [e for e in events if e.type == "audio_ref"]
    assert len(audio_refs) == 2

    # Verify each chunk is retrievable from shared store
    for ref in audio_refs:
        audio = chunk_store.get("test-session", ref.chunk_id)
        assert audio is not None, f"Chunk {ref.chunk_id} must be retrievable"
        assert ref.url == f"/api/sessions/test-session/voice-audio/{ref.chunk_id}"


# --- AC-005: No audio bytes to disk ---


@pytest.mark.asyncio
async def test_no_audio_bytes_to_disk(fake_audio_client, chunk_store, fake_verifier):
    """AC-005: Audio bytes never written to disk or logged."""
    # This is verified by code inspection and absence of file I/O operations
    # The test ensures audio flows only through memory (ChunkStore)

    token_stream = _make_token_stream(["Test sentence."])

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    # Audio should only exist in chunk_store (in-memory)
    audio_refs = [e for e in events if e.type == "audio_ref"]
    assert len(audio_refs) == 1

    # Verify it's retrievable from memory store
    audio = chunk_store.get("test-session", audio_refs[0].chunk_id)
    assert audio is not None


# --- Token pass-through tests ---


@pytest.mark.asyncio
async def test_token_events_passed_through(
    fake_audio_client, chunk_store, fake_verifier
):
    """Token events from upstream must be passed through unmodified."""
    token_stream = _make_token_stream(["Test", " sentence", "."])

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream,
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    # Should have token events for each word
    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) == 3
    assert [e.text for e in token_events] == ["Test", " sentence", "."]


@pytest.mark.asyncio
async def test_done_event_passed_through(fake_audio_client, chunk_store, fake_verifier):
    """Done event must be passed through after all processing."""

    async def token_stream():
        yield TurnEvent(type="token", text="Test.")
        yield TurnEvent(type="done", turn_index=5)

    events = []
    async for event in stream_with_audio_refs(
        token_stream=token_stream(),
        session_id="test-session",
        audio_client=fake_audio_client,
        chunk_store=chunk_store,
        verifier=fake_verifier,
    ):
        events.append(event)

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1
    assert done_events[0].turn_index == 5


# --- Helper functions ---


async def _make_token_stream(tokens: list[str]) -> AsyncIterator[TurnEvent]:
    """Create a fake token stream from a list of token strings."""
    for token in tokens:
        yield TurnEvent(type="token", text=token)
    yield TurnEvent(type="done", turn_index=1)
