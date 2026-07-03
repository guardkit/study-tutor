# W0 — Stand up the study-tutor Postgres (StudentStore) — GB10 session opener

**Status:** Ready to execute. **G-ADR is done** (ADR-ARCH-023 ratified → Accepted, 2026-07-03); W0 is the next action.
**Date:** 2026-07-03.
**For:** a Claude Code session **on the GB10** (`promaxgb10`).
**Objective:** Provision a **study-tutor-dedicated Postgres 16** as the durable StudentStore — an **empty DB + role on port 5433** — to unblock the W1 build. **This does not create any tables** (Alembic owns the schema in W1).
**Authoritative procedure:** [RUNBOOK-study-tutor-postgres-deploy.md](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) — follow it for the exact blocks and gates. This doc is orientation + the one decision to make.

---

## 0. Before you start — pull the repo

The GB10 checkout must include the ratified ADR-023 and the reconciled architecture. From the study-tutor repo root on the GB10:

```bash
git pull origin main          # must include commit a9449f8 (ADR-ARCH-023 → Accepted) or later
git log --oneline -3          # confirm you see the G-ADR ratification commit
```

> **If `git pull` shows nothing new:** the commits may not be pushed yet. Ask the operator to push `main` from the Mac (this handoff was authored there).

---

## 1. TL;DR

[ADR-ARCH-023](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) replaced the Graphiti/FalkorDB student model with a **study-tutor-owned Postgres (JSONB)** store, **independently deployable** from the agent fleet (D4). W0 stands that store up. Everything for W0 already exists in the repo:

- [deploy/postgres/docker-compose.yml](../../deploy/postgres/docker-compose.yml) — Postgres 16, port 5433, JSONB, **no pgvector**, `pgdata` bind mount, healthcheck.
- [deploy/postgres/.env.deploy.example](../../deploy/postgres/.env.deploy.example) — the deploy-host secrets template.
- [RUNBOOK-study-tutor-postgres-deploy.md](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) — phases 0–4, gates G0–G7, "what NOT to do".
- [src/study_tutor/knowledge/store/schema_reference.sql](../../src/study_tutor/knowledge/store/schema_reference.sql) — **reference-only** DDL (the shape W1's Alembic migration encodes; do **not** apply by hand).

**W0 produces:** an empty `study_tutor` database + role, reachable on `5433`, on a backed-up volume. **W0 does NOT:** create tables, install extensions, or touch application code.

---

## 2. Where it runs — the NAS (`whitestocks`)

The store lives in a **dedicated Postgres container on the Synology NAS** `whitestocks` (`whitestocks.tailebf801.ts.net`), reached by the GB10 tutor backend over Tailscale. This is the right home for real learner data: the NAS is always-on, already has Hyper Backup, and satisfies the on-device-residency posture for a minor's non-reindexable state ([ADR-ARCH-015](../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md)).

The **GB10 is the deploy host** — you run the deploy from the GB10, which `rsync`s the compose to the NAS and brings the container up over SSH. This reuses the existing fleet-memory NAS prep (SSH key, administrators group, docker-sudoers), so Phase 0 is mostly done. The app itself only ever reads one env var: `STUDY_TUTOR_PG_DSN` — the host is invisible to the code.

> The [runbook](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) also documents a *Target B* (docker-on-GB10) for a future portable/cloud deploy — **ignore it for W0**; we're standing up the durable NAS instance directly.

---

## 3. Quickstart (run from the GB10; deploys to the NAS)

The [runbook](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) Phases 0–3 are authoritative — this is the condensed path. Run from the study-tutor repo root on the GB10.

```bash
cd deploy/postgres
cp .env.deploy.example .env.deploy && chmod 600 .env.deploy
openssl rand -base64 24                        # → paste into STUDY_TUTOR_PG_PASSWORD in .env.deploy
git check-ignore deploy/postgres/.env.deploy   # GATE G1a: must echo the path (gitignored)
grep -c '=$' .env.deploy                        # GATE G1: prints 0 (no empty values)
source .env.deploy
SSH="ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -o BatchMode=yes -p ${NAS_SSH_PORT} ${NAS_USER}@${NAS_HOST}"

# GATE G0 — reuse the fleet-memory NAS proof (SSH + passwordless docker), then the one new prep step:
$SSH 'echo SSH_OK && sudo -n /usr/local/bin/docker version --format "DOCKER_OK {{.Server.Version}}"'
$SSH "mkdir -p ${NAS_DOCKER_ROOT}/pgdata"
# DSM firewall (Control Panel → Security → Firewall): allow TCP 5433 from LAN + 100.64.0.0/10 (tailnet), deny else.

# Phase 2 — deploy: sync compose, render the NAS-side .env, bring it up
rsync -avz -e "ssh -i $HOME/.ssh/fleet_memory_nas_ed25519 -p ${NAS_SSH_PORT}" \
  --exclude '.env.deploy*' docker-compose.yml ${NAS_USER}@${NAS_HOST}:${NAS_DOCKER_ROOT}/
$SSH "printf 'POSTGRES_PASSWORD=%s\nPG_PORT=%s\n' '${STUDY_TUTOR_PG_PASSWORD}' '${PG_PORT}' > ${NAS_DOCKER_ROOT}/.env && chmod 600 ${NAS_DOCKER_ROOT}/.env"
$SSH "cd ${NAS_DOCKER_ROOT} && sudo -n /usr/local/bin/docker compose up -d"

# Phase 3 — gates G2–G5:
$SSH "sudo -n /usr/local/bin/docker ps --filter name=study_tutor_postgres --format '{{.Status}}'"   # G2: Up (healthy)
$SSH "sudo -n /usr/local/bin/docker exec study_tutor_postgres psql -U study_tutor -d study_tutor -tAc \"SELECT '{\\\"ok\\\":true}'::jsonb;\""  # G3
psql "postgresql://study_tutor:${STUDY_TUTOR_PG_PASSWORD}@${NAS_HOST}:${PG_PORT}/study_tutor" -c 'SELECT 1;'   # G4: DSN reachable
$SSH "cat ${NAS_DOCKER_ROOT}/pgdata/PG_VERSION"    # G5: prints 16 (data on the backed-up /volume1)
```

---

## 4. Definition of Done (W0 = gates G0–G6)

| Gate | Proves |
|---|---|
| G0 | Batch SSH + `sudo -n docker` on the NAS (reuses fleet-memory prep) |
| G1 | `.env.deploy` complete, gitignored, `chmod 600` |
| G2 | container `Up (healthy)` on the NAS |
| G3 | `pg_isready` + a JSONB `SELECT` (proves **no pgvector needed**) |
| G4 | `psql` over the **DSN on 5433** (the path the tutor backend uses) |
| G5 | `pgdata/PG_VERSION` = 16 on the backed-up `/volume1` (**STOP** if the bind mount is wrong) |
| G6 | reboot persistence — reboot the NAS from DSM, container auto-restarts, data intact (when convenient) |

⚠️ **G7 (`alembic upgrade head`) is NOT part of W0.** It is the schema-init gate and it belongs to **W1 / FEAT-SMP-001** — the Alembic migrations do not exist yet. W0 stops at an empty DB + role.

**Then wire the app:** put the DSN in the study-tutor `.env`:
```
STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<password>@<host>:5433/study_tutor
#   host = localhost (Target B) or whitestocks.tailebf801.ts.net (Target A)
```
(The `.env.example` swap — replacing the old Graphiti/FalkorDB config with `STUDY_TUTOR_PG_DSN` — is part of the W3 config swap; not required to finish W0.)

---

## 5. Hard constraints (from the runbook's "what NOT to do")

- **No pgvector, no extensions.** JSONB only; semantic recall reuses ChromaDB ([ADR-ARCH-022](../architecture/decisions/ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md)), not this DB.
- **Nightly `pg_dump` is REQUIRED** (Phase 4). Learner state is **not** reindexable — a volume snapshot alone is insufficient. Schedule it via DSM Task Scheduler into the backed-up `backups/` dir (runbook Phase 4).
- **Own everything** — own container, own volume (`/volume1/docker/study_tutor` on the NAS), own port **5433**. Never share fleet-memory's DB/volume/port (5432).
- **No table DDL by hand** — Alembic (W1) owns the schema; `schema_reference.sql` is reference-only.
- **Never `docker compose down -v`** (nukes the data bind). Rollback is snapshot / `pg_restore`.
- **Don't expose 5433 beyond LAN + tailnet**, and never point CI/hermetic tests at this instance.

---

## 6. After W0 → W1 (FEAT-SMP-001)

With the empty DB reachable on 5433, W1 is the first build. From the build plan [§6](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md):

```bash
/feature-spec "Student Model Postgres Store — JSONB schema + Alembic migrations, StudentStore port + Postgres adapter, synchronous transactional session-end write (replaces GraphitiWriteHelper F1/F2/F3), reusing the persistence-agnostic Pydantic entities" \
  --context src/study_tutor/knowledge/store/port.py \
  --context src/study_tutor/knowledge/store/entities.py \
  --context src/study_tutor/knowledge/store/postgres.py \
  --context src/study_tutor/knowledge/store/schema_reference.sql \
  --context docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md \
  --context docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md \
  --context docs/gamification/design.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md \
  --context docs/design/events-schema.yaml
```
W1 fills the `PostgresStudentStore` bodies (today `NotImplementedError`), writes the **first Alembic migration** (encoding `schema_reference.sql`), and adds `sqlalchemy[asyncio]`/`asyncpg`/`alembic` to `pyproject.toml`. W1's gate is runbook **G7**.

> **Note:** FEAT-SMP-003 (session persistence) is gated by **G-CON** (`/design-refine` on the cross-device session contract) — still pending, separate track. FEAT-SMP-001 (W1) and FEAT-SMP-002 (reads) are **not** blocked by G-CON.

---

## 7. Suggested opener for the GB10 session

> Stand up the study-tutor StudentStore Postgres per `docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md` (W0 of the migration build plan) — a **dedicated container on the NAS `whitestocks`**, deployed from this GB10 over SSH. Objective: an empty `study_tutor` DB + role on port 5433, gates **G0–G6** green; **do not** run Alembic (that's W1). Then set `STUDY_TUTOR_PG_DSN` in the study-tutor `.env`. Constraints: JSONB only, no pgvector, nightly `pg_dump` via DSM, never `down -v`.

---

## 8. Related documents

- [ADR-ARCH-023](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the decision (Accepted 2026-07-03); D1 (Postgres schema), D4 (no fleet coupling / independently deployable).
- [RUNBOOK-study-tutor-postgres-deploy.md](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) — **the** procedure; Targets A/B, phases 0–4, gates G0–G7.
- [migration scope + build plan](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) — §5 (waves), §9 (Step 2 = this W0, Step 3 = W1).
- [deploy/postgres/](../../deploy/postgres/) — compose + `.env.deploy.example`.
- [schema_reference.sql](../../src/study_tutor/knowledge/store/schema_reference.sql) — reference DDL (W1 Alembic encodes it).
- C4 [system-context.md](../architecture/system-context.md) / [container.md](../architecture/container.md) — the revised topology (Postgres in, FalkorDB/Gemini out).
