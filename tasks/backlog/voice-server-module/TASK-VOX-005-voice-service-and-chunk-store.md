---
id: TASK-VOX-005
title: "voice/service.py \u2014 voice-turn orchestration + in-memory TTL chunk store\
  \ (ASSUM-005 half-failure)"
task_type: feature
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-VOX-002
- TASK-VOX-004
consumer_context:
- task: TASK-VOX-002
  consumes: AudioClient
  framework: httpx async, injectable transport
  driver: httpx
  format_note: transcribe(bytes, filename=, content_type=) -> str (verbatim, may be
    whitespace); synthesize(text, response_format='wav') -> bytes; only VoiceUnavailable
    escapes
- task: TASK-VOX-004
  consumes: parse_voice_upload
  framework: Starlette Request stream parsing
  driver: python-multipart
  format_note: returns ValidatedUpload(bytes, filename, content_type) already validated
    in the pinned order; raises the six voice exceptions
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T13:11:43.866905'
  last_updated: '2026-07-08T13:23:14.680538'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-08T13:11:43.866905'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

`src/study_tutor/voice/service.py` — the non-streaming voice turn (design
§5.2, contract §5 Rev 1):

**`ChunkStore`** — in-memory only, never disk: `put(session_id, wav_bytes) ->
chunk_id` (opaque, unguessable — `secrets.token_urlsafe`), `get(session_id,
chunk_id) -> bytes | None` (None when expired/unknown/wrong-session), TTL
`config.chunk_ttl_seconds` (120 s) evicted on read + on put, hard cap on
entries (oldest-first eviction), asyncio-lock-guarded. Session-scoped keys so
another student's session can never fetch a chunk (spec: "Another student
cannot fetch my reply audio").

**`VoiceTurnService.voice_turn(session_id, student_id, request) ->
VoiceTurnResult{transcript, tutor_response, audio: [AudioRef(seq, chunk_id, url)]}`**:
1. `parse_voice_upload` (rejections propagate before anything else runs —
   spec: "no turn should be added").
2. `AudioClient.transcribe`; strip → empty ⇒ `UnintelligibleQuery` (no turn
   recorded). Discard the audio bytes reference immediately after (the
   ephemeral invariant — no retention on the service object, no logging of
   bytes).
3. Run the **unchanged** turn path with the transcript as `user_message` —
   the same `SessionService.turn()` + reply-factory seam the text handler
   uses (`http/app.py:283-292`); ownership/lifecycle errors propagate as-is.
4. `AudioClient.synthesize(tutor_response, response_format="wav")` → one
   chunk (MVP), `ChunkStore.put`, `url = /api/sessions/{sid}/voice-audio/{chunk_id}`.
5. **ASSUM-005 (owner-confirmed):** if step 4 raises `VoiceUnavailable`
   *after* step 3 committed the turn, return the result with `audio: []` and
   `spoken_unavailable: true` — NOT an error; the turn exists exactly once.
   (If STT (step 2) fails ⇒ `VoiceUnavailable` propagates and no turn exists.)

## Acceptance Criteria

- [ ] Full happy path returns transcript + tutor_response + one audio ref; transcript persisted via the standard turn path (two rows, verifiable through `SessionService`)
- [ ] Validation/UnintelligibleQuery/STT-down paths add **no** turn; TTS-down-after-turn returns text-only result with the turn recorded exactly once (ASSUM-005)
- [ ] ChunkStore: TTL expiry → `get` returns None; cap eviction oldest-first; wrong session → None; chunk_ids unguessable and collision-free across rapid turns
- [ ] No audio bytes at rest: no disk/DB writes of audio anywhere in the module; no audio bytes in log records (test with a capturing log handler)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify the validate-before-transcribe contract from TASK-VOX-004."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("parse_voice_upload")
async def test_rejection_precedes_stt(mock_audio_transport, service_with_oversized_upload):
    """Contract: parse_voice_upload raises before AudioClient is invoked.
    Producer: TASK-VOX-004; consumer: VoiceTurnService (this task)."""
    with pytest.raises(RecordingTooLarge):
        await service_with_oversized_upload.voice_turn(...)
    assert mock_audio_transport.stt_calls == 0
```

## References

- Design §5.2/§5.6 · contract §5 Rev 1 · spec ASSUM-004/005/006 + Groups A/C/D · `session/service.py:274-297` (the turn seam) · blueprint §3 exclusions (no narration cache/batch port)
