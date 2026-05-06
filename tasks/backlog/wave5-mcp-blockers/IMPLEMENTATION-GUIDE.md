# Wave 5 MCP demo blockers — Implementation Guide

**Spawned by:** TASK-REV-GRD5 (decision review accepted via [I]mplement, 2026-05-05)
**Parent task:** [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) (status: `blocked`)
**Feature ID:** FEAT-FD32 (inherited from TASK-GR-DEMO)
**Source review:** [TASK-REV-GRD5-review-report.md](../../../.claude/reviews/TASK-REV-GRD5-review-report.md)
**Source incident report:** [REVIEW-TASK-GR-DEMO-2026-05-05.md](../../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md)

---

## Problem statement

The 2026-05-05 live MCP tutor session attempt completed transport-level round-trips (7 turns,
`tutor_session_end` returned successfully) but failed to satisfy AC-DEMO-02/03/05/06 because three
implementation gaps prevent the Phase-1 path from activating:

| Block | Gap | Effect |
|---|---|---|
| BLOCK-1 | `orchestrator_factory` not injected at MCP server entry point | Phase-0 single-LLM path active; no Coach revision; AC-DEMO-01.2 falsified |
| BLOCK-2 | `roles/tutor/prompts/player.md` is a placeholder stub | Empty system prompt to gemma4-tutor; lecture-style responses |
| BLOCK-3 | `tutor_session_end` is a TODO; no Graphiti write-back | AC-DEMO-02 (`session_completed` episode) and AC-DEMO-03 (TopicConfidence delta) falsified |

The review's headline finding: BLOCK-3 partially collapses to a wiring task because
`perform_session_end()` already exists at `src/study_tutor/tutoring/session_end.py:334` with seven
unit tests and a complete F4-lifecycle / DDR-003-ordering / fire-and-forget contract. Only the
TopicConfidence node-attribute update is genuinely new code. BLOCK-3 is therefore re-decomposed:

- **BLOCK-3a** (wiring) — bundle with BLOCK-1 into TASK-GR-WIRE
- **BLOCK-3b** (typed-entity update) — its own task TASK-GR-CONF

---

## Subtasks

| ID | Title | Complexity | Wave | Workspace |
|---|---|---:|:---:|---|
| [TASK-GR-PMT](./TASK-GR-PMT-populate-player-prompt.md) | BLOCK-2: populate player.md with verbatim Open WebUI system prompt | 1 | 1 | `wave5-mcp-blockers-wave1-1` |
| [TASK-GR-WIRE](./TASK-GR-WIRE-orchestrator-and-session-end.md) | BLOCK-1+3a: wire orchestrator_factory and perform_session_end into MCP adapter | 5 | 1 | `wave5-mcp-blockers-wave1-2` |
| [TASK-GR-CONF](./TASK-GR-CONF-topic-confidence-update.md) | BLOCK-3b: TopicConfidence node update on session end (typed-entity write + pluggable policy) | 5 | 2 | `wave5-mcp-blockers-wave2-1` |

---

## Execution strategy

### Wave 1 — parallel-eligible

```
TASK-GR-PMT  ──┐
               ├── (no file overlap; can parallel via Conductor)
TASK-GR-WIRE ──┘
```

- **TASK-GR-PMT** edits `roles/tutor/prompts/player.md` (markdown only).
- **TASK-GR-WIRE** edits `src/study_tutor/mcp/adapter.py`, `src/study_tutor/cli/main.py`, and adds
  unit + integration tests.

There is **no hard build dependency** between them — TASK-GR-WIRE compiles and tests with the
placeholder prompt unchanged. However the operator-conducted demo session that captures AC-WIRE-09
evidence is **honest only after TASK-GR-PMT lands** (Coach revision evidence under AC-DEMO-01.2 needs
to come from a Player using the real Socratic prompt; the lecture-stub prompt confounds the signal).

**Recommended order**:
- **Sequential**: TASK-GR-PMT first (10 minutes), then TASK-GR-WIRE (~3h). Cleanest evidence trail.
- **Parallel via Conductor**: spawn both in their own workspaces; merge TASK-GR-PMT first; rebase
  TASK-GR-WIRE onto main; conduct AC-WIRE-09 demo session against the rebased branch.

Either way, AC-DEMO-04 (turn-level latency capture) is harvested from the same demo session that
captures AC-WIRE-09 — no separate latency-capture task. Instrumentation already exists per FEAT-PO-002
(`tutor_turn_complete` structured-log line carries `elapsed_ms`).

### Wave 2 — sequential

```
TASK-GR-WIRE  ──→  TASK-GR-CONF
```

**TASK-GR-CONF depends on TASK-GR-WIRE** (hard build dependency): TASK-GR-CONF consumes the
`write_helper` and `event_bus` injection points added to `MCPAdapter.__init__` by TASK-GR-WIRE
(AC-WIRE-05). Without that injection, TASK-GR-CONF has no helper to call `record_topic_confidence_update`
through.

---

## Gate-flip outcomes

After all three tasks land, [phase-1-validation.md](../../../docs/research/ideas/phase-1-validation.md)
gates flip:

| Gate | Before | After GR-PMT | After GR-WIRE | After GR-CONF |
|---|---|---|---|---|
| **G3** (planner explainable, live) | **Held** (since 2026-05-04) | Held | Held | Held |
| **G4** (P-C loop runs end-to-end) | Falsified at runtime | Falsified | **Held** | Held |
| **G5** (Coach feedback observable) | Falsified at runtime | Falsified | **Held** | Held |
| **G6** (E2E demo flow works) | Falsified | Falsified | Mostly Held (AC-DEMO-03 outstanding) | **Fully Held** |
| **G13** (dynamic retrieval observable) | Falsified at runtime | Falsified | **Held** | Held |

Operator should re-run `/task-work TASK-GR-DEMO` (or conduct the live AC-DEMO session manually since
AC-DEMO-01 is human-in-the-loop) after Wave 2 lands. TASK-GR-DEMO's existing `autobuild_state`
(`current_turn: 2` with two advisory-non-blocking turns) is fine — it picks up from turn 3 with the
implementation actually in place.

---

## Architectural compliance summary

| Concern | Source | How this work satisfies it |
|---|---|---|
| Async fire-and-forget at every Graphiti write point | [ADR-ARCH-019](../../../docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (CC-13) | TASK-GR-WIRE delegates to `perform_session_end` which schedules F3 via `GraphitiWriteHelper.schedule_write`. TASK-GR-CONF uses `asyncio.create_task` for `EntityNode.save` and `schedule_write(F2)` for the episode. `tutor_session_end` returns < 2s. |
| `tutor_turn` p95 < 10s | CC-08 / LES1 | Coach + Player are awaited inside the orchestrator's per-turn budget; orchestrator already enforces `latency_budget_seconds` and emits flagged_for_review on overrun. |
| Typed-entity writes bypass LLM extraction | [ADR-ARCH-021](../../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) | TASK-GR-CONF mirrors the seed's `EntityNode.save` pattern (ms latency; bypasses Gemini; bypasses RediSearch dash-as-NOT bug). |
| DDR-003 ordering | `phase-1-scope.md` | `perform_session_end` already enforces "emit `session.completed` on bus before `add_episode` schedule_write" — pinned by `tests/unit/tutoring/test_session_end.py`. |
| Misconfigured-loop guard | ADR-ARCH-012 / orchestrator | TASK-GR-WIRE smoke-builds an orchestrator at adapter init to surface `OrchestratorConfigurationError` at boot rather than first turn. |
| Single-process / single-user | [ADR-ARCH-014](../../../docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md) | No new processes, no out-of-process queue. All async runs in the tutor's asyncio loop. |
| Single-topic per Phase-1 session | Planner contract | TASK-GR-CONF updates exactly one TopicConfidence node per session (the `topic_override` or planner-selected `topic_name`). |

---

## Phase-2 handoff

TASK-GR-CONF ships `Phase1MinimalDeltaPolicy` as a stub. The Phase-2 build plan §"Coach signal
quality" (`docs/research/ideas/phase-2-build-plan.md`) explicitly assigns the real
confidence-update policy to **FEAT-PH2-001**.

The Protocol seam (`ConfidenceDeltaPolicyLike`) defined in TASK-GR-CONF's AC-CONF-02 is the surface
FEAT-PH2-001 substitutes against. The `confidence_source: str` field on
`TopicConfidenceUpdatedEpisode` (AC-CONF-07) is the mechanism by which Phase-2 dashboards filter
heuristic-era data out of percentage-trend visualisations:

```
Phase-1 stub:    confidence_source = "phase1_minimal_policy"
FEAT-PH2-001:    confidence_source = "<descriptive name>" (e.g. "coach_misconception_aggregator_v1")
```

Phase-2 dashboards SHOULD filter `confidence_source != "phase1_minimal_policy"` when surfacing
percentage trends to users.

See [TASK-REV-GRD5 review §R1.3](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) for the
Coach-signal taxonomy analysis driving this design.

---

## Risk register (cross-task summary)

| Risk | Owner task | Severity | Mitigation |
|---|---|---|---|
| Factory closure captures wrong state | TASK-GR-WIRE | High | AC-WIRE-04 per-turn isolation unit test |
| Coach + Player same provider misconfiguration | TASK-GR-WIRE | High | AC-WIRE-02 boot-time smoke build |
| Test coverage gap on serve() entry point | TASK-GR-WIRE | Medium | AC-WIRE-11 integration smoke test |
| Drift between repo prompt and GB10 source | TASK-GR-PMT | Medium | AC-PMT-02 provenance comment with date |
| Category-error trap (Coach scores Player not student) | TASK-GR-CONF + FEAT-PH2-001 | High | Protocol seam (AC-CONF-02); explicit rationale in TASK-GR-CONF AC-CONF-12 |
| Heuristic-era data poisons Phase-2 analytics | TASK-GR-CONF + Phase-2 dashboards | Medium | `confidence_source` field (AC-CONF-07) for filtering |
| R-WAVE5-03 (RediSearch dash-as-NOT) re-surfaces on F2 episode write | TASK-GR-CONF | Medium | Entity update path bypasses; episode failure is logged-only |
| Heuristic delta drives band boundary unexpectedly | TASK-GR-CONF | Low | Band recomputation is the correct semantic; if Phase-2 wants stability, policy-layer fix |

---

## Cross-references

- [TASK-REV-GRD5 review report](../../../.claude/reviews/TASK-REV-GRD5-review-report.md) — primary input (with revision R1)
- [docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md](../../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) — original incident report (BLOCK-1/2/3 narrative)
- [docs/research/ideas/phase-1-validation.md](../../../docs/research/ideas/phase-1-validation.md) — gate file (G3..G13)
- [docs/research/ideas/phase-2-build-plan.md](../../../docs/research/ideas/phase-2-build-plan.md) — FEAT-PH2-001 ownership of the real confidence-update policy
- [docs/architecture/container.md](../../../docs/architecture/container.md) — C4 Container view
- [TASK-GR-DEMO](../TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) — parent task awaiting unblock
- [TASK-GSM-009](../../completed/TASK-GSM-009/TASK-GSM-009.md) — typed-entity seed (the pattern TASK-GR-CONF mirrors)
