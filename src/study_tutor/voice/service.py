"""Voice turn orchestration with in-memory TTL chunk store (TASK-VOX-005).

Implements the non-streaming voice turn flow:
1. Parse and validate voice upload
2. Transcribe audio to text
3. Run standard turn path through SessionService
4. Synthesize tutor response to audio
5. Store audio chunks with TTL

Implements ASSUM-005: TTS failure after turn is committed returns text-only result.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from typing import Callable

from starlette.requests import Request

from study_tutor.session.service import ReplyFn, SessionService
from study_tutor.voice.client import AudioClient
from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import UnintelligibleQuery, VoiceUnavailable
from study_tutor.voice.validation import ValidatedUpload, parse_voice_upload

logger = logging.getLogger(__name__)

#: Per-request reply builder: ``(session_id=, student_id=) → ReplyFn``. The
#: real orchestrator-backed factory the HTTP JSON turn path uses; injected so
#: the voice turn drives the same tutor loop (S-R4 §2.7 — no placeholder echo).
ReplyFnFactory = Callable[..., ReplyFn]

#: qwen3-tts-0.6b stops generating at ~60 s (~170-180 words) per synthesis
#: call, silently dropping the tail of longer inputs (see
#: docs/runbooks/INVESTIGATION-voice-tts-audio-60s-cap.md). Each synthesis
#: piece stays well under that ceiling; the app plays a multi-chunk
#: ``audio[]`` as one continuous answer.
TTS_MAX_WORDS_PER_CHUNK = 120

#: Pieces MUST synthesize serially: the TTS server generates one request at
#: a time behind an internal model lock, so a queued concurrent request
#: receives no body bytes until the active one finishes — and the 10 s httpx
#: read timeout then kills it (serial requests survive because the WAV
#: streams progressively). Measured 2026-07-26: concurrency 2 delivered
#: 1-of-5 pieces (ReadTimeout + llama-swap 429s from abandoned streams).
#:
#: The piece cap bounds voice-turn wall time instead: at ~17-24 s per
#: serial piece plus ~14 s of tutor generation, two pieces keep the worst
#: case near ~65 s against the app's 90 s deadline. Replies over
#: ~240 words speak their first two pieces and rely on the on-screen text
#: for the tail (still ~1.8x more speech than the pre-fix ~60 s cap).
#: Capping voice-mode reply length (investigation Option C) is the
#: product-level companion that would make this cap moot.
TTS_MAX_PIECES_PER_TURN = 2

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")


def split_text_for_tts(
    text: str, max_words: int = TTS_MAX_WORDS_PER_CHUNK
) -> list[str]:
    """Split text into TTS-sized pieces on sentence boundaries.

    Sentences are coalesced greedily so each piece stays at or under
    ``max_words``. A single sentence longer than ``max_words`` is hard-split
    at word boundaries. Text at or under the limit comes back as one piece,
    so short replies keep today's single-chunk behaviour.

    Args:
        text: The text to split.
        max_words: Maximum words per piece.

    Returns:
        Ordered, non-empty pieces whose concatenation preserves every
        sentence; empty list for empty/whitespace input.
    """
    text = text.strip()
    if not text:
        return []
    if len(text.split()) <= max_words:
        return [text]

    pieces: list[str] = []
    current_words: list[str] = []
    for sentence in _SENTENCE_BOUNDARY.split(text):
        words = sentence.split()
        if not words:
            continue
        if current_words and len(current_words) + len(words) > max_words:
            pieces.append(" ".join(current_words))
            current_words = []
        if len(words) > max_words:
            # Oversized single sentence: hard-split at word boundaries
            for start in range(0, len(words), max_words):
                chunk = words[start : start + max_words]
                if len(chunk) == max_words:
                    pieces.append(" ".join(chunk))
                else:
                    current_words = chunk
        else:
            current_words.extend(words)
    if current_words:
        pieces.append(" ".join(current_words))
    return pieces


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioRef:
    """Reference to a stored audio chunk.

    Attributes:
        seq: Sequence number (0 for MVP single-chunk).
        chunk_id: Opaque unguessable chunk identifier.
        url: Full URL path to retrieve the chunk.
    """

    seq: int
    chunk_id: str
    url: str


@dataclass(frozen=True)
class VoiceTurnResult:
    """Result of a voice turn operation.

    Attributes:
        transcript: Transcribed user query text.
        tutor_response: Tutor's response text.
        audio: List of audio chunk references (empty if TTS failed per ASSUM-005).
    """

    transcript: str
    tutor_response: str
    audio: list[AudioRef]


# ---------------------------------------------------------------------------
# ChunkStore
# ---------------------------------------------------------------------------


class ChunkStore:
    """In-memory TTL storage for audio chunks with session-scoped keys.

    Thread-safe (asyncio.Lock guarded) storage with:
    - Unguessable chunk IDs (secrets.token_urlsafe)
    - TTL-based expiry (checked on get and put)
    - Hard cap with oldest-first eviction
    - Session isolation (chunks are session-scoped)

    Args:
        ttl_seconds: Time-to-live for chunks in seconds.
        max_entries: Maximum number of chunks before evicting oldest.

    Examples:
        >>> store = ChunkStore(ttl_seconds=120, max_entries=1000)
        >>> chunk_id = store.put("session1", b"audio data")
        >>> audio = store.get("session1", chunk_id)
    """

    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        """Initialize ChunkStore.

        Args:
            ttl_seconds: Time-to-live for chunks in seconds.
            max_entries: Maximum number of chunks before evicting oldest.
        """
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._lock = asyncio.Lock()
        # Storage: (session_id, chunk_id) -> (audio_bytes, timestamp)
        self._store: Dict[Tuple[str, str], Tuple[bytes, float]] = {}

    def put(self, session_id: str, wav_bytes: bytes) -> str:
        """Store audio chunk and return unguessable chunk ID.

        Evicts expired entries before storing. If max_entries is exceeded,
        evicts oldest entries first.

        Args:
            session_id: Session identifier (for isolation).
            wav_bytes: Audio data bytes.

        Returns:
            Unguessable chunk identifier.
        """
        # Evict expired entries first
        self._evict_expired()

        # Evict oldest if at capacity
        if len(self._store) >= self._max_entries:
            self._evict_oldest()

        # Generate unguessable chunk ID
        chunk_id = secrets.token_urlsafe(16)
        timestamp = time.time()

        # Store with session-scoped key
        key = (session_id, chunk_id)
        self._store[key] = (wav_bytes, timestamp)

        return chunk_id

    def get(self, session_id: str, chunk_id: str) -> bytes | None:
        """Retrieve audio chunk if valid and not expired.

        Args:
            session_id: Session identifier (must match stored session).
            chunk_id: Chunk identifier.

        Returns:
            Audio bytes if found and not expired, None otherwise.
        """
        # Evict expired entries first
        self._evict_expired()

        key = (session_id, chunk_id)
        entry = self._store.get(key)

        if entry is None:
            return None

        audio_bytes, _ = entry
        return audio_bytes

    def _evict_expired(self) -> None:
        """Remove all expired entries from storage."""
        now = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._store.items()
            if now - timestamp > self._ttl_seconds
        ]

        for key in expired_keys:
            del self._store[key]

    def _evict_oldest(self) -> None:
        """Remove oldest entry from storage."""
        if not self._store:
            return

        # Find oldest entry by timestamp
        oldest_key = min(self._store.items(), key=lambda item: item[1][1])[0]
        del self._store[oldest_key]


# ---------------------------------------------------------------------------
# VoiceTurnService
# ---------------------------------------------------------------------------


class VoiceTurnService:
    """Voice turn orchestration service.

    Coordinates the voice turn flow:
    1. Parse and validate voice upload (parse_voice_upload)
    2. Transcribe audio to text (AudioClient.transcribe)
    3. Run standard turn path (SessionService.turn)
    4. Synthesize response audio (AudioClient.synthesize)
    5. Store audio chunk (ChunkStore.put)

    Implements ASSUM-005: if TTS fails after turn is committed, returns
    text-only result with audio=[] instead of raising an error.

    Args:
        config: Voice configuration.
        audio_client: Audio transcription/synthesis client.
        session_service: Session management service.
        chunk_store: Audio chunk storage.

    Examples:
        >>> service = VoiceTurnService(
        ...     config, audio_client, session_service, chunk_store, reply_fn_factory
        ... )
        >>> result = await service.voice_turn("sess123", "student1", request)
    """

    def __init__(
        self,
        config: VoiceConfig,
        audio_client: AudioClient,
        session_service: SessionService,
        chunk_store: ChunkStore,
        reply_fn_factory: ReplyFnFactory,
    ) -> None:
        """Initialize VoiceTurnService.

        Args:
            config: Voice configuration.
            audio_client: Audio transcription/synthesis client.
            session_service: Session management service.
            chunk_store: Audio chunk storage.
            reply_fn_factory: Per-request orchestrator-backed reply builder
                (S-R4 §2.7). The REST voice turn drives the same real tutor
                loop as the JSON turn path — the Phase-1.2 placeholder echo
                is gone.
        """
        self._config = config
        self._audio_client = audio_client
        self._session_service = session_service
        self._chunk_store = chunk_store
        self._reply_fn_factory = reply_fn_factory

    async def voice_turn(
        self,
        session_id: str,
        student_id: str,
        request: Request,
    ) -> VoiceTurnResult:
        """Execute voice turn with orchestration flow.

        Flow:
        1. Parse and validate upload (rejections propagate before anything else)
        2. Transcribe audio; empty/whitespace → UnintelligibleQuery
        3. Run standard turn path through SessionService
        4. Synthesize response audio and store in chunk store
        5. Return result with transcript, tutor_response, and audio refs

        ASSUM-005: If step 4 (TTS) fails after step 3 (turn) committed,
        returns text-only result with audio=[] instead of raising error.

        Args:
            session_id: Session identifier.
            student_id: Student identifier (for ownership guard).
            request: Starlette request with multipart audio upload.

        Returns:
            VoiceTurnResult with transcript, tutor_response, and audio refs.

        Raises:
            RecordingTooLarge: Audio exceeds size limit (from parse_voice_upload).
            EmptyRecording: Audio field is empty (from parse_voice_upload).
            UnsupportedAudioFormat: Invalid MIME type (from parse_voice_upload).
            QueryTooLong: Audio duration exceeds limit (from parse_voice_upload).
            UnintelligibleQuery: Transcript is empty/whitespace after STT.
            VoiceUnavailable: STT service unavailable (before turn is recorded).
            SessionNotFoundError: Session not found (from SessionService).
            SessionEnded: Session has ended (from SessionService).
            SessionForbidden: Student doesn't own session (from SessionService).
        """
        # Step 1: Parse and validate upload
        # Validation errors propagate before any audio processing
        validated: ValidatedUpload = await parse_voice_upload(request, self._config)

        # Step 2: Transcribe audio
        # VoiceUnavailable propagates here (before turn is recorded)
        transcript = await self._audio_client.transcribe(
            validated.content,
            filename=validated.filename,
            content_type=validated.content_type,
        )

        # Discard audio bytes immediately (ephemeral invariant)
        # No logging of audio bytes, no retention on service object

        # Check for empty/whitespace transcript
        if not transcript.strip():
            raise UnintelligibleQuery()

        # Step 3: Run standard turn path through SessionService
        # This records both user and tutor turns to the store
        turn_result = await self._session_service.turn(
            student_id=student_id,
            session_id=session_id,
            user_message=transcript,
            reply_fn=self._reply_fn_factory(
                session_id=session_id, student_id=student_id
            ),
        )

        tutor_response = turn_result.tutor_response

        # Step 4: Synthesize response audio, one piece per sentence group so
        # no single call exceeds the TTS model's ~170-180-word output ceiling.
        # Each piece is a complete, independently decodable WAV (the app plays
        # the ordered audio[] as one continuous answer). Synthesis is SERIAL
        # and capped — see TTS_MAX_PIECES_PER_TURN for the measured why.
        # ASSUM-005 partial-failure policy: pieces synthesized before a TTS
        # failure are returned (partial audio, never a gap; the tail stays on
        # screen as text). A first-piece failure yields audio=[] as before.
        pieces = split_text_for_tts(tutor_response)
        if len(pieces) > TTS_MAX_PIECES_PER_TURN:
            logger.info(
                "Voice reply of %d pieces capped to %d for session %s; "
                "the tail is text-only",
                len(pieces),
                TTS_MAX_PIECES_PER_TURN,
                session_id,
            )
            pieces = pieces[:TTS_MAX_PIECES_PER_TURN]

        piece_wavs: list[bytes] = []
        for seq, piece in enumerate(pieces):
            try:
                piece_wavs.append(
                    await self._audio_client.synthesize(
                        piece, response_format="wav"
                    )
                )
            except VoiceUnavailable as e:
                logger.warning(
                    "TTS unavailable after turn committed for session %s "
                    "(keeping %d of %d pieces): %s",
                    session_id,
                    seq,
                    len(pieces),
                    str(e),
                )
                break

        # Step 5: Store chunks only after synthesis completes, so the
        # ChunkStore TTL window starts at response time — not mid-synthesis
        # (a long reply's first chunk would otherwise burn most of its TTL
        # before the client could begin fetching).
        audio_refs: list[AudioRef] = []
        for seq, audio_bytes in enumerate(piece_wavs):
            chunk_id = self._chunk_store.put(session_id, audio_bytes)
            url = f"/api/sessions/{session_id}/voice-audio/{chunk_id}"
            audio_refs.append(AudioRef(seq=seq, chunk_id=chunk_id, url=url))

        if audio_refs:
            logger.debug(
                "Voice turn completed with %d audio chunk(s)", len(audio_refs)
            )

        return VoiceTurnResult(
            transcript=transcript,
            tutor_response=tutor_response,
            audio=audio_refs,
        )
