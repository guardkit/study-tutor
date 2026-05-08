---
id: TASK-REV-NATS-001
title: 'Plan: study-tutor NATS Fleet Integration (3-phase)'
task_type: review
status: review_complete
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
feature_id: FEAT-NATS
parent_review: null
clarification:
  context_a:
    timestamp: 2026-05-08T00:00:00Z
    decisions:
      focus: all
      depth: comprehensive
      tradeoff: quality
      mode: streamlined
      rationale: 'Review scope was exhaustively defined in docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md (951 lines, file:line citations across specialist-agent / jarvis / forge / nats-core / nats-infrastructure). /task-review redundant given the existing review doc supersedes its output.'
  context_b:
    timestamp: 2026-05-08T00:00:00Z
    decisions:
      approach: 'specialist-agent class-based pattern (NATSAdapter + CommandRouter + manifest factory + role registry)'
      execution: 'parallel where dependency graph allows (12 waves total: P1=6, P2=2, P3=4)'
      testing: standard
      assum_007_resolution: 'Option C (defer); jarvis MUST NOT duplicate-dispatch; tutor-side dedup deferred to TASK-NATS-FU-005 contingent on real runbook observation'
tags:
  - nats
  - fleet-integration
  - feat-nats
  - phase-1
  - phase-2
  - phase-3
  - demo-critical
---

# Task: Plan study-tutor NATS Fleet Integration (3-phase)

## Description

Kanban trail entry for the planning work that produced the build plan for study-tutor's NATS fleet integration. Planning was executed via the streamlined path:

1. **Research**: Multi-agent review of three sibling repos (specialist-agent, jarvis, forge) plus nats-core and nats-infrastructure → [docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md](../../docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md) (951 lines)
2. **Three project decisions** taken on 2026-05-08:
   - Phase 1 includes live registration + heartbeat (no stub-yaml fallback)
   - Session durability uses hybrid Graphiti, not JetStream KV
   - Stale-agent reaper deferred to jarvis post-demo (jarvis-owned)
3. **Gherkin spec generated** via `/feature-spec` → [features/nats-fleet-integration/nats-fleet-integration.feature](../../features/nats-fleet-integration/nats-fleet-integration.feature) (31 scenarios across 8 groups)
4. **Build plan generated** via `/feature-plan --streamlined` → 18 tasks across 3 phases (Phase 1: 10, Phase 2: 3, Phase 3: 5) plus 5 post-demo follow-ups
5. **ASSUM-007 resolved** via deferral (Option C); contingent follow-up captured as TASK-NATS-FU-005

## Outcome

Review complete. All implementation tasks scaffolded under `tasks/backlog/nats-fleet-integration/`. Feature YAML at `.guardkit/features/FEAT-NATS.yaml`. Gherkin scenarios tagged with `@task:<TASK-ID>` via Step 11 BDD linker.

## References

- **Canonical review**: [docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md](../../docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md)
- **Gherkin spec**: [features/nats-fleet-integration/nats-fleet-integration.feature](../../features/nats-fleet-integration/nats-fleet-integration.feature)
- **Implementation guide**: [tasks/backlog/nats-fleet-integration/IMPLEMENTATION-GUIDE.md](../backlog/nats-fleet-integration/IMPLEMENTATION-GUIDE.md)
- **Feature YAML**: [.guardkit/features/FEAT-NATS.yaml](../../.guardkit/features/FEAT-NATS.yaml)
- **Superseded scope doc**: [features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md](../../features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md) (kept as historical reference; do not act on its task list)
- **Source bug catalogue**: `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md` (lines 60-138)

## Demo deadline

2026-05-11 (Phase 1 must ship). Phases 2-3 ship before DDD South West demo on 2026-05-16.
