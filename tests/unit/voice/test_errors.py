"""Unit tests for voice errors (TASK-VOX-001).

Tests exception hierarchy, constructor signatures, and error messages.
Verifies that exception classes don't subclass HTTP exception types.
"""

from __future__ import annotations

import pytest

from study_tutor.voice.errors import (
    EmptyRecording,
    QueryTooLong,
    RecordingTooLarge,
    UnintelligibleQuery,
    UnsupportedAudioFormat,
    VoiceError,
    VoiceUnavailable,
)


# AC-003: Six exception classes exist with constructors/messages
def test_voice_error_is_base_exception():
    """VoiceError is the base exception class."""
    exc = VoiceError("test message")
    assert isinstance(exc, Exception)
    assert str(exc) == "test message"


def test_recording_too_large_constructor_and_message():
    """RecordingTooLarge accepts max_bytes and includes it in message."""
    max_bytes = 10 * 1024 * 1024  # 10MB
    exc = RecordingTooLarge(max_bytes)

    assert isinstance(exc, VoiceError)
    assert exc.max_bytes == max_bytes
    assert str(max_bytes) in str(exc)
    assert "exceeds maximum size" in str(exc).lower()


def test_query_too_long_constructor_and_message():
    """QueryTooLong accepts max_seconds and includes it in message."""
    max_seconds = 60
    exc = QueryTooLong(max_seconds)

    assert isinstance(exc, VoiceError)
    assert exc.max_seconds == max_seconds
    assert str(max_seconds) in str(exc)
    assert "exceeds maximum duration" in str(exc).lower()


def test_unsupported_audio_format_constructor_and_message():
    """UnsupportedAudioFormat names received type and lists supported set (sorted)."""
    received = "audio/flac"
    supported = {"audio/wav", "audio/mp4", "audio/aac"}
    exc = UnsupportedAudioFormat(received, supported)

    assert isinstance(exc, VoiceError)
    assert exc.received_mimetype == received
    assert exc.supported == supported

    # Message should include received type
    assert received in str(exc)

    # Message should list supported types in sorted order
    message = str(exc)
    assert "audio/aac" in message
    assert "audio/mp4" in message
    assert "audio/wav" in message

    # Verify sorted order by checking positions
    aac_pos = message.index("audio/aac")
    mp4_pos = message.index("audio/mp4")
    wav_pos = message.index("audio/wav")
    assert aac_pos < mp4_pos < wav_pos, "Supported types should be sorted in message"


def test_empty_recording_constructor_and_message():
    """EmptyRecording takes no parameters and has meaningful message."""
    exc = EmptyRecording()

    assert isinstance(exc, VoiceError)
    assert "empty" in str(exc).lower()


def test_unintelligible_query_constructor_and_message():
    """UnintelligibleQuery takes no parameters and has meaningful message."""
    exc = UnintelligibleQuery()

    assert isinstance(exc, VoiceError)
    message = str(exc).lower()
    assert "could not understand" in message or "unintelligible" in message


def test_voice_unavailable_default_message():
    """VoiceUnavailable has default message when constructed with no args."""
    exc = VoiceUnavailable()

    assert isinstance(exc, VoiceError)
    assert exc.message == "Voice services are temporarily unavailable"
    assert str(exc) == "Voice services are temporarily unavailable"


def test_voice_unavailable_custom_message():
    """VoiceUnavailable accepts custom message."""
    custom = "STT service is down for maintenance"
    exc = VoiceUnavailable(custom)

    assert isinstance(exc, VoiceError)
    assert exc.message == custom
    assert str(exc) == custom


# AC-003: None subclass Starlette/HTTP types
def test_exceptions_do_not_subclass_http_types():
    """Voice exceptions are plain Python exceptions, not HTTP exceptions."""
    # Import starlette types if available (they're in project dependencies)
    try:
        from starlette.exceptions import HTTPException
    except ImportError:
        pytest.skip("Starlette not available in test environment")

    # Verify none of the voice exceptions inherit from HTTPException
    exceptions_to_test = [
        VoiceError,
        RecordingTooLarge,
        QueryTooLong,
        UnsupportedAudioFormat,
        EmptyRecording,
        UnintelligibleQuery,
        VoiceUnavailable,
    ]

    for exc_class in exceptions_to_test:
        assert not issubclass(exc_class, HTTPException), (
            f"{exc_class.__name__} should not inherit from HTTPException. "
            "Status code mapping happens per-handler in TASK-VOX-006."
        )
