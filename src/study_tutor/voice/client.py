"""Audio client for speech-to-text and text-to-speech (TASK-VOX-002).

Provider-agnostic OpenAI-audio client with injectable transport for testing.
No framework coupling, no disk I/O — pure bytes in, bytes out.
"""

from __future__ import annotations

import httpx

from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import VoiceUnavailable


class AudioClient:
    """Client for audio transcription and synthesis.

    Fresh httpx.AsyncClient per call with timeout from config.
    All httpx exceptions collapse to VoiceUnavailable.

    Args:
        config: Voice service configuration.
        transport: Optional httpx transport for testing (injectable test seam).

    Examples:
        >>> config = VoiceConfig.from_env(enabled="true")
        >>> client = AudioClient(config)
        >>> text = await client.transcribe(audio_bytes, filename="q.wav", content_type="audio/wav")
        >>> audio = await client.synthesize("Hello world")
    """

    def __init__(
        self,
        config: VoiceConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Initialize AudioClient with config and optional transport.

        Args:
            config: Voice service configuration.
            transport: Optional httpx transport for testing.
        """
        self._config = config
        self._transport = transport

    async def transcribe(
        self, audio: bytes, *, filename: str, content_type: str
    ) -> str:
        """Transcribe audio to text via speech-to-text service.

        Args:
            audio: Raw audio bytes.
            filename: Filename for multipart form (e.g., "query.ogg").
            content_type: Full content-type with codec params (e.g., "audio/ogg;codecs=opus").

        Returns:
            Transcribed text (may be empty or whitespace-only).

        Raises:
            VoiceUnavailable: On HTTP errors, timeouts, or network failures.

        Examples:
            >>> text = await client.transcribe(b"...", filename="q.ogg", content_type="audio/ogg;codecs=opus")
        """
        url = f"{self._config.stt_base_url}/audio/transcriptions"

        # Multipart form data: file field with (filename, bytes, content-type) + model field
        files = {"file": (filename, audio, content_type)}
        data = {"model": self._config.stt_model}

        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(self._config.audio_timeout_seconds),
            ) as client:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()
                return response.json()["text"]
        except (
            httpx.HTTPStatusError,
            httpx.RequestError,
            httpx.TimeoutException,
        ) as exc:
            raise VoiceUnavailable(
                f"Speech-to-text service unavailable: {type(exc).__name__}"
            ) from exc

    async def synthesize(
        self, text: str, *, response_format: str = "wav"
    ) -> bytes:
        """Synthesize text to audio via text-to-speech service.

        Args:
            text: Text to synthesize.
            response_format: Audio format (e.g., "wav", "mp3"). Defaults to "wav".

        Returns:
            Raw audio bytes.

        Raises:
            VoiceUnavailable: On HTTP errors, timeouts, or network failures.

        Examples:
            >>> audio = await client.synthesize("Hello world")
            >>> audio_mp3 = await client.synthesize("Hello", response_format="mp3")
        """
        url = f"{self._config.tts_base_url}/audio/speech"

        # JSON body with model, voice, input, response_format
        payload = {
            "model": self._config.tts_model,
            "voice": self._config.tts_voice,
            "input": text,
            "response_format": response_format,
        }

        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(self._config.audio_timeout_seconds),
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.content
        except (
            httpx.HTTPStatusError,
            httpx.RequestError,
            httpx.TimeoutException,
        ) as exc:
            raise VoiceUnavailable(
                f"Text-to-speech service unavailable: {type(exc).__name__}"
            ) from exc
