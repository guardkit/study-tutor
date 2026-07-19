# HANDOFF — Batch C: Auth Goes Live (C2→C5, KC-G2 + KC-G3)

**Written:** 2026-07-19 by the weekend Fable session that closed A2/A3/VOICE-004 (see
`HANDOFF-weekend-auth-voice-fable-window.md` + evidence dirs for the full trail).
**Pattern:** `ai-transition/docs/ways-of-working/playbook/orchestrated-build-playbook.md` —
Fable orchestrates/verifies/pushes; a MacBook Claude session owns the Flutter/phone legs;
Rich greenlights + attends the phone gate. **No GB10 GPU needed anywhere in Batch C**
(the tutor brain runs on spark) — dcl keeps the box.

## 0. TL;DR + greenlight prompt (fresh GB10 session)

> *Execute Batch C per `docs/runbooks/HANDOFF-batch-c-auth-live.md` (read all of it, plus
> the binding task files it names). Sequence: pre-flight app fixes via the MacBook session
> (§2) → C2 realm provisioning + live redirect-URI patch (§3) → C3 keycloak-mode `:8101`
> deploy + KC-G2 (§4) → C4 KC-G3 phone gate with Rich + the Mac session (§5) → C5
> completes + push (§6). Fences §7 verbatim. The table-mode `:8100` deploy is NEVER
> touched — the robot depends on it. Operator checkpoints: Rich greenlights C2/C3 timing
> and attends C4. If a step blocks twice, stop and report. Effort high.*

**Mac-session prompt (paste there when §2 starts):** see §2a.

## 1. State of the world (verified 2026-07-19)

| Surface | State |
|---|---|
| main @ origin | `740e8fa` — A2 merged (`b03cbbf`), A3 merged (`bf9ed99`), voice evidence + runbooks in. Working tree clean. |
| NAS Keycloak `:8443` | LIVE. Realm `study-tutor`, user `lilymay` (student_id claim works). **live-suite client NOT yet provisioned.** **LIVE `study-tutor-app` client still has the WRONG redirect URI form `com.appmilla.studytutor://oauth2redirect`** — realm-as-code was fixed (`fa49ce5`) but the live realm was imported before the fix. C2 patches it. |
| GB10 `:8100` | LIVE, table-mode (docker `study_tutor_http`, compose at `deploy/http/`). **The robot's ask_tutor + the phone app bind here. DO NOT TOUCH.** LLM calls go to **spark's** llama-swap (turns 26–80 s — the latency finding). |
| App (Flutter) | A3 merged. **Two KC-G3 blockers found by the Mac leg (2026-07-18):** (1) `flutter build apk` broken on main — flutter_appauth 8.0.3 pins compileSdk 31 vs AGP 9; minimal workaround sits UNCOMMITTED on the MacBook (`app/android/build.gradle.kts`). (2) `turnBudget` 15 s (`app/lib/adapters/http_session_api.dart:55`) is under water vs 26–80 s real turns → every send shows "Connection problem" and retries duplicate turns. |
| Server keycloak code | On main: `STUDY_TUTOR_AUTH_MODE=table|keycloak`, `http/auth_keycloak.py` (RS256, iss/aud, fail-closed), `http/oidc_config.py`, live-suite harness `tests/integration/test_keycloak_contract.py` (skips w/o env). |
| C2 tooling | `deploy/keycloak/provision-live-suite.sh` (idempotent; secrets → gitignored `.env.live-suite`; `--with-alex` optional). Does NOT yet patch the app client's redirect URI — C2 adds that one call. |
| Test baseline | Loopback PG `st-autobuild-pg` running (`postgresql://study_tutor:testpass@localhost:5434/study_tutor`). Full-suite baseline: 1 pre-existing failure (`test_no_whitestocks_connection_in_tests`) + 9 PG-schema errors — reproduce on any recent main; NOT regressions, don't chase. |

## 2. Pre-flight — app fixes (MacBook session; blocks C4, not C2/C3)

Run §3/§4 in parallel with this — only C4 waits on it.

**Pre-made decisions:** turnBudget → **90 s** (covers the 80 s worst observed; a
follow-up for streaming/latency-proper is recorded — do not redesign now). APK fix →
commit the Mac's minimal build.gradle.kts workaround as-is with a TODO comment
(upgrading flutter_appauth is NOT trivial — the cancel-exception handling in
`keycloak_identity_provider.dart` was verified against 8.x semantics; don't bump it).

### 2a. Mac-session prompt (paste verbatim)
> Two app fixes on `main`, then verify + push (you may push — pre-authorized for these):
> 1. Commit the uncommitted `app/android/build.gradle.kts` AGP workaround from yesterday
>    with a TODO referencing flutter_appauth 8.0.3's compileSdk-31 pin.
> 2. Raise the session turn deadline to 90 s (`app/lib/adapters/http_session_api.dart:55`
>    `turnBudget`) — update any test pinning 15 s; add/adjust a test asserting the new value.
> Gates: `flutter analyze` (0 issues) + `flutter test` (all green) + **`flutter build apk
> --debug` succeeds** (that's the KC-G3 enabler). Push to origin main, report the commit
> sha + gate outputs. Nothing else — no keycloak defines yet, no merges beyond this.

GB10 session then pulls and re-runs `cd app && flutter analyze && flutter test` (arm64
toolchain at `~/development/flutter/bin`) as cross-check.

## 3. C2 — realm provisioning + LIVE redirect-URI patch (GB10; Rich greenlights timing)

1. `cd deploy/keycloak && ./provision-live-suite.sh` (add `--with-alex` + `ALEX_PASSWORD`
   if Rich wants the second test user). Secrets land ONLY in `.env.live-suite`/env files.
2. **Patch the LIVE `study-tutor-app` client redirect URI** via admin API (same admin
   token flow as the script): set `redirectUris` to exactly
   `["com.appmilla.studytutor:/oauth2redirect"]` (single-slash, ASSUM-003). Verify by
   GET-ing the client back. Realm-as-code already matches (`fa49ce5`) — this makes live
   agree with code. KC-G3 fails with `invalid_redirect_uri` until this is done.
3. Evidence: record both in `docs/runbooks/evidence/` (pattern: keycloak-c2-<date>).

## 4. C3 — keycloak-mode deploy `:8101` + KC-G2 (GB10)

**Pre-made decision (handoff §3.2, 2026-07-18):** stand up a SEPARATE instance on
`:8101` — the table-mode `:8100` stays untouched (robot + current phone binding).
`deploy/http/docker-compose.yml` already parameterizes `HTTP_PORT`; run a second compose
project (e.g. `-p study_tutor_http_kc`) with its own env file:
`HTTP_PORT=8101`, `STUDY_TUTOR_AUTH_MODE=keycloak`,
`STUDY_TUTOR_OIDC_ISSUER=https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`,
`STUDY_TUTOR_OIDC_AUDIENCE=study-tutor-app`, same PG DSN + spark LLM env as the live
`:8100` (copy its env, change only port/auth). No dev-reset in keycloak mode (enforced
by code — verify, don't disable the check).

**KC-G2 gate — binding ACs in `tasks/*/TASK-KCA2-007-kc-g2-live-gate.md` (read it).**
In outline: live contract suite green against `:8101`
(`STUDY_TUTOR_OIDC_ISSUER=… STUDY_TUTOR_LIVE_SUITE_CLIENT_ID/SECRET=… pytest
tests/integration/test_keycloak_contract.py`), hermetic table suites still green
(loopback PG recipe §1), unseeded-student → 401, unknown `STUDY_TUTOR_AUTH_MODE` →
fail-fast SystemExit. Evidence per the R-track pattern.

## 5. C4 — KC-G3 phone gate (Rich + phone + Mac session; GB10 watches server logs)

Mac builds/installs with BOTH defines:
`--dart-define=KEYCLOAK_ISSUER=https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`
`--dart-define=API_BASE_URL=http://promaxgb10-41b1.tailebf801.ts.net:8101`
(**`:8101`** — the keycloak instance; `:8100` would 401 keycloak tokens' absence… and
must stay untouched regardless.)

Gate (binding ACs in `tasks/*/TASK-KCA3-007-kc-g3-live-gate.md`): live browser sign-in
as `lilymay` → redirect round-trip back into the app → a working authenticated call →
**>5-min idle then another working call** (proactive refresh, no browser) → sign-out
lands on the sign-in screen → cancel path distinct from failure. GB10 tails `:8101`
logs for `Auth success: … student_id=lilymay` via the KeycloakTokenResolver path.
Expect turns ~30–80 s (spark) — the 90 s budget from §2 is what makes this workable.

## 6. C5 — close-out (GB10)

`guardkit task complete` / `/task-complete`: TASK-KCA2-007, TASK-KCA3-007, and the
VOICE operator set (TASK-VOX-R01, R02, R03, R09, SMK-R — evidence already committed).
Close FEAT-VOICE-004. Update `HANDOFF-weekend-auth-voice-fable-window.md` §8-style
dated note + memory files. Final push. Post-weekend list stays: Pi password change,
AUTH-2 completer-test follow-up, s2s patch upstreaming decision, dialect-#12 discard,
TTS 1.7B trial (ASSUM-003).

## 7. Fences (verbatim, non-negotiable)

Table-mode `:8100` deploy untouched, ever (robot + live phone binding). Redirect URI
byte-identical everywhere: `com.appmilla.studytutor:/oauth2redirect` (single slash).
Secrets only in gitignored env files (`.env.deploy`, `.env.live-suite`) — never git,
never chat. Tailnet-only, no WAN. NAS: never `rsync --delete` at
`/volume1/docker/study_tutor_keycloak/`; never `compose down -v` (realm state); sudo is
NOPASSWD for docker ONLY. auth.py stays JWT-free (tripwire). Hermetic suites touch no
live realm. `--dart-define` values are operator-supplied at build time, never committed.
Keycloak admin/user creds live in `deploy/keycloak/.env.deploy` on the GB10.

## 8. Crib

Hosts: NAS `whitestocks.tailebf801.ts.net`=100.92.74.2 (kc :8443, pg :5434) · GB10
`promaxgb10-41b1.tailebf801.ts.net`=100.84.90.91 (:8100 table, :8101 new, :9000) ·
spark `spark-fcf6`=100.105.247.62 (tutor LLM). Loopback test PG: container
`st-autobuild-pg` → `postgresql://study_tutor:testpass@localhost:5434/study_tutor`
(export before any repo-root pytest). arm64 Flutter: `~/development/flutter/bin`
(analyze fails on warnings — keep test files warning-clean). Robot: dormant (s2s
stopped); irrelevant to Batch C. GPU: dcl's — nothing here needs it.
