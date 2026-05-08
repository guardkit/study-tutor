# REVIEW: NATS Fleet Integration Patterns for study-tutor

**Date:** 2026-05-08
**Reviewer:** Claude (research agent — Opus 4.7, 1M ctx)
**Scope:** All three phases of the planned NATS fleet integration for study-tutor
**Reference repos (HEAD shas):**
- `specialist-agent` @ `82ce8a6` (post `7345e33` TASK-LLM-0D07; bug-fix delta below)
- `jarvis` @ `4a7eee9` (post `30e4ae4` TASK-DSR-003 W2 — live KV resolver)
- `forge` @ `1b04b89`
- `nats-core` @ working tree (sibling, vendored via BuildKit named context)
- `nats-infrastructure` @ working tree (provisioning + creds)
**Target:** `study-tutor` — `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration/`
**Demo deadline:** 2026-05-11 (Phase 1 must ship); Phases 2-3 land before DDD South West (2026-05-16)

---

## Executive summary

- **Adopt the specialist-agent pattern verbatim.** `NATSAdapter` (lifecycle), `CommandRouter` (dispatch), `manifest.py` (capability factory), `roles/<role>/__init__.py` (`register_role` self-registration), and `cli/main.py:serve-nats` (entrypoint) are a tight, well-factored template. study-tutor's "tutor" role is structurally simpler than architect (4 commands, no path args, no mode inference), but the *shape* must match for parity with the rest of the fleet.
- **Land all four bugs from `RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md` from day one.** The PubAck race (Bug #1), `on_command` mapping miss (Bug #2), `OPENAI_BASE_URL` /v1 suffix (Bug #3), and the wire-tap subject pattern (Bug #4) are all already fixed in the `82ce8a6` snapshot of specialist-agent's `nats_adapter.py` + `command_router.py`. study-tutor only needs to *not regress* them.
- **`nats-core` is the contract.** Every subject string comes from `nats_core.Topics.resolve(...)`, every payload is a `MessageEnvelope` wrapping a `CommandPayload`/`ResultPayload` from `nats_core.events._agent`, and `agent_id` is kebab-case (regex `^[a-z][a-z0-9-]*$`). study-tutor's `gcse-tutor` agent_id is compliant.
- **The existing scope doc is broadly right but understates the bugs.** The "thin dispatcher" framing in Phase 1 is fine *only if* the team adopts the canonical request/reply contract from day one (i.e. `subscribe_with_reply` + raw-publish to inbox AND envelope-publish to result topic). The doc says "match command:" — that's structurally OK but must include the `tool_to_command.get(cmd, cmd)` alias resolution (Bug #2 fix), or jarvis dispatches will fail.
- **Phase 1 includes live registration + heartbeat (decision 2026-05-08).** The original scope doc deferred these to Phase 2. Decision: collapse registration + heartbeat into Phase 1 (~30 LoC, the architect already ships them), eliminating the stub-yaml fallback entirely. Lower demo risk; one less moving part for jarvis-side discovery. See [Decision log](#decision-log-2026-05-08).
- **Session durability uses hybrid Graphiti, not JetStream KV (decision 2026-05-08).** Sessions are tutor-domain (already serialised to Graphiti via `SessionCompletedEpisode` at end-of-session — see [`session/tutor_session.py:1-5`](../../src/study_tutor/session/tutor_session.py#L1-L5) docstring stating original design intent). KV is the *fleet-control* layer (`agent-registry`, `agent-status`). Recommendation: keep in-memory `SessionStore` as the active-turn hot path; add async mid-session checkpoints to Graphiti every N turns; resume-on-boot by querying Graphiti for the agent's active sessions. Phase 1-3 ship with in-memory only; durability lands as TASK-NATS-FU-001 post-demo. See [Decision log](#decision-log-2026-05-08).
- **Stale-agent reaper deferred to jarvis post-demo (decision 2026-05-08).** Today: 3-agent controlled environment, manual `nats kv del agent-registry <id>` is acceptable. Post-demo: background polling reaper in jarvis (TASK-NATS-FU-002, jarvis-owned). study-tutor's Phase 3 runbook documents the symptom + cleanup command. Not blocking. See [Decision log](#decision-log-2026-05-08).

---

## Reference architecture (current state on GB10)

```
┌─────────────────┐       ┌──────────────────────┐
│   Open WebUI    │       │   Reachy Mini        │
│  (browser UI)   │       │   (voice — future)   │
└────────┬────────┘       └──────────┬───────────┘
         │ HTTP                      │ NATS pub
         ▼                           ▼
┌──────────────────────┐    ┌───────────────────────┐
│ NATS Pipe Function   │    │  (post-hackathon —    │
│ (fleet-gateway)      │    │   direct to jarvis)   │
└────────┬─────────────┘    └───────────────────────┘
         │ jarvis.command.<adapter>
         ▼
┌────────────────────────────────────────────────────┐
│                    JARVIS                          │
│ (supervisor: qwen36-workhorse via llama-swap)      │
│  • CapabilitiesRegistry (live KV-backed)           │
│  • dispatch_by_capability(tool_name=...)           │
│  • RoutingHistoryWriter → ~/.jarvis/traces/        │
└────────────────────────┬───────────────────────────┘
                         │ agents.command.<agent_id>
                         │   (request/reply via _INBOX)
                         ▼
        ┌────────────────┴───────────────┐
        ▼                ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  architect-  │  │ product-     │  │ gcse-tutor   │
│  agent       │  │ owner-agent  │  │  (PLANNED)   │
│  (LIVE)      │  │   (LIVE)     │  │ this review  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │ agents.result.<agent_id>          │
       └────────────────┬──────────────────┘
                        ▼
           ┌────────────────────────┐
           │    forge (autobuild)   │
           │  pipeline.build-* via  │
           │  PIPELINE JetStream    │
           └────────────────────────┘

NATS JetStream streams (verify-nats.sh):
  PIPELINE      pipeline.>          work, 7d, 10000
  AGENTS        agents.>            limits, 24h, 5000   ← study-tutor traffic
  JARVIS        jarvis.>            limits, 1h, 1000
  NOTIFICATIONS notifications.>     work, 24h, 1000
  SYSTEM        system.>            limits, 1h, 500
  FLEET         fleet.>             limits, 1h, 5000    ← register/heartbeat
  FINPROXY      finproxy.>          work, 24h, 5000     (project-scoped)

KV buckets (kv-definitions.json):
  agent-status      no TTL, 64KB    last status per agent
  agent-registry    no TTL, 256KB   manifests; jarvis reads/watches this
  pipeline-state    7d, 64KB        feature build state
  jarvis-session    1h, 128KB       jarvis conversation context

Auth: APPMILLA account; user 'rich' / RICH_NATS_PASSWORD
NATS host: ships-computer-nats container, port :4222 + :8222 (monitor)
```

**What works today (post 2026-05-08 W2 fix):** infrastructure, KV catalogue propagation, jarvis dispatch resolver reads live KV, qwen36-workhorse selects `dispatch_by_capability` correctly.

**What's red:** end-to-end dispatch path itself — Bugs #1 + #2 stack on top of one another and produce `outcome_type=exhausted` traces. Both are fixed in `82ce8a6` (the architect-side reference at the time of this review). Evidence: `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md` lines 60-138.

**What's amber:** OPENAI_BASE_URL `/v1` suffix (Bug #3) needs an env-var fix in `.env` AND in compose. Wire-tap subject pattern in the runbook §5.1/5.2 was wrong (Bug #4) — should be `agents.command.>` not `agents.command.architect-agent.>`.

---

## Phase 1 — Minimum viable NATS adapter

### 1.1 Subject conventions

All subjects live in `nats-core/src/nats_core/topics.py` (single source of truth). study-tutor MUST resolve subjects through `Topics.resolve(...)` — never compose strings directly.

| Subject template | Constant | study-tutor resolves to | Direction |
|---|---|---|---|
| `agents.command.{agent_id}` | `Topics.Agents.COMMAND` | `agents.command.gcse-tutor` | Inbound (jarvis → tutor) |
| `agents.result.{agent_id}` | `Topics.Agents.RESULT` | `agents.result.gcse-tutor` | Outbound (event-stream consumers) |
| `agents.{agent_id}.tools.{tool_name}` | `Topics.Agents.TOOLS` | `agents.gcse-tutor.tools.tutor_turn` | Optional direct tool-call surface |
| `fleet.register` | `Topics.Fleet.REGISTER` | `fleet.register` | Outbound (Phase 2) |
| `fleet.heartbeat.{agent_id}` | `Topics.Fleet.HEARTBEAT` | `fleet.heartbeat.gcse-tutor` | Outbound (Phase 2) |
| `fleet.deregister` | `Topics.Fleet.DEREGISTER` | `fleet.deregister` | Outbound on shutdown (Phase 2) |

Key constraint: `agents.>` is captured by the `AGENTS` JetStream stream (file storage, 24h, 5000 msgs). This means **publishing to `agents.command.<agent_id>` returns a JetStream PubAck** (`{"stream":"AGENTS","seq":N}`) on the publisher's reply-inbox unless the subscriber pre-empts it. **This is the source of Bug #1.** See §Bug catalogue.

#### Wire format

`MessageEnvelope` wraps every event-stream publish; raw `ResultPayload` JSON is used for inbox replies (request/reply contract). Citations:

- `nats-core/src/nats_core/envelope.py` — `MessageEnvelope`, `EventType` enum.
- `nats-core/src/nats_core/events/_agent.py:133-189` — `CommandPayload` and `ResultPayload`.
- `MessageEnvelope.version = "1.0"` (`command_router.py:85` — `_EXPECTED_VERSION`); forward-compat: log warn but process.

Minimal `CommandPayload` shape (`nats-core/src/nats_core/events/_agent.py:133-159`):

```python
class CommandPayload(BaseModel):
    command: str  # e.g. "tutor_turn" OR "tutor_start_session" (alias resolved in router)
    args: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
```

Minimal `ResultPayload` shape (`nats-core/src/nats_core/events/_agent.py:161-189`):

```python
class ResultPayload(BaseModel):
    command: str
    result: dict[str, Any]
    correlation_id: str | None = None
    success: bool
```

**Critical:** jarvis's `dispatch_by_capability` parses inbox replies as raw `ResultPayload` JSON, not as `MessageEnvelope` (`jarvis/src/jarvis/tools/dispatch.py:582` → `ResultPayload.model_validate_json(reply_body)`). study-tutor's adapter must raw-publish a `ResultPayload` to the inbox — see §1.2 below.

### 1.2 NATSAdapter (agent-side)

The canonical reference is `specialist-agent/src/specialist_agent/adapters/nats_adapter.py:42-312`. study-tutor's adapter should be a structural copy with:

- `role_id="tutor"` (not `architect`)
- Smaller `manifest.max_concurrent` if desired (`1` is fine for Phase 1; the architect uses `2`)
- No mode-inference plumbing (`set_mode_inference` not needed)

**Connection + auth.** AgentConfig is loaded from env (`AGENT_*` prefix, `__` nested delimiter). The relevant vars:

```bash
# nats-core/src/nats_core/agent_config.py:78-152
AGENT_NATS__URL=nats://rich:${NATS_PASSWORD}@host.docker.internal:4222
AGENT_NATS__USER=rich              # if not embedded in URL
AGENT_NATS__PASSWORD=...           # SecretStr; NATS_PASSWORD passes through for compatibility
AGENT_MODELS__REASONING_MODEL=local
AGENT_HEARTBEAT_INTERVAL_SECONDS=30
AGENT_HEARTBEAT_TIMEOUT_SECONDS=90
```

Canonical CLI (`specialist-agent/src/specialist_agent/cli/main.py:1712-1769`) accepts `--nats <url>` and `--user/--password-env` overrides. study-tutor's CLI should mirror this.

**Subscription setup.** `specialist-agent/src/specialist_agent/adapters/nats_adapter.py:115-133` is the load-bearing fragment — copy literally:

```python
# Subscribe to command subject and wire CommandRouter
self._router = CommandRouter.for_role(self._role_id, self)
command_subject = Topics.resolve(
    Topics.Agents.COMMAND, agent_id=self._manifest.agent_id
)
# TASK-IMP-DDSW-001 Bug #1: subscribe_with_reply propagates msg.reply
# so on_command can publish the response straight to the requester's
# _INBOX inbox (jarvis parses the reply as raw ResultPayload, not as
# an envelope). Event-stream consumers continue to use subscribe().
self._command_sub = await self._client.subscribe_with_reply(
    command_subject, self._router.on_command
)
```

**Why `subscribe_with_reply` not `subscribe`?** `nats-core/src/nats_core/client.py:177-223` — the former passes `msg.reply` (the `_INBOX.<token>` allocated by `nc.request(...)`) through to the callback. Without it, Bug #1 reasserts.

**Publish/reply pattern (Bug #1 fix).** `command_router.py:1052-1103` is the canonical implementation:

```python
async def _publish_result(
    self, command, result, success, correlation_id, reply_to=None
):
    payload = ResultPayload(
        command=command, result=result,
        correlation_id=correlation_id, success=success,
    )

    if reply_to is not None:
        # Raw-publish to the requester's inbox (request/reply contract).
        await self._adapter._client.publish_raw(
            reply_to, payload.model_dump_json().encode()
        )
        return

    # Fallback: envelope-wrapped publish to the result topic for
    # event-stream consumers that don't use request/reply.
    topic = Topics.resolve(
        Topics.Agents.RESULT,
        agent_id=self._adapter._manifest.agent_id,
    )
    await self._adapter._client.publish(
        topic, payload, event_type=EventType.RESULT,
        source_id=self._adapter._manifest.agent_id,
        correlation_id=correlation_id,
    )
```

Observation: the architect publishes ONLY to inbox when `reply_to` is set, and ONLY to the result topic when it isn't. The runbook's "Fix option (A)" was "reply to inbox AND publish on result subject"; the actual landed fix is "reply to inbox OR publish on result subject" — single-write, deterministic. study-tutor should do the same. The runbook's wording is misleading; the *code* is correct.

**Graceful shutdown.** `nats_adapter.py:145-215`. Steps in order: cancel heartbeat → unsubscribe → wait for active tasks → publish deregistration → drain + close NATS connection.

### 1.3 CommandRouter / on_command — Bug #2 fix

The canonical fragment is `command_router.py:496-503`:

```python
# TASK-IMP-DDSW-001 Bug #2: resolve tool-name aliases (e.g.
# "architect_align" → "align") before the command_map lookup. Mirrors
# what on_tool_call already does, giving a single source of truth for
# command resolution across the command-subject and tool-call paths.
# Canonical verbs are absent from tool_to_command, so .get(c, c)
# passes them through unchanged.
command = self.tool_to_command.get(command, command)
```

For study-tutor, `tool_to_command` will be:

```python
{
    "tutor_start_session": "start_session",
    "tutor_turn": "tutor_turn",            # canonical name
    "tutor_session_status": "session_status",
    "tutor_session_end": "end_session",
}
```

Or — alternatively — keep canonical commands as `tutor_*` and leave `tool_to_command` empty so the `.get(c, c)` pass-through works without aliasing. Both are valid. Match whatever shape `fleet-gateway/openwebui/nats_fleet_pipe.py` and jarvis's catalogue advertise.

**`on_command` vs `on_tool_call`.** `on_command` (`command_router.py:328`) handles `agents.command.<agent_id>` — the path jarvis uses. `on_tool_call` (`command_router.py:408`) handles `agents.<agent_id>.tools.<tool_name>` — direct tool-call surface, optional. **Phase 1 only needs `on_command`.** `on_tool_call` is not wired in `nats_adapter.py:start()` for the architect either; treat it as future scope.

### 1.4 Role pattern — study-tutor as a "tutor" role

The architect role's self-registration is `specialist-agent/src/specialist_agent/roles/architect/__init__.py:32-47`. study-tutor's equivalent (in `study-tutor/src/study_tutor/roles/tutor/__init__.py` or wherever — pick a path that matches existing conventions):

```python
# Mirror of specialist-agent/src/specialist_agent/roles/architect/__init__.py:32-47
from study_tutor.roles.registry import FleetRoleEntry, register_role
from study_tutor.adapters.manifest import _tutor_manifest_factory  # to be created

register_role(
    FleetRoleEntry(
        role_id="tutor",
        default_agent_id="gcse-tutor",
        manifest_factory=_tutor_manifest_factory,
        tool_to_command={
            "tutor_start_session": "start_session",
            "tutor_turn": "tutor_turn",
            "tutor_session_status": "session_status",
            "tutor_session_end": "end_session",
        },
        output_handler_import_path=(
            # Phase 1: not strictly needed (no result_wrapper). Set to
            # the adapter or a placeholder; the architect's wrap_role_output
            # is invoked only when result is a SessionResult — study-tutor
            # returns plain dicts.
            "study_tutor.mcp.adapter.MCPAdapter"
        ),
    )
)
```

`FleetRoleEntry` shape from `specialist-agent/src/specialist_agent/roles/registry.py:18-26`:

```python
@dataclass(frozen=True)
class FleetRoleEntry:
    role_id: str
    default_agent_id: str
    manifest_factory: Callable[[str], AgentManifest]
    tool_to_command: dict[str, str]
    output_handler_import_path: str
```

**Manifest factory.** Mirror `specialist-agent/src/specialist_agent/adapters/manifest.py:23-218` (the `_architect_manifest_factory`). For study-tutor:

```python
def _tutor_manifest_factory(agent_id: str) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,                # "gcse-tutor"
        name="GCSE Tutor Agent",
        version="0.1.0",
        template="player-coach-deterministic-planner",  # or whatever matches
        trust_tier="specialist",
        required_permissions=["graphiti:read", "graphiti:write"],
        max_concurrent=1,
        intents=[
            IntentCapability(
                pattern="tutoring.*",
                signals=["tutor", "study", "GCSE", "literature", "lesson"],
                confidence=0.95,
                description="Interactive tutoring sessions with criteria-based feedback",
            ),
        ],
        tools=[
            ToolCapability(
                name="tutor_start_session",
                description="Start a new tutoring session — mints session_id, plans first turn.",
                parameters={
                    "type": "object",
                    "properties": {
                        "student_id": {"type": "string"},
                        "topic_override": {"type": "string"},
                    },
                    "required": ["student_id"],
                },
                returns="SessionStart with session_id and plan_summary",
                risk_level="read_only",
                async_mode=False,
                requires_approval=False,
            ),
            # ... three more tools — see §1.6 for the full surface
        ],
    )
```

`AgentManifest` enforces `agent_id` matches `^[a-z][a-z0-9-]*$` (`nats-core/src/nats_core/manifest.py:106-109`); `gcse-tutor` is compliant. `metadata` is capped at 64KB JSON (`manifest.py:147-164`).

**Note on `intents=[]`.** `InMemoryManifestRegistry.register` (line 261-263 of manifest.py) raises `ValueError` if `manifest.intents` is empty. The KV-backed registry path doesn't validate this, but the architect manifest still ships at least one intent. study-tutor must include at least one IntentCapability.

### 1.5 Settings / .env / config

study-tutor must accept the same env shape as specialist-agent. Required vars:

```bash
# NATS connection (AgentConfig — pydantic-settings, env_prefix=AGENT_, nested __)
AGENT_NATS__URL=nats://host.docker.internal:4222
AGENT_NATS__USER=rich
AGENT_NATS__PASSWORD=<RICH_NATS_PASSWORD>     # or via --password-env

# LLM provider — must equal "local" for the GB10 demo
AGENT_MODELS__REASONING_MODEL=local

# llama-swap endpoint
LLM_BASE_URL=http://host.docker.internal:9000
OPENAI_BASE_URL=http://host.docker.internal:9000/v1   # ← Bug #3 — MUST include /v1
OPENAI_API_KEY=not-needed                              # placeholder; llama-swap ignores it
LOCAL_MODEL=gemma4-tutor                              # the fine-tuned tutor model alias

# Optional / per-role
SPECIALIST_AGENT_ID=gcse-tutor                # if you keep the same env name
ANTHROPIC_API_KEY=                            # only if cloud fallback wanted
TAVILY_API_KEY=                               # not used by tutor; carry-over
```

**Bug #3 trap.** `specialist-agent/.env.example` does NOT include `OPENAI_BASE_URL` — this was the cause. `RUNBOOK-jarvis-architect-align-dddsw-demo.md:200` shows the correct value: `OPENAI_BASE_URL=http://host.docker.internal:9000/v1`. study-tutor's `.env.example` must include this line from the start.

**Settings module pattern.** `nats-core/src/nats_core/agent_config.py:78-174` — `AgentConfig(BaseSettings)` with nested `ModelConfig`, `NATSConfig`, optional `GraphitiConfig`. study-tutor can either reuse `AgentConfig` directly (preferred) or write a sibling settings model that exposes the same env shape. Reusing `AgentConfig` is simpler — it is already the contract specialist-agent's CLI is built around, and `from nats_core.agent_config import AgentConfig` is one line.

### 1.6 Capability advertisement (stub mode)

`jarvis/src/jarvis/config/stub_capabilities.yaml` is the bootstrap surface jarvis uses when the live KV is unreachable (DDR-021 soft-fail). To make study-tutor reachable from jarvis on day one — even before its own registration is wired — add a row to this yaml:

```yaml
  - agent_id: gcse-tutor
    role: GCSE Tutor
    description: >
      Interactive tutoring sessions for GCSE English literature. Player-Coach
      orchestration with deterministic session planning and Graphiti-backed
      student model. Best for "start a tutoring session for X", "tutor me on Y",
      "what's the status of session Z". Not for non-tutoring product or
      architecture work.
    capability_list:
      - tool_name: tutor_start_session
        description: Mint a session_id and plan the first turn for a student.
        risk_level: read_only
      - tool_name: tutor_turn
        description: Submit a learner message; receive a Player-Coach tutor reply.
        risk_level: read_only
      - tool_name: tutor_session_status
        description: Read the current state of a tutoring session.
        risk_level: read_only
      - tool_name: tutor_session_end
        description: Mark a session ended; emits session.completed and writes to Graphiti.
        risk_level: mutating
    cost_signal: "low (~$0 per turn — local Gemma)"
    latency_signal: "5-15s per turn"
    last_heartbeat_at: null
    trust_tier: specialist
```

This is a **jarvis repo edit**, not a study-tutor edit. Phase 2's live KV registration supersedes it, but until then the stub is what `dispatch_by_capability` uses if the live path can't bind. The architect/PO entries on lines 4-51 of `stub_capabilities.yaml` show the exact shape.

### 1.7 Phase 1 acceptance criteria (concrete, testable)

1. `study-tutor serve-nats --nats nats://localhost:4222` starts and logs `nats_connect_success` (or equivalent — match the architect's banner: see `nats_adapter.py:99-143`).
2. The agent subscribes to `agents.command.gcse-tutor` via `subscribe_with_reply` (NOT `subscribe`).
3. `nats request agents.command.gcse-tutor '<envelope-json>'` → returns a JSON `ResultPayload` (NOT `{"stream":"AGENTS","seq":N}`) within ~2s for `tutor_start_session`. Validate by:
   ```bash
   nats request agents.command.gcse-tutor "$(jq -nc '{
     message_id:"test-001", timestamp:"2026-05-08T12:00:00Z", version:"1.0",
     source_id:"smoke", event_type:"command", correlation_id:"test-corr",
     payload:{command:"tutor_start_session", args:{student_id:"lilymay"}, correlation_id:"test-corr"}
   }')" --timeout 30s | jq .
   # Expect: {"command":"tutor_start_session","result":{"session_id":"...","plan_summary":{...}},"correlation_id":"test-corr","success":true}
   ```
4. `jarvis chat` (running with live KV resolver) successfully invokes `dispatch_by_capability(tool_name="tutor_start_session", ...)` and gets a valid `ResultPayload`.
5. Wire-tap on `agents.command.>` (NOT `agents.command.gcse-tutor.>` — Bug #4) captures one envelope; wire-tap on `agents.result.>` captures zero (because Phase 1 replies to inbox only). `agents.result.gcse-tutor` will only see traffic when there's no `reply_to` (event-stream consumers).
6. All four commands (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`) round-trip end-to-end.
7. The Open WebUI → NATS Pipe → jarvis → study-tutor → response flow completes a full session (start → turn → end).
8. Existing MCP-path tests still pass (no regressions in `tests/`).

---

## Phase 2 — Live capabilities, registration, heartbeat, lifecycle

### 2.1 Live CapabilitiesRegistry pattern

jarvis's live capability registry is `jarvis/src/jarvis/infrastructure/capabilities_registry.py:227-515` (`LiveCapabilitiesRegistry`). It is a **consumer** of the `agent-registry` KV bucket. study-tutor is a **producer** — it puts its manifest into the bucket.

The producer-side mechanism is `nats-core/src/nats_core/client.py:269-290` — `NATSClient.register_agent(manifest)`:

```python
async def register_agent(self, manifest: AgentManifest) -> None:
    payload_bytes = manifest.model_dump_json().encode()
    # 1. Publish to fleet.register topic
    await self.publish(
        topic=Topics.Fleet.REGISTER, payload=manifest,
        event_type=EventType.AGENT_REGISTER, source_id=manifest.agent_id,
    )
    # 2. Store in KV bucket
    kv = await self._get_kv_bucket()        # binds 'agent-registry'
    await kv.put(manifest.agent_id, payload_bytes)
```

The architect calls this from `nats_adapter.py:107-113` (`await self._client.register_agent(self._manifest)`). study-tutor's `NATSAdapter.start()` should do the same.

**KV bucket details (`nats-infrastructure/kv/kv-definitions.json`):**

| Bucket | TTL | Storage | History | Max value | Purpose |
|---|---|---|---|---|---|
| `agent-registry` | none | file | 5 | 256KB | Manifests; jarvis watches this |
| `agent-status` | none | file | 1 | 64KB | Last-known status per agent |
| `pipeline-state` | 7d | file | 3 | 64KB | Build state per feature_id |
| `jarvis-session` | 1h | memory | 1 | 128KB | Conversation context |

The `agent-registry` bucket is created on first KV access via `nats_core.NATSKVManifestRegistry.create(nc)` (`nats-core/src/nats_core/client.py:448+`). Idempotent.

**TASK-DSR-003 W2 — what changed.** Before W2, jarvis's `dispatch_by_capability` resolver iterated `stub_capabilities.yaml` only. Post-W2 (`50704b6` in jarvis), the resolver consults the live KV first; the stub is the DDR-021 NATS-down soft-fail. study-tutor benefits from this: as soon as it registers itself live, jarvis sees it without a stub yaml edit. **However** — until study-tutor lands Phase 2, the stub yaml remains the only source of truth jarvis sees, hence the §1.6 stub edit is required for Phase 1.

### 2.2 Heartbeat / liveness

Architect heartbeat loop: `nats_adapter.py:217-252`. Subject: `fleet.heartbeat.{agent_id}` resolved via `Topics.Fleet.HEARTBEAT`. Period: `config.heartbeat_interval_seconds` (default 30).

Payload (`nats_adapter.py:238-252`, schema in `nats_core/events/_fleet.py`):

```python
return AgentHeartbeatPayload(
    agent_id=self._manifest.agent_id,
    status="busy" if self._active_tasks > 0 else "ready",
    active_tasks=self._active_tasks,
    queue_depth=0,                # No queue — reject when at capacity
    uptime_seconds=int(time.monotonic() - self._start_time),
)
```

Published via `NATSClient.heartbeat(payload)` (`nats-core/src/nats_core/client.py:319-334`).

**Stale-agent treatment in jarvis.** `LiveCapabilitiesRegistry` has a 30s in-memory cache (ADR-ARCH-017) with KV-watch invalidation (`capabilities_registry.py:351-471`). It does NOT use heartbeat freshness for liveness — agent presence is determined by KV bucket membership. So heartbeats are advisory in the current architecture. (This is a known gap; see Risks below.)

### 2.3 Lifecycle

Boot:
1. Connect to NATS (`NATSClient.connect()` — `client.py:60-75`).
2. Subscribe to command subject (`subscribe_with_reply`).
3. Publish manifest via `register_agent` (publishes to `fleet.register` AND writes to `agent-registry` KV).
4. Start heartbeat loop.
5. Set `_ready` event (gates `on_command` from accepting commands before manifest is published — `command_router.py:378-386`).

Crash recovery / restart:
- KV bucket history is 5 (kv-definitions.json line 16); a re-register replaces the entry. `NATSKVManifestRegistry.register` upserts.
- A jarvis dispatch in flight when the agent dies will fail with `TIMEOUT` (the inbox reply never lands), recorded as `outcome_type=exhausted` after one redirect attempt.
- No durable command queue — `agents.command.<agent_id>` is JetStream-backed but commands are consumed via core NATS subscribe, so a crash before reply means lost work.

Shutdown (`nats_adapter.py:145-215`):
1. Cancel heartbeat task.
2. Unsubscribe from command subject.
3. Wait up to 30s for active tasks to drain.
4. Publish `AgentDeregistrationPayload` to `fleet.deregister` AND delete from `agent-registry` KV (`NATSClient.deregister_agent` — `client.py:292-317`).
5. Drain + close NATS connection.

### 2.4 Phase 2 acceptance criteria

1. On boot, `nats kv get agent-registry gcse-tutor` returns the full manifest JSON with 4 tools.
2. `fleet.register` envelope captured by `nats sub fleet.register` during boot.
3. `fleet.heartbeat.gcse-tutor` envelopes arriving every 30s (configurable).
4. SIGTERM/SIGINT: `fleet.deregister` envelope published; KV row removed; existing in-flight commands complete (subject to 30s timeout) before disconnect.
5. Commands received before manifest publication return error `ResultPayload` with `success=false` and a "not ready" message (`command_router.py:378-386`).
6. jarvis's `LiveCapabilitiesRegistry` picks up `gcse-tutor` within 30s (KV-watch fires `_force_refresh` immediately; the 30s is just the cache TTL ceiling).

---

## Phase 3 — Docker / GB10 deployment

### 3.1 Dockerfile pattern

`specialist-agent/Dockerfile` is 37 lines and demonstrates the canonical sibling-`nats-core` install pattern:

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app

# Install sibling nats-core from build context BEFORE specialist-agent deps
COPY nats-core/ /build/nats-core/
RUN pip install --no-cache-dir /build/nats-core

# Install agent deps (with providers extra)
COPY specialist-agent/pyproject.toml ./
RUN pip install --no-cache-dir '.[providers]'

# Copy app source
COPY specialist-agent/src/ src/
COPY specialist-agent/roles/ roles/

# Editable re-install for the entrypoint
RUN pip install --no-cache-dir -e '.[providers]'

ENTRYPOINT ["specialist-agent"]
CMD ["--help"]
```

**Build context must be the parent dir** so both `nats-core/` and `specialist-agent/` are visible. Same applies to study-tutor.

For study-tutor, the equivalent:

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app

COPY nats-core/ /build/nats-core/
RUN pip install --no-cache-dir /build/nats-core

COPY study-tutor/pyproject.toml ./
RUN pip install --no-cache-dir '.[providers]'

COPY study-tutor/src/ src/
# study-tutor has no roles/ dir at top level; if it does later, add it here

RUN pip install --no-cache-dir -e '.[providers]'

ENTRYPOINT ["study-tutor"]
CMD ["serve-nats", "--help"]
```

Forge uses a multi-stage build with BuildKit named contexts (`forge/Dockerfile`) — overkill for study-tutor at this stage. The specialist-agent pattern is the right baseline.

### 3.2 docker-compose

`specialist-agent/docker-compose.dual-role.yml` (lines 1-49) is the reference. Key features:

- `image: specialist-agent:latest` (built externally; compose only runs)
- `command: serve-nats --nats ${NATS_URL:-...} --role architect`
- `extra_hosts: - "host.docker.internal:host-gateway"` — mandatory on Linux for the container to reach the host's NATS + llama-swap
- All env vars threaded through with `${VAR:-default}` substitution

For study-tutor (`docker-compose.study-tutor.yml`):

```yaml
services:
  gcse-tutor:
    image: study-tutor:latest
    command: serve-nats --nats ${NATS_URL:-nats://host.docker.internal:4222}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      AGENT_NATS__URL: ${NATS_URL:-nats://host.docker.internal:4222}
      AGENT_NATS__USER: ${NATS_USER:-rich}
      AGENT_NATS__PASSWORD: ${NATS_PASSWORD:-}
      AGENT_MODELS__REASONING_MODEL: ${AGENT_MODELS__REASONING_MODEL:-local}
      LLM_BASE_URL: ${TUTOR_LLM_BASE_URL:-http://host.docker.internal:9000}
      OPENAI_BASE_URL: ${TUTOR_OPENAI_BASE_URL:-http://host.docker.internal:9000/v1}  # /v1 mandatory — Bug #3
      OPENAI_API_KEY: ${OPENAI_API_KEY:-not-needed}
      LOCAL_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}
      # Graphiti — same as MCP serve path
      GRAPHITI_HOST: ${GRAPHITI_HOST:-host.docker.internal}
      GRAPHITI_PORT: ${GRAPHITI_PORT:-7687}
      AGENT_GRAPHITI__ENDPOINT: ${AGENT_GRAPHITI__ENDPOINT:-bolt://host.docker.internal:7687}
    restart: unless-stopped
```

The dual-role container co-existence is automatic — both compose stacks point at the same external NATS, llama-swap, and Graphiti. No port conflicts because study-tutor doesn't expose any.

### 3.3 NATS provisioning

study-tutor does NOT manage NATS infrastructure. The `nats-infrastructure` repo owns it. The seven JetStream streams + four KV buckets defined in `nats-infrastructure/streams/stream-definitions.json`:

| Stream | Subjects | Retention | Max age | Why study-tutor cares |
|---|---|---|---|---|
| `PIPELINE` | `pipeline.>` | work | 7d | Forge build queue (irrelevant to tutor) |
| `AGENTS` | `agents.>` | limits | 24h | **Tutor commands + results pass through here** |
| `JARVIS` | `jarvis.>` | limits | 1h | Jarvis-internal (intent classification) |
| `NOTIFICATIONS` | `notifications.>` | work | 24h | Outbound to adapters (irrelevant to tutor today) |
| `SYSTEM` | `system.>` | limits | 1h | Health checks |
| `FLEET` | `fleet.>` | limits | 1h | **Tutor register/heartbeat/deregister pass through here** |
| `FINPROXY` | `finproxy.>` | work | 24h | Project-scoped (unused) |

KV buckets the tutor needs:
- `agent-registry` — its manifest lives here.

`verify-nats.sh` (`nats-infrastructure/scripts/verify-nats.sh`) runs:
1. Health endpoint HTTP 200
2. JetStream initialised (memory/store fields present in `/jsz`)
3. Server name = `ships-computer`, version reported
4. APPMILLA `rich` user can publish (RICH_NATS_PASSWORD env)
5. Placeholder creds rejected (security guard)
6. All 7 streams present (`nats stream info <name>`)

study-tutor's Phase 3 acceptance criteria should depend on the runbook reaffirming all of these are green via `verify-nats.sh`.

### 3.4 Model wiring (llama-swap)

The runbook (`RUNBOOK-jarvis-architect-align-dddsw-demo.md:97`) confirms `gemma4-tutor` exists in llama-swap's `/v1/models` listing as of 2026-05-08:

> `architect-agent`, `qwen36-workhorse`, **`gemma4-tutor`**, `nomic-embed`, `qwen-graphiti`

study-tutor should set `LOCAL_MODEL=gemma4-tutor` in compose env. The langchain-openai client (used inside the tutor's existing LLMClient) reads `OPENAI_BASE_URL` and posts to `<BASE>/chat/completions`. With `OPENAI_BASE_URL=http://host.docker.internal:9000/v1`, this becomes `http://host.docker.internal:9000/v1/chat/completions` — the route llama-swap accepts.

Without `/v1` (Bug #3 surface), it becomes `http://host.docker.internal:9000/chat/completions` — 404.

### 3.5 Phase 3 acceptance criteria

1. `docker compose -f docker-compose.study-tutor.yml up -d` brings the container up.
2. `docker ps --filter name=study-tutor` shows `Up`, healthcheck optional.
3. `docker exec study-tutor-gcse-tutor-1 printenv OPENAI_BASE_URL` returns `http://host.docker.internal:9000/v1` (NOT missing the /v1).
4. `nats kv get agent-registry gcse-tutor --raw` shows the full manifest.
5. From a host shell: a `nats request agents.command.gcse-tutor '<envelope>'` round-trips a `ResultPayload` (full E2E equivalent of the architect's evidence-runbook capture).
6. `jarvis chat` end-to-end demo: "start a tutoring session for Lilymay on Macbeth" → tutor session lands.
7. The Open WebUI → NATS Pipe → jarvis → tutor → reply round-trip works for at least one full conversation arc (start → 3 turns → end).

---

## Bug catalogue (apply from day one)

All four bugs are documented in `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md:60-138`. Bugs #1, #2 are already fixed in the `82ce8a6` snapshot of specialist-agent — study-tutor only needs to NOT regress. Bug #3 is environmental. Bug #4 is a runbook fix.

### Bug #1 — PubAck race on JetStream-backed COMMAND subject (DEMO BLOCKER)

- **Symptom.** Every dispatch records `3 validation errors for ResultPayload: command: Field required ... input_value={'stream':'AGENTS','seq':N}`. Trace `outcome_type=exhausted`. No `AlignmentJudgment` returned to chat.
- **Cause.** `Topics.Agents.COMMAND = "agents.command.{agent_id}"`. The `AGENTS` JetStream stream filters `agents.>` so this subject is JetStream-stored. jarvis publishes via `nats_client.request()` (`jarvis/src/jarvis/tools/dispatch.py:531`) which sets a reply-to inbox. nats-server delivers the JetStream PubAck to that inbox immediately. The architect's actual reply was published by `NATSAdapter` to `agents.result.architect-agent` — not to the inbox. jarvis's request future resolved with the PubAck, `ResultPayload.model_validate_json` failed, attempt recorded as `specialist_error`.
- **Fix (option A — landed).** `NATSAdapter` subscribes via `subscribe_with_reply` (`nats-core/src/nats_core/client.py:177-223`); the `reply_to` is propagated through to `command_router.on_command`; `_publish_result` raw-publishes the `ResultPayload` JSON to the reply inbox via `client.publish_raw(reply_to, ...)` (`command_router.py:1084-1089`). The PubAck still goes to the inbox first, but the raw-publish lands ~milliseconds later, and jarvis's `client.request(...)` future resolves with the raw `ResultPayload` (not the PubAck) because `nats-py` returns the *reply* message, not the publish-ack.
- **Where it must live in study-tutor.** `study-tutor/src/study_tutor/adapters/nats_adapter.py` `start()` method MUST call `subscribe_with_reply` not `subscribe`. The CommandRouter's `_publish_result` MUST consult `reply_to` and call `publish_raw` when set. Citations: `nats_adapter.py:126-128`, `command_router.py:1084-1089`.

### Bug #2 — `command_router.on_command` does not consult `tool_to_command`

- **Symptom.** `agents.result.<agent_id>` shows `{"error":"Command 'architect_align' is not supported. Available commands: ['align','explore','feasibility','greenfield']", "success":false}`. Masked by Bug #1 in current production traces; surfaces immediately once Bug #1 is fixed.
- **Cause.** Pre-fix, `on_command` read `command = cmd_payload.command` literally and looked up in `command_map`. It never consulted `self.tool_to_command`. Meanwhile `on_tool_call` *did* apply the mapping. Asymmetric.
- **Fix (5 lines).** `command_router.py:496-503` — single line in `_dispatch_command`:
  ```python
  command = self.tool_to_command.get(command, command)
  ```
  before the `command_map.get(command)` lookup. Pass-through for canonical verbs (which are absent from `tool_to_command`).
- **Where it must live in study-tutor.** Same place — `_dispatch_command` (or the equivalent named function in study-tutor's router). For study-tutor, decide upfront: are canonical commands `tutor_*` or `start_session`/`tutor_turn`/etc.? The runbook's recommendation is to keep `tool_to_command` either empty (canonical = `tutor_*`) or fully populated, never half. Either way, the alias resolution line goes in.

### Bug #3 — `OPENAI_BASE_URL` missing `/v1` suffix → 404 at the LLM call

- **Symptom.** Direct `nats request` with `command="align"` (bypassing Bug #2) returns `Command 'align' failed: Error code: 404 ... openai.NotFoundError: Error code: 404` from `langchain_openai/chat_models/base.py:_handle_openai_api_error`.
- **Cause.** `LLM_BASE_URL=http://host.docker.internal:9000` was set, but `OPENAI_BASE_URL` was not — and a TASK-LLM-0D07 setdefault did `os.environ.setdefault("OPENAI_BASE_URL", LLM_BASE_URL)`, propagating the no-`/v1` URL into the langchain-openai client. POSTs went to `/chat/completions` (404) instead of `/v1/chat/completions` (200).
- **Fix.** Belt-and-braces:
  1. Add `OPENAI_BASE_URL=http://host.docker.internal:9000/v1` to `study-tutor/.env.example`.
  2. Add `OPENAI_BASE_URL: ${TUTOR_OPENAI_BASE_URL:-http://host.docker.internal:9000/v1}` to `docker-compose.study-tutor.yml` environment block.
  3. (Optional, defence-in-depth) In `study-tutor/src/study_tutor/llm/client.py` (or wherever the BASE_URL is read), if the env var is set without `/v1`, append it.
- **Where it must live in study-tutor.** Both files (`.env.example` and `docker-compose.study-tutor.yml`) must include the explicit `/v1` value. study-tutor's existing LLM client already reads via langchain-openai, so the URL plumbs through automatically once env is right.

### Bug #4 — Wire-tap subject pattern `agents.command.<agent>.>` returns 0 envelopes

- **Symptom.** `nats sub "agents.command.architect-agent.>"` captures nothing during a real dispatch.
- **Cause.** `Topics.Agents.COMMAND = "agents.command.{agent_id}"` — flat, no correlation_id suffix. NATS `>` wildcard requires ≥1 token after, so `agents.command.architect-agent.>` doesn't match `agents.command.architect-agent`.
- **Fix.** Subscribe to `agents.command.>` (or exact `agents.command.gcse-tutor`) for wire-taps. Document this in the study-tutor runbook so the next operator doesn't trip.
- **Where it must live in study-tutor.** Any runbook that includes a wire-tap step (e.g. an evidence-capture script analogous to `specialist-agent/scripts/capture-nats-roundtrip.sh`). The bug is a docs bug, not a code bug.

### Bug #5 (predicted, not from runbook) — `intents=[]` rejection

- **Symptom.** If study-tutor's manifest factory ships with `intents=[]`, the `InMemoryManifestRegistry.register` test path raises `ValueError: at least one intent capability is required` (`nats-core/src/nats_core/manifest.py:261-263`). The KV-backed path doesn't enforce it, but unit tests against `InMemoryManifestRegistry` will fail.
- **Fix.** Always include at least one `IntentCapability` in the manifest. The architect ships 3 (`manifest.py:42-76`), product-owner ships 3 (`manifest.py:243-281`). study-tutor needs at least one — `pattern="tutoring.*"` with relevant signals.
- **Where.** `study-tutor/src/study_tutor/adapters/manifest.py:_tutor_manifest_factory`.

---

## Runbook artifact pattern (study-tutor should adopt)

The jarvis repo uses a three-part artifact pattern that study-tutor should mirror:

| Artifact | Path pattern | Purpose |
|---|---|---|
| `RUNBOOK-{slug}.md` | `docs/runbooks/RUNBOOK-{slug}.md` | The procedure — phases, gates, expected outputs |
| `RESULTS-{slug}-{date}.md` | `docs/runbooks/RESULTS-{slug}-{YYYY-MM-DD}.md` | One per execution; phase × gate × outcome × evidence table |
| `evidence/{slug}/` | `docs/runbooks/evidence/{slug}/` | Chat logs, wire-tap logs, traces, captured payloads |

Reference shape: `jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md` (the procedure) + `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08.md` and `RESULTS-...-followup-post-W2.md` (executions) + `jarvis/docs/runbooks/evidence/dddsw-demo/` (artefacts).

The RESULTS file template at minimum:
- HEAD shas of all participating repos
- "Outcome" line at the top: ✅/⏸/❌
- "Demo blocking?" line
- Phase × Gate table
- Bug catalogue (if any)
- "What's working" narrative
- "Next steps" with concrete fix-and-rerun list

---

## Reconciliation with existing scope doc

For `study-tutor/features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md`:

| Scope doc claim | Verdict | Notes |
|---|---|---|
| "MCPAdapter already contains all the business logic; NATS adapter is purely a transport layer" | ✅ Confirmed | `MCPAdapter.tutor_start_session/tutor_turn/tutor_session_status/tutor_session_end` (`mcp/adapter.py:189,285,358,372`) all return dicts. ResultPayload-compatible. |
| "Specialist-agent's CommandRouter is ~500 lines of generic dispatch tables, mode inference, tool-call subjects. The study-tutor has 4 fixed commands. A `match command:` handler is sufficient for Phase 1." | ⚠️ Needs adjustment | Half-true. Even a simplified handler MUST include the `tool_to_command.get(c, c)` alias resolution (Bug #2 fix). And it MUST honour `reply_to` and raw-publish (Bug #1 fix). The "thin" version is fine if those two are present from day one. |
| Subject contract: `agents.command.gcse-tutor` inbound, `agents.result.gcse-tutor` outbound, `fleet.heartbeat.gcse-tutor` heartbeat | ✅ Confirmed | All from `Topics.Agents.COMMAND/RESULT` and `Topics.Fleet.HEARTBEAT` with `agent_id="gcse-tutor"`. |
| "No fleet registration / heartbeat / Docker in Phase 1" | ❌ Superseded by 2026-05-08 decision | Decision: **registration + heartbeat collapse into Phase 1** (option (b) from prior draft). Stub yaml fallback (option (a)) is dropped. Rationale: lower demo risk, ~30 LoC, architect already ships it. Docker remains Phase 3. See [Decision log](#decision-log-2026-05-08). |
| "AgentManifest publication on startup" (Phase 2) | ✅ Confirmed | Mirror `nats_adapter.py:107-113`. |
| Phase 2 heartbeat at configured interval | ✅ Confirmed | `nats_adapter.py:217-252`. |
| Phase 3 Dockerfile + compose | ✅ Confirmed | `specialist-agent/Dockerfile` + `docker-compose.dual-role.yml` are the templates. |
| "No mode inference — study-tutor has no modes" | ✅ Confirmed | study-tutor has 4 fixed commands; `set_mode_inference()` is not called. |
| "Session state in-memory; in production, only one transport runs per container" | ⚠️ Worth flagging — durability path decided 2026-05-08 | Container restart loses sessions. Pre-demo acceptable (single live conversation). Durability path: **hybrid Graphiti, NOT JetStream KV** — sessions are tutor-domain (already projected via `SessionCompletedEpisode`); KV is fleet-control. Hot path stays in-memory; mid-session async checkpoints to Graphiti; resume-on-boot from Graphiti. TASK-NATS-FU-001, post-demo. See [Decision log](#decision-log-2026-05-08). |
| GuardKit specialist-agent commands at lines 138-205 | ⚠️ Adjust | Those commands invoke specialist-agent's CLI to *plan* the work. They reference `--player-model local` — that requires the architect container to have `OPENAI_BASE_URL` correctly set (Bug #3). Operator must verify env before running these. |
| Risks list (lines 268-277) | ✅ Confirmed | All four risks (MCPAdapter return types, sibling deps in Docker, session loss, agent ID mismatch) are real. The "wire format drifts" risk is mitigated by adopting `ResultPayload` directly — the schema is fixed by `nats-core`. |
| `output_handler_import_path` in `FleetRoleEntry` | ❌ Should be removed for Phase 1 | study-tutor doesn't need a custom output handler (no `SessionResult` shape; handlers return plain dicts). Set to a placeholder import path or skip the field. The architect uses it for `wrap_role_output(...)` which expects an `Evaluation` — irrelevant here. |

---

## Risks and open questions

1. **(High)** No durable retry for in-flight commands. If study-tutor crashes mid-`tutor_turn`, the user gets a `TIMEOUT`. Acceptable for Phase 1-3; a Phase 4 task should evaluate using JetStream pull consumers (forge's pattern, `forge/src/forge/adapters/nats/pipeline_consumer.py:1-39`) for the `agents.command.gcse-tutor` subject so commands persist across restarts. *Open question:* does the team want this for the demo, or post-demo?

2. **(Medium) — DECIDED 2026-05-08.** `SessionStore` is in-process; container restart loses sessions. **Path chosen: hybrid Graphiti** (in-memory hot path + async mid-session checkpoints + resume-on-boot from Graphiti). Rationale: sessions are tutor-domain, not fleet-control; existing `SessionCompletedEpisode` projection extends naturally. Lands as TASK-NATS-FU-001, post-demo. See [Decision log](#decision-log-2026-05-08).

3. **(Medium) — DECIDED 2026-05-08.** Heartbeat published but jarvis presence is from KV-bucket membership, not heartbeat freshness. SIGKILL → stale registry rows → confusing dispatch failures. **Path chosen: D for demo (manual cleanup + runbook documentation), A for post-demo (jarvis-side background reaper based on heartbeat freshness).** Rationale: 3-agent controlled environment doesn't need it now; jarvis is the natural owner because it owns CapabilitiesRegistry. Out of study-tutor's repo entirely. Tracked as TASK-NATS-FU-002 (jarvis repo). See [Decision log](#decision-log-2026-05-08).

4. **(Low)** `ResultPayload.result` is `dict[str, Any]` — pydantic doesn't validate inner shape. study-tutor's existing handler returns are not strictly typed in the schema. *Open question:* is it worth adding study-tutor-specific result models? Recommend NO for Phase 1-3 (matches architect — `_shape_result` falls back to `model_dump()` or pass-through).

5. **(Low)** `gcse-tutor` agent_id is hardcoded in fleet-gateway's `_FLEET_AGENTS` registry per the scope doc. If the team picks a different default, both must be updated atomically. *Open question:* where is this registry actually defined? The scope doc references `fleet-gateway/openwebui/nats_fleet_pipe.py:_FLEET_AGENTS` but I have not inspected that file (out of scope per task). Validate at integration time.

6. **(Operational)** The `nats-infrastructure` repo is the single source of truth for NATS provisioning. study-tutor's runbook should NOT duplicate provisioning steps — link to `nats-infrastructure/scripts/verify-nats.sh` instead.

7. **(Operational)** specialist-agent's `82ce8a6` HEAD includes the Bug #1 + #2 fixes per the runbook; the running container image on GB10 may or may not include them. **The Phase 1 acceptance test for study-tutor must run AGAINST a freshly-built specialist-agent image to confirm the architect-side fix is live.** Otherwise the symptom may look like a study-tutor bug.

---

## Recommended task breakdown

Suggested task IDs / scope. Phase 1 is demo-critical; Phases 2-3 ship before 2026-05-16 ideally.

**Updated 2026-05-08:** Phase 1 now includes live registration + heartbeat (was Phase 2). Stub-yaml fallback removed. Phase 2 reduces to readiness-gating + KV-watch hardening. See [Decision log](#decision-log-2026-05-08).

### Phase 1 — FEAT-NATS-001 (DEMO-CRITICAL, 11 May)

| Task ID | Scope | AC | Size | Phase |
|---|---|---|---|---|
| TASK-NATS-PH1-001 | Add `nats-core` dep to `pyproject.toml` (sibling, editable). Add `study-tutor.adapters` package skeleton. | `from nats_core import Topics` works in repl; `study_tutor.adapters` importable. | S | 1 |
| TASK-NATS-PH1-002 | Create `study_tutor/adapters/manifest.py` with `_tutor_manifest_factory(agent_id)` returning AgentManifest with 4 ToolCapabilities + ≥1 IntentCapability (Bug #5 fix). | `_tutor_manifest_factory("gcse-tutor")` validates; `agent_id` matches kebab-case regex; `len(manifest.tools) == 4`; `len(manifest.intents) >= 1`. | S | 1 |
| TASK-NATS-PH1-003 | Create `study_tutor/roles/registry.py` (mirror specialist-agent's) and `study_tutor/roles/tutor/__init__.py` calling `register_role(...)` with `tool_to_command`. | `get_role("tutor").tool_to_command` returns 4-key dict; `_ensure_roles_registered()` is idempotent. | S | 1 |
| TASK-NATS-PH1-004 | Create `study_tutor/adapters/command_router.py` — minimal CommandRouter with `on_command`, `_dispatch_command` including `tool_to_command.get(c, c)` alias resolution (Bug #2 fix), `_publish_result` honouring `reply_to` (Bug #1 fix). 4 handlers wrapping MCPAdapter methods. | Unit test: dispatch `tutor_start_session` via on_command → MCPAdapter.tutor_start_session called → ResultPayload.success=True. | M | 1 |
| TASK-NATS-PH1-005 | Create `study_tutor/adapters/nats_adapter.py` — NATSAdapter with `start`/`stop` and full lifecycle (subscribe, register, heartbeat loop, deregister). Uses `subscribe_with_reply` (Bug #1 fix). | `await adapter.start()` connects + subscribes + registers in `agent-registry` KV + starts heartbeat; `await adapter.stop()` deregisters + cancels heartbeat + drains + closes cleanly. | M | 1 |
| TASK-NATS-PH1-006 | Wire `register_agent` call in `NATSAdapter.start` (mirror `specialist-agent/src/specialist_agent/adapters/nats_adapter.py:107-113`). Wire heartbeat loop on `fleet.heartbeat.gcse-tutor` (mirror lines 217-252). | `nats kv get agent-registry gcse-tutor` returns full manifest after boot; `nats sub fleet.heartbeat.gcse-tutor` shows period heartbeats. | M | 1 |
| TASK-NATS-PH1-007 | Wire graceful deregistration in `NATSAdapter.stop`. | SIGTERM → KV row removed within 30s. | S | 1 |
| TASK-NATS-PH1-008 | Add `study-tutor serve-nats --nats <url>` CLI subcommand mirroring `specialist-agent/src/specialist_agent/cli/main.py:1712-1769`. Wire AgentConfig env loading + signal handlers. | `study-tutor serve-nats --nats nats://localhost:4222 --help` shows the same flag surface as specialist-agent. | S | 1 |
| TASK-NATS-PH1-009 | Update `study-tutor/.env.example` with required vars including `OPENAI_BASE_URL=http://host.docker.internal:9000/v1` (Bug #3). | grep '^OPENAI_BASE_URL=' .env.example matches `/v1$`. | S | 1 |
| TASK-NATS-PH1-010 | Smoke test: `nats request agents.command.gcse-tutor '<envelope>' --timeout 30s` returns valid `ResultPayload` JSON for all 4 commands. | All 4 round-trip; no `{"stream":"AGENTS"}` PubAck leakage. | M | 1 |
| TASK-NATS-PH1-011 | Live-discovery smoke: jarvis CapabilitiesRegistry sees `gcse-tutor` after boot WITHOUT any stub-yaml entry. | `jarvis chat` resolves `tutor_start_session` via live KV watch; trace `outcome_detail.visited=["gcse-tutor"]`. | S | 1 |
| TASK-NATS-PH1-012 | E2E demo gate: full path Open WebUI → NATS Pipe → jarvis → tutor → session created. | RESULTS file with all phases ✅; AlignmentJudgment-equivalent (`SessionResult`) lands in chat. | L | 1 |

### Phase 2 — FEAT-NATS-002 (parity hardening, post-demo)

| Task ID | Scope | AC | Size | Phase |
|---|---|---|---|---|
| TASK-NATS-PH2-001 | Readiness gating in `on_command` — reject commands before `_ready` is set with `success=false` and a clear error message. | Smoke: send command between `start()` invoked and `_ready.set()` → error result with "not ready" message. | S | 2 |
| TASK-NATS-PH2-002 | Add `NATSKVManifestRegistry`-backed Phase 2 KV-watch test so jarvis sees tutor reg/dereg events synchronously. | Test: tutor SIGTERM → jarvis CapabilitiesRegistry sees deregistration within 5s; subsequent dispatch returns `unresolved`, not timeout. | M | 2 |
| TASK-NATS-PH2-003 | Document the "stale registry entry" symptom + manual cleanup command (`nats kv del agent-registry <id>`) in study-tutor's runbook. Reaper itself stays in jarvis backlog (TASK-NATS-FU-002). | Runbook section "Known issue: stale registry entries" with reproduction + cleanup. | S | 2 |

### Phase 3 — FEAT-NATS-003 (Docker, GB10)

| Task ID | Scope | AC | Size | Phase |
|---|---|---|---|---|
| TASK-NATS-PH3-001 | Write `study-tutor/Dockerfile` mirroring specialist-agent's pattern (sibling nats-core + editable install). | `docker build -f study-tutor/Dockerfile .` from parent dir succeeds. | M | 3 |
| TASK-NATS-PH3-002 | Write `study-tutor/docker-compose.study-tutor.yml` with full env block including `OPENAI_BASE_URL` /v1. | `docker compose -f docker-compose.study-tutor.yml up -d` brings tutor up; reachable from host NATS. | M | 3 |
| TASK-NATS-PH3-003 | Add `scripts/docker-build.sh` (mirror specialist-agent's). | One-line build invocation; idempotent. | S | 3 |
| TASK-NATS-PH3-004 | Write `RUNBOOK-study-tutor-nats-fleet-demo.md` and a `RESULTS-...-{date}.md` template under `docs/runbooks/`. Mirror jarvis's runbook structure. Use `agents.command.>` (NOT `.>` suffix) for wire taps (Bug #4). | Runbook reads end-to-end without ambiguity; wire-tap subject is correct. | M | 3 |
| TASK-NATS-PH3-005 | Smoke test on GB10: full E2E from Open WebUI through containerised tutor. | RESULTS file with all phases ✅. | L | 3 |

### Risk-tracked follow-ups (post-demo)

| Task ID | Scope |
|---|---|
| TASK-NATS-FU-001 | **Hybrid Graphiti session durability.** Keep in-memory `SessionStore` as active-turn hot path; add async mid-session checkpoints to Graphiti every N turns; resume-on-boot by querying Graphiti for the agent's active sessions. Reuses existing `SessionCompletedEpisode` projection. NOT JetStream KV — sessions are tutor-domain, not fleet-control. |
| TASK-NATS-FU-002 | **Stale-agent reaper (jarvis repo, not study-tutor).** Background coroutine in jarvis polls heartbeat freshness on `fleet.heartbeat.<agent_id>`; deletes `agent-registry` rows whose last heartbeat is older than threshold. Approach A (background polling), not B (lazy dispatch-time check). |
| TASK-NATS-FU-003 | Add an evidence-capture script (`scripts/capture-nats-roundtrip.sh`) analogous to specialist-agent's. |
| TASK-NATS-FU-004 | Durable retry for in-flight commands: evaluate JetStream pull consumers (forge's pattern, `forge/src/forge/adapters/nats/pipeline_consumer.py:1-39`) for `agents.command.gcse-tutor` so commands survive tutor crashes. |
| TASK-NATS-FU-005 | **Correlation-id idempotency (only if observed).** Contingent follow-up: if duplicate delivery is observed in a real runbook, add a recent-correlation_id cache to study-tutor's CommandRouter (Option A from ASSUM-007 resolution). Per 2026-05-08 decision, the demo runs without tutor-side dedup; jarvis owns the "MUST NOT duplicate-dispatch" contract. |

---

## Appendix A — Quick reference: file:line citations used

### Specialist-agent (canonical agent-side reference)
- NATSAdapter: `specialist-agent/src/specialist_agent/adapters/nats_adapter.py:42-312`
- subscribe_with_reply call site: `nats_adapter.py:115-133`
- CommandRouter: `specialist-agent/src/specialist_agent/adapters/command_router.py:161-1126`
- on_command: `command_router.py:328-406`
- Bug #2 fix line: `command_router.py:496-503`
- Bug #1 fix in _publish_result: `command_router.py:1052-1103`
- Architect role registration: `specialist-agent/src/specialist_agent/roles/architect/__init__.py:32-47`
- Manifest factory: `specialist-agent/src/specialist_agent/adapters/manifest.py:23-218`
- Role registry: `specialist-agent/src/specialist_agent/roles/registry.py:18-54`
- CLI serve-nats: `specialist-agent/src/specialist_agent/cli/main.py:1515-1670, 1712-1769`
- Dockerfile: `specialist-agent/Dockerfile:1-37`
- Compose: `specialist-agent/docker-compose.dual-role.yml:1-49`
- .env.example: `specialist-agent/.env.example:1-88`
- nats-evidence-runbook: `specialist-agent/scripts/nats-evidence-runbook.md`

### Jarvis (dispatcher, runbooks)
- dispatch_by_capability: `jarvis/src/jarvis/tools/dispatch.py:451-658`
- Subject formatted at: `dispatch.py:525`
- request call site: `dispatch.py:531`
- ResultPayload parse: `dispatch.py:582`
- LiveCapabilitiesRegistry: `jarvis/src/jarvis/infrastructure/capabilities_registry.py:227-515`
- StubCapabilitiesRegistry: `capabilities_registry.py:518-593`
- Fleet registration (jarvis self): `jarvis/src/jarvis/infrastructure/fleet_registration.py`
- Stub yaml: `jarvis/src/jarvis/config/stub_capabilities.yaml`
- Runbook: `jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md`
- Bug catalogue: `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md:60-138`

### nats-core (contract)
- Topics: `nats-core/src/nats_core/topics.py:1-191`
- Subject constants: `topics.py:95-106` (Agents), `108-115` (Fleet)
- AgentManifest: `nats-core/src/nats_core/manifest.py:81-164`
- ToolCapability/IntentCapability: `manifest.py:22-79`
- CommandPayload/ResultPayload: `nats-core/src/nats_core/events/_agent.py:133-189`
- NATSClient: `nats-core/src/nats_core/client.py:35-433`
- subscribe_with_reply: `client.py:177-223`
- publish_raw: `client.py:225-243`
- register_agent: `client.py:269-290`
- heartbeat: `client.py:319-334`
- AgentConfig: `nats-core/src/nats_core/agent_config.py:78-174`

### Forge (additional fleet reference)
- Inbound pipeline consumer: `forge/src/forge/adapters/nats/pipeline_consumer.py` (heavyweight pattern; not needed for tutor)
- Fleet publisher: `forge/src/forge/adapters/nats/fleet_publisher.py:1-40` (similar to specialist-agent's adapter but module-level functions, not a class). study-tutor should follow specialist-agent's class-based pattern; forge's flatter structure is forge-specific.

### nats-infrastructure (provisioning)
- Stream definitions: `nats-infrastructure/streams/stream-definitions.json`
- KV definitions: `nats-infrastructure/kv/kv-definitions.json`
- Verify script: `nats-infrastructure/scripts/verify-nats.sh:266-294` (the 7-streams check)

### study-tutor (target)
- MCPAdapter: `study-tutor/src/study_tutor/mcp/adapter.py:127-510`
- Handler entry points: `mcp/adapter.py:189` (start), `285` (turn), `358` (status), `372` (end)
- MCP server tool registration: `study-tutor/src/study_tutor/mcp/server.py:19-58`
- pyproject.toml deps: `study-tutor/pyproject.toml:11-79`
- SessionStore: `study-tutor/src/study_tutor/session/tutor_session.py:38-68` (in-memory; docstring at lines 1-5 states original Graphiti-serialisation intent)
- SessionCompletedEpisode projection: `study-tutor/src/study_tutor/tutoring/session_end.py:243`
- Existing scope doc: `study-tutor/features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md`
- Architecture decision: `study-tutor/docs/talks/openwebui-nats-pipe-architecture.md`

---

## Decision log (2026-05-08)

Three decisions taken after the initial review draft was reviewed by the project lead. Each supersedes prior recommendations elsewhere in this document.

### Decision 1 — Phase 1 includes live registration + heartbeat

**Context.** Original scope doc deferred fleet registration / heartbeat / lifecycle to Phase 2. Phase 1's "thin dispatcher" framing relied on a `stub_capabilities.yaml` row in jarvis as the discovery fallback.

**Options weighed.**
- **(a) Stub-yaml fallback in Phase 1.** Add a `gcse-tutor` row to `jarvis/src/jarvis/config/stub_capabilities.yaml` so jarvis can dispatch before tutor implements registration.
- **(b) Collapse registration + heartbeat into Phase 1.** Implement live KV registration + heartbeat loop from day one (~30 LoC; the architect already ships them).

**Decision: (b).**

**Rationale.**
- Demo deadline 2026-05-11 leaves no margin for "registration broke after switching off the stub" surprises.
- Stub yaml introduces a discovery path that only exists for ~3 days, then must be torn down — adds work, not removes it.
- Architect's `nats_adapter.py:107-143, 217-252` is a copy-paste-and-rename template; risk is low.
- Eliminates a cross-repo dependency (jarvis PR for stub yaml + later removal).

**Consequences.**
- Phase 1 grows from 10 to 12 tasks (TASK-NATS-PH1-006 register_agent, TASK-NATS-PH1-007 deregister, TASK-NATS-PH1-011 live-discovery smoke, TASK-NATS-PH1-008 stub yaml dropped).
- Phase 2 reduces to readiness-gating + KV-watch hardening (3 tasks).
- Reconciliation table row "No fleet registration / heartbeat / Docker in Phase 1" → ❌ Superseded.

### Decision 2 — Session durability uses hybrid Graphiti, not JetStream KV

**Context.** `SessionStore` is in-memory ([`session/tutor_session.py:38-68`](../../src/study_tutor/session/tutor_session.py#L38-L68)). Container restart loses all active sessions. The original review flagged this as TASK-NATS-FU-001 with JetStream KV (`tutor-sessions` bucket) as the proposed fix.

**Options weighed.**

| | Graphiti (hybrid) | JetStream KV (`tutor-sessions`) |
|---|---|---|
| **Pros** | Already integrated. [`session/tutor_session.py:1-5`](../../src/study_tutor/session/tutor_session.py#L1-L5) docstring states original design intent. [`tutoring/session_end.py:243`](../../src/study_tutor/tutoring/session_end.py#L243) already projects to `SessionCompletedEpisode`. Temporal model fits turns. Cross-session continuity ("what we covered last week"). Single source of truth for tutor data. | Already-required infra (NATS is on critical path). Fast K/V (no LLM in write path). Same-fabric ops story with `agent-registry`. TTL + watch semantics. |
| **Cons** | LLM-driven entity extraction — too slow for per-turn hot path. Needs mid-session checkpointing layer (currently end-of-session only). Heavier infra dependency. | Parallel persistence path duplicates Graphiti for tutor-domain data. Plain blob storage loses queryability. Sessions still land in Graphiti at end (existing pattern), so KV would be interim only. Two stores to keep consistent. ~64KB per-key cap. |

**Decision: hybrid Graphiti.**

**Rationale.**
- Sessions are tutor-domain, not fleet-control. KV is the wrong layer.
- Existing `SessionCompletedEpisode` projection extends naturally — "checkpoint" is the same shape as the existing end-of-session writeback, just earlier and async.
- Original design intent (per the docstring) was already Graphiti-serialisation; the runbook's "back with KV" suggestion was a fleet-pattern reflex, not a tutor-domain decision.

**Architecture.**
- **Hot path:** in-memory `SessionStore` stays — no I/O on the per-turn critical path.
- **Mid-session checkpoints:** every N turns (configurable; suggest N=3 to start), async write to Graphiti as a `SessionInProgressEpisode` (new shape, mirrors `SessionCompletedEpisode`).
- **End-of-session:** existing `SessionCompletedEpisode` projection, unchanged.
- **Resume-on-boot:** on container start, query Graphiti for episodes tagged `agent_id=gcse-tutor` with `status=active`, hydrate `SessionStore`.

**Consequences.**
- TASK-NATS-FU-001 reframed: not "KV-back SessionStore" but "hybrid Graphiti durability".
- Phase 1-3 ship with in-memory only; demo runs on a single live conversation, restart loss is acceptable.
- Minor schema work post-demo: a `SessionInProgressEpisode` projection.

### Decision 3 — Stale-agent reaper deferred to jarvis post-demo

**Context.** jarvis's CapabilitiesRegistry reads from `agent-registry` KV (no TTL). Heartbeats publish to `fleet.heartbeat.<agent_id>`, but jarvis presence detection is currently from KV-bucket membership, not heartbeat freshness. SIGKILL → stale registry rows → confusing "advertised but unresponsive" dispatch failures.

**Options weighed.**

| Approach | Pros | Cons |
|---|---|---|
| **A. jarvis-side background reaper** — coroutine polls heartbeat freshness, deletes stale KV rows | Fixes root cause. Centralised policy. Works for all agents. | Cross-repo (jarvis owns it). Adds jarvis stateful behavior. |
| **B. jarvis-side lazy check at dispatch time** — check freshness before dispatching | Simpler. No background process. | Stale rows still pollute the registry. Operator confusion remains. |
| **C. Agent-side TTL on KV row** — short-TTL writes, refreshed each heartbeat | Idiomatic Etcd/Consul pattern. No jarvis change. | Mixes liveness into manifest persistence (manifests are *meant* to be durable). Changes registry semantics. |
| **D. Skip for demo** — manual `nats kv del agent-registry <id>`, document in runbook | Zero work. 3-agent controlled environment doesn't need it. | Punts the problem. |

**Decision: D for demo, A for post-demo (jarvis-owned).**

**Rationale.**
- 3-agent controlled environment: stale rows are rare and trivially recoverable (`nats kv del`).
- jarvis is the natural owner — it owns CapabilitiesRegistry, reads the bucket, knows the dispatch model. study-tutor shouldn't bear this concern.
- C rejected: registry rows are *manifests* (stable agent identity + capabilities). Mixing liveness into manifest persistence muddies the data model. Better to keep durable manifests + a separate liveness layer.
- B rejected: stale rows still appear in `nats kv ls agent-registry`, confusing operators and runbook authors. A is only marginally more code.

**Consequences.**
- Zero study-tutor code change for demo.
- Phase 2 adds TASK-NATS-PH2-003 (runbook-only documentation of the symptom + cleanup command).
- TASK-NATS-FU-002 stays in the post-demo backlog, scope clarified to "background polling reaper, jarvis repo".
