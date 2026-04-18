# ADR-ARCH-001 — Use Domain-Driven Design structural pattern

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-002 (three-layer architecture), domain-model.md

## Context

Study Tutor's architecture needs to accommodate three Layer-wise
concerns (behaviour / knowledge / student model) plus a gamification
engine, all delivered in staged phases (P0 scaffolding → P1 student
model + harness → P2 gamification engine). The `deepagents-patterns-review.md`
research treats the three-layer split as primary. Per-phase features
introduce new concerns (Graphiti student model in P1; gamification state
in P2) with their own aggregates, invariants, and consumers.

The team is inheriting scaffolding patterns from `specialist-agent` —
which uses role-aware code organisation that is already DDD-flavoured
(roles as bounded contexts, per-role `role.yaml` with criteria and
prompts, a shared CommandRouter dispatch matrix).

## Decision

Adopt **Domain-Driven Design** as the structural pattern for Study
Tutor. Decompose into six bounded contexts:

1. Tutoring
2. Knowledge & Curriculum
3. Student Model
4. Gamification
5. Inference Runtime
6. MCP Transport

Two shared kernels:

1. **Domain Taxonomy** — Subject, Paper, Text, AssessmentObjective,
   Topic, GradeTarget, ConfidenceBand.
2. **Session Event Vocabulary** — session.started,
   session.turn_completed, session.completed, achievement.unlocked,
   quest.completed, quest.expired, boss_battle.completed.

One anti-corruption layer: **Inference Runtime** (`LLMClient`)
normalises across Ollama, Bedrock, and API providers.

See `domain-model.md` for full entity relationships.

## Alternatives considered

- **Modular Monolith** — reasonable for Phase 0 (small enough), but
  the three-layer architecture from `deepagents-patterns-review.md §1.3`
  is explicit in the research and maps directly to bounded contexts.
  Phase 1/2 additions (student model, gamification engine) benefit from
  DDD's ubiquitous-language vocabulary. Modular Monolith would force
  re-structuring later.
- **Layered Architecture** — rejected. A strict layered split (API →
  service → repository → DB) would obscure the bounded contexts and
  produce cross-layer coupling when the Gamification Engine needs to
  read Student Model aggregates.
- **Event-Driven Architecture** — rejected as primary pattern.
  Study Tutor's event vocabulary is important (Shared Kernel B) but
  the system is predominantly request/response (`tutor_turn`). Events
  are the seam between contexts, not the architectural foundation.
- **Clean / Hexagonal** — partially adopted for the Inference Runtime
  anti-corruption layer, but the full hexagonal pattern's
  ports-and-adapters rigour is over-specified for a single-user system.

## Consequences

**Positive:**
- Matches the research vocabulary (three-layer architecture, Player-Coach,
  session planner) used by `deepagents-patterns-review.md`.
- Maps cleanly onto specialist-agent inheritance.
- Explicit bounded contexts make Phase 1/2 feature boundaries
  self-documenting.
- Shared kernels prevent duplication of the domain taxonomy in four
  places.

**Negative:**
- Some DDD ceremony (aggregate invariants, event vocabulary) is
  over-specified for Phase 0 single-user scope. Accepted cost.
- Anti-corruption layer for inference costs an extra abstraction but
  pays back immediately (three providers × four contexts would
  otherwise create 12 coupling points).
- Developers unfamiliar with DDD need to learn the shared-kernel
  pattern; mitigated by `domain-model.md` reading as a reference.
