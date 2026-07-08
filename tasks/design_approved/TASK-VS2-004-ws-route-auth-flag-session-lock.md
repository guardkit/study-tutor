---
complexity: 7
consumer_context:
- consumes: RUN_TURN_STREAM
  driver: python stdlib
  format_note: async def run_turn_stream(session_state, learner_message) -> AsyncIterator[TurnEvent];
    reuses _apply_coach_handover/_dispatch_async_coach internally — no duplicate Coach
    dispatch
  framework: asyncio async generator
  task: TASK-VS2-003
- consumes: TURN_EVENT_SHAPE
  driver: uvicorn[standard] / websockets
  format_note: TurnEvent members serialize byte-identically to contract §7 Rev 1 frame
    table; error frames are {type:'error', error, error_type} closed-set envelope
  framework: Starlette WebSocket JSON frames
  task: TASK-VS2-003
dependencies:
- TASK-VS2-003
feature_id: FEAT-VOICE-002
id: TASK-VS2-004
implementation_mode: task-work
parent_review: TASK-REV-F732
status: design_approved
task_type: feature
title: WS live channel — WebSocketRoute, auth-at-upgrade, voice-flag gating, per-session
  ordering lock, uvicorn[standard]
wave: 3
---

## Description

New `WebSocketRoute` `GET /api/sessions/{session_id}/ws` (binding §2.1 Rev 1)
in new module `src/study_tutor/http/ws.py`, registered in `http/app.py`
(currently `Route`-only). Mounted **only** when `STUDY_TUTOR_VOICE_ENABLED`
(ASSUM-002 — same conditional-route pattern as `/__dev__/reset`); flag-off
looks like the channel never existed while plain tutoring is unaffected.

**Auth at upgrade** via the existing, unmodified
`resolve_student_from_token` (`http/auth.py`) on the `Authorization` header;
ownership via the existing `SessionService` owned-session guard. Domain errors
surface as `{type:"error", error, error_type}` frames (closed-set envelope,
contract §9), then close for the **terminal** class — unauthenticated,
forbidden, not-found, session-ended (ASSUM-003 terminal half; the non-terminal
half lands in TASK-VS2-006).

**Per-session ordering lock (ASSUM-008 — new machinery, flag for Coach
architectural review):** a per-`session_id` serialization lock (not merely
per-connection) so a second `{type:"turn"}` frame arriving while a turn
streams — on the same connection or a second device's connection — is queued
and processed strictly in arrival order, never interleaved, never rejected.

**Server dep:** plain `uvicorn` rejects WS upgrades — add `uvicorn[standard]`
(or explicit `websockets`) to `pyproject.toml` (currently `uvicorn>=0.27`).
Note: must not be paired with a multi-worker deploy — the in-memory chunk
store assumption (design §5.2) rides the single-worker uvicorn deploy.

## Acceptance Criteria

- [ ] Flag-off: WS upgrade refused as if the route never existed (matching the conditional-route pattern's flag-off outcome); a plain non-streamed `turn` on the same session still succeeds
- [ ] Missing/invalid token refused as unauthenticated with zero frames delivered before close; another student's connect refused as forbidden; unknown session → not found; ended session → session-ended (terminal class: error frame then close, ASSUM-003)
- [ ] Two `{type:"turn"}` sends while a turn is streaming — same connection AND two connections on the same session_id — are answered strictly in arrival order with no frame interleaving (per-session lock test)
- [ ] Two different students/sessions streaming concurrently each receive only their own frames (no cross-session leakage)
- [ ] `pyproject.toml` gains `uvicorn[standard]` (or `websockets`); dependency resolves and app boots
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "Opening the live channel without valid credentials is refused"
- "Another student cannot open my session's live channel"
- "Streaming a turn on an ended session is refused"
- "The live channel for an unknown session is refused as not found"
- "With the voice feature disabled, the live channel is absent and plain tutoring is unaffected"
- "A second question sent while an answer is still streaming"
- "Questions from two of my devices on the same session are answered one at a time"
- "Two students streaming at the same time see only their own answers"

## Seam Tests

```python
"""Seam test: verify TURN_EVENT_SHAPE / WS_FRAME_ENVELOPE over the socket."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("WS_FRAME_ENVELOPE")
def test_ws_frames_match_frozen_vocabulary(test_client):
    """Contract: every frame sent on the channel uses exactly the contract §7
    Rev 1 types; terminal errors close the socket, per binding §2.1.
    Producer: this task; consumers: TASK-VS2-005/006/007/008.
    """
    with test_client.websocket_connect(ws_url, headers=auth) as ws:
        ws.send_json({"type": "turn", "text": "q", "stream": True})
        frames = drain(ws)
    assert {f["type"] for f in frames} <= {"token", "done", "transcript", "audio_ref", "error"}
    assert frames[-1]["type"] == "done"
```

## References

- Binding §2.1 Rev 1 (`BINDING_SHA=e50897d1…`, terminal-vs-non-terminal close) · contract §9 error set · ASSUM-002/003/008 · `http/app.py` (Route-only table, `/__dev__/reset` pattern) · `http/auth.py` (`resolve_student_from_token`) · review report Material Finding 3 · auth-touching ⇒ FULL_REQUIRED human checkpoint regardless of score