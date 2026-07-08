---
id: TASK-VS2-008
title: "Voice-channel acceptance suite — chunk ownership/scoping, long-answer availability, voice scenarios (Tier B)"
task_type: testing
parent_review: TASK-REV-F732
feature_id: FEAT-VOICE-002
wave: 7
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VS2-006, TASK-VS2-007]
external_dependencies: [TASK-VOX-005, TASK-VOX-006, TASK-VOX-007]
consumer_context:
  - task: TASK-VS2-004
    consumes: WS_FRAME_ENVELOPE
    framework: "Starlette TestClient websocket_connect"
    driver: "starlette / httpx"
    format_note: "voice frames per contract §7 Rev 1; non-terminal refusals leave the channel open"
---

## Description

**Tier B closer.** Integration tests for the remaining voice-only scenarios of
`features/streaming-voice/streaming-voice.feature`, using fake
AudioClient/ChunkStore test doubles matching VOX-007's BDD conventions. New
test module(s) under `tests/` mirroring `study_tutor.voice`.

Ownership/session-scoping of chunk fetches is VOX-006's route logic — these
tests verify **WS-announced** chunks are correctly subject to it (no parallel
unguarded fetch path was minted by FEAT-VOICE-002), not new production code.

ASSUM-010 (eviction never touches an unplayed, unexpired chunk of a
maximum-length answer) is VOX-005's eviction policy consumed here — hermetic
with a fake clock; this test cannot be written meaningfully until VOX-005
exists (part of why this task is wave-gated behind FEAT-VOICE-001).

Same isolation rule as TASK-VS2-005: fresh `session_id` per test or
`--concurrency=1`, documented in the module docstring.

## Acceptance Criteria

- [ ] Another student's fetch of an announced chunk is refused as forbidden; a fetch of the same chunk through the owner's *other* session is refused as not found (session-scoped references)
- [ ] Long-answer chunk availability: with a fake clock and a many-chunk answer, every announced chunk is still retrievable when fetched in announced order (ASSUM-010, hermetic)
- [ ] Full spoken-turn flow test: transcript → incremental tokens → in-order audio_refs → done, all frames per contract §7 Rev 1 vocabulary
- [ ] All tests hermetic (fake AudioClient/ChunkStore/clock, no real STT/TTS) and pass with `uv run pytest <new test paths> -x -q`
- [ ] Isolation strategy documented in the module docstring

## BDD Scenarios Served

- "Another student cannot fetch my announced spoken chunks"
- "An announced chunk reference is valid only within its own session"
- "A very long spoken answer does not lose chunks before they can be played"

## References

- `features/streaming-voice/streaming-voice.feature` (voice scenarios) · ASSUM-010 · FEAT-VOICE-001 TASK-VOX-005/006/007 · review report operator-handoff note (live long-answer run under real TTS pacing is an operator follow-up, not this suite)
