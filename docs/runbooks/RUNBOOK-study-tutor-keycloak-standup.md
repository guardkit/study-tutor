# RUNBOOK — study-tutor Keycloak Standup (Identity Provider + OIDC)

**Date:** 2026-07-15
**Status:** Ready to execute. Phase 0 largely **reuses** the already-provisioned NAS prep from the postgres deploy; Phases 1–5 configure the new identity service.
**Purpose:** Stand up a **study-tutor-dedicated** Keycloak 26.6.x IdP as the OIDC authentication provider for [FEAT-AUTH-001](../history/feature-spec-feat-auth-001-keycloak-standup-on-the-nas-per-design-kc-d1-d-history.md), per [ADR-ARCH-028](../architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md).
**Scope:** The **production identity provider only**. Test/dev realms and CI hermetic environments are out of scope and must never point to production secrets.
**Related:** [ADR-ARCH-028](../architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md), [keycloak-auth-user-management-design.md](../design/keycloak-auth-user-management-design.md) (KC-D1/D2), [RUNBOOK-study-tutor-postgres-deploy.md](RUNBOOK-study-tutor-postgres-deploy.md) (the G0–G7 gate model this mirrors).

---

## 0. How this differs from the postgres deploy (read first)

| | Postgres deploy | **Keycloak deploy (this runbook)** |
|---|---|---|
| Purpose | durable learner state store | **identity provider + OIDC issuer** |
| Container | `study_tutor_postgres` | **`study_tutor_keycloak`** (Keycloak 26.6.x, optimized start) |
| Host port | 5434 | **8443** (HTTPS/TLS only, no HTTP) |
| Data | schema owned by Alembic | **realm-as-code** (JSON import), users **runbook-created never committed** |
| Backup | nightly `pg_dump` of `study_tutor` DB | **nightly `pg_dump` of `keycloak` DB** (already in extended `backup.sh` from TASK-KC-004) |
| TLS | N/A (postgres wire protocol) | **Tailscale Let's Encrypt cert** mounted; issuer pins to `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` |
| Dependencies | standalone | **depends on `study_tutor_postgres`** (co-located `keycloak` DB via TASK-KC-003) |
| Memory | postgres default | **1-2 GB container limit** (`mem_limit: 2g`) |

**Reuses from postgres deploy (G0):** SSH key, NAS admin group, User Home, docker-sudoers, firewall posture — all proven. Only new: `/volume1/docker/study_tutor_keycloak/` directory and TLS cert provisioning.

---

## 1. Credentials & secrets summary

| Item | Lives where | Notes |
|---|---|---|
| SSH **key** (`~/.ssh/fleet_memory_nas_ed25519`) | deploy host (GB10/Mac), agent | **Reuse** the existing NAS key from the postgres deploy |
| `deploy/keycloak/.env` | NAS, `chmod 600`, rendered by deploy | `KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_USERNAME`, `KC_BOOTSTRAP_ADMIN_PASSWORD`, `KC_HOSTNAME`, `KC_TLS_CERT_PATH`, `KC_TLS_KEY_PATH` |
| `deploy/keycloak/.env.deploy` | deploy host only, `chmod 600`, gitignored | `NAS_HOST`, `NAS_USER`, `NAS_SSH_PORT`, `NAS_DOCKER_ROOT=/volume1/docker/study_tutor_keycloak`, plus all KC_* values |
| TLS cert/key | NAS `/volume1/docker/study_tutor_keycloak/certs/` | **Tailscale Let's Encrypt cert** for `whitestocks.tailebf801.ts.net` |
| Keycloak admin console | `https://whitestocks.tailebf801.ts.net:8443/admin` | Bootstrap admin credentials from `.env` (env-only, **never committed**) |
| Realm users (Lilymay, Alex) | Created in admin console | **Never committed** — deliberate PII posture for a minor's identity |

**CRITICAL:** Users and secrets **never in git**. The realm JSON (`deploy/keycloak/realm/study-tutor-realm.json`) defines the realm structure (clients, roles, mappers) but **not** users — those are provisioned manually post-import (Phase 4) and survive realm re-imports per ASSUM-003.

`deploy/keycloak/.env.deploy.example` (committed):

```bash
# Database connection (co-located keycloak database on study_tutor_postgres instance)
KC_DB_PASSWORD=                            # generate: openssl rand -base64 24

# Hostname (pinned for stable issuer — ADR-ARCH-028 D1)
KC_HOSTNAME=whitestocks.tailebf801.ts.net:8443
KC_HTTPS_PORT=8443

# TLS certificates (tailscale cert paths on NAS host)
KC_TLS_CERT_PATH=/volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.crt
KC_TLS_KEY_PATH=/volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.key

# Bootstrap admin (initial admin user, env-only)
KC_BOOTSTRAP_ADMIN_USERNAME=admin          # or your choice
KC_BOOTSTRAP_ADMIN_PASSWORD=               # generate: openssl rand -base64 24

# Deployment metadata
NAS_HOST=whitestocks.tailebf801.ts.net
NAS_USER=RichardWoollcott
NAS_SSH_PORT=22
NAS_DOCKER_ROOT=/volume1/docker/study_tutor_keycloak
```

---

## Phase 0 — NAS prep (mostly DONE — inherited from postgres deploy)

Already provisioned by the postgres NAS runbook and **not repeated**: SSH key, `RichardWoollcott` in administrators, User Home service, `/etc/sudoers.d/fleet_memory_docker` (docker NOPASSWD). **Only new:**

```bash
# on the NAS (interactive; DSM password OK here) — create the dedicated data root
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST" \
  'mkdir -p /volume1/docker/study_tutor_keycloak/certs'
```

Network exposure / access scoping: tailnet-only, **no WAN** — see **Phase 6** for the full three-layer posture (mirrors the postgres 5434 deployment).

**GATE G0 (from the deploy host) — reuse the existing proof from postgres deploy:**
```bash
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p 22 "$NAS_USER@$NAS_HOST" \
  'echo SSH_OK && sudo -n /usr/local/bin/docker version --format "DOCKER_OK {{.Server.Version}}"'
# PASS: SSH_OK + DOCKER_OK <ver>, no password prompt. FAIL → see postgres runbook Phase 0.
```

---

## Phase 1 — TLS cert mint (Tailscale Let's Encrypt)

Keycloak requires an **https issuer** for OIDC on native mobile (AppAuth-family libraries reject plain http off-loopback). Mint a Let's Encrypt cert via `tailscale cert` for the NAS's MagicDNS name.

### Primary path: Direct cert mount (attempt first)

```bash
# On the NAS (interactive):
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST"

# Mint the cert (Tailscale CLI, ~90-day renewal):
sudo tailscale cert whitestocks.tailebf801.ts.net

# Move to keycloak cert dir:
sudo mv whitestocks.tailebf801.ts.net.{crt,key} /volume1/docker/study_tutor_keycloak/certs/
sudo chmod 600 /volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.key
sudo chmod 644 /volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.crt

# GATE KC-G0a: Verify cert file and issuer name
openssl x509 -in /volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.crt -noout -subject -issuer
# PASS: Subject CN=whitestocks.tailebf801.ts.net, Issuer Let's Encrypt (R3 or similar)
```

**Cert renewal (automatic):** Tailscale cert renews **~90 days** unattended. Check expiry periodically with:
```bash
openssl x509 -in /volume1/docker/study_tutor_keycloak/certs/whitestocks.tailebf801.ts.net.crt -noout -dates
```

### Fallback A: Tailscale serve (if direct mount fails on DSM)

If DSM's Tailscale package prevents direct cert mount or container mounts fail:

```bash
# On the NAS: front Keycloak with tailscale serve (preserves issuer name)
sudo tailscale serve --https 8443 https://localhost:8080

# Update .env: set KC_HTTPS_PORT=8080 (Keycloak listens on 8080, serve fronts it on 8443)
# Issuer name remains: https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor
```

### Fallback B: GB10 placement (last resort)

If both above fail, move Keycloak to the GB10 where `tailscale cert` is well-trodden:
- Change `NAS_HOST` to GB10's tailnet address
- Postgres DB connection requires `host:5434` via `extra_hosts` instead of service name
- **Loss:** GB10 is not a backup target (durability degrades; mitigate with off-box dumps)

**Issuer name preserved across all fallbacks:** `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` — clients pin this, so it must not change.

---

## Phase 2 — Database + role (apply TASK-KC-003 init SQL)

Keycloak stores realm/user state in a dedicated `keycloak` database on the existing `study_tutor_postgres` instance. Apply the init SQL from TASK-KC-003.

```bash
set -euo pipefail
source deploy/keycloak/.env.deploy
SSH="ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p ${NAS_SSH_PORT} ${NAS_USER}@${NAS_HOST}"

# Copy init SQL to NAS
scp -i $HOME/.ssh/fleet_memory_nas_ed25519 -P ${NAS_SSH_PORT} \
  deploy/keycloak/init-keycloak-db.sql ${NAS_USER}@${NAS_HOST}:/tmp/

# Apply SQL (creates keycloak DB + role, sets password from .env)
$SSH "sudo -n /usr/local/bin/docker exec -i study_tutor_postgres psql -U postgres -d study_tutor" <<EOF
\i /tmp/init-keycloak-db.sql
ALTER USER keycloak PASSWORD '${KC_DB_PASSWORD}';
EOF

# GATE KC-G0b: Verify keycloak DB and role
$SSH "sudo -n /usr/local/bin/docker exec study_tutor_postgres psql -U postgres -d keycloak -c 'SELECT 1;'"
# PASS: returns 1. FAIL: DB or role creation failed — check logs, re-run SQL.
```

**Isolation (KC-D3):** The `keycloak` role owns the `keycloak` database. The `study_tutor` role has **no grants** into it — zero cross-project access.

---

## Phase 3 — Deploy + realm import (compose up with realm-as-code)

Deploy Keycloak with the committed realm JSON (TASK-KC-002) imported via `--import-realm`.

```bash
set -euo pipefail
source deploy/keycloak/.env.deploy
SSH="ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p ${NAS_SSH_PORT} ${NAS_USER}@${NAS_HOST}"

# 3a. Sync compose + realm (repo is canonical)
rsync -avz -e "ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -P ${NAS_SSH_PORT}" \
  --exclude '.env*' deploy/keycloak/ ${NAS_USER}@${NAS_HOST}:${NAS_DOCKER_ROOT}/

# 3b. Render runtime .env on the NAS (all KC_* values), lock it down
$SSH "cat > ${NAS_DOCKER_ROOT}/.env <<'ENV_EOF'
KC_DB_PASSWORD=${KC_DB_PASSWORD}
KC_HOSTNAME=${KC_HOSTNAME}
KC_HTTPS_PORT=${KC_HTTPS_PORT}
KC_TLS_CERT_PATH=${KC_TLS_CERT_PATH}
KC_TLS_KEY_PATH=${KC_TLS_KEY_PATH}
KC_BOOTSTRAP_ADMIN_USERNAME=${KC_BOOTSTRAP_ADMIN_USERNAME}
KC_BOOTSTRAP_ADMIN_PASSWORD=${KC_BOOTSTRAP_ADMIN_PASSWORD}
ENV_EOF
chmod 600 ${NAS_DOCKER_ROOT}/.env"

# 3c. Up (with --import-realm for realm-as-code)
$SSH "cd ${NAS_DOCKER_ROOT} && sudo -n /usr/local/bin/docker compose up -d"

# GATE KC-G1a — container healthy (may take 60s for optimized start)
sleep 30  # initial start period
$SSH "sudo -n /usr/local/bin/docker ps --filter name=study_tutor_keycloak --format '{{.Status}}'"
# PASS: starts with "Up" and "(healthy)" after ~60s. FAIL: docker logs study_tutor_keycloak, fix, re-run.
```

**Realm import behavior (ASSUM-003):** `--import-realm` is **non-overwriting** — it imports the realm structure (clients, roles, mappers) but **does not delete existing users**. Runbook-created users (Lilymay, Alex) survive re-imports, which is the intended idempotency posture.

---

## Phase 4 — User provisioning (manual, never committed)

Create production user **Lilymay** in the Keycloak admin console **and** seed the student record. Dev realm additionally gets **Alex** + the `live-suite` test client.

### 4a. Create Lilymay (production realm user)

```bash
# Access admin console (from a device on the tailnet):
# https://whitestocks.tailebf801.ts.net:8443/admin
# Login with KC_BOOTSTRAP_ADMIN_USERNAME / KC_BOOTSTRAP_ADMIN_PASSWORD from .env

# In admin console:
# 1. Select realm: "study-tutor"
# 2. Users → Add user:
#    - Username: lilymay
#    - Email: (optional)
#    - First/Last name: (optional)
#    - Enabled: ON
# 3. Credentials → Set password (temporary: OFF)
# 4. Attributes → Add attribute:
#    - Key: student_id
#    - Value: <Lilymay's actual student_id from the app>
# 5. Role mappings → Assign role: "student" (realm role from the imported JSON)
```

**CRITICAL:** The `student_id` attribute is **required** — the backend derives `student_id` from this claim (KC-D3 mapping). Without it, authentication will succeed but API calls will fail.

### 4b. Seed student record in the app

```bash
# From the study-tutor app env (GB10 or dev host):
STUDY_TUTOR_PG_DSN="postgresql://study_tutor:<password>@whitestocks.tailebf801.ts.net:5434/study_tutor" \
  .venv/bin/python -m study_tutor.cli seed-students --student-ids <Lilymay's student_id>

# Verify seed:
STUDY_TUTOR_PG_DSN="..." .venv/bin/python -m study_tutor.cli list-students
# PASS: Lilymay's student_id appears. FAIL: check DB connection or seed command.
```

### 4c. Dev realm: Add Alex + live-suite client (optional)

If the dev realm is configured (separate from production):
- Repeat 4a for user "alex" with a dev `student_id`
- Create client "live-suite" (confidential, service account enabled) for automated tests
- **Never commit** these credentials — store in `.env.test` (gitignored)

---

## Phase 5 — Backup configuration (extended backup.sh from TASK-KC-004)

Realm/user state is **non-reindexable** (same durability class as learner data), so the nightly `pg_dump` must cover the `keycloak` database. This is already implemented in the extended `deploy/postgres/backup.sh` from TASK-KC-004.

**Verify backup includes keycloak:**

```bash
# Check backup.sh has the keycloak dump block:
grep -A5 'keycloak database' deploy/postgres/backup.sh

# Backup script is already installed from postgres runbook Phase 4:
# /volume1/docker/study_tutor/backup.sh (runs nightly via DSM Task Scheduler)

# GATE KC-G1b: Verify backup.sh is scheduled
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST" \
  'ls -lh /volume1/docker/study_tutor/backup.sh'
# PASS: file exists, executable. FAIL: install from deploy/postgres/backup.sh

# Manual test (optional — will create real backups):
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST" \
  'sudo /volume1/docker/study_tutor/backup.sh'
# PASS: log shows both study_tutor and keycloak dumps succeed. FAIL: check backup.sh logs.
```

**Backup location:** `/volume1/docker/study_tutor/backups/keycloak_<YYYY-MM-DD>.dump` (custom format `-Fc`). Volume-level Hyper Backup covers `backups/` implicitly. Retention: **14 days** (shared `RETENTION_DAYS`).

**Rollback:** `pg_restore -U keycloak -d keycloak /volume1/docker/study_tutor/backups/keycloak_<date>.dump` (on the postgres container).

---

## Phase 6 — Network exposure & access hardening (tailnet-only)

Intent: **8443 reachable only from the trusted tailnet + LAN**, **never the internet**. No WAN port-forward. Mirrors the postgres 5434 three-layer posture.

For **whitestocks** (NAS LAN `172.30.1.0/24` on `eth0`; tailnet `100.64.0.0/10`, NAS = `100.92.74.2`; edge = HPE/Aruba **Instant On SG2505P** gateway; **DSM firewall currently OFF**) enforcement is three layers:

1. **Internet edge — Aruba Instant On gateway (the control that matters).** NAT blocks all unsolicited inbound by default. Instant On app / `portal.arubainstanton.com` → **Policies → Port Forwarding**: confirm **no** rule forwards any WAN port to `172.30.1.156:8443` — the deploy never requests one.

2. **Tailnet — Tailscale ACLs (the path clients actually use).** The issuer URL resolves to the **tailnet IP `100.92.74.2`**, so devices reach 8443 over Tailscale — governed by Tailscale ACLs, not the gateway. Scope it in the Tailscale admin **Access Controls**:
   ```json
   {
     "action": "accept",
     "src": ["tag:mobile-device", "tag:tutor-backend"],
     "dst": ["100.92.74.2:8443"]
   }
   ```

3. **LAN host-level — DSM firewall (optional defence-in-depth, currently off).** Only restricts which `172.30.1.0/24` hosts may reach 8443. **Caveat:** DSM's firewall governs the physical adapter; `tailscale0` traffic generally **bypasses** it, so rely on layer 2 for the tailnet. The admin console password is the LAN backstop.

**Do not** treat the DSM firewall as the primary control — layers 1 (Aruba) and 2 (Tailscale) are.

**Admin console access:** `https://whitestocks.tailebf801.ts.net:8443/admin` — tailnet-only, same posture. No WAN exposure.

---

## GATE KC-G1 — Validation (the pass condition for TASK-KC-006)

The gate confirms: (a) devices can sign in with no cert warning, (b) discovery doc serves over the pinned issuer, (c) NAS RAM has positive headroom.

```bash
# GATE KC-G1a: Device browser reaches realm sign-in with no cert warning
# From a device on the tailnet (phone, laptop):
# Navigate to: https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor/account
# PASS: Sign-in page loads, cert is valid (Let's Encrypt, no warning).
# FAIL: cert mismatch, self-signed warning, or connection refused → check Phase 1 cert or Phase 3 deploy.

# GATE KC-G1b: Discovery doc serves over pinned issuer
curl -s https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor/.well-known/openid-configuration \
  | jq -r '.issuer'
# PASS: prints exactly "https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor"
# FAIL: wrong issuer, 404, or cert error → check KC_HOSTNAME in .env or realm import.

# GATE KC-G1c: NAS RAM headroom (before/after)
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST" 'free -m'
# PASS: Available memory ≥ 2 GB (comfortable for Keycloak's 1-2 GB + postgres).
# FAIL: < 1 GB free → NAS RAM upgrade needed or reduce container limits.

# GATE KC-G1d: Test authentication (optional, requires provisioned user)
# Use study-tutor app or curl + AppAuth to obtain a token, verify claims include student_id
```

---

## Idempotency & re-run safety

- **Second run no-ops/fails cleanly:** `docker compose up -d` is idempotent (container recreates if needed). Realm import (`--import-realm`) is **non-overwriting** — runbook-created users (Lilymay, Alex) survive re-imports (ASSUM-003).
- **Already-bound resources:** Port 8443 already bound → compose recreates container. Keycloak DB already exists → init SQL exits with "already exists" (non-fatal). Cert already minted → `tailscale cert` refreshes if near expiry.
- **Cert renewal (~90 days):** Tailscale cert renews **unattended** before expiry. Check expiry with `openssl x509 -in <cert> -noout -dates`. If expired, re-run Phase 1 cert mint.

---

## Decision gates

| Gate | Test | PASS → | FAIL → |
|---|---|---|---|
| G0 | Batch SSH + `sudo -n docker` (reuse) | Phase 1 | postgres runbook Phase 0 (sudoers/DSM) |
| KC-G0a | Cert file + issuer name (Phase 1) | Phase 2 | re-mint cert, check tailscale CLI |
| KC-G0b | Keycloak DB + role exist (Phase 2) | Phase 3 | re-run init SQL, check postgres logs |
| KC-G1a | Container healthy (Phase 3) | Phase 4 | read logs, fix compose/env, re-run |
| KC-G1b | Backup.sh scheduled (Phase 5) | Phase 6 | install backup.sh, add to Task Scheduler |
| KC-G1 | Issuer reachable + RAM headroom (Phase 6) | Done | check cert, compose, or NAS RAM |

---

## What NOT to do

- Do **NOT** commit users or secrets to git — realm JSON defines structure only; users are **runbook-created** and stay in the database (deliberate PII posture).
- Do **NOT** expose 8443 to the internet — no WAN port-forward on the edge gateway (Phase 6). Tailnet-only access.
- Do **NOT** skip the nightly `pg_dump` of the `keycloak` database — realm/user state is **non-reindexable** (same class as learner data).
- Do **NOT** change the issuer URL after clients are configured — `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor` is **pinned** in client configs. Changing it breaks token validation.
- Do **NOT** run `docker compose down -v` — nukes the realm state. Rollback is `pg_restore` from the latest `keycloak_<date>.dump`.
- Do **NOT** edit compose on the NAS directly — the repo copy is canonical; change there, re-run Phase 3.
- Do **NOT** use `start-dev` mode or disable TLS in production — OIDC on devices requires https (AppAuth libraries reject http off-loopback).
- Do **NOT** reuse the postgres `study_tutor` role for Keycloak — the `keycloak` role is isolated (KC-D3); cross-project access is forbidden.

---

*This runbook documents the KC-G1 gate for [FEAT-AUTH-001](../history/feature-spec-feat-auth-001-keycloak-standup-on-the-nas-per-design-kc-d1-d-history.md). Execution is TASK-KC-006 (operator_handoff). Artifacts: [deploy/keycloak/](../../deploy/keycloak/) (compose, realm JSON, init SQL), [deploy/postgres/backup.sh](../../deploy/postgres/backup.sh) (extended for keycloak DB).*
