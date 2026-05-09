# Runbook: study-tutor → NATS Fleet — DDD South West Demo

**Status:** Draft (rehearsal target). Demo date: **2026-05-16** (DDD South West).
This runbook is intended to be executed end-to-end at least twice before the
talk: once for verification, once as a dress rehearsal the day before. Update
Status to "Verified" after the first green walkthrough.

**Purpose:** Demonstrate the local-first **tutor** dispatch path live on
stage as a sibling member of the same NATS fleet that hosts the architect
and product-owner agents:

```
human prompt in jarvis chat REPL
  → supervisor reasons + selects dispatch_by_capability
  → tool_name=tutor_start_session (or tutor_turn / session_status / end_session)
  → dispatch via NATS agents.command.gcse-tutor
  → study-tutor container (`gcse-tutor`) on Docker on the host
  → llama-swap on the host serving the `gemma4-tutor` Gemma 4 model
  → structured TutoringResult Pydantic returns via agents.result.gcse-tutor
  → supervisor renders the tutoring transcript fragment back to the human
```

Zero cloud LLM on the path. The tutor reuses the same NATS adapter pattern
that specialist-agent's architect / product-owner roles ship today
(`agents.command.<agent_id>` request-reply with raw inbox reply per Bug #1
fix); the only Phase-3 novelty is that there is now a **third fleet member**
running side-by-side under the same compose pattern.

**Companion / source-of-truth references:**

- `tasks/backlog/nats-fleet-integration/IMPLEMENTATION-GUIDE.md` — the
  feature plan (Phases 1–3, the four binding decisions, the data-flow and
  sequence diagrams).
- `features/nats-fleet-integration/nats-fleet-integration.feature` — the
  Gherkin spec; this runbook is its operational dress.
- `docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md` — review doc that
  catalogued Bugs #1–#4 (the four bugs the fleet fix-stream eliminated).
- `~/Projects/appmilla_github/jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md` —
  structural template this runbook mirrors. The Phase × Gate × Outcome ×
  Evidence shape is identical so cross-runbook comparisons are trivial.
- `~/Projects/appmilla_github/specialist-agent/scripts/nats-evidence-runbook.md` —
  canonical NATS round-trip recipe; reuse §1.1 for credential loading.

**Machine layout (single-host):** GB10 (`promaxgb10-41b1`) hosts:

- NATS JetStream (`ships-computer-nats`, host-network, `:4222`)
- llama-swap (host process, `:9000`, serving `gemma4-tutor` for the tutor
  + `architect-agent` for the architect + `qwen36-workhorse` for the
  supervisor)
- specialist-agent dual-role compose
  (`specialist-agent-architect-agent-1`, `specialist-agent-product-owner-agent-1`)
- **study-tutor compose** (`gcse-tutor` — the Phase-3 addition; see
  `docker-compose.study-tutor.yml`)
- jarvis chat REPL (host venv)

**Expected wall-clock:** ~10–15 minutes for a clean dry-run (most of which
is `tutor_start_session` then a single `tutor_turn` round-trip). On the day,
expect 3–5 minutes from "type prompt" to "tutor's response rendered".

**Outputs:**

- `docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-<YYYY-MM-DD>.md`
  capturing per-phase outcomes and evidence pointers (use
  `docs/runbooks/templates/RESULTS-template.md` as the starting shape).
- `~/.jarvis/transcripts/<correlation_id>.txt` — the chat transcript.
- `~/.jarvis/traces/<correlation_id>.json` — DDR-019 / DDR-029
  routing-history offload (FRR-003 path).
- The captured `TutoringResult` JSON saved to
  `docs/runbooks/evidence/dddsw-demo/<correlation_id>.json` for the talk
  slide.

---

## What this runbook does NOT cover

- **Forge / autobuild dispatch path** — covered by the jarvis
  `RUNBOOK-FEAT-JARVIS-INTERNAL-001-first-real-run.md`. Tutor dispatch
  uses the same `agents.command.<agent_id>` request-reply contract as the
  architect, **not** the workqueue PIPELINE stream.
- **Mid-session Graphiti checkpoints** — Decision 2 (2026-05-08): hot path
  remains in-memory `SessionStore`; checkpoint persistence lands post-demo
  as TASK-NATS-FU-001.
- **Stale-agent reaper.** Decision 3 (2026-05-08): the demo runs with
  manual cleanup of the `agent-registry` KV row. See §6 "Known issue:
  stale registry entries". Self-healing lands as TASK-NATS-FU-002 in the
  jarvis repo, post-demo.

---

## Demo narrative (Talk Track) — read this first

The runbook below is the operator script. The talk track is what the
operator says aloud while the runbook executes:

1. **Frame** (~30s): "Earlier I showed you the architect agent — a
   fine-tuned 26B Gemma. Now I'm going to show you a *second* fleet member
   that ships under the same operational shape. Same NATS contract. Same
   `docker compose up` lifecycle. Different domain — this one is a GCSE
   English Literature tutor, fine-tuned for student-facing dialogue."
2. **Show topology slide** (~30s): five boxes from the architect demo, but
   now a **sixth box** appears: `study-tutor (gcse-tutor)`. Same arrows,
   same wire format, same dispatch contract.
3. **Type the prompt** (~20s): one line into the chat REPL (§4.2).
4. **While it runs** (~30–60s): narrate. The supervisor is selecting
   `tutor_start_session` from the live capability KV, dispatching it to
   `agents.command.gcse-tutor`, the tutor container picks it up, runs the
   business logic against `gemma4-tutor`, returns a structured result on
   `agents.result.gcse-tutor`. Have the wire-tap pane mirrored on stage so
   the audience sees the envelopes flow live (§5).
5. **Read the result aloud** (~30s): the tutor's first turn. "This came
   from the same fleet. Same machine. Same operational discipline. The
   architect was the proof-of-concept; this is the proof-of-pattern."
6. **Land the point** (~30s): "Adding an agent to this fleet is not a
   project — it's a Tuesday. The cost of the next agent is a Dockerfile
   and a manifest."

Total: ~3–4 minutes. Buffer for first-turn latency.

---

## Phase 0: Go/no-go pre-flight

### 0.1 Confirm study-tutor main + clean tree

```bash
cd ~/Projects/appmilla_github/study-tutor
git fetch origin
git status -s -uno
git log --oneline -5
```

**Pass:** Working tree clean, branch `main` up-to-date with `origin/main`.
Top of log includes the four Bug-#1..#4 fixes (PH1-005..PH1-007) plus the
Phase 3 image / compose / runbook tasks (PH3-001..PH3-004).

### 0.2 Confirm specialist-agent + jarvis main

```bash
cd ~/Projects/appmilla_github/specialist-agent && git status -s -uno && git log --oneline -1
cd ~/Projects/appmilla_github/jarvis && git status -s -uno && git log --oneline -1
```

**Pass:** Both repos on `main`, working trees clean. Specialist-agent must
include the Bug #1 (`NATSAdapter` honours inbound `reply` header) and Bug
#2 (`on_command` consults `tool_to_command`) fixes — those are also the
prerequisites for the architect demo, so a green
`RUNBOOK-jarvis-architect-align-dddsw-demo.md` run is the strongest
upstream signal.

### 0.3 Confirm `study-tutor:dev` image is built and current

```bash
docker images study-tutor --format 'table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}'
```

**Pass:** `study-tutor:dev` (or `:latest`) exists; created date is post the
last code change to `src/study_tutor/adapters/`. When in doubt, rebuild:

```bash
cd ~/Projects/appmilla_github/study-tutor
./scripts/docker-build.sh        # produces study-tutor:latest
TAG=dev ./scripts/docker-build.sh # produces study-tutor:dev (compose default)
```

The script wires the BuildKit named context that the Dockerfile expects
(`--build-context nats-core=../nats-core`) — the sibling `nats-core/`
checkout MUST exist alongside `study-tutor/` for the build to succeed
(see `Dockerfile` header).

### 0.4 Confirm llama-swap is up and serving `gemma4-tutor`

```bash
ss -tlnp 2>/dev/null | grep :9000
curl -sf http://localhost:9000/v1/models | jq -r '.data[].id' | sort
```

**Pass:** Port 9000 listening (llama-swap systemd service). Models list
includes **`gemma4-tutor`** (the tutor model) and `qwen36-workhorse` for
the supervisor.

> If `gemma4-tutor` is missing from the model list, the demo fails at the
> tutor's first LLM call with "model not found". Check llama-swap's config
> for the alias mapping. The tutor container reads `LOCAL_MODEL` from env
> (default `gemma4-tutor` per `docker-compose.study-tutor.yml`); if a
> deployment standardises on a different alias, set `TUTOR_LOCAL_MODEL`
> before `compose up`.

### 0.5 Confirm NATS is up + auth env is sourced

```bash
docker ps --filter name=ships-computer-nats --format '{{.Names}}\t{{.Status}}'
```

**Pass:** `ships-computer-nats` Up (healthy).

Surgically load the APPMILLA-account creds (per
`specialist-agent/scripts/nats-evidence-runbook.md` §1.1 — do **not**
source the whole `.env` because it carries stale `OPENAI_API_KEY`
baggage):

```bash
export RICH_NATS_PASSWORD="$(grep '^RICH_NATS_PASSWORD=' ~/Projects/appmilla_github/nats-infrastructure/.env | cut -d= -f2-)"
export RICH_NATS_USER=appmilla
echo "RICH_NATS_USER=$RICH_NATS_USER  RICH_NATS_PASSWORD set: $([[ -n "$RICH_NATS_PASSWORD" ]] && echo yes || echo no)"
```

**Pass:** `RICH_NATS_USER=appmilla  RICH_NATS_PASSWORD set: yes`. If
`set: no`, `docker-compose.study-tutor.yml` will refuse to start (the
`NATS_PASSWORD: ${RICH_NATS_PASSWORD:?must-be-set}` guard fires loudly,
which is the intended behaviour — see Bug-catalogue Bug #2 below).

### 0.6 Confirm canonical NATS provisioning is in place

This is a strict subset of the architect demo's Phase 1. The tutor needs:

- The `AGENTS` JetStream stream (covers `agents.>` subjects)
- The `FLEET` stream (covers `fleet.heartbeat.>` for liveness)
- The `agent-registry` KV bucket (where `gcse-tutor` registers itself)

```bash
cd ~/Projects/appmilla_github/nats-infrastructure
set -a && source .env && set +a
export NATS_URL="nats://rich:${RICH_NATS_PASSWORD}@localhost:4222"
bash scripts/verify-nats.sh
```

**Pass:** all 7 streams + 4 KV buckets reported present.

---

## Phase 1: study-tutor compose up and registered

### 1.1 Bring the tutor stack up

`docker-compose.study-tutor.yml` (TASK-NATS-PH3-002) is additive — it does
not touch the specialist-agent dual-role compose or NATS itself. Both can
coexist.

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml down
docker compose -f docker-compose.study-tutor.yml up -d
sleep 5
docker ps --filter name=gcse-tutor --format 'table {{.Names}}\t{{.Status}}'
```

**Pass:** `gcse-tutor` (or `study-tutor-gcse-tutor-1` depending on compose
project naming) shows Status `Up`.

### 1.2 Confirm the container received the right env

```bash
docker exec gcse-tutor printenv AGENT_ID
docker exec gcse-tutor printenv LOCAL_MODEL
docker exec gcse-tutor printenv OPENAI_BASE_URL
docker exec gcse-tutor printenv LLM_BASE_URL
docker exec gcse-tutor printenv NATS_URL | sed 's/:[^@]*@/:***@/'
```

**Expect:**

```
gcse-tutor
gemma4-tutor
http://host.docker.internal:9000/v1
http://host.docker.internal:9000
nats://appmilla:***@host.docker.internal:4222
```

**Bug #3 trap (the `/v1` suffix):** `OPENAI_BASE_URL` MUST end with `/v1`.
langchain-openai appends `/chat/completions`, so a base URL without `/v1`
yields a POST to `/chat/completions` (no `/v1`) and llama-swap returns
404 — visible only mid-`tutor_turn`, not at startup. The compose default
includes `/v1`; the `tests/unit/test_compose_structure.py` regression
guard asserts every override path keeps the suffix.

### 1.3 Verify the tutor registered to `agent-registry` KV

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv ls agent-registry
```

**Pass:** Output includes a `gcse-tutor` row with non-zero size (alongside
the existing `architect-agent`, `product-owner-agent`, `jarvis` rows from
the architect-demo stack).

### 1.4 Verify the manifest advertises four tools

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv get agent-registry gcse-tutor --raw 2>/dev/null \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('agent_id:', d['agent_id']); print('tool count:', len(d['tools'])); [print('  -', t['name']) for t in d['tools']]"
```

**Pass:** Output:

```
agent_id: gcse-tutor
tool count: 4
  - tutor_start_session
  - tutor_turn
  - tutor_session_status
  - tutor_session_end
```

### 1.5 Verify the heartbeat is firing

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "fleet.heartbeat.gcse-tutor" --count 1
```

**Pass:** A single heartbeat envelope arrives within 30 seconds (default
`HEARTBEAT_INTERVAL_SECONDS=30` per the compose file).

---

## Phase 2: jarvis chat boots clean and surfaces tutor capabilities

### 2.1 Boot jarvis chat

```bash
cd ~/Projects/appmilla_github/jarvis
set -a && source ../nats-infrastructure/.env && set +a
export JARVIS_NATS_URL="nats://rich:${RICH_NATS_PASSWORD}@localhost:4222"
export JARVIS_LOG_LEVEL=INFO
.venv/bin/jarvis chat 2>&1 | tee /tmp/dddsw-tutor-demo-chat.log
```

**Pass (visible in boot log):**

- `nats_connect_success` ✅
- `jarvis_capability_registry_loaded ... capabilities_mode=live` ✅
- `gcse-tutor` appears in the live capability watch (KV-backed registry,
  per TASK-DSR-003 W2 in jarvis)
- The chat banner + `>` prompt rendered

> Use `JARVIS_LOG_LEVEL=INFO`, not DEBUG, for the demo run — DEBUG floods
> the screen with httpx envelopes and obscures the demo. Keep DEBUG for
> rehearsals where you want full evidence.

### 2.2 Confirm the live catalogue surfaced the tutor

In the REPL:

```text
> What tutoring tools do you have available?
```

**Pass:** The supervisor's response names `gcse-tutor` and at least one of
`tutor_start_session` / `tutor_turn` / `tutor_session_status` /
`tutor_session_end`. If the supervisor doesn't see the tutor at all, give
the live KV watch 5–10 seconds to settle and re-ask. If it persists, jump
to §6 troubleshooting.

> Don't dwell on this in the talk — it's an internal check. On stage, skip
> §2.2 and go straight to §3.

---

## Phase 3: The demo turn — start a tutoring session and take one turn

### 3.1 The exact prompt to type

In the chat REPL:

```text
> Please start a GCSE English Literature tutoring session on Macbeth, focused on AO1 and AO2 (knowledge of the text and language analysis), then ask the tutor to walk me through how Shakespeare uses imagery to characterise Macbeth in his "Is this a dagger which I see before me" soliloquy.
```

### 3.2 What should happen (the supervisor's expected behaviour)

The supervisor should:

1. Recognise this as tutor-routable work.
2. Resolve `tutor_start_session` from the live capability catalogue
   (loaded from `agent-registry` KV in §2.1).
3. Construct a `payload_json` matching the manifest (text, focus_aos,
   etc.).
4. Call
   `dispatch_by_capability(tool_name="tutor_start_session", payload_json="{...}", timeout_seconds=120)`.
5. On success, follow up with
   `dispatch_by_capability(tool_name="tutor_turn", payload_json="{...}", timeout_seconds=600)`
   for the dagger-soliloquy question.
6. Render the tutor's response (a coaching prompt + question to the
   student) back to the chat.

**Stage tip:** while it runs, narrate the topology. `tutor_start_session`
is fast (no LLM call); `tutor_turn` is the latency window — Gemma
4-tutor on Blackwell typically responds in 10–30s warm.

### 3.3 Capture the correlation_id

The supervisor will print correlation_ids inline. Capture both
(start_session + turn) — you'll need them for §5 wire evidence and §7
transcript naming.

---

## Phase 4: Wire-level evidence (parallel session — for the talk's "live wire" mirror)

This is the second SSH/terminal pane mirrored on the stage screen behind
you. Run these subscriptions **before** §3 so the envelopes are captured
live as they happen.

> **Bug #4 lesson burned into this section:** the wire-tap subjects below
> are **flat** — `agents.command.>` and `agents.result.>`. Do NOT add an
> agent-id segment followed by a trailing wildcard token — the canonical
> subject is `agents.command.<agent_id>` (no further segments), so a
> wildcard pattern requiring ≥1 token after the agent-id matches **zero**
> envelopes during a real dispatch and the on-stage live mirror goes
> silent. The negative-grep guard in this task's coach validation
> (matching any `agents.command.<token>.<wildcard>` shape against this
> file) enforces the "flat patterns only" rule in CI.

### 4.1 Tail `agents.command.>` (all command envelopes — see Bug #4 note above)

In a second pane:

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "agents.command.>" --raw \
  | tee /tmp/dddsw-tutor-demo-command.log
```

**Pass during §3:** Two envelopes arrive in succession with
`subject=agents.command.gcse-tutor`, `correlation_id`s matching §3.3 (one
for `tutor_start_session`, one for `tutor_turn`), payloads containing the
prompt fields the supervisor extracted.

### 4.2 Tail `agents.result.>` (all result envelopes — see Bug #4 note above)

In a third pane:

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    sub "agents.result.>" --raw \
  | tee /tmp/dddsw-tutor-demo-result.log
```

**Pass during §3:** Two response envelopes arrive shortly after each
command (start_session is sub-second; turn is 10–30s warm). Each envelope
has a `correlation_id` matching its §4.1 counterpart, `payload.success:
true`, and a structured `payload.result` with the tutor's response shape.

> **32-byte trap (per `nats-evidence-runbook.md`):** if the captured
> response file is exactly 32 bytes with `{"stream":"AGENTS","seq":N}`
> inside, you've subscribed wrong (you read a JetStream PubAck instead of
> the agent result). The `--raw` flag on `nats sub` does the right thing;
> only an issue if you use `nats request` interactively.

### 4.3 Save the TutoringResult for the talk slide

After §3 completes:

```bash
mkdir -p docs/runbooks/evidence/dddsw-tutor-demo
jq '.payload.result' /tmp/dddsw-tutor-demo-result.log \
  > docs/runbooks/evidence/dddsw-tutor-demo/<correlation_id_from_3.3>.json
cat docs/runbooks/evidence/dddsw-tutor-demo/<correlation_id_from_3.3>.json | jq .
```

**Pass:** A clean JSON file under
`docs/runbooks/evidence/dddsw-tutor-demo/` with the tutor's reply. **This
is the artefact for the post-talk blog post and slide.**

---

## Phase × Gate × Outcome × Evidence summary table

This is the canonical scoring shape for the RESULTS file. Mirror exactly
when populating `docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-<DATE>.md`.

| Phase | Gate | Expected Outcome | Evidence |
|---|---|---|---|
| 0.1 | study-tutor main + clean tree | ✅ clean | `git status -s -uno` |
| 0.2 | specialist-agent + jarvis main | ✅ clean | `git status` × 2 |
| 0.3 | `study-tutor:dev` image current | ✅ image present, recent | `docker images study-tutor` |
| 0.4 | llama-swap + `gemma4-tutor` | ✅ port 9000 + alias | `/v1/models` |
| 0.5 | NATS up + APPMILLA creds | ✅ healthy + creds set | `docker ps`, env check |
| 0.6 | Canonical NATS provisioning | ✅ 7 streams + 4 KV | `verify-nats.sh` |
| 1.1 | tutor stack up | ✅ Up | `docker ps` |
| 1.2 | container env propagated (incl. `/v1`) | ✅ all five vars | `docker exec printenv` |
| 1.3 | KV registration | ✅ `gcse-tutor` row present | `kv ls agent-registry` |
| 1.4 | Manifest advertises 4 tools | ✅ tool count 4 | `kv get` parsed |
| 1.5 | Heartbeat firing | ✅ envelope within 30s | `sub fleet.heartbeat.gcse-tutor` |
| 2.1 | jarvis boot clean | ✅ `capabilities_mode=live`, gcse-tutor in watch | chat log |
| 2.2 | Live catalogue surfaces tutor | ✅ supervisor names tutor + tools | chat log |
| 3 | Dispatch fires + result rendered | ✅ both round-trips green | chat log + traces |
| 4.1 | Wire tap on `agents.command.>` | ✅ 2 envelopes captured | `evidence/dddsw-tutor-demo/command.log` |
| 4.2 | Wire tap on `agents.result.>` | ✅ 2 envelopes captured | `evidence/dddsw-tutor-demo/result.log` |
| 4.3 | TutoringResult captured | ✅ JSON file under evidence/ | `evidence/dddsw-tutor-demo/<corr>.json` |
| 7.1 | Chat transcript saved | ✅ at `~/.jarvis/transcripts/` | — |
| 7.2 | Routing-history offload | ✅ `outcome_type=success` | `~/.jarvis/traces/<corr>.json` |
| 7.3 | command_history.md entry | ✅ appended | — |
| 7.4 | RESULTS file written | ✅ this file's sibling | — |
| 8 | Demo close | ✅ green | — |

---

## Bug catalogue (template — populate per execution)

Use this shape for any bugs surfaced during a run. The shape mirrors
jarvis's `RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md`
exactly — symptom / cause / fix / where-it-must-live.

### Bug #N — <one-line title> (DEMO BLOCKER | NON-BLOCKING)

**Symptom:** What the operator saw. Include the literal log line, error
text, or wire envelope shape that surfaced the issue.

**Cause:** The actual mechanism. Reference the line of code or the
contract (e.g. "`Topics.Agents.COMMAND = 'agents.command.{agent_id}'` —
no correlation_id suffix, so `agents.command.<id>.>` matches zero
envelopes").

**Confirmed by:** Concrete evidence — trace ID, wire-tap log file, direct
`nats request` diagnostic with timing. Cite the file under
`docs/runbooks/evidence/dddsw-tutor-demo/` that contains the proof.

**Fix options (pick one):**

- **(A)** First option — usually the smallest blast-radius fix.
- **(B)** Alternative if (A) is constrained (e.g. wrong repo).
- **(C)** Cleanest topology fix if breakage is at the contract layer.

**Recommend (A | B | C)** — repository scope: `<which-repo>`.

**Important note (if relevant):** Whether this bug is masked by another
bug (so fixing it surfaces the next layer) or whether it interacts with a
known-issue.

---

The four reference bugs from the original
`docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md` are reproduced
below as worked examples:

### Reference Bug #1 — PubAck race on JetStream-backed COMMAND subject

**Symptom:** Every dispatch's FRR-003 trace records:

```
3 validation errors for ResultPayload
  command: Field required [type=missing, input_value={'stream': 'AGENTS', 'seq': N}, input_type=dict]
  result:  Field required ...
  success: Field required ...
```

**Cause:** `Topics.Agents.COMMAND = "agents.command.{agent_id}"` is
filtered by the AGENTS JetStream stream. `nats_client.request()` sets a
reply-to inbox; nats-server delivers the JetStream ingest-ack to that
inbox immediately. The agent's actual reply lands on `agents.result.<id>`
microseconds later — too late, the future already resolved with the
PubAck.

**Fix (canonical, baked into nats-core `NATSAdapter`):** the adapter
honours the inbound message's `reply` header and republishes the result
payload to that inbox **in addition** to the canonical
`agents.result.<agent_id>` topic. study-tutor inherits this fix via
`nats-core`; no per-role implementation needed.

### Reference Bug #2 — `command_router.on_command` does not consult `tool_to_command`

**Symptom:** The agent rejects the supervisor's tool name verbatim:

```json
{"error": "Command 'tutor_start_session' is not supported.
  Available commands: ['start_session', 'turn', 'session_status', 'end_session']"}
```

**Cause:** The COMMAND-subject handler reads `cmd_payload.command`
literally and looks it up in `command_map`, **never** consulting the
`tool_to_command` mapping that translates manifest tool names to internal
command names.

**Fix (canonical, baked into study-tutor `CommandRouter`):**

```python
command = self.tool_to_command.get(cmd_payload.command, cmd_payload.command)
```

Plus a regression test that sends `tutor_start_session` via the COMMAND
subject and asserts it dispatches `_handle_start_session`.

### Reference Bug #3 — `OPENAI_BASE_URL` missing `/v1` suffix → 404

**Symptom:** First `tutor_turn` returns:

```
Command 'turn' failed: Error code: 404
File "langchain_openai/chat_models/base.py", line 1925, in _agenerate
    _handle_openai_api_error(e)
openai.NotFoundError: Error code: 404
```

**Cause:** `OPENAI_BASE_URL=http://host.docker.internal:9000` (no `/v1`)
yields a POST to `/chat/completions` which llama-swap doesn't route.

**Fix (canonical):** `docker-compose.study-tutor.yml` defaults
`OPENAI_BASE_URL` to `http://host.docker.internal:9000/v1`. The
`tests/unit/test_compose_structure.py` regression guard asserts every
override path keeps the suffix.

### Reference Bug #4 — Wire-tap subject pattern is broken (DOCS BUG)

**Symptom:** Following an older runbook verbatim — subscribing to
`agents.command` plus an agent-id segment plus a trailing wildcard token
— captures **0** envelopes during a real dispatch.

**Cause:** `Topics.Agents.COMMAND = "agents.command.{agent_id}"` — no
trailing token. The NATS `>` wildcard requires ≥1 token after, so any
subscription pattern that appends a wildcard segment beyond the agent-id
matches zero envelopes.

**Fix:** Use the flat patterns `agents.command.>` and `agents.result.>`
as in §4.1 / §4.2 above. The negative-grep guard in this task's coach
validation enforces this in CI by asserting that no
`agents.command.<token>.<wildcard>` shape exists in this runbook.

---

## Phase 6: Failure modes — fast triage during rehearsal

Internalise this; don't read it on stage.

| Symptom | Likely cause | Fix |
|---|---|---|
| `dispatch_by_capability` returns `ERROR: unresolved` for a tutor_* tool | The live `agent-registry` KV doesn't have `gcse-tutor`, OR the row exists but has `tool count: 0`. Most commonly registration failed at boot due to `Authorization Violation`. | Redo §0.5 (export RICH_NATS_PASSWORD, etc.) **in the same shell**, then `compose down + up -d` so compose re-substitutes env. |
| Dispatch returns `TIMEOUT` after 600s | Tutor container is up but llama-swap is overloaded or `gemma4-tutor` is cold-loading | Check llama-swap logs. The first `tutor_turn` against a cold model can exceed normal latency. Warm the model first (one prior call) or bump `timeout_seconds`. |
| Response `payload.success: false` with `error` mentioning `404` | `OPENAI_BASE_URL` lost the `/v1` suffix (Bug #3 regression) | `docker exec gcse-tutor printenv OPENAI_BASE_URL` and confirm it ends in `/v1`. If not, check the override env vars or rebuild from a clean compose file. |
| Response `payload.success: false` with `error` mentioning `'tutor_start_session' is not supported` | Bug #2 regression — `on_command` not consulting `tool_to_command` | This means the deployed image is pre-PH1-004 fix. Rebuild per §0.3. |
| `agents.result.gcse-tutor` tail captures a 32-byte JetStream PubAck | `nats request` used instead of `sub` | Use `nats sub --raw` per §4.2. |
| `agent-registry` KV is empty for `gcse-tutor` after `up -d` | `RICH_NATS_PASSWORD` not propagated into the container — `:?must-be-set` should have prevented this, but if env was set in a different shell the compose file may have started with a stale value | Container logs will show `nats: 'Authorization Violation'`. Redo §0.5 (in the same shell), then §1.1. |
| Jarvis chat REPL doesn't see `gcse-tutor` at all | Live KV watch hasn't propagated yet, OR jarvis is in `capabilities_mode: stub` | Wait 10s and re-ask in §2.2. Confirm jarvis boot log shows `capabilities_mode=live`. |
| Tutor responds correctly the first time but next dispatch hangs | **See §6 below — Known issue: stale registry entries** if a prior tutor process was killed without graceful shutdown | Run the manual cleanup in §6. |

---

## §6 — Known issue: stale registry entries

> Per Decision 3 (2026-05-08) in
> `tasks/backlog/nats-fleet-integration/IMPLEMENTATION-GUIDE.md`: the
> stale-agent reaper is **deferred to jarvis post-demo**. Until it lands,
> this section is the operational cleanup procedure.

**Symptom:** jarvis lists `gcse-tutor` as an available agent (the live
KV-backed catalogue still shows the row) but commands time out instead of
returning errors. No `agents.result.gcse-tutor` envelope ever arrives.

**Cause:** The previous tutor process was killed without graceful shutdown
(SIGKILL, OOM, container crash, host reboot, `docker rm -f`). The
`agent-registry` KV row persists indefinitely because **the registry has
no TTL** — DECISION-NATS-PH2 chose Graphiti over JetStream-KV TTLs for
session durability, and the agent registry inherits the no-TTL property.
Since the tutor process is no longer running, no subscriber is bound to
`agents.command.gcse-tutor`, so jarvis's request publishes successfully
(producing a JetStream PubAck) but no agent-side reply ever materialises
on `agents.result.gcse-tutor`. The dispatch hits its timeout.

**Cleanup (manual, until jarvis-side reaper lands):**

```bash
nats --server "nats://rich:${RICH_NATS_PASSWORD}@localhost:4222" \
    kv del agent-registry gcse-tutor
```

Then bring the tutor back up cleanly:

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml up -d
```

The fresh `start()` in `NATSAdapter` republishes the manifest to the KV
and the row is current again.

**When jarvis-side reaper lands:** TASK-NATS-FU-002 (jarvis repo,
post-demo) wires a background sweeper that consults `fleet.heartbeat.>`
liveness and reaps `agent-registry` entries whose heartbeat is stale by
≥3× the publish interval. After that lands this manual cleanup is no
longer needed; this section can be retired or rewritten as a
historical-context note.

---

## Phase 7: Capture evidence

### 7.1 Save the chat transcript

```bash
cp /tmp/dddsw-tutor-demo-chat.log \
   ~/.jarvis/transcripts/<correlation_id_from_3.3>.txt
```

### 7.2 Verify the routing-history offload landed

```bash
ls -la ~/.jarvis/traces/<correlation_id_from_3.3>.json
jq '{decision_id, outcome_type, outcome_detail, supervisor_reasoning_summary}' \
   ~/.jarvis/traces/<correlation_id_from_3.3>.json
```

**Pass:** `outcome_type=success`,
`outcome_detail.tool_name=tutor_start_session` (or `tutor_turn`),
`supervisor_reasoning_summary=dispatch_by_capability`.

### 7.3 Append a `command_history.md` entry

In `study-tutor/command_history.md`, append a section dated to today with:

- Scenario (e.g. "Macbeth dagger soliloquy, AO1+AO2")
- Both correlation_ids (start_session + turn)
- Latency observations (turn LLM round-trip)
- One-line summary of the tutor's response quality

This is for the post-talk write-up; not visible during the demo.

### 7.4 Write the RESULTS file

Copy `docs/runbooks/templates/RESULTS-template.md` to
`docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-<YYYY-MM-DD>.md` and
populate every section. Mirror this runbook's phase structure with the
Phase × Gate × Outcome × Evidence table from above.

---

## Phase 8: Demo close

Once §3 has rendered the tutor's response and §4 has captured the wire
envelopes:

- [ ] `agents.command.gcse-tutor` (captured via `agents.command.>` tap)
      received both inbound dispatch envelopes with the correlation_ids
      jarvis published
- [ ] `agents.result.gcse-tutor` (captured via `agents.result.>` tap)
      returned both response envelopes with `payload.success: true`
- [ ] Chat REPL rendered the tutor's reply (start_session
      acknowledgement + first tutor_turn answer to the dagger question)
- [ ] Routing-history traces landed at `~/.jarvis/traces/<correlation_id>.json`
      with `outcome_type=success`
- [ ] Talk track delivered against the rolling demo (~3–4 minutes total)

If all five check, the demo is **green**. Take down the tutor stack only
if you're done for the session:

```bash
cd ~/Projects/appmilla_github/study-tutor
docker compose -f docker-compose.study-tutor.yml down
```

> Prefer `down` over `kill` so the adapter's graceful shutdown runs and
> deregisters from `agent-registry` — this is the canonical way to avoid
> §6 (stale registry entries) in the first place.

Leave `ships-computer-nats`, llama-swap, and the specialist-agent
dual-role stack running — other work depends on them.

---

## See also

- **Architect-demo runbook (sibling fleet member):**
  `~/Projects/appmilla_github/jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md`
- **Implementation guide (decisions, sequence diagrams, task breakdown):**
  `tasks/backlog/nats-fleet-integration/IMPLEMENTATION-GUIDE.md`
- **NATS dual-role evidence-capture script** (the
  `agents.command.*` → `agents.result.*` round-trip recipe):
  `~/Projects/appmilla_github/specialist-agent/scripts/nats-evidence-runbook.md`
  + `capture-nats-roundtrip.sh`
- **Phase-3 image / compose / build script:**
  - `Dockerfile` (TASK-NATS-PH3-001)
  - `docker-compose.study-tutor.yml` (TASK-NATS-PH3-002)
  - `scripts/docker-build.sh` (TASK-NATS-PH3-003)
- **NATSAdapter (Bug #1 fix lives here):**
  `src/study_tutor/adapters/nats_adapter.py`
- **CommandRouter (Bug #2 fix lives here):**
  `src/study_tutor/adapters/command_router.py`
- **Manifest factory (the four `tutor_*` tool names):**
  `src/study_tutor/adapters/manifest.py`
- **RESULTS template (use for every per-execution capture):**
  `docs/runbooks/templates/RESULTS-template.md`
- **Evidence directory:** `docs/runbooks/evidence/`
