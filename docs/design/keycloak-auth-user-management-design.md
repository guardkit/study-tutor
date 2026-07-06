# Keycloak Auth + User Management — Design (D9 execution)

**Status:** Drafted 2026-07-06 (Fable window). Executes handoff decision **D9** ("Keycloak fronts
the HTTP/WS API" — resolved, do-not-reopen); closes contract **§11 OQ1** (sub→student_id mapping +
provisioning) with a recommendation; proposes the placement, client, and rollout decisions
**KC-D1…KC-D7** below for ratification (`/design-refine` / `/arch-refine` where marked).
**Decision authority (unchanged by this doc):** D9 + D8 (same-subject cross-device pickup) in the
[mobile-voice handoff](../handoffs/study-tutor-mobile-voice-conversation-starter.md) ·
[ADR-ARCH-008](../architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md) (amended: HTTP/WS
surface only; MCP stdio keeps process-level trust) ·
[ADR-ARCH-014](../architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md) (one
student, not multi-tenancy) ·
[ADR-ARCH-015](../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md) (household
residency — **rules out any cloud IdP**).
**Contract impact: none.** Contract §3 / binding §3 were written so that "the contract does not
change when auth turns on; only the derivation source does." Both docs stay frozen; §11 OQ1's
resolution is doc-text only and is folded in at the next coordinated `/design-refine` touch, not
as its own freeze event.
**Recon basis:** contracts + `http/auth.py` seam + app `IdentityProvider` seam + NAS/GB10 topology
+ Keycloak 26.6 facts, gathered and source-cited 2026-07-06 (auth-design recon pass).

---

## 1. What exists today (the seams this design fills)

- **Server:** every handler calls `_resolve_student_id(request)` →
  `resolve_student_from_token(header, config, student_store)`
  ([auth.py](../../src/study_tutor/http/auth.py)) in three ordered steps: (1) Bearer extraction
  (header only), (2) token→student_id via the static `STUDY_TUTOR_HTTP_TOKENS` table — **the only
  derivation-specific line** — (3) unseeded-student guard (`student_exists`, ASSUM-001 → 401).
  Keycloak replaces **step 2 only**. WS (Rev 1) authenticates with the same Bearer header on the
  upgrade request — no separate mechanism needed.
- **App:** `IdentityProvider` port (`currentPrincipal / signIn() / signOut()`);
  `Principal = {token, displayName}` (no studentId, by design); token injected at one choke point
  (`HttpSessionApi._headers()`, read fresh per request — a rotating token needs zero adapter
  changes); `Unauthenticated` → `routeToSignIn()` is the existing recovery path. Refresh, storage,
  and sign-out UI deliberately absent (phase-2 scope §5).
- **Robot:** uses the same dev-table token mechanism until Keycloak fronts `:8100` (voice design
  §7.4 / plan Out-list).
- **Provisioning:** `study-tutor seed-students` (idempotent `INSERT … ON CONFLICT DO NOTHING`),
  defaulting its ID list to the token-table values — the only coupling of seeding to the table.

## 2. Decisions

### KC-D1 — Placement: Keycloak runs on the NAS (whitestocks) ★recommendation

Own container (`study_tutor_keycloak`, image `quay.io/keycloak/keycloak:26.6.x` — official image
is multi-arch incl. arm64, though the NAS is x86 DSM; version pinned at build), own
`/volume1/docker/study_tutor_keycloak/` dir, own host port, per the ADR-ARCH-023 D4 independence
rule. **Why NAS over GB10:** (a) a minor's identity data belongs with the other durable minor's
data — the NAS is the documented durability home (Hyper Backup + nightly logical dumps); the GB10
"is NOT a backup target", so any GB10-local Keycloak state would be a durability violation;
(b) zero cost against the GB10's actively-budgeted ~105–110 GB unified-memory envelope that the
voice track is about to spend into (W0-R gates P0/R-G4); (c) immune to GB10 model-work churn;
(d) all NAS deploy mechanics (SSH, sudoers, Task Scheduler, port allocation) are proven.
**Accepted costs:** devices talk to two hosts (NAS for tokens, GB10 for API — each keeps its own
posture); NAS RAM is undocumented (pre-deploy op-check: record NAS RAM; Keycloak needs a **1–2 GB
container memory limit**, 750 MB minimum per official sizing); `tailscale cert` on DSM is less
trodden than on Linux (KC-D2 fallback covers this). Record the placement as a short ADR at
ratification (**ADR-ARCH-028** candidate, via `/arch-refine`).

**DB:** a second database + role (`keycloak`) inside the existing `study_tutor_postgres`
container on `:5434` (same project — the D4 rule separates *projects*, not a project's own
services; Postgres 16 is in Keycloak 26.6's supported range). `deploy/postgres/backup.sh` gains a
second `pg_dump -d keycloak` line (realm/user state is durable and non-reindexable, same class as
learner data); the volume-level Hyper Backup covers it implicitly via `pgdata` either way.
**Exposure:** tailnet-only, no WAN — identical three-layer posture to the 5434 deployment.

### KC-D2 — TLS/issuer: Tailscale cert for the NAS MagicDNS name ★recommendation

OIDC on devices effectively requires an https issuer (AppAuth-family libraries reject plain http
off-loopback). Issuer pins to
`https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` using a Let's Encrypt cert minted
by `tailscale cert` for the NAS's MagicDNS name, mounted into Keycloak (`start --optimized` with
`--https-certificate-file/--https-certificate-key-file`). Fallback if DSM's Tailscale package
fights this: front Keycloak with `tailscale serve` on the NAS, or (last resort) move placement to
the GB10 where `tailscale cert` is well-trodden — the rest of this design is placement-agnostic.
**Known gotcha carried from the 5434 deploy:** containers' embedded DNS may not resolve
`*.ts.net`, so the GB10 `study_tutor_http` container fetches JWKS via the tailnet IP
(`extra_hosts: whitestocks.tailebf801.ts.net:100.92.74.2`) while **issuer validation stays pinned
to the ts.net name** — the issuer string in tokens must match what devices used.

### KC-D3 — sub→student_id mapping (closes contract §11 OQ1) ★recommendation

**Keycloak user attribute → custom token claim.** Each Keycloak user carries a `student_id`
attribute; a realm protocol mapper emits it as a `student_id` claim in the access token; the
server derives `student_id` from that claim **after** signature/issuer/audience/exp validation,
then the existing unseeded guard still runs (a mis-provisioned attribute yields 401, never a 500 —
ASSUM-001 already covers this). **Why not a `keycloak_sub` column on `student`:** the attribute
keeps identity mapping in one system, needs no schema migration, and keeps the server stateless
about the mapping; the claim is trustworthy because the token is validated.
**Provisioning story (the other half of OQ1):** create the Keycloak user (with `student_id`
attribute) in the admin console **and** run `study-tutor seed-students --student-ids <id>` —
two idempotent steps, captured in the standup runbook. `seed-students` gains `--student-ids` as
the primary path (its token-table default becomes legacy). Realm config (realm, clients, roles,
mappers — **not** users/secrets) is exported as JSON into the repo (`deploy/keycloak/realm/`) so
the realm is reproducible; users are runbook-created (secrets never in git).

### KC-D4 — Clients and flows

| Client | Type | Flow | Notes |
|---|---|---|---|
| `study-tutor-app` (Flutter) | public | **Authorization Code + PKCE (S256 enforced)** | via `flutter_appauth` (Keycloak officially recommends AppAuth); custom-scheme redirect URI; `scope=offline_access` → offline token so the family device stays signed in (offline idle default 30 days — refresh at least monthly; "Offline Session Max Limited" stays disabled → no lifespan expiry) |
| `reachy-robot` | public, device-flow enabled | **OAuth 2.0 Device Authorization Grant** | the robot must act **as the student** (D8: same subject → same `student_id` → session pickup — client-credentials would mint a machine identity and break D8). One-time pairing: robot surfaces `user_code`, a parent approves at `/realms/study-tutor/device` from any browser, robot stores the offline token on the Pi and refreshes. Token injected into `ask_tutor`/tool HTTP calls from a root-owned file/env (FEAT-VOICE-004 alignment) |
| `live-suite` (dev realm only) | confidential | Direct Access Grant (password) | test-only client so the live contract suite can mint tokens for `lilymay`/`alex` test users; never exists in the prod realm |
| server (`study_tutor_http`) | — | resource server | validates JWTs locally against JWKS; no client registration required |

Realm roles `student` and `parent` are **created now** (cheap, schema-stable) but only `student`
is required by the API in this phase (KC-D5).

### KC-D5 — Parent role: reserve, don't build ★recommendation

Parent visibility (Reachy queries, preference propagation — gamification research) needs its own
product design; bolting read-endpoints on now would outrun ADR-ARCH-014. This phase: the `parent`
realm role exists; no parent user, no parent endpoints; parent-visible progress remains the
existing admin-side option. Revisit trigger: the gamification/dashboard track picking up
parent-facing scenarios.

### KC-D6 — Server validation architecture: TokenResolver seam, sibling module

Introduce `TokenResolver` protocol (`async resolve(token) -> student_id`, raises
`Unauthenticated`); `resolve_student_from_token` keeps its outer contract (Bearer extraction +
unseeded guard) and delegates step 2 to the injected resolver.
- **`TableTokenResolver`** (in `auth.py`, unchanged behaviour) — remains the dev-flavour default
  and the interim/degenerate mode; the hermetic test suites keep it (they are already
  derivation-agnostic apart from fixtures).
- **`KeycloakTokenResolver`** in a **new sibling module `http/auth_keycloak.py`** — PyJWT +
  `PyJWKClient` (cached JWKS, kid-rotation aware); validates signature, `iss` (ts.net issuer
  string), `aud`, `exp`; extracts the `student_id` claim (KC-D3). The AC-005 tripwire
  (`test_no_keycloak_jwt_imports`) is **kept and re-scoped**: `auth.py` stays JWT-free forever;
  the new module carries the imports.
- **Selection by env:** `STUDY_TUTOR_AUTH_MODE=table|keycloak` (+ `STUDY_TUTOR_OIDC_ISSUER`,
  `STUDY_TUTOR_OIDC_AUDIENCE`, `STUDY_TUTOR_OIDC_JWKS_URL` optional override for the
  extra_hosts/IP-fetch gotcha, `STUDY_TUTOR_OIDC_STUDENT_CLAIM` default `student_id`). Fail-fast
  at boot on incomplete keycloak-mode config (SystemExit, matching the DSN discipline).
- **WS**: zero extra work — same `_resolve_student_id` at upgrade time (binding §2.1).
- **`/__dev__/reset`**: unchanged (existence-gated); dev flavour keeps table mode, so the route
  never coexists with Keycloak. Assert that pairing in the spec.

### KC-D7 — App sign-in: real OIDC behind the unchanged port

`KeycloakIdentityProvider` implements the existing 3-member port. Deps: `flutter_appauth` +
`flutter_secure_storage` — a deliberate DoD zero-deps scope event, same pattern as voice's
(record it). The port's **sync** `currentPrincipal` stays: the adapter refreshes proactively in
the background (appauth token response carries expiry) and the existing
`Unauthenticated → routeToSignIn()` path remains the hard fallback (signIn() attempts silent
refresh before interactive browser flow). SignInScreen gains loading/failure/cancel states and a
sign-out affordance (port already has `signOut`). Composition: `main.dart` only —
`composeSessionApi`'s parameter de-types from concrete `FakeIdentityProvider` to the port
(FakeSessionApi keeps the concrete fake for its introspection hook); hermetic flavour unchanged.

## 3. Rollout (no big-bang, reversible at every step)

1. **A1 standup (operator + agent runbook):** NAS container + `keycloak` DB + realm-as-code import
   + tailscale cert + users (Lilymay; dev realm additionally Alex + live-suite client) + backup.sh
   extension. Gate KC-G1: device browser reaches the https realm; discovery doc serves; NAS RAM
   recorded before/after.
2. **A2 server (flag-gated):** TokenResolver refactor + `auth_keycloak.py` + env wiring. Default
   mode stays `table` everywhere — merging A2 changes nothing in prod. Gate KC-G2: live contract
   suite green against a dev deploy in `keycloak` mode (tokens minted via the live-suite client);
   hermetic suite untouched and green in table mode.
3. **A3 app:** Keycloak adapter + sign-in UX against the A2 dev deploy. Gate KC-G3: end-to-end on
   the real phone — sign in via browser flow, session lifecycle, token refresh across a >5-min
   idle, 401-recovery path.
4. **A4 robot pairing:** device-grant pairing + token file + `ask_tutor` bearer injection —
   sequenced **after** voice R3 (needs `ask_tutor` to exist). Gate KC-G4: the D8 proof — phone
   session resumed by the robot under the **same Keycloak subject** (this replaces the dev-table
   variant of AC-R2).
5. **Cutover:** prod flavour flips to `keycloak` mode via the dev-deploy runbook pattern (env
   change + restart); rollback is the same env flip back to `table`. The static token table is
   retired from *prod* config only after KC-G3 holds for a week of real use.

Voice-track independence: dev flavour stays on table mode, so **no voice wave blocks on, or is
blocked by, this design** — the only shared artifact is FEAT-VOICE-004's token-injection detail
(A4 aligns with R3, whichever lands second wires the bearer file).

## 4. Out of scope

- Multi-tenancy / more-than-household students (ADR-ARCH-014 stands; dev realm's `alex` remains a
  test principal).
- Parent-facing endpoints/UI (KC-D5 — reserved role only).
- MCP/stdio surface auth (ADR-ARCH-008 process-level trust unchanged).
- Token refresh sophistication beyond appauth defaults (rotation-on-refresh can be revisited if
  "Revoke Refresh Token" is ever enabled).
- WAN exposure of anything (tailnet-only posture unchanged).

## 5. Ratification checklist (before A1 builds)

- [ ] KC-D1 placement + KC-D2 TLS story → `/arch-refine` (ADR-ARCH-028 candidate).
- [ ] KC-D3 mapping + provisioning → closes contract §11 OQ1; fold the §11 text edit into the
      next coordinated `/design-refine` touch (doc-only, no wire change, no standalone freeze).
- [ ] KC-D4 robot device-flow + KC-D5 parent deferral → owner sign-off (product-shaped).
- [ ] NAS RAM op-check recorded (KC-D1 accepted-cost verification).

---

*Authored 2026-07-06 in the Fable window per the model-allocation rule (voice plan §0a): design by
Fable; feature-spec/plan next (Fable if window remains, else Opus with this doc as `--context`);
builds by Opus. Companion scope/build plan:
[keycloak-auth-scope-and-build-plan.md](../research/ideas/keycloak-auth-scope-and-build-plan.md).*
