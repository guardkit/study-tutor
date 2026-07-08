"""Quote-aware sentence chunker with ADR-ARCH-027 verification gate.

TASK-VS2-002: Implements the sentence-chunk buffer design §5.3 pin (~15–25 words,
breaks only at sentence boundaries) with fail-closed quote verification.

Contract: VERIFIED_CHUNK_ITERATOR
  Producer: TASK-VS2-002 (this module)
  Consumers: TASK-VS2-003 (token frames), TASK-VS2-007 (TTS trigger)
  Interface: async generator yielding (chunk_text: str, seq: int)
"""
from __future__ import annotations

from typing import AsyncIterator, Callable, Any


# Chunk size parameters (design §5.3)
MIN_CHUNK_WORDS = 15
MAX_CHUNK_WORDS = 25
TARGET_CHUNK_WORDS = 20

# Sentence boundary detection
SENTENCE_TERMINATORS = '.!?'


async def chunk_stream(
    tokens: AsyncIterator[str],
    verifier: Callable[[str], Any],
) -> AsyncIterator[tuple[str, int]]:
    """Chunk token stream at sentence boundaries with quote-aware verification.

    Args:
        tokens: Async iterator yielding word tokens (with trailing spaces)
        verifier: Callable that accepts accumulated text and returns response
                  object with .response and .metadata.verifier_exception

    Yields:
        Tuples of (chunk_text: str, seq: int) for each verified chunk

    Raises:
        RuntimeError: If verifier_exception=True (ASSUM-007 fail-closed)

    Invariants:
        - Chunks break only at sentence boundaries
        - Chunk boundaries deferred past target size if quote is open
        - Verifier called with full accumulated text, not isolated chunk
        - Previously released chunks never retroactively altered
        - Sequence numbers strictly increasing from 0
    """
    accumulated_text = ""
    last_released_pos = 0
    chunk_seq = 0
    buffer_words = []
    buffer_text = ""

    async for token in tokens:
        accumulated_text += token
        buffer_text += token
        buffer_words.append(token)

        # Check if we've hit a sentence boundary
        stripped = buffer_text.rstrip()
        if not stripped or stripped[-1] not in SENTENCE_TERMINATORS:
            continue

        # Check if we have enough words for a chunk
        word_count = len(buffer_words)
        if word_count < MIN_CHUNK_WORDS:
            continue

        # Check if quote is open (odd number of quote marks in buffer)
        quote_count = buffer_text.count('"') + buffer_text.count("'")
        if quote_count % 2 != 0:
            # Quote is open - defer chunk boundary
            continue

        # We have a candidate chunk at sentence boundary with closed quotes
        # Verify the accumulated text (not just the chunk)
        verification_result = verifier(accumulated_text)

        # Check for verifier exception (ASSUM-007 fail-closed)
        if verification_result.metadata.verifier_exception:
            raise RuntimeError(
                "Quote verification failed: verifier_exception=True on chunk "
                f"{chunk_seq} at position {len(accumulated_text)}"
            )

        # Extract the newly verified chunk (from last release to current position)
        verified_chunk = accumulated_text[last_released_pos:].rstrip()

        # Release the verified chunk
        yield (verified_chunk, chunk_seq)

        # Update state for next chunk
        chunk_seq += 1
        last_released_pos = len(accumulated_text)
        buffer_words = []
        buffer_text = ""

    # Handle remaining buffer as final chunk
    if buffer_text.strip():
        # Verify final accumulated text
        verification_result = verifier(accumulated_text)

        if verification_result.metadata.verifier_exception:
            raise RuntimeError(
                f"Quote verification failed on final chunk {chunk_seq}: "
                "verifier_exception=True"
            )

        # Release final chunk
        final_chunk = accumulated_text[last_released_pos:].rstrip()
        if final_chunk:
            yield (final_chunk, chunk_seq)
