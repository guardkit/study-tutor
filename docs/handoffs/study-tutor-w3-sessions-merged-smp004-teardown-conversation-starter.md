# Study-tutor — W1/W2/W3 (Postgres StudentStore) DONE → FEAT-SMP-004 (Graphiti teardown) next

**Status:** W0 (durable NAS Postgres) live + schema applied; **W1 (writes), W2 (reads), and W3 (durable sessions) built, verified, merged, and pushed.** G-CON ratified. The Flutter mobile client (the contract's other side) landed. **Next and LAST wave is FEAT-SMP-004 — delete the Graphiti/FalkorDB write plumbing.**
**Date:** 2026-07-04. **Host:** GB10 (`promaxgb10-41b1`, Linux/aarch64). Repo root: `~/Projects/appmilla_github/study-tutor`.
**`main` HEAD:** `ea7c135` (pushed, in sync with `origin/main`). This doc is the orientation + condensed steps for the next session.
**Sequencing update (2026-07-05):** FEAT-SMP-004 now runs **SECOND**, after the HTTP App Access adapter (**FEAT-APP-001**, [its handoff](study-tutor-http-adapter-conversation-starter.md)) — both features edit `cli/main.py` + `pyproject.toml` (so sequential, never parallel), and the Mac-side app waves are blocked on the HTTP binding table + a live `:8100` while this teardown blocks nobody. Two knock-ons for this doc: **(a)** every "`serve` boots" gate below extends to **`serve-http` boots READY** as well — the teardown guts the same `cli/main.py` boot path all three entrypoints share; **(b)** §3e's seed decision narrows — FEAT-APP-001 seeds the Postgres `student` identity rows for its token table, so SMP-004 only decides the graph seed script's disposition.

---

## 0. Where we are in one glance

```
ADR-ARCH-023 (Graphiti/FalkorDB → study-tutor Postgres JSONB)          ✅ ratified
W0  durable Postgres on NAS whitestocks:5434 + schema (G7) + backup    ✅ DONE
W1  FEAT-SMP-001: schema+migration + write path (F1/F2/F3, ping)       ✅ MERGED (efe4fb0)
G-CON  /design-refine cross-device session contract                    ✅ ratified (22791af)
W2  FEAT-SMP-002: read path + planner repoint + drop graph read copies ✅ MERGED
W3  FEAT-SMP-003: 6 session methods + adapter cutover + session-end→PG  ✅ MERGED (ea7c135)
mobile  Flutter app (client of the session contract, under app/)       ✅ landed on origin (waves 0–10)
W4  FEAT-SMP-004: delete the graph WRITE plumbing + tutor_session       ⬅️ NEXT (this doc)
```

## 1. TL;DR

The study-tutor learner store + sessions are now **fully Postgres**. Writes (W1), reads (W2), and durable cross-device sessions (W3) are all live end-to-end on the NAS Postgres, and session-end learner-state persistence goes through `record_session_completion` (Postgres, idempotent), **not** Graphiti. The MCP adapter was cut over onto `SessionService`; the MCP + NATS tool surface is byte-for-byte unchanged. **What remains is dead-code removal:** the Graphiti/FalkorDB WRITE path (`GraphitiWriteHelper` F1/F2/F3, `record_topic_confidence_update`, the graph episodes/client/seed_uuids), the retired in-memory `session/tutor_session.py`, the now-vestigial graph wiring in `cli/main.py`, and the `graphiti-core[falkordb]` dependency. The events bus (DDR-003) stays.

## 2. What shipped (commits on `main`, all pushed)

| Commit | What |
|---|---|
| `ea7c135` | **`feat(smp)`: FEAT-SMP-003 durable cross-device sessions (W3)** — 6 store session methods, `SessionService` wired into both MCP adapter sites, adapter cutover, session-end→Postgres. +2 hand-fixes (see §6). |
| `95f2aba` / `f0ec77e` | W3 plan + spec |
| (rebased) | W2 reads (FEAT-SMP-002) — read methods, planner repoint, Graphiti read-copy removal from `queries.py` |
| `22791af` | `design(smp)`: G-CON — cross-device session contract Accepted |
| `331fa74` | `docs(runbook)`: 5434 hardening reframed for the Aruba/Tailscale topology (Phase 5) |
| `02af6b4` | `ops(smp)`: nightly `pg_dump` backup script (`deploy/postgres/backup.sh`) |
| `efe4fb0` | FEAT-SMP-001 write path (W1) |
| overnight | Flutter mobile app (waves 0–10, under `app/`) — the session contract's client |

## 3. FEAT-SMP-004 — the teardown inventory (READ CAREFULLY)

**Goal (migration build plan §6 W3 / §7):** delete the Graphiti write plumbing; drop `graphiti-core[falkordb]`; swap config to a Postgres DSN; keep the events bus. **Verification gate:** `rg graphiti src/study_tutor` returns only history/comments; `python -c "import graphiti_core"` fails; the app **serves on Postgres end-to-end** (`serve` AND `serve-http` boot clean — FEAT-APP-001 lands first, see the sequencing update); full suite green.

### 3a. DELETE (the graph write path — verify no live importer FIRST, per the call-site-drift retro)
- `src/study_tutor/knowledge/async_write.py` — **`GraphitiWriteHelper`** (F1/F2/F3 `schedule_write`/`drain`, the CC-13 single-`add_episode` machinery).
- `src/study_tutor/knowledge/graphiti_client.py` — the client wrapper + `get_client`.
- `src/study_tutor/knowledge/episodes.py` — `SessionCompletedEpisode`/`TopicConfidenceUpdatedEpisode` etc.
- `src/study_tutor/knowledge/seed_uuids.py` — `topic_confidence_uuid` etc.
- `src/study_tutor/knowledge/queries.py` — the REMAINING write surface: `record_topic_confidence_update`, the fire-and-forget `record_session_completion`, `ConfidenceDeltaPolicyLike`, and `Phase1MinimalDeltaPolicy` (**NOTE: the pure policy was already ported to `session/completion.py` in W3 — the `queries.py` copy is now redundant; confirm and delete**). After removal, `queries.py` may be empty → delete the module + its `__init__` export.
- `src/study_tutor/session/tutor_session.py` — the in-memory `SessionStore` + `TutorTurn`/`TutorSession` + the `SessionNotFoundError(KeyError)` copy. **The W3 adapter cutover stopped using it**; the canonical `SessionNotFoundError` lives in `session/errors.py`. Delete + retire `tests/unit/session/test_tutor_session.py`.
- `src/study_tutor/tutoring/session_end.py` — the OLD graph session-end path: `perform_session_end`, the `SessionCompletedEpisode` build, `GraphitiWriteHelper` drain, `runtime_shutdown`. **W3 routes session-end through `SessionService.end_session`**, so `perform_session_end` should be dead — VERIFY (grep for callers) before deleting; keep whatever the `session.completed` EventBus emit needs (DDR-003 — the event stays; today its payload is built in `session_end.py:440-450`, and W3's adapter preserves it — decide where the emit lives post-teardown).

### 3b. EDIT (vestigial graph wiring)
- `src/study_tutor/cli/main.py` — **the tricky one.** `serve` (line ~369–374) and `_build_nats_runtime` (~538–540) still construct `wrapper = asyncio.run(get_client(...))` + `write_helper = GraphitiWriteHelper(...)`. After W3 the adapter no longer takes them (they're passed to `runtime_shutdown(write_helper)` on shutdown + logged + returned in the nats tuple `(adapter, write_helper)` at line 561/764/768). Remove the graph client/helper construction, the `runtime_shutdown` drain, and simplify the nats return. **This heavily touches the boot path — see §5's boot-on-main verification.** By the time this runs, `cli/main.py` also carries FEAT-APP-001's `serve-http` subcommand on the same boot path — it must keep booting READY too.
- `src/study_tutor/mcp/adapter.py` — matched the grep only via the SR-07 guard comment ("graphiti"/"async" must not appear in tool descriptions) + possibly a dead import; the adapter has **0 internal graph refs** post-W3. Keep the SR-07 guard; remove any dead graph imports.
- `src/study_tutor/planner/pipeline.py` — W2 repointed reads to `store.reads`; the `client` param on `plan_session` is kept for back-compat but unused for the read. Clean if trivial.
- `pyproject.toml` line ~41 — drop `"graphiti-core[falkordb] @ git+..."` (+ the related pins/comments at ~26/74/95) and re-`uv lock`.
- `.env.example` — ensure it advertises `STUDY_TUTOR_PG_DSN` and drops any Graphiti/FalkorDB vars (it currently has 0 graphiti refs — verify it's not stale).
- `adapters/manifest.py`, `tutoring/coach/*` (factory/rubric/sanitise) — matched the grep; **triage** whether their graphiti references are the write path (remove) or unrelated config/prompt-injection hygiene (leave). Don't blanket-delete.

### 3c. KEEP (do NOT touch)
- The events bus + `session.completed` (DDR-003) — decoupled from the write, stays.
- The Postgres layer: `knowledge/store/*`, `session/{service,provider,wiring,errors,completion,identity}.py` — their graphiti mentions are docstring history.
- `student_model.py`, `store/entities.py`, `store/port.py`, `store/reads.py` — history comments only.

### 3d. ADR / docs reconciliation (build plan §7)
- Flip `ADR-ARCH-003` / `-007` / `-019` (async Graphiti write-back) to `Status: superseded`; note `ADR-ARCH-021`'s CC-13 retirement.
- Retire SR-08 (write-back asynchrony). SR-09 unaffected.
- Update `docs/planning/feature-roadmap.md` FEAT-PH1-001 row (Graphiti → Postgres).

### 3e. The seed-script decision (carried from W2, ASSUM-010)
`scripts/seed_student_model.py` seeds the **graph** (Lilymay baseline) and has no Postgres counterpart. W2 reworked its post-seed verification to not import the deleted read symbols, but it still seeds FalkorDB. **Update 2026-07-05 — partially resolved by sequencing:** FEAT-APP-001 (built first) ships a minimal idempotent Postgres seed for its token-table `student` identity rows (`lilymay`, `alex`), because `session.student_id` FKs `student` (`schema_reference.sql:47`) and `create_session` doesn't auto-create. **What remains for FEAT-SMP-004:** the graph seed script itself — port the Lilymay baseline `topic_confidence` seed to Postgres, or deprecate/delete it. Still REVIEW-REQUIRED in `/feature-spec`.

## 4. Workflow — same as W1/W2/W3

`/feature-spec` → `/feature-plan` → `guardkit autobuild feature FEAT-SMP-004`. Suggested kickoff:

```
/feature-spec "Graphiti/FalkorDB write-path teardown (FEAT-SMP-004) — delete GraphitiWriteHelper (async_write), graphiti_client, episodes, seed_uuids, the queries.py write path (record_topic_confidence_update / fire-and-forget record_session_completion / Phase1MinimalDeltaPolicy already ported to session/completion), and the retired in-memory session/tutor_session; strip the vestigial graph client/helper construction + runtime_shutdown drain from cli/main.py serve + _build_nats_runtime; drop graphiti-core[falkordb] from pyproject + uv.lock; swap .env.example to STUDY_TUTOR_PG_DSN; keep the events bus (DDR-003). Verify: rg graphiti src empty bar comments, import graphiti_core fails, serve boots on Postgres end-to-end, full suite green." \
  --context docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md \
  --context docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/knowledge/queries.py \
  --context src/study_tutor/tutoring/session_end.py \
  --context src/study_tutor/cli/main.py \
  --context src/study_tutor/session/tutor_session.py \
  --context pyproject.toml
```
Then `/feature-plan "Graphiti Teardown" --context features/<slug>/<slug>_summary.md --feature-id FEAT-SMP-004 --no-questions`, serialize the waves, then autobuild.

## 5. AutoBuild playbook (READ the retros — all three failure classes have bitten this migration)

Retros to read first — **`docs/retros/`** (study-tutor) + **`guardkit/docs/retros/`**:
1. **Parallel-wave worktree pollution** → **serialize `orchestration.parallel_groups` to one-task-per-wave** (no `--max-parallel` on `autobuild feature`; a strict dep chain auto-serializes). Teardown tasks all touch overlapping modules → serialize.
2. **Self-defeating boundary tests** → scope boundary tests to real invariants; **run the WHOLE `pytest tests/`**, not just `tests/unit` (the `tests/`-vs-`tests/unit` split hides composition breaks).
3. **Coach missed an undefined BDD step** (guardkit) → run `pytest features/<slug>` explicitly; an undefined step is a FAILURE, not `pending`.
4. **Signature change missed production call sites** (guardkit, `99bf79d5`) → **the big one for a teardown.** When you delete a symbol, GREP every call site. And the Coach's unit tests inject deps directly / never boot via `main.py`, so they can't catch a broken `serve`. **After autobuild, independently run the full suite ON THE MERGED `main` TREE WITH `.env` PRESENT** — the worktree has no `.env`, so DSN-gated wiring + the graph-client boot latency MASK boot bugs. **Explicitly assert `serve` boots** (`pytest tests/unit/mcp/test_stdio_discipline.py` with the DSN exported).

**Operational checklist:**
- Serialize the waves in the YAML; add `smoke_gates: after_wave:[…] command: pytest tests/unit`.
- `export STUDY_TUTOR_PG_DSN=<EPHEMERAL throwaway postgres:16 on a non-5434 port, e.g. :55432>` before launching (pre-pull `postgres:16`; `alembic upgrade head`). **NEVER the NAS.**
- Launch: `GUARDKIT_HARNESS=sdk guardkit autobuild feature FEAT-SMP-004 --fresh` (background; SDK harness auths via the bundled CLI, no `ANTHROPIC_API_KEY`).
- **Independent verification before merge (on `main`, `.env` present):** `pytest tests/` + `pytest features/<slug>` + `pytest tests/unit/mcp/test_stdio_discipline.py` (serve boots) + **FEAT-APP-001's READY boot smoke for `serve-http`** + `python -c "import graphiti_core"` should FAIL + `rg graphiti src/study_tutor`.
- **Selective squash-merge** code+test paths only (NOT `.guardkit/`/`tasks/`/`.claude/` churn). Then `git worktree remove --force`, `git branch -D`, tear down the ephemeral PG. Rebase onto `origin/main` before push (origin moves — the Flutter/other work lands frequently; disjoint so rebases are clean).

## 6. W3 hand-fixes to be aware of (context for the teardown)

Two defects the W3 autobuild shipped Coach-approved, caught in independent on-main verification and fixed before merge (both are `ea7c135`):
1. `cli/main.py` — SMP3-06 changed `MCPAdapter.__init__` (`write_helper`/`graphiti_client` → `session_service`) and updated the tests but NOT the `serve` / `_build_nats_runtime` call sites → `serve` crashed on startup. **This is exactly the `write_helper`/`wrapper` vestige FEAT-SMP-004 now removes** — the boot path is fragile; verify `serve` boots after your edits.
2. `tests/integration/test_mcp_lca_smoke.py` — same signature drift in an integration test outside the unit gate.

## 7. Known issues / risks

- **3 pre-existing NATS-smoke failures:** `tests/integration/test_nats_smoke.py::TestSmokeFourCommands` — `command was 'tutor_start_session', expected canonical 'start_session' after alias resolution`. Fails on `main`, **unrelated to the migration** (NATS command-alias routing). Exclude via `--ignore=tests/integration/test_nats_smoke.py` when computing "0 new failures"; worth a separate look sometime.
- Teardown is high-blast-radius (~10 real files + the boot path). The `perform_session_end` / `runtime_shutdown` deletion in `tutoring/session_end.py` + `cli/main.py` is where breakage will hide — grep callers, boot `serve`.

## 8. The durable store (W0) — running instance + operator items

- **Instance:** Postgres 16 `study_tutor_postgres` on NAS **`whitestocks`** (`whitestocks.tailebf801.ts.net`, tailnet `100.92.74.2`), host port **5434**, bind mount `/volume1/docker/study_tutor/pgdata`. **Schema IS applied** (G7 closed 2026-07-04: 7 tables + `alembic_version=3c7cd4bca034`). App DSN in gitignored repo-root `.env` (`STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<pw>@whitestocks…:5434/study_tutor`).
- **Backups:** `deploy/postgres/backup.sh` installed at `/volume1/docker/study_tutor/backup.sh`; **operator has scheduled the nightly DSM Task Scheduler job** (2026-07-04). First dump proven restorable.
- **Still open (operator, low priority):** the **5434 exposure posture** — DSM firewall is OFF; NAS is behind an HPE/Aruba **Instant On SG2505P** gateway. Per RUNBOOK Phase 5: confirm no WAN port-forward for 5434 (Instant On app → Policies → Port Forwarding) + scope tailnet access via **Tailscale ACLs** (the app connects to the tailnet IP; DSM firewall / Instant On can't scope that). **G6 reboot-persistence check** still pending.
- Runbook: [`docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md`](../runbooks/RUNBOOK-study-tutor-postgres-deploy.md) (Phase 5 = the hardening reframe).

## 9. Never point tests at the NAS

DB-backed tests **skip** when `STUDY_TUTOR_PG_DSN` is unset (CI-safe). To run them, point that var at an **ephemeral throwaway Postgres** (`docker run postgres:16 -p 55432:5432`), NEVER `whitestocks:5434`. A scope-guard test asserts no test targets host `whitestocks`/port `5434`. Baseline: full `tests/` minus NATS ≈ **1252 passed** on `main`; `tests/unit` ≈ **1049**.

## 10. Key files & pointers

- **Build plan (authoritative sequence):** [`docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md`](../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) — §6 W3 = the teardown `/feature-spec`; §7 = ADR reconciliation. (NB: the doc's inline command flags have drifted — `/design-refine` no longer takes `--target`; verify skill syntax before copy-paste.)
- **Decision:** [`ADR-ARCH-023`](../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md).
- **Retros (READ before autobuild):** `docs/retros/` (parallel-wave, self-defeating tests) + `guardkit/docs/retros/` (undefined-BDD-step `54ab79fd`, call-site-drift `99bf79d5`).
- **W1/W2/W3 spec+plan artifacts:** `features/student-model-postgres-store*/`, `features/durable-cross-device-sessions/`, `tasks/backlog/*`, `.guardkit/features/FEAT-SMP-00{1,2,3}.yaml`.
- **Mobile track:** `app/` (Flutter client) + [`docs/handoffs/study-tutor-mobile-voice-conversation-starter.md`](./study-tutor-mobile-voice-conversation-starter.md) + `docs/research/ideas/flutter-app-phase2-scope.md`.

## 11. Suggested opener for the next session

> W1 (writes), W2 (reads), W3 (durable sessions) of the Postgres migration are all merged + pushed (`main` @ `ea7c135`); the store + sessions are fully Postgres and session-end no longer touches Graphiti. **FEAT-APP-001 (HTTP App Access adapter) has landed first per the 2026-07-05 sequencing decision** — confirm it's merged before starting. Build the LAST wave, **FEAT-SMP-004 (Graphiti/FalkorDB write-path teardown)**: delete `GraphitiWriteHelper`/`async_write`, `graphiti_client`, `episodes`, `seed_uuids`, the `queries.py` write path (Phase1MinimalDeltaPolicy already ported to `session/completion`), and the retired `session/tutor_session`; strip the vestigial graph client/helper + `runtime_shutdown` drain from `cli/main.py` serve + `_build_nats_runtime`; drop `graphiti-core[falkordb]` from `pyproject`; keep the events bus. Decide the seed-script disposition (Postgres seed vs deprecate). Start with `/feature-spec`, `/feature-plan`, then autobuild. **Read `docs/retros/` + `guardkit/docs/retros/` first** — serialize the waves, export an ephemeral `STUDY_TUTOR_PG_DSN`, and — critically for a teardown — **grep every call site before deleting a symbol** and **independently verify the full suite AND that `serve` boots on the merged `main` tree with `.env` present** (the worktree's missing `.env` masked a `serve`-crash in W3). Verification gate: `rg graphiti src` empty bar comments, `import graphiti_core` fails, `serve` AND `serve-http` boot on Postgres. Don't chase the 3 pre-existing NATS-smoke failures (unrelated).
