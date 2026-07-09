# ADR-ARCH-029 — Phased productionisation: local-first build (Phase 2), cloud-native AWS with data governance (Phase 3)

## Status

Accepted

**Date:** 2026-07-08
**Phase:** spans Phase 2 (voice + auth, local) → Phase 3 (AWS productionisation)
**Supersedes:** none. **Annotates** (forward-pointer, no change to current force):
[ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (on-device residency — now the *Phase 1–2*
posture, with Phase 3 revisiting it toward cloud-native), [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)
(NAS Keycloak placement — the *Phase-2-local* decision; Phase 3 makes cloud-hosted OIDC a first-class
target, not a fallback).
**Related:** [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-student posture —
holds through Phase 2; Phase 3 multi-user is a separate future decision),
[keycloak-validation-reference-lpa-poc.md](../../design/references/keycloak-validation-reference-lpa-poc.md)
(the FastAPI-in-Docker, env-driven, reverse-proxy-aware shape that already demonstrates cloud-portability).

## Context

study-tutor now has a second, explicit goal alongside "a working tutor for one student": it is a
**productionisation portfolio piece** — evidence of taking an AI system from local development to a
real cloud deployment (tracked in the operator's `ai-transition` career docs). That reframes the
data-residency question that [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) answered in a
hackathon context.

**Two facts make this a phasing decision, not a reversal:**

1. **ADR-015 was a hackathon-narrative choice, and already permits cloud.** Its driver was *"a submission
   claiming 'on-device AI tutor for your child' is undermined by cloud telemetry"* — a marketing posture,
   not a legal necessity. It already puts inference on **AWS Bedrock** and weights in **S3**, region-pinned
   to `eu-west-2`, with data-minimisation and documented exceptions. "On-device" always meant *"keep the
   high-value data household-scoped, use cloud deliberately and minimally,"* never literally no-cloud. It
   does not mention auth/identity at all — the "rules out cloud IdP" reading was a later extrapolation,
   stricter than 015 requires.
2. **Cloud + children's data is regulated, not forbidden.** Every ed-tech SaaS (Duolingo, Khan Academy)
   hosts minors' data in the cloud lawfully, by handling a governance surface: privacy notice, parental
   consent (UK Age Appropriate Design Code / UK-GDPR; COPPA in the US), region residency, encryption at
   rest + in transit, a data-processing agreement with the cloud provider, and data-subject-rights
   handling. On-device *sidestepped* that surface. For the productionisation goal, **building that surface
   correctly is the experience worth demonstrating** — it is the centrepiece of the Phase 3 story, not an
   obstacle to it.

## Decision

**Local-first build; cloud-native AWS is the destination. Phase the move; keep the seams portable.**

### D1 — Phase map
- **Phase 1 (done):** three-layer tutor, Postgres student model, on-device posture ([ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md), 015).
- **Phase 2 (active — voice + auth, local):** voice (FEAT-VOICE-*) and Keycloak auth (FEAT-AUTH-*) built
  and run on **NAS + GB10 over the tailnet** ([ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)).
  This is treated as a **realistic proxy** of the pre-cloud production app — the same containers, config
  model, and validation code that Phase 3 will lift.
- **Phase 3 (target — AWS productionisation):** deploy the same stack to AWS `eu-west-2` (UK) as a
  cloud-native service with a first-class data-governance surface. Revisits ADR-015 at that point via a
  superseding ADR; makes cloud-hosted OIDC (Keycloak-on-ECS, or Cognito) the primary auth target.

### D2 — Phase 2 portability guardrails (keep the Phase 3 move a config + infra swap, not a rewrite)
The Phase 2 auth/voice build MUST preserve these seams (all already implied by the design — this ADR makes
them load-bearing requirements, not incidental choices):
- **All deploy-specific config is env-driven** — `STUDY_TUTOR_AUTH_MODE`, `STUDY_TUTOR_OIDC_ISSUER`,
  `_AUDIENCE`, `_JWKS_URL`, `_STUDENT_CLAIM`, the PG DSN, model endpoints. No host, issuer, or region string
  literals in app code (design KC-D6 already mandates this).
- **`TokenResolver` stays deploy-agnostic** — validation logic knows nothing about the tailnet; swapping the
  issuer/JWKS to an ALB/ACM URL is pure config.
- **Realm-as-code, users-not-in-git** ([ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)/KC-D3)
  — the realm JSON imports into Keycloak-on-ECS unchanged; no-users-in-git means **no PII to migrate** to AWS.
- **Reverse-proxy / `X-Forwarded-Proto` discipline from day one** (as `lpa-platform-poc` already does with
  `--proxy-headers --forwarded-allow-ips`) so an ALB in front of the API in Phase 3 is a non-event.
- **Containerised, 12-factor, no host-specific paths** in app code — NAS mechanics (`/volume1`, DSM Task
  Scheduler) live only in runbooks/compose, never the app.

### D3 — What is explicitly *transient* (Phase-2-local scaffolding, replaced in Phase 3)
Named so nobody mistakes it for permanent architecture:
- `tailscale cert` + the `whitestocks.tailebf801.ts.net` MagicDNS issuer → replaced by **ACM cert + ALB +
  Route53** in Phase 3.
- The `extra_hosts` tailnet-IP JWKS workaround → **disappears** on AWS (normal DNS/service discovery); it is
  a symptom of tailnet DNS, not a design commitment.
- NAS/DSM deploy runbook → **ECS/Fargate + RDS** deploy in Phase 3.
The `iss`-vs-internal-URL *split itself* (design KC-D2/D6) is **not** transient — it survives to AWS
(browser-facing issuer vs internal JWKS fetch is the same pattern behind an ALB).

### D4 — Phase 3 data-governance surface (the productionisation deliverable, scoped now, built later)
When Phase 3 lands, ADR-015 is superseded by a posture that includes: UK region residency (`eu-west-2`),
encryption at rest + in transit, a minimal parental-consent record, data minimisation (already the KC-D3
habit — `student_id` claim, terse payloads), and a documented data-subject-rights/erasure path. This
surface **is** the portfolio artifact; it is not required for Phase 2.

## Alternatives considered

- **Reverse ADR-015 now and go cloud-native immediately.** Rejected — no need to run real cloud infra while
  the app is still being built; local NAS/GB10 is a faithful proxy and iterates faster and cheaper. Phasing
  keeps the build velocity while preserving the destination.
- **Keep on-device permanently; AWS only as a synthetic-data demo.** Rejected — a synthetic-only AWS deploy is
  a contrived "productionisation" story (no real data-governance surface, which is the valuable part) and
  leaves the dev→AWS path perpetually awkward. The operator's stated goal is a real cloud deployment.
- **Hybrid (session content local, identity/profile cloud) as the end state.** Rejected as a *destination*
  (more moving parts, a harder story to explain) though the phasing naturally passes through a
  cloud-auth/local-content state transiently.
- **Cognito instead of Keycloak-on-AWS for Phase 3.** Deferred to the Phase 3 ADR — Cognito is OIDC-compliant
  so the `TokenResolver` largely works, but Keycloak-on-ECS ports the realm-as-code with zero app change and
  tells a cleaner "same system, managed infra" story. Decide at Phase 3.

## Consequences

**Positive:**
- The Phase 2 voice + auth build proceeds **unchanged** — nothing here slows current work; it only names
  seams the design already has.
- The Phase 3 AWS move becomes a **config + infra swap** (issuer/JWKS/DSN env values, ACM/ALB/Route53, ECS/RDS)
  rather than a rearchitecture — the `extra_hosts` gotcha even *disappears*.
- The data-governance work is captured as the **explicit productionisation deliverable**, which is the
  portfolio value — reframing residency from an obstacle into the headline.
- No PII migration burden (users-not-in-git; realm-as-code is reproducible).

**Negative / accepted:**
- ADR-015 and ADR-028 now carry a forward-pointer and are known to be **phase-scoped** — a reader must hold
  "current force = Phase 2 local; trajectory = Phase 3 cloud" in mind until the Phase 3 superseding ADR lands.
- Phase 3 takes on real **data-controller responsibilities** (for a single child, with the parent's consent,
  in-region — manageable; scales with any future multi-user move, which is a separate ADR).
- The portability guardrails (D2) are now **requirements** on the Phase 2 build, not nice-to-haves — the
  FEAT-AUTH / FEAT-VOICE specs and reviews should enforce them.

## C4 diagram re-review status

No structural change **now** — this is a trajectory/requirements decision; Phase 2 topology is unchanged
(the Keycloak IdP added by ADR-028 stands). The C4 re-review gate is **not** triggered by this ADR. Phase 3
will regenerate L1/L2 for the AWS topology (ALB, ECS, RDS, cloud OIDC) as part of its own superseding ADR.

## References

- [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) — the residency posture this ADR phases
  (Phase 3 supersedes).
- [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) — the Phase-2-local Keycloak
  placement whose seams D2 keeps portable.
- [keycloak-validation-reference-lpa-poc.md](../../design/references/keycloak-validation-reference-lpa-poc.md)
  — env-driven, reverse-proxy-aware FastAPI+Keycloak shape already proving cloud-portability in a sibling repo.
- [keycloak-auth-user-management-design.md](../../design/keycloak-auth-user-management-design.md) KC-D6 — the
  env-driven config seam D2 depends on.
