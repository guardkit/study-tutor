"""Voice service module (FEAT-VOICE-001).

This module provides configuration and error handling for voice features
(speech-to-text and text-to-speech).
"""

from __future__ import annotations

from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import (
    EmptyRecording,
    QueryTooLong,
    RecordingTooLarge,
    UnintelligibleQuery,
    UnsupportedAudioFormat,
    VoiceError,
    VoiceUnavailable,
)

__all__ = [
    "VoiceConfig",
    "VoiceError",
    "RecordingTooLarge",
    "QueryTooLong",
    "UnsupportedAudioFormat",
    "EmptyRecording",
    "UnintelligibleQuery",
    "VoiceUnavailable",
]
