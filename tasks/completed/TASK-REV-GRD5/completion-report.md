# TASK-REV-GRD5 — Completion Report

**Title:** Review: Analyse TASK-GR-DEMO blockers and sequence the BLOCK-1/2/3 fixes
**Type:** Review (decision mode, standard depth)
**Completed:** 2026-05-06
**Complexity:** 4/10
**Parent feature:** FEAT-FD32 (Graphiti Runtime Integration Repair)
**Review report:** [review-report.md](./review-report.md)

## Outcome

Review accepted on revision R1 with decision `[I]mplement`. Three implementation tasks were spawned and have all since landed:

| Block | Task | Status | Commit |
|---|---|---|---|
| BLOCK-2 (Socratic prompt) | TASK-GR-PMT — populate player.md with verbatim Open WebUI prompt | completed | `d8972b6` |
| BLOCK-1 + BLOCK-3a (orchestrator factory + perform_session_end wiring) | TASK-GR-WIRE — orchestrator and session end | completed | `8249a5e` |
| BLOCK-3b (TopicConfidence typed-entity update + pluggable policy) | TASK-GR-CONF — TopicConfidence update on session end | completed | `1946ec7` |

The recommended hybrid sequencing (BLOCK-2 standalone → BLOCK-1+3a bundled → BLOCK-3b standalone) was followed. The Protocol seam (`ConfidenceDeltaPolicyLike` + `Phase1MinimalDeltaPolicy`) designed in §R1.3.3 was implemented as specified, with FEAT-PH2-001 named as the owner of the real policy.

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-REV-01 | ✅ | `review-report.md` §AC-REV-01 — three BLOCKs verified with file:line citations against `main`. |
| AC-REV-02 | ✅ | Hybrid sequencing decided (3 tasks; BLOCK-2 → BLOCK-1+3a → BLOCK-3b). Rationale captured in §AC-REV-02. |
| AC-REV-03 | ✅ | BLOCK-2 resolved → option **(b1)** verbatim copy of Open WebUI prompt. Cost of deferring (b2) documented. |
| AC-REV-04 | ✅ | BLOCK-3 resolved → async fire-and-forget per ADR-ARCH-019; episode payload shape pinned; TopicConfidence update strategy is per-touched-topic with pluggable delta policy (R1.3.3). |
| AC-REV-05 | ✅ | Risk register produced (§AC-REV-05 + §R1.4 additions) covering category-error trap, heuristic-era data poisoning, R-WAVE5-03 dash-NOT bite. |
| AC-REV-06 | ✅ | Three `/task-create` invocations spawned under `tasks/backlog/wave5-mcp-blockers/`. AC-CONF set revised in R1.3.4. |
| AC-REV-07 | ✅ | Phase-1 gate impact: G4/G5/G6/G13 flip on BLOCK-1+2+3a; G3 already Held; AC-DEMO-03 needs BLOCK-3b. |

## Key decisions captured

1. **Hybrid task split** (not three independent or one bundled). BLOCK-2 ships qualitative lift in one PR; BLOCK-1+3a co-located in `adapter.py` so they share review surface; BLOCK-3b is the only genuinely new code path.
2. **Async write-back** per ADR-ARCH-019; `tutor_session_end` returns within ASSUM-004's 2s budget regardless of FalkorDB latency.
3. **Pluggable Protocol seam for confidence delta** — `ConfidenceDeltaPolicyLike` + `Phase1MinimalDeltaPolicy` stub. Forces FEAT-PH2-001 to expose its policy contract explicitly; bakes provenance (`confidence_source`) into episode payloads so heuristic-era data is filterable in perpetuity.
4. **Major scoping discovery** (§Executive summary): `SessionCompletedEpisode` / `record_session_completion` / `GraphitiWriteHelper.schedule_write` / `perform_session_end` / `EventBus`-based F3 dispatch already existed and were unit-tested — BLOCK-3 was a wiring task on the F3 side, not new code. Only BLOCK-3b was net-new.

## Verification

- All three unblockers landed and are in `tasks/completed/`:
  - `tasks/completed/TASK-GR-PMT/`
  - `tasks/completed/TASK-GR-WIRE/`
  - `tasks/completed/TASK-GR-CONF/`
- TASK-GR-CONF's own completion report confirms AC-CONF set (revised by this review) was implemented as specified.

## Follow-ups (not in scope of this review)

- **TASK-GR-DEMO re-attempt** with the three landed unblockers — the operator-supervised live MCP session that flips G4/G5/G6/G13 from Falsified to Held in `phase-1-validation.md`.
- **FEAT-PH2-001** — owner of the real `ConfidenceDeltaPolicy` that replaces `Phase1MinimalDeltaPolicy`. Reference §R1.3.2 in that feature's spec so the category-error trap stays sealed.
- **Phase-2 analytics filter** — when dashboards surface percentage trends, filter `confidence_source != "phase1_minimal_policy"` so heuristic-era data does not contaminate real-signal trends.
