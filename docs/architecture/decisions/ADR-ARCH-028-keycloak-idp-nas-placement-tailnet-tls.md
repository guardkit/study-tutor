# ADR-ARCH-028 — Self-hosted Keycloak IdP: NAS placement + tailnet-only TLS/issuer posture

## Status

Accepted

**Ratified:** 2026-07-08 via `/arch-refine` (KC-D1/D2 §5 ratification checklist —
[keycloak-auth-user-management-design.md §5](../../design/keycloak-auth-user-management-design.md)). Made
effective on ratification: the design's KC-D1/D2 checklist item is discharged; C4 **L1/L2** diagrams
regenerated to add the Keycloak IdP trust boundary (and, incidentally, the D9 HTTP/WS App Access adapter
that hosts the token-validation seam — previously absent from L2). Supersedes nothing.

> **Dated correction (2026-08-13, verified by Rich in the DSM console):** this ADR's
> durability claims ("the NAS is the documented durability home (**Hyper Backup** +
> nightly logical dumps)", :79; "volume-level Hyper Backup covers it implicitly too",
> :87; ":5434 … Hyper Backup", :130) are **wrong on the Hyper Backup half — it was
> never installed** (no Snapshot Replication or cloud backup either). The nightly
> logical dumps are real (14-day retention). The resulting no-off-box-copy gap is
> ledgered in `known-issues.md`; ADR-ARCH-033's erasure path carries the corrected
> story.

> **Dated note (2026-08-13):** the "ADR-015 rules out any cloud IdP" reading in this
> ADR's context/alternatives is **relaxed by
> [ADR-ARCH-033](ADR-ARCH-033-pilot-residency-governance-eu-west-2.md) D4** (ratified by
> Rich 2026-08-13): cloud-hosted OIDC is now permitted for the pilot inside 033's
> posture, and **Keycloak remains the identity provider** (Keycloak-on-cloud ports the
> realm-as-code with no PII to migrate; Cognito stays the recorded alternative). The NAS
> placement here remains the Phase-2/household record.

> **Trajectory note (2026-07-08):** this NAS placement is the **Phase-2-local** decision. Per
> [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md), **Phase 3
> makes cloud-hosted OIDC (Keycloak-on-ECS or Cognito) a first-class target, not a fallback** — the
> `tailscale cert` / MagicDNS issuer and the `extra_hosts` JWKS workaround (D2) are explicitly *transient*
> Phase-2 scaffolding (ACM/ALB/Route53 replace them; the JWKS workaround disappears). The `iss`-vs-internal-URL
> *split* survives. The "rules out cloud IdP" framing below is the Phase-2 posture, relaxed in Phase 3.

**Date:** 2026-07-08
**Phase:** Auth (D9 execution) — decided during the Keycloak auth + user-management build
**Supersedes:** none. This is a new decision.
**Related:** [ADR-ARCH-008](ADR-ARCH-008-mcp-only-agent-access.md) (auth posture already **amended on the
HTTP/WS surface only** by ADR-FLEET-003 / API-session-cross-device — this ADR makes that amendment
concrete by siting the IdP and its TLS story), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md)
(single-student posture — one realm user in prod), [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)
(UK on-device residency — **rules out any cloud IdP**, the load-bearing constraint here),
[ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) (the D4 project-independence
rule the placement follows; the `keycloak` DB co-locates in `study_tutor_postgres`). **Reference
implementation:** [keycloak-validation-reference-lpa-poc.md](../../design/references/keycloak-validation-reference-lpa-poc.md)
(the OIDC/JWKS mechanics and the issuer-vs-internal-URL split, proven in `lpa-platform-poc`).

## Context

Handoff decision **D9** turns authentication on: Keycloak fronts the study-tutor HTTP/WS API
(mobile app + Reachy), while MCP stdio keeps process-level trust ([ADR-ARCH-008](ADR-ARCH-008-mcp-only-agent-access.md),
amended). The *contract* does not change when auth turns on — only the `student_id` **derivation
source** does (static token table → validated Keycloak claim). What D9 did **not** settle, and what
this ADR ratifies, are two placement/infrastructure decisions the design raises as KC-D1/D2:

1. **Where does the IdP run?** [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) rules out any
   cloud IdP (a minor's identity data must stay on household-owned hardware). The realistic hosts are
   the **NAS (whitestocks)** or the **GB10 (promaxgb10-41b1)**.
2. **How is TLS/issuer done?** OIDC on native mobile effectively requires an **https issuer**
   (AppAuth-family libraries reject plain http off-loopback), so a self-signed/http dev posture is not
   viable for the real app.

**Two prerequisites are now cleared, which is why this is ratifiable today:**

- **NAS RAM op-check (the KC-D1 accepted-cost verification):** Whitestocks (DS918+, DSM 7.1.1-42962 U9)
  reports **8192 MB** total physical memory — the RAM upgrade is in. Keycloak's official sizing wants
  **750 MB minimum / 1–2 GB** container limit; against 8 GB total (shared with `study_tutor_postgres`)
  this is comfortable. The design's "NAS RAM is undocumented" accepted-cost is hereby **documented: 8 GB**.
- **OIDC mechanics de-risked:** the sibling `lpa-platform-poc` stack has run Keycloak-fronted OIDC since
  2026-05. It proves the JWKS-validation core, the **issuer-vs-internal-URL split** (the exact "container
  DNS can't resolve MagicDNS → fetch JWKS by tailnet IP while `iss` stays the ts.net name" gotcha), and
  the **attribute→claim protocol mapper** mechanism — see the reference note. It does **not** prove the
  two things this ADR decides (it runs on the **GB10**, `start-dev`, `sslRequired: none`, **http** issuer),
  so NAS placement and the DSM `tailscale cert` path remain the genuine residual risk.

## Decision

### D1 — Keycloak runs on the NAS (whitestocks)

Own container `study_tutor_keycloak` (`quay.io/keycloak/keycloak:26.6.x`, version pinned at build,
`start --optimized`, **1–2 GB container memory limit**), own `/volume1/docker/study_tutor_keycloak/`
dir, own host port, per the [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)
D4 project-independence rule.

- **Why NAS over GB10:** (a) a minor's identity data belongs with the other durable minor's data — the
  NAS is the documented durability home (Hyper Backup + nightly logical dumps); the GB10 "is NOT a backup
  target", so GB10-local Keycloak state would be a durability violation; (b) zero cost against the GB10's
  actively-budgeted ~105–110 GB unified-memory envelope the voice track is spending into; (c) immune to
  GB10 model-work churn; (d) all NAS deploy mechanics (SSH, sudoers, Task Scheduler, port allocation) are
  proven.
- **DB:** a second database + role (`keycloak`) inside the existing `study_tutor_postgres` container on
  `:5434` (the D4 rule separates *projects*, not a project's own services; Postgres 16 is in Keycloak
  26.6's supported range). `deploy/postgres/backup.sh` gains a second `pg_dump -d keycloak` line
  (realm/user state is durable and non-reindexable); volume-level Hyper Backup covers it implicitly too.
- **Realm-as-code:** realm/clients/roles/mappers exported as JSON into `deploy/keycloak/realm/` so the
  realm is reproducible. **Users are runbook-created and never in git** — the deliberate PII posture for a
  minor's identity (this is the one place study-tutor diverges from the lpa-poc reference, which commits
  test users to its realm JSON).
- **Exposure:** tailnet-only, **no WAN** — identical three-layer posture to the `:5434` Postgres deploy.

### D2 — TLS/issuer: Tailscale cert for the NAS MagicDNS name

Issuer pins to `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`, using a Let's Encrypt
cert minted by `tailscale cert` for the NAS's MagicDNS name, mounted into Keycloak (`start --optimized`
with `--https-certificate-file` / `--https-certificate-key-file`).

- **Known gotcha (carried from the 5434 deploy, proven in lpa-poc):** containers' embedded DNS may not
  resolve `*.ts.net`, so the GB10 `study_tutor_http` container fetches JWKS via the tailnet IP
  (`extra_hosts: whitestocks.tailebf801.ts.net:100.92.74.2`) while **issuer validation stays pinned to
  the ts.net name** — the `iss` string in tokens must match what devices used. This is the
  `STUDY_TUTOR_OIDC_JWKS_URL` override + `STUDY_TUTOR_OIDC_ISSUER` split in the design (KC-D6).

## Alternatives considered

- **Keycloak on the GB10.** Rejected as the primary — durability (GB10 is not a backup target) and the
  memory-envelope contention with the voice track. **Retained as a documented fallback:** if DSM's
  Tailscale package fights `tailscale cert`, moving placement to the GB10 (where `tailscale cert` is
  well-trodden) is viable because the rest of the design is placement-agnostic. This is a fallback, not
  the decision.
- **A cloud IdP (Auth0/Cognito/hosted Keycloak).** Rejected by [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)
  — a minor's identity data may not leave household-owned hardware.
- **`tailscale serve` in front of Keycloak instead of a mounted cert.** Held as the **first fallback** if
  the direct `tailscale cert` mount fights DSM — same issuer name, different TLS-termination mechanism.
- **Plain-http issuer (dev-style).** Rejected — `flutter_appauth` rejects non-https issuers off loopback,
  so the real app cannot use it. (This is exactly why the lpa-poc's http-only `start-dev` posture does not
  transfer.)
- **A separate Postgres container for Keycloak.** Rejected — the D4 rule separates projects, not a
  project's own services; co-locating the `keycloak` DB in `study_tutor_postgres` avoids a second
  container and a second backup target for no isolation benefit.

## Consequences

**Positive:**
- Learner/identity data stays on owned, backed-up hardware — strengthens [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)
  (minor-data-by-design) and keeps the durability story in one place (the NAS).
- Zero draw on the GB10 memory envelope the voice track is budgeting into — the two tracks stay decoupled.
- Reuses the proven `:5434` deploy posture (tailnet-only, nightly `pg_dump`, Hyper Backup) — no new
  operational surface class.
- The OIDC/JWKS mechanics and the issuer/internal-URL split are **already proven** in lpa-poc, so the
  build risk is concentrated on exactly one thing: the DSM cert path.

**Negative / accepted costs:**
- Devices talk to **two hosts** (NAS for tokens, GB10 for the API) — each keeps its own posture. Accepted.
- **NAS RAM** was undocumented; now **documented at 8 GB** and verified sufficient for a 1–2 GB Keycloak
  limit alongside Postgres — the accepted-cost is discharged, not merely deferred.
- **`tailscale cert` on DSM is less-trodden than on Linux** — the single residual risk. Mitigated by two
  ordered fallbacks (`tailscale serve`, then GB10 placement) and by lpa-poc having proven every other
  moving part.

## C4 diagram re-review status

System topology **changed**: the Keycloak IdP is a new external trust boundary that fronts the HTTP/WS
API. Ratification therefore **triggered the mandatory C4 re-review gate**. Revised C4 **Level 1**
([system-context.md](../system-context.md)) and **Level 2** ([container.md](../container.md)) were
regenerated to add the Keycloak IdP (NAS), the token-validation relationship, and the Reachy
device-grant pairing edge; L2 additionally gained the **D9 HTTP/WS App Access adapter** node that hosts
the `TokenResolver` seam (previously absent from the Phase-0-canonical L2 despite ADR-FLEET-003). The
Flutter mobile client itself remains unrepresented in these diagrams — a pre-existing C4 debt from the
voice/cross-device work, flagged for the next dedicated C4 pass, **not** introduced or resolved by this ADR.
Approved 2026-07-08 during the interactive `/arch-refine` session.

## References

- [keycloak-auth-user-management-design.md](../../design/keycloak-auth-user-management-design.md) §2
  (KC-D1/D2), §3 (rollout A1 standup + KC-G1 gate), §5 (ratification checklist).
- [keycloak-validation-reference-lpa-poc.md](../../design/references/keycloak-validation-reference-lpa-poc.md)
  — proven OIDC/JWKS mechanics + the issuer/internal-URL split (evidence for the "de-risked" claim).
- [keycloak-auth-scope-and-build-plan.md](../../research/ideas/keycloak-auth-scope-and-build-plan.md) —
  the feature decomposition (FEAT-AUTH-001…004) and sequencing this ADR unblocks.
- [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) — the residency constraint that rules out a
  cloud IdP.
- [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the D4 project-independence
  rule and the `study_tutor_postgres` instance the `keycloak` DB co-locates in.
