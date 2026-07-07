# Feature Spec Summary: Streaming tutoring turns — live text and voice (FEAT-VOICE-002)

**Stack**: python (Starlette HTTP adapter, WS transport)
**Generated**: 2026-07-06T20:32:40+01:00
**Scenarios**: 31 total (3 smoke, 1 regression)
**Assumptions**: 10 total (1 high / 3 medium / 6 low confidence — all owner-confirmed 2026-07-06)
**Review required**: No (every assumption, including all six low-confidence items, was owner-confirmed at Phase 5)

## Scope

The streaming path of the frozen contract (Rev 1, §7 frames): the live session
channel carrying typed streamed turns (TASK-STREAM-001) and spoken turns
(transcript first, incremental answer text, spoken sentence chunks announced
as ready, terminal completion), with chunk-by-URL audio delivery, sentence-
chunked TTS at the design's ~15–25-word pin, and chunk-boundary quote
verification per ADR-ARCH-027 (including the straddling-quote obligation and
a fail-closed posture on verification failure). Covers connection-time auth /
ownership / lifecycle refusals, degradation (speech down → typed streaming
unaffected), durability parity with plain turns (including disconnect
mid-stream and mid-generation failure), single-channel and cross-channel
concurrency, chunk-store pressure, and the retained whole-answer path for
non-streaming clients.

Not covered here (other features): the non-streaming HTTP `voice_turn` and its
upload-validation boundary pairs (FEAT-VOICE-001, `features/voice-server-module/`
— this spec asserts refusal *parity* on the channel, not the caps themselves),
the Flutter client (FEAT-VOICE-003), Reachy (FEAT-VOICE-004).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 7 |
| Boundary conditions (@boundary) | 5 |
| Negative cases (@negative) | 11 (incl. overlaps with boundary/edge) |
| Edge cases (@edge-case) | 12 |

(Tag overlaps mean columns sum past 31. The Group C outline counts as 1 scenario with 3 examples.)

## Deferred Items

None — all four groups accepted as proposed; all six expansion scenarios included.

## Open Assumptions (low confidence)

None outstanding — all ten were owner-confirmed at Phase 5 (2026-07-06). The
consequential ones to keep visible during planning:

- **ASSUM-002** (medium): the WS live channel is flag-gated with the voice
  routes — typed token streaming requires `STUDY_TUTOR_VOICE_ENABLED`.
- **ASSUM-003**: validation refusals are non-terminal (channel survives);
  auth/ownership/lifecycle errors are terminal (error frame, then close).
- **ASSUM-005**: on client disconnect the server finishes and records the turn.
- **ASSUM-007**: verification mechanism failure fails closed (turn errors).
- **ASSUM-008**: one question at a time per channel, queued in order.

## Non-Gherkin obligations (for /feature-plan)

Implementation-level pins the scenarios deliberately do not encode (domain
language), but the plan must carry:

- **Contract is already frozen — implement, don't re-freeze.** Frame vocabulary
  byte-for-byte per contract §7 Rev 1 (`token`/`done` unchanged; `transcript`,
  `audio_ref {seq, chunk_id, url}`, `error`, `voice_turn` header + one binary
  frame added). Pins: `CONTRACT_SHA=574615e9…`, `BINDING_SHA=e50897d1…` (build
  plan §0). No second freeze (design §8).
- **`SessionService.turn_stream`** implemented from the stub
  (`src/study_tutor/session/service.py:299`, currently `NotImplementedError`);
  **`TurnEvent` widened** from `Literal["token","done"]` to add
  `transcript`/`audio_ref`/`error` members and `seq`/`chunk_id`/`url` fields
  (service.py:163) — part of the already-frozen §8 shape. `ReplyStreamFn`
  stays a plain token-string iterator; voice frames are emitted by the voice
  layer around it (design §5.2).
- **`LLMClient.generate_stream`** (TASK-STREAM-001 Scope 1): the client
  hardcodes `"stream": False` and is sync (`llm/client.py:185`), bridged via
  `asyncio.to_thread` in the Player adapter
  (`tutoring/adapters/llm_player_adapter.py:162,192`) — the streaming path
  touches **both** seams; the upstream llama-swap/OpenAI endpoint already
  supports SSE token streaming.
- **Server dependency:** plain `uvicorn` rejects WS upgrades — pin
  `uvicorn[standard]` (or an explicit `websockets` dep) in `pyproject.toml`
  (design §5.2).
- **WS route** is a `WebSocketRoute` (route table is `Route`-only today);
  auth at upgrade via `resolve_student_from_token` on the `Authorization`
  header; domain errors surface as `{type:"error", error, error_type}` frames
  (closed-set envelope); mounted under the `STUDY_TUTOR_VOICE_ENABLED`
  conditional-route pattern (ASSUM-002).
- **Sentence-chunked TTS:** one `/v1/audio/speech` call per chunk with
  `response_format=wav`; chunks synthesized and announced in `seq` order;
  chunk store in-memory, TTL ≤120 s, capped, never disk (never-at-rest
  invariant, design §5.6); single-process store assumption rides the
  single-worker uvicorn deploy (noted multi-worker redesign item).
- **Chunk-boundary quote verification** via the existing
  `apply_quote_verification`, scoped to the accumulated text so far
  (ADR-ARCH-027) — a chunk's tokens are emitted only after that chunk passes;
  Coach stays async and evaluates the assembled full response after the
  stream completes (ADR-ARCH-026 D1).
- **Acceptance:** streaming variants of the 35-assertion contract suite
  (`app/test_live/`, TASK-STREAM-001 Scope 4), run `--concurrency=1` per the
  binding's global-reset note; the non-streaming JSON `turn` endpoint is
  retained and re-verified unchanged.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "FEAT-VOICE-002 streaming voice" \
      --context features/streaming-voice/streaming-voice_summary.md
