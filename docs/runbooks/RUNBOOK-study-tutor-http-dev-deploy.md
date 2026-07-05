# RUNBOOK — study-tutor HTTP Session API: GB10 dev deployment (TASK-APP1-08)

**Purpose:** put the FEAT-APP-001 HTTP adapter live on the GB10 at `:8100` (dev
flavour) so the Mac-side Flutter build can run its live contract suite and the
cross-device walk. This runbook covers TASK-APP1-08's operator checklist
AC-OP-01 … AC-OP-06.

**Host:** GB10 (`promaxgb10-41b1`, tailnet `100.84.90.91`,
MagicDNS `promaxgb10-41b1.tailebf801.ts.net`).
**Store:** the durable NAS Postgres (`whitestocks`, tailnet `100.92.74.2:5434`)
— the same StudentStore the MCP surface uses; that shared store IS the
cross-device mechanism.
**Code:** `main` ≥ `6747d3d` (FEAT-APP-001 merged + verified).
**Binding contract:** `docs/design/contracts/API-session-http-binding.md`,
frozen at **`BINDING_SHA=6eb7b88c4c8ae412fb36327a4f56286c6b539a7a`** (AC-OP-06 —
communicate this to the Mac side / record in the app build plan).

---

## ⚠️ Read first: what the dev flavour arms

The dev flavour mounts **`POST /__dev__/reset`**, which truncates `session` +
`session_turn` on the DURABLE store — globally, for all students. Learner
state (`student`, XP, streaks, `topic_confidence`, misconceptions,
achievements, quests) is untouched by design, but **real session transcripts
are wiped every time the Mac live suite runs** (it resets per test,
`--concurrency=1`). That is the designed test-isolation trade-off (phase-2
scope §2.4). Phase 1 takes a dump first so nothing is unrecoverable.

When the phase-2 acceptance is done, either take the deployment down or
switch it to the prod flavour (single token, no reset route).

## Phase 0 — Prerequisites (verify, don't assume)

```bash
# NAS Postgres up + schema applied (7 tables + alembic_version)
docker run --rm postgres:16 pg_isready -h 100.92.74.2 -p 5434 -U study_tutor

# llama-swap serving on the GB10 host (the tutor loop's model endpoint)
curl -s http://localhost:9000/health          # expect OK
curl -s http://localhost:9000/v1/models | grep -o 'gemma4-tutor\|qwen36-workhorse'

# tailscale up, GB10 visible
tailscale status --self

# sibling checkout present (the image build sources it as a named context)
ls ../nats-core/pyproject.toml
```

## Phase 1 — Safety dump of the durable store (before arming reset)

```bash
mkdir -p ~/study-tutor-dumps
docker run --rm -e PGPASSWORD='<study_tutor password from repo-root .env>' postgres:16 \
  pg_dump -h 100.92.74.2 -p 5434 -U study_tutor -d study_tutor -Fc \
  > ~/study-tutor-dumps/pre-http-deploy-$(date +%Y%m%d-%H%M).dump

# Record the pre-deploy session row counts for the log:
docker run --rm -e PGPASSWORD='<pw>' postgres:16 \
  psql -h 100.92.74.2 -p 5434 -U study_tutor -d study_tutor -tc \
  "SELECT 'sessions='||count(*) FROM session UNION ALL SELECT 'turns='||count(*) FROM session_turn UNION ALL SELECT 'students='||count(*) FROM student;"
```

(The NAS also has the nightly `pg_dump` via DSM Task Scheduler — this is
belt-and-braces immediately before the first reset-armed deployment.)

## Phase 2 — Author `deploy/http/.env` (gitignored — never commit)

```bash
cd deploy/http
cat > .env <<'EOF'
# DSN uses the NAS TAILNET IP, not the MagicDNS name — the container's
# embedded DNS may not resolve *.ts.net names.
STUDY_TUTOR_PG_DSN=postgresql://study_tutor:<pw>@100.92.74.2:5434/study_tutor
# Dev flavour: BOTH tokens + reset armed (values are the binding doc's §5.1)
STUDY_TUTOR_HTTP_TOKENS={"token-lilymay": "lilymay", "token-alex": "alex"}
STUDY_TUTOR_HTTP_DEV_RESET=1
EOF
```

Prod flavour later: single `token-lilymay` entry, DELETE the
`STUDY_TUTOR_HTTP_DEV_RESET` line.

Model config: the compose defaults already point the tutor loop at llama-swap
via `host.docker.internal:9000` (`gemma4-tutor` / `qwen36-workhorse`). Only add
`TUTOR_*` overrides to `.env` if those aliases change.

## Phase 3 — Build, start, READY check (AC-OP-01)

```bash
cd deploy/http
docker compose build          # named-context build; sources ../nats-core sibling
docker compose up -d
docker compose ps             # wait for healthy (healthcheck = GET /healthz)
curl -s http://localhost:8100/healthz
```

Boot is fail-fast: missing DSN / unreachable store / bad token JSON exits
non-zero before binding — check `docker compose logs` if the container
restarts.

## Phase 4 — Seed + smoke (AC-OP-02)

```bash
# Idempotent identity rows for the token table (runs INSIDE the container,
# which already carries the DSN + token env):
docker compose exec study_tutor_http study-tutor seed-students

# Smoke — both tokens can start a session (proves the FK gap is closed):
curl -s -X POST http://localhost:8100/api/sessions/start \
  -H 'Authorization: Bearer token-lilymay' -H 'Content-Type: application/json' \
  -d '{"subject": "english-literature"}'
curl -s -X POST http://localhost:8100/api/sessions/start \
  -H 'Authorization: Bearer token-alex' -H 'Content-Type: application/json' \
  -d '{"subject": "english-literature"}'

# Negative smoke — unknown token refused per the binding doc (401):
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8100/api/sessions/start \
  -H 'Authorization: Bearer not-a-token' -H 'Content-Type: application/json' -d '{"subject": "x"}'

# Optional: a real turn (exercises the tutor loop → llama-swap; expect a
# tutored reply within the p95<10s budget, first call may pay model load):
curl -s -m 60 -X POST http://localhost:8100/api/sessions/<session_id>/turn \
  -H 'Authorization: Bearer token-lilymay' -H 'Content-Type: application/json' \
  -d '{"user_message": "What does the dagger symbolise in Macbeth?"}'

# Reset roundtrip (dev flavour only — wipes ALL session rows, learner state
# survives; the Phase-1 dump covers you):
curl -s -X POST http://localhost:8100/__dev__/reset
```

## Phase 5 — Tailscale reachability for the Mac (AC-OP-03)

The app/emulator connects across the tailnet:

```bash
# On the Mac:
curl -s http://promaxgb10-41b1.tailebf801.ts.net:8100/healthz   # or http://100.84.90.91:8100/healthz
```

If it fails: Tailscale admin console → Access Controls. A default ("allow
all") tailnet needs nothing; a scoped ACL needs a rule permitting the Mac →
`promaxgb10-41b1:8100`. (The DSM firewall / Aruba gateway are NOT in this
path — tailnet traffic only.)

Android emulator note (scope §3.5): the emulator reaches the Mac's host via
`10.0.2.2` but the GB10 via the tailnet address — use the MagicDNS/IP URL as
`API_BASE_URL`, with the cleartext posture scoped to that host.

## Phase 6 — Mac-side acceptance (AC-OP-04, AC-OP-05 — attended)

1. Live contract suite (Mac repo, `app/test_live/`, built by the p2 waves):
   `API_BASE_URL=http://promaxgb10-41b1.tailebf801.ts.net:8100` +
   **`--concurrency=1`** (the reset is global server state).
2. Cross-device walk (phase-2 scope §3.6): emulator as Lilymay → start + 2
   turns → curl as the same student (`list_sessions` shows `turn_count: 2`,
   `turn` adds an exchange, `resume_session` returns all turns in order) →
   emulator Resume shows all six messages including the curl pair → End on
   emulator → curl `session_status` shows `ended`, `resumable: false`.

## Phase 7 — Close out

- Record `BINDING_SHA=6eb7b88c4c8ae412fb36327a4f56286c6b539a7a` in the app
  build plan (AC-OP-06).
- `/task-complete TASK-APP1-08`, then `/feature-complete FEAT-APP-001`.
- Decide the deployment's standing posture: down (`docker compose down`) or
  re-flavour to prod (edit `.env`, `docker compose up -d`).

## Maintenance / rollback

```bash
docker compose logs -f study_tutor_http     # tail
docker compose restart study_tutor_http
docker compose down                          # stop (store is untouched)
# Restore the Phase-1 dump if ever needed:
docker run --rm -i -e PGPASSWORD='<pw>' postgres:16 \
  pg_restore -h 100.92.74.2 -p 5434 -U study_tutor -d study_tutor --clean --if-exists \
  < ~/study-tutor-dumps/<dumpfile>.dump
```

---

## Execution record — 2026-07-05 (GB10, phases 0–5) ✅

Executed by the deploying session; Mac-side phases 6–7 pending.

| Phase | Result |
|---|---|
| 0 Prerequisites | ✅ NAS PG accepting from GB10; llama-swap OK with `gemma4-tutor` + `qwen36-workhorse`; tailscale up; nats-core sibling present |
| 1 Safety dump | ✅ `~/study-tutor-dumps/pre-http-deploy-20260705-1100.dump`; pre-deploy counts: sessions=0, turns=0, **students=0** (store had never been seeded — the FK gap was live) |
| 2 `.env` authored | ✅ dev flavour, tailnet-IP DSN, gitignore-confirmed |
| 3 Build + READY | ✅ healthy + `{"status":"ok"}` — after three deploy-time fixes (below) |
| 4 Seed + smoke | ✅ seed 2 students (idempotent); start 200 for BOTH tokens; 401 missing/unknown token; 403 cross-student; **real tutored turn** (52s incl. model cold-load); resume returns ordered 2-turn transcript; end → status shows `ended`/`resumable:false` (carve-out); reset deleted 3 sessions + 3 turns, learner rows survived, list `[]` |
| 5 Tailnet reachability | ✅ `http://100.84.90.91:8100/healthz` answers from the GB10 tailnet interface; **Mac-side curl + ACL confirmation = operator** |

**Deploy-time fixes (all pushed):** the wave-6/4 artefacts carried four defects
invisible to config-parse/stub-injection validation — (1) compose build
context/named-context wiring, (2) missing tutor-loop model env +
host-gateway, (3) healthcheck used `curl` (absent from python:3.11-slim →
perpetual unhealthy), (4) `serve-http`'s reply closure called a nonexistent
`PlayerCoachOrchestrator.orchestrate` → every real turn 500'd; replaced with a
per-request `reply_fn_factory` that builds the typed `SessionState` and calls
`run_turn` (the MCP path's API), plus a wiring-guard unit test that pins the
real orchestrator method. Also killed a leaked wave-4 boot-smoke `serve-http`
process squatting `127.0.0.1:8100`.

**For the Mac session:** `API_BASE_URL=http://promaxgb10-41b1.tailebf801.ts.net:8100`
(or `http://100.84.90.91:8100`), `BINDING_SHA=6eb7b88c…`, live suite with
`--concurrency=1`. The service is up and seeded; the reset is armed.

---

## Mac-side acceptance — 2026-07-05 (phase 6, in progress)

Reported by the Mac Flutter session against this deployment.

| AC | Result |
|---|---|
| **AC-OP-03** Tailnet reachability | ✅ **Closed.** `healthz` answered 200 in 16ms from the Mac; tailnet is allow-all, **no ACL work needed**. |
| **AC-OP-04** Live contract suite | 🟢 **Running green.** `app/test_live/`, `--concurrency=1`, detached (~37 real LLM turns, ~30 min at observed latency). §9 unknown-session mapping already green against the real adapter; full triage against the pre-registered success bar when it finishes. |
| **AC-OP-05** Cross-device walk | ⏳ **Stays with GB10/operator** — needs the emulator observed on screen (scope §3.6). |

Full manual round-trip independently re-verified on the Mac: start → real
tutored turn (Socratic reply on fractions) → reset, both directions clean.

### ⚠️ Conformance gap — turn latency breaches SR-07 (GB10-side triage)

**Observed:** `tutor_turn` ~**43s warm, 66s cold**. **Contract:** SR-07 =
p95 < 10s, **hard ceiling 30s** ([API-tutoring.md](../design/contracts/API-tutoring.md#L67)).
So warm turns are ~4× the p95 budget **and over the 30s hard ceiling** — the
tool is currently outside its *sync* classification. Graphiti writes are
fire-and-forget (ADR-ARCH-019) and are **not** the cause; this is the
Player→Coach generation path itself.

- **Not an app-posture issue.** The Mac session correctly kept the app's 15s
  product deadline (the UI would show "connection problem" on most turns
  today — that is the *deployment* being out of spec, not the client). The
  live harness deadline was raised to 120s (loudly documented) so the
  **functional** conformance run stays meaningful; latency conformance is
  tracked separately here.
- **Ranked triage (GB10 side):**
  1. **llama-swap model thrash (most likely, biggest lever).** Player
     (`gemma4-tutor`) and Coach (`qwen36-workhorse`) are two different aliases
     on the single-GPU llama-swap at `:9000`. If they are not co-resident,
     **every turn pays ≥1 model load/unload** (the ~23s cold-vs-warm delta ≈
     one model load, consistent with swapping). `graphiti.yaml` proves
     always-loaded aliases exist on this llama-swap; make `gemma4-tutor` +
     `qwen36-workhorse` (and `nomic-embed` if the coach-handover RAG hits it)
     co-resident / same group, or split them across ports. See in-review
     `TASK-LSP-001` (player-provider route via llama-swap). Confirm from
     llama-swap logs (load/unload lines correlated with turns).
  2. **Per-turn sequential call count.** Happy path = Player **then** Coach = 2
     sequential calls; a below-threshold Coach verdict enters the bounded
     revision loop (`MAX_REVISION_ATTEMPTS=3`) → up to **6** sequential calls.
     Check `TurnResult.attempts`/`decision` in logs — if `attempts>1` is
     common, the Coach rubric threshold is driving revisions. The orchestrator
     already self-reports the breach via `latency_over_budget` flags (budget
     30s, orchestrator.py:72); grep those.
  3. **Generation length + model sizing.** `num_predict ≥ 1500`
     ([API-inference-runtime.md](../design/contracts/API-inference-runtime.md#L100));
     verify GB10 token throughput for the loaded quants.

This gate is for `/feature-complete FEAT-APP-001`'s *latency* conformance, not
for the *functional* live-suite result. Recommend a dedicated GB10-side triage
task before the real app points at this deployment.
