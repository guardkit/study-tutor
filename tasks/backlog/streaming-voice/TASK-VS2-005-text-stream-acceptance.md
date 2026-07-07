---
id: TASK-VS2-005
title: "Text-stream acceptance suite — hermetic integration tests for every Tier-A scenario (Tier A closes here)"
task_type: testing
parent_review: TASK-REV-F732
feature_id: FEAT-VOICE-002
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VS2-004]
consumer_context:
  - task: TASK-VS2-004
    consumes: WS_FRAME_ENVELOPE
    framework: "Starlette TestClient websocket_connect"
    driver: "starlette / httpx"
    format_note: "frame types limited to contract §7 Rev 1 vocabulary; terminal errors close the socket, non-terminal refusals leave it open (ASSUM-003)"
---

## Description

Hermetic integration tests for every Tier-A (non-voice) scenario of
`features/streaming-voice/streaming-voice.feature`, using a fake
`respond_stream` and the existing fake-store test conventions — no real LLM,
no real network. New test module(s) under `tests/` mirroring
`study_tutor.http` / `study_tutor.session` / `study_tutor.tutoring` (confirm
exact sibling file names against the existing `tests/unit/` layout before
creating; may split happy-path/boundary vs negative/concurrency into two
files without changing task count).

**Test-isolation decision (explicit, from the review Risk Register):** new
tests either run `--concurrency=1` (the `/__dev__/reset` global-truncation
constraint, per the binding's global-reset note) or avoid global reset by
using a fresh `session_id` per test — pick one and document it in the test
module docstring.

Includes the retained-path regression: the non-streaming JSON `turn` endpoint
is re-verified unchanged.

## Acceptance Criteria

- [ ] One test per Tier-A scenario: typed streaming (first fragment before full answer; terminal done with history position), chunking boundaries (single-chunk short answer, pinned-size multi-chunk, straddling quote), quote correction + fail-closed verification, durability parity (streamed turn = plain turn in history; disconnect mid-stream; mid-generation failure leaves no exchange), async-Coach non-blocking, connection refusals (unauthenticated/forbidden/not-found/ended), flag-off absence, single-channel queueing, two-device ordering, cross-channel isolation, stall timeout
- [ ] Regression test: "Asking without streaming still returns the whole answer in one response" — existing HTTP `turn` route behaviour asserted unchanged
- [ ] All tests hermetic (fake `respond_stream`, fake store, no real LLM/network) and pass with `uv run pytest <new test paths> -x -q`
- [ ] Isolation strategy (fresh-session-per-test or `--concurrency=1`) chosen and documented in the module docstring

## BDD Scenarios Served

All Tier-A scenarios (see task list above), plus:
- "Asking without streaming still returns the whole answer in one response" (@regression)

## References

- `features/streaming-voice/streaming-voice.feature` (Tier-A scenarios) · spec summary "Acceptance" (streaming variants, `--concurrency=1` note) · TASK-STREAM-001 Scope 4 · `tests/unit/http/` layout conventions
