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

## 2. The one decision — where does the durable instance live?

The app only ever sees a **DSN**; the host is an operator choice. The runbook supports two targets:

| | **Target A — dedicated container on the NAS** (runbook default) | **Target B — docker-on-GB10** |
|---|---|---|
| Host | Synology NAS `whitestocks` (`whitestocks.tailebf801.ts.net`) | this GB10 |
| Network | GB10 tutor → NAS over Tailscale | localhost DSN (simplest path) |
| Backup | inherits NAS Hyper Backup + nightly `pg_dump` | **`pg_dump` must ship off-box** (→ NAS/Tailscale); GB10 is not a backup target |
| Deploy | SSH + `rsync` compose to NAS (reuses fleet-memory NAS prep; Phase 0 mostly done) | `docker compose up -d` locally on the GB10 |
| Best for | **real learner data** — a minor's non-reindexable state ([ADR-ARCH-015](../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md)) | fast dev unblock; the natural shape for the eventual **cloud** deploy (mobile handoff) |

**Recommendation:**
- If you want the durable instance in one shot → **Target A (NAS)**. It is the runbook default and the right posture for Lilymay's real state.
- If you want to unblock W1 development **right now** on the GB10 → **Target B** is fine as the dev instance, **but** the durable NAS instance (Target A) must exist **before W1's write-path is validated against real persistence** (build plan §5 W0). Don't ship real learner state to a GB10-only DB with no off-box backup.

Either way the app reads one env var: `STUDY_TUTOR_PG_DSN`.

---

## 3. Quickstart

### Target B (docker-on-GB10) — fastest unblock
```bash
cd deploy/postgres
cp .env.deploy.example .env.deploy && chmod 600 .env.deploy
openssl rand -base64 24                      # → paste into STUDY_TUTOR_PG_PASSWORD in .env.deploy
git check-ignore deploy/postgres/.env.deploy # GATE G1a: must echo the path (gitignored)

# runtime .env for compose (password + port), then up:
printf 'POSTGRES_PASSWORD=%s\nPG_PORT=5433\n' "$STUDY_TUTOR_PG_PASSWORD" > .env && chmod 600 .env
docker compose up -d

# GATE G2/G3/G4 — healthy, JSONB sane, DSN reachable:
docker ps --filter name=study_tutor_postgres --format '{{.Status}}'         # "Up ... (healthy)"
docker exec study_tutor_postgres psql -U study_tutor -d study_tutor -tAc "SELECT '{\"ok\":true}'::jsonb;"
psql "postgresql://study_tutor:$STUDY_TUTOR_PG_PASSWORD@localhost:5433/study_tutor" -c 'SELECT 1;'
```

### Target A (NAS) — durable, recommended
Follow the runbook **Phases 0 → 3** verbatim (SSH prep is mostly inherited from fleet-memory; gate **G0** proves it). The GB10 is the deploy host: `source .env.deploy`, `rsync` the compose to `${NAS_DOCKER_ROOT}`, render the NAS-side `.env`, `docker compose up -d` over SSH, then gates **G2–G6**.

---

## 4. Definition of Done (W0 = gates G0–G6)

| Gate | Proves | Scope |
|---|---|---|
| G0 | Batch SSH + `sudo -n docker` on the NAS | Target A only |
| G1 | `.env.deploy` complete, gitignored, `chmod 600` | both |
| G2 | container `Up (healthy)` | both |
| G3 | `pg_isready` + a JSONB `SELECT` (proves **no pgvector needed**) | both |
| G4 | `psql` over the **DSN on 5433** (the path the tutor backend uses) | both |
| G5 | `pgdata/PG_VERSION` = 16 on the backed-up volume | Target A (**STOP** if the bind mount is wrong) |
| G6 | reboot persistence (container auto-restarts, data intact) | when convenient |

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
- **Nightly `pg_dump` is REQUIRED** (Phase 4). Learner state is **not** reindexable — a volume snapshot alone is insufficient. On GB10 (Target B) the dump **must** ship off-box.
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

> Stand up the study-tutor StudentStore Postgres per `docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md` (W0 of the migration build plan). Target **[A: NAS `whitestocks` | B: docker-on-GB10]**. Objective: an empty `study_tutor` DB + role on port 5433, gates **G0–G6** green; **do not** run Alembic (that's W1). Then set `STUDY_TUTOR_PG_DSN` in the study-tutor `.env`. Constraints: JSONB only, no pgvector, nightly `pg_dump` off-box, never `down -v`.

---

## 8. Related documents

- [ADR-ARCH-023](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the decision (Accepted 2026-07-03); D1 (Postgres schema), D4 (no fleet coupling / independently deployable).
- [RUNBOOK-study-tutor-postgres-deploy.md](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) — **the** procedure; Targets A/B, phases 0–4, gates G0–G7.
- [migration scope + build plan](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) — §5 (waves), §9 (Step 2 = this W0, Step 3 = W1).
- [deploy/postgres/](../../deploy/postgres/) — compose + `.env.deploy.example`.
- [schema_reference.sql](../../src/study_tutor/knowledge/store/schema_reference.sql) — reference DDL (W1 Alembic encodes it).
- C4 [system-context.md](../architecture/system-context.md) / [container.md](../architecture/container.md) — the revised topology (Postgres in, FalkorDB/Gemini out).
