---
id: TASK-REV-GRD5
title: "Review: Analyse TASK-GR-DEMO blockers and sequence the BLOCK-1/2/3 fixes"
task_type: review
review_mode: decision
review_depth: standard
status: review_complete
priority: critical
created: 2026-05-05T00:00:00+00:00
updated: 2026-05-05T22:00:00+00:00
complexity: 4
tags:
  - graphiti
  - mcp
  - tutor-session
  - phase-1-gate-closure
  - review
  - decision-point
  - human-in-the-loop
parent_task: TASK-PH2-GR-001
related:
  - TASK-GR-DEMO
  - TASK-PH2-GR-001
  - TASK-REV-GR1A
context_files:
  - docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md
  - tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md
  - src/study_tutor/mcp/adapter.py
  - roles/tutor/prompts/player.md
  - docs/research/ideas/phase-1-validation.md
feature_id: FEAT-FD32
decision_required: true
review_results:
  mode: decision
  depth: standard
  revisions: 1
  findings_count: 3
  recommendations_count: 3
  decision: spawn-three-tasks
  sequencing: hybrid
  block_2_choice: b1-verbatim-copy
  block_3_writeback: async-fire-and-forget-per-ADR-ARCH-019
  block_3_decomposition: 3a-wiring + 3b-typed-entity-update
  block_3b_delta_policy: pluggable-protocol-with-phase1-minimal-stub-feat-ph2-001-owns-real-policy
  unblockers_proposed:
    - TASK-GR-PMT (BLOCK-2)
    - TASK-GR-WIRE (BLOCK-1 + BLOCK-3a)
    - TASK-GR-CONF (BLOCK-3b — revised AC-CONF in R1.3.4)
  unblockers_spawned:
    - TASK-GR-PMT
    - TASK-GR-WIRE
    - TASK-GR-CONF
  spawn_location: tasks/backlog/wave5-mcp-blockers/
  report_path: .claude/reviews/TASK-REV-GRD5-review-report.md
  recommendation: implement
  decision_taken: implement
  decision_taken_at: 2026-05-05T22:45:00+00:00
  awaiting: task-complete-of-review
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  reason: review-task-no-automated-tests
---

# Review: Analyse TASK-GR-DEMO blockers and sequence the BLOCK-1/2/3 fixes

## Why this exists

The live MCP tutor session attempt on 2026-05-05 (TASK-GR-DEMO) completed transport-level round-trips but failed to close AC-DEMO-02/03/05/06. The session report at [docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md](../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) identifies three discrete implementation gaps (BLOCK-1, BLOCK-2, BLOCK-3) and recommends BLOCK-2 as a quick win. Before spawning implementation tasks, this review consolidates the findings, validates the scope/sequence, and decides whether each block becomes its own task or whether they collapse into a single fix-up task.

## Inputs

- **Primary:** [docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md](../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) (session findings, AC-DEMO status table, three BLOCK items, Open WebUI vs MCP contrast)
- **Source task:** [tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md](./TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) (AC-DEMO-01 through AC-DEMO-07)
- **Code under review:** `src/study_tutor/mcp/adapter.py` (Phase 0 vs Phase 1 path, `tutor_session_end` TODO), `roles/tutor/prompts/player.md` (placeholder stub), MCP server entry point (orchestrator_factory injection point)
- **Working reference:** Open WebUI system prompt at `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` (GB10) — the prompt that activates Socratic behaviour in the same model

## Acceptance Criteria

- [ ] **AC-REV-01** — Each of the three BLOCK items is independently validated against the codebase as it stands on `main` today. Confirm or refute:
  - BLOCK-1: `MCPAdapter.__init__` accepts `orchestrator_factory` but the server entry point does not inject one.
  - BLOCK-2: `roles/tutor/prompts/player.md` is the placeholder stub described in the report.
  - BLOCK-3: `tutor_session_end` in `adapter.py` contains the `TODO(phase-1)` comment with no Graphiti write-back code path.
  Each finding gets a code-level citation (file:line) and a one-line confirmation.

- [ ] **AC-REV-02** — Sequencing decided. Output one of:
  - **(a)** Three separate implementation tasks, ordered by dependency (recommended ordering with rationale).
  - **(b)** A single fix-up task covering all three (with rationale for why bundling beats splitting).
  - **(c)** A hybrid (e.g. BLOCK-2 standalone, BLOCK-1+3 bundled).
  The decision must explain *why* — blast radius, review surface, parallelisability, and whether the AC-DEMO gates can flip incrementally.

- [ ] **AC-REV-03** — BLOCK-2 design choice resolved. Decide between:
  - **(b1)** Verbatim copy of Open WebUI prompt into `roles/tutor/prompts/player.md` (30-second fix; immediate quality lift).
  - **(b2)** Wire FEAT-PO-001's `GOAL.md` → player prompt generation as originally intended.
  Include a recommendation and the cost of deferring (b2) if (b1) is chosen first.

- [ ] **AC-REV-04** — BLOCK-3 design choice resolved. Decide:
  - Sync vs async write-back (per DEC-02 guidance in the TODO).
  - Episode payload shape (turn count, summary, p50/p95 latency? — what does AC-DEMO-02 actually require for replay?).
  - TopicConfidence update strategy (single topic from `topic_override`? all touched topics? confidence delta source — heuristic from turn count, Coach signal, or explicit student self-report?).

- [ ] **AC-REV-05** — Risk register produced. Identify failure modes for each block:
  - BLOCK-1: orchestrator_factory wiring — what breaks if the factory closure captures wrong state? Test coverage gap on the entry-point path?
  - BLOCK-2: prompt-as-data — version control story, drift risk vs the GB10 file.
  - BLOCK-3: Graphiti write-back — partial-failure semantics (episode written but TopicConfidence update fails?), transactional expectations, retry posture.

- [ ] **AC-REV-06** — Spawn decision recorded. The review concludes with either:
  - One or more `/task-create` invocations (with prefix, title, dependencies, AC outline) ready to run, **OR**
  - A justified "no new task — fold fixes into TASK-GR-DEMO and re-attempt" decision.
  Either way, TASK-GR-DEMO's `status: blocked` must reflect the outcome (unblocked-by lineage updated, or unblocking conditions explicit).

- [ ] **AC-REV-07** — Phase-1 gate impact stated. For each of G3/G4/G5/G6/G13 in `phase-1-validation.md`, state whether the proposed fixes are sufficient to flip the gate or whether further work is required (e.g. is AC-DEMO-04 latency capture covered by the Phase 1 path's instrumentation, or is more work needed?).

## Test Requirements

This is an analysis task — no automated tests. Verification is:

1. **Code-citation accuracy.** Every finding cites file:line and the citation actually matches the code on `main`.
2. **Decision auditability.** Each AC produces a decision with a written rationale, not just a recommendation.
3. **Spawn-readiness.** If AC-REV-06 recommends new tasks, the `/task-create` invocations are concrete enough to run as-is (titles, prefixes, AC sketches, dependency links).

## Implementation Notes (for the reviewer)

### Read order

1. `docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md` — the source findings.
2. `tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md` — the parent ACs the blocks must satisfy.
3. `src/study_tutor/mcp/adapter.py` — verify Phase 0/Phase 1 branching and the `tutor_session_end` TODO are exactly as described.
4. `roles/tutor/prompts/player.md` — verify it is still the placeholder.
5. MCP server entry point (search for `MCPAdapter(` instantiation) — confirm `orchestrator_factory` is omitted.

### Sequencing tradeoff to weigh explicitly

The report recommends BLOCK-2 first as a "30-second fix that unblocks immediately". That is true for *qualitative* session improvement, but BLOCK-2 alone does not flip any AC-DEMO gate — AC-DEMO-01.2 still needs BLOCK-1 (Coach revision) and AC-DEMO-02/03 still need BLOCK-3 (Graphiti write). Decide whether the right sequencing is:
- BLOCK-2 → BLOCK-1 → BLOCK-3 (build quality up, then plumbing) — ships visible improvements early, but no gate flips until the third PR.
- BLOCK-1 + BLOCK-3 first, BLOCK-2 last (plumbing first, polish second) — gates flip on the first two PRs, but the demo session quality stays poor until BLOCK-2 lands.
- All three bundled — single re-attempt of TASK-GR-DEMO when all three are done.

### What the existing autobuild_state on TASK-GR-DEMO tells us

TASK-GR-DEMO has `autobuild_state.current_turn: 2` with two prior task-work attempts that the Coach flagged as advisory-non-blocking (missing Phase 3 invocation, ACs not met). This review should consider whether re-running task-work on TASK-GR-DEMO after BLOCK-1/2/3 land is appropriate, or whether the existing autobuild state should be reset.

### Graphiti write-back specifics worth resolving

- `DEC-02` is referenced in the TODO comment — find that decision record and confirm what it actually mandates (sync? async? specific episode shape?).
- `TopicConfidence` is a typed entity from TASK-GSM-009 — the seed has 6 nodes covering all three planner bands. The update strategy needs to specify which nodes get touched per session and how `last_revised_at` is computed.

## Cross-references

- [docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md](../../docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md) — primary input
- [tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md](./TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) — parent task being unblocked
- [tasks/in_review/TASK-REV-GR1A-plan-graphiti-runtime-integration-repair.md](../in_review/TASK-REV-GR1A-plan-graphiti-runtime-integration-repair.md) — original Wave-5 plan
- `docs/research/ideas/phase-1-validation.md` — gate file (G3/G4/G5/G6/G13)
- `docs/research/ideas/RUNBOOK-open-webui-tutor-access.md` — Open WebUI working reference
