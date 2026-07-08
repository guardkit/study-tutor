"""Voice service configuration (TASK-VOX-001).

Boot-time snapshot configuration for voice feature, loaded from environment.
Mirrors HTTPAuthConfig pattern (src/study_tutor/http/auth.py).

No import-time environment access (SR-03 discipline).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceConfig:
    """Voice service configuration loaded from environment.

    Attributes:
        enabled: Whether voice features are enabled.
        stt_base_url: Speech-to-text service base URL.
        stt_model: Speech-to-text model name.
        tts_base_url: Text-to-speech service base URL.
        tts_model: Text-to-speech model name.
        tts_voice: Text-to-speech voice name.
        audio_timeout_seconds: Timeout for audio processing operations.
        max_query_seconds: Maximum allowed query duration.
        max_recording_bytes: Maximum allowed recording size in bytes.
        chunk_ttl_seconds: Time-to-live for audio chunks in seconds.
        supported_base_mimetypes: Set of supported audio MIME types.
    """

    enabled: bool
    stt_base_url: str
    stt_model: str
    tts_base_url: str
    tts_model: str
    tts_voice: str
    audio_timeout_seconds: float
    max_query_seconds: int
    max_recording_bytes: int
    chunk_ttl_seconds: int
    supported_base_mimetypes: set[str]

    @classmethod
    def from_env(
        cls,
        enabled: str = "",
        stt_base_url: str = "",
        stt_model: str = "",
        tts_base_url: str = "",
        tts_model: str = "",
        tts_voice: str = "",
    ) -> VoiceConfig:
        """Parse voice config from environment variables.

        Args:
            enabled: STUDY_TUTOR_VOICE_ENABLED flag string ("true"/"false"/"1"/"0" etc).
            stt_base_url: STT_BASE_URL service URL.
            stt_model: STT_MODEL model name.
            tts_base_url: TTS_BASE_URL service URL.
            tts_model: TTS_MODEL model name.
            tts_voice: TTS_VOICE voice name.

        Returns:
            Parsed VoiceConfig with defaults applied.

        Raises:
            ValueError: On malformed boolean flag with clear error message.

        Examples:
            >>> config = VoiceConfig.from_env(enabled="true")
            >>> config.enabled
            True
            >>> config.stt_base_url
            'http://promaxgb10-41b1:9000/v1'
        """
        # Parse enabled flag with clear error on malformed input
        try:
            enabled_bool = _parse_bool_flag(enabled)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse STUDY_TUTOR_VOICE_ENABLED: {e}"
            ) from e

        # Apply defaults for optional fields
        return cls(
            enabled=enabled_bool,
            stt_base_url=stt_base_url or "http://promaxgb10-41b1:9000/v1",
            stt_model=stt_model or "parakeet-tdt",
            tts_base_url=tts_base_url or "http://promaxgb10-41b1:9000/v1",
            tts_model=tts_model or "qwen3-tts",
            tts_voice=tts_voice or "Ryan",
            # Constants (spec ASSUM-006, contract §5 Rev 1, spec ASSUM-004, spec ASSUM-003)
            audio_timeout_seconds=10.0,
            max_query_seconds=60,
            max_recording_bytes=10 * 1024 * 1024,
            chunk_ttl_seconds=120,
            supported_base_mimetypes={
                "audio/mp4",
                "audio/m4a",
                "audio/aac",
                "audio/ogg",
                "audio/webm",
                "audio/wav",
                "audio/mpeg",
            },
        )


def _parse_bool_flag(value: str) -> bool:
    """Parse a boolean flag from string.

    Args:
        value: String value ("true", "false", "1", "0", "yes", "no", etc).

    Returns:
        Boolean interpretation.

    Raises:
        ValueError: If value is an invalid boolean string (not empty, not recognized).

    Examples:
        >>> _parse_bool_flag("true")
        True
        >>> _parse_bool_flag("false")
        False
        >>> _parse_bool_flag("")
        False
    """
    if not value:
        return False

    normalized = value.lower().strip()

    # Check for recognized true values
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True

    # Check for recognized false values
    if normalized in {"false", "0", "no", "n", "off"}:
        return False

    # Value is not empty but not recognized - this is an error
    raise ValueError(
        f"Invalid boolean value '{value}'. "
        f"Expected one of: true, false, 1, 0, yes, no, y, n, on, off (case-insensitive)"
    )
