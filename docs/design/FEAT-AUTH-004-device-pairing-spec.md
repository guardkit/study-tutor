# FEAT-AUTH-004 — Reachy device pairing (OAuth 2.0 device authorization grant)

**Status:** SPEC — drafted 2026-08-14, awaiting Rich's spec word on the digest
([`FEAT-AUTH-004-digest.md`](FEAT-AUTH-004-digest.md); playbook amendment 6 — he rules on
the digest, never the raw spec).
**Feature row:** `docs/research/ideas/keycloak-auth-scope-and-build-plan.md:31` — *"Reachy
pairing: device-grant flow, Pi token file + refresh, `ask_tutor` bearer injection; KC-G4 =
the D8 same-subject resume proof."*
**Gating deps, both DISCHARGED:** FEAT-AUTH-002 (server validation — KC-G2 passed
2026-07-19, `docs/study-tutor-plan-of-record.md:36`) **and** voice R3 (`ask_tutor` exists —
full round trip through the robot's own tool code, 2026-08-13,
`docs/study-tutor-plan-of-record.md:37`).
**Design parent:** `docs/design/keycloak-auth-user-management-design.md` — KC-D4 (client and
flow, `:104`), KC-D6 (server seam, `:119`), rollout step A4 + gate KC-G4 (`:172`).

**Receipt convention:** every factual claim below names a `file:line` in this repo or a row
of THE PLAN. Claims that could only be settled against a live host are marked
**[verify at build]** — this spec was written from files alone (docs lane; no live host, no
realm probe, no container).

---

## 1. What this feature is, in one paragraph

The Reachy robot stops holding a shared secret and starts holding **its own Keycloak
identity for Lilymay**. A one-time pairing — the "sign-in on a TV" pattern — mints an
offline token on the Pi under Lilymay's own Keycloak subject; the robot refreshes it
itself, injects it into every call to the spark, and can be un-paired from Keycloak alone
without touching her phone. When it lands, static bearer tokens have no consumer left and
table mode retires — the end of an interim that has outlived its replacement by a month
(`docs/study-tutor-plan-of-record.md:36`: `http/auth.py` predates `http/auth_keycloak.py`
by twelve days and "is the original interim auth that was never retired once its
replacement gated").

## 2. Why now — the two forcing facts

1. **Ruling E3 (Rich, 2026-08-07):** *"the static bearer is entered per-robot via the app's
   settings web UI and persisted on-robot. FEAT-AUTH-004 (per-device pairing) is sequenced
   AFTER, untouched"* — `docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:35-36`,
   with the forcing date named in the design pass:
   *"September, with Dulcie's robot, is the natural forcing date"*
   (`docs/design/robot-app-distribution-design-pass-2026-08-07.md:336-339`).
2. **The rotation taught what a static bearer costs.** Ruling queue #9
   (`docs/study-tutor-plan-of-record.md:512-527`): a bearer that authenticated as a
   14-year-old was published in two public repos; closing it required cutting over **three
   separate copies on the robot alone** — the Scholar app config via its settings API,
   `sitecustomize.py`, and `/home/pollen/lattice-backup/`, *"which is the one a later
   restore would have used to resurrect a dead token"* (`:513-515`) — **and** rebuilding and
   re-installing the APK on her phone (`:516-519`). The interim fix was to give the robot
   its **own** static bearer, *"revocable without reflashing her phone"* (`:36`). This
   feature makes that revocation a Keycloak session delete instead of a `.env` edit plus a
   container recreate, and removes the shared-secret class entirely.

**One live fact, pinned (do not re-probe):** the realm already advertises
`urn:ietf:params:oauth:grant-type:device_code` — verified live 2026-08-14, ruling queue
#12, `docs/study-tutor-plan-of-record.md:570-572`: *"the headless flow it needs exists
server-side today."* The realm-as-code agrees: `reachy-robot` is a public client with
`"oauth2.device.authorization.grant.enabled": "true"`
(`deploy/keycloak/realm/study-tutor-realm.json:119-132`).

## 3. Preconditions

| # | Precondition | State |
|---|---|---|
| P1 | Keycloak live on the NAS; realm `study-tutor`; issuer `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` | ✅ `docs/runbooks/HANDOFF-batch-c-auth-live.md:75` |
| P2 | Server validates Keycloak JWTs (KC-G2) | ✅ `docs/study-tutor-plan-of-record.md:36` |
| P3 | `ask_tutor` exists and round-trips to the spark | ✅ `docs/study-tutor-plan-of-record.md:37` |
| P4 | A Scholar app package with a settings web UI exists on the robot | ⏳ Lane 6 packaging build, stages 1–3 (`docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:137-151`). **This feature edits that settings page; it cannot land before it exists.** |
| P5 | **Lilymay's phone actually on keycloak mode** | ⏳ ruling queue #12's one remaining human step: a build carrying `--dart-define=KEYCLOAK_ISSUER=…` (`docs/study-tutor-plan-of-record.md:565-568`). **Hard precondition for the retirement half (§9), not for pairing itself** — retiring table mode with the phone still on a static bearer would strand a child mid-term. |
| P6 | A `dulcie` realm user with a `student_id` attribute, for the second robot | ❌ not created; ADR-ARCH-034 (ratified 2026-08-13) makes the shape legal — `docs/study-tutor-plan-of-record.md:282-295`. Out of scope here; §13 Q4. |

## 4. The one server-side finding — the realm will mint a token the server rejects

This is the single substantive defect this spec found, and it is config, not code.

- The server validates `aud` and refuses a mismatch:
  `jwt.decode(..., audience=self.settings.audience, ...)`
  (`src/study_tutor/http/auth_keycloak.py:120-137`) →
  `InvalidAudienceError` → `Unauthenticated` (`:147-149`).
- The deployed expectation is `STUDY_TUTOR_OIDC_AUDIENCE=study-tutor-app`
  (`docs/runbooks/HANDOFF-batch-c-auth-live.md:76`; KC-G2 evidence
  `docs/runbooks/evidence/keycloak-kcg2-2026-07-19/EVIDENCE.md:22`).
- The `study-tutor-app` client carries an explicit `oidc-audience-mapper` adding itself to
  `aud` (`deploy/keycloak/realm/study-tutor-realm.json:90-96`) — i.e. the realm authors
  already knew Keycloak does not add the resource-server audience by itself. The
  `live-suite` provisioning script adds the *same* mapper naming `study-tutor-app` to a
  *different* client (`deploy/keycloak/provision-live-suite.sh:101-109`) — the exact
  precedent for our case.
- **`reachy-robot` has no audience mapper.** Its `protocolMappers` block contains
  `student_id` and nothing else (`deploy/keycloak/realm/study-tutor-realm.json:148-164`).

**Conclusion:** a device-grant access token minted for `reachy-robot` today will validate
signature, issuer and expiry, carry the right `student_id` — and be rejected on `aud`.

**Required change (R1):** add to `reachy-robot`'s `protocolMappers` an
`oidc-audience-mapper` with `included.client.audience: study-tutor-app`,
`access.token.claim: true`, `id.token.claim: false` — byte-shaped like
`deploy/keycloak/realm/study-tutor-realm.json:88-97`. Realm-as-code first, live realm
second; the file is the source of truth (`docs/design/keycloak-auth-user-management-design.md:96`:
realm config "is exported as JSON into the repo … so the realm is reproducible").
**Rejected alternative:** widening `STUDY_TUTOR_OIDC_AUDIENCE` — it would loosen the check
for the phone too, for the robot's convenience.
**[verify at build]** decode one real robot token and assert `aud` contains
`study-tutor-app` **before** blaming anything else for a 401.

**Second config item (R2) — the offline-token half.** `offline_access` is a *default* client
scope on `reachy-robot` (`deploy/keycloak/realm/study-tutor-realm.json:135-142`), so it is
requested on every token call. The other half — the user holding the built-in
`offline_access` realm role — is **not pinned by this file**: the realm JSON declares only
`student` and `parent` roles and no `defaultRole` composite (`:roles` block; verified by
inspection). If Lilymay's account lacks that role, Keycloak returns an ordinary
SSO-bound refresh token instead of an offline one, and the robot silently un-pairs when
the SSO session idles out — a failure that looks like "the robot stopped working
overnight", not like an auth bug. **[verify at build]** confirm the paired user holds
`offline_access`, and confirm the minted refresh token is an offline one, at pairing time,
loudly.

## 5. Pairing UX — who reads what, off which screen

The robot is headless: no screen, no keyboard. It has antennas, a speaker, and — once the
Lane 6 app exists — a **settings web page served off the robot itself**
(`custom_app_url` → the SDK serves the package's `static/` via FastAPI on
`self.settings_app`; the dashboard shows a gear icon —
`docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:110-113`). That page is where
the static bearer is typed today (ruling E3). **It is the right screen for pairing too**,
and this feature replaces the "bearer" field on it with a "Pair this robot" button.

The flow, end to end:

1. **Start.** A parent opens the robot's settings page from the Reachy dashboard on the Mac
   or the phone, and taps **Pair this robot**.
2. **The robot asks Keycloak.** `POST {issuer}/protocol/openid-connect/auth/device` with
   `client_id=reachy-robot`, `scope=offline_access`. Response: `device_code`, `user_code`,
   `verification_uri` (`{issuer}/device`), `verification_uri_complete`, `expires_in`,
   `interval`.
3. **The page shows the code.** The settings page displays the `user_code` in large type,
   the `verification_uri` as a tappable link, **and a QR of `verification_uri_complete`**
   so the phone can jump straight in with the code pre-filled. The page also states plainly
   which robot it is and which child it is about to be paired as.
4. **The human approves — signed in as the student.** The browser opens
   `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor/device`, signs in **as
   Lilymay**, enters the code, approves. This is deliberate and is the whole point of D8:
   the robot must act *as the student*, not as a machine —
   *"client-credentials would mint a machine identity and break D8"*
   (`docs/design/keycloak-auth-user-management-design.md:104`).
   **The approving browser must be on the tailnet** — the realm is tailnet-only
   (ADR-ARCH-028 posture; `docs/design/keycloak-auth-user-management-design.md:74-77`). Lilymay's phone and Rich's Mac both are; a visitor's laptop is not.
   *Who signs in is a genuine question — §13 Q1.*
5. **The robot polls and stores.** The robot polls the token endpoint at `interval`,
   honouring `authorization_pending` / `slow_down` / `expired_token` / `access_denied`,
   and on success writes the token file (§6). The settings page flips to **Paired — as
   Lilymay, <date>**; the code disappears from the page and is never written to a log.
6. **Confirmation the family can feel.** The robot says one short line out loud through the
   normal spark voice path ("I'm signed in now") — presence, not a credential. **The code
   is never spoken**: an eight-character code by ear is error-prone, and speaking a
   credential-adjacent string aloud in a bedroom is a worse posture than showing it on the
   screen of the person already holding it.

**Expiry.** The `user_code` expires (Keycloak default 10 minutes). If it lapses, the page
says so and offers **Start again**. No silent retry, no code that lives longer than the
person's attention.

**Re-pairing** is the same flow. It is expected to be rare — after a robot re-flash, after
a revocation, or when a robot changes child.

## 6. The token on the Pi

**One file, and only one.** The single hardest lesson of ruling #9 is that a credential
had *three* homes on this robot and the third one was a backup nobody listed
(`docs/study-tutor-plan-of-record.md:513-515`). This feature ships exactly one location and
says so in the runbook.

| Property | Decision |
|---|---|
| Path | An app-owned config directory, separate from the human-editable settings file — recommended `/home/pollen/.config/scholar/pairing.json`. **fleet-gateway owns the final path**; it must not be inside the app package, the Space checkout, or any git clone. |
| Mode | `0600`, owner = the user the app daemon runs as. Created with `os.open(..., O_CREAT|O_WRONLY|O_TRUNC, 0o600)` so the mode does not depend on the umask; directory `0700`. |
| Write | Atomic: temp file in the same directory, `fsync`, `os.replace`. A half-written token file after a power cut must never be a half-paired robot. |
| Contents | `refresh_token` (offline), the cached `access_token` + its absolute expiry, `issuer`, `client_id`, and two human fields — `paired_as` (the `student_id`) and `paired_at` — so a person can see which child a robot is paired to without decoding a JWT. |
| Not in | Backups that get copied around (the `lattice-backup` lesson), logs, the settings-page HTML, the Space repo, any `sitecustomize.py`. |
| Logging | Only a fingerprint, never a prefix — mirror the server's `sha256(token)[:12]` convention (`src/study_tutor/http/auth.py:28-40`), which exists precisely so two devices sharing a `student_id` are distinguishable without a token reaching a log file (`docs/study-tutor-plan-of-record.md:36`). |

**Refresh loop.**

- Refresh **proactively** at ~60% of the access token's remaining life, and **reactively**
  on a 401, once. Access-token lifespan is the realm default — the realm JSON pins no
  `accessTokenLifespan` override (verified by inspection of
  `deploy/keycloak/realm/study-tutor-realm.json`), so treat it as short (minutes) and
  never hard-code a number: read `expires_in` from the token response.
- **Single-flight.** One refresh at a time, under a lock: a spoken turn can have three
  calls in flight at once (`voice-turn` plus `voice-audio` chunks), and three parallel
  refreshes against one refresh token is how rotation-enabled realms lock themselves out.
- **Refresh on app start**, always, before the first turn — the app is the startup app
  (ruling E5, `docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:41-42`), so this
  is effectively "on every boot".
- **The 30-day fact.** The offline session idles out on Keycloak's default (the design
  states 30 days, with "Offline Session Max Limited" left disabled so there is no absolute
  lifespan — `docs/design/keycloak-auth-user-management-design.md:103`). Because the tutor
  is the startup app, a robot switched on at all will refresh. A robot **switched off for
  a whole school holiday will come back un-paired.** That is acceptable and must be
  *said*, not discovered: the settings page shows **Needs pairing again** and the robot
  says one honest line rather than failing mutely.

**Failure handling — what actually happens mid-session, honestly.**

| Situation | What the robot does | What the child experiences |
|---|---|---|
| Access token expires mid-session, refresh succeeds | Transparent; the next call carries the new token | Nothing |
| Refresh fails, access token still valid | Finishes the current turn; retries refresh with backoff | Nothing, until the token expires |
| Refresh fails **and** the token has expired → spark returns 401 | One reactive refresh; if that fails, stop trying, mark **Needs pairing again** on the settings page, and let the tutor client's existing contract-shaped failure line stand | Exactly *"The tutor isn't reachable right now."* — the one string the lifted `common/tutor_client.py` yields for any failure, never a raise (`docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:99-101`) |
| Keycloak (the NAS) is down, spark is up | Cached access token keeps working until it expires; **no new tokens** | Session continues, then degrades as above |
| Network down entirely | Same one line | Same one line |

Three rules that make the above a design and not an accident:

- **Never re-pair mid-session.** A device-code prompt cannot appear in the middle of a
  child's tutoring turn. Pairing is an act a parent starts, on a page, on purpose.
- **Never invent tutoring text.** The failure line is the tutor client's; the auth layer
  adds nothing (mirrors the server-side rule that the adapter does not invent
  learner-facing text — plan ruling queue #10, `docs/study-tutor-plan-of-record.md:528-533`).
- **Nothing on the server is lost.** A 401 mid-session leaves the session active in the
  store; the phone can pick it straight up, and so can the robot after re-pairing, because
  the robot always sends `resume_if_active: true`
  (`docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:69-71`). Law 7: nothing
  that can make a session end sad (`:127-128`).

**One server-side subtlety worth knowing:** the spark's JWKS client caches keys, so a NAS
outage does not break validation of already-issued tokens — but an unknown `kid` triggers a
cache-bypassing fetch which, with the NAS down, fails closed to `Unauthenticated`
(`src/study_tutor/http/auth_keycloak.py:103-115`). Key rotation during a NAS outage is the
one compound case where a valid token 401s. Accepted; not mitigated.

## 7. The `ask_tutor` bearer-injection seam

Today the bearer is a static string read from config and put in a header. The whole change
is **where the string comes from and when it is read**.

- **Per-call, not per-construction.** The client must obtain the header value at call time
  from a provider (`get_access_token() -> str` that refreshes if near expiry), never
  capture it into a session's default headers at construction. A static bearer tolerated
  capture; a rotating one does not. This is the single line that most often gets this
  wrong.
- **Every surface, one seam.** The server resolves the bearer through exactly one function
  at three call sites — HTTP (`src/study_tutor/http/app.py:108`), voice
  (`src/study_tutor/voice/routes.py:134`) and the WS upgrade
  (`src/study_tutor/http/ws.py:160`), all calling `resolve_student_from_token`
  (`src/study_tutor/http/auth.py:223`). The robot must mirror that: one token provider
  feeding the tutor turn calls, the `voice-turn` multipart, the `voice-audio` chunk
  fetches, and the WS handshake.
- **The WS property, stated deliberately:** the server authenticates **at upgrade only** —
  `ws.py:158-166` resolves the student and then enters the message loop with no
  re-validation. So an access token expiring mid-stream does **not** drop a live streaming
  turn. That is benign and desirable (a sentence-by-sentence spoken turn must not die
  half-spoken), and it is a property to know rather than to fix. **Reconnects need a fresh
  token** — the provider must be consulted on every connect, not once per process.
- **Nothing else in the header changes.** `Authorization: Bearer <token>` is the same wire
  shape (`src/study_tutor/http/auth.py:265-275`); the value is simply a JWT (~1–2 KB)
  rather than a short opaque string. Any settings-UI validation that assumes a short bearer
  must go with the field it validated.
- **The three old consumers must end up with nothing.** Per ruling #9's cutover list
  (`docs/study-tutor-plan-of-record.md:513-515`): the Scholar app's settings config (now
  holds a pairing, not a secret), `sitecustomize.py` (removed by Lane 6 stage 4 —
  `docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md:152-155`), and
  `/home/pollen/lattice-backup/` (**must be scrubbed explicitly** — it is a backup, so it
  survives the tidy-up that removes the other two, which is exactly how a dead credential
  gets resurrected).

## 8. Gate KC-G4 — the D8 same-subject resume proof

The design names the gate: *"the D8 proof — phone session resumed by the robot under the
**same Keycloak subject** (this replaces the dev-table variant of AC-R2)"*
(`docs/design/keycloak-auth-user-management-design.md:172-175`).

| AC | Claim | Evidence |
|---|---|---|
| G4-01 | Pairing completes from the settings page; the token file exists at the one path, mode `0600`; no token or user code in the app logs, the Space repo, or the settings HTML | file listing + `grep` |
| G4-02 | The robot's access token carries `iss` = the realm issuer, `aud` ∋ `study-tutor-app`, `student_id` = Lilymay's, and a `sub` **equal to the phone token's `sub`** | decode both tokens side by side (the R1 check, §4) |
| G4-03 | **Both devices point at the SAME server process in keycloak mode.** Not the phone on `:8100` and the robot on `:8101` | container/config check before the walk |
| G4-04 | A session started on the phone is JOINED by the robot: `POST /api/sessions/start {resume_if_active: true}` returns the phone's session id, the robot's turn appears in the phone's mirror | attended walk (this is Lane 6 stage 3's mirror check, `HANDOFF-fleet-gateway-scholar-app-build.md:148-151`) |
| G4-05 | A static bearer presented to the same server → **401** | one request |
| G4-06 | Refresh works unattended: idle past the access-token lifetime, then take another turn with no re-pairing | attended walk with a wait |
| G4-07 | **Revocation works from Keycloak alone**: delete the robot's offline session in the admin console → the robot 401s and shows *Needs pairing again*; the phone is untouched | admin console + one turn on each device |

**Why G4-03 is on this list.** `:8100` and `:8101` share one Postgres
(`deploy/http/docker-compose.keycloak.yml:26`: *"Same PG DSN and spark LLM env as
`:8100`"*). A "resume" observed across the two ports would prove only that they share a
store — the very thing that already made the GB10 serve *"a byte-identical record"*
(`docs/study-tutor-plan-of-record.md:37`). The D8 claim is about a *subject*, and only a
single-server walk can carry it.

## 9. Rollout — and how table mode is finally retired

Order, each step reversible on its own:

0. **Realm** — R1 (audience mapper) into `deploy/keycloak/realm/study-tutor-realm.json`,
   then applied to the live realm; R2 verified (`offline_access` role). Additive: the
   phone is unaffected by an extra client's mapper.
1. **Lane 6 stages 1–3 land** — the Scholar app exists with settings and a spoken loop
   (P4). This feature edits that page; E3 sequenced it exactly this way.
2. **Pairing ships, alongside the old field.** The app supports **both** token sources for
   one release — a pairing (preferred when present) and the typed bearer (fallback). This
   is the rollback path, and it costs one `if`.
3. **Pair the robot** against the keycloak-mode server. Run **KC-G4**.
4. **The phone precondition (P5)** — ruling #12's remaining human step, a phone build
   carrying the Keycloak issuer (`docs/study-tutor-plan-of-record.md:565-568`). Table mode
   cannot retire before this, whatever the robot does.
5. **Collapse the ports.** Today `:8100` is table and `:8101` is keycloak — two compose
   projects, deliberately independent (`deploy/http/docker-compose.keycloak.yml:1-16`).
   The end state is one server in keycloak mode. **Recommendation: flip `:8100` in place**
   (env change + restart, the design's own cutover shape —
   `docs/design/keycloak-auth-user-management-design.md:176-179`) and retire `:8101` as the
   experiment it was, because every device already holds the `:8100` base URL: no phone
   rebuild, no robot re-configuration. *Rich's call — §13 Q3.*
6. **Drop the table.** `STUDY_TUTOR_HTTP_TOKENS={}`. Per the design's own discipline this
   happens only after the live flavour holds *"for a week of real use"*
   (`docs/design/keycloak-auth-user-management-design.md:176-178`), and with `.env` backups
   either side — the practice ruling #9 already established
   (`docs/study-tutor-plan-of-record.md:527`).
7. **Remove the fallback.** The typed-bearer field comes out of the settings page in the
   following release, and the `sitecustomize.py` + `lattice-backup` copies are gone
   (Lane 6 stage 4 + §7 above).

**An honest correction to "the robot is the last table-mode consumer."** For *children's
devices* it is true, and that is what ruling E3 meant. But the table holds **four** entries
today — phone, robot, `alex`, `suite-runner`
(`docs/study-tutor-plan-of-record.md:520-522`). Two are test principals, and retiring the
table also moves them: `alex` becomes a realm user, and the live contract suite moves to
its Keycloak variant. Both paths already exist and are not free —
`deploy/keycloak/provision-live-suite.sh` provisions the `live-suite` client, and
`tests/integration/test_keycloak_contract.py` *"skips cleanly without live env"*
(`docs/runbooks/HANDOFF-weekend-auth-voice-fable-window.md:45`). Step 6 must not be taken
on a day when the live suite is the thing proving the deploy.

## 10. Rollback

| Step | Rollback | Cost |
|---|---|---|
| 0 (realm mapper) | Re-import the realm JSON without the mapper | Nil — an extra audience harms nothing |
| 2–3 (pairing ships / robot paired) | Type the static bearer back into the settings page; delete the token file | Minutes, no rebuild — this is why step 2 keeps both sources |
| 5 (port flip) | Env flip back to `table` + restart — the design's stated rollback (`keycloak-auth-user-management-design.md:176-178`) | One restart |
| 6 (table dropped) | Restore the `.env` backup and recreate the container | One restart; **the only step with a real blast radius, hence the week-green rule** |
| Whole feature | The Pi lattice stays as the deeper rollback until Lane 6 stage 4 removes it (`HANDOFF-fleet-gateway-scholar-app-build.md:133`) | — |

## 11. What changes in which repo

**study-tutor (this repo) — no `src/` change. The argument, not the assertion:**

- The auth entry point takes the Bearer token from the header and hands it to the injected
  resolver; it knows nothing about how the token was obtained
  (`src/study_tutor/http/auth.py:223-300`; extraction at `:265-275`).
- `KeycloakTokenResolver.resolve` validates signature via JWKS, `iss`, `aud`, `exp`/`nbf`,
  RS256-only, then reads the `student_id` claim
  (`src/study_tutor/http/auth_keycloak.py:76-186`). A device-grant token from the same
  realm and same user is identical on every one of those axes — same issuer, same signing
  keys, same `student_id` mapper (`deploy/keycloak/realm/study-tutor-realm.json:148-164`)
  — **except `aud`, which is §4's realm change, not a code change.**
- All three surfaces already inherit it: HTTP (`http/app.py:108`), voice
  (`voice/routes.py:134`), WS upgrade (`http/ws.py:160`). The design predicted this:
  *"WS: zero extra work — same `_resolve_student_id` at upgrade time"*
  (`docs/design/keycloak-auth-user-management-design.md:143`).
- The frozen HTTP contract is untouched: no verb, field, shape or status code changes;
  additive-or-re-pin does not apply because nothing is edited (root `CLAUDE.md`;
  `docs/design/contracts/API-session-http-binding.md` §7).

So the study-tutor footprint is:

1. `deploy/keycloak/realm/study-tutor-realm.json` — the audience mapper (R1).
2. This spec + the digest, and a short operator runbook for the pairing/retirement steps.
3. **Recommended, cheap, hermetic:** a test asserting the realm JSON gives `reachy-robot`
   an audience mapper naming `study-tutor-app` — it catches §4's exact defect in CI rather
   than in a bedroom on a Tuesday night.

**fleet-gateway (the robot's repo) — all the build work:**

1. Settings page: **Pair this robot** replacing the bearer field (code + link + QR +
   status), with the typed bearer kept as a fallback for one release.
2. Device-flow client: device-authorization request, polling with `interval` /
   `slow_down` / `expired_token` / `access_denied` handling.
3. Token store: one file, `0600`, atomic write, fingerprint-only logging (§6).
4. Refresh loop: proactive + reactive, single-flight, on-start, with the honest
   failure states of §6.
5. Token provider seam wired into `common/tutor_client.py` and the voice/WS paths (§7).
6. The three old consumers ended: settings config, `sitecustomize.py`,
   `/home/pollen/lattice-backup/` (§7).

**Neither repo:** the Flutter app. The phone is unaffected by this feature; its own
Keycloak move is ruling #12's step, and the two are independent apart from the retirement
ordering (P5).

## 12. What this does not fix (say it plainly)

- **The token file is still readable by anyone with root on the Pi.** The gain over a
  static bearer is revocability, expiry, and per-device identity — not secrecy of a file in
  a bedroom.
- **Pairing as the student means the robot can do anything the student can.** By design
  (D8). There is no reduced-scope robot role in this phase, and inventing one would outrun
  KC-D5's deliberate deferral (`docs/design/keycloak-auth-user-management-design.md:111-117`).
- **A malformed `Authorization` header still logs its first 50 characters**
  (`src/study_tutor/http/auth.py:268-272`). That is existing behaviour and only triggers on
  a wrong scheme, but with JWTs it means a partial token could reach a log. Worth a
  follow-up ticket; not a blocker for this feature and not silently changed here.
- **Nothing here addresses ruling queue #13** (release APKs debug-signed,
  `docs/study-tutor-plan-of-record.md:574-583`). Different device, different fix.

## 13. Questions for the spec word

*(These need Rich. They are not resolved above.)*

**Q1 — Who signs in at the pairing screen?** The device flow needs someone to authenticate
**as Lilymay** at the Keycloak page (§5 step 4). Either Rich holds her credentials and
pairs on her behalf, or she approves on her own phone with Rich present. KC-D4 says "a
parent approves" (`docs/design/keycloak-auth-user-management-design.md:104`); that predates
her having her own realm account in real use. *Recommendation: Lilymay signs in, Rich
present — it keeps her credential hers, and it is the same act she already does on the
phone.*

**Q2 — Is a robot that has been off for a school holiday allowed to need re-pairing?**
The offline session idles out (§6). Alternatives are a longer idle timeout on the realm or
a periodic wake — both add a moving part. *Recommendation: accept it, and make the message
honest and the re-pair one tap.*

**Q3 — Port collapse: flip `:8100` to keycloak in place, or move the household to `:8101`
and retire `:8100`?** (§9 step 5.) *Recommendation: flip `:8100` in place — every device
already holds that base URL, so no phone rebuild and no robot re-configuration; `:8101`
retires as the experiment it was.*

**Q4 — Dulcie's robot in September (the E3 forcing date).** Does FEAT-AUTH-004 ship
paired-for-one-child now and take a second child when her account exists, or does the
`dulcie` realm user + `student_id` land in the same lane? *Recommendation: ship for one
child now; her account is a runbook act on the day her robot arrives, and the pairing flow
is per-robot by construction.*

**Q5 — The week-green rule before dropping the table (§9 step 6).** The design says a week
of real use before retiring the static table
(`docs/design/keycloak-auth-user-management-design.md:176-178`). With term time starting,
is a week the right wait, and does it start from the phone's cutover (P5) or the robot's?
*Recommendation: a week from whichever cuts over **last**, so both devices have run real
sessions on the same server.*

---

*Drafted 2026-08-14 in the docs lane: files only — no live host, realm, container or broker
was contacted. Every `[verify at build]` marks a claim the build must confirm against the
running realm before relying on it.*
