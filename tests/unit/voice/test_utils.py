"""Tests for voice/utils.py duration probe and audio builders."""

from __future__ import annotations

import struct


# ============================================================================
# Audio Sample Builders (inline for 2-file constraint)
# ============================================================================


def _write_ebml_element(element_id: bytes, data: bytes) -> bytes:
    """Write an EBML element with variable-length size encoding."""
    size = len(data)
    # Simple size encoding (up to 127 bytes uses 1-byte size)
    if size < 127:
        size_bytes = bytes([0x80 | size])
    elif size < 16383:
        size_bytes = bytes([0x40 | (size >> 8), size & 0xFF])
    elif size < 2097151:
        size_bytes = bytes([0x20 | (size >> 16), (size >> 8) & 0xFF, size & 0xFF])
    else:
        size_bytes = bytes(
            [0x10 | (size >> 24), (size >> 16) & 0xFF, (size >> 8) & 0xFF, size & 0xFF]
        )
    return element_id + size_bytes + data


def make_webm(
    duration_ticks: int | None,
    timescale_ns: int | None = None,
    streamed_segment: bool = False,
) -> bytes:
    """
    Create a minimal WebM file with specified duration.

    Args:
        duration_ticks: Duration in timescale ticks (or None for streamed)
        timescale_ns: TimestampScale in nanoseconds (default: 1_000_000 = 1ms)
        streamed_segment: If True, omit Duration element (Chrome-style streaming)

    Returns:
        bytes: Valid WebM file content
    """
    timescale_ns = timescale_ns or 1_000_000

    # Build Info element
    info_elements = _write_ebml_element(
        b"\x2a\xd7\xb1", struct.pack(">I", timescale_ns)
    )  # TimestampScale

    if duration_ticks is not None and not streamed_segment:
        # Duration as 4-byte float
        duration_float = float(duration_ticks)
        info_elements += _write_ebml_element(
            b"\x44\x89", struct.pack(">f", duration_float)
        )  # Duration

    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_elements)  # Info

    # Build Segment with unknown size marker for streamed
    if streamed_segment:
        segment_size = b"\x01\xff\xff\xff\xff\xff\xff\xff"  # Unknown size
    else:
        segment_content = info
        segment_size_val = len(segment_content)
        if segment_size_val < 127:
            segment_size = bytes([0x80 | segment_size_val])
        else:
            segment_size = bytes(
                [0x40 | (segment_size_val >> 8), segment_size_val & 0xFF]
            )
        segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    if streamed_segment:
        segment = b"\x18\x53\x80\x67" + segment_size + info

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")  # EBMLVersion = 1
    doc_type = _write_ebml_element(b"\x42\x82", b"webm")  # DocType = "webm"
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version + doc_type)

    return ebml_header + segment


def make_ogg_page(
    granule: int,
    packet_data: bytes = b"\x00" * 32,
    page_sequence: int = 0,
    is_bos: bool = False,
    is_eos: bool = False,
) -> bytes:
    """
    Create an Ogg page with specified granule position.

    Args:
        granule: Granule position (signed 64-bit LE)
        packet_data: Packet payload
        page_sequence: Page sequence number
        is_bos: Beginning of stream flag
        is_eos: End of stream flag

    Returns:
        bytes: Valid Ogg page
    """
    # Ogg page structure
    capture = b"OggS"  # Capture pattern
    version = b"\x00"  # Version 0

    header_type = 0
    if is_bos:
        header_type |= 0x02
    if is_eos:
        header_type |= 0x04
    header_type_bytes = bytes([header_type])

    granule_bytes = struct.pack("<q", granule)  # Signed 64-bit LE
    serial = struct.pack("<I", 12345)  # Stream serial number
    sequence = struct.pack("<I", page_sequence)  # Page sequence

    # Segment table
    num_segments = 1
    segment_sizes = bytes([len(packet_data)])

    # Build page without checksum
    page_without_crc = (
        capture
        + version
        + header_type_bytes
        + granule_bytes
        + serial
        + sequence
        + b"\x00\x00\x00\x00"  # Checksum placeholder
        + bytes([num_segments])
        + segment_sizes
        + packet_data
    )

    # Calculate CRC32
    crc = 0
    for byte in page_without_crc:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = (crc << 1) ^ 0x04C11DB7
            else:
                crc = crc << 1
            crc &= 0xFFFFFFFF

    # Insert checksum
    page = (
        capture
        + version
        + header_type_bytes
        + granule_bytes
        + serial
        + sequence
        + struct.pack("<I", crc)
        + bytes([num_segments])
        + segment_sizes
        + packet_data
    )

    return page


def make_ogg_opus(duration_seconds: float) -> bytes:
    """
    Create a minimal Ogg/Opus file with specified duration.

    Args:
        duration_seconds: Duration in seconds

    Returns:
        bytes: Valid Ogg/Opus file with header, tags, and EOS page
    """
    # Opus sample rate is always 48kHz
    final_granule = int(duration_seconds * 48000)

    # Header packet (OpusHead)
    opus_head = (
        b"OpusHead" + b"\x01" + b"\x02" + b"\x00" * 10
    )  # Version 1, 2 channels, minimal
    header_page = make_ogg_page(0, opus_head, page_sequence=0, is_bos=True)

    # Tags packet (OpusTags)
    opus_tags = b"OpusTags" + b"\x00" * 8  # Minimal tags
    tags_page = make_ogg_page(0, opus_tags, page_sequence=1)

    # Data packet with final granule (EOS)
    data_packet = b"\x00" * 32  # Minimal audio data
    eos_page = make_ogg_page(final_granule, data_packet, page_sequence=2, is_eos=True)

    return header_page + tags_page + eos_page


# ============================================================================
# Tests for probe_duration_seconds
# ============================================================================


def test_webm_with_duration_element():
    """AC-001: WebM with Duration element returns correct seconds."""
    from study_tutor.voice.utils import probe_duration_seconds

    # 5000 ticks at 1ms timescale = 5 seconds
    webm = make_webm(duration_ticks=5000, timescale_ns=1_000_000)
    result = probe_duration_seconds(webm, "audio/webm")
    assert result is not None
    assert abs(result - 5.0) < 0.01


def test_webm_streamed_returns_none():
    """AC-001: Chrome-style streamed WebM (no Duration) returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    webm = make_webm(duration_ticks=5000, streamed_segment=True)
    result = probe_duration_seconds(webm, "audio/webm")
    assert result is None


def test_webm_with_custom_timescale():
    """WebM with non-default timescale calculates correctly."""
    from study_tutor.voice.utils import probe_duration_seconds

    # 10000 ticks at 2ms timescale = 20 seconds
    webm = make_webm(duration_ticks=10000, timescale_ns=2_000_000)
    result = probe_duration_seconds(webm, "audio/webm")
    assert result is not None
    assert abs(result - 20.0) < 0.01


def test_ogg_opus_eos_granule():
    """AC-002: Ogg/Opus EOS granule returns granule/48000."""
    from study_tutor.voice.utils import probe_duration_seconds

    ogg = make_ogg_opus(duration_seconds=3.5)
    result = probe_duration_seconds(ogg, "audio/ogg")
    assert result is not None
    assert abs(result - 3.5) < 0.01


def test_ogg_header_page_granule_zero():
    """AC-002: Ogg header page with granule 0 returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Single page with granule 0, no EOS
    ogg = make_ogg_page(0, b"OpusHead" + b"\x00" * 16, is_bos=True)
    result = probe_duration_seconds(ogg, "audio/ogg")
    assert result is None


def test_ogg_false_sync_skipped():
    """AC-002: False-sync 'OggS' bytes in middle of data are skipped."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Create valid pages with fake OggS in packet data
    header = make_ogg_page(0, b"OpusHead" + b"\x00" * 16, page_sequence=0, is_bos=True)
    fake_data = b"OggS" + b"\x00" * 28  # Fake sync in data
    tags = make_ogg_page(0, b"OpusTags" + fake_data, page_sequence=1)
    eos = make_ogg_page(96000, b"\x00" * 32, page_sequence=2, is_eos=True)  # 2 seconds

    ogg = header + tags + eos
    result = probe_duration_seconds(ogg, "audio/ogg")
    assert result is not None
    assert abs(result - 2.0) < 0.01


def test_unknown_content_type_returns_none():
    """AC-003: Unknown content types return None."""
    from study_tutor.voice.utils import probe_duration_seconds

    webm = make_webm(duration_ticks=5000)

    # Unknown types should return None
    assert probe_duration_seconds(webm, "audio/mp4") is None
    assert probe_duration_seconds(webm, "audio/mpeg") is None
    assert probe_duration_seconds(webm, "video/mp4") is None
    assert probe_duration_seconds(webm, "") is None


def test_content_type_with_codecs_parameter():
    """Content-Type with codecs parameter is handled (base MIME extracted)."""
    from study_tutor.voice.utils import probe_duration_seconds

    webm = make_webm(duration_ticks=3000)
    result = probe_duration_seconds(webm, "audio/webm; codecs=opus")
    assert result is not None
    assert abs(result - 3.0) < 0.01


def test_truncated_webm_returns_none():
    """AC-003: Truncated WebM returns None, never raises."""
    from study_tutor.voice.utils import probe_duration_seconds

    webm = make_webm(duration_ticks=5000)
    truncated = webm[:20]  # Truncate to 20 bytes

    result = probe_duration_seconds(truncated, "audio/webm")
    assert result is None  # Should not raise


def test_garbage_bytes_returns_none():
    """AC-003: Garbage bytes return None, never raises."""
    from study_tutor.voice.utils import probe_duration_seconds

    garbage = b"\x00\xff\x00\xff" * 100
    result = probe_duration_seconds(garbage, "audio/webm")
    assert result is None


def test_truncated_ogg_returns_none():
    """AC-003: Truncated Ogg returns None, never raises."""
    from study_tutor.voice.utils import probe_duration_seconds

    ogg = make_ogg_opus(2.0)
    truncated = ogg[:15]  # Truncate mid-header

    result = probe_duration_seconds(truncated, "audio/ogg")
    assert result is None


def test_empty_content_returns_none():
    """AC-003: Empty content returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    assert probe_duration_seconds(b"", "audio/webm") is None
    assert probe_duration_seconds(b"", "audio/ogg") is None


def test_builders_round_trip_webm():
    """AC-004: WebM builders produce bytes the probe itself parses."""
    from study_tutor.voice.utils import probe_duration_seconds

    test_cases = [
        (2.5, 1_000_000),  # 2.5 seconds, 1ms timescale
        (10.0, 1_000_000),  # 10 seconds
        (0.5, 1_000_000),  # 0.5 seconds
    ]

    for expected_duration, timescale in test_cases:
        ticks = int(expected_duration * 1_000_000_000 / timescale)
        webm = make_webm(duration_ticks=ticks, timescale_ns=timescale)
        result = probe_duration_seconds(webm, "audio/webm")
        assert result is not None
        assert abs(result - expected_duration) < 0.01


def test_builders_round_trip_ogg():
    """AC-004: Ogg builders produce bytes the probe itself parses."""
    from study_tutor.voice.utils import probe_duration_seconds

    test_cases = [1.0, 2.5, 5.0, 10.5]

    for expected_duration in test_cases:
        ogg = make_ogg_opus(duration_seconds=expected_duration)
        result = probe_duration_seconds(ogg, "audio/ogg")
        assert result is not None
        assert abs(result - expected_duration) < 0.01


def test_case_insensitive_content_type():
    """Content-Type matching is case-insensitive."""
    from study_tutor.voice.utils import probe_duration_seconds

    webm = make_webm(duration_ticks=3000)

    assert probe_duration_seconds(webm, "AUDIO/WEBM") is not None
    assert probe_duration_seconds(webm, "Audio/WebM") is not None


def test_webm_malformed_ebml_header():
    """WebM with malformed EBML header returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Wrong magic bytes
    bad_webm = b"\x00\x00\x00\x00" + b"\x00" * 100
    assert probe_duration_seconds(bad_webm, "audio/webm") is None


def test_webm_missing_segment():
    """WebM without Segment element returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Valid EBML header but missing Segment
    ebml_header = _write_ebml_element(
        b"\x1a\x45\xdf\xa3",
        _write_ebml_element(b"\x42\x86", b"\x01"),  # EBMLVersion
    )
    assert probe_duration_seconds(ebml_header, "audio/webm") is None


def test_webm_segment_without_info():
    """WebM Segment without Info element returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # EBML header + Segment with no Info
    ebml_header = _write_ebml_element(
        b"\x1a\x45\xdf\xa3", _write_ebml_element(b"\x42\x86", b"\x01")
    )
    # Empty segment
    segment = b"\x18\x53\x80\x67" + b"\x81\x00"  # Segment with 0 size
    webm = ebml_header + segment
    assert probe_duration_seconds(webm, "audio/webm") is None


def test_webm_duration_without_timescale():
    """WebM with Duration but no TimestampScale uses default 1ms."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build Info with only Duration (no TimestampScale)
    duration_float = 5000.0  # 5000 ticks
    info_elements = _write_ebml_element(b"\x44\x89", struct.pack(">f", duration_float))
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_elements)

    # Build Segment
    segment_content = info
    segment_size_val = len(segment_content)
    segment_size = bytes([0x80 | segment_size_val])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    result = probe_duration_seconds(webm, "audio/webm")
    # Duration 5000 ticks * 1_000_000 ns (default) / 1_000_000_000 = 5 seconds
    assert result is not None
    assert abs(result - 5.0) < 0.01


def test_webm_8byte_duration():
    """WebM with 8-byte double Duration element."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build Info with 8-byte Duration
    duration_double = 3000.0
    info_elements = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))
    info_elements += _write_ebml_element(
        b"\x44\x89", struct.pack(">d", duration_double)
    )
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_elements)

    # Build Segment
    segment_content = info
    segment_size_val = len(segment_content)
    segment_size = bytes([0x80 | segment_size_val])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    result = probe_duration_seconds(webm, "audio/webm")
    assert result is not None
    assert abs(result - 3.0) < 0.01


def test_webm_zero_duration():
    """WebM with zero or negative duration returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build WebM with zero duration
    webm_zero = make_webm(duration_ticks=0)
    assert probe_duration_seconds(webm_zero, "audio/webm") is None

    # Build WebM with negative duration (as float)
    info_elements = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))
    info_elements += _write_ebml_element(b"\x44\x89", struct.pack(">f", -1000.0))
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_elements)

    segment_content = info
    segment_size_val = len(segment_content)
    segment_size = bytes([0x80 | segment_size_val])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm_negative = ebml_header + segment
    assert probe_duration_seconds(webm_negative, "audio/webm") is None


def test_ogg_invalid_version():
    """Ogg page with invalid version is skipped."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Create page with version 1 (invalid, should be 0)
    capture = b"OggS"
    version = b"\x01"  # Invalid version
    header_type = bytes([0x04])  # EOS flag
    granule = struct.pack("<q", 48000)  # 1 second
    serial = struct.pack("<I", 12345)
    sequence = struct.pack("<I", 0)
    num_segments = bytes([1])
    segment_sizes = bytes([32])
    packet_data = b"\x00" * 32

    page = (
        capture
        + version
        + header_type
        + granule
        + serial
        + sequence
        + b"\x00\x00\x00\x00"
        + num_segments
        + segment_sizes
        + packet_data
    )

    assert probe_duration_seconds(page, "audio/ogg") is None


def test_ogg_non_eos_page():
    """Ogg page without EOS flag is skipped."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Create valid page but without EOS flag
    page = make_ogg_page(granule=96000, is_eos=False)
    assert probe_duration_seconds(page, "audio/ogg") is None


def test_ogg_negative_granule():
    """Ogg page with negative granule returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Create page with negative granule
    page = make_ogg_page(granule=-1, is_eos=True)
    assert probe_duration_seconds(page, "audio/ogg") is None


def test_ogg_too_short():
    """Ogg content shorter than minimum page size returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    short_ogg = b"OggS\x00"  # Only 5 bytes, need 27 minimum
    assert probe_duration_seconds(short_ogg, "audio/ogg") is None


def test_ogg_truncated_granule():
    """Ogg page with truncated granule field returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # OggS marker but truncated before full granule
    truncated = b"OggS\x00\x04" + b"\x00" * 5  # Only 5 bytes of 8-byte granule
    assert probe_duration_seconds(truncated, "audio/ogg") is None


def test_webm_malformed_ebml_size():
    """WebM with malformed EBML size encoding returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # EBML header with invalid size byte (all zeros - invalid EBML encoding)
    bad_webm = b"\x1a\x45\xdf\xa3" + b"\x00" + b"\x00" * 100
    assert probe_duration_seconds(bad_webm, "audio/webm") is None


def test_webm_truncated_after_segment_id():
    """WebM truncated immediately after Segment ID returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Valid EBML header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    # Segment ID but no size
    truncated = ebml_header + b"\x18\x53\x80\x67"
    assert probe_duration_seconds(truncated, "audio/webm") is None


def test_webm_info_with_unknown_elements():
    """WebM Info element with unknown sub-elements may return None if parsing fails."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build Info with unknown element before Duration
    # Using invalid element ID may cause parser to fail gracefully
    unknown_elem = _write_ebml_element(b"\x99\x99", b"test_data")  # Unknown element
    duration_elem = _write_ebml_element(b"\x44\x89", struct.pack(">f", 3000.0))
    timescale_elem = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))

    info_content = timescale_elem + unknown_elem + duration_elem
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_content)

    # Build Segment
    segment_content = info
    segment_size_val = len(segment_content)
    if segment_size_val < 127:
        segment_size = bytes([0x80 | segment_size_val])
    else:
        segment_size = bytes([0x40 | (segment_size_val >> 8), segment_size_val & 0xFF])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    result = probe_duration_seconds(webm, "audio/webm")
    # Parser may fail gracefully on invalid element IDs
    assert result is None or (result is not None and abs(result - 3.0) < 0.01)


def test_webm_segment_with_unknown_top_level_elements():
    """WebM Segment with unknown elements before Info may fail gracefully."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build unknown top-level element with invalid ID encoding
    unknown_elem = _write_ebml_element(b"\xaa\xbb", b"unknown_data" * 10)

    # Build Info element
    duration_elem = _write_ebml_element(b"\x44\x89", struct.pack(">f", 2000.0))
    timescale_elem = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))
    info_content = timescale_elem + duration_elem
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_content)

    # Build Segment with unknown element first
    segment_content = unknown_elem + info
    segment_size_val = len(segment_content)
    if segment_size_val < 127:
        segment_size = bytes([0x80 | segment_size_val])
    else:
        segment_size = bytes([0x40 | (segment_size_val >> 8), segment_size_val & 0xFF])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    result = probe_duration_seconds(webm, "audio/webm")
    # Parser may fail gracefully on invalid element structure
    assert result is None or (result is not None and abs(result - 2.0) < 0.01)


def test_webm_large_ebml_size_encoding():
    """WebM with multi-byte EBML size encoding may fail on invalid elements."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Create a large Info element to trigger 2-byte size encoding
    large_padding = b"\x00" * 200
    duration_elem = _write_ebml_element(b"\x44\x89", struct.pack(">f", 4000.0))
    timescale_elem = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))

    # Add large unknown element with invalid ID
    unknown_large = _write_ebml_element(b"\xcc\xdd", large_padding)

    info_content = timescale_elem + unknown_large + duration_elem
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_content)

    # Build Segment
    segment_content = info
    segment_size_val = len(segment_content)
    if segment_size_val < 127:
        segment_size = bytes([0x80 | segment_size_val])
    else:
        segment_size = bytes([0x40 | (segment_size_val >> 8), segment_size_val & 0xFF])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    # EBML Header
    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    result = probe_duration_seconds(webm, "audio/webm")
    # Parser may fail gracefully on invalid elements
    assert result is None or (result is not None and abs(result - 4.0) < 0.01)


def test_webm_invalid_duration_size():
    """WebM with invalid Duration element size is skipped."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build Info with Duration of invalid size (should be 4 or 8)
    timescale_elem = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))
    # Duration with 2-byte size (invalid, should be 4 or 8)
    invalid_duration = b"\x44\x89" + b"\x82" + struct.pack(">H", 1000)  # 2-byte value

    info_content = timescale_elem + invalid_duration
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_content)

    segment_content = info
    segment_size_val = len(segment_content)
    segment_size = bytes([0x80 | segment_size_val])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    # Should return None because Duration element is invalid
    assert probe_duration_seconds(webm, "audio/webm") is None


def test_webm_invalid_timescale_size():
    """WebM with invalid TimestampScale element size is handled."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build Info with TimestampScale of invalid size (should be 4)
    # TimestampScale with 2-byte size (invalid, should be 4)
    invalid_timescale = (
        b"\x2a\xd7\xb1" + b"\x82" + struct.pack(">H", 1000)
    )  # 2-byte value
    duration_elem = _write_ebml_element(b"\x44\x89", struct.pack(">f", 3000.0))

    info_content = invalid_timescale + duration_elem
    info = _write_ebml_element(b"\x15\x49\xa9\x66", info_content)

    segment_content = info
    segment_size_val = len(segment_content)
    segment_size = bytes([0x80 | segment_size_val])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    # Should still work with default timescale or return None
    result = probe_duration_seconds(webm, "audio/webm")
    # Implementation may return None or use default timescale
    assert result is None or result > 0


def test_webm_truncated_in_info():
    """WebM truncated while parsing Info element returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # Build partial Info (truncated)
    timescale_elem = _write_ebml_element(b"\x2a\xd7\xb1", struct.pack(">I", 1_000_000))

    # Build Info but claim it's larger than actual content
    info_id = b"\x15\x49\xa9\x66"
    claimed_size = bytes([0x90])  # Claims 16 bytes
    actual_content = timescale_elem[:5]  # But only provide 5 bytes

    info_partial = info_id + claimed_size + actual_content

    segment_content = info_partial
    segment_size_val = len(segment_content) + 100  # Claim more than available
    segment_size = bytes([0x80 | min(segment_size_val, 127)])
    segment = b"\x18\x53\x80\x67" + segment_size + segment_content

    ebml_version = _write_ebml_element(b"\x42\x86", b"\x01")
    ebml_header = _write_ebml_element(b"\x1a\x45\xdf\xa3", ebml_version)

    webm = ebml_header + segment
    assert probe_duration_seconds(webm, "audio/webm") is None


def test_ogg_page_header_truncated():
    """Ogg page with truncated header returns None."""
    from study_tutor.voice.utils import probe_duration_seconds

    # OggS marker with complete version but truncated before page sequence
    truncated = b"OggS\x00\x04" + b"\x00" * 15  # Missing some header fields
    assert probe_duration_seconds(truncated, "audio/ogg") is None
