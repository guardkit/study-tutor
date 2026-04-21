---
id: TASK-REV-PO02
title: "Plan: FEAT-PO-002 — Fine-tuned English tutoring runtime over local deployment"
status: review_complete
created: 2026-04-19T00:00:00Z
updated: 2026-04-20T00:00:00Z
priority: high
task_type: review
review_results:
  mode: decision
  depth: standard
  score: 82
  findings_count: 3
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-PO02-review-report.md
  completed_at: 2026-04-20T00:00:00Z
tags: [feature-planning, phase-0, critical-path, mcp, tutoring-runtime]
complexity: 6
feature_id: FEAT-PO-002
epic: EPIC-001
parent_feature: FEAT-PO-002
decision_required: true
clarification:
  context_a:
    timestamp: 2026-04-19T00:00:00Z
    decisions:
      review_depth: confirm_plus_spot_checks
      risk_tolerance: balanced
      focus_areas: [parity_surfaces, mcp_transport_tool_contract, task_decomposition]
    user_override: defaults
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Plan: FEAT-PO-002 — Fine-tuned English tutoring runtime over local deployment

## Description

Review-and-plan task for **FEAT-PO-002**, the critical-path weekend feature of Phase 0. The feature delivers the Python package scaffold, MCP adapter, LLM provider abstraction (Ollama local + AWS Bedrock Custom Model Import), tutor session management, role manifest, and the six parity surfaces (SR-01 through SR-07) required to submit Phase 0 for the Gemma 4 Good Hackathon (deadline 2026-05-18).

An authoritative hour-by-hour build plan already exists at [docs/research/ideas/phase-0-build-plan.md](../../docs/research/ideas/phase-0-build-plan.md). Per the clarification answers, this review does **not** re-open technical options — it **confirms the plan with targeted spot-checks** and produces a GuardKit task breakdown that mirrors the plan's structure.

## Authoritative Inputs

- **Roadmap entry:** [docs/product/roadmap/roadmap.md:102](../../docs/product/roadmap/roadmap.md#L102)
- **Build plan:** [docs/research/ideas/phase-0-build-plan.md](../../docs/research/ideas/phase-0-build-plan.md)
- **Scope document:** [docs/research/ideas/phase-0-scope.md](../../docs/research/ideas/phase-0-scope.md)
- **Domain goal:** [domains/gcse-english/GOAL.md](../../domains/gcse-english/GOAL.md)
- **Architecture reviews:** [docs/reviews/architecture/claude-desktop-review-system-arch-output.md](../../docs/reviews/architecture/claude-desktop-review-system-arch-output.md)
- **Dependency:** FEAT-PO-001 (domain configuration — also not yet built)

## Review Scope (per Context A defaults)

**Depth:** Confirm plan + targeted spot-checks (option B)
**Priority trade-off:** Balanced (option C) — weekend-code / weekday-ops split is correct
**Focus areas:** (1) parity surfaces, (3) MCP transport + tool contract, (5) task decomposition granularity

### In-scope for this review

1. **Parity surface transfer (SR-01 → SR-07)** — verify the specialist-agent patterns transfer cleanly to `study_tutor`: stdio discipline (SR-01), secrets via env (SR-02), provider resolution via env (SR-03), role manifest (SR-04), criteria definitions skeleton (SR-05), `.env.example` provenance (SR-06), tool description≡behaviour (SR-07).
2. **MCP transport + tool contract** — four tools (`tutor_start_session`, `tutor_turn`, `tutor_status`, `tutor_end_session`); long-running pattern for `tutor_start_session`; description fields honestly describe side effects; synchronous turn contract.
3. **Task decomposition granularity** — are the build plan's natural breakpoints (morning scaffold, afternoon scaffolding, evening MCP skeleton, Sunday parity hardening, Sunday public repo packaging, Mon/Tue Bedrock) the right GuardKit task boundaries? Too coarse blocks parallelism; too fine creates ceremony overhead.

### Out-of-scope (deferred)

- Full re-evaluation of technology choices (Python, MCP SDK, Ollama, Bedrock) — answered by the existing plan.
- Phase 1 concerns (Graphiti, DeepAgents, student memory) — handled by later features.
- Domain configuration details — belongs to FEAT-PO-001.
- Bedrock ops sequencing detail — covered by FEAT-PO-004 (separate feature).

## Acceptance Criteria

- [ ] Review confirms the build plan's six parity surfaces map cleanly onto discrete, testable work items.
- [ ] Review produces a spot-check finding for each of the three focus areas (parity, MCP transport, decomposition), flagging risks proportionately (balanced stance).
- [ ] Review outputs a task breakdown of 5–8 implementation subtasks that collectively deliver FEAT-PO-002.
- [ ] Each proposed subtask has: `task_type`, complexity score (1–10), dependencies, and rough duration estimate.
- [ ] Parallel-execution groups (waves) are identified for Sat/Sun weekend work.
- [ ] Integration Contracts section (§4) is drafted for any cross-task data dependencies (e.g. role manifest → MCP adapter, env vars → LLM client).
- [ ] Decision Checkpoint is presented with A/R/I/C options; on [I]mplement, subtask markdown files and a `.guardkit/features/FEAT-PO-002.yaml` structured feature file are generated.

## Decision Points

This review must explicitly decide:

1. **D1 — Role manifest in scope of FEAT-PO-002 or FEAT-PO-001?** Build plan assigns `roles/tutor/role.yaml` to BOTH. Review must pick a primary owner to avoid duplicate work.
2. **D2 — Unit tests for parity surfaces: one consolidated task or per-surface tasks?** Plan lists `test_stdio_discipline.py` and `test_provider_resolution.py` only; SR-04, SR-05, SR-06, SR-07 have no dedicated test tasks in the plan.
3. **D3 — Bedrock-facing code lives in `llm/client.py` from day one, or introduced only in FEAT-PO-004?** Plan says both files list shows `src/study_tutor/llm/client.py | FEAT-PO-002 + FEAT-PO-004 | NEW`.
4. **D4 — MCP wrapper script (`scripts/mcp-wrapper.sh`) — is it a subtask of FEAT-PO-002 or a scaffolding task owned by FEAT-PO-003 (public repo packaging)?**
5. **D5 — Task execution mode: reviewer-in-loop via `/task-work` (as flagged in the plan) or AutoBuild `/feature-build`?** Plan's explicit guidance is reviewer-in-loop.

## Review Output

On completion, this task produces:

- A Decision Log section appended below.
- Findings report with one paragraph per focus area.
- Proposed subtask list (5–8 tasks) with waves, complexity, dependencies, task_type.
- Integration Contracts (§4) for cross-task artefacts (e.g. `TUTOR_LLM_PROVIDER`, role manifest path).
- A generated IMPLEMENTATION-GUIDE.md with mandatory Mermaid diagrams (data flow, integration contract sequence, task dependency graph).

## Decision Log

_(To be populated by `/task-review TASK-REV-PO02 --mode=decision --depth=standard`)_

## Next Steps

1. Execute review: `/task-review TASK-REV-PO02 --mode=decision --depth=standard`
2. On [I]mplement at the decision checkpoint, `/feature-plan` orchestrator generates:
   - `tasks/backlog/feat-po-002-tutoring-runtime/` with subtask markdown files
   - `.guardkit/features/FEAT-PO-002.yaml` structured feature file
   - `IMPLEMENTATION-GUIDE.md` with Mermaid diagrams
3. Begin implementation with the first wave subtask via `/task-work`.
