---
id: TASK-VOX-001
title: "voice/config.py + voice/errors.py \u2014 frozen config dataclass and the six\
  \ voice exceptions"
task_type: declarative
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T12:15:36.624127'
  last_updated: '2026-07-08T12:22:22.920862'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-08T12:15:36.624127'
    player_summary: Implemented VoiceConfig as a frozen dataclass with from_env()
      classmethod that mirrors HTTPAuthConfig pattern. Created six exception classes
      (VoiceError base + RecordingTooLarge, QueryTooLong, UnsupportedAudioFormat,
      EmptyRecording, UnintelligibleQuery, VoiceUnavailable) with specified constructors
      and messages. All exceptions are plain Python exceptions, not HTTP types. UnsupportedAudioFormat
      includes sorted supported types in error message. Boolean parsing uses _parse_bool_flag
      function with c
    player_success: true
    coach_success: true
---

## Description

Create `src/study_tutor/voice/` with the two declarative modules everything
else consumes.

**`voice/config.py`** — frozen dataclass `VoiceConfig` with classmethod
`from_env()`, mirroring `HTTPAuthConfig.from_env` (`src/study_tutor/http/auth.py:42-107`):
boot-time snapshot, clear `ValueError` messages, no import-time env reads.

| Field | Env var | Default |
|---|---|---|
| `enabled` | `STUDY_TUTOR_VOICE_ENABLED` | `False` (parse like `_parse_bool_flag`, auth.py:110) |
| `stt_base_url` | `STT_BASE_URL` | `http://promaxgb10-41b1:9000/v1` |
| `stt_model` | `STT_MODEL` | `parakeet-tdt` |
| `tts_base_url` | `TTS_BASE_URL` | `http://promaxgb10-41b1:9000/v1` |
| `tts_model` | `TTS_MODEL` | `qwen3-tts` |
| `tts_voice` | `TTS_VOICE` | `Ryan` |
| `audio_timeout_seconds` | — (constant) | `10.0` (spec ASSUM-006) |
| `max_query_seconds` | — (constant) | `60` (contract §5 Rev 1) |
| `max_recording_bytes` | — (constant) | `10 * 1024 * 1024` (contract §5 Rev 1) |
| `chunk_ttl_seconds` | — (constant) | `120` (spec ASSUM-004) |
| `supported_base_mimetypes` | — (constant set) | `{audio/mp4, audio/m4a, audio/aac, audio/ogg, audio/webm, audio/wav, audio/mpeg}` (spec ASSUM-003) |

Env names `STT_*`/`TTS_*` are the fleet convention (lpa-platform-poc uses the
same names; blueprint §refs TASK-VOICE-011 prerequisites).

**`voice/errors.py`** — plain exception hierarchy (do **not** subclass any
HTTP exception; mapping to status codes happens per-handler in TASK-VOX-006):
`VoiceError` base; `RecordingTooLarge(max_bytes)`, `QueryTooLong(max_seconds)`,
`UnsupportedAudioFormat(received_mimetype, supported)` (message names the
received type and lists the supported set), `EmptyRecording()`,
`UnintelligibleQuery()`, `VoiceUnavailable(message="Voice services are temporarily unavailable")`.
Class names ARE the wire `error_type` values (contract §9 Rev 1).

## Acceptance Criteria

- [ ] `VoiceConfig.from_env()` returns a frozen instance; defaults above; malformed boolean raises `ValueError` naming the variable
- [ ] No `os.environ` access at import time (SR-03 discipline)
- [ ] Six exception classes exist with the constructors/messages above; none subclass Starlette/HTTP types
- [ ] Unit tests cover: default construction, env overrides, bad-flag error, exception messages (UnsupportedAudioFormat names received type + sorted supported set)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## References

- Design §5.1 (config + errors rows) · contract §9 Rev 1 · `lpa-platform-poc/src/voice/{config.py,exceptions.py}` (shape source; do not port pydantic-settings or HTTPException)
