# NATS Fleet Integration — Feature Scope & Build Plan

**Project:** study-tutor
**Date:** 7 May 2026 (updated same day after fleet-gateway repo creation)
**Driver:** DDD Southwest demo (16 May) + Gemma 4 Good Hackathon (18 May)
**Dependencies:**
- `nats-core` — shared contract library (Pydantic models, NATSClient, Topics)
- `specialist-agent` — `serve-nats` reference implementation
- `fleet-gateway` — Open WebUI Pipe Function + Reachy Mini Scholar profile
- `jarvis` — intent router; dispatches structured `CommandPayload` to the study-tutor via NATS (the primary consumer of this work)

**Architecture decision:** `docs/talks/openwebui-nats-pipe-architecture.md`

---

## Context

The study-tutor currently serves via MCP (stdio transport) through Claude Desktop. The fleet is moving to Open WebUI + NATS Pipe Functions as the user-facing surface (see architecture decision doc). The study-tutor needs a `serve-nats` mode so it can receive commands from the NATS bus and return results — making it a first-class fleet participant alongside the specialist-agent's architect and product-owner roles.

The study-tutor's `MCPAdapter` already contains all the business logic: session creation with deterministic planning, tutor turns with Player-Coach orchestration, session status reads, and session end with Graphiti write-back. The NATS adapter is purely a transport layer — it calls the same methods through a different protocol.

### Who consumes this work

The primary consumer is **Jarvis** (the fleet's intent router). The user types a message in Open WebUI → the Pipe Function sends it to Jarvis → Jarvis's supervisor understands the intent and calls `dispatch_by_capability(agent_id="gcse-tutor", command="tutor_turn", ...)` → the study-tutor receives the structured `CommandPayload` on `agents.command.gcse-tutor`.

The study-tutor's NATS adapter doesn't care who publishes the `CommandPayload` — it just handles whatever arrives on its topic. Today that's Jarvis. Post-hackathon, Reachy Mini Scholar could also publish directly (voice-transcribed commands). The adapter is consumer-agnostic by design.

**Jarvis scope:** `jarvis/features/feat-jarvis-006-nats-chat-gateway/nats-chat-gateway-scope-and-build-plan.md`
**Pipe Function:** `fleet-gateway/openwebui/nats_fleet_pipe.py` (sends all messages to Jarvis, not to agents directly)
**Scholar (hackathon):** reads directly from Graphiti (no NATS needed). Post-hackathon: NATS gateway through Jarvis.

---

## Reference implementation

The specialist-agent's NATS stack is the template:

| Component | Path | Purpose |
|---|---|---|
| `NATSAdapter` | `specialist-agent/src/specialist_agent/adapters/nats_adapter.py` | Lifecycle manager: connect, manifest, heartbeat, shutdown |
| `CommandRouter` | `specialist-agent/src/specialist_agent/adapters/command_router.py` | Routes `CommandPayload` → core API functions |
| `manifest.py` | `specialist-agent/src/specialist_agent/adapters/manifest.py` | Builds `AgentManifest` per role |
| `result_wrapper.py` | `specialist-agent/src/specialist_agent/adapters/result_wrapper.py` | Shapes session results for NATS publishing |
| CLI `serve-nats` | `specialist-agent/src/specialist_agent/cli/main.py` (bottom) | Wires config → manifest → adapter → event loop |
| Docker compose | `specialist-agent/docker-compose.dual-role.yml` | Dual-role deployment on GB10 |
| NATS subjects contract | `specialist-agent/docs/design/contracts/API-nats-subjects.md` | Subject naming, message schemas |

The fleet-gateway repo contains the consumers:

| Component | Path | Purpose |
|---|---|---|
| NATS Pipe Function | `fleet-gateway/openwebui/nats_fleet_pipe.py` | Open WebUI → NATS gateway (sends all messages to Jarvis) |
| Scholar profile | `fleet-gateway/reachy/external_content/` | Reachy Mini companion (reads Graphiti; future NATS publisher) |
| Gateway architecture | `fleet-gateway/docs/architecture.md` | Gateway design principles and topology |

---

## Command surface

Four commands, mapping 1:1 to the existing MCP tools:

| NATS command | MCP tool | Required args | What it does |
|---|---|---|---|
| `start_session` | `tutor_start_session` | `text_name`, `focus_aos` (optional: `learner_name`) | Mints session_id, runs deterministic planner, returns session plan |
| `tutor_turn` | `tutor_turn` | `session_id`, `user_message` | Player-Coach loop → Socratic response + Coach quality gate |
| `session_status` | `tutor_session_status` | `session_id` | Pure read of current session state |
| `end_session` | `tutor_session_end` | `session_id` | DDR-003 session.completed event + F3 Graphiti write |

NATS subjects (using nats-core `Topics.resolve()`):
- Inbound: `agents.command.gcse-tutor`
- Outbound: `agents.result.gcse-tutor`
- Heartbeat: `fleet.heartbeat.gcse-tutor`

---

## Three phases

### Phase 1 — Minimum viable NATS adapter (DEMO-CRITICAL)

**Deadline:** 11 May 2026 (before video shoot window)
**Estimate:** 4–6 hours
**Feature ID:** `FEAT-NATS-001`

Add `nats-core` dependency. Write a thin NATS adapter that subscribes to the command subject, dispatches to `MCPAdapter` methods, and publishes results. Add `study-tutor serve-nats` CLI command. No fleet registration, no heartbeat, no Docker — just the command/result loop working end-to-end on GB10.

**Acceptance criteria:**
- `study-tutor serve-nats --nats nats://localhost:4222` starts and subscribes
- A `CommandPayload` with `command: "start_session"` returns a `ResultPayload` with session_id and plan
- A `CommandPayload` with `command: "tutor_turn"` returns the Player-Coach response
- A `CommandPayload` with `command: "end_session"` triggers session.completed and Graphiti write
- The Pipe Function in `fleet-gateway/openwebui/nats_fleet_pipe.py` can complete a full tutoring session (start → turns → end) via Open WebUI
- All existing MCP-path tests still pass (no regressions)

**What this does NOT include:**
- Fleet registration / heartbeat / deregistration (Phase 2)
- Docker deployment (Phase 3)
- Concurrency control beyond the existing `MCPAdapter` session store isolation
- Mode inference (study-tutor has no modes — it's always "tutor")
- The Pipe Function itself (already written in fleet-gateway; this feature is the agent-side NATS subscriber)

### Phase 2 — Fleet registration and lifecycle

**Deadline:** Post-demo (stretch)
**Estimate:** 2 hours
**Feature ID:** `FEAT-NATS-002`

Add `AgentManifest` publication on startup, heartbeat loop at configured interval, graceful deregistration on shutdown. Follows the specialist-agent's `NATSAdapter` lifecycle exactly. Adds readiness gating (reject commands before manifest is published).

**Acceptance criteria:**
- `fleet.register` receives an `AgentManifest` on startup
- `fleet.heartbeat.gcse-tutor` publishes at configured interval
- `fleet.deregister` fires on SIGTERM/SIGINT
- Commands received before manifest publication return an error `ResultPayload`

### Phase 3 — Docker deployment on GB10

**Deadline:** Post-demo (stretch)
**Estimate:** 1–2 hours
**Feature ID:** `FEAT-NATS-003`

Write `Dockerfile` and `docker-compose.study-tutor.yml` for deployment on GB10, following the specialist-agent's container pattern. The study-tutor runs as `study-tutor serve-nats --nats nats://localhost:4222` inside a container alongside the specialist-agent containers. Environment variables for LLM provider, Graphiti endpoint, etc. follow the same `.env` pattern.

**Acceptance criteria:**
- `docker compose -f docker-compose.study-tutor.yml up` starts the tutor on GB10
- Container connects to NATS on GB10 (localhost or host.docker.internal)
- Container connects to llama-swap on GB10 for inference
- Container connects to Graphiti (via Tailscale to Synology) for student model reads/writes
- Full tutoring session completes end-to-end through Docker

---

## GuardKit commands

### Phase 1 — FEAT-NATS-001

**Feature spec** (generates BDD scenarios, assumptions, task breakdown):

```bash
# Option A: Product-owner extract against full docs tree
specialist-agent run \
    --role product-owner \
    --mode extract \
    --docs /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/ \
    --output /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase1/ \
    --player-model local \
    --verbose
```

```bash
# Option B: Architect greenfield with targeted scope (preferred — tighter scope)
specialist-agent run \
    --role architect \
    --mode greenfield \
    --docs /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/ \
    --scope "Phase 1 NATS adapter: add nats-core dependency, write thin command dispatcher that routes NATS CommandPayload to existing MCPAdapter methods (start_session, tutor_turn, session_status, end_session), add serve-nats CLI command. Reference implementation: specialist-agent/src/specialist_agent/adapters/. Consumer: fleet-gateway/openwebui/nats_fleet_pipe.py (the Open WebUI Pipe Function that publishes to agents.command.gcse-tutor). No fleet registration, no heartbeat, no Docker. Scope doc at features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md" \
    --output /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase1/ \
    --player-model local \
    --no-web-search \
    --skip-confirmation \
    --verbose
```

**Feature plan** (generates task breakdown from the feature spec):

```bash
# Run after feature-spec is reviewed and approved
specialist-agent run \
    --role product-owner \
    --mode evolve \
    --docs /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/ \
    --build-plan /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase1/ \
    --output /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase1/ \
    --player-model local \
    --verbose
```

### Phase 2 — FEAT-NATS-002

```bash
specialist-agent run \
    --role architect \
    --mode greenfield \
    --docs /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/ \
    --scope "Phase 2 fleet lifecycle: add AgentManifest publication on startup, heartbeat loop, graceful deregistration on shutdown, readiness gating. Follows specialist-agent NATSAdapter lifecycle exactly. Builds on Phase 1 adapter. Scope doc at features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md" \
    --output /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase2/ \
    --player-model local \
    --no-web-search \
    --skip-confirmation \
    --verbose
```

### Phase 3 — FEAT-NATS-003

```bash
specialist-agent run \
    --role architect \
    --mode greenfield \
    --docs /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/ \
    --scope "Phase 3 Docker deployment: Dockerfile and docker-compose for study-tutor on GB10. Follows specialist-agent docker-compose.dual-role.yml pattern. Connects to NATS, llama-swap, and Graphiti on GB10. Scope doc at features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md" \
    --output /Users/richardwoollcott/Projects/appmilla_github/study-tutor/features/nats-fleet-integration-phase3/ \
    --player-model local \
    --no-web-search \
    --skip-confirmation \
    --verbose
```

---

## Key context files for Claude Code

When spinning up a Claude Code session to implement Phase 1, these files provide the necessary context:

### Study-tutor (this repo — the agent being modified)

| File | Why |
|---|---|
| This document | Scope, phasing, command surface |
| `src/study_tutor/mcp/adapter.py` | The business logic being exposed via NATS — all four handler methods |
| `src/study_tutor/cli/main.py` | Current `serve` command — shows how MCPAdapter is constructed with Graphiti wiring, orchestrator factory, event bus |

### Specialist-agent (reference implementation)

| File | Why |
|---|---|
| `src/specialist_agent/adapters/nats_adapter.py` | Reference: lifecycle manager pattern |
| `src/specialist_agent/adapters/command_router.py` | Reference: command dispatch pattern (Phase 1 uses a simplified version) |
| `src/specialist_agent/cli/main.py` (`serve-nats` section) | Reference: CLI wiring — config → manifest → adapter → event loop |
| `docs/design/contracts/API-nats-subjects.md` | NATS subject naming contract |

### nats-core (shared contract library)

| File | Why |
|---|---|
| `src/nats_core/topics.py` | `Topics.resolve()` — the authoritative subject registry |
| `src/nats_core/events/_agent.py` | `CommandPayload`, `ResultPayload` — the wire format |

### fleet-gateway (the consumer of this work)

| File | Why |
|---|---|
| `openwebui/nats_fleet_pipe.py` | The Pipe Function that will publish to `agents.command.gcse-tutor` — defines the wire format the study-tutor must respond to |
| `reachy/external_content/external_tools/query_student_model.py` | Scholar's Graphiti reader — reads the same student model the tutor writes to; confirms the data shape contract |
| `docs/architecture.md` | Gateway design principles — confirms gateways are thin, agents own all logic |

### Architecture decision

| File | Why |
|---|---|
| `docs/talks/openwebui-nats-pipe-architecture.md` | The architecture decision driving this work — Open WebUI + NATS replaces Claude Desktop + MCP |

---

## Design decisions

| Decision | Choice | Reasoning |
|---|---|---|
| **Adapter pattern** | Thin dispatcher (Phase 1), full lifecycle (Phase 2) | Demo deadline demands speed. The specialist-agent's `CommandRouter` is ~500 lines of generic dispatch tables, mode inference, tool-call subjects. The study-tutor has 4 fixed commands. A `match command:` handler is sufficient for Phase 1 and can be refactored to the full pattern post-demo. |
| **Agent ID** | `gcse-tutor` | Lowercase kebab-case per `AgentManifest` convention. Matches the llama-swap model id pattern. Must match the `nats_agent_id` in `fleet-gateway/openwebui/nats_fleet_pipe.py`'s `_FLEET_AGENTS` registry. |
| **MCPAdapter reuse** | NATS adapter holds a reference to `MCPAdapter` and delegates | The business logic lives in MCPAdapter. Duplicating it would create drift. The NATS adapter is a transport layer, not a second implementation. |
| **Session state** | Shared in-memory `SessionStore` between MCP and NATS paths | Sessions are mutable state; both transports must see the same store. In production (Phase 3, Docker), only one transport runs per container instance. During development, both may coexist for testing. |
| **nats-core version** | Same version as specialist-agent (editable install from sibling) | Wire contract must be identical across all fleet participants. |
| **No mode inference** | Study-tutor has no modes — every command is a tutor command | The specialist-agent's mode inference handles "is this a greenfield or an align?" ambiguity. The study-tutor doesn't have that ambiguity. |
| **Gateway code lives in fleet-gateway, not here** | The Pipe Function and Scholar profile are in `fleet-gateway/` | One gateway per modality, not per agent. The study-tutor owns the NATS subscriber; the gateway owns the NATS publisher. Clean separation of concerns. |

---

## Risks

| Risk | Mitigation |
|---|---|
| MCPAdapter methods have MCP-specific assumptions (e.g. return types) | Phase 1 task includes a review of handler return types to ensure they serialise cleanly into `ResultPayload.result` (dict). The handlers already return dicts for MCP; should be compatible. |
| nats-core sibling dependency causes import issues in Docker | Phase 3 addresses this. specialist-agent already solved it (see `TASK-MDF-DKRF-dockerfile-rewrite-for-sibling-nats-core.md`). |
| Session state lost on container restart | Known limitation. In-memory `SessionStore` is ephemeral. Post-demo, sessions should be backed by JetStream KV or Graphiti. |
| NATS not running on GB10 during demo | Pre-flight check: `nats-server` must be running. Add to dry-run checklist in demo strategy doc. |
| Pipe Function wire format drifts from study-tutor response shape | The Pipe Function (`fleet-gateway/openwebui/nats_fleet_pipe.py`) and the study-tutor NATS adapter must agree on `ResultPayload.result` structure. Phase 1 smoke test should exercise the full loop: Open WebUI → Pipe Function → NATS → study-tutor → NATS → Pipe Function → Open WebUI. |
| Agent ID mismatch between Pipe Function and study-tutor | The Pipe Function's `_FLEET_AGENTS` registry uses `nats_agent_id: "gcse-tutor"`. The study-tutor's `serve-nats` must subscribe to `agents.command.gcse-tutor`. Test this in the Phase 1 smoke. |

---

*Drafted: 7 May 2026*
*Updated: 7 May 2026 — added fleet-gateway references; updated consumer from Pipe Function to Jarvis (v4 architecture)*
*For: Claude Code implementation session (Phase 1 target: 11 May)*
