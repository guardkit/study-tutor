"""Voice service exception hierarchy (TASK-VOX-001).

Exception classes for voice feature error handling. These are plain Python
exceptions that do NOT inherit from HTTP exception types; status code mapping
happens per-handler in TASK-VOX-006.

Class names ARE the wire ``error_type`` values (contract §9 Rev 1).
"""

from __future__ import annotations


class VoiceError(Exception):
    """Base exception for all voice-related errors."""

    pass


class RecordingTooLarge(VoiceError):
    """Recording exceeds maximum allowed bytes.

    Args:
        max_bytes: Maximum allowed recording size in bytes.
    """

    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        super().__init__(
            f"Recording exceeds maximum size of {max_bytes} bytes "
            f"({max_bytes / (1024 * 1024):.1f}MB)"
        )


class QueryTooLong(VoiceError):
    """Query exceeds maximum allowed duration.

    Args:
        max_seconds: Maximum allowed query duration in seconds.
    """

    def __init__(self, max_seconds: int):
        self.max_seconds = max_seconds
        super().__init__(
            f"Query exceeds maximum duration of {max_seconds} seconds"
        )


class UnsupportedAudioFormat(VoiceError):
    """Audio format is not supported.

    Args:
        received_mimetype: The MIME type that was received.
        supported: Set of supported MIME types.
    """

    def __init__(self, received_mimetype: str, supported: set[str]):
        self.received_mimetype = received_mimetype
        self.supported = supported
        # Sort supported types for consistent error messages
        supported_sorted = sorted(supported)
        super().__init__(
            f"Unsupported audio format '{received_mimetype}'. "
            f"Supported formats: {', '.join(supported_sorted)}"
        )


class EmptyRecording(VoiceError):
    """Recording contains no audio data."""

    def __init__(self):
        super().__init__("Recording is empty or contains no audio data")


class UnintelligibleQuery(VoiceError):
    """Speech-to-text service could not transcribe the audio."""

    def __init__(self):
        super().__init__(
            "Could not understand the query. Please speak clearly and try again"
        )


class VoiceUnavailable(VoiceError):
    """Voice services are temporarily unavailable.

    Args:
        message: Optional custom message. Defaults to generic unavailability message.
    """

    def __init__(self, message: str = "Voice services are temporarily unavailable"):
        self.message = message
        super().__init__(message)
