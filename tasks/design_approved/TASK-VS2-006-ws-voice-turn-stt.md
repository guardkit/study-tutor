---
complexity: 7
consumer_context:
- consumes: WS_FRAME_ENVELOPE
  driver: uvicorn[standard] / websockets
  format_note: voice_turn = {type:'voice_turn', content_type, size_bytes} header frame
    + exactly one binary frame; refusals use the closed-set error envelope; validation
    refusals are NON-terminal (channel stays open, ASSUM-003)
  framework: Starlette WebSocket
  task: TASK-VS2-004
- consumes: validation core (bytes-blob entry point)
  driver: python stdlib / python-multipart (HTTP side only)
  format_note: size→empty→base-MIME→duration pinned order against bytes ACTUALLY received;
    requires the FEAT-VOICE-001 scope note extracting a validate_audio_bytes(data,
    content_type)-shaped core from parse_voice_upload — do NOT write a second validator
    here
  framework: pure validation functions + six voice exception classes
  task: TASK-VOX-004
- consumes: AudioClient (transcribe)
  driver: httpx
  format_note: transcribe(bytes, filename=, content_type=) -> str (verbatim, may be
    whitespace); only VoiceUnavailable escapes
  framework: httpx async, injectable transport
  task: TASK-VOX-002
- consumes: RUN_TURN_STREAM
  driver: python stdlib
  format_note: voice variant feeds the transcript in as learner_message; token/done
    frames come from the same iterator the typed path uses
  framework: asyncio async generator
  task: TASK-VS2-003
dependencies:
- TASK-VS2-004
- TASK-VS2-005
external_dependencies:
- TASK-VOX-001
- TASK-VOX-002
- TASK-VOX-003
- TASK-VOX-004
feature_id: FEAT-VOICE-002
id: TASK-VS2-006
implementation_mode: task-work
parent_review: TASK-REV-F732
status: design_approved
task_type: feature
title: WS voice_turn frame handling — STT ingestion, validation-core reuse, transcript-first
  ordering (Tier B)
wave: 5
---

## Description

**Tier B — do not schedule before FEAT-VOICE-001 TASK-VOX-001/002/003/004 are
complete** (voice config + six errors, AudioClient, duration probe, validation
core). New module `src/study_tutor/voice/ws_voice_turn.py`.

Handle the client's `{type:"voice_turn", content_type, size_bytes}` header
frame followed by exactly one binary WS message (contract §7 Rev 1):

1. **Validate** the received byte blob with the **same** validation order and
   exception classes VOX-004 establishes (size → empty → base-MIME →
   duration), enforced against bytes **actually received**, not the declared
   `size_bytes` header. Refusal parity with the plain HTTP `voice_turn` is the
   spec's whole point here — reuse, never reimplement. Refusals are
   **non-terminal** (error frame, channel stays open for immediate retry —
   ASSUM-003's non-terminal half), as is `VoiceUnavailable` when speech
   services are down (typed streaming on the same channel keeps working).
2. **Transcribe** via `AudioClient.transcribe` (VOX-002); emit
   `{type:"transcript", text}` **before any other turn frame**; discard audio
   bytes immediately (never-at-rest invariant, design §5.6).
3. **Stream the answer** by feeding the transcript into `run_turn_stream`
   (VS2-003) — token/done frames identical to the typed path; transcript
   persisted via the standard turn path.

**Coordination note (review Material Finding 2):** VOX-004's
`parse_voice_upload` is scoped for Starlette's HTTP `request.stream()`
multipart. This task needs its per-check core callable on a plain bytes blob —
resolved as a small extraction inside FEAT-VOICE-001 (shared
`validate_audio_bytes`-shaped function both callers use). If that entry point
is missing when this task starts, raise it against TASK-VOX-004; writing a
second validator here is the refusal-parity drift the review's Option 3
rejected.

## Acceptance Criteria

- [ ] `transcript` frame observed strictly before the first `token` frame (frame-order test)
- [ ] Validation refusals map to the correct contract §9 `error_type`, are non-terminal, and a follow-up question on the same channel succeeds (ASSUM-003)
- [ ] Recording exactly at the size cap accepted; one byte over refused with the identical `error_type` a plain `voice_turn` gives, channel stays usable
- [ ] Recording with more bytes actually sent than declared is judged on bytes received
- [ ] Speech services down: `voice_turn` refused as unavailable (non-terminal); a typed streamed question on the same channel still succeeds
- [ ] Validation calls resolve to the shared VOX-004 core (seam test asserts the shared function is invoked — no second validator in this module)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "A spoken question streams a transcript, then answer text, then spoken sentences" (@smoke — transcript/text half)
- "A recording at exactly the size cap is accepted over the live channel"
- "A recording just over the size cap is refused and the channel stays usable"
- "Invalid recordings over the live channel are refused for the same reasons as a plain voice turn" (outline, 3 examples)
- "A recording larger than its declared size is judged on what was actually sent"
- "When speech services are down, voice is refused but typed streaming still works"

## Seam Tests

```python
"""Seam test: verify validation-core reuse (no-duplication check)."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("VOX_VALIDATION_CORE")
async def test_ws_voice_turn_calls_shared_validation_core(monkeypatch, ws_session):
    """Contract: the WS path calls the same VOX-004 validation core the HTTP
    voice_turn uses (size→empty→MIME→duration on bytes actually received).
    Producer: TASK-VOX-004; consumer: this task.
    """
    calls = spy_on_shared_core(monkeypatch)
    await send_voice_turn(ws_session, oversized_blob)
    assert calls, "WS path must invoke the shared validation core, not a local copy"


@pytest.mark.seam
@pytest.mark.integration_contract("AUDIO_STT_SEAM")
async def test_transcript_frame_precedes_tokens(ws_session, fake_audio_client):
    """Contract: {type:'transcript'} emitted before any token frame."""
    frames = await send_voice_turn(ws_session, valid_wav_blob)
    types = [f["type"] for f in frames]
    assert types.index("transcript") < types.index("token")
```

## References

- Contract §7 Rev 1 (`voice_turn` header + one binary frame) · §9 error set · ASSUM-003 (non-terminal half) · design §5.6 (never-at-rest) · FEAT-VOICE-001 TASK-VOX-002/004 · review report Material Finding 2 · spec summary "Not covered here" (refusal *parity* asserted, caps themselves specced in FEAT-VOICE-001)