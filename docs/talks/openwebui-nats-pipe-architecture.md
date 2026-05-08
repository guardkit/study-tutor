# Open WebUI + NATS via Jarvis — Architecture Decision

**Status:** Agreed (7 May 2026, evolved same day through v1→v4)
**Scope:** Fleet-wide — affects DDD Southwest demo, Gemma 4 Good Hackathon, and long-term fleet UI surface
**Related:** `ddd-southwest-demo-strategy.md` (v4), `distributed_agent_orchestration_architecture.md`, DECISION-DF-001
**Companion scopes:**
- `jarvis/features/feat-jarvis-006-nats-chat-gateway/` — Jarvis serve-nats
- `study-tutor/features/nats-fleet-integration/` — study-tutor serve-nats
- `fleet-gateway/` — Pipe Function + Reachy Scholar profile

---

## The decision in one paragraph

Replace Claude Desktop as the user-facing surface for the software factory with Open WebUI, connected to **Jarvis** (the fleet's intent router) via a NATS Pipe Function. The Pipe Function sends every user message to Jarvis over NATS. Jarvis's supervisor — powered by Qwen3.6-35B-A3B (3B active params via llama-swap) — understands the user's intent, constructs structured `CommandPayload` messages, and dispatches to the right specialist agent (architect, product-owner, study-tutor, forge) over NATS. The specialist agents receive clean, structured arguments — exactly as their `CommandRouter` was designed to handle. Jarvis replaces Claude in the routing role; Open WebUI replaces Claude Desktop as the UI shell. The Pipe Function is ~60 lines of Python. All intelligence lives in Jarvis and the agents.

---

## Why

### The Claude Desktop problem

Claude Desktop makes the DDD audience think "he's just using Claude." The actual intelligence — fine-tuned models, Player-Coach loops, Graphiti — is invisible behind a Claude-branded shell.

### Why not MCP via Open WebUI?

MCP tool calling requires the model to output structured function-call JSON. The fine-tuned specialist models weren't trained for tool calling. A separate routing model would be needed. And MCP is a second transport alongside NATS.

### Why not a Pipe Function manifold (individual agents)?

The v3 approach exposed each agent as a separate model in the Open WebUI dropdown. This created a wire format mismatch: the specialist-agent's `CommandRouter` expects structured arguments (`context`, `proposal`, `question` for align; `docs_path`, `scope` for greenfield), but a chat UI sends natural language. Something needs to bridge that gap.

### Why Jarvis?

Jarvis is that bridge — and it already exists. On 4 May 2026, Jarvis ran on GB10 with `qwen36-workhorse` (Qwen3.6 via llama-swap), successfully called `queue_build` with structured arguments, and completed a full NATS round-trip to Forge. The supervisor, dispatch infrastructure, fleet registration, and capabilities registry are all proven (FEAT-JARVIS-004/005, all tasks complete).

Jarvis replaces Claude in the same role Claude played in Claude Desktop: receive natural language, understand intent, construct structured tool calls, dispatch. The difference: Jarvis runs on the GB10 using a 3B-active-parameter local model, not a cloud API.

---

## Architecture

```
Browser (Mac / any device)
    │
    │ Tailscale (or LAN)
    ▼
┌──────────────────────────────────────────────────────────────┐
│  GB10 — everything runs here                                  │
│                                                               │
│  Open WebUI (:3000)                                           │
│    │ Dropdown: "Jarvis"                                       │
│    ▼                                                          │
│  NATS Pipe Function (~60 lines)                               │
│    │ nats.request("agents.command.jarvis", message)            │
│    ▼                                                          │
│  Jarvis (serve-nats, Qwen3.6-35B-A3B, 3B active)             │
│    │ Supervisor decides: dispatch_by_capability / queue_build  │
│    │ Constructs structured CommandPayload                      │
│    ▼                                                          │
│  NATS JetStream (:4222)                                       │
│    │                    │                    │                 │
│    ▼                    ▼                    ▼                 │
│  specialist-agent     study-tutor          forge               │
│  (architect / PO)     (tutor)              (autobuild)         │
│    │                    │                    │                 │
│    ▼                    ▼                    ▼                 │
│  llama-swap (:9000)                                           │
│    ├── qwen36-workhorse (routing, 3B active, always-on)       │
│    ├── architect-agent (fine-tune, 26B)                        │
│    ├── gcse-tutor-gemma4-moe (fine-tune, 26B)                 │
│    ├── nomic-embed-text (embeddings, always-on)               │
│    └── Coder-Next / GPT-OSS-120B (swappable)                 │
└──────────────────────────────────────────────────────────────┘
```

**Two LLM calls per request:** one small (3B routing) and one large (26B specialist). Both local. Both via llama-swap. Zero cloud.

---

## The Pipe Function

A single Python file (~60 lines) deployed into Open WebUI. It does one thing: send every message to Jarvis.

```python
def pipes(self):
    return [{"id": "jarvis", "name": "Jarvis"}]

async def pipe(self, body):
    # Every message goes to Jarvis. Jarvis routes.
    response = await nc.request("agents.command.jarvis", payload)
    return response.data.decode()
```

No manifold. No per-agent argument mappers. No tool calling. The Pipe Function doesn't know what agents exist — Jarvis does.

Full implementation: `fleet-gateway/openwebui/nats_fleet_pipe.py`

---

## Design principles

1. **Jarvis is the only entry point from the UI.** The Pipe Function sends everything to Jarvis. Jarvis routes. Adding a new agent means registering it in the fleet (NATS manifest + KV); the Pipe Function doesn't change.

2. **Gateways are thin.** The Pipe Function is a transport adapter. Reachy Mini Scholar is a transport adapter. All intelligence lives in Jarvis and the agents.

3. **NATS is the only internal transport.** Open WebUI → NATS → Jarvis → NATS → agents. No MCP, no HTTP between agents, no second protocol.

4. **nats-core is the wire contract.** `MessageEnvelope`, `CommandPayload`, `ResultPayload`. Same models everywhere.

5. **Two LLM calls is the right architecture.** The routing model (3B) is cheap and fast. The specialist model (26B) is the expensive call. Separating them means the specialist's `CommandRouter` receives clean structured arguments — no argument-mapping hacks in the gateway.

---

## What this replaces

| Before | After |
|---|---|
| Claude Desktop as MCP client | Open WebUI as NATS publisher → Jarvis |
| Claude (cloud LLM) decides tool calls | Jarvis (local 3B MoE) decides tool calls |
| MCP stdio transport to agents | NATS request/reply to agents |
| Pipe Function knows about all agents | Pipe Function knows about Jarvis only |
| Per-agent argument mappers | Jarvis's supervisor handles arg extraction |
| Agents on Mac | Agents on GB10 (Docker) |
| Two transports (MCP + NATS) | One transport (NATS everywhere) |

---

## What this does NOT replace

- **Claude Desktop for development.** Rich uses Claude Desktop + MCP for research, planning, and iterative sessions.
- **Claude Code for implementation.** Autonomous runbook execution on GB10 unchanged.
- **The agents themselves.** study-tutor, specialist-agent, forge — all preserved. Only the transport to the user changes.
- **Scholar's hackathon path.** Scholar reads directly from Graphiti for the hackathon (no NATS needed). Post-hackathon, Scholar becomes another NATS gateway in fleet-gateway.

---

## Decision record

**Preferred direction:** Open WebUI → NATS Pipe Function → Jarvis → agents. Jarvis is the intent router. The Pipe Function is thin. Challenge only with new evidence.

**Evolution:**
- v1: Claude Desktop + MCP (working but audience perception problem)
- v2: Open WebUI + NATS Pipe Function manifold (individual agents) — wire format mismatch discovered
- v3: Open WebUI + Jarvis routing — the natural architecture; Jarvis already proven on 4 May
- v4: Agreed — Jarvis serve-nats scoped, Pipe Function simplified, demo strategy updated

**Decided:** 7 May 2026
**Participants:** Rich Woollcott, Claude (research + analysis)

---

*This document should be reviewed after the DDD Southwest demo (16 May) and updated with lessons learned.*
