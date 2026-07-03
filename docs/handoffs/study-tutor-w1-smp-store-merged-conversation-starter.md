# Study-tutor — W0 + W1 (Postgres StudentStore) DONE → FEAT-SMP-002 (reads) next

**Status:** W0 (durable Postgres) live; **W1 / FEAT-SMP-001 (write path + migration) built, verified, and merged to `main`.** Next build is **FEAT-SMP-002 (the read path)**.
**Date:** 2026-07-03. **Host:** this work ran on the **GB10** (`promaxgb10-41b1`, Linux/aarch64). Repo root: `~/Projects/appmilla_github/study-tutor`.
**`main` HEAD:** `975547a` (in sync with `origin/main`). This doc is the orientation + condensed steps for the next session.

---

## 0. Where we are in one glance

```
ADR-ARCH-023 (Graphiti/FalkorDB → study-tutor-owned Postgres JSONB)   ✅ ratified
W0  stand up durable Postgres on NAS whitestocks:5434                 ✅ DONE (gates G0–G5)
W1  FEAT-SMP-001: schema+migration + write path (ping/F1/F2/F3)       ✅ BUILT + MERGED (efe4fb0)
W2  FEAT-SMP-002: read path (get_student_state / topic_confidences / misconceptions)  ⬅️ NEXT
W3  FEAT-SMP-003: session CRUD (create/append/list/end)              ⛔ gated by G-CON (/design-refine, pending)
W3' config swap (.env.example: drop Graphiti/FalkorDB → STUDY_TUTOR_PG_DSN)  ⬜ deferred
```

## 1. TL;DR

The study-tutor learner store is now **Postgres, not Graphiti**. A durable instance runs on the NAS (`whitestocks:5434`), and the **write path is implemented and on `main`**: the first Alembic migration (schema), `ping`, and the three synchronous transactional writes that replaced `GraphitiWriteHelper` F1/F2/F3. **Reads and session CRUD are still `NotImplementedError`** and are the next two waves. Full test suite is green (`1165 passed`) and CI-safe.

## 2. What shipped this session (commits, newest first)

| Commit | What |
|---|---|
| `975547a` | `docs(retros)`: two AutoBuild failure retros (see §7) |
| `efe4fb0` | **`feat(smp)`: FEAT-SMP-001 W1 write path + migration** (25 files, +4,977) — the feature |
| `64e3d92` | `plan(smp)`: `/feature-plan` — 7 tasks / 5 waves + `.guardkit/features/FEAT-SMP-001.yaml` + 28 BDD scenarios `@task:`-tagged |
| `c7dfaa9` | `test`: fixed 10 **pre-existing** unit-test failures (API drift + fragile assertions; all test-only) |
| `56f4732` | `feat(smp)`: `/feature-spec` 28-scenario BDD spec + **resolved 2 conflicts** (band thresholds; xp_awarded) |
| `8784a8a` | `docs(w0)`: corrected the Postgres port **5433 → 5434** across the docs |

## 3. StudentStore state — what's implemented vs pending

`src/study_tutor/knowledge/store/postgres.py` (the `PostgresStudentStore` adapter):

| Method | Status | Wave |
|---|---|---|
| `ping` | ✅ implemented | W1 |
| `record_session_completion` (session-end, one txn, idempotent on `session_id`, atomic) | ✅ implemented | W1 |
| `record_misconception` (F1, append-only, 500-char + ctrl-char hygiene, no injection reject) | ✅ implemented | W1 |
| `apply_confidence_update` (F2, band via `confidence_band_for` 40/60/80) | ✅ implemented | W1 |
| `get_student_state` / `get_topic_confidences` / `get_recent_misconceptions` | ⛔ `NotImplementedError` | **W2 / SMP-002** |
| `create_session` / `get_session` / `list_sessions` / `append_turn` / `get_turns` / `end_session` | ⛔ `NotImplementedError` | W3 / SMP-003 (gated) |

New code from W1: `alembic.ini` + `alembic/` (async `env.py` + the initial migration `..._initial_studentstore_schema.py`), `src/study_tutor/knowledge/store/{db.py, wiring.py}`, filled `postgres.py`. Deps added to `pyproject.toml`: `sqlalchemy[asyncio]`, `asyncpg`, `alembic` (already synced into the repo `.venv`).

The read helpers already exist and are wired to the port: `src/study_tutor/knowledge/store/reads.py` (`get_student_state`, `load_planner_inputs`) — they call the store and degrade to empty on failure. **SMP-002 fills the adapter's read methods behind them.** `provider.py` is the DI seam (`set_student_store`).

## 4. The durable store (W0) — running instance + OUTSTANDING manual items

- **Instance:** dedicated Postgres 16 container `study_tutor_postgres` on the Synology NAS **`whitestocks`** (`whitestocks.tailebf801.ts.net`, tailnet `100.92.74.2`), host port **5434**, bind mount `/volume1/docker/study_tutor/pgdata` (backed up). Deployed from the GB10 over SSH (key `~/.ssh/fleet_memory_nas_ed25519`).
- **Port note (important):** the original docs said 5433; **reality is 5432 = DSM's own internal Postgres (localhost), 5433 = fleet-memory, 5434 = study-tutor.** All docs corrected in `8784a8a`. Never reuse fleet-memory's port/volume/DB.
- **App wiring:** `.env` (repo root, gitignored) has `STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<pw>@whitestocks.tailebf801.ts.net:5434/study_tutor`.
- **Gates G0–G5 green.** ⬜ **Still outstanding (operator, manual):**
  - **Nightly `pg_dump` — REQUIRED** (learner state is non-reindexable). Schedule via DSM Task Scheduler into `/volume1/docker/study_tutor/backups/` (runbook Phase 4). **Not yet done.**
  - **DSM firewall:** confirm/add a rule scoping TCP **5434** to LAN + `100.64.0.0/10` (tailnet) only. (It was reachable over tailnet during W0, but confirm the posture.)
  - **G6 reboot-persistence check** — reboot the NAS from DSM, confirm the container auto-restarts + data intact (when convenient).
- Authoritative procedure: [`docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md`](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md).

## 5. How to run / test locally (⚠️ never point tests at the NAS)

The suite is **CI-safe**: DB-backed tests **skip** when `STUDY_TUTOR_PG_DSN` is unset. To actually run them, point that var at an **ephemeral throwaway Postgres**, never the durable NAS instance (runbook scope rule).

```bash
# throwaway PG on a NON-5434 port (5432 is taken locally by finproxy-postgres on the GB10)
docker run -d --name smp_test_pg -e POSTGRES_USER=study_tutor -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=study_tutor -p 5455:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:testpass@localhost:5455/study_tutor"

.venv/bin/python -m pytest tests/ -q          # full suite (with DB tests live)
.venv/bin/python -m pytest tests/unit -q      # fast, no PG needed (DB tests skip)
.venv/bin/alembic upgrade head                # gate G7 against the ephemeral DB
docker rm -f smp_test_pg                       # tear down when done
```

**Baseline numbers:** full suite `1165 passed`; `tests/unit` `1029 passed` (no PG). Only failures anywhere are **3 pre-existing** `tests/integration/test_nats_smoke.py` cases (NATS command-alias resolution — fail on `main` too, unrelated to SMP). See §9.

## 6. NEXT: FEAT-SMP-002 (the read path)

Fills the adapter's three read methods (`get_student_state`, `get_topic_confidences`, `get_recent_misconceptions`) against the W1 schema, behind the existing `reads.py` helpers (which repoint `queries.py`'s graphiti reads and preserve graceful-degradation). **Not gated by G-CON.** Suggested kickoff:

```bash
/feature-spec "Student Model Postgres Store reads (FEAT-SMP-002) — implement get_student_state / get_topic_confidences / get_recent_misconceptions on PostgresStudentStore over the W1 schema, behind knowledge.store.reads, preserving the graceful-degradation contract (empty StudentState on unavailability); then repoint queries.py reads and delete the Graphiti read copies" \
  --context src/study_tutor/knowledge/store/port.py \
  --context src/study_tutor/knowledge/store/postgres.py \
  --context src/study_tutor/knowledge/store/reads.py \
  --context src/study_tutor/knowledge/store/entities.py \
  --context src/study_tutor/knowledge/store/schema_reference.sql \
  --context src/study_tutor/knowledge/queries.py \
  --context docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md
```
Then `/feature-plan` → (optionally) `/feature-build`. **FEAT-SMP-003** (session CRUD — the 6 `create/get/list/append/get_turns/end` methods) is **gated by G-CON** (`/design-refine` on the cross-device session contract, still pending) — don't start it until G-CON clears.

## 7. AutoBuild playbook (READ THIS before re-running `guardkit autobuild`)

W1 was built with `GUARDKIT_HARNESS=sdk guardkit autobuild feature FEAT-SMP-001` (SDK harness auths via the bundled Claude Code CLI — **no `ANTHROPIC_API_KEY` needed**). It took **3 runs** (~2.5h) because of two failure classes, both now written up in [`docs/retros/`](../retros/):

1. **[Parallel-wave worktree pollution](../retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md).** Tasks in the same wave run **in parallel in ONE shared worktree**; store tasks editing overlapping modules collide → `context_pollution_stall`. **Fix: serialize `orchestration.parallel_groups` in the feature YAML to one-task-per-wave** (there is no `--max-parallel` flag). Only parallelise tasks that touch disjoint files.
2. **[Self-defeating boundary tests](../retros/2026-07-03-autobuild-self-defeating-boundary-tests.md).** Players write tests asserting a *transient* state (e.g. "write methods raise `NotImplementedError`", "alembic `versions/` empty") that a **later task correctly invalidates**. Locally valid → Coach approves → detonates in composition. **Fix: scope boundary tests to real invariants; run the full-feature suite before merge.**

**Operational checklist for a store-feature autobuild:**
- Serialize the waves in the YAML.
- `export STUDY_TUTOR_PG_DSN=<ephemeral PG>` before launching so the Coach's DB tests run (pre-pull `postgres:16`).
- After it finishes, **independently verify** the full `pytest tests/` (Coach per-task green ≠ composition green), then **squash-merge** to `main` (checkout only the code paths — `alembic*`, `pyproject.toml`, `uv.lock`, `src/.../store/*`, `tests/` — NOT `.guardkit/`, `.claude/`, `tasks/` churn), and `git worktree remove` + delete the branch. `guardkit autobuild complete` refuses unless the YAML task statuses say completed (needs `--force`).

## 8. Resolved decisions to remember (don't re-litigate)

- **Confidence bands = 40/60/80** (struggling <40, developing 40–59, secure 60–79, mastered 80–100). `confidence_band_for` was corrected from 40/70/90 — evidence: hackathon plan §5.2 awards Mastery at **80%** (and its worked example "76% → one session → Macbeth Master"). This gates mastery achievements.
- **`session.xp_awarded`** column added to `schema_reference.sql` (per-session XP home; cumulative `total_xp`/`level`/`streak` on `student` are a **Phase 2** gamification-engine concern, not W1).
- **3 low-confidence assumptions** the build honoured (see `features/student-model-postgres-store/*_assumptions.yaml`): unknown-learner write **rejected** (FK, ASSUM-003); `record_misconception` **append-only, no dedup** (ASSUM-006); prompt-injection rejection **dropped** (no LLM in the Postgres path, ASSUM-005).

## 9. Known issues / risks

- **3 pre-existing NATS failures:** `tests/integration/test_nats_smoke.py::TestSmokeFourCommands` — `ResultPayload.command was 'tutor_start_session', expected canonical 'start_session' after alias resolution`. Fails on `main` too, **unrelated to SMP** (NATS command-alias routing). Worth a separate look sometime.
- The durable-store **backup is not yet scheduled** (§4) — the single most important operator follow-up, since learner state is not reindexable.

## 10. Key files & pointers

- **Spec/plan:** `features/student-model-postgres-store/` (28-scenario `.feature` + `_assumptions.yaml` + `_summary.md`), `.guardkit/features/FEAT-SMP-001.yaml`, `tasks/backlog/student-model-postgres-store/` (7 task md + IMPLEMENTATION-GUIDE + README).
- **Code:** `src/study_tutor/knowledge/store/{port,postgres,entities,db,wiring,provider,reads,schema_reference.sql}`, `alembic/`.
- **Decision:** [`ADR-ARCH-023`](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md). **Runbook:** [`RUNBOOK-study-tutor-postgres-deploy.md`](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md). **Build plan:** [`student-model-postgres-migration-scope-and-build-plan.md`](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md). **Retros:** [`docs/retros/`](../retros/).

## 11. Suggested opener for the next session

> W0 (durable Postgres on NAS `whitestocks:5434`) and W1 / FEAT-SMP-001 (schema + write path) are done and merged (`main` @ `975547a`). Build **FEAT-SMP-002 (the read path)**: implement `get_student_state` / `get_topic_confidences` / `get_recent_misconceptions` on `PostgresStudentStore` over the W1 schema, behind `knowledge.store.reads`, preserving graceful degradation; then repoint `queries.py` reads and drop the Graphiti read copies. Start with `/feature-spec`, `/feature-plan`, then autobuild. If you use `guardkit autobuild`, first read `docs/retros/` and serialize the waves + export `STUDY_TUTOR_PG_DSN` at an ephemeral Postgres. Don't touch FEAT-SMP-003 (session CRUD) — it's gated by G-CON. Also nudge the operator: the nightly `pg_dump` for the NAS store still isn't scheduled.
