---
id: TASK-VOX-004
title: "voice/validation.py \u2014 in-memory multipart parse + order-pinned upload\
  \ validation"
task_type: feature
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 2
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-VOX-001
- TASK-VOX-003
consumer_context:
- task: TASK-VOX-001
  consumes: VoiceConfig
  framework: frozen dataclass
  driver: stdlib dataclasses
  format_note: max_recording_bytes=10MB, max_query_seconds=60, supported_base_mimetypes
    set
- task: TASK-VOX-003
  consumes: probe_duration_seconds
  framework: pure function
  driver: stdlib
  format_note: "returns float | None; None means duration not derivable \u2014 only\
    \ the byte cap applies"
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T12:57:05.315102'
  last_updated: '2026-07-08T13:11:20.491564'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-08T12:57:05.315102'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

`src/study_tutor/voice/validation.py`:

**In-memory multipart parsing — the never-at-rest invariant.**
`async parse_voice_upload(request: Request, config: VoiceConfig) -> ValidatedUpload`
(bytes + filename + content_type). **Never call `await request.form()`** —
Starlette spools file parts >1 MB to a disk-backed `SpooledTemporaryFile`
(`starlette/formparsers.py`, `spool_max_size = 1MB`), which violates the
no-audio-at-rest invariant (design §5.6, spec scenario "No recording audio is
ever kept"). Instead stream-parse with `python-multipart`'s push parser over
`request.stream()`, accumulating the `audio` field into memory and **enforcing
`max_recording_bytes` during the read** — an over-cap body is rejected as
`RecordingTooLarge` even when its headers declare a smaller size, and the read
stops there (never buffer more than cap+1 bytes).

Add **`python-multipart` as a direct dependency** in `pyproject.toml` (today
it is transitive via `mcp`; house precedent: the starlette/uvicorn direct-pin
comment at `pyproject.toml:20-24`).

**Order-pinned validation** (after the field is assembled), raising the
TASK-VOX-001 exceptions:
1. size (`RecordingTooLarge`) → 2. empty (`EmptyRecording`) →
3. base-MIME (`UnsupportedAudioFormat` — strip `;codecs…`, strip whitespace,
lowercase; message echoes the received type) →
4. best-effort duration via `probe_duration_seconds` (`QueryTooLong` only when
derivable and over 60 s).

The LPA never test-pinned this order — **add an order-pinning test here**
(design §5.1): a payload violating multiple rules reports the earliest one.

## Acceptance Criteria

- [ ] `request.form()` absent from the module; a test patches `tempfile.SpooledTemporaryFile` to raise and the parse path still succeeds (proves no spooling)
- [ ] Over-cap body with lying Content-Length/declared size → `RecordingTooLarge` (spec scenario "claims to be smaller")
- [ ] Missing `audio` field → validation error (maps to the 400 transport posture in TASK-VOX-006)
- [ ] 7-way MIME-variant matrix passes: `audio/ogg`, `audio/ogg;codecs=opus`, `audio/ogg; codecs=opus`, `audio/ogg;codecs="opus"`, `AUDIO/OGG`, `audio/mp4`, `audio/webm;codecs=opus`; unsupported types rejected naming the received value
- [ ] Order-pinning test green; duration boundaries (exactly 60 s pass / just over fail) via TASK-VOX-003 builders; duration-less streamed WebM passes (byte cap only)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## References

- Design §5.1 (validation row) + §5.6 · spec Group B/C + "true size" scenario · `lpa-platform-poc/src/voice/router.py:71-128` (order source) + `tests/voice/test_router.py:199-222` (MIME matrix)
