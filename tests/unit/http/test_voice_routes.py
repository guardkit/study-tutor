"""Unit tests for voice HTTP routes (TASK-VOX-006).

Tests the two voice endpoints (POST voice-turn, GET voice-audio) with starlette TestClient
over fake VoiceTurnService and ChunkStore. Verifies route paths/methods, error mapping,
flag-gated mounting, and binding §2/§4 Rev 1 compliance.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock

from starlette.testclient import TestClient

from study_tutor.voice.errors import (
    RecordingTooLarge,
    QueryTooLong,
    UnsupportedAudioFormat,
    EmptyRecording,
    UnintelligibleQuery,
    VoiceUnavailable,
)
from study_tutor.voice.service import VoiceTurnResult, AudioRef
from study_tutor.session.errors import (
    SessionNotFoundError,
    SessionEnded,
    SessionForbidden,
)


# -------------------- Fixtures --------------------


@pytest.fixture
def fake_voice_service():
    """Mock VoiceTurnService for testing route logic."""
    return AsyncMock()


@pytest.fixture
def fake_chunk_store():
    """Mock ChunkStore for testing audio retrieval."""
    store = Mock()
    store.get = Mock(return_value=b"fake-audio-wav-bytes")
    return store


@pytest.fixture
def fake_voice_config():
    """Mock VoiceConfig with voice enabled."""
    from study_tutor.voice.config import VoiceConfig

    return VoiceConfig.from_env(enabled="true", stt_model="test-stt", tts_model="test-tts")


@pytest.fixture
def fake_voice_config_disabled():
    """Mock VoiceConfig with voice disabled."""
    from study_tutor.voice.config import VoiceConfig

    return VoiceConfig.from_env(enabled="false")


@pytest.fixture
def fake_service():
    """Mock SessionService for non-voice routes."""
    return AsyncMock()


@pytest.fixture
def fake_reply_fn():
    """Mock reply_fn for turn endpoint."""
    return AsyncMock()


@pytest.fixture
def fake_auth_config():
    """Mock HTTPAuthConfig with test token."""
    from study_tutor.http.auth import HTTPAuthConfig, TableTokenResolver

    token_to_student = {"token-test": "test-student"}
    return HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
    )


@pytest.fixture
def fake_student_store():
    """Mock StudentStore for auth layer."""
    store = AsyncMock()
    store.student_exists.return_value = True
    return store


@pytest.fixture
def client_with_voice(
    fake_service, fake_reply_fn, fake_auth_config, fake_student_store,
    fake_voice_config, fake_voice_service, fake_chunk_store
):
    """TestClient with voice enabled and injected fake dependencies."""
    from study_tutor.http.app import create_app

    app = create_app(
        service=fake_service,
        reply_fn=fake_reply_fn,
        auth_config=fake_auth_config,
        student_store=fake_student_store,
        voice_config=fake_voice_config,
        voice_service=fake_voice_service,
        chunk_store=fake_chunk_store,
    )
    return TestClient(app)


@pytest.fixture
def client_without_voice(
    fake_service, fake_reply_fn, fake_auth_config, fake_student_store,
    fake_voice_config_disabled
):
    """TestClient with voice disabled (default)."""
    from study_tutor.http.app import create_app

    app = create_app(
        service=fake_service,
        reply_fn=fake_reply_fn,
        auth_config=fake_auth_config,
        student_store=fake_student_store,
        voice_config=fake_voice_config_disabled,
    )
    return TestClient(app)


# -------------------- voice-turn error mapping tests --------------------


def test_voice_turn_recording_too_large(client_with_voice, fake_voice_service):
    """RecordingTooLarge → 413 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = RecordingTooLarge(max_bytes=10485760)

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error_type"] == "RecordingTooLarge"


def test_voice_turn_query_too_long(client_with_voice, fake_voice_service):
    """QueryTooLong → 413 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = QueryTooLong(max_seconds=60)

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error_type"] == "QueryTooLong"


def test_voice_turn_unsupported_audio_format(client_with_voice, fake_voice_service):
    """UnsupportedAudioFormat → 415 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = UnsupportedAudioFormat(
        "audio/flac", {"audio/wav", "audio/mp4"}
    )

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.flac", b"fake-audio", "audio/flac")},
    )

    assert response.status_code == 415
    assert response.json()["error_type"] == "UnsupportedAudioFormat"


def test_voice_turn_empty_recording(client_with_voice, fake_voice_service):
    """EmptyRecording → 422 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = EmptyRecording()

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"", "audio/wav")},
    )

    assert response.status_code == 422
    assert response.json()["error_type"] == "EmptyRecording"


def test_voice_turn_unintelligible_query(client_with_voice, fake_voice_service):
    """UnintelligibleQuery → 422 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = UnintelligibleQuery()

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 422
    assert response.json()["error_type"] == "UnintelligibleQuery"


def test_voice_turn_voice_unavailable(client_with_voice, fake_voice_service):
    """VoiceUnavailable → 503 with error_type (binding §2 Rev 1)."""
    fake_voice_service.voice_turn.side_effect = VoiceUnavailable()

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["error_type"] == "VoiceUnavailable"


# -------------------- voice-turn session error mapping tests --------------------


def test_voice_turn_missing_token(client_with_voice):
    """Missing Authorization → 401 Unauthenticated."""
    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 401
    assert response.json()["error_type"] == "Unauthenticated"


def test_voice_turn_invalid_token(client_with_voice):
    """Invalid token → 401 Unauthenticated."""
    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer invalid-token"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 401
    assert response.json()["error_type"] == "Unauthenticated"


def test_voice_turn_session_forbidden(client_with_voice, fake_voice_service):
    """SessionForbidden (wrong student) → 403."""
    fake_voice_service.voice_turn.side_effect = SessionForbidden(
        "sess1", "test-student", "other-student"
    )

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 403
    assert response.json()["error_type"] == "SessionForbidden"


def test_voice_turn_session_not_found(client_with_voice, fake_voice_service):
    """SessionNotFoundError → 404."""
    fake_voice_service.voice_turn.side_effect = SessionNotFoundError("sess1")

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 404
    assert response.json()["error_type"] == "SessionNotFoundError"


def test_voice_turn_session_ended(client_with_voice, fake_voice_service):
    """SessionEnded → 410."""
    fake_voice_service.voice_turn.side_effect = SessionEnded("sess1")

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 410
    assert response.json()["error_type"] == "SessionEnded"


# -------------------- voice-turn happy path tests --------------------


def test_voice_turn_happy_path(client_with_voice, fake_voice_service):
    """Happy path: POST voice-turn returns transcript + tutor_response + audio refs."""
    fake_voice_service.voice_turn.return_value = VoiceTurnResult(
        transcript="Hello tutor",
        tutor_response="Hello student! How can I help?",
        audio=[AudioRef(seq=0, chunk_id="chunk123", url="/api/sessions/sess1/voice-audio/chunk123")],
    )

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "Hello tutor"
    assert data["tutor_response"] == "Hello student! How can I help?"
    assert len(data["audio"]) == 1
    assert data["audio"][0]["seq"] == 0
    assert data["audio"][0]["chunk_id"] == "chunk123"
    assert data["audio"][0]["url"] == "/api/sessions/sess1/voice-audio/chunk123"


def test_voice_turn_stream_field_ignored(client_with_voice, fake_voice_service):
    """stream: true field is accepted and ignored (binding §2.1 Rev 1)."""
    fake_voice_service.voice_turn.return_value = VoiceTurnResult(
        transcript="Test",
        tutor_response="Response",
        audio=[],
    )

    response = client_with_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
        data={"stream": "true"},
    )

    assert response.status_code == 200


# -------------------- voice-audio tests --------------------


def test_voice_audio_happy_path(client_with_voice, fake_chunk_store):
    """GET voice-audio returns audio/wav bytes with correct content-type."""
    fake_chunk_store.get.return_value = b"wav-audio-bytes-here"

    response = client_with_voice.get(
        "/api/sessions/sess1/voice-audio/chunk123",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"wav-audio-bytes-here"
    fake_chunk_store.get.assert_called_once_with("sess1", "chunk123")


def test_voice_audio_chunk_miss_404_no_error_type(client_with_voice, fake_chunk_store):
    """ChunkStore.get -> None maps to 404 with NO error_type (binding §4.2 Rev 1)."""
    fake_chunk_store.get.return_value = None

    response = client_with_voice.get(
        "/api/sessions/sess1/voice-audio/expired",
        headers={"Authorization": "Bearer token-test"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "error_type" not in data


def test_voice_audio_missing_token(client_with_voice):
    """GET voice-audio without token → 401."""
    response = client_with_voice.get(
        "/api/sessions/sess1/voice-audio/chunk123",
    )

    assert response.status_code == 401


# -------------------- flag-gated mounting tests --------------------


def test_voice_routes_not_mounted_when_disabled(client_without_voice):
    """When voice_config.enabled=false, voice routes return 404."""
    # Try voice-turn
    response = client_without_voice.post(
        "/api/sessions/sess1/voice-turn",
        headers={"Authorization": "Bearer token-test"},
        files={"audio": ("test.wav", b"fake-audio", "audio/wav")},
    )
    assert response.status_code == 404

    # Try voice-audio
    response = client_without_voice.get(
        "/api/sessions/sess1/voice-audio/chunk123",
        headers={"Authorization": "Bearer token-test"},
    )
    assert response.status_code == 404


def test_existing_routes_unaffected_when_voice_disabled(client_without_voice, fake_service):
    """When voice disabled, existing text routes still work (zero changes)."""
    from study_tutor.session.service import StartSessionResult

    fake_service.start_session.return_value = StartSessionResult(
        session_id="new-sess",
        student_id="test-student",
        subject="Math",
        topic=None,
        resumed=False,
        turns=None,
    )

    response = client_without_voice.post(
        "/api/sessions/start",
        headers={"Authorization": "Bearer token-test"},
        json={},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "new-sess"


# -------------------- seam tests --------------------


@pytest.mark.seam
@pytest.mark.integration_contract("chunk_store_get")
def test_chunk_miss_is_transport_404(client_with_voice, fake_chunk_store):
    """Contract: ChunkStore.get -> None maps to 404 with NO error_type
    (binding §4.2 Rev 1). Producer: TASK-VOX-005; consumer: voice_audio route."""
    fake_chunk_store.get.return_value = None

    r = client_with_voice.get(
        "/api/sessions/s1/voice-audio/expired",
        headers={"Authorization": "Bearer token-test"}
    )
    assert r.status_code == 404
    assert "error_type" not in r.json()
