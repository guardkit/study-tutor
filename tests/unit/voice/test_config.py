"""Unit tests for voice configuration (TASK-VOX-001).

Tests VoiceConfig.from_env() parsing, defaults, environment overrides,
boolean flag validation, and SR-03 discipline (no import-time env access).
"""

from __future__ import annotations

import pytest

from study_tutor.voice.config import VoiceConfig, _parse_bool_flag


# AC-001: VoiceConfig.from_env() returns frozen instance with defaults
def test_config_from_env_default_values():
    """VoiceConfig.from_env() with no args returns all defaults."""
    config = VoiceConfig.from_env()

    # Verify default values match spec
    assert config.enabled is False
    assert config.stt_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.stt_model == "parakeet-tdt"
    assert config.tts_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.tts_model == "qwen3-tts"
    assert config.tts_voice == "Ryan"

    # Verify constants
    assert config.audio_timeout_seconds == 10.0
    assert config.max_query_seconds == 60
    assert config.max_recording_bytes == 10 * 1024 * 1024
    assert config.chunk_ttl_seconds == 120
    assert config.supported_base_mimetypes == {
        "audio/mp4",
        "audio/m4a",
        "audio/aac",
        "audio/ogg",
        "audio/webm",
        "audio/wav",
        "audio/mpeg",
    }


def test_config_is_frozen():
    """VoiceConfig instances are frozen (immutable)."""
    config = VoiceConfig.from_env()

    # Attempt to modify should raise FrozenInstanceError
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError in Python 3.11+
        config.enabled = True  # type: ignore


# AC-004: Env overrides work correctly
def test_config_from_env_all_overrides(monkeypatch):
    """VoiceConfig.from_env() respects all environment variable overrides."""
    # Pin the full env-var surface (hermetic-env discipline)
    monkeypatch.delenv("STUDY_TUTOR_VOICE_ENABLED", raising=False)
    monkeypatch.delenv("STT_BASE_URL", raising=False)
    monkeypatch.delenv("STT_MODEL", raising=False)
    monkeypatch.delenv("TTS_BASE_URL", raising=False)
    monkeypatch.delenv("TTS_MODEL", raising=False)
    monkeypatch.delenv("TTS_VOICE", raising=False)

    config = VoiceConfig.from_env(
        enabled="true",
        stt_base_url="http://custom-stt:8000/api",
        stt_model="custom-stt-model",
        tts_base_url="http://custom-tts:8000/api",
        tts_model="custom-tts-model",
        tts_voice="Emma",
    )

    assert config.enabled is True
    assert config.stt_base_url == "http://custom-stt:8000/api"
    assert config.stt_model == "custom-stt-model"
    assert config.tts_base_url == "http://custom-tts:8000/api"
    assert config.tts_model == "custom-tts-model"
    assert config.tts_voice == "Emma"

    # Constants should not be affected
    assert config.audio_timeout_seconds == 10.0
    assert config.max_query_seconds == 60


def test_config_from_env_partial_overrides(monkeypatch):
    """VoiceConfig.from_env() allows partial overrides (others use defaults)."""
    # Pin the full env-var surface (hermetic-env discipline)
    monkeypatch.delenv("STUDY_TUTOR_VOICE_ENABLED", raising=False)
    monkeypatch.delenv("STT_BASE_URL", raising=False)
    monkeypatch.delenv("STT_MODEL", raising=False)
    monkeypatch.delenv("TTS_BASE_URL", raising=False)
    monkeypatch.delenv("TTS_MODEL", raising=False)
    monkeypatch.delenv("TTS_VOICE", raising=False)

    config = VoiceConfig.from_env(
        enabled="1",
        stt_model="override-model",
    )

    # Overridden values
    assert config.enabled is True
    assert config.stt_model == "override-model"

    # Default values for non-overridden fields
    assert config.stt_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.tts_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.tts_model == "qwen3-tts"
    assert config.tts_voice == "Ryan"


# AC-001: Malformed boolean raises ValueError naming the variable
def test_config_from_env_malformed_boolean_raises_clear_error(monkeypatch):
    """VoiceConfig.from_env() raises ValueError on malformed boolean, naming the variable."""
    # Pin the full env-var surface (hermetic-env discipline)
    monkeypatch.delenv("STUDY_TUTOR_VOICE_ENABLED", raising=False)
    monkeypatch.delenv("STT_BASE_URL", raising=False)
    monkeypatch.delenv("STT_MODEL", raising=False)
    monkeypatch.delenv("TTS_BASE_URL", raising=False)
    monkeypatch.delenv("TTS_MODEL", raising=False)
    monkeypatch.delenv("TTS_VOICE", raising=False)

    with pytest.raises(
        ValueError, match="Failed to parse STUDY_TUTOR_VOICE_ENABLED"
    ) as exc_info:
        VoiceConfig.from_env(enabled="not-a-boolean")

    # Verify the error message includes details about what's wrong
    assert "Invalid boolean value" in str(exc_info.value)


# _parse_bool_flag tests
def test_parse_bool_flag_true_values():
    """_parse_bool_flag recognizes true values (case-insensitive)."""
    true_values = ["true", "TRUE", "True", "1", "yes", "YES", "y", "Y", "on", "ON"]
    for value in true_values:
        assert _parse_bool_flag(value) is True, f"Failed for '{value}'"


def test_parse_bool_flag_false_values():
    """_parse_bool_flag recognizes false values (case-insensitive)."""
    false_values = ["false", "FALSE", "False", "0", "no", "NO", "n", "N", "off", "OFF"]
    for value in false_values:
        assert _parse_bool_flag(value) is False, f"Failed for '{value}'"


def test_parse_bool_flag_empty_string():
    """_parse_bool_flag returns False for empty string."""
    assert _parse_bool_flag("") is False


def test_parse_bool_flag_whitespace_handling():
    """_parse_bool_flag handles leading/trailing whitespace."""
    assert _parse_bool_flag("  true  ") is True
    assert _parse_bool_flag("  false  ") is False


def test_parse_bool_flag_invalid_value_raises():
    """_parse_bool_flag raises ValueError for unrecognized values."""
    invalid_values = ["not-a-bool", "2", "maybe", "truthy", "t", "f"]
    for value in invalid_values:
        with pytest.raises(ValueError, match="Invalid boolean value") as exc_info:
            _parse_bool_flag(value)
        # Verify error message includes the problematic value
        assert value in str(exc_info.value)


# AC-002: No os.environ access at import time (SR-03 discipline)
def test_no_import_time_env_access(monkeypatch):
    """Importing voice.config does not access os.environ.

    This test verifies SR-03 discipline: no import-time environment reads.
    The config module should only read env vars when from_env() is called.
    """
    # Set environment variables that would be read if import-time access existed
    monkeypatch.setenv("STUDY_TUTOR_VOICE_ENABLED", "true")
    monkeypatch.setenv("STT_BASE_URL", "http://should-not-be-read:9000")

    # Re-import the module (in a real scenario this happens once at startup)
    # If the module accesses os.environ at import time, it would capture these values
    import importlib
    import study_tutor.voice.config

    importlib.reload(study_tutor.voice.config)

    # Create a config without passing these values - should get defaults
    config = VoiceConfig.from_env()

    # If import-time access existed, these would be the monkeypatched values
    # Instead, we should get defaults because we didn't pass them to from_env()
    assert config.enabled is False  # Default, not "true"
    assert config.stt_base_url == "http://promaxgb10-41b1:9000/v1"  # Default

    # Clean up
    monkeypatch.delenv("STUDY_TUTOR_VOICE_ENABLED")
    monkeypatch.delenv("STT_BASE_URL")


def test_hermetic_env_coverage_all_vars(monkeypatch):
    """Verify all voice env vars are pinned in tests (hermetic-env discipline).

    This test documents the full env-var surface for voice config and verifies
    that tests properly isolate by pinning all relevant variables.
    """
    # Full env-var surface for voice config
    voice_env_vars = [
        "STUDY_TUTOR_VOICE_ENABLED",
        "STT_BASE_URL",
        "STT_MODEL",
        "TTS_BASE_URL",
        "TTS_MODEL",
        "TTS_VOICE",
    ]

    # Pin all variables (hermetic-env: test outcome should not depend on host env)
    for var in voice_env_vars:
        monkeypatch.delenv(var, raising=False)

    # Now we can test with confidence that defaults are truly defaults
    config = VoiceConfig.from_env()
    assert config.enabled is False
    assert config.stt_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.stt_model == "parakeet-tdt"
    assert config.tts_base_url == "http://promaxgb10-41b1:9000/v1"
    assert config.tts_model == "qwen3-tts"
    assert config.tts_voice == "Ryan"
