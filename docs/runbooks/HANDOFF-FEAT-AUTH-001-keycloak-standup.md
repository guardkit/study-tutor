# HANDOFF — FEAT-AUTH-001 Keycloak Standup (resume point)

**Written:** 2026-07-16 · **Author:** Claude (driven session) · **Owner:** Richard
**Task:** TASK-KC-006 (operator_handoff, KC-G1 gate) · **Runbook:** [RUNBOOK-study-tutor-keycloak-standup.md](RUNBOOK-study-tutor-keycloak-standup.md)

---

## TL;DR

**Keycloak is LIVE and healthy on the NAS** (`Up 21h (healthy)` as of this writing). The realm imported, TLS is valid, and **every automated KC-G1 gate passed**. What remains is: (A) create user **Lilymay**, (B) three human-eyes verifications I can't do headless, (C) commit the repo bug-fixes I made live, (D) close TASK-KC-006.

Service URL: **https://whitestocks.tailebf801.ts.net:8443** (tailnet-only)
Admin console: **https://whitestocks.tailebf801.ts.net:8443/admin** — user `admin`

---

## Access & where things live (read first)

| Thing | Value |
|---|---|
| NAS SSH | `ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 RichardWoollcott@whitestocks.tailebf801.ts.net` |
| Deploy-host secrets | `deploy/keycloak/.env.deploy` (this repo, **gitignored, chmod 600**) — holds `KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_PASSWORD`, etc. |
| Same secrets on NAS | `/volume1/docker/study_tutor_keycloak/.env` (chmod 600) |
| **Admin password** | `grep KC_BOOTSTRAP_ADMIN_PASSWORD deploy/keycloak/.env.deploy` (recover it here if not saved) |
| NAS deploy root | `/volume1/docker/study_tutor_keycloak/` (compose, Dockerfile, realm/, certs/, .env) |
| Container / image | `study_tutor_keycloak` / `quay.io/keycloak/keycloak:26.0.7` (built optimized) |
| Docker network | `study_tutor_default` (shared with `study_tutor_postgres`) |
| Keycloak DB | database `keycloak`, role `keycloak` on the running `study_tutor_postgres` (superuser is **`study_tutor`**, not `postgres`) |
| TLS cert | `/volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.{crt,key}` — Let's Encrypt, **expires 2026-10-13** (auto-renews ~90d) |
| Backups | `/volume1/docker/study_tutor/backup.sh` (nightly, DSM Task Scheduler) → `/volume1/docker/study_tutor/backups/keycloak_<date>.dump` |

---

## DONE — automated gates (evidence captured this session)

| Gate | Result |
|---|---|
| KC-G0a — TLS cert minted | ✅ CN=`whitestocks.tailebf801.ts.net`, Let's Encrypt, valid → 2026-10-13 |
| KC-G0b — keycloak DB + role + isolation | ✅ created; `keycloak` role is LOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE; connecting it to `study_tutor` DB → **permission denied** (KC-D3 proven) |
| KC-G1a — container healthy | ✅ `healthy` |
| KC-G1b — pinned issuer over valid TLS | ✅ `.well-known/openid-configuration` → `issuer: https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` |
| KC-G1c — RAM headroom | ✅ ~5.8 GiB avail / 7.8 total (Keycloak ~300 MB, 2g limit) |
| AC-G1-06 (partial) — realm structure | ✅ roles `student`,`parent`; clients `study-tutor-app`,`reachy-robot`; **`student_id` protocol mapper on both** |
| Phase 5 — keycloak backup | ✅ `backup.sh` updated + live run produced **both** `study_tutor` and `keycloak` dumps |

**Exposure:** only `8443` is published (management port `9000` intentionally NOT published).

---

## REMAINING

### A. Phase 4 — create Lilymay (closes the rest of AC-G1-06)

Needs from Richard: Lilymay's **`student_id`** and a **password** (or generate one). Then run this from the deploy host (the study-tutor repo root):

```bash
cd <study-tutor repo>
source deploy/keycloak/.env.deploy
BASE="https://whitestocks.tailebf801.ts.net:8443"
LILYMAY_STUDENT_ID="<FILL IN>"
LILYMAY_PASSWORD="<FILL IN or: $(openssl rand -base64 18)>"

TOKEN=$(curl -sS "$BASE/realms/master/protocol/openid-connect/token" \
  -d client_id=admin-cli -d "username=$KC_BOOTSTRAP_ADMIN_USERNAME" \
  --data-urlencode "password=$KC_BOOTSTRAP_ADMIN_PASSWORD" -d grant_type=password \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 1) create user with the student_id attribute (REQUIRED — backend derives student_id from this claim)
curl -sS -X POST "$BASE/admin/realms/study-tutor/users" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d "{
    \"username\":\"lilymay\",\"enabled\":true,
    \"attributes\":{\"student_id\":[\"$LILYMAY_STUDENT_ID\"]}
  }"

UID=$(curl -sS "$BASE/admin/realms/study-tutor/users?username=lilymay" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")

# 2) set password (temporary=false = permanent)
curl -sS -X PUT "$BASE/admin/realms/study-tutor/users/$UID/reset-password" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d "{\"type\":\"password\",\"value\":\"$LILYMAY_PASSWORD\",\"temporary\":false}"

# 3) assign realm role "student"
ROLE=$(curl -sS "$BASE/admin/realms/study-tutor/roles/student" -H "Authorization: Bearer $TOKEN")
curl -sS -X POST "$BASE/admin/realms/study-tutor/users/$UID/role-mappings/realm" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "[$ROLE]"

# 4) verify
curl -sS "$BASE/admin/realms/study-tutor/users/$UID" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;u=json.load(sys.stdin);print('user',u['username'],'student_id',u['attributes']['student_id'])"
```

Then **seed the app student record** (runbook Phase 4b):
```bash
STUDY_TUTOR_PG_DSN="postgresql://study_tutor:<STUDY_TUTOR_PG_PASSWORD>@whitestocks.tailebf801.ts.net:5434/study_tutor" \
  .venv/bin/python -m study_tutor.cli seed-students --student-ids "$LILYMAY_STUDENT_ID"
```
**Do not commit** Lilymay's id/password anywhere (PII posture, KC-D2).

### B. Human verification (can't be done headless)

- **AC-G1-01** — On a phone/laptop on the tailnet, open `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor/account` → must load with **no cert warning**. (Cert chain already validated via curl; this is the eyes-on confirmation.)
- **AC-G1-04** — In the **Aruba Instant On** app / `portal.arubainstanton.com` → Policies → Port Forwarding: confirm **no** rule forwards any WAN port to the NAS `:8443`. (Ideally also probe `:8443` from a non-tailnet network → should fail.)
- **AC-G1-05** — Admin console reachable only over the tailnet; no admin creds in any committed file (they're in `.env` only). ✅ on the creds part; confirm the reachability.
- **AC-G1-07** (note only) — cert auto-renews ~90d; expiry **2026-10-13** recorded.

### C. Commit the repo bug-fixes made live (IMPORTANT — artifacts must match reality)

Uncommitted now: `deploy/keycloak/docker-compose.yml` (my fixes). **Still to fix in-repo:** `deploy/keycloak/.env.deploy.example` and the runbook. All are genuine KC-001/KC-002 bugs the AutoBuild Coach couldn't catch without a live NAS:

| # | File | Bug → Fix |
|---|---|---|
| 1 | `docker-compose.yml` (done, uncommitted) | external network `study_tutor_postgres_default` → **`study_tutor_default`** |
| 2 | `docker-compose.yml` (done, uncommitted) | `depends_on: study_tutor_postgres` is invalid (external container) → **removed** |
| 3 | `docker-compose.yml` (done, uncommitted) | published mgmt port `9000:9000` → **removed** (not needed; tightens exposure) |
| 4 | `docker-compose.yml` (done, uncommitted) | healthcheck did plain-HTTP over the TLS mgmt port (+ no curl/wget in image) → **TCP-open probe** on `localhost:9000` |
| 5 | `.env.deploy.example` line 8 (**TODO**) | `KC_HOSTNAME=whitestocks.tailebf801.ts.net:8443` is rejected by KC26 → must be full URL **`https://whitestocks.tailebf801.ts.net:8443`** |
| 6 | `docs/runbooks/RUNBOOK-...-standup.md` (**TODO**) | Phase 2 uses `psql -U postgres`; real superuser is **`study_tutor`**. Also document: key must be `chmod 640` for container uid 1000/gid 0; use rsync/`ssh 'cat >'` not scp (DSM sftp disabled); cert mint via explicit `--cert-file/--key-file`. |
| 7 | `deploy/keycloak/Dockerfile` (optional) | comment says 26.6.x but pins `26.0.7` — align comment or bump. |

Suggested commit: `fix(keycloak): correct compose network/depends_on/healthcheck + KC_HOSTNAME URL form + runbook superuser (live-validated on NAS standup)`

### D. Close the task

After A + B pass: `guardkit task complete TASK-KC-006` (the only way an operator_handoff task leaves `deferred`). FEAT-AUTH-001 is already merged/completed; this just records the runtime gate.

---

## Environment gotchas (hard-won this session)

- **NAS sudo is NOPASSWD for `/usr/local/bin/docker` ONLY.** `tailscale`, `chmod`, `mv`, `find` on system paths all prompt for the DSM password. Anything root-but-not-docker is a **you-interactive** step.
- **Cert mint is interactive** (`sudo tailscale cert …`). The tailscaled socket isn't in the standard path, so the containerized-root workaround didn't pan out — just run it by hand. Binary: `/var/packages/Tailscale/target/bin/tailscale`. Use explicit `--cert-file`/`--key-file` (cwd-independent).
- **NEVER `rsync --delete` into `/volume1/docker/study_tutor_keycloak/`** — the certs live only on the NAS and `--delete` wipes them (happened once; recovered by re-mint). The sync command now excludes `certs/`, `.env`, `.env.deploy`.
- **scp is dead on this DSM** (sftp subsystem disabled). Use `rsync -e ssh` or `ssh NAS 'cat > /path' < localfile`.
- **Cert key perms:** container runs uid 1000/gid 0; key must be `640 root:root` (group-readable) or Keycloak can't read it. Root-owned file perms can be fixed **without the DSM password** via a throwaway root container: `sudo -n docker run --rm -v <certs>:/c postgres:16 chmod 640 /c/<key>`.
- **Health/mgmt port 9000** serves HTTPS and is not published; the healthcheck is an internal TCP-open probe.

## Re-verify the service is up (quick)

```bash
source deploy/keycloak/.env.deploy   # from repo root
ssh -i ~/.ssh/fleet_memory_nas_ed25519 RichardWoollcott@whitestocks.tailebf801.ts.net \
  "sudo -n /usr/local/bin/docker ps --filter name=study_tutor_keycloak --format '{{.Status}}'"
curl -sS https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor/.well-known/openid-configuration \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['issuer'])"
# expect: Up … (healthy)  and  https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor
```
