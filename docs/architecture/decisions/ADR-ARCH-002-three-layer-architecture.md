# ADR-ARCH-002 — Three-layer architecture: behaviour + knowledge + student model

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-001, ADR-ARCH-003, deepagents-patterns-review.md §1.3

## Context

The research literature (Daniel Bourke; Queensland AI Meetup;
`deepagents-patterns-review.md`) distinguishes two layers in effective
LLM systems: **fine-tuned behaviour** (how the model responds) and
**RAG knowledge** (what it responds about). Study Tutor's student-centric
design requires a third layer — **per-student state** (progress, topic
confidence, misconceptions, gamification status) — because tutoring
quality degrades without memory of the specific learner.

This three-layer split is specifically called out as the foundational
architecture for Study Tutor in `deepagents-patterns-review.md §1.3`.

## Decision

Commit to three independently updatable architectural layers:

1. **Layer 1 — Behaviour (fine-tuned Gemma 4 31B Dense LoRA):**
   teaches *how* the tutor responds. Socratic questioning,
   AO-alignment, grade-calibrated language, safeguarding posture.
   Located in the fine-tuned weights. Updated by re-running the
   Unsloth fine-tune on an updated `train.jsonl`.
2. **Layer 2 — Knowledge (ChromaDB curriculum RAG):** provides
   *what* the tutor draws from — curriculum content per subject,
   set text references, exam paper shapes. Located in per-subject
   ChromaDB collections seeded from user-provided Docling-processed
   sources. Updated by re-running the ingestion pipeline.
3. **Layer 3 — Student Model (Graphiti):** *who* is being tutored —
   per-student `TopicConfidence`, `Misconception`, `SessionEpisode`,
   `AssessmentObjectiveProgress`. Located in Graphiti graph DB.
   Updated per session-end via async write-back (see ADR-ARCH-003).

Independence properties:
- Retraining the model (Layer 1) does not invalidate the RAG index
  (Layer 2) or the student state (Layer 3).
- Adding curriculum content (Layer 2) does not require a retrain.
- Per-student state (Layer 3) evolves continuously without touching
  Layers 1 or 2.

## Alternatives considered

- **Two-layer only (behaviour + knowledge).** Rejected. Matches
  research literature but removes the key Study Tutor differentiator —
  a tutor that knows its specific student.
- **Four or more layers.** Considered (separating e.g. "curriculum
  knowledge" from "exam technique knowledge"). Rejected. The extra
  decomposition is not empirically motivated; both are retrieved via
  the same RAG path.
- **All-in-one fine-tune including student history.** Rejected.
  Would require re-finetuning per-student, scales poorly, and breaks
  the "independently updatable layers" property.

## Consequences

**Positive:**
- Matches research vocabulary; judges and peers see the architecture
  framed in familiar terms.
- Enables Phase 1/2 incremental build — Layer 3 doesn't block Layer 1
  shipping in Phase 0.
- Multi-subject expansion (post-hackathon) is a Layer-1 + Layer-2
  scaling story; Layer 3 shape is subject-agnostic.

**Negative:**
- Three integration points (LLM endpoint + ChromaDB + Graphiti) are
  three failure domains. Mitigated by fail-soft degradation (ADR-ARCH-014).
- Extra operational complexity vs a single-layer system. Accepted —
  the engagement and personalisation value is load-bearing for the
  hackathon submission narrative.

## References

- `deepagents-patterns-review.md §1.3`
- `docs/research/ideas/state-of-the-project-and-phase-recommendation.md §2.2`
- Daniel Bourke / Queensland AI Meetup talk on two-layer LLM architecture.
