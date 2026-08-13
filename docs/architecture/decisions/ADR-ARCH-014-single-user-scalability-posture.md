# ADR-ARCH-014 — Single-user scalability posture; multi-student schema-ready

## Status

Accepted

> **Dated note (2026-08-13):** the **runtime clause** ("single-user only through
> Phase 2") is **superseded by
> [ADR-ARCH-034](ADR-ARCH-034-pilot-multi-user-accounts.md) D4** (ratified by Rich
> 2026-08-13), and the **Bedrock inference scale-out escape hatch** ("Bedrock already
> supports concurrent per-student inference; no new work") is **retired as dead** —
> Bedrock Custom Model Import cannot serve the fine-tune (no Gemma architecture support,
> no eu-west-2; AWS research 2026-07-06 §2). The **multi-student schema posture STANDS
> and is vindicated**: ADR-034 D1's receipts (the student_id partition at every call
> site, the 2026-08-04 byte-identical live isolation proof) are this ADR's day-1 bet
> paying out.

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-006, ADR-ARCH-008, ASSUM-015

## Context

Study Tutor's reference user is Lilymay (single student). The hackathon
submission is a personal-learning-tool pitch with a multi-subject,
multi-student roadmap implied but not implemented. Post-hackathon
multi-student deployment (e.g. for a school cohort) is a Phase 3+ /
post-hackathon concern.

Scalability concerns fall into three categories:

1. **Concurrent users.** Phase 0/1/2 = 1. Post-hackathon = TBD.
2. **Data volume.** Per-student Graphiti graph is small (hundreds of
   sessions × per-turn annotations) — under 1GB even over years.
3. **Inference throughput.** Single-user = 1 concurrent turn max.
   Bedrock scale-to-zero handles multi-user if ever needed.

The Graphiti schema must be designed to allow multi-student without
re-migration later — cheap now, prohibitively expensive post-hoc.

## Decision

**Runtime:** single-user only through Phase 2. No load balancing,
horizontal scaling, multi-region deployment, HA targets. Session
manager is single-process. If GB10 / Synology / tutor host crash,
Lilymay loses the tutor temporarily — acceptable.

**Schema:** multi-student-ready from day 1 via Graphiti group IDs
(`student:{student_id}`, `subject:gcse-english`). Every persisted
entity is scoped by student. Queries always include the group-ID
filter. No singleton "current student" in the schema.

**Inference scale-out path:** already captured via Bedrock
(ADR-ARCH-006). If/when multi-user deployment is needed, Bedrock
already supports concurrent per-student inference; no new work.

**Fail-soft degradation:**
- Graphiti write-back failure → log, return success to user;
  replay queue is a Phase 3 consideration.
- Inference provider failure → surface as MCP error; no retry in
  Phase 0 (ADR-ARCH-011).
- ChromaDB / RAG retrieval failure (Phase 1+) → degrade to
  no-RAG response; log; return.

## Alternatives considered

- **Multi-tenancy from day 1 (full auth stack, per-tenant isolation).**
  Rejected. Over-engineering; no Phase 0/1/2 user demand; would absorb
  the entire hackathon timeline.
- **Single-tenant runtime and single-tenant schema.** Rejected.
  The per-student group-ID schema is ~5 lines of code cost and saves
  a full migration post-hackathon.
- **Multi-user runtime via session sharding.** Rejected. No one is
  asking for it; premature.

## Consequences

**Positive:**
- Phase 0 surface is small; no auth / session-isolation complexity.
- Future multi-student story is schema-ready — a real scale-up path.
- Bedrock dual inference path already covers multi-user inference
  capacity if needed.

**Negative:**
- Post-hackathon multi-student deployment requires authentication +
  per-student session isolation work. Scoped as Phase 3+.
- A hard crash of GB10 / Synology loses the tutor temporarily.
  Accepted; single-user household; not a service.

## References

- DEC-05 (primary interface decision).
- ASSUM-015 (Reachy arrival — ties into single-user deployment).
