---
complexity: 8
consumer_context:
- consumes: GENERATE_STREAM
  driver: httpx
  format_note: AsyncIterator[str] of delta tokens in SSE source order, terminates
    on [DONE]; read-timeout (not total-deadline) semantics per ASSUM-009
  framework: httpx AsyncClient SSE streaming
  task: TASK-VS2-001
- consumes: VERIFIED_CHUNK_ITERATOR
  driver: python stdlib
  format_note: 'yields (chunk_text: str, seq: int) per VERIFIED chunk only, seq strictly
    increasing; raises (fail-closed) on verifier_exception=True'
  framework: pure async generator
  task: TASK-VS2-002
dependencies:
- TASK-VS2-001
- TASK-VS2-002
feature_id: FEAT-VOICE-002
id: TASK-VS2-003
implementation_mode: task-work
parent_review: TASK-REV-F732
status: design_approved
task_type: feature
title: SessionService.turn_stream + TurnEvent widening + PlayerCoachOrchestrator.run_turn_stream
  (durability, async Coach)
wave: 2
---

## Description

Implement `SessionService.turn_stream` from its stub
(`session/service.py:299`, currently `NotImplementedError`) and widen
`TurnEvent` (`service.py:163`) from `Literal["token","done"]` to add
`"transcript"`, `"audio_ref"`, `"error"` members plus `seq`/`chunk_id`/`url`
fields — the **already-frozen §8 shape**; no members or fields beyond contract
§7 Rev 1. `ReplyStreamFn` stays a plain token-string iterator; voice frames
are emitted by the voice layer around it (design §5.2).

Add `PlayerCoachOrchestrator.run_turn_stream(...)`
(`tutoring/orchestrator.py`) **reusing** the existing private helpers
(`_apply_coach_handover`, `_dispatch_async_coach`) — no duplicate
Coach-dispatch path: drive `respond_stream` (VS2-001) through the sentence
chunker (VS2-002), yield a `token` TurnEvent per verified chunk; on completion
persist the assembled full answer via the same `store.append_turn` path
`turn()` uses (`service.py:274`), then dispatch the async Coach against the
full text exactly like the sync path (ADR-ARCH-026 D1 — streaming never waits
for the quality review).

**ASSUM-004:** generation failure mid-stream persists no tutor row and yields
an `error` TurnEvent instead of `done` — no partial text persists as a
completed exchange; the student can retry.

**ASSUM-005 (load-bearing):** on client disconnect the
generation/persistence/Coach-dispatch coroutine must NOT be cancelled by the
WS handler's cancellation scope — it runs to completion detached from the
socket's lifetime, so resume shows the full exchange.

## Acceptance Criteria

- [ ] `TurnEvent` JSON serialization key set matches the contract §7 Rev 1 frame table verbatim for every member (`token`/`done` unchanged; `transcript`, `audio_ref {seq, chunk_id, url}`, `error {error, error_type}` added) — no extra/renamed fields (grep/serialization test against the frozen table)
- [ ] Forced mid-generation failure yields an `error` event; a subsequent resume/status call shows no tutor row for that turn (ASSUM-004, existing store fakes)
- [ ] Cancelling the consuming task mid-stream (simulating WS disconnect) still completes and persists the turn (ASSUM-005 detachment test)
- [ ] Coach dispatch after stream completion is asserted via the same mechanism already tested for `run_turn`'s async mode; first token yields before any Coach evaluation runs (ADR-ARCH-026)
- [ ] Completed streamed turn appears in session history identically to a plain turn (two rows via `store.append_turn`, same shape)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "A streamed turn is recorded in the session history exactly like a plain turn"
- "Streaming never waits for the tutor's quality review"
- "Answer generation fails partway through streaming"
- "My connection drops while an answer is streaming"

## Seam Tests

```python
"""Seam test: verify GENERATE_STREAM consumption + persistence ordering."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("GENERATE_STREAM")
async def test_turn_stream_persistence_ordering(fake_store):
    """Contract: append user turn -> stream verified chunks -> append tutor
    turn -> dispatch Coach. Producer: TASK-VS2-001/002; consumer: this task.
    """
    events = [e async for e in service.turn_stream(sid, student, "q")]
    assert events[-1].type == "done"
    assert fake_store.calls == ["append_turn(user)", "append_turn(tutor)"]
    assert fake_coach.dispatched_after_stream_complete


@pytest.mark.seam
@pytest.mark.integration_contract("TURN_EVENT_SHAPE")
def test_turn_event_serialization_matches_contract_rev1():
    """Contract: byte-identical key sets vs contract §7 Rev 1 frame table.
    Producer: this task; consumers: TASK-VS2-004/006/007.
    """
    assert serialized_keys(audio_ref_event) == {"type", "seq", "chunk_id", "url"}
    assert serialized_keys(error_event) == {"type", "error", "error_type"}
```

## References

- Contract §7 Rev 1 (frame vocabulary, byte-frozen; `CONTRACT_SHA=574615e9…`) · design §5.2/§8 · ADR-ARCH-026 D1 · ASSUM-004/005 · `session/service.py:163,274,299` · `tutoring/orchestrator.py:534-549` (`_dispatch_async_coach`) · review report Material Finding 1