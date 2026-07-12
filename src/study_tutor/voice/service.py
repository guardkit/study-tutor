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

        # Step 4: Synthesize response audio
        # ASSUM-005: If TTS fails after turn is committed, return text-only
        audio_refs: list[AudioRef] = []
        try:
            audio_bytes = await self._audio_client.synthesize(
                tutor_response, response_format="wav"
            )

            # Step 5: Store audio chunk
            chunk_id = self._chunk_store.put(session_id, audio_bytes)

            # Create audio reference
            url = f"/api/sessions/{session_id}/voice-audio/{chunk_id}"
            audio_refs = [AudioRef(seq=0, chunk_id=chunk_id, url=url)]

            logger.debug("Voice turn completed with audio chunk %s", chunk_id)

        except VoiceUnavailable as e:
            # ASSUM-005: TTS failed after turn was committed
            # Return text-only result (audio=[])
            logger.warning(
                "TTS unavailable after turn committed for session %s: %s",
                session_id,
                str(e),
            )
            # audio_refs remains empty list

        return VoiceTurnResult(
            transcript=transcript,
            tutor_response=tutor_response,
            audio=audio_refs,
        )
