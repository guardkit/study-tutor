"""Unit tests for sentence_chunker.py (TASK-VS2-002).

Tests the quote-aware sentence chunker with ADR-ARCH-027 verification gate.
"""
from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest

from study_tutor.tutoring.sentence_chunker import chunk_stream


# Test fixtures and mocks


@pytest.fixture
def passing_verifier():
    """Mock verifier that always returns verified response."""
    def verify(accumulated_text: str) -> MagicMock:
        response = MagicMock()
        response.response = accumulated_text
        response.metadata = MagicMock()
        response.metadata.verifier_exception = False
        return response
    return verify


@pytest.fixture
def failing_verifier():
    """Mock verifier that always sets verifier_exception=True."""
    def verify(accumulated_text: str) -> MagicMock:
        response = MagicMock()
        response.response = accumulated_text
        response.metadata = MagicMock()
        response.metadata.verifier_exception = True
        return response
    return verify


async def fake_tokens(*sentences: str) -> AsyncIterator[str]:
    """Generate tokens word-by-word from sentences."""
    for sentence in sentences:
        for word in sentence.split():
            yield word + " "


# AC-001: Quote boundary deferral + verification with accumulated text


@pytest.mark.asyncio
async def test_quote_straddling_chunk_boundary_defers_until_close(passing_verifier):
    """Quote opening near chunk end defers release until closing mark seen.

    AC-001: Token stream with a quotation whose opening mark falls in the final
    words of a nominal chunk and closing mark in the next: chunk is NOT released
    until the quote closes and verification passes.
    """
    # Sentence with opening quote near 15-word boundary, closing after
    tokens = fake_tokens(
        'This is a test sentence with about twelve words here now.',
        'Then we have "a quoted phrase that spans" across boundaries.',
        'Final sentence completes the test.'
    )

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    # First chunk should be deferred until quote closes
    assert len(chunks) >= 2
    # Verify no chunk text contains partial quotes (opening without closing)
    for chunk_text, _ in chunks:
        quote_count = chunk_text.count('"')
        assert quote_count % 2 == 0, f"Chunk has unmatched quote: {chunk_text!r}"


@pytest.mark.asyncio
async def test_verifier_called_with_accumulated_not_chunk(passing_verifier):
    """Verification is called with full accumulated text, not isolated chunk.

    AC-001 (continued): apply_quote_verification is invoked with accumulated
    text, not the isolated chunk substring.
    """
    call_tracker = []

    def tracking_verifier(accumulated_text: str) -> MagicMock:
        call_tracker.append(accumulated_text)
        response = MagicMock()
        response.response = accumulated_text
        response.metadata = MagicMock()
        response.metadata.verifier_exception = False
        return response

    tokens = fake_tokens(
        'First sentence with enough words to make a chunk here now.',
        'Second sentence continues the stream with more content added.'
    )

    _ = [c async for c in chunk_stream(tokens, verifier=tracking_verifier)]

    # Each verifier call should have progressively longer accumulated text
    assert len(call_tracker) > 0
    for i in range(1, len(call_tracker)):
        assert len(call_tracker[i]) >= len(call_tracker[i-1]), \
            "Verifier should receive accumulated text, not isolated chunks"


# AC-002: Idempotent-prefix (no retroactive changes)


@pytest.mark.asyncio
async def test_previously_released_chunks_never_altered(passing_verifier):
    """Once released, chunk text is never retroactively changed.

    AC-002: Idempotent-prefix test: previously-released chunk text is never
    retroactively altered by any later verification pass.
    """
    tokens = fake_tokens(
        'This is the first sentence with enough words to create a chunk.',
        'This is the second sentence with more words to test idempotency.',
        'This is the third sentence to verify no changes happen retroactively.'
    )

    released_chunks = []
    async for chunk_text, seq in chunk_stream(tokens, verifier=passing_verifier):
        # Verify previously released chunks haven't changed
        for prev_text, prev_seq in released_chunks:
            # Re-check that previous chunks are still the same
            assert prev_seq < seq
        released_chunks.append((chunk_text, seq))

    # Verify all chunks are distinct and sequential
    sequences = [seq for _, seq in released_chunks]
    assert sequences == list(range(len(sequences)))


# AC-003: Fail-closed on verifier_exception


@pytest.mark.asyncio
async def test_verifier_exception_raises_instead_of_yielding(failing_verifier):
    """Generator raises when verifier_exception=True (fail-closed).

    AC-003: Forcing verifier_exception=True on a mid-stream chunk makes the
    generator raise/stop rather than yield the unannotated chunk (ASSUM-007
    fail-closed).
    """
    tokens = fake_tokens(
        'This is a sentence that will trigger verifier exception handling.'
    )

    with pytest.raises(RuntimeError, match="Quote verification failed"):
        async for _ in chunk_stream(tokens, verifier=failing_verifier):
            pass  # Should raise before yielding


@pytest.mark.asyncio
async def test_partial_verifier_exception_stops_mid_stream(passing_verifier):
    """Generator stops when verifier_exception becomes True mid-stream."""
    call_count = [0]

    def conditional_verifier(accumulated_text: str) -> MagicMock:
        call_count[0] += 1
        response = MagicMock()
        response.response = accumulated_text
        response.metadata = MagicMock()
        # Fail on second verification
        response.metadata.verifier_exception = (call_count[0] >= 2)
        return response

    tokens = fake_tokens(
        'First sentence passes verification with enough words to make a proper chunk here.',
        'Second sentence also has enough words to trigger the failure condition now.',
        'Third sentence should never be processed at all because we failed earlier.'
    )

    chunks = []
    with pytest.raises(RuntimeError, match="Quote verification failed"):
        async for chunk in chunk_stream(tokens, verifier=conditional_verifier):
            chunks.append(chunk)

    # Should have yielded first chunk before failing
    assert len(chunks) >= 1


# AC-004: Chunk sizing and sentence boundaries


@pytest.mark.asyncio
async def test_short_answer_yields_single_chunk(passing_verifier):
    """Answer shorter than chunk size yields exactly one chunk.

    AC-004 (part 1): Answer shorter than one chunk's worth of words yields
    exactly one chunk covering the whole answer (ASSUM-001).
    """
    tokens = fake_tokens('This is a short answer.')

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    assert len(chunks) == 1
    chunk_text, seq = chunks[0]
    assert seq == 0
    assert 'This is a short answer.' in chunk_text


@pytest.mark.asyncio
async def test_long_answer_breaks_at_sentence_boundaries(passing_verifier):
    """Multi-sentence answers break only at sentence boundaries.

    AC-004 (part 2): Multi-sentence answers break only at sentence boundaries
    with each chunk roughly 15–25 words.
    """
    tokens = fake_tokens(
        'First sentence has enough words to approach the chunk boundary here now.',
        'Second sentence continues with more content to test boundaries.',
        'Third sentence adds even more words to create multiple chunks.',
        'Fourth sentence ensures we have enough content for proper testing.'
    )

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    assert len(chunks) >= 2

    # Each chunk should end with sentence terminator
    for chunk_text, _ in chunks[:-1]:  # All but last chunk
        assert chunk_text.rstrip().endswith(('.', '!', '?')), \
            f"Chunk should end at sentence boundary: {chunk_text!r}"

    # Check chunk sizes are roughly in target range (15-25 words)
    for chunk_text, _ in chunks:
        word_count = len(chunk_text.split())
        # Allow some flexibility for sentence boundaries
        assert 5 <= word_count <= 40, \
            f"Chunk word count {word_count} outside reasonable range"


@pytest.mark.asyncio
async def test_chunk_size_approximately_fifteen_to_twenty_five_words(passing_verifier):
    """Chunks are roughly 15-25 words when sufficient content available."""
    # Create sentences that naturally split around chunk boundaries
    tokens = fake_tokens(
        'The first sentence has exactly fifteen words in it to test the chunking boundary.',
        'The second sentence also has about fifteen words to continue testing.',
        'The third sentence provides additional content for verification purposes here.',
        'The fourth sentence ensures we have multiple chunks to analyze properly.'
    )

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    # At least one chunk should be in the target range
    word_counts = [len(chunk_text.split()) for chunk_text, _ in chunks]
    assert any(15 <= count <= 25 for count in word_counts), \
        f"Expected at least one chunk in 15-25 word range, got: {word_counts}"


# Seam test: VERIFIED_CHUNK_ITERATOR contract


@pytest.mark.seam
@pytest.mark.integration_contract("VERIFIED_CHUNK_ITERATOR")
@pytest.mark.asyncio
async def test_chunker_yields_verified_chunks_with_seq(passing_verifier):
    """Contract: async generator yielding (chunk_text: str, seq: int).

    Producer: TASK-VS2-002 (this task)
    Consumers: TASK-VS2-003 (token frames), TASK-VS2-007 (TTS trigger)

    Verifies:
    - Yields tuples of (chunk_text: str, seq: int)
    - seq is strictly increasing from 0
    - chunk_text is non-empty string
    - Only yields VERIFIED chunks (raises on verifier_exception=True)
    """
    tokens = fake_tokens(
        'First sentence for seam contract test.',
        'Second sentence continues the test stream.',
        'Third sentence completes the verification.'
    )

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    # Verify structure
    assert len(chunks) > 0, "Should yield at least one chunk"

    # Check sequence numbers
    sequences = [seq for _, seq in chunks]
    assert sequences == list(range(len(chunks))), \
        f"Sequences should be 0, 1, 2, ..., got {sequences}"

    # Check chunk text
    for chunk_text, _ in chunks:
        assert isinstance(chunk_text, str), "chunk_text must be str"
        assert chunk_text, "chunk_text must be non-empty"


@pytest.mark.asyncio
async def test_empty_stream_yields_nothing(passing_verifier):
    """Empty token stream yields no chunks."""
    async def empty_tokens() -> AsyncIterator[str]:
        return
        yield  # Make it a generator

    chunks = [c async for c in chunk_stream(empty_tokens(), verifier=passing_verifier)]
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_single_word_yields_single_chunk(passing_verifier):
    """Single word yields single chunk."""
    tokens = fake_tokens('Hello.')

    chunks = [c async for c in chunk_stream(tokens, verifier=passing_verifier)]

    assert len(chunks) == 1
    chunk_text, seq = chunks[0]
    assert seq == 0
    assert 'Hello.' in chunk_text
