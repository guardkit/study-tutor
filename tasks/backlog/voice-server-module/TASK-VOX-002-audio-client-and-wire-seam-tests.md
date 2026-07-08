---
id: TASK-VOX-002
title: "voice/client.py \u2014 AudioClient with injectable transport + the multipart\
  \ wire-seam pins"
task_type: feature
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-VOX-001
consumer_context:
- task: TASK-VOX-001
  consumes: VoiceConfig
  framework: frozen dataclass, boot-time from_env
  driver: stdlib dataclasses
  format_note: stt_base_url/tts_base_url end in /v1; audio_timeout_seconds=10.0 governs
    every call
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T12:57:05.315290'
  last_updated: '2026-07-08T13:11:14.218321'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Test collection failed for tests/unit/voice/test_validation.py -
      pytest cannot collect tests from this file. Error: ''ERROR collecting tests/unit/voice/test_validation.''
      This indicates a syntax error, import error, or structural problem that prevents
      the file from being parsed.: Debug tests/unit/voice/test_validation.py to identify
      and fix the syntax/import error preventing test collection. Run pytest -v tests/unit/voice/test_validation.py
      in isolation to see the specific error. Verify all imports are valid and the
      file structure matches pytest conventions.

      - Evidence gathering aborted with status ''partial_gate_abort'' - the orchestrator''s
      test run failed before completing, resulting in tests_passed: false and null
      coverage data. This means no independent verification of the implementation
      is available.: Fix the test collection error in test_validation.py first. Once
      that file can be collected successfully, the full test suite should run and
      produce coverage data for verification.'
    timestamp: '2026-07-08T12:57:05.315290'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-07-08T13:01:54.674064'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

Port the LPA `AudioClient` (`lpa-platform-poc/src/voice/clients/audio.py`)
into `src/study_tutor/voice/client.py` — near-verbatim; it is
provider-agnostic OpenAI-audio with no framework coupling:

- `__init__(config: VoiceConfig, *, transport: httpx.AsyncBaseTransport | None = None)`
  — **the injectable transport is THE test seam**.
- `async transcribe(audio: bytes, *, filename: str, content_type: str) -> str`
  — POST `{stt_base_url}/audio/transcriptions`, multipart
  `files={"file": (filename, audio, content_type)}`, `data={"model": stt_model}`;
  returns `response.json()["text"]` verbatim (may be empty/whitespace — the
  caller decides `UnintelligibleQuery`).
- `async synthesize(text: str, *, response_format: str = "wav") -> bytes`
  — POST JSON `{model, voice, input, response_format}` to
  `{tts_base_url}/audio/speech`; returns raw bytes.
- Fresh `httpx.AsyncClient(transport=…, timeout=Timeout(config.audio_timeout_seconds))`
  per call; **every** `httpx.HTTPStatusError | RequestError | TimeoutException`
  collapses to `raise VoiceUnavailable(...) from exc` — no httpx exception escapes.

Tests (`tests/unit/voice/test_audio_client.py`) port the LPA's
`MockAudioTransport` pattern (subclass `httpx.MockTransport`: `set_transcript`,
`set_synth_bytes`, `simulate_stt_down/tts_down/total_unavailability`, request
capture) and **pin the wire contract on the raw captured request** — the
"green but broken" defence:

- STT request: path ends `/audio/transcriptions`; `content-type` starts
  `multipart/form-data`; raw body contains `name="file"`, the exact filename,
  the full content-type **with codec parameters intact**
  (e.g. `audio/ogg;codecs=opus`), the audio bytes unchanged, `name="model"` +
  the configured model value.
- TTS request: JSON body fields `model`, `voice` (=`Ryan` from config),
  `input`, `response_format`.
- 503/timeout on either leg → `VoiceUnavailable`; whitespace-only transcript
  is returned, not raised.

## Acceptance Criteria

- [ ] Signatures and behaviour above; no disk I/O (bytes in/bytes out)
- [ ] Wire-seam pins assert on the captured raw request body, not just "was called"
- [ ] Both failure legs collapse to `VoiceUnavailable`; timeout honoured at 10 s
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify AudioClient STT multipart contract (consumed by TASK-VOX-005)."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("audio_stt_multipart")
async def test_stt_multipart_wire_shape(mock_audio_transport, voice_config):
    """Contract: multipart field 'file' with (filename, bytes, full content-type
    incl. codec params) + 'model' field. Producer: TASK-VOX-002; consumers: GB10
    /v1/audio/transcriptions (live) and VoiceTurnService (TASK-VOX-005)."""
    client = AudioClient(voice_config, transport=mock_audio_transport)
    await client.transcribe(b"xx", filename="q.ogg", content_type="audio/ogg;codecs=opus")
    body = mock_audio_transport.last_request_body
    assert b'name="file"' in body and b'filename="q.ogg"' in body
    assert b"audio/ogg;codecs=opus" in body and b'name="model"' in body
```

## References

- Design §5.1 (client row) · blueprint §3/§7 · `lpa-platform-poc/src/voice/clients/audio.py` + `tests/voice/test_audio_client.py` + `tests/integration/test_voice_integration.py:263-304` (the pinned multipart assert)
