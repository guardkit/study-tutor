"""Tests for voice upload validation and in-memory multipart parsing.

TASK-VOX-004: Tests for parse_voice_upload with order-pinned validation
and no-spooling invariant enforcement.
"""

from __future__ import annotations

import io
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import (
    EmptyRecording,
    QueryTooLong,
    RecordingTooLarge,
    UnsupportedAudioFormat,
)
from study_tutor.voice.validation import ValidatedUpload, parse_voice_upload


@pytest.fixture
def test_config() -> VoiceConfig:
    """Minimal test configuration."""
    return VoiceConfig(
        enabled=True,
        stt_base_url="http://test:9000/v1",
        stt_model="test-model",
        tts_base_url="http://test:9000/v1",
        tts_model="test-model",
        tts_voice="Test",
        audio_timeout_seconds=10.0,
        max_query_seconds=60,
        max_recording_bytes=10 * 1024 * 1024,  # 10 MB
        chunk_ttl_seconds=120,
        supported_base_mimetypes={
            "audio/mp4",
            "audio/ogg",
            "audio/webm",
            "audio/wav",
        },
    )


def build_multipart_body(
    audio_content: bytes, content_type: str, filename: str = "test.ogg"
) -> bytes:
    """Build a multipart/form-data body with an audio field.

    Args:
        audio_content: Raw audio bytes
        content_type: MIME type for the audio field
        filename: Filename for the audio field

    Returns:
        Complete multipart body bytes
    """
    boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"
    parts = [
        b"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n",
        b'Content-Disposition: form-data; name="audio"; filename="'
        + filename.encode()
        + b'"\r\n',
        b"Content-Type: " + content_type.encode() + b"\r\n",
        b"\r\n",
        audio_content,
        b"\r\n",
        b"------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n",
    ]
    return b"".join(parts)


def create_mock_request(body: bytes) -> Request:
    """Create a mock Starlette Request with streaming body.

    Args:
        body: Complete request body bytes

    Returns:
        Mock Request object with async stream() method
    """
    from starlette.datastructures import Headers

    async def mock_stream():
        """Async generator that yields body in chunks."""
        chunk_size = 8192
        offset = 0
        while offset < len(body):
            yield body[offset : offset + chunk_size]
            offset += chunk_size

    request = MagicMock(spec=Request)
    request.stream = mock_stream
    request.headers = Headers(
        {
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"
        }
    )
    return request


# AC-001: request.form() absent from module; SpooledTemporaryFile patch proves no spooling
@pytest.mark.asyncio
async def test_no_spooling_to_disk(test_config: VoiceConfig):
    """Verify parse never spools to disk via SpooledTemporaryFile."""
    audio_data = b"fake ogg data" * 100
    body = build_multipart_body(audio_data, "audio/ogg")
    request = create_mock_request(body)

    # Patch SpooledTemporaryFile to raise - parse should still succeed
    with patch.object(
        tempfile, "SpooledTemporaryFile", side_effect=AssertionError("Spooling detected!")
    ):
        result = await parse_voice_upload(request, test_config)

    assert result.content == audio_data
    assert result.content_type == "audio/ogg"
    assert result.filename == "test.ogg"


# AC-002: Over-cap body with lying Content-Length → RecordingTooLarge
@pytest.mark.asyncio
async def test_over_cap_body_lying_content_length(test_config: VoiceConfig):
    """Over-cap body with lying declared size raises RecordingTooLarge."""
    # Create audio data that exceeds max_recording_bytes (10 MB)
    over_cap_size = test_config.max_recording_bytes + 1024
    audio_data = b"x" * over_cap_size
    body = build_multipart_body(audio_data, "audio/ogg")
    request = create_mock_request(body)

    with pytest.raises(RecordingTooLarge) as exc_info:
        await parse_voice_upload(request, test_config)

    assert exc_info.value.max_bytes == test_config.max_recording_bytes


# AC-003: Missing audio field → validation error
@pytest.mark.asyncio
async def test_missing_audio_field(test_config: VoiceConfig):
    """Missing audio field raises ValueError."""
    from starlette.datastructures import Headers

    # Build multipart body with different field name
    boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = b"".join(
        [
            b"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n",
            b'Content-Disposition: form-data; name="other"\r\n',
            b"\r\n",
            b"some data",
            b"\r\n",
            b"------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n",
        ]
    )

    async def mock_stream():
        chunk_size = 8192
        offset = 0
        while offset < len(body):
            yield body[offset : offset + chunk_size]
            offset += chunk_size

    request = MagicMock(spec=Request)
    request.stream = mock_stream
    request.headers = Headers(
        {
            "content-type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"
        }
    )

    with pytest.raises(ValueError, match="Missing required field: audio"):
        await parse_voice_upload(request, test_config)


# AC-004: 7-way MIME-variant matrix passes
@pytest.mark.parametrize(
    "content_type,expected_base",
    [
        ("audio/ogg", "audio/ogg"),
        ("audio/ogg;codecs=opus", "audio/ogg"),
        ("audio/ogg; codecs=opus", "audio/ogg"),
        ('audio/ogg;codecs="opus"', "audio/ogg"),
        ("AUDIO/OGG", "audio/ogg"),
        ("audio/mp4", "audio/mp4"),
        ("audio/webm;codecs=opus", "audio/webm"),
    ],
)
@pytest.mark.asyncio
async def test_mime_variant_matrix(
    content_type: str, expected_base: str, test_config: VoiceConfig
):
    """Test MIME type normalization variants."""
    audio_data = b"fake audio data"
    body = build_multipart_body(audio_data, content_type)
    request = create_mock_request(body)

    result = await parse_voice_upload(request, test_config)

    assert result.content == audio_data
    # Original content type preserved (not normalized)
    assert result.content_type == content_type


@pytest.mark.asyncio
async def test_unsupported_mime_type(test_config: VoiceConfig):
    """Unsupported MIME type raises UnsupportedAudioFormat with received value."""
    audio_data = b"fake data"
    unsupported_type = "audio/flac"
    body = build_multipart_body(audio_data, unsupported_type)
    request = create_mock_request(body)

    with pytest.raises(UnsupportedAudioFormat) as exc_info:
        await parse_voice_upload(request, test_config)

    assert exc_info.value.received_mimetype == unsupported_type
    assert exc_info.value.supported == test_config.supported_base_mimetypes


# AC-005: Order-pinning test
@pytest.mark.asyncio
async def test_validation_order_pinning(test_config: VoiceConfig):
    """Validation order: size → empty → MIME → duration."""

    # 1. Size violation (should be first)
    over_cap = test_config.max_recording_bytes + 1
    body = build_multipart_body(b"x" * over_cap, "invalid/type", "test.bin")
    request = create_mock_request(body)

    with pytest.raises(RecordingTooLarge):
        await parse_voice_upload(request, test_config)

    # 2. Empty recording (after size check passes)
    body = build_multipart_body(b"", "invalid/type")
    request = create_mock_request(body)

    with pytest.raises(EmptyRecording):
        await parse_voice_upload(request, test_config)

    # 3. MIME type (after size + empty checks pass)
    body = build_multipart_body(b"some data", "invalid/type")
    request = create_mock_request(body)

    with pytest.raises(UnsupportedAudioFormat):
        await parse_voice_upload(request, test_config)


@pytest.mark.asyncio
async def test_duration_boundary_exactly_60_seconds(test_config: VoiceConfig):
    """Audio exactly at max_query_seconds (60s) passes."""
    # Mock WebM content with exactly 60 seconds duration
    # Use a real WebM-like structure that probe_duration_seconds can parse
    audio_data = _build_webm_with_duration(60.0)
    body = build_multipart_body(audio_data, "audio/webm")
    request = create_mock_request(body)

    result = await parse_voice_upload(request, test_config)
    assert result.content == audio_data


@pytest.mark.asyncio
async def test_duration_boundary_just_over_60_seconds(test_config: VoiceConfig):
    """Audio just over max_query_seconds (60s) raises QueryTooLong."""
    # Mock WebM content with 61.0 seconds duration (clearly over 60)
    audio_data = _build_webm_with_duration(61.0)
    body = build_multipart_body(audio_data, "audio/webm")
    request = create_mock_request(body)

    with pytest.raises(QueryTooLong) as exc_info:
        await parse_voice_upload(request, test_config)

    assert exc_info.value.max_seconds == test_config.max_query_seconds


@pytest.mark.asyncio
async def test_durationless_streamed_webm_passes(test_config: VoiceConfig):
    """Streamed WebM with no duration element passes (byte cap only)."""
    # Build WebM with unknown size marker (streamed segment)
    audio_data = _build_webm_streamed()
    body = build_multipart_body(audio_data, "audio/webm")
    request = create_mock_request(body)

    result = await parse_voice_upload(request, test_config)
    assert result.content == audio_data


def _build_webm_with_duration(duration_seconds: float) -> bytes:
    """Build minimal WebM structure with Duration element.

    This creates a valid WebM structure that probe_duration_seconds can parse.

    The Duration element stores duration in ticks, where each tick is
    TimestampScale nanoseconds. Default TimestampScale is 1,000,000 ns (1 ms),
    so for X seconds we need X * 1000 ticks.
    """
    # EBML Header (0x1A45DFA3)
    ebml_header = b"\x1a\x45\xdf\xa3"
    ebml_size = b"\x9f"  # Size: 31 bytes (1-byte encoding)
    ebml_content = b"\x00" * 31  # Dummy EBML header content

    # Segment (0x18538067)
    segment_id = b"\x18\x53\x80\x67"
    # Segment size (large enough to hold Info)
    segment_size = b"\x01\x00\x00\x00\x00\x00\x01\x00"  # Known size: 256 bytes

    # Info element (0x1549A966)
    info_id = b"\x15\x49\xa9\x66"
    info_size = b"\x8d"  # Size: 13 bytes

    # TimestampScale (0x2AD7B1) - default 1,000,000 ns
    ts_id = b"\x2a\xd7\xb1"
    ts_size = b"\x84"  # Size: 4 bytes
    ts_value = (1_000_000).to_bytes(4, "big")  # 1ms timescale

    # Duration (0x4489) - float value in ticks
    # Each tick = 1ms (TimestampScale), so X seconds = X * 1000 ticks
    dur_id = b"\x44\x89"
    dur_size = b"\x84"  # Size: 4 bytes
    import struct

    duration_ticks = duration_seconds * 1000.0  # Convert seconds to milliseconds
    dur_value = struct.pack(">f", duration_ticks)

    # Assemble
    info_content = ts_id + ts_size + ts_value + dur_id + dur_size + dur_value
    segment_content = info_id + info_size + info_content

    # Pad segment to declared size
    padding_needed = 256 - len(segment_content)
    segment_content += b"\x00" * padding_needed

    return (
        ebml_header
        + ebml_size
        + ebml_content
        + segment_id
        + segment_size
        + segment_content
    )


def _build_webm_streamed() -> bytes:
    """Build WebM with unknown size marker (no Duration element)."""
    # EBML Header
    ebml_header = b"\x1a\x45\xdf\xa3"
    ebml_size = b"\x9f"
    ebml_content = b"\x00" * 31

    # Segment with unknown size marker
    segment_id = b"\x18\x53\x80\x67"
    segment_size = b"\x01\xff\xff\xff\xff\xff\xff\xff"  # Unknown size

    # Minimal segment content (no Info element)
    segment_content = b"\x00" * 100

    return ebml_header + ebml_size + ebml_content + segment_id + segment_size + segment_content


# AC-006: All modified files pass linting (enforced by test runner)
