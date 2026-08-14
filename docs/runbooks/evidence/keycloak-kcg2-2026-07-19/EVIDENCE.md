# KC-G2 Evidence — keycloak-mode `:8101` deploy + live gate (TASK-KCA2-007)

**Date:** 2026-07-19 · **Operator:** GB10 Fable session (Batch C3, handoff
`docs/runbooks/HANDOFF-batch-c-auth-live.md` §4) · **Gate:** KC-G2, binding ACs in
`tasks/backlog/TASK-KCA2-007-kc-g2-live-gate.md` · **Verdict: ALL PASS**

## Deploy shape (pre-made decision, handoff §3.2 2026-07-18)

Second, fully separate compose project — the table-mode `:8100` deploy untouched:

| | table-mode (robot + phone) | keycloak-mode (new) |
|---|---|---|
| compose project | `study_tutor_http` | `study_tutor_http_kc` |
| container | `study_tutor_http` | `study_tutor_http_kc` |
| image | `study-tutor:latest` (`bd5496f0`, built Jul 13) | **`study-tutor:kc-a2`** (`e428a20a`, built 2026-07-19 from main `bbb0af7`) |
| host port | 8100 | 8101 |
| auth | `table` | `keycloak` (`STUDY_TUTOR_AUTH_MODE=keycloak`) |
| env | `deploy/http/.env` | `deploy/http/.env.kc` (gitignored) — copy of `.env`, changed ONLY port/auth: `HTTP_PORT=8101`, `STUDY_TUTOR_HTTP_TOKENS={}`, dev-reset unset, OIDC vars added |

Overlay: `deploy/http/docker-compose.keycloak.yml` (committed; parameterized, no
secrets). Issuer `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`,
audience `study-tutor-app`.

**KC-D2 (JWKS via tailnet IP):** containers don't resolve ts.net MagicDNS, so the
overlay pins `whitestocks.tailebf801.ts.net -> 100.92.74.2` via `extra_hosts`.
In-container proof: `getent hosts whitestocks.tailebf801.ts.net` →
`100.92.74.2`. The issuer/JWKS URL keep the ts.net NAME (iss pinning + TLS
hostname match); only resolution is overridden. JWKS fetch verified working by
every successful validation below.

**`:8100` untouched (fence):** after all of C3, `docker inspect study_tutor_http`
→ same image `sha256:bd5496f0…`, `started=2026-07-13T18:50:36Z`, status running;
`:8100/healthz` 200. The `kc-a2` image tag means `study-tutor:latest` was never
rebuilt/retagged.

## AC-G2-01 — keycloak-mode server live against the A1 realm ✅

Boot log: store wired to `100.92.74.2:5434`, serving on 8100-in-container
(host 8101), healthcheck healthy. Container env verified:
`STUDY_TUTOR_AUTH_MODE=keycloak`, issuer + audience as above, `STUDY_TUTOR_HTTP_TOKENS={}`.

## AC-G2-02 — live contract suite green + e2e against `:8101` ✅

Suite (env surface from gitignored `.env.live-suite` + users JSON built in-shell
from `.env.deploy`; loopback PG DSN exported):

```
tests/integration/test_keycloak_contract.py::test_token_endpoint_url_construction PASSED
tests/integration/test_keycloak_contract.py::test_token_response_parsing PASSED
tests/integration/test_keycloak_contract.py::test_mint_token_for_test_student PASSED   <- real DAG mint, live realm
tests/integration/test_keycloak_contract.py::test_mint_token_invalid_username_fails PASSED
tests/integration/test_keycloak_contract.py::test_hermetic_suites_never_mint_real_tokens PASSED
5 passed in 0.26s
```

End-to-end for a **seeded student** (alex — seeded in the NAS PG `student` table;
lilymay reserved for Rich's C4 sign-in, credentials untouched): DAG-minted token →
`GET :8101/api/sessions` → **200**. Server log (KeycloakTokenResolver path):

```
INFO study_tutor.http.auth_keycloak: Token validated successfully: student_id=alex, iss=https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor
INFO study_tutor.http.auth: Auth success: Resolved student_id=alex from token
```

**C4 pre-check (beyond the AC, so Rich's attended gate can't stall on a dead LLM
path):** full authenticated session on `:8101` — `start` 200 (topic planned),
`turn` 200 in **16.2 s** with a tutor response (spark path live), `end` 200.
(Reply content shows the known Gemma system-prompt-echo quirk — coach/latency
lane's follow-up, not an auth-gate concern.)

## AC-G2-03 — hermetic suite green in table mode, same build ✅

Full repo suite on main `bbb0af7` (the commit the kc-a2 image is built from),
loopback throwaway PG (`st-autobuild-pg`, localhost:5434):

```
1 failed, 1597 passed, 7 skipped, 197 warnings, 9 errors in 50.66s
```

Identical failure set to the §1 baseline: pre-existing
`test_no_whitestocks_connection_in_tests` + the 9 unmigrated-PG-schema errors in
`test_session_integration_guards_and_scope.py` — reproduce on any recent main, not
regressions. Keycloak contract tests **skipped cleanly** without live env
(hermetic suites minted no real tokens; no live realm touched).

## AC-G2-04 — ASSUM-001 confirmed against the real resolver ✅

Wall-clock probe, real Keycloak token (lifetime 300 s), deployed `:8101` resolver:

```
[10:15:05] minted for alex: lifetime=300s, nbf claim present: False
[10:15:05] T+0 fresh call -> 200 (expect 200)
[10:20:35] exp+30s call -> 200 (expect 200: inside 60s leeway)
[10:21:35] exp+90s call -> 401 (expect 401: outside 60s leeway)
ASSUM-001 VERDICT: PASS
```

Server log at the refusal: `WARNING study_tutor.http.auth_keycloak: Token expired:
Signature has expired`. **nbf:** real Keycloak access tokens carry **no `nbf`
claim** (observed on every minted token); the resolver validates `nbf` only when
present (`require_nbf=False`, `verify_nbf=True`) with the same 60 s leeway —
that branch is pinned by the hermetic unit suite
(`tests/unit/http/test_auth_keycloak.py`, in-test RSA keys). Documented-leeway
behaviour matches.

## AC-G2-05 — ASSUM-007 confirmed: unknown auth mode fails fast ✅

```
$ docker run --rm --env-file .env.kc -e STUDY_TUTOR_AUTH_MODE=bogus study-tutor:kc-a2 study-tutor serve-http ...
[study-tutor] Error: OIDC configuration validation failed:
  - Invalid STUDY_TUTOR_AUTH_MODE: 'bogus'. Must be 'table' or 'keycloak'.
exit code: 1
```

`SystemExit(1)` at boot, no silent fallback.

## Handoff §4 outline extras ✅

| Check | Result |
|---|---|
| Unseeded student → 401 | Temp KC user `kcg2-unseeded-probe` (student_id not in PG), valid minted token → `GET /api/sessions` → **401** `"Student kcg2-unseeded-probe is not seeded…"`; guard log line captured; **probe user deleted** (0 matches after) — realm left clean |
| Dev-reset never in keycloak mode | `POST :8101/__dev__/reset` → **404** (route not mounted; code check verified at `cli/main.py` — forced `dev_reset=false` in keycloak branch, check NOT disabled) |
| Missing auth header | 401 |
| Garbage token (`not.a.jwt`) | 401 (fail-closed, no 500) |
| Old table token (`<bearer-alex>`) | 401 (table resolver inactive in keycloak mode) |

## Fences honoured

Table-mode `:8100` untouched (verified above) · secrets only in gitignored env
files, none echoed/committed · tailnet-only (all endpoints 100.x/ts.net) · no NAS
filesystem operations · `auth.py` untouched (no code changes this batch beyond
`provision-live-suite.sh` + compose overlay) · hermetic suites touched no live
realm.
