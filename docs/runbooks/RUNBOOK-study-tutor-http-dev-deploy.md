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
# Explicit since 2026-08-14 — an unset mode used to mean a silent 'table'
STUDY_TUTOR_AUTH_MODE=table
# Dev flavour: BOTH tokens + reset armed. `<bearer-…>` are PLACEHOLDERS —
# substitute the real random values from the operator's
# ~/.config/study-tutor/tokens-<date>.json (mode 600) on the spark, and
# never paste one back into this repo: it is public, and the bearers this
# runbook used to spell out were rotated on 2026-08-14 for exactly that
# reason. Generate a fresh one with
#   python -c "import secrets; print('st_' + secrets.token_urlsafe(32))"
STUDY_TUTOR_HTTP_TOKENS={"<bearer-lilymay>": "lilymay", "<bearer-alex>": "alex"}
STUDY_TUTOR_HTTP_DEV_RESET=1
EOF
```

Prod flavour later: single `<bearer-lilymay>` entry, DELETE the
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
  -H 'Authorization: Bearer <bearer-lilymay>' -H 'Content-Type: application/json' \
  -d '{"subject": "english-literature"}'
curl -s -X POST http://localhost:8100/api/sessions/start \
  -H 'Authorization: Bearer <bearer-alex>' -H 'Content-Type: application/json' \
  -d '{"subject": "english-literature"}'

# Negative smoke — unknown token refused per the binding doc (401):
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8100/api/sessions/start \
  -H 'Authorization: Bearer not-a-token' -H 'Content-Type: application/json' -d '{"subject": "x"}'

# Optional: a real turn (exercises the tutor loop → llama-swap; expect a
# tutored reply within the p95<10s budget, first call may pay model load):
curl -s -m 60 -X POST http://localhost:8100/api/sessions/<session_id>/turn \
  -H 'Authorization: Bearer <bearer-lilymay>' -H 'Content-Type: application/json' \
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

## Mac-side acceptance — 2026-07-05 (phase 6)

Reported by the Mac Flutter session against this deployment.

| AC | Result |
|---|---|
| **AC-OP-03** Tailnet reachability | ✅ **Closed.** `healthz` answered 200 in 16ms from the Mac; tailnet is allow-all, **no ACL work needed**. |
| **AC-OP-04** Live contract suite | 🟡 **22/35, all 13 failures backend-side (none app-side).** Both root causes fixed (below); re-run expected **35/35**. §9 error mappings, auth, ownership, lifecycle, list semantics, reset isolation all passed live on first contact; the same 35 test bodies pass on the fake ran unmodified against the real adapter. |
| **AC-OP-05** Cross-device walk | ⏳ **Stays with GB10/operator** — needs the emulator observed on screen (scope §3.6). |

### Live-run failures → all three GB10-side, all resolved 2026-07-05

1. **8× wire-shape:** turn entries emitted `"timestamp"` where binding §5 +
   contract §5 pin `ts`. **Fixed** — `http/app.py` serializers, commit `208ebf1`
   (+ a wire-shape regression guard on `resume_session`).
2. **4× `turn_count`:** counted raw transcript rows, not `(user, tutor)` pairs
   (1 turn reported 2). **Fixed** — halved at the serializer, mirroring the MCP
   adapter's `student_turn_count = turn_count // 2` (commit `208ebf1`).
3. **1× >120s first-turn cold-load:** transient — the latency issue below.

### Turn latency (SR-07) — root cause + fix ✅

The earlier "llama-swap thrash" hypothesis was **wrong** — direct inspection
disproved it (both models were co-resident; the keepalive timer is not even
installed). **Actual root cause:** the `tutor` llama-swap set and the
deployment both pointed the Coach at **`qwen36-workhorse`** — a 35B *reasoning*
model (`--reasoning auto`). The study-tutor Coach parser
([`rubric.py` `parse_coach_output`](../../src/study_tutor/tutoring/coach/rubric.py))
does a **strict `json.loads`** on `message.content` (the prompt demands "ONE
JSON object — no prose, no fences"). qwen36-workhorse emitted ~8.8 KB of CoT
into `content` (often leaving it empty) → **`MalformedCoachOutputError` on every
turn**, so the Coach was silently bypassed via the unevaluated-turn fallback,
*and* it burned ~33s doing it → ~43s turns, breaching SR-07 (p95<10s / 30s ceiling).

**Fix (applied 2026-07-05):**
- New llama-swap model **`tutor-coach`** = base Gemma-4-26B-A4B-IT GGUF (same
  weights as `gemma4-coach`, 17/17 JSON-discipline) with **`--reasoning off
  --reasoning-budget 0`**, ctx 32768. `tutor` set changed `gt & qw & em` →
  **`gt & tc & em`** (lighter — drops the 35B @ ctx 131072). Config at
  `/opt/llama-swap/config/config.yaml` (backup `.bak-pre-tutor-coach-2026-07-05`).
- Deployment `deploy/http/.env`: `TUTOR_COACH_MODEL=tutor-coach` (overrides the
  compose default `qwen36-workhorse`). Container rebuilt + recreated.
- `coach-ft-v3` was rejected — `--reasoning off` but its autobuild fine-tune
  emits ```json fences that break the strict parser.

**Validated live (smoke):** warm turn **8.5s** (was ~43s), **0
`MalformedCoachOutputError` / 0 `coach_unreachable`** — the Coach now actually
evaluates (`decision=accept`, 6 criteria). Cold first-turn ≈ **26s** (loads the
tutor set); `gemma4-tutor` has `ttl:1800`, so **warm the set with one throwaway
turn before the attended §3.6 walk** to keep every observed send ~8.5s (< the
app's 15s deadline). `tutor-coach` is `ttl:0` (stays resident).

### Multi-turn latency — async Coach ([ADR-ARCH-026](../architecture/decisions/ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md))

The coach-model swap fixed the *single*-turn case, but the Mac then measured
**36–48s deep in a session**. Probing showed it was neither prefill (3,385 tok
→ 2.7s) nor the revision loop (fired 0/20) — it was the **synchronous Coach
generating a ~500-token verdict (~9s) before the learner saw anything**, every
turn. Fix (ADR-ARCH-026): the Coach is now an **async monitor** — `run_turn`
returns the Player response immediately and `coach.evaluate` runs off the caller
path (single pass, no revision, still flags below-threshold turns); the verdict
prompt is trimmed to ~250 tokens so the background eval clears the single GPU
before the next turn.

**Validated live (2026-07-05, `study-tutor:latest` rebuilt):** with realistic
think-time, turns are **2.1–3.6s** (Player-only critical path; was ~43s). Coach
runs in the background (0 failures; 1 below-threshold turn correctly flagged for
review). Rapid-fire (zero think-time) worst case ~5–12s from background-Coach
GPU contention — not representative of real use, and still < 15s. The cold-load
warm-up note above still applies. Streaming (the perceived-latency end-state) is
tracked as `TASK-STREAM-001` (ADR-ARCH-026 D4), purely additive to this.

**Remaining:** Mac re-runs `test_live` (command unchanged) → expected **35/35**;
then the attended §3.6 cross-device walk (operator, emulator on screen); then
`/feature-complete FEAT-APP-001`.
