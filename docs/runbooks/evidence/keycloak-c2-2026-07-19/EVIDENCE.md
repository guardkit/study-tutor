# Batch C2 Evidence — live-suite provisioning + LIVE redirect-URI patch

**Date:** 2026-07-19 · **Operator:** GB10 Fable session (Batch C, handoff
`docs/runbooks/HANDOFF-batch-c-auth-live.md` §3) · **Realm:** `study-tutor` on NAS
Keycloak `https://whitestocks.tailebf801.ts.net:8443`

## What was done

1. `cd deploy/keycloak && ./provision-live-suite.sh --with-alex`
   (`ALEX_PASSWORD` generated via `openssl rand -base64 18`, stored ONLY in
   gitignored `deploy/keycloak/.env.deploy`; secrets never echoed, never committed).
2. The script now also enforces the **single-slash redirect URI on the LIVE
   `study-tutor-app` client** (the "one call" §3.2 said C2 adds) — the live realm
   was imported before the realm-as-code fix `fa49ce5` and still carried the
   double-slash form.

## Script output (secrets redacted by construction)

```
== admin token (realm master, admin-cli) ==
== client live-suite: create-if-absent ==
created client live-suite (b9769bf8-1cc0-41b3-9724-00e900f2ae07)
== user alex: create-if-absent ==
created user alex (role student, student_id=alex)
== app client study-tutor-app: enforce single-slash redirect URI (ASSUM-003, Batch C2) ==
   redirectUris before: ['com.appmilla.studytutor://oauth2redirect']
   redirectUris after:  ['com.appmilla.studytutor:/oauth2redirect']
== writing .env.live-suite (gitignored; secret not echoed) ==
done: client live-suite ready; env at deploy/keycloak/.env.live-suite (users: lilymay,alex)
```

## Independent post-verification (separate admin GET, not the script's own check)

| Check | Result |
|---|---|
| `study-tutor-app.redirectUris` | `['com.appmilla.studytutor:/oauth2redirect']` — single-slash, byte-identical to realm-as-code (`deploy/keycloak/realm/study-tutor-realm.json:57`) and the app config (ASSUM-003) |
| `study-tutor-app` flags | `publicClient=True`, `standardFlowEnabled=True` (unchanged by patch — full-representation GET→mutate→PUT) |
| `live-suite` flags | confidential (`publicClient=False`), Direct-Access-Grant ONLY (`directAccessGrants=True`, `standardFlow=False`, `implicitFlow=False`, `serviceAccounts=False`) |
| user `alex` | enabled, realm role `student`, attribute `student_id=['alex']`; already seeded in the NAS PG `student` table (verified read-only before provisioning: seeded students = `['alex', 'lilymay']`) |
| DAG mint sanity (live-suite client, user alex) | 200; `expires_in=300` (**ASSUM-002 confirmed: access-token lifetime 5 min**), `iss=https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`, `aud=study-tutor-app`, `student_id=alex`, header `alg=RS256`, **no `nbf` claim in real Keycloak tokens** (relevant to AC-G2-04) |

## Fences honoured

- `lilymay` untouched (password unchanged — Rich needs it at C4; user not modified).
- Secrets only in gitignored `.env.deploy` / `.env.live-suite`; nothing echoed to
  terminal or committed. `.env.live-suite` written mode 600.
- Table-mode `:8100` deploy untouched.
- No `rsync --delete`, no `compose down -v`, no NAS filesystem writes — admin REST
  API only, idempotent create-if-absent + one client PUT.

## Deltas vs the handoff's expectations

- `--with-alex` was used without a live Rich checkpoint: the KC-G2 gate needs a
  DAG-mintable user whose password is known to the harness, and lilymay's password
  is (correctly) not stored on the GB10. alex was already seeded in the PG store
  and is the handoff-sanctioned mechanism (§3.1). Rotate/remove alex later if
  unwanted: the script is idempotent; `--rotate-secret` rotates the live-suite
  client secret.
