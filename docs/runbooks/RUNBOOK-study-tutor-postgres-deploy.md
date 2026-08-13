# RUNBOOK — study-tutor Postgres Deploy (StudentStore durable store)

**Date:** 2026-07-02
**Status:** Ready to execute. Phase 0 largely **reuses** the already-provisioned fleet-memory NAS prep; Phases 1–3 are new (a dedicated instance).
**Purpose:** Stand up a **study-tutor-dedicated** Postgres 16 as the durable StudentStore for [FEAT-SMP-001](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md), independently deployable from the agent fleet ([ADR-ARCH-023](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) D4).
**Scope:** The **durable learner-state instance only**. Hermetic CI/test DBs (ephemeral, per-test) are out of scope and must never point here.
**Related:** [ADR-ARCH-023](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md), [migration build plan §4/§6](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md); templates reused: `fleet-memory/docs/runbooks/RUNBOOK-nas-postgres-deploy.md` (the NAS prep this inherits) and `jarvis` ADR-ARCH-014 (the docker-on-GB10 alternative).

---

## 0. How this differs from the fleet-memory Postgres (read first)

| | fleet-memory PG | **study-tutor PG (this runbook)** |
|---|---|---|
| Instance | shared fleet store | **dedicated, own container/volume/DSN** (independent deploy — ADR-ARCH-023 D4) |
| Extensions | **pgvector** (embeddings) | **none** — JSONB only; embeddings/corpus stay on **ChromaDB** ([ADR-ARCH-022](../architecture/decisions/ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md)) |
| Data | reindexable-from-markdown | **real learner state — NOT reindexable** |
| Backup | *deferrable* (snapshot enough) | **nightly `pg_dump` REQUIRED from day one** (see Phase 4) |
| Host port | 5433 | **5434** (5432 = DSM's own internal Postgres, localhost-only; fleet-memory holds 5433) |
| Schema/DDL | — | created by **Alembic** (FEAT-SMP-001), not this runbook — this stands up an **empty DB + role** |

**Two supported targets** (pick one; the app only ever sees a DSN):

- **Target A — dedicated container on the NAS (recommended).** Reuses the already-provisioned fleet-memory NAS prep (SSH key, admin group, User Home, docker-sudoers, firewall), inherits Hyper Backup durability — the right posture for a minor's real learner data ([ADR-ARCH-015](../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md)) — and is reachable by the GB10 tutor backend over Tailscale.
- **Target B — docker-on-GB10** (jarvis ADR-ARCH-014 pattern). Co-located with the tutor runtime (localhost DSN, simplest network path), but the GB10 is **not** a backup target, so Phase 4's `pg_dump` must ship off-box (→ NAS/Tailscale). Also the natural shape for the eventual portable **cloud** deploy (mobile handoff): same compose, DSN is the only knob.

The blocks below are **Target A**. Target-B deltas are called out inline.

---

## 1. Credentials & secrets summary

| Item | Lives where | Notes |
|---|---|---|
| SSH **key** (`~/.ssh/fleet_memory_nas_ed25519`) | deploy host (GB10/Mac), agent | **Reuse** the existing NAS key — it authenticates the host to the NAS regardless of which container it deploys. (Target B: no SSH — deploy runs locally on the GB10.) |
| `deploy/postgres/.env.deploy` | deploy host only, `chmod 600`, gitignored | `NAS_HOST`, `NAS_USER`, `NAS_SSH_PORT`, `NAS_DOCKER_ROOT=/volume1/docker/study_tutor`, `PG_PORT=5434`, `STUDY_TUTOR_PG_PASSWORD` |
| `.env` next to compose on the NAS | NAS, `chmod 600`, rendered by deploy | `POSTGRES_PASSWORD` only (compose auto-loads) |
| sudoers entry | NAS `/etc/sudoers.d/fleet_memory_docker` | **Already in place** — NOPASSWD for the docker binary only. No new sudoers needed. |
| App DSN | study-tutor `.env` → `STUDY_TUTOR_PG_DSN` | `postgresql://study_tutor:<pw>@<host>:5434/study_tutor` |

`deploy/postgres/.env.deploy.example` (committed):

```bash
NAS_HOST=whitestocks.tailebf801.ts.net     # Tailscale MagicDNS (same NAS as fleet-memory)
NAS_USER=RichardWoollcott                  # DSM account NAME, administrators group
NAS_SSH_PORT=22
NAS_DOCKER_ROOT=/volume1/docker/study_tutor
PG_PORT=5434                               # 5432=DSM internal PG (localhost), 5433=fleet-memory; study-tutor owns 5434
STUDY_TUTOR_PG_PASSWORD=                   # generate: openssl rand -hex 24  (hex → URL-safe in the DSN)
```

---

## 2. `deploy/postgres/docker-compose.yml` (canonical; productized during FEAT-SMP-001)

```yaml
services:
  study_tutor_postgres:
    image: postgres:16
    container_name: study_tutor_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: study_tutor
      POSTGRES_DB: study_tutor
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set in .env}
    ports:
      - "${PG_PORT:-5434}:5432"
    volumes:
      - ./pgdata:/var/lib/postgresql/data        # bind mount → lands on /volume1 (backed up)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U study_tutor -d study_tutor"]
      interval: 10s
      timeout: 5s
      retries: 5
```

_No `vector` extension, no init SQL — Alembic (FEAT-SMP-001) owns the schema._

---

## Phase 0 — NAS prep (mostly DONE — inherited from fleet-memory)

Already provisioned by the fleet-memory NAS runbook and **not repeated**: SSH key, `RichardWoollcott` in administrators, User Home service, `/etc/sudoers.d/fleet_memory_docker` (docker NOPASSWD). **Only new:**

```bash
# on the NAS (interactive; DSM password OK here) — create the dedicated data root
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -p 22 "$NAS_USER@$NAS_HOST" \
  'mkdir -p /volume1/docker/study_tutor/pgdata'
```
Network exposure / access scoping is deployment-specific — see **Phase 5**. For this deployment the primary controls are the **Aruba Instant On** edge gateway (no WAN port-forward for 5434) and **Tailscale ACLs**; the DSM firewall is optional defence-in-depth and is **currently off** (do not treat it as the enforcement point here).

**GATE G0 (from the deploy host) — reuse the existing proof:**
```bash
ssh -i ~/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p 22 "$NAS_USER@$NAS_HOST" \
  'echo SSH_OK && sudo -n /usr/local/bin/docker version --format "DOCKER_OK {{.Server.Version}}"'
# PASS: SSH_OK + DOCKER_OK <ver>, no password prompt. FAIL → see fleet-memory runbook Phase 0 (DSM may have wiped sudoers).
```
_Target B: skip Phase 0 entirely — you deploy locally on the GB10 (`docker compose` already runs there for the fleet)._

## Phase 1 — Local env (deploy host)

```bash
cd ~/Projects/appmilla_github/study-tutor/deploy/postgres
cp .env.deploy.example .env.deploy && chmod 600 .env.deploy
openssl rand -hex 24                                 # → STUDY_TUTOR_PG_PASSWORD (hex = URL-safe; base64 may emit / or + that break URL-form DSNs)
git check-ignore deploy/postgres/.env.deploy         # GATE G1a PASS: echoes the path
grep -c '=$' .env.deploy                             # GATE G1 PASS: prints 0 (no empty values)
```

## Phase 2 — Deploy (idempotent; becomes `deploy/postgres/deploy.sh`)

```bash
set -euo pipefail
source .env.deploy
SSH="ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p ${NAS_SSH_PORT} ${NAS_USER}@${NAS_HOST}"

# 2a. Sync compose (repo is canonical; NAS copy is an artifact)
rsync -avz -e "ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -p ${NAS_SSH_PORT}" \
  --exclude '.env.deploy*' docker-compose.yml ${NAS_USER}@${NAS_HOST}:${NAS_DOCKER_ROOT}/

# 2b. Render runtime .env on the NAS (password + port), lock it down
$SSH "printf 'POSTGRES_PASSWORD=%s\nPG_PORT=%s\n' '${STUDY_TUTOR_PG_PASSWORD}' '${PG_PORT}' > ${NAS_DOCKER_ROOT}/.env && chmod 600 ${NAS_DOCKER_ROOT}/.env"

# 2c. Up
$SSH "cd ${NAS_DOCKER_ROOT} && sudo -n /usr/local/bin/docker compose up -d"

# GATE G2 — container healthy
$SSH "sudo -n /usr/local/bin/docker ps --filter name=study_tutor_postgres --format '{{.Status}}'"
# PASS: starts with "Up" (and "(healthy)" after ~30s). FAIL: docker logs study_tutor_postgres, fix, re-run (idempotent).
```
_Target B: drop the `$SSH` wrapper and `rsync` — run `docker compose up -d` in `deploy/postgres/` on the GB10._

## Phase 3 — Validation gates (from the deploy host)

```bash
# GATE G3 — server ready + JSONB sane (NO pgvector)
$SSH "sudo -n /usr/local/bin/docker exec study_tutor_postgres pg_isready -U study_tutor -d study_tutor"
$SSH "sudo -n /usr/local/bin/docker exec study_tutor_postgres psql -U study_tutor -d study_tutor -tAc \"SELECT '{\\\"ok\\\":true}'::jsonb;\""
# PASS: accepting connections; prints {"ok": true}

# GATE G4 — the network path the tutor backend will actually use
psql "postgresql://study_tutor:${STUDY_TUTOR_PG_PASSWORD}@${NAS_HOST}:${PG_PORT}/study_tutor" -c 'SELECT 1;'
# PASS: returns 1. FAIL: DSM firewall (5434) or port mapping.

# GATE G5 — data on the backed-up volume, not container-internal
$SSH "sudo -n /usr/local/bin/docker inspect -f 'MOUNT: {{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{end}}' study_tutor_postgres"
$SSH "sudo -n /usr/local/bin/docker exec study_tutor_postgres cat /var/lib/postgresql/data/PG_VERSION"
# PASS: MOUNT is a `bind` from /volume1/docker/study_tutor/pgdata AND PG_VERSION prints 16. FAIL: bind mount wrong — STOP, do not run migrations.
# NOTE: read PG_VERSION *via the container* — the host pgdata is mode 0700 owned by the container's postgres uid, so a plain `cat` as the SSH user returns "Permission denied" (that error alone still confirms the bind is populated).

# GATE G7 — schema-init: Alembic head applies (run from the study-tutor app env, FEAT-SMP-001)
STUDY_TUTOR_PG_DSN="postgresql://study_tutor:${STUDY_TUTOR_PG_PASSWORD}@${NAS_HOST}:${PG_PORT}/study_tutor" \
  .venv/bin/alembic upgrade head
# PASS: migrations apply clean; \dt shows student/topic_confidence/achievement/quest/session tables.
```

**GATE G6 — reboot persistence (once, convenient moment):** reboot the NAS from DSM; re-run G2+G4. PASS: container auto-restarted and data intact.

## Phase 4 — Ops

- **Backup (REQUIRED — this is the key divergence from fleet-memory).** The learner state is **not** reindexable, so a crash-consistent snapshot alone is insufficient:
  1. Confirm `/volume1/docker/study_tutor` is in the Hyper Backup / Snapshot schedule (volume-level).
     > **Dated outcome (2026-08-13, Rich in the DSM console):** this confirm step, run for the
     > first time, FAILED — **Hyper Backup is not installed** (nor Snapshot Replication, nor any
     > cloud backup). No volume-level schedule exists; the nightly `pg_dump` (14-day retention)
     > is the ONLY backup layer. Gap ledgered in `known-issues.md`; ADR-ARCH-028/033 carry
     > dated corrections.
  2. **Add a nightly logical dump** into the backup share. Productized as [`deploy/postgres/backup.sh`](../../deploy/postgres/backup.sh) (atomic temp-then-rename, `PGDMP`-magic validity check, 14-day retention, logs to `backups/backup.log`, non-zero exit on failure); installed at `/volume1/docker/study_tutor/backup.sh` and scheduled nightly via **DSM Task Scheduler** (user `root`, e.g. daily 03:15 → `bash /volume1/docker/study_tutor/backup.sh`). The raw command it wraps:
     ```bash
     # NAS cron (Control Panel → Task Scheduler), nightly:
     sudo -n /usr/local/bin/docker exec study_tutor_postgres \
       pg_dump -U study_tutor -d study_tutor -Fc \
       > /volume1/docker/study_tutor/backups/study_tutor_$(date +\%F).dump
     # keep 14 days; the backups/ dir rides the same Hyper Backup share
     ```
  Target B (GB10): the dump must ship **off-box** — write it to a Tailscale/NAS path, never only to GB10-local disk.
- **Upgrade:** bump the image tag in the repo compose → re-run Phase 2 (idempotent). Postgres **major** upgrades need dump/restore — a separate, deliberate task.
- **Rollback:** `$SSH "cd ${NAS_DOCKER_ROOT} && sudo -n /usr/local/bin/docker compose down"` (**never `-v`**), restore `pgdata/` from snapshot **or** `pg_restore` the latest dump, `compose up -d`.

## Phase 5 — Network exposure & access hardening (this deployment)

Intent: 5434 reachable only from the trusted LAN + the tutor backend, **never the internet**. How that maps depends on topology. For **whitestocks** (NAS LAN `172.30.1.0/24` on `eth0`; tailnet `100.64.0.0/10`, NAS = `100.92.74.2`; edge = HPE/Aruba **Instant On SG2505P** gateway; **DSM firewall currently OFF**) enforcement is three layers, in priority order:

1. **Internet edge — Aruba Instant On gateway (the control that matters).** NAT blocks all unsolicited inbound by default, so 5434 is off the internet unless a port-forward maps it. Instant On app / `portal.arubainstanton.com` → **Policies → Port Forwarding**: confirm **no** rule forwards any WAN port to `172.30.1.156` (esp. 5434) — the deploy never requests one. Instant On has no intra-LAN host ACLs, so it cannot scope which LAN devices reach 5434.
2. **Tailnet — Tailscale ACLs (the path the app actually uses).** The DSN host resolves to the **tailnet IP `100.92.74.2`**, so the tutor backend reaches 5434 over Tailscale — governed by Tailscale ACLs, not the gateway or (reliably) the DSM firewall. Scope it in the Tailscale admin **Access Controls**: `{ "action": "accept", "src": ["tag:tutor-backend"], "dst": ["100.92.74.2:5434"] }`.
3. **LAN host-level — DSM firewall (optional defence-in-depth, currently off).** Only restricts which `172.30.1.0/24` hosts may reach 5434. Enabling it default-denies all non-allowlisted traffic (**lockout risk**) — only turn on with a full allowlist (DSM 5000/5001, SSH 22, SMB, then allow TCP 5434 from `172.30.1.0/24` + `100.64.0.0/10`, deny 5434 otherwise, placed above the profile's default-deny). **Caveat:** DSM's firewall governs the physical adapter; `tailscale0` traffic generally **bypasses** it, so rely on layer 2 for the tailnet. The `study_tutor` role password is the LAN backstop, so this layer is optional.

**Do not** treat the DSM firewall as the primary control on this deployment — layers 1 (Aruba) and 2 (Tailscale) are.

## Decision gates

| Gate | Test | PASS → | FAIL → |
|---|---|---|---|
| G0 | Batch SSH + `sudo -n docker` | Phase 1 | fleet-memory runbook Phase 0 (sudoers/DSM) |
| G1 | `.env.deploy` complete + gitignored + 600 | Phase 2 | fill/ignore/chmod |
| G2 | Container Up (healthy) | G3 | read logs, fix, re-run |
| G3 | pg_isready + JSONB select | G4 | image/init issue |
| G4 | psql over the DSN on 5434 | G5 | firewall/port |
| G5 | `pgdata/PG_VERSION` = 16 on /volume1 | G7 (G6 when convenient) | **STOP** — bind mount wrong |
| G7 | `alembic upgrade head` applies | Done | migration bug (FEAT-SMP-001) |

## What NOT to do

- Do **NOT** share fleet-memory's DB, volume, or port — study-tutor is an independent deploy (ADR-ARCH-023 D4). Own container, own `/volume1/docker/study_tutor`, own **5434**.
- Do **NOT** skip the nightly `pg_dump` — this store holds **non-reindexable** learner state (the exact opposite of fleet-memory's posture).
- Do **NOT** install pgvector or any extension — keep the surface minimal; semantic recall reuses ChromaDB, not this DB.
- Do **NOT** put table DDL in this runbook — **Alembic** (FEAT-SMP-001) owns the schema; this runbook stands up an empty DB + role only.
- Do **NOT** expose 5434 to the internet — no WAN port-forward for it on the edge gateway (Phase 5) — and do **NOT** point any CI/hermetic test at this instance.
- Do **NOT** run `docker compose down -v` (nukes the data bind); rollback is snapshot/dump restore.
- Do **NOT** edit compose on the NAS directly — the repo copy is canonical; change there, re-run Phase 2.
- Do **NOT** put an SSH password in any file or reuse `sshpass` — key auth + the existing scoped NOPASSWD only.

---

*Productized during [FEAT-SMP-001](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) as `deploy/postgres/deploy.sh` + `smoke.sh` with these gates inline. This runbook remains the operator reference.*
</content>
