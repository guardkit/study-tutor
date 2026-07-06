# /design-refine — add-voice-routes-binding-2-the-voice-ws-frame-vocabulary-con — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /design-refine add-voice-routes-binding-2-the-voice-ws-frame-vocabulary-con — 2026-07-06T14:01:21Z

### Prompt

```
/design-refine "Add voice routes (binding §2), the voice WS frame vocabulary (contract §7), and six voice error_types (contract §9) per the voice design §8; re-freeze both contract docs; CONTRACT_SHA and BINDING_SHA bumped together, once" \
  --context docs/design/contracts/API-session-cross-device.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md
```

### Assistant response

Running /design-refine. Given the last session's memory says G-CON was already executed (contract + binding at Revision 1, SHAs pinned in the plan §0), my first job is to verify whether this refinement is already applied rather than re-applying it. Graphiti is retired, so this runs markdown-only. Let me load the context files.

Line 8 has the same class of staleness — it still labels ADR-ARCH-026 "(Proposed — gated)" even though line 3 records G-RAT as executed. I'll fix both.
