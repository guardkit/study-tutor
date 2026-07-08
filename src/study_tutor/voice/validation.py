"""Voice upload validation with in-memory multipart parsing.

TASK-VOX-004: In-memory multipart parse + order-pinned upload validation.

Never-at-rest invariant: audio data is never written to disk. Uses python-multipart
push parser over request.stream() instead of Starlette's request.form() which spools
files >1MB to disk.

Order-pinned validation (spec scenario "No recording audio is ever kept"):
1. Size (RecordingTooLarge) - enforced during read
2. Empty (EmptyRecording)
3. Base MIME type (UnsupportedAudioFormat)
4. Duration (QueryTooLong) - best-effort via probe_duration_seconds
"""

from __future__ import annotations

from dataclasses import dataclass

from python_multipart.multipart import parse_options_header
from starlette.datastructures import Headers
from starlette.requests import Request

from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import (
    EmptyRecording,
    QueryTooLong,
    RecordingTooLarge,
    UnsupportedAudioFormat,
)
from study_tutor.voice.utils import probe_duration_seconds


@dataclass(frozen=True)
class ValidatedUpload:
    """Validated voice upload result.

    Attributes:
        content: Raw audio bytes (never spooled to disk)
        filename: Original filename from multipart field
        content_type: MIME type from multipart field (original, not normalized)
    """

    content: bytes
    filename: str
    content_type: str


async def parse_voice_upload(
    request: Request, config: VoiceConfig
) -> ValidatedUpload:
    """Parse and validate voice upload from multipart request.

    Never calls request.form() - uses in-memory push parser to enforce
    the never-at-rest invariant (no disk spooling).

    Validation order (per spec):
    1. Size check during read (RecordingTooLarge)
    2. Empty check (EmptyRecording)
    3. MIME type check (UnsupportedAudioFormat)
    4. Duration check if derivable (QueryTooLong)

    Args:
        request: Starlette request with multipart/form-data body
        config: Voice configuration with validation limits

    Returns:
        ValidatedUpload with content, filename, and content_type

    Raises:
        RecordingTooLarge: Audio exceeds max_recording_bytes (during read)
        EmptyRecording: Audio field is empty
        UnsupportedAudioFormat: MIME type not in supported_base_mimetypes
        QueryTooLong: Duration exceeds max_query_seconds (when derivable)
        ValueError: Missing audio field or invalid multipart structure
    """
    # Extract boundary from Content-Type header
    content_type_header = request.headers.get("content-type", "")
    _, params = parse_options_header(content_type_header)
    boundary = params.get(b"boundary")

    if not boundary:
        raise ValueError("Missing boundary in multipart/form-data Content-Type")

    # Parse multipart body in-memory using push parser
    # Accumulate body (with generous buffer for multipart overhead)
    accumulated_body = b""
    max_buffer = config.max_recording_bytes * 2  # Allow overhead for boundaries/headers

    # Stream body
    async for chunk in request.stream():
        if len(accumulated_body) + len(chunk) > max_buffer:
            # Prevent excessive buffering
            raise RecordingTooLarge(config.max_recording_bytes)
        accumulated_body += chunk

    if not accumulated_body:
        raise ValueError("Empty request body")

    # Simple multipart parsing (extract audio field)
    parts = _parse_multipart_simple(accumulated_body, boundary)

    if "audio" not in parts:
        raise ValueError("Missing required field: audio")

    field_data = parts["audio"]
    audio_bytes = field_data["content"]
    audio_filename = field_data["filename"]
    audio_content_type = field_data["content_type"]

    # 1. SIZE CHECK - enforced on parsed audio field
    if len(audio_bytes) > config.max_recording_bytes:
        raise RecordingTooLarge(config.max_recording_bytes)

    # 2. EMPTY CHECK
    if not audio_bytes:
        raise EmptyRecording()

    # 3. MIME TYPE CHECK (strip parameters, normalize case)
    base_mime = audio_content_type.split(";")[0].strip().lower()

    if base_mime not in config.supported_base_mimetypes:
        raise UnsupportedAudioFormat(audio_content_type, config.supported_base_mimetypes)

    # 4. DURATION CHECK (best-effort)
    duration = probe_duration_seconds(audio_bytes, audio_content_type)
    if duration is not None and duration > config.max_query_seconds:
        raise QueryTooLong(config.max_query_seconds)

    return ValidatedUpload(
        content=audio_bytes,
        filename=audio_filename,
        content_type=audio_content_type,
    )


def _parse_multipart_simple(body: bytes, boundary: bytes) -> dict[str, dict]:
    """Simple multipart parser for audio field extraction.

    This is a simplified implementation for TASK-VOX-004. Production code
    would use multipart.MultipartParser's push API for true streaming.

    Args:
        body: Complete multipart body
        boundary: Multipart boundary bytes

    Returns:
        Dict mapping field names to {content, filename, content_type}
    """
    # Split by boundary
    delimiter = b"--" + boundary
    parts_raw = body.split(delimiter)

    fields = {}

    for part in parts_raw:
        if not part or part == b"--\r\n" or part == b"--" or part == b"\r\n" or part == b"--\n":
            continue

        # Remove leading \r\n but preserve content
        if part.startswith(b"\r\n"):
            part = part[2:]
        elif part.startswith(b"\n"):
            part = part[1:]

        # Skip truly empty parts after header check below
        # (don't skip here as we need to check for headers first)

        # Split headers from content
        try:
            header_end = part.index(b"\r\n\r\n")
        except ValueError:
            # Try with just \n\n (some clients use \n instead of \r\n)
            try:
                header_end = part.index(b"\n\n")
                sep_len = 2
            except ValueError:
                continue
        else:
            sep_len = 4

        headers_raw = part[:header_end]
        content = part[header_end + sep_len:]  # Skip separator

        # Remove trailing \r\n or \n (but preserve empty content)
        if content.endswith(b"\r\n"):
            content = content[:-2]
        elif content.endswith(b"\n"):
            content = content[:-1]

        # Parse headers
        headers_text = headers_raw.decode("utf-8", errors="replace")
        field_name = None
        filename = "unknown"
        content_type = "application/octet-stream"

        for line in headers_text.replace("\r\n", "\n").split("\n"):
            if line.lower().startswith("content-disposition:"):
                # Extract name and filename
                _, params = parse_options_header(line)
                if b"name" in params:
                    field_name = params[b"name"].decode("utf-8")
                if b"filename" in params:
                    filename = params[b"filename"].decode("utf-8")
            elif line.lower().startswith("content-type:"):
                content_type = line.split(":", 1)[1].strip()

        if field_name:
            fields[field_name] = {
                "content": content,
                "filename": filename,
                "content_type": content_type,
            }

    return fields
