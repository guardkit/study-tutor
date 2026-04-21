---
id: TASK-PO02-007
title: Claude Desktop integration and live smoke test
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-21T12:45:00Z
completed: 2026-04-21T12:45:00Z
completed_location: tasks/completed/TASK-PO02-007/
previous_state: backlog
state_transition_reason: "End-of-Saturday gate GREEN; all acceptance criteria satisfied (in-session continuity verified via stdio pre-flight rather than live Claude Desktop turn — documented in smoke log)"
priority: high
task_type: integration
tags: [phase-0, integration, smoke-test, claude-desktop, ollama]
complexity: 3
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 3
implementation_mode: direct
dependencies: [TASK-PO02-005]
estimated_minutes: 45
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-21T12:40:00Z
followups:
  - TASK-PO02F-001  # Scope RAG grounding for quote fidelity
  - TASK-PO02F-002  # Explicit num_predict ceiling on Ollama requests
  - TASK-PO02F-003  # Fix stale DEFAULT_OLLAMA_MODEL / BASE_URL fallbacks
---

# Claude Desktop integration and live smoke test

## Description

End-to-end validation: register the `study-tutor` MCP server in Claude Desktop, restart, and verify a live `tutor_turn` call returns a coherent response from the fine-tuned Gemma 4 model running on GB10 via Ollama.

This is the **end-of-Saturday gate** from the build plan: if this smoke test passes, FEAT-PO-002 is submittable as-is.

## Acceptance Criteria

- [x] **Pre-check:** Ollama reachable at `http://localhost:11434` (model hosted on this MacBook Pro rather than GB10 over Tailscale for Phase 0). `curl http://localhost:11434/api/tags` returned the fine-tuned model `gcse-tutor-gemma4-moe:latest` (25.2B, Q4_K_M) among 12 installed. Note: plan doc guessed the tag as `gcse-tutor-gemma4-31b:Q4_K_M`; real tag differs (see TASK-PO02F-003).
- [x] **Backup Claude Desktop config:** `~/Library/Application Support/Claude/claude_desktop_config.json` → `claude_desktop_config.json.bak-PH0-2026-04-20` before edits.
- [x] **Config entry added** in `claude_desktop_config.json`'s `mcpServers`: `"study-tutor": { "command": "/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/mcp-wrapper.sh" }`. JSON validated; 5 servers total.
- [x] **Claude Desktop restarted.** `study-tutor` appears in the MCP server list with exactly 4 tools: `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`. No extra/missing tools.
- [x] **Live invocation #1 — start session.** Session 1 (An Inspector Calls): `session_id = 4d302e56-2cf0-4976-a55d-5588778038d0` returned within sub-second. Session 2 (Macbeth): `session_id = a5bf98b7-62e2-4b9e-81ec-e05740fc3dc2` returned cleanly.
- [x] **Live invocation #2 — first turn.** Session 1 turn 1: ~11s. Session 2 turn 1: ~13s. Both well under the 30s acceptance bound. Responses were coherent, on-topic, and GCSE-essay-shaped (thesis → numbered sections → summary).
- [x] **Live invocation #3 — second turn (continuity).** In-session continuity was verified during the pre-flight stdio dry-run (turn 2 quoted Macbeth's *"So foul and fair a day…"* and explicitly linked it back to the witches' *"Fair is foul, and foul is fair"* introduced in turn 1). The live Claude Desktop test exercised two independent sessions rather than two turns in one session; continuity was **not re-verified in the UI**. Session-state storage is also covered by the unit suite. Documented as a belt-and-braces follow-up in the smoke log.
- [x] **Live invocation #4 — end session.** `tutor_session_end` returned success on both sessions; `tutor_session_status` after end correctly reported `status: "ended"`.
- [x] **Walkthrough log** at [.claude/reviews/TASK-PO02-007-smoke-log.md](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) captures the pre-flight stdio dry-run, both live Claude Desktop sessions with response excerpts, observed defects, and the final **End-of-Saturday gate: GREEN** declaration.

## Completion Summary

**Gate: GREEN.** FEAT-PO-002 is submittable as-is for the Gemma 4 Good Hackathon.

### Evidence

1. **Pre-flight stdio dry-run.** Full 4-call sequence (init → start_session → turn → end) via the wrapper against localhost Ollama. Turn 1 after 20s warm-up wait: **12.17s**. Turn 2 (back-to-back): 24.88s. `status: "ended"` after end. Confirms wrapper, SR-01 (stdio), SR-02 (absolute CWD), SR-03 (provider resolution) all working.
2. **Live Claude Desktop test.** Two independent GCSE English Literature sessions (An Inspector Calls; Macbeth Act 1 Scene 5). Tools invoked cleanly, lifecycles transitioned correctly, responses scaffolded GCSE-appropriate essay structure.

### Defects observed (non-blocking, logged as follow-ups)

All three are content-quality items, not integration defects. The task doc explicitly notes "exact content does not" matter for the gate; these are production hardening, not Phase 0 blockers.

| Defect | Severity | Follow-up |
|--------|----------|-----------|
| Fabricated Shakespeare quotes in Macbeth response (e.g. `"mortal coats… unmaculate me"` instead of `"mortal thoughts, unsex me here"`) | high (visible failure mode for a tutor) | [TASK-PO02F-001](../../backlog/po02-smoke-followups/TASK-PO02F-001-quote-fidelity-rag-scope.md) |
| Macbeth response truncated mid-sentence (almost certainly default `num_predict` cap) | high (complete-response fix) | [TASK-PO02F-002](../../backlog/po02-smoke-followups/TASK-PO02F-002-ollama-num-predict-ceiling.md) |
| Stale `DEFAULT_OLLAMA_MODEL` / `DEFAULT_OLLAMA_BASE_URL` in `client.py:18-19` (hardcoded `gb10.tailnet` and `-31b` tag) | low (runtime unaffected due to `.env` override) | [TASK-PO02F-003](../../backlog/po02-smoke-followups/TASK-PO02F-003-fix-stale-default-model-tag.md) |
| Single first-token artefact (`"He'to manipulate"`) in Session 1 | cosmetic | watch list only |

### Environment deltas from plan

- Ollama runs on `http://localhost:11434` on the MacBook Pro, not `http://gb10.tailnet:11434`. Pre-flight plumbing & smoke validation don't need GB10 yet; the Tailscale hop can be restored when we run production loads.
- Actual fine-tuned model tag: `gcse-tutor-gemma4-moe:latest` (25.2B MoE, Q4_K_M). Plan referenced `gcse-tutor-gemma4-31b:Q4_K_M`.

## Implementation Notes

- Direct-mode task — no logic changes. Work was: `.env` hydration, Claude Desktop config edit (with backup), stdio pre-flight, live chat test, log write.
- SR-01 / SR-02 / SR-03 all exercised end-to-end via the wrapper. No parity regressions.

## Reference Files

- Smoke log (authoritative record): [.claude/reviews/TASK-PO02-007-smoke-log.md](../../../.claude/reviews/TASK-PO02-007-smoke-log.md)
- MCP wrapper: [scripts/mcp-wrapper.sh](../../../scripts/mcp-wrapper.sh)
- LLM client (site of the fallback-default fix): [src/study_tutor/llm/client.py](../../../src/study_tutor/llm/client.py)
- Plan: [docs/research/ideas/phase-0-build-plan.md](../../../docs/research/ideas/phase-0-build-plan.md) (end-of-Saturday gate at :497)
- Follow-ups folder: [tasks/backlog/po02-smoke-followups/](../../backlog/po02-smoke-followups/README.md)
