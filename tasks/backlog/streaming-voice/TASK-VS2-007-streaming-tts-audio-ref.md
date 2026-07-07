---
id: TASK-VS2-007
title: "Sentence-chunked TTS — audio_ref frames in seq order, chunk-store integration, mid-answer TTS degradation (Tier B)"
task_type: feature
parent_review: TASK-REV-F732
feature_id: FEAT-VOICE-002
wave: 6
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VS2-002, TASK-VS2-006]
external_dependencies: [TASK-VOX-002, TASK-VOX-005]
consumer_context:
  - task: TASK-VS2-002
    consumes: VERIFIED_CHUNK_ITERATOR
    framework: "pure async generator"
    driver: "python stdlib"
    format_note: "TTS is triggered per VERIFIED chunk only — a chunk's audio is synthesized only from text that passed the ADR-027 gate (corrected text, never the raw form)"
  - task: TASK-VOX-002
    consumes: AudioClient (synthesize)
    framework: "httpx async, injectable transport"
    driver: "httpx"
    format_note: "synthesize(text, response_format='wav') -> bytes; one /v1/audio/speech call per chunk; only VoiceUnavailable escapes"
  - task: TASK-VOX-005
    consumes: ChunkStore
    framework: "in-memory TTL store, asyncio-lock-guarded"
    driver: "python stdlib"
    format_note: "put(session_id, wav_bytes) -> chunk_id; get(session_id, chunk_id) -> bytes|None; url = /api/sessions/{session_id}/voice-audio/{chunk_id}; TTL ≤120s, capped, never disk — MUST be the same instance the HTTP voice_audio route reads; confirm exact put() signature when VOX-005 lands"
---

## Description

**Tier B — do not schedule before FEAT-VOICE-001 TASK-VOX-002 (AudioClient)
and TASK-VOX-005 (ChunkStore) are complete.** New module
`src/study_tutor/voice/streaming_tts.py` (or extend `ws_voice_turn.py` if
small — Coach's call at review).

For voice turns: after each sentence chunk passes verification (VS2-002/003's
gate), call `AudioClient.synthesize(chunk_text, response_format="wav")` — one
`/v1/audio/speech` call per chunk (design §5.3 pin) — then
`ChunkStore.put(session_id, wav_bytes)` on the **same store instance** the
HTTP `voice_audio` route (VOX-006) reads from, and emit
`{type:"audio_ref", seq, chunk_id, url}` frames in `seq` order. Chunks are
synthesized and announced in order; audio bytes never touch disk (design
§5.6 never-at-rest).

**ASSUM-006 (owner-confirmed, carries FEAT-VOICE-001 ASSUM-005 unchanged):**
`VoiceUnavailable` mid-answer skips all remaining `audio_ref` frames; token
frames continue to completion; the turn records normally.

Ownership/session-scoping of chunk fetches is VOX-005/006's logic — this task
mints **no** new fetch path; WS-announced chunks are fetched through the
existing `voice_audio` route and are therefore subject to its guards.

## Acceptance Criteria

- [ ] `audio_ref.seq` strictly increasing and gapless for a fully-succeeded turn; announced order matches chunk order
- [ ] Audio for a corrected/annotated sentence is synthesized only from the corrected text (verified-chunk input, never raw LLM text)
- [ ] Forced TTS failure after the first chunk: exactly one `audio_ref` frame, zero further `audio_ref` frames, token frames continue to `done`, turn recorded normally (ASSUM-006)
- [ ] Chunks fetched via the existing `voice_audio` route return playable `audio/wav` bytes in announced order; no new fetch route exists in this module
- [ ] No audio bytes written to disk or DB anywhere in the module (never-at-rest check, capturing log handler included)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "A spoken question streams a transcript, then answer text, then spoken sentences" (@smoke — spoken-chunk half)
- "Announced spoken chunks are playable and reproduce the answer in order"
- "Speech synthesis fails partway through a spoken answer"

## Seam Tests

```python
"""Seam test: verify CHUNK_STORE put/announce contract from TASK-VOX-005."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("CHUNK_STORE")
async def test_audio_ref_urls_resolve_via_shared_store(fake_audio_client, shared_chunk_store):
    """Contract: put(session_id, wav_bytes) -> chunk_id; announced url is
    /api/sessions/{sid}/voice-audio/{chunk_id}; the SAME instance serves the
    voice_audio route. Producer: TASK-VOX-005; consumer: this task.
    """
    refs = await stream_voice_answer(chunks=["First sentence.", "Second one."])
    assert [r["seq"] for r in refs] == [0, 1]
    for r in refs:
        assert shared_chunk_store.get(session_id, r["chunk_id"]) is not None
        assert r["url"] == f"/api/sessions/{session_id}/voice-audio/{r['chunk_id']}"
```

## References

- Contract §7 Rev 1 (`audio_ref {seq, chunk_id, url}`) · design §5.2/§5.3/§5.6 · ASSUM-006 · FEAT-VOICE-001 TASK-VOX-002/005 (AudioClient, ChunkStore) · review report §4 contracts table
