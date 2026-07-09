# ADR-ARCH-015 — UK on-device data residency; Gemini as explicit exception

## Status

Accepted — **phase-scoped (Phase 1–2).**

> **Trajectory note (2026-07-08):** this on-device posture is the **Phase 1–2 default** and remains in
> force for the local NAS/GB10 build. Per [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md),
> **Phase 3 revisits it toward a cloud-native AWS posture** (UK `eu-west-2` + a data-governance surface),
> at which point a superseding ADR replaces this one. Not yet superseded — no change to current force.

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-007, DEC-02, DEC-08, ASSUM-013, [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md) (phasing toward cloud-native)

## Context

Study Tutor's product story emphasises on-device privacy. Student
tutoring data is sensitive — sessions reveal what a student struggles
with, what they don't understand, their writing samples, their
Year-10-level mistakes. A submission claiming "on-device AI tutor for
your child" is undermined by cloud telemetry.

Three data-residency facts shape the architecture:

1. **Layer 1 inference.** Primary on GB10 (household network).
   Validation on AWS Bedrock — region pinned to `eu-west-2` (London)
   if Custom Model Import for Gemma 4 31B is supported there;
   otherwise `us-east-1` (Virginia) or `us-west-2` (Oregon) as a
   demo-week fallback. Verified during FEAT-PO-004 setup
   (21–22 Apr 2026); see ASSUM-007.
2. **Layer 2 knowledge.** ChromaDB on MacBook; source PDFs in
   `domains/*/sources/` (user-provided, gitignored).
3. **Layer 3 student model.** Graphiti — FalkorDB on Synology NAS
   (household), but entity extraction via Google Gemini (Google
   Cloud, GCP region).

Gemini sees session summaries during write-back. This is an explicit
exception to on-device residency.

## Decision

**Default posture: on-device + household Tailscale network.**

| Data | Location | Controlled by |
|---|---|---|
| Session turns (in-memory during session) | MacBook or tutor host | Filesystem permissions |
| Session exports (JSON) | Local filesystem | Filesystem permissions |
| Student Model (Graphiti entities) | Synology NAS FalkorDB | Tailscale + FalkorDB auth |
| Fine-tuned model weights | GB10 (household) + S3 (Bedrock ingestion) | IAM + Tailscale |
| RAG curriculum content | MacBook ChromaDB | Filesystem |
| Source documents | `domains/*/sources/` gitignored | Filesystem; never committed |
| Logs | MacBook stderr + rotating file (P1+) | Filesystem |

**Explicit exception: Google Gemini 2.5 Pro** for Graphiti entity
extraction. Documented in this ADR and in the submission write-up.

Mitigations for the exception:

- Session summaries to Gemini are **terse, topic-focused**. Full
  student names are not required for entity extraction; use
  `student_id` (UUID or short handle).
- No school identifiers, parental contact info, or full turn
  transcripts in the payload to Gemini. Just AO-level observations
  and topic references.
- ASSUM-013 tracks the assumption that Gemini payloads stay clean;
  revisit in Phase 1 entity-extraction spike.
- If PII leaks, add a pre-Gemini redaction layer (ADR-TBD in Phase 1).

**Bedrock exception** — AWS Bedrock is a cloud service, but:
- **Region:** preferred `eu-west-2` (London — UK-region) if Bedrock
  Custom Model Import supports Gemma 4 31B there. If `eu-west-2` does
  not yet list Gemma 4 31B, the demo-week fallback is `us-east-1`
  (Virginia) or `us-west-2` (Oregon) — a deliberate residency
  trade-off for the hackathon, accepted because only prompts and
  responses transit (see next bullet). The actual region is verified
  during FEAT-PO-004 setup (21–22 Apr 2026) via the AWS Bedrock
  console's "Custom model import" region selector; the verification
  outcome is recorded in TASK-CDR-003 and ASSUM-007.
- Only **prompts and responses** pass through; no student identity
  or session metadata beyond what the prompt carries.
- Fine-tuned model weights are in S3 (user's AWS account).
- Residency posture for the non-UK fallback is a Phase 3 concern —
  post-hackathon migration to a UK region (or a local-only inference
  path) once `eu-west-2` Custom Model Import catches up.

**No** telemetry, analytics, error reporting to any third-party
service (Sentry, LogRocket, etc.) in any phase.

## Alternatives considered

- **No cloud at all; local Graphiti LLM (e.g. Qwen-on-GB10).**
  Rejected for Phase 1 MVP per DEC-08 — Gemini is paid-for, known
  latency, and moving it local conflicts with DEC-07 training
  schedule. Revisit post-hackathon.
- **End-to-end encryption of Gemini payloads.** Rejected as
  overkill — Gemini is the LLM that needs to read the payload to
  extract entities. Encryption at rest / in transit is already
  provided by Google's TLS.
- **Multi-region Bedrock.** Considered; out of scope for
  single-user hackathon.

## Consequences

**Positive:**
- Submission narrative holds up — "AI tutor for your child,
  household-scoped" is true for all of the high-value data.
- Single documented exception (Gemini), clean story.

**Negative:**
- One data-residency exception is one more thing to monitor.
  Mitigated by ASSUM-013 and the Phase 1 redaction review.
- Dependency on Gemini availability for Phase 1+ entity extraction.
  Fail-soft: if Gemini is down, session-end returns successfully and
  the write-back goes into a replay queue.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`.
- `gemma4-hackathon-submission-plan.md` — privacy story.
