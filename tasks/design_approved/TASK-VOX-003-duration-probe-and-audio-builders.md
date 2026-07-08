---
complexity: 4
dependencies: []
feature_id: FEAT-VOICE-001
id: TASK-VOX-003
implementation_mode: task-work
parent_review: TASK-REV-852B
status: design_approved
task_type: feature
title: voice/utils.py — stdlib WebM/Ogg duration probe + synthetic audio builders
  for tests
wave: 1
---

## Description

Port the LPA's stdlib duration probe (`lpa-platform-poc/src/voice/utils.py`)
verbatim-in-shape into `src/study_tutor/voice/utils.py`:

- `probe_duration_seconds(content: bytes, content_type: str) -> float | None`
  — dispatch on lowercased base MIME (strip `;codecs…`); `audio/webm` → EBML
  walk (first 64 KiB, magic check, unknown-size streamed Segment handled,
  `TimestampScale` default 1_000_000, 4/8-byte float Duration);
  `audio/ogg` → backwards `OggS` scan, page-structure validation, signed LE
  granule ≥ 0, `granule / 48_000`; anything else → `None`. **Never raises**
  on malformed input. m4a/MP4 returns `None` (byte cap + client stop govern —
  design §5.1; do not add an MP4 probe unless trivial).

- Test-support builders in `tests/unit/voice/audio_samples.py` (port of the
  LPA's `tests/voice/audio_samples.py`): `make_webm(duration_ticks, timescale_ns=None,
  streamed_segment=False)`, `make_ogg_page(granule, …)`, `make_ogg_opus(duration_seconds)`.
  These are consumed by TASK-VOX-004's boundary tests.

## Acceptance Criteria

- [ ] WebM with Duration element → correct seconds; Chrome-style streamed WebM (no Duration) → `None`
- [ ] Ogg/Opus EOS granule → `granule/48000`; header-page granule 0 → `None`; false-sync `OggS` bytes skipped
- [ ] Unknown/absent content types and truncated/garbage bytes → `None`, never an exception
- [ ] Builders produce bytes the probe itself parses (round-trip tests)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## References

- Design §5.1 (utils row) · `lpa-platform-poc/src/voice/utils.py` + `tests/voice/audio_samples.py` · blueprint §3