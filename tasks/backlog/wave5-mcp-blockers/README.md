# Wave 5 MCP demo blockers

Three implementation tasks that unblock [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md)
(the live end-to-end MCP tutor session with G3/G4/G5/G6/G13 evidence). Spawned by
[TASK-REV-GRD5](../TASK-REV-GRD5-analyse-gr-demo-blockers.md) on 2026-05-05.

## Quick index

- [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — full execution strategy, gate-flip outcomes, risk register, Phase-2 handoff
- [TASK-GR-PMT](./TASK-GR-PMT-populate-player-prompt.md) — Wave 1 — populate `roles/tutor/prompts/player.md` (BLOCK-2)
- [TASK-GR-WIRE](./TASK-GR-WIRE-orchestrator-and-session-end.md) — Wave 1 — wire `orchestrator_factory` + delegate to `perform_session_end` (BLOCK-1 + BLOCK-3a)
- [TASK-GR-CONF](./TASK-GR-CONF-topic-confidence-update.md) — Wave 2 — TopicConfidence typed-entity update with pluggable policy (BLOCK-3b)

## TL;DR

The 2026-05-05 live MCP tutor session conducted via Claude Desktop completed transport-level
round-trips but failed three AC-DEMO gates. Three discrete implementation gaps were identified;
TASK-REV-GRD5's deep-dive review then re-decomposed BLOCK-3 into a wiring task (BLOCK-3a, much
smaller than originally thought because `perform_session_end` already exists) and a genuine new-code
task (BLOCK-3b, the TopicConfidence entity update with explicit FEAT-PH2-001 handoff).

## Suggested execution

```
Wave 1 (parallel-eligible):
  /task-work TASK-GR-PMT     # 10 min, single-line file edit
  /task-work TASK-GR-WIRE    # ~3h, MCP adapter rewiring

Wave 2 (after WIRE):
  /task-work TASK-GR-CONF    # ~4h, new typed-entity write helper + Protocol policy seam

Re-attempt the live demo:
  /task-work TASK-GR-DEMO    # picks up AC-DEMO-01..07 evidence capture
```

## Provenance

| Field | Value |
|---|---|
| Spawning review | TASK-REV-GRD5 |
| Spawned via | /task-review → [I]mplement (2026-05-05) |
| Feature ID | FEAT-FD32 |
| Wave | 5 |
| Parent task | TASK-GR-DEMO |
| Source incident | [REVIEW-TASK-GR-DEMO-2026-05-05.md](../../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) |
| Source review | [TASK-REV-GRD5-review-report.md](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) |
