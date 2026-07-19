# HANDOFF — Weekend Fable Window: Finish Auth (A2 + A3) + Voice (Reachy R-track)

**Written:** 2026-07-17 (Fri) by the Fable coordinator session that surveyed both lanes (workflow `wf_3a0b1284-b65`, 6 Opus readers over specs + code).
**Window:** Fri ~midday → Mon 08:00 — multiple subscriptions reset with Fable access; burn it on finishing auth + voice.
**Pattern:** `ai-transition/docs/ways-of-working/orchestrated-build-playbook.md` — Fable coordinates/verifies/pushes; Opus subagents build; coach gates before building on a stage; local commits; early-stop on blockers.
**Who does what:** Rich = greenlights + the operator-attended checkpoints (§7). Fable = everything else.

---

## 0. TL;DR + the greenlight prompt

**Done and live:** A1 Keycloak IdP (NAS, healthy, user `lilymay` with working `student_id` claim), voice server + streaming + Flutter tap-to-talk (VOICE-001/002/003 merged, flag-gated), GB10 `:8100` dev deploy (table-mode auth), GB10 llama-swap `:9000`.

**Remaining:** three lanes, 24 tasks — **A2** server Keycloak validation (7 tasks, study-tutor Python), **A3** Flutter sign-in (7 tasks, `app/`), **VOICE-004** Reachy local-voice migration (10 tasks — 5 agent-buildable code, 5 operator).

**The greenlight prompt (paste into the weekend Fable session):**

> *Orchestrate the weekend auth+voice finish. Spec = `docs/runbooks/HANDOFF-weekend-auth-voice-fable-window.md` (this doc — read all of it) plus the binding specs it names per lane. Mechanisms: A2 then A3 via `GUARDKIT_HARNESS=sdk guardkit autobuild feature …` with the §4/§5 env recipes; VOICE-004 code subset (R04/R05/R06/R07/R08) via a playbook Workflow with Opus builders + coach gates in `../fleet-gateway` (+ R06 in study-tutor), skeleton in §6. Fences = each lane's §4–§6 fence block, verbatim, coach-checked. Commit locally per stage; merge via `/feature-complete` only after lane review; push after my review checkpoints. Operator steps (§7) are mine — queue them and tell me when a batch is ready. Sequencing fence: Reachy SMK-R runs against the table-mode `:8100` BEFORE any keycloak-mode flip (§3). Effort high. If a stage blocks twice, stop that lane and move on — don't burn the window.*

---

## 1. State of the world (verified 2026-07-17)

| Surface | State |
|---|---|
| NAS Keycloak `:8443` | LIVE, healthy. Issuer pinned `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`. Realm has clients `study-tutor-app`, `reachy-robot` (both with `student_id` mapper), roles `student`/`parent`, user profile declares `student_id`. User `lilymay` (role student, `student_id=lilymay`) verified end-to-end and durable across `--import-realm`. Admin + user creds: `deploy/keycloak/.env.deploy` (gitignored) — **never commit**. |
| NAS Postgres `:5434` | LIVE (`whitestocks.tailebf801.ts.net:5434`, superuser role **`study_tutor`**, NOT `postgres`). Nightly backup dumps both `study_tutor` + `keycloak` DBs. |
| GB10 `:8100` study-tutor | LIVE (deployed + walked 2026-07-05). Auth = **static token table** (`STUDY_TUTOR_HTTP_TOKENS`); no keycloak mode exists in code yet. |
| GB10 `:9000` llama-swap | LIVE. Keepalive timer inactive since 07-03 → cold loads (~26 s first tutor turn); warm before attended gates. |
| Voice (server+app) | VOICE-001/002/003 merged, test-green. **Flag-gated OFF by default** (`STUDY_TUTOR_VOICE_ENABLED`). Frozen voice `CONTRACT_SHA`/`BINDING_SHA` + six-verb freeze are hard commitments — additive work only. |
| Missing from realm | **`live-suite` confidential client** (Direct Access Grant) + optional test user `alex` — required by KCA2-006/KC-G2; deliberately not in realm-as-code. Provision via admin API (§7 C2). |

## 2. What remains

### Lane A2 — FEAT-AUTH-002 server-side Keycloak validation (study-tutor Python; ~10 h est)
Waves: `[001,002] → [003] → [004] → [005,006] → [007*]` (\* = operator).

| Task | What | Notes |
|---|---|---|
| KCA2-001 | `http/oidc_config.py` OIDCSettings + `PyJWT[crypto]` dep | env surface `STUDY_TUTOR_AUTH_MODE/OIDC_ISSUER/OIDC_AUDIENCE/OIDC_JWKS_URL/OIDC_STUDENT_CLAIM/OIDC_LEEWAY`; NO PyJWT import here |
| KCA2-002 | `TokenResolver` protocol + `TableTokenResolver` refactor in `auth.py` | byte-identical behaviour; existing tests pass unchanged; FULL_REQUIRED |
| KCA2-003 | `http/auth_keycloak.py` KeycloakTokenResolver (PyJWKClient) | cx-8 security core; RS256 allowlist only; all failures → `Unauthenticated`, never 500; FULL_REQUIRED |
| KCA2-004 | Boot wiring: mode-select + SystemExit fail-fast in `cli/main.py` (serve_http ~:848, auth wiring ~:925) | lazy import of auth_keycloak in the keycloak branch; dev-reset never mounts in keycloak mode; FULL_REQUIRED |
| KCA2-005 | AC-005 tripwire re-scope + coexistence guard (tests only, `implementation_mode: direct`) | auth.py stays JWT-free forever (tripwire at `test_auth.py:242`) |
| KCA2-006 | Live-suite token harness (`tests/integration/test_keycloak_contract.py`) | **skips cleanly** without live env (`STUDY_TUTOR_OIDC_ISSUER` + `STUDY_TUTOR_LIVE_SUITE_CLIENT_ID/SECRET`) — builds green with no realm |
| KCA2-007* | KC-G2 live gate | operator §7 — needs keycloak-mode deploy + live-suite client |

### Lane A3 — FEAT-AUTH-003 Flutter Keycloak sign-in (`app/`; ~11 h est)
Waves: `[001] → [002,005] → [003] → [004] → [006] → [007*]`. Smoke gate `set -e; cd app && flutter analyze && flutter test` after waves 3 and 5. Hermetic throughout — no live services needed until KC-G3.

| Task | What | Notes |
|---|---|---|
| KCA3-001 | deps (`flutter_appauth`, `flutter_secure_storage` — the ONLY two), redirect scheme, `KeycloakConfig` | see drift fixes §5 |
| KCA3-002 | `SecureSessionStore` (fail-closed `read()`) | new `app/lib/adapters/secure_session_store.dart` |
| KCA3-005 | Sign-out app-bar action | task .md says `task-work` (authoritative) — YAML line 43 wrongly says `direct` |
| KCA3-003 | `KeycloakIdentityProvider` — silent-then-interactive PKCE adapter behind the UNCHANGED 3-member port | cx-8 security core; FULL_REQUIRED |
| KCA3-004 | SignInScreen state machine (loading/failure/cancel distinct) | reconcile the ctor — current widget also takes `voiceApi` |
| KCA3-006 | Composition de-type + flavour wiring | see the three-seam + flavour-key decisions §5 |
| KCA3-007* | KC-G3 live gate | operator §7 — real device, keycloak-mode deploy, >5-min idle refresh |

### Lane V — FEAT-VOICE-004 Reachy local voice (5 code + 5 operator; ~13 h est)
**FENCE (verbatim from the YAML): do NOT run `/feature-build FEAT-VOICE-004` from study-tutor — the code artefacts live in `../fleet-gateway` and cannot be built from this repo.** Execution model is Operator + Opus. Waves: W1 `[R01*,R02*,R04,R06]` W2 `[R03*,R05,R07]` W3 `[R08]` W4 `[R09*]` W5 `[SMK-R*]`.

| Task | Repo | What |
|---|---|---|
| R04 | fleet-gateway | `query_student_model` → Pollen `core_tools.Tool` ABC (`parameters_schema` + `async __call__`, returns dict) |
| R05 | fleet-gateway | port its read onto `:8100` student-model endpoint (bearer, connect-per-call) — replaces frozen Graphiti read |
| R06 | **study-tutor** | subject single-source `'english'` — AC-R06-1 already done (`app/lib/ui/home_screen.dart:25`); remaining: one documented source of truth + seam test |
| R07 | fleet-gateway | `ask_tutor` external tool → `:8100` sessions API (`resume_if_active:true, subject:'english'`); offline string EXACTLY `The tutor isn't reachable right now.` for every failure incl. rejected bearer |
| R08 | fleet-gateway | reconciled Scholar profile (adds ask_tutor; emotion tool stays ABSENT; task_cancel/task_status stay; Pi reality authoritative) |
| R01*/R02*/R03*/R09*/SMK-R* | GB10 + Pi | operator §7 — s2s unit standup `:8765`, Pi version check, re-point + tool round-trip, clean re-clone deploy, live smoke AC-R1..R4 |

**Straggler:** `tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md` is ~90 % superseded by VOICE-002/003 — **close/re-scope it, do not build it.**

## 3. Cross-lane ordering (the load-bearing constraints)

1. **A2 code → keycloak-mode deploy → KC-G2 → KC-G3.** A3 KC-G3 hard-depends on a keycloak-mode `:8100` + the A1 realm. A3 code waves 1–5 are hermetic — build them in parallel with A2, any order.
2. **The robot conflict:** R07's `ask_tutor` authenticates with a **static bearer** ("same binding the app uses") — i.e. against **table mode**. A keycloak-mode flip of the live `:8100` breaks the robot (device pairing is A4/FEAT-AUTH-004, out of scope). **Fence: run Reachy R03 + R09 + SMK-R against the table-mode deploy BEFORE flipping `:8100` to keycloak mode** (or stand the keycloak-mode instance up separately and leave the table deploy alone — Fable's call at deploy time; flag it either way).
3. VOICE code (R04–R08) is independent of A2/A3 — run its Workflow concurrently with the autobuild lanes.
4. KCA2-006's live leg + KC-G2 need the **`live-suite` client provisioned in the realm first** (§7 C2 — Fable can do this via the admin API; secret goes in `.env`/`.env.deploy` files only, never git).

## 4. Lane A2 mechanism (guardkit autobuild — proven on A1 this week)

```bash
cd ~/Projects/appmilla_github/study-tutor
# Coach test-gates need a loopback PG (repo conftest.py aborts the whole pytest session on a non-loopback DSN):
docker run -d --name st-autobuild-pg -e POSTGRES_USER=study_tutor -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=study_tutor -p 127.0.0.1:5434:5432 postgres:16
export GUARDKIT_HARNESS=sdk          # EXPORT it — a one-command prefix does not survive into tool subshells
STUDY_TUTOR_PG_DSN=postgresql://study_tutor:testpass@localhost:5434/study_tutor \
  guardkit autobuild feature FEAT-AUTH-002
# afterwards: guardkit autobuild complete FEAT-AUTH-002 → FF-merge → push after review; docker rm -f st-autobuild-pg
```

Known-infra notes: exit-143/SIGTERM coach failures in parallel waves are races → `--resume`, don't re-author. `--fresh` clears a poisoned state. Never add `OPENAI_BASE_URL` to an sdk-harness run.

**A2 fences (coach-checked, verbatim):** `auth.py` imports no jwt/JWT/keycloak/Keycloak/jose symbol and never imports `auth_keycloak` (AC-005 tripwire, permanent). Resolver selection lives in the boot path, NEVER in auth.py; `app.py`/`ws.py` callsites unchanged (WS inherits at upgrade, binding §2.1). RS256 positive allowlist only (reject `alg:none`/HS256 explicitly). `iss` must equal the ts.net issuer even when JWKS is fetched via an IP override (KC-D2). Every validation failure → `Unauthenticated`, never a 500. Unseeded-student guard STAYS in `resolve_student_from_token` (after resolve — don't move it into resolvers). `/__dev__/reset` and keycloak mode never coexist. Hermetic tests mint in-test RSA keys; no live realm in the default run.

**Known drift for builders:** `HTTPAuthConfig` today has NO `resolver` field (that IS KCA2-002's deliverable — `auth.py:42-52`); dev-reset mount today is `app.py:596-599`; DSN fail-fast precedent `cli/main.py:869-882`.

## 5. Lane A3 mechanism (guardkit autobuild, same recipe — Flutter 3.44.4 present in build env)

Run after or alongside A2 (no code dependency): `export GUARDKIT_HARNESS=sdk; guardkit autobuild feature FEAT-AUTH-003` (loopback DSN export harmless/unneeded — the Flutter suite doesn't touch PG).

**A3 fences (verbatim, coach-checked):** Redirect URI frozen `com.appmilla.studytutor:/oauth2redirect` — byte-identical in Keycloak client, Android manifest placeholder, iOS CFBundleURLSchemes, and `KeycloakConfig`. The 3-member `IdentityProvider` port UNCHANGED; sync `currentPrincipal` answered from an in-memory cached principal, never I/O. `signIn()` silent-then-interactive (always try stored-session refresh before any browser). `SignInCancelled` ≠ `SignInFailed`, never conflated; missing discovery doc = failure. `signOut` wins an in-flight refresh (generation/epoch bump; local clear only — no IdP end-session this slice, ASSUM-004). `Unauthenticated`→routeToSignIn strictly distinct from `TransportError`→showConnectionProblem. Scopes `[openid, offline_access]`. Tokens only in the platform secure store; `read()` fail-closes to null on absent/corrupt/store-throw. PKCE S256. Empty `KEYCLOAK_ISSUER` → hermetic-fake flavour keeps the CONCRETE `FakeIdentityProvider` (for `studentIdForToken`) and stays green with no network.

**Pre-made decisions (so the run doesn't stall):**
- **KCA3-005 mode:** the task .md frontmatter (`task-work`) is authoritative over the feature YAML's `direct` (YAML line 43 is wrong — fix it or let autobuild follow the .md).
- **Flavour key:** TASK-KCA3-006 is authoritative — real-vs-fake selection keys on `KEYCLOAK_ISSUER` (empty → fake). Today `main.dart` keys flavour off `API_BASE_URL`; the builder migrates the selection, `API_BASE_URL` stays what it is (the backend URL).
- **Three seams, not one:** `main.dart` has THREE concrete-`FakeIdentityProvider` seams — `composeSessionApi` (:27), `composeVoiceApi` (:32), `composeStudentModelApi` (:41). Task 006 names only the first. Direction: de-type whatever the keycloak flavour must construct with the real adapter (all three take `identity`); the fake flavour keeps concretes. `composition_test.dart` asserts the composeSessionApi rule — keep it green. Coach verifies no flavour ends up mixing fake+real identity.
- **Path/line drift (do not trip):** Android manifest placeholder lives in `app/android/app/build.gradle.kts` (Kotlin DSL — task says `build.gradle`); `composeSessionApi` is at `main.dart:27` (docs cite :21); current `SignInScreen` ctor also requires `voiceApi` — reconcile the widget signature with task 004's two-arg seam test rather than blindly following either.
- Expected non-failures: feature-validate warns "does not cover the final wave" (wave 6 is un-gated operator_handoff) — not a build failure. Some PKCE wire-mechanics oracles resolve `pending` by design (README scope guard).

## 6. Lane V mechanism (playbook Workflow — Opus builders + coach gates in `../fleet-gateway`)

Not autobuild. Fable authors/launches this (adapt the playbook §5 skeleton):

```js
export const meta = { name: 'reachy-rtrack-code', description: 'R04→R05, R06→R07→R08 Opus build+coach in fleet-gateway (+R06 in study-tutor), seam-test gated, local commits', phases: [
  { title: 'R04 tool ABC' }, { title: 'R06 subject SoT' }, { title: 'R05 postgres read' }, { title: 'R07 ask_tutor' }, { title: 'R08 profile' } ] }
const FG = '/home/richardwoollcott/Projects/appmilla_github/fleet-gateway'
const ST = '/home/richardwoollcott/Projects/appmilla_github/study-tutor'
const PREFLIGHT = `You are an Opus EXECUTOR. Build to spec; DO NOT redesign; commit LOCALLY; do NOT push.
BINDING SPECS (read in full): ${ST}/tasks/backlog/reachy-local-voice-migration/IMPLEMENTATION-GUIDE.md (§4 contracts SUBJECT_DEFAULT + STUDY_TUTOR_HTTP_8100), README.md, and your task's TASK-VOX-R0x .md.
FENCES: Pollen core_tools.Tool ABC = parameters_schema + async __call__ returning dict (NOT parameters/run()/str). ask_tutor offline string EXACTLY "The tutor isn't reachable right now." for httpx error / non-2xx / rejected bearer — never raises. subject default 'english' single-source (producer R06). Scholar profile: emotion tool ABSENT, task_cancel/task_status PRESENT, Pi reality authoritative. Seam tests against fakes/MockTransport — no live services, no robot, no GB10.`
// stages sequentially per dependency chain (R04→R05; R06→R07→R08), each: build agent → coach agent
// (independent verify: run the seam tests yourself) with the playbook VERDICT schema; one fix pass; early-stop.
```

Notes: R06's remaining work is in **study-tutor** (single source-of-truth doc + seam test; `home_screen.dart:25` already `'english'`); grep for `resume_if_active` (now `session/service.py:429` — the task's :218-233 citation is stale). The fleet-gateway claims in the task files (rejected tool shape, Graphiti read, ask_jarvis template, hardcoded NATS creds on the Pi clone) were NOT re-verified by the survey — the first builder in each stage verifies before editing.

## 7. Operator checkpoints (Rich — batched; everything else runs without you)

**Batch A (Fri/Sat, ~30 min, parallel with code builds):**
- A1. R02 — read + record the Pi's installed `reachy_mini_conversation_app` version; confirm it honours `HF_REALTIME_CONNECTION_MODE=local` + `HF_REALTIME_WS_URL`; upgrade if not.
- A2. R01 — GB10 s2s unit standup on `:8765` (systemd/docker, digest-pinned, non-loopback bind; Silero-VAD-v5 + parakeet-tdt + qwen3 TTS; 0.6B→1.7B fallback pre-approved ASSUM-003; cu130 wheel BEFORE speech-to-speech; LLM stage → `http://127.0.0.1:9000/v1`; quiet-GPU rule; never GET `:9000/unload`). Fable preps every command; you run/watch.

**Batch B (Sat/Sun, robot, table-mode `:8100` still live):**
- B1. R03 — re-point robot to local s2s (env via `sitecustomize.py` `os.environ.setdefault`; `REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY` never set) + prove tool round-trip (R-G3).
- B2. R09 — ship R05/R07/R08 to the Pi via **clean re-clone** (never `git pull` — the Pi clone is hand-edited); re-apply sitecustomize + NATS creds.
- B3. SMK-R — live smoke AC-R1..R4: open-mic with NO HF-cloud session; tools fire locally; **phone-started tutor session picked up on the robot** (D8 — needs a phone session, subject `english`); no raw audio at rest (Pi + GB10 disk/DB sweep).

**Batch C (Sun, auth going live — AFTER Batch B or on a separate instance per §3):**
- C1. Merge-review A2 (Fable presents; you skim the FULL_REQUIRED diffs: KCA2-002/003/004).
- C2. Provision realm `live-suite` confidential client (Direct Access Grant) + optional `alex` user — Fable drives the admin API with creds from `deploy/keycloak/.env.deploy`; secrets land only in env files.
- C3. Keycloak-mode deploy: `STUDY_TUTOR_AUTH_MODE=keycloak` + OIDC issuer/audience env on the `:8100` deploy (per §3 decision), then **KC-G2** (AC-G2-01..05: live suite green, hermetic table green, unseeded-401, unknown-mode fail-fast).
- C4. **KC-G3** on a real phone: install A3 build (`--dart-define KEYCLOAK_ISSUER=…`), live browser sign-in as `lilymay`, redirect round-trip, >5-min idle then a working call (proactive refresh), sign-out → sign-in screen; cancel path distinct.
- C5. `/feature-complete` A2 + A3, `guardkit task complete` the operator tasks, push.

## 8. Fable review-and-push checklist (playbook §8, adapted)

Every coach/autobuild verdict green, no open blocker; full suites re-run by Fable (`pytest` hermetic + `cd app && flutter analyze && flutter test`). Spec fidelity: §4 contract names verbatim (TOKEN_RESOLVER, OIDC_SETTINGS, REDIRECT_URI, STORED_SESSION, SIGNIN_OUTCOME, SUBJECT_DEFAULT, STUDY_TUTOR_HTTP_8100). Fences held — verify, don't trust (grep the AC-005 tripwire yourself; redirect URI byte-identical ×4; offline string exact). Nothing leaked: no secrets/users in git (realm JSON = structure only), no live-suite secret, no Pi NATS creds. Frozen voice CONTRACT_SHA/BINDING_SHA + six-verb freeze undisturbed. Claims match code. Then push; record run ids + a dated note here.

## 9. Environment crib sheet

Hosts: NAS `whitestocks.tailebf801.ts.net` = 100.92.74.2 (keycloak :8443, postgres :5434); GB10 `promaxgb10-41b1.tailebf801.ts.net` = 100.84.90.91 (app :8100, llama-swap :9000, s2s target :8765); tailnet-only, no WAN, ever. Secrets: `deploy/keycloak/.env.deploy`, `deploy/postgres/.env.deploy`, NAS `.env` files — all gitignored. NAS SSH: `ssh -i ~/.ssh/fleet_memory_nas_ed25519 RichardWoollcott@whitestocks…`; sudo is NOPASSWD for docker ONLY; scp dead (use rsync/`ssh 'cat >'`); never `rsync --delete` at `/volume1/docker/study_tutor_keycloak/` (certs live only there); never `compose down -v` (realm state). Tests: repo-root `pytest` guards `STUDY_TUTOR_PG_DSN` loopback-only (session abort otherwise); Flutter `cd app && flutter analyze && flutter test` (live suites need `--dart-define=API_BASE_URL`, `--concurrency=1`). Voice needs `STUDY_TUTOR_VOICE_ENABLED=true` to mount routes — 404 without it is by design, not a regression. `../nats-core` sibling checkout must exist for `deploy/http` compose builds. Cold GPU: warm the tutor set with a throwaway turn before latency-sensitive gates.

## 10. Cleanups to fold in (low-effort, during review lulls)

1. Close/re-scope `TASK-STREAM-001` as superseded (record what VOICE-002/003 shipped vs. its scope).
2. Fix FEAT-AUTH-003.yaml line 43 (`KCA3-005 implementation_mode: task-work`).
3. Update stale citations: R06's `session/service.py:218-233` → `:429`; A3 guide's `main.dart:21` → `:27`; KCA3-001's `build.gradle` → `build.gradle.kts`.
4. After KC-G2: record the keycloak-mode deploy + gate evidence in `docs/runbooks/evidence/` (pattern from the R-track tasks).

## 11. Batch C close-out — auth is LIVE (2026-07-19, GB10 Fable session)

Executed per `docs/runbooks/HANDOFF-batch-c-auth-live.md`. **All gates green; auth
lane complete end-to-end on a real device.**

**C2 (commit `67f7a63`):** `provision-live-suite.sh --with-alex` created the
`live-suite` DAG client + `alex` user; the script now also patches the LIVE
`study-tutor-app` client's redirect URI to the single-slash form
`com.appmilla.studytutor:/oauth2redirect` (the live realm predated the `fa49ce5`
fix). Secrets in gitignored env files only. Evidence: `evidence/keycloak-c2-2026-07-19/`.

**C3 + KC-G2 (commit `67f7a63`):** keycloak-mode deploy stood up as a SEPARATE compose
project `study_tutor_http_kc` on `:8101` (image `study-tutor:kc-a2`, overlay
`deploy/http/docker-compose.keycloak.yml`, KC-D2 JWKS via `extra_hosts` tailnet-IP
pin). **Table-mode `:8100` never touched.** KC-G2 (TASK-KCA2-007) ALL PASS: contract
suite 5/5, e2e 200, hermetic baseline match, ASSUM-001 wall-clock, ASSUM-007 fail-fast,
unseeded-401, dev-reset-404. Note vs §7 plan: keycloak mode runs on a **new `:8101`
instance**, not toggled on `:8100` (the batch-c handoff §3.2 decision — protects the
robot + live phone binding). Evidence: `evidence/keycloak-kcg2-2026-07-19/`.

**C4 + KC-G3 (commits `4336035`, `641c4b8`, `8c438eb`, `c2e3b1a`, `5a5384c`):** live
sign-in on a real Android device (SM-A236B) as `lilymay` against `:8101`. **GATE PASS,
all six ACs + cancel.** The gate surfaced and fixed **five** real defects the hermetic
A3 gates couldn't (analyze+test only, no APK, no live IdP):
1. `turnBudget` 15 s → 90 s (spark turns 26–80 s) — `641c4b8`.
2. APK build (flutter_appauth compileSdk-31 vs AGP 9) — `4336035`.
3. Duplicate OAuth redirect handler (manual MainActivity intent-filter + appauth's
   receiver) — `8c438eb`.
4. Missing `aud=study-tutor-app` audience mapper on the app client (KC-G2 masked it via
   the live-suite client) — `c2e3b1a` (live realm + realm-as-code).
5. Redirect never completed in-app: missing browser/Custom-Tabs `<queries>` →
   full-Chrome fallback whose gestureless custom-scheme redirect Chrome drops; and
   `taskAffinity=""` split the redirect into a new task with no appauth state — `5a5384c`.
Server-verified: `Token validated successfully: student_id=lilymay`, 200s on
student-model/sessions/turn/resume; silent refresh on reopen; 12-min-idle resume with
no re-auth; sign-out → sign-in screen; cancel reads as cancel. Evidence:
`evidence/keycloak-kcg3-2026-07-19/`.

**C5 (this commit):** completed TASK-KCA2-007, TASK-KCA3-007, and the VOX operator set
(R01/R02/R03/R09/SMK-R, evidence in `evidence/voice-r0*-batch*`); closed
FEAT-VOICE-004 (code tasks R04–R08 in `../fleet-gateway` verified end-to-end by the
passing SMK-R live smoke). FEAT-AUTH-002/003 already merged (`b03cbbf`/`bf9ed99`).

**Post-gate follow-ups (defects/observations, NOT blockers):**
1. **Refresh hot-loop** — proactive scheduler refreshes ~10.7×/s (300 s token,
   refresh-5-min-before-expiry → ~0 delay). Floor the delay in
   `app/lib/adapters/keycloak_identity_provider.dart`.
2. **"Hi, User"** — id_token lacks `name`/`preferred_username`; add a mapper to the app
   client (beside the audience mapper).
3. **Custom login theme** — `prompt=login` re-auth page disables Sign In on mobile
   Chrome; fix theme or drop `promptValues:['login']`. Workaround used at the gate:
   clear the user's SSO session so re-sign-in gets the fresh form.
4. **Fix B (robustness)** — switch the redirect to a verified HTTPS App Link
   (assetlinks.json + client redirect-URI update) so it never depends on Custom-Tab
   availability.
5. Keycloak event logging was enabled on the realm for C4 diagnosis (2 h expiry,
   auto-clears) — includes REFRESH_TOKEN, which the hot-loop floods; disable/trim if it
   stays noisy.
6. **Rotate `lilymay`'s password** — it appeared in a screenshot shared during the gate.

Post-weekend list unchanged: Pi password change, AUTH-2 completer-test follow-up, s2s
patch upstreaming, dialect-#12 discard, TTS 1.7B trial (ASSUM-003).
