---
id: TASK-REV-7DC0
title: "Plan: Graphiti Student Model"
status: in_review
feature_id: FEAT-1773
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
priority: high
task_type: review
tags: [feature-plan, graphiti, student-model, phase-1, async, knowledge-graph]
complexity: 7
test_results:
  status: pending
  coverage: null
  last_run: null
decision: implement
clarification:
  context_a:
    timestamp: 2026-04-27T00:00:00Z
    decisions:
      focus: all
      tradeoff: quality
      concerns: all (async correctness, scoping/isolation, prompt-injection-via-misconception)
  context_b:
    timestamp: 2026-04-27T00:00:00Z
    decisions:
      approach: 1 (build-plan-aligned 6 slices, recommended)
      execution: parallel (Conductor for Wave 1 + Wave 2)
      testing: standard (full quality gates)
generated_subtasks:
  - TASK-GSM-001
  - TASK-GSM-002
  - TASK-GSM-003
  - TASK-GSM-004
  - TASK-GSM-005
  - TASK-GSM-006
context_files:
  - features/graphiti-student-model/graphiti-student-model_summary.md
  - features/graphiti-student-model/graphiti-student-model.feature
  - features/graphiti-student-model/graphiti-student-model_assumptions.yaml
---

# Task: Plan: Graphiti Student Model

## Description

Feature planning task for **FEAT-PH1-001: Graphiti Student Model** — a persistent knowledge-graph-backed student model providing a learner profile (identity, subjects, texts, topics, AOs, misconceptions, topic confidence), three core query helpers (state read, topic recommendation, session-completion record), a one-off seeding script, and async fire-and-forget write-back at every write point per ADR-ARCH-019 / DDR-002 / DDR-003.

## Scope

**Included** (38 BDD scenarios across 5 implementation groups):

- **Group A — Schema** (8 scenarios): Student / Subject / Text / Topic / AO / Misconception / TopicConfidence + 6 relationships
- **Group A — Episodes** (3 scenarios): `session_completed`, `topic_confidence_updated`, `misconception_observed`
- **Group A/D — Client wrapper** (3 scenarios): Lazy import, graceful degradation, store unreachable
- **Group A/B — Query helpers** (8 scenarios): `get_student_state`, `get_topic_recommendations`, `record_session_completion` + recommendation count / cooldown / band-mapping
- **Group B/D/E — Async write-back** (12 scenarios): Single fire-and-forget shared helper per DDR-002, latency / failed-write / concurrency / crash / shutdown / read-your-writes / extraction-LLM / embeddings-endpoint
- **Group C/D — Seeding** (4 scenarios): Idempotency, store unreachable, unknown learner, concurrent

**Cross-cutting tags**: `@async` (6), `@security` (3), `@concurrency` (3), `@scoping` (3), `@integration-boundary` (2), `@seeding` (3), `@module-load` (1), `@crash-recovery` (1)

**Excluded**: CC-14 (runtime LLM params) lives in the Inference Runtime feature.

## Architectural Anchors

- **ADR-ARCH-019** — Every-write-point async, handler-return budget asserted at 2 seconds
- **DDR-002** — Coach AsyncSubAgent owns its own writes (per-write ownership, not session-end batch)
- **DDR-003** — Events emit on state transition (no persisted episode for abandoned sessions)
- **CC-13** — Every Graphiti write site fire-and-forget (failures log-only, never surface to caller)
- **LES1 §3** — Graceful module load (lazy import; module loads when graphiti-core absent)

## Review Scope (Context A)

- **Focus**: All — correctness, architecture, async safety, security, performance
- **Trade-off priority**: Quality — correctness and safety primary
- **Specific concerns to deep-dive**:
  1. Async correctness (fire-and-forget, crash recovery, write ordering)
  2. Scope / isolation (group_id boundaries, cross-learner leakage)
  3. Prompt-injection via misconception field (untrusted text into LLM extraction)

## Open Assumptions

- **ASSUM-007** — Process-shutdown grace period (30s) inferred; not specified. Should be validated during Phase 1 demo testing and may need to become a configurable env var.
- **ASSUM-008** — Group identifier discrepancy: `phase-1-scope.md` specifies `fleet:appmilla` while specialist-agent code uses `appmilla-fleet`. study-tutor will follow the scope doc.

## Acceptance Criteria

- [ ] Technical options analysed against ADR-ARCH-019 / DDR-002 / DDR-003 constraints
- [ ] Risk analysis covers async correctness, scoping isolation, and prompt-injection
- [ ] Effort estimation per implementation group (schema / episodes / client / queries / async / seeding)
- [ ] Recommended approach identified with rationale
- [ ] Decision checkpoint reached
- [ ] If [I]mplement chosen: subtasks generated with task_type, parent_review, feature_id, wave, implementation_mode
- [ ] If [I]mplement chosen: IMPLEMENTATION-GUIDE.md includes mandatory Mermaid diagrams (data flow, integration contract, task dependency graph) and §4 Integration Contracts where cross-task data dependencies exist
- [ ] If [I]mplement chosen: structured YAML feature file generated at `.guardkit/features/FEAT-XXXX.yaml`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- N/A — review/analysis task, no implementation work in this task

## Implementation Notes

This is a **review task**. Use `/task-review TASK-REV-7DC0 --mode=decision --depth=standard` to execute the analysis, present a decision checkpoint, and (on [I]mplement) generate subtasks + IMPLEMENTATION-GUIDE.md + structured YAML feature file.

Context files seeded:
- `features/graphiti-student-model/graphiti-student-model_summary.md` (38 scenarios summary)
- `features/graphiti-student-model/graphiti-student-model.feature` (BDD scenarios)
- `features/graphiti-student-model/graphiti-student-model_assumptions.yaml` (8 assumptions)

Reference docs to load during review:
- `docs/research/ideas/phase-1-scope.md`
- `docs/research/ideas/phase-1-build-plan.md`
- `docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md`
- `docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md`
- `docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md`
- ADR-ARCH-005, ADR-ARCH-022 (Graphiti as long-term memory substrate)
