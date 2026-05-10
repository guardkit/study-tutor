# Runbook: study-tutor — GB10 Docker Deployment + NATS Availability

**Status:** Draft (first execution pending — promote to "Verified" after the
first green walkthrough on `promaxgb10-41b1`).
**Date prepared:** 2026-05-10
**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 128 GB unified memory.
**Expected wall-clock:** ~15–25 minutes for a clean deployment from a
dependency-ready host (image builds in ~5–10 minutes from cache-cold; the
rest is verification).

**Purpose:** Deploy the `study-tutor` (`gcse-tutor`) NATS subscriber as a
sibling fleet member of the architect / product-owner agents on GB10, then
prove end-to-end that it is **available on NATS** — registered to the
`agent-registry` KV with the expected manifest, publishing heartbeats on
`fleet.heartbeat.gcse-tutor`, and responding to a real
`agents.command.gcse-tutor` → `agents.result.gcse-tutor` request-reply.

**Scope:** Deployment + availability verification only. This is the
operational runbook you execute when:

- Bringing the tutor up on a fresh GB10.
- Re-deploying after a code change, image rebuild, or host reboot.
- Recovering after a container crash or KV registry desync.

**Out of scope:** demo dress rehearsal, talk track, slide capture — those
live in [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
and reuse Phases 1–5 below as their pre-flight.

**Pattern provenance:** structure mirrors
[`jarvis/docs/runbooks/RUNBOOK-FEAT-JARVIS-INTERNAL-001-first-real-run.md`](../../../jarvis/docs/runbooks/RUNBOOK-FEAT-JARVIS-INTERNAL-001-first-real-run.md)
(Phase × Gate × Outcome shape) and
[`guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`](../../../guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md)
(Phase 0 pre-flight + decision-gate table + rollback appendix). The NATS
credential discipline and the 32-byte JetStream PubAck trap come from
[`specialist-agent/scripts/nats-evidence-runbook.md`](../../../specialist-agent/scripts/nats-evidence-runbook.md).
The terse step cadence + "verify end state" close section borrows from
[`guardkit/docs/guides/falkordb-nas-deployment-runbook.md`](../../../guardkit/docs/guides/falkordb-nas-deployment-runbook.md).

---

## Outputs

- A running `gcse-tutor` container on GB10 with `restart: unless-stopped`.
- A current row in NATS `agent-registry` KV with the expected 4-tool
  manifest (`tutor_start_session`, `tutor_turn`, `tutor_session_status`,
  `tutor_session_end`).
- A live heartbeat stream on `fleet.heartbeat.gcse-tutor` at the configured
  interval (default 30 s).
- One captured request-reply round-trip envelope pair under
  `docs/runbooks/evidence/gb10-docker-deployment-<YYYY-MM-DD>/` proving
  end-to-end wire availability.
- A populated decision-gate table (Phase 7) and a `command_history.md`
  entry referencing this run.

---

## Cross-repo state preconditions

Confirm these still hold before executing. If any has drifted, stop and
resolve drift first.

| Repo | Required state |
|---|---|
| `study-tutor` | `main` includes the four PH1 fix tasks (PH1-005..PH1-007 — `NATSAdapter` Bug #1 inbox-reply, `CommandRouter` Bug #2 `tool_to_command` mapping, `OPENAI_BASE_URL` Bug #3 `/v1` suffix) plus PH3-001..PH3-004 (`Dockerfile`, `docker-compose.study-tutor.yml`, `scripts/docker-build.sh`, this runbook's sibling demo runbook). |
| `nats-core` | Sibling of `study-tutor`. Provides `Topics.Agents.COMMAND = "agents.command.{agent_id}"`, `Topics.Agents.RESULT = "agents.result.{agent_id}"`, `Topics.Fleet.HEARTBEAT = "fleet.heartbeat.{agent_id}"`. The `NATSAdapter` Bug #1 fix (honour inbound `reply` header) lives in `nats_core.client`. |
| `nats-infrastructure` | Has `docker-compose.yml` + `streams/provision-streams.sh` + `kv/provision-kv.sh`. Streams: PIPELINE, AGENTS, JARVIS, FLEET, NOTIFICATIONS, SYSTEM, FINPROXY. KV: agent-status, **agent-registry**, pipeline-state, jarvis-session. Multi-account auth (APPMILLA / FINPROXY / SYS) — bare `nats://localhost:4222` will fail. |
| `llama-swap` (host service) | Active on `:9000`, serving the `gemma4-tutor` alias. See [`guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`](../../../guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md) Phases 5–6 for the canonical bring-up. |

---

## Phase 0: Pre-flight

### 0.1 Confirm host + repo layout

```bash
# This runbook assumes you are executing on GB10. /etc/hosts on GB10 maps
# promaxgb10-41b1 to 127.0.0.1, so any `ssh promaxgb10-41b1 …` prefix in
# upstream runbooks is a no-op here.

uname -a
ls -d ~/Projects/appmilla_github/{study-tutor,nats-core,nats-infrastructure,specialist-agent}
```

**Pass:** all four sibling repos resolve. The `nats-core` checkout being
**sibling** to `study-tutor` is a hard requirement of `Dockerfile` /
`scripts/docker-build.sh` (BuildKit named context
`--build-context nats-core=../nats-core` resolves there).

### 0.2 Confirm `study-tutor` checkout is on `main` and clean

```bash
cd ~/Projects/appmilla_github/study-tutor
git fetch origin
git status -s -uno
git log --oneline -5
```

**Pass:** working tree clean (`git status` empty), branch is `main`
up-to-date with `origin/main`. Top of log includes the PH1-005..PH1-007
+ PH3-001..PH3-004 commits referenced in the cross-repo preconditions.

### 0.3 Confirm Docker + BuildKit are present

```bash
docker version --format '{{.Server.Version}}'
docker buildx version
```

**Pass:** server version reported, `buildx` reports `github.com/docker/buildx
v0.x.y`. BuildKit is required for the `--build-context` flag the build
script passes (without it, the image build fails at the `COPY --from=nats-core`
layer).

### 0.4 Confirm llama-swap is up and serving `gemma4-tutor`

```bash
ss -tlnp 2>/dev/null | grep :9000 || sudo ss -tlnp | grep :9000
curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' | sort
```

**Pass:** `:9000` is listening (llama-swap systemd service per
RUNBOOK-v3 §10.2). The model list **must** include `gemma4-tutor` — that
is the alias the tutor's `LOCAL_MODEL` defaults to (per
`docker-compose.study-tutor.yml`). Also acceptable on the same proxy:
`qwen-graphiti`, `nomic-embed`, `qwen36-workhorse` (used by other fleet
members; not required by the tutor).

> **If `gemma4-tutor` is missing:** stop. The container will start cleanly
> and register on NATS, but the first real `tutor_turn` dispatch will
> fail with `model not found` from llama-swap. Either fix the llama-swap
> config (RUNBOOK-v3 Phase 5) or set `TUTOR_LOCAL_MODEL` to an alias the
> proxy actually serves before §3.

### 0.5 Confirm NATS infrastructure is up

```bash
docker ps --filter name=ships-computer-nats --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

**Pass:** `ships-computer-nats` is `Up (healthy)` with `4222`
(client) and `8222` (monitoring) bound.

**If not running:**

```bash
cd ~/Projects/appmilla_github/nats-infrastructure
docker compose up -d
sleep 5
docker compose ps
```

### 0.6 Surgically load NATS credentials (do NOT source the full `.env`)

Per `specialist-agent/scripts/nats-evidence-runbook.md` §1.1: sourcing the
sibling `.env` wholesale clobbers `OPENAI_API_KEY` and other shell state
with stale values. Grab **only** what compose needs:

```bash
export RICH_NATS_PASSWORD="$(grep '^RICH_NATS_PASSWORD=' ~/Projects/appmilla_github/nats-infrastructure/.env | cut -d= -f2-)"
export RICH_NATS_USER=appmilla

# Sanity check (no secrets printed):
echo "RICH_NATS_USER=$RICH_NATS_USER  RICH_NATS_PASSWORD set: $([[ -n "$RICH_NATS_PASSWORD" ]] && echo yes || echo no)"
```

**Pass:** `RICH_NATS_USER=appmilla  RICH_NATS_PASSWORD set: yes`. If
`set: no`, `compose up` will fail loudly via the
`NATS_PASSWORD: ${RICH_NATS_PASSWORD:?must-be-set}` guard in
`docker-compose.study-tutor.yml` — that is the intended behaviour, not a
bug.

### 0.7 Confirm canonical NATS provisioning is in place

```bash
cd ~/Projects/appmilla_github/nats-infrastructure
set -a && source .env && set +a
export NATS_URL="nats://rich:${RICH_NATS_PASSWORD}@localhost:4222"
bash scripts/verify-nats.sh
```

**Pass:** `verify-nats.sh` reports all 7 streams present (PIPELINE,
**AGENTS**, JARVIS, **FLEET**, NOTIFICATIONS, SYSTEM, FINPROXY) and all 4
KV buckets present (agent-status, **agent-registry**, pipeline-state,
jarvis-session). The bolded streams + bucket are the ones the tutor
actually uses.

> **If you see all streams `[MISSING]`:** the `verify-nats.sh` script
> silently swallows `nats stream ls` auth errors and treats them as
> stream-absence — so the standard symptom of forgotten auth is "everything
> looks fresh and red". Re-export `NATS_URL` with the credentials shown
> above and re-run.

**If a stream or bucket is genuinely missing** (typically a fresh
JetStream volume):

```bash
cd ~/Projects/appmilla_github/nats-infrastructure
set -a && source .env && set +a
export NATS_URL="nats://rich:${RICH_NATS_PASSWORD}@localhost:4222"
bash streams/provision-streams.sh
bash kv/provision-kv.sh
bash scripts/verify-nats.sh
```

---

## Phase 1: Build the image

### 1.1 Build `study-tutor:dev`

```bash
cd ~/Projects/appmilla_github/study-tutor
TAG=dev ./scripts/docker-build.sh
```

The build script normalises paths and sets the BuildKit named context
(`--build-context nats-core=../nats-core`) so the Dockerfile's
`COPY --from=nats-core …` layer resolves. Cold build: ~5–10 minutes (uv
dependency resolution + sync). Warm cache rebuild after a source change in
`src/`: ~30–60 s.

**Pass:**

```bash
docker images study-tutor --format 'table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}'
```

shows `study-tutor:dev` with a `CreatedAt` of "less than a minute ago" (or
recent enough to include the latest source change).

> **`compose up` builds on demand.** If you skip §1.1 entirely, the
> compose `build:` directive in `docker-compose.study-tutor.yml` will
> trigger the build at first `up`. Doing it explicitly here separates the
> "did the build break?" failure mode from the "did the container fail to
> start?" failure mode, which is the right shape for an operational
> runbook.

### 1.2 Smoke-test the image without NATS

```bash
docker run --rm study-tutor:dev study-tutor --help | head -10
```

**Pass:** the `study-tutor` console_script resolves and prints its CLI
help (subcommands include `serve`, `serve-nats`). If you get
`exec: study-tutor: not found`, the editable install in Layer 2 of the
Dockerfile failed silently — rebuild with `--no-cache`:

```bash
TAG=dev ./scripts/docker-build.sh --no-cache
```

---

## Phase 2: Bring up the container

### 2.1 Start the stack

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml down 2>/dev/null || true
docker compose -f docker-compose.study-tutor.yml up -d
sleep 5
docker ps --filter name=gcse-tutor --format 'table {{.Names}}\t{{.Status}}\t{{.RestartCount}}'
```

**Pass:** A container named `gcse-tutor` (or `study-tutor-gcse-tutor-1`,
depending on compose project naming) shows Status `Up X seconds`,
`RestartCount` 0.

> **Why `down` then `up -d` rather than `up -d` alone:** compose only
> re-substitutes shell-exported environment variables into the container
> at container *creation* time. If a previous attempt started the
> container with stale `RICH_NATS_PASSWORD` (for example, exported in a
> different terminal pane), `up -d` alone will not pick up the corrected
> value. The `down` + `up` cycle is the canonical fix and matches the
> pattern in `nats-evidence-runbook.md` §1.3.

### 2.2 Confirm container env was propagated correctly

```bash
docker exec gcse-tutor printenv AGENT_ID
docker exec gcse-tutor printenv LOCAL_MODEL
docker exec gcse-tutor printenv OPENAI_BASE_URL
docker exec gcse-tutor printenv LLM_BASE_URL
docker exec gcse-tutor printenv NATS_URL | sed 's/:[^@]*@/:***@/'
docker exec gcse-tutor printenv NATS_USER
docker exec gcse-tutor printenv HEARTBEAT_INTERVAL_SECONDS
```

**Expect:**

```
gcse-tutor
gemma4-tutor
http://host.docker.internal:9000/v1
http://host.docker.internal:9000
nats://host.docker.internal:4222
appmilla
30
```

> **The `/v1` trap (Bug #3):** `OPENAI_BASE_URL` MUST end with `/v1`.
> langchain-openai appends `/chat/completions`, so a base URL without
> `/v1` produces a POST to `/chat/completions` (no `/v1`) and llama-swap
> returns 404 — visible only mid-`tutor_turn`, not at startup. The
> compose default includes `/v1`; the regression-guard test
> `tests/unit/test_compose_structure.py` enforces this. If the value
> reported above does not end in `/v1`, investigate before continuing —
> dispatch will fail at the first turn.

### 2.3 Confirm the container reached `serve-nats` ready state

```bash
docker logs gcse-tutor --tail 50
```

**Pass:** logs include the adapter start sequence — connect → register →
subscribe → heartbeat — with no `Authorization Violation`,
`Connection refused`, or unhandled exception traceback. The exact log
shape depends on the agent's logging config; what you are looking for is
**the absence of red lines** and the presence of either an explicit
`adapter ready` / `serve-nats ready` line or the first
`fleet.heartbeat.gcse-tutor` publish (visible in §3.3 below within 30 s).

**If you see `nats: 'Authorization Violation'`:** the most common cause
is `RICH_NATS_PASSWORD` was not exported before `compose up`. Redo
§0.6 in this same shell, then redo §2.1.

---

## Phase 3: Verify NATS availability

This is the canonical "is it on the wire?" check. A **green Phase 3 is
the deployment success criterion**.

### 3.1 Confirm registration in `agent-registry` KV

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv ls agent-registry
```

**Pass:** output includes a `gcse-tutor` row. If other fleet members are
also up (architect, product-owner, jarvis), they will appear alongside —
that is fine.

### 3.2 Confirm the manifest advertises four tools

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv get agent-registry gcse-tutor --raw 2>/dev/null \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('agent_id:', d['agent_id']); print('tool count:', len(d['tools'])); [print('  -', t['name']) for t in d['tools']]"
```

**Pass:** output is exactly:

```
agent_id: gcse-tutor
tool count: 4
  - tutor_start_session
  - tutor_turn
  - tutor_session_status
  - tutor_session_end
```

If `tool count: 0`, the adapter started but the manifest factory failed —
check `docker logs gcse-tutor` for the manifest construction error.

### 3.3 Confirm the heartbeat is firing

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "fleet.heartbeat.gcse-tutor" --count 1
```

**Pass:** a single heartbeat envelope arrives within
`HEARTBEAT_INTERVAL_SECONDS` seconds (default 30). If nothing arrives in
~45 s, the adapter is up but the heartbeat task is not — check container
logs for an asyncio exception in the heartbeat coroutine.

> Heartbeat subject is **flat** (`fleet.heartbeat.gcse-tutor`, no
> trailing token) per `nats_core/topics.py:113`. Do not append a `>`
> wildcard token after the agent-id (canonical Bug #4 in the demo
> runbook's bug catalogue) — it will match zero envelopes.

---

## Phase 4: End-to-end dispatch verification

Phase 3 proves the agent is *registered and alive*. Phase 4 proves it is
**responsive** — the wire is good for real request-reply work.

### 4.1 Open the wire taps in two extra panes

In **pane A** (command tap):

```bash
mkdir -p ~/Projects/appmilla_github/study-tutor/docs/runbooks/evidence/gb10-docker-deployment-$(date +%Y-%m-%d)
EVIDENCE_DIR="$HOME/Projects/appmilla_github/study-tutor/docs/runbooks/evidence/gb10-docker-deployment-$(date +%Y-%m-%d)"

nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "agents.command.>" --raw \
  | tee "$EVIDENCE_DIR/command.log"
```

In **pane B** (result tap):

```bash
EVIDENCE_DIR="$HOME/Projects/appmilla_github/study-tutor/docs/runbooks/evidence/gb10-docker-deployment-$(date +%Y-%m-%d)"

nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "agents.result.>" --raw \
  | tee "$EVIDENCE_DIR/result.log"
```

> **Subject patterns are flat.** `agents.command.>` and `agents.result.>`
> capture every fleet member's traffic — fine for a single-tutor
> deployment check; the `gcse-tutor` correlation_ids in §4.2 disambiguate
> if the architect or product-owner is also running.

### 4.2 Drive a synthetic `tutor_session_status` round-trip

`tutor_session_status` is the cheapest tool to exercise — it does **no
LLM call**, so a green round-trip proves NATS plumbing and the tutor's
command router without depending on llama-swap or model latency. (The
expected response is a structured "no such session" payload, which is the
*correct* answer for a session_id we just made up — the success signal is
that we got a structured reply, not the content of it.)

In **pane C** (driver):

```bash
CORRELATION_ID="depcheck-$(date +%s)"
echo "Correlation ID: $CORRELATION_ID"

nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    request "agents.command.gcse-tutor" \
    --timeout 30s \
    "$(jq -nc --arg cid "$CORRELATION_ID" '{
        correlation_id: $cid,
        command: "tutor_session_status",
        payload: { session_id: "no-such-session-deployment-check" }
    }')"
```

**Pass:** `nats request` prints a JSON response within a few seconds with
shape:

```json
{
  "correlation_id": "depcheck-...",
  "command": "tutor_session_status",
  "success": true|false,
  "result": { ... structured "session not found" payload ... }
}
```

> **The 32-byte JetStream PubAck trap.** If `nats request` returns
> *exactly* 32 bytes of `{"stream":"AGENTS","seq":N}`, the request landed
> in JetStream but the response went to the canonical `agents.result.<id>`
> subject *after* the 30 s window expired — i.e. you're seeing the
> JetStream ingest-ack, not the agent's reply. Per
> `nats-evidence-runbook.md` §1.6 + the demo runbook's Bug #1: the
> `NATSAdapter` from `nats-core` honours the inbound `reply` header and
> publishes the result to the request's reply-inbox **in addition** to
> the canonical RESULT subject — so this should not happen on a healthy
> stack. If it does, the running image predates the Bug #1 fix; rebuild
> per Phase 1 against current `main` of both `study-tutor` and
> `nats-core`.

### 4.3 Confirm the wire taps captured the round-trip

In pane A's `command.log` and pane B's `result.log` you should now see
matching `correlation_id: depcheck-…` envelopes. Save the round-trip as
deployment evidence:

```bash
EVIDENCE_DIR="$HOME/Projects/appmilla_github/study-tutor/docs/runbooks/evidence/gb10-docker-deployment-$(date +%Y-%m-%d)"

grep "$CORRELATION_ID" "$EVIDENCE_DIR/command.log" > "$EVIDENCE_DIR/$CORRELATION_ID-command.json"
grep "$CORRELATION_ID" "$EVIDENCE_DIR/result.log"  > "$EVIDENCE_DIR/$CORRELATION_ID-result.json"

echo "Captured:"
ls -la "$EVIDENCE_DIR"/$CORRELATION_ID-*.json
```

### 4.4 (Optional) Drive a real `tutor_turn` to validate the LLM path

Skip if you do not need to validate the llama-swap path in this
deployment (e.g. you've already verified it via the demo runbook today).
Run if you need to prove the model alias and `OPENAI_BASE_URL` `/v1`
suffix are good end-to-end.

```bash
CORRELATION_ID="depcheck-turn-$(date +%s)"

# 1. Start a real session.
SESSION_RES=$(nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    request "agents.command.gcse-tutor" --timeout 60s \
    "$(jq -nc --arg cid "$CORRELATION_ID" '{
        correlation_id: $cid,
        command: "tutor_start_session",
        payload: { text: "Macbeth Act 2 dagger soliloquy", focus_aos: ["AO1","AO2"] }
    }')")
echo "$SESSION_RES" | jq .

SESSION_ID=$(echo "$SESSION_RES" | jq -r '.result.session_id // empty')
[ -n "$SESSION_ID" ] || { echo "FAIL: no session_id in start_session response"; exit 1; }

# 2. Take one turn (this is the LLM call — 10–30 s warm).
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    request "agents.command.gcse-tutor" --timeout 600s \
    "$(jq -nc --arg cid "${CORRELATION_ID}-t1" --arg sid "$SESSION_ID" '{
        correlation_id: $cid,
        command: "tutor_turn",
        payload: { session_id: $sid, message: "Walk me through how Shakespeare uses imagery in this soliloquy." }
    }')" | jq .
```

**Pass:** the second response has `success: true` and `result.message`
containing a substantive (>50-word) reply. If `success: false` with
`error` mentioning `404`, the `/v1` suffix is missing — see §2.2 trap
note.

---

## Phase 5: Operational hardening

### 5.1 Confirm the container will survive a Docker daemon restart

The compose file declares `restart: unless-stopped`. Verify the policy is
in effect:

```bash
docker inspect gcse-tutor --format '{{.HostConfig.RestartPolicy.Name}}'
# Expect: unless-stopped
```

**Pass:** prints `unless-stopped`. The container will restart on Docker
daemon restart and on host reboot (provided Docker itself is enabled at
boot — `systemctl is-enabled docker` should report `enabled`).

### 5.2 Decide on supervision: compose vs systemd-managed compose

For most GB10 deployments, `restart: unless-stopped` is sufficient — the
Docker daemon is already managed by systemd, so a host reboot brings the
container back automatically. **Do not** also wrap it in a systemd
service unless you actually need one of the following:

- A dependency ordering constraint (e.g. wait for `ships-computer-nats`
  to be healthy *before* starting the tutor — Docker's
  `depends_on: condition: service_healthy` only works inside a single
  compose project, and the tutor compose intentionally does not include
  NATS).
- A VS Code-terminal lifecycle escape hatch — see RUNBOOK-v3 §10.2 for
  the warning that processes started from a VS Code integrated terminal
  inherit the Chromium cgroup and bypass `Restart=on-failure`. If you
  are starting the tutor from a VS Code terminal on the GB10 *without*
  using `docker compose up -d` (e.g. running `study-tutor serve-nats`
  directly under uv), wrap it in a systemd unit. Inside Docker the
  daemon already isolates from the parent shell scope, so this is
  usually a non-issue.

If you do need a systemd wrapper, mirror RUNBOOK-v3 §10.2 with this unit:

```bash
sudo tee /etc/systemd/system/study-tutor.service << 'EOF'
[Unit]
Description=study-tutor (gcse-tutor) NATS subscriber
After=network.target docker.service ships-computer-nats.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/home/richardwoollcott/Projects/appmilla_github/study-tutor
EnvironmentFile=/home/richardwoollcott/Projects/appmilla_github/nats-infrastructure/.env
ExecStart=/usr/bin/docker compose -f docker-compose.study-tutor.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.study-tutor.yml down

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable study-tutor
sudo systemctl start study-tutor
systemctl status study-tutor
```

### 5.3 (Optional) Set up log rotation / size cap

The compose file does not declare a logging driver, so the default
`json-file` driver is in effect with no size cap. For long-running
deployments, append a `logging:` block to the service:

```yaml
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

This is a one-off edit and does not need to be in this runbook's hot
path; flag it as a follow-up if your `docker logs gcse-tutor --tail 50`
in §2.3 takes more than a second to return (a sign the log file has
grown unbounded).

---

## Phase 6: Verify end state

Run this block and confirm every line of output matches the expected
shape. This is the canonical "deployment is good" check.

```bash
echo "=== Container ==="
docker ps --filter name=gcse-tutor --format 'table {{.Names}}\t{{.Status}}\t{{.RestartCount}}'

echo ""
echo "=== Image ==="
docker images study-tutor --format 'table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}'

echo ""
echo "=== Container env (sensitive values redacted) ==="
for VAR in AGENT_ID LOCAL_MODEL OPENAI_BASE_URL LLM_BASE_URL HEARTBEAT_INTERVAL_SECONDS; do
    printf '  %-32s %s\n' "$VAR" "$(docker exec gcse-tutor printenv "$VAR")"
done
printf '  %-32s %s\n' "NATS_URL" "$(docker exec gcse-tutor printenv NATS_URL | sed 's/:[^@]*@/:***@/')"
printf '  %-32s %s\n' "NATS_USER" "$(docker exec gcse-tutor printenv NATS_USER)"

echo ""
echo "=== NATS registration ==="
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv get agent-registry gcse-tutor --raw 2>/dev/null \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('  agent_id  :', d['agent_id']); print('  tool count:', len(d['tools']))"

echo ""
echo "=== Heartbeat ==="
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "fleet.heartbeat.gcse-tutor" --count 1 --timeout 45s 2>&1 | tail -3
```

**Pass shape:**

```
=== Container ===
NAMES                   STATUS                RESTARTCOUNT
gcse-tutor              Up X minutes          0

=== Image ===
REPOSITORY              TAG    CREATED AT
study-tutor             dev    2026-05-10 ...

=== Container env (sensitive values redacted) ===
  AGENT_ID                         gcse-tutor
  LOCAL_MODEL                      gemma4-tutor
  OPENAI_BASE_URL                  http://host.docker.internal:9000/v1
  LLM_BASE_URL                     http://host.docker.internal:9000
  HEARTBEAT_INTERVAL_SECONDS       30
  NATS_URL                         nats://host.docker.internal:4222
  NATS_USER                        appmilla

=== NATS registration ===
  agent_id  : gcse-tutor
  tool count: 4

=== Heartbeat ===
[#1] Received on "fleet.heartbeat.gcse-tutor"
{...}
```

---

## Phase 7: Decision gate

Mirror this table into `docs/runbooks/RESULTS-study-tutor-gb10-docker-deployment-<DATE>.md`
or append to `command_history.md` for the deployment record.

| Phase | Gate | Expected outcome | Evidence |
|---|---|---|---|
| 0.1 | Host + repo layout | study-tutor, nats-core, nats-infrastructure, specialist-agent all sibling | `ls -d` output |
| 0.2 | study-tutor on main + clean | clean working tree | `git status -s -uno` |
| 0.3 | Docker + BuildKit present | versions reported | `docker version`, `buildx version` |
| 0.4 | llama-swap up + `gemma4-tutor` alias | port 9000 + alias present | `/v1/models` |
| 0.5 | NATS up | `ships-computer-nats` Up (healthy) | `docker ps` |
| 0.6 | NATS creds loaded surgically | `RICH_NATS_PASSWORD set: yes` | shell echo |
| 0.7 | Streams + KV provisioned | 7 streams + 4 KV buckets | `verify-nats.sh` |
| 1.1 | Image built | `study-tutor:dev` recent | `docker images` |
| 1.2 | CLI smoke test | `study-tutor --help` resolves | container stdout |
| 2.1 | Compose up | `gcse-tutor` Up, RestartCount 0 | `docker ps` |
| 2.2 | Container env propagated | all 7 vars correct, `OPENAI_BASE_URL` ends in `/v1` | `docker exec printenv` |
| 2.3 | Container reached ready | no auth violations / tracebacks | `docker logs --tail 50` |
| 3.1 | KV registration | `gcse-tutor` row present | `kv ls agent-registry` |
| 3.2 | Manifest tools | exactly 4 tools advertised | `kv get` parsed |
| 3.3 | Heartbeat firing | one envelope within 30 s | `sub fleet.heartbeat.gcse-tutor` |
| 4.1 | Wire taps open | both panes streaming | tee → `evidence/.../*.log` |
| 4.2 | `tutor_session_status` round-trip | structured reply within timeout, no 32-byte PubAck | `nats request` output |
| 4.3 | Round-trip captured | command + result envelopes filed | `evidence/<corr>-{command,result}.json` |
| 4.4 | (optional) `tutor_turn` LLM path | `success: true`, >50 word reply | result envelope |
| 5.1 | Restart policy | `unless-stopped` | `docker inspect` |
| 5.2 | (optional) systemd wrapper | service active | `systemctl status` |
| 6   | End-state block green | all sections match expected shape | composite |

A deployment is **green** when 0.x, 1.x, 2.x, 3.x (registration + heartbeat
+ tool count), 4.1–4.3 (synthetic round-trip), 5.1 (restart policy), and
the Phase 6 end-state block all pass. 4.4 is optional but recommended on
first deploy or after a llama-swap config change.

---

## Phase 8: Rollback / takedown

### 8.1 Graceful takedown

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml down
```

> **Prefer `down` over `kill`.** `down` lets the adapter's graceful
> shutdown run — it deregisters from `agent-registry`, cancels the
> heartbeat task, drains in-flight commands. Skipping graceful shutdown
> leaves a stale `agent-registry` row that confuses the next dispatch
> (jarvis sees the row, dispatches to `agents.command.gcse-tutor`, no
> subscriber answers, dispatch times out). The cleanup procedure is in
> the demo runbook §6 ("Known issue: stale registry entries"); avoid
> needing it by always taking the agent down with `compose down`.

### 8.2 Manual cleanup if takedown was not graceful

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv del agent-registry gcse-tutor
```

Then bring back up cleanly via Phase 2.1.

### 8.3 Roll back to a previous image

If a new image is bad and you have an older tag locally:

```bash
docker images study-tutor
# Pick the previous tag, then either re-tag or override the compose image.

docker tag study-tutor:<previous-good-sha-or-date> study-tutor:dev
docker compose -f docker-compose.study-tutor.yml up -d
```

If no older tag is locally available, check out the previous git SHA and
rebuild:

```bash
cd ~/Projects/appmilla_github/study-tutor
git log --oneline -10
git checkout <previous-good-sha>
TAG=dev ./scripts/docker-build.sh
git checkout main   # don't leave the worktree in detached-HEAD
docker compose -f docker-compose.study-tutor.yml up -d
```

Then re-run Phases 3 + 6 to confirm the rolled-back image is healthy.

### 8.4 Full teardown (rare — only when the host is being repurposed)

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml down
docker rmi study-tutor:dev
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv del agent-registry gcse-tutor

# If a systemd wrapper was installed in §5.2:
sudo systemctl disable --now study-tutor
sudo rm /etc/systemd/system/study-tutor.service
sudo systemctl daemon-reload
```

Leave `ships-computer-nats`, `llama-swap`, and the specialist-agent
dual-role stack running — the architect / product-owner / jarvis fleet
members depend on them.

---

## Appendix A: Troubleshooting

Reuses the Bug catalogue from
[`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
§6 + Reference Bugs #1–#4. Ops triage table for deployment-time symptoms:

| Symptom | Likely cause | Fix |
|---|---|---|
| `compose up` fails with `must-be-set` on `NATS_PASSWORD` | §0.6 not done in the same shell as §2.1 | Redo §0.6, then §2.1. The guard is intentional. |
| Container is `Up` but `kv ls agent-registry` does not list `gcse-tutor` | `Authorization Violation` in container logs (creds did not reach the container) | `docker logs gcse-tutor --tail 50` to confirm. Redo §0.6 + §2.1 (via `down + up -d`, not `restart`). |
| Heartbeat tap (§3.3) returns nothing | Adapter started but the heartbeat coroutine raised | Inspect logs for an asyncio exception; if absent, the agent-side heartbeat config may be off — `docker exec gcse-tutor printenv HEARTBEAT_INTERVAL_SECONDS`. |
| `serve-nats` exits immediately with `ImportError: No module named 'study_tutor.adapters.command_router'` (or `.nats_adapter` / `.manifest`) | TASK-NATS-PH1-004 / PH1-005 modules under `study_tutor/adapters/` have not landed on the running checkout — `_build_nats_runtime` lazy-imports them and surfaces a clear failure rather than a cryptic AttributeError | Confirm the working checkout includes those tasks (`git log --oneline -- src/study_tutor/adapters/`); rebuild the image after pulling. |
| `nats request` (§4.2) returns 32 bytes of `{"stream":"AGENTS","seq":N}` | Image predates the Bug #1 fix in `nats-core` `NATSAdapter` (inbox-reply) | Rebuild from current `main` of both `study-tutor` and `nats-core` (Phase 1). |
| `tutor_turn` returns `success: false` with HTTP 404 | Bug #3 — `OPENAI_BASE_URL` lost the `/v1` suffix | Confirm via §2.2; correct via env override or compose file edit. |
| `tutor_turn` returns `success: false` with `model not found` | llama-swap is not serving the `gemma4-tutor` alias | §0.4 to confirm; fix llama-swap config per RUNBOOK-v3 Phase 5. |
| Dispatch is rejected with `'tutor_start_session' is not supported. Available commands: ['start_session', ...]` | Bug #2 regression — `CommandRouter.on_command` not consulting `tool_to_command` | Image predates PH1-004; rebuild from current `main` (Phase 1). |
| Heartbeat sub returns 0 envelopes when written as `fleet.heartbeat.gcse-tutor.>` | Bug #4 — flat subject, no trailing token | Drop the `.>` suffix. The canonical subject is `fleet.heartbeat.gcse-tutor` (no further segments). |

---

## Appendix B: Configuration reference

### Container environment variables

| Variable | Default (compose) | Purpose |
|---|---|---|
| `NATS_URL` | `nats://host.docker.internal:4222` | NATS server URL. Override `NATS_HOST` to target a remote NATS over Tailscale. |
| `NATS_USER` | `appmilla` (`${RICH_NATS_USER:-appmilla}`) | NATS account user. |
| `NATS_PASSWORD` | `${RICH_NATS_PASSWORD:?must-be-set}` | NATS account password. Must be exported before `compose up`. |
| `AGENT_ID` | `gcse-tutor` | Identity used for KV registration + heartbeat subject. |
| `OPENAI_BASE_URL` | `http://host.docker.internal:9000/v1` | langchain-openai base URL. **MUST end in `/v1`** (Bug #3). |
| `LLM_BASE_URL` | `http://host.docker.internal:9000` | Bare host for GBNF / llama.cpp branches. **No `/v1` suffix.** |
| `LOCAL_MODEL` | `gemma4-tutor` | llama-swap alias for the tutor model. |
| `OPENAI_API_KEY` | `local-no-auth-required` | Sentinel — llama-swap does not validate, but langchain-openai refuses to construct a client with an empty key. |
| `HEARTBEAT_INTERVAL_SECONDS` | `30` | Cadence of `fleet.heartbeat.gcse-tutor` publishes. |

### NATS subjects (canonical, from `nats_core/topics.py`)

| Subject | Direction | Purpose |
|---|---|---|
| `agents.command.gcse-tutor` | inbound | Dispatch envelope from jarvis (or any caller) — request-reply. |
| `agents.result.gcse-tutor` | outbound | Canonical reply subject; the adapter also publishes to the request's `reply` inbox per Bug #1 fix. |
| `fleet.heartbeat.gcse-tutor` | outbound | Liveness signal at `HEARTBEAT_INTERVAL_SECONDS`. |
| `agent-registry` (KV bucket) | r/w | Tutor's tool manifest, written at adapter `start()`. |

### Ports in use

| Port | Process | Notes |
|---|---|---|
| `4222` | `ships-computer-nats` (host) | NATS client — accessed from inside the container as `host.docker.internal:4222`. |
| `8222` | `ships-computer-nats` (host) | NATS monitoring. |
| `9000` | `llama-swap` (host) | Model serving — accessed from inside the container as `host.docker.internal:9000`. |
| `host.docker.internal` | resolved via `extra_hosts: host-gateway` in compose | Routes the container to the host network. |

The `gcse-tutor` container itself **exposes no ports**; it is a NATS
subscriber, not an HTTP service. There is no healthcheck endpoint —
liveness is observed via the `fleet.heartbeat.gcse-tutor` subject.

---

## See also

- **Demo dress-rehearsal runbook** (uses Phases 1–5 of *this* runbook as
  its pre-flight, then adds talk track + slide capture):
  [`RUNBOOK-study-tutor-nats-fleet-demo.md`](RUNBOOK-study-tutor-nats-fleet-demo.md)
- **llama-swap production deployment** (the upstream model service this
  runbook depends on):
  [`guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`](../../../guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md)
- **NATS fleet bring-up + KV/streams** (the upstream NATS infrastructure
  this runbook depends on; auth + verify pattern):
  [`jarvis/docs/runbooks/RUNBOOK-FEAT-JARVIS-INTERNAL-001-first-real-run.md`](../../../jarvis/docs/runbooks/RUNBOOK-FEAT-JARVIS-INTERNAL-001-first-real-run.md)
  Phases 0–1
- **NATS round-trip evidence capture** (the surgical creds load + the
  32-byte PubAck trap):
  [`specialist-agent/scripts/nats-evidence-runbook.md`](../../../specialist-agent/scripts/nats-evidence-runbook.md)
- **NAS deployment runbook style** (terse, "verify end state", rollback):
  [`guardkit/docs/guides/falkordb-nas-deployment-runbook.md`](../../../guardkit/docs/guides/falkordb-nas-deployment-runbook.md)
- **Container build + compose definitions:**
  - [`Dockerfile`](../../Dockerfile)
  - [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml)
  - [`scripts/docker-build.sh`](../../scripts/docker-build.sh)
- **Code loci for the four reference bugs:**
  - Bug #1 (PubAck race): `nats-core/src/nats_core/client.py` (adapter
    honours inbound `reply` header)
  - Bug #2 (`tool_to_command`): wired in
    [`src/study_tutor/cli/main.py`](../../src/study_tutor/cli/main.py)
    around line 519 (`CommandRouter(... tool_to_command=role_entry.tool_to_command, ...)`).
    The `CommandRouter` / `NATSAdapter` / `_tutor_manifest_factory` modules
    under `study_tutor.adapters.*` are lazy-imported in `_build_nats_runtime`
    and depend on TASK-NATS-PH1-004 / PH1-005 having merged — if those
    tasks are not yet on the running checkout, `serve-nats` will fail
    fast with `ImportError` (intentional, per the docstring on
    `_build_nats_runtime`).
  - Bug #3 (`/v1` suffix): [`docker-compose.study-tutor.yml`](../../docker-compose.study-tutor.yml)
    + [`tests/unit/test_compose_structure.py`](../../tests/unit/test_compose_structure.py)
    regression guard
  - Bug #4 (flat wire-tap subjects): `nats-core/src/nats_core/topics.py`
