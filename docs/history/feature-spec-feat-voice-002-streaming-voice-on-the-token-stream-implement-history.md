# /feature-spec — feat-voice-002-streaming-voice-on-the-token-stream-implement — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec feat-voice-002-streaming-voice-on-the-token-stream-implement — 2026-07-06T16:12:07Z

### Prompt

```
/feature-spec "FEAT-VOICE-002 streaming voice on the token stream: implement and widen SessionService.turn_stream/TurnEvent + WebSocketRoute turn per the frozen contract §7 frames; uvicorn[standard]/websockets server dep; LLMClient generate_stream incl. the asyncio.to_thread Player-adapter seam (TASK-STREAM-001 Scope 1); sentence-chunked TTS (~15-25 words, response_format=wav) emitting audio_ref frames; chunk-boundary quote verification per the G-RAT ADR; streaming variants of the contract suite" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md
```

### Assistant response

I'll run the /feature-spec phases. Starting with **Phase 1: Context Gathering** — detecting the stack, scanning the codebase, and reading the four context files (skipping Graphiti per project memory: it's retired).

Context is nearly complete. Quick look at the code seams the spec will exercise (`turn_stream` stub, `TurnEvent`, `LLMClient`, Player adapter).

Phase 1 done. One last consistency check against the W1 spec's phrasing conventions, then I'll generate the proposal.
