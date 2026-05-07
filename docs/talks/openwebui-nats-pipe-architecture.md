# Open WebUI + NATS Pipe Functions — Architecture Decision

**Status:** Proposed (7 May 2026)
**Scope:** Fleet-wide — affects DDD Southwest demo, Gemma 4 Good Hackathon, and long-term fleet UI surface
**Related:** `ddd-southwest-demo-strategy.md` (v2), `distributed_agent_orchestration_architecture.md`, DECISION-DF-001

---

## The decision in one paragraph

Replace Claude Desktop as the user-facing surface for the software factory with Open WebUI, connected to the agent fleet via NATS Pipe Functions. Each agent (architect, product-owner, study-tutor, forge) appears as a named model in Open WebUI's model selector. The Pipe Function is a thin NATS client — it publishes the user's message to the selected agent's NATS topic and streams the response back. No MCP, no intermediary routing model, no tool calling. NATS is already the fleet backbone; this makes Open WebUI another participant on the bus.

---

## Why

### The Claude Desktop problem

The current demo surface is Claude Desktop acting as an MCP client to the study-tutor and specialist-agent. This works for development but fails for two audiences:

- **DDD Southwest (16 May):** The audience sees Claude Desktop and thinks "he's just using Claude." The actual intelligence — fine-tuned Gemma 4 models, Player-Coach quality loops, Graphiti knowledge graphs — is invisible behind a Claude-branded shell. The narrative is about local inference and zero marginal cost; the UI contradicts the story.
- **Gemma 4 Good Hackathon (18 May):** Judges evaluating an education-track submission won't understand MCP tools in Claude Desktop. They need to see a student-facing interface that's obviously not a commercial AI product.

### Why not MCP via Open WebUI?

Open WebUI supports MCP natively (v0.6.31+, Streamable HTTP) and via the `mcpo` proxy for stdio MCP servers. The study-tutor and specialist-agent already expose stdio MCP servers. So the path exists.

The problem is that MCP tool calling in Open WebUI requires the **model** to decide when to call tools. That means the fine-tuned Gemma 4 models would need to output structured function-call JSON in Open WebUI's Native Mode. These models weren't trained for tool calling — they were trained for architecture review and Socratic tutoring. You'd need a separate routing model that does tool calling, adding complexity and an extra inference step. And it doesn't use NATS — it's a completely different transport from the fleet architecture.

MCP solves the right problem (tool discovery and routing) for general-purpose assistants. It's the wrong abstraction when you have purpose-built agents that already know what they do.

### Why NATS Pipe Functions?

NATS is already the fleet message bus. The specialist-agent already has `serve-nats` mode (see `docker-compose.dual-role.yml`). Every agent in the fleet will eventually be a NATS subscriber. Making Open WebUI a NATS publisher is the natural extension — it becomes another node on the bus, not a special case.

Open WebUI Pipe Functions are Python classes that register as custom "models" in the model selector. The `pipe()` method receives the user's message and returns the response. Inside, it can run any Python — including an async NATS client. The Pipe Function doesn't need a model to decide what to do; the user already selected the agent from the dropdown.

---

## Architecture

### Before (Claude Desktop + MCP)

```
┌───────────────────────┐         ┌─────────────────────────┐
│ Claude Desktop (Mac)  │  stdio  │ study-tutor MCP server  │
│                       │ ───────►│ (Mac, Python process)   │
│ Claude (the LLM)      │         │                         │
│ decides when to call  │         │ Player-Coach orchestrator│
│ MCP tools             │         │ Graphiti, RAG, Coach QG  │
│                       │  stdio  │                         │
│                       │ ───────►│ specialist-agent MCP    │
│                       │         │ (Mac, Python process)   │
└───────────────────────┘         └────────────┬────────────┘
                                               │ Tailscale
                                               ▼
                                        ┌──────────────┐
                                        │ GB10         │
                                        │ llama-swap   │
                                        └──────────────┘
```

Problems: Claude is the UI *and* the router. Audience sees Claude. Agents run on Mac. Cross-network inference calls. MCP is a second transport alongside NATS.

### After (Open WebUI + NATS)

```
Browser (Mac / any device)
    │
    │ Tailscale (or LAN)
    ▼
┌──────────────────────────────────────────────────────────┐
│  GB10 (promaxgb10-41b1) — everything runs here           │
│                                                           │
│  Open WebUI (:3000)                                       │
│    │                                                      │
│    │ Model selector shows:                                │
│    │   • Architect Agent                                  │
│    │   • Product Owner                                    │
│    │   • GCSE Study Tutor                                 │
│    │   • Forge Build Pipeline                             │
│    │   • (+ direct llama-swap models for free chat)       │
│    │                                                      │
│    ▼                                                      │
│  NATS Pipe Function (Python, in Open WebUI / Pipelines)   │
│    │                                                      │
│    │ nats.request("agents.architect.align", payload)       │
│    │ nats.request("agents.tutor.turn", payload)            │
│    │                                                      │
│    ▼                                                      │
│  NATS JetStream (:4222)                                   │
│    │                     │                     │          │
│    ▼                     ▼                     ▼          │
│  specialist-agent      study-tutor           forge        │
│  (Docker, dual-role)   (NATS subscriber)     (pipeline)   │
│  ├─ architect           │                     │          │
│  └─ product-owner       │                     │          │
│    │                     │                     │          │
│    ▼                     ▼                     ▼          │
│  llama-swap (:9000) ◄───┘─────────────────────┘          │
│    ├─ architect-agent (Gemma 4 MoE fine-tune)             │
│    ├─ gcse-tutor-gemma4-moe (tutor fine-tune)             │
│    ├─ nomic-embed-text (/v1/embeddings)                   │
│    ├─ Coder-Next (code gen)                               │
│    └─ GPT-OSS-120B (reasoning, swappable)                 │
│                                                           │
│  ChromaDB (PersistentClient, data/chroma/)                │
│    ├─ architect-knowledge-v1                              │
│    └─ gcse-english-v1                                     │
│                                                           │
│  Graphiti → FalkorDB (Synology, via Tailscale)            │
└──────────────────────────────────────────────────────────┘
```

Benefits:
- **One transport.** NATS everywhere. No MCP, no stdio, no second protocol.
- **One box.** Open WebUI, Pipe Function, NATS, agents, llama-swap, ChromaDB — all localhost on GB10. Zero cross-network hops for internal operations.
- **Named agents, not "Claude."** The audience sees "Architect Agent" in the dropdown, not a Claude-branded shell. The intelligence is visibly local and purpose-built.
- **The agents are the product.** Player-Coach loops, Graphiti integration, RAG pipelines, quality gates — all preserved. The Pipe Function is a thin transport adapter, not a replacement.
- **The Mac is just glass.** A browser pointed at Open WebUI over Tailscale. Nothing runs on the Mac except the browser.

---

## Pipe Function design

### Shape

A single Pipe Function file (registered in Open WebUI Workspace → Functions, or deployed via Pipelines container) that exposes all agents as a manifold:

```python
from pydantic import BaseModel, Field
from typing import AsyncGenerator

class Pipe:
    """NATS Fleet Gateway — exposes fleet agents as Open WebUI models."""

    class Valves(BaseModel):
        NATS_URL: str = Field(
            default="nats://localhost:4222",
            description="NATS server URL (localhost on GB10)",
        )
        REQUEST_TIMEOUT: int = Field(
            default=120,
            description="NATS request timeout in seconds",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        """Register each fleet agent as a selectable model."""
        return [
            {"id": "architect-align", "name": "Architect Agent (Align)"},
            {"id": "product-owner", "name": "Product Owner"},
            {"id": "gcse-tutor", "name": "GCSE Study Tutor"},
            {"id": "forge-build", "name": "Forge Build Pipeline"},
        ]

    async def pipe(self, body: dict) -> str | AsyncGenerator[str, None]:
        """
        Publish user message to the selected agent's NATS topic,
        await and return the response.

        Wire format: nats-core Pydantic models (JSON over NATS).
        """
        import nats  # lazy import — nats.py must be installed in the container

        agent_id = body.get("model", "").split(".")[-1]  # strip manifold prefix
        messages = body.get("messages", [])
        user_message = messages[-1]["content"] if messages else ""

        # Build nats-core wire payload
        # (actual implementation uses nats-core Pydantic models)
        payload = {
            "agent": agent_id,
            "message": user_message,
            "conversation_history": messages,
        }

        nc = await nats.connect(self.valves.NATS_URL)
        try:
            topic = f"agents.{agent_id}.request"
            response = await nc.request(
                topic,
                json.dumps(payload).encode(),
                timeout=self.valves.REQUEST_TIMEOUT,
            )
            return response.data.decode()
        finally:
            await nc.close()
```

This is a sketch. The production version needs:
- **nats-core Pydantic models** as the wire contract (not raw JSON)
- **Streaming support** — the `pipe()` method can return an `AsyncGenerator[str, None]` for SSE streaming; the NATS subscriber in the agent would publish incremental chunks to a reply subject
- **Session state** — the study-tutor's `tutor_turn` needs session context (text_name, focus_aos, session_id); this comes from the conversation history or from Open WebUI's chat metadata
- **Error handling** — NATS timeouts, agent unavailability, malformed responses
- **Connection pooling** — don't open/close a NATS connection per request; use a persistent connection initialised in `__init__` or a module-level singleton

### What the Pipe Function does NOT do

- **No LLM routing.** The user selects the agent from the dropdown. The Pipe Function publishes to a deterministic NATS topic based on that selection. No model needs to "decide" which tool to call.
- **No agent logic.** The Player-Coach loop, RAG retrieval, Graphiti writes, quality gates — all of that stays inside the agents. The Pipe Function is a transport adapter.
- **No MCP.** The Pipe Function speaks NATS directly. No mcpo proxy, no tool schemas, no function-call JSON.
- **No direct model calls.** The Pipe Function never calls llama-swap directly. All inference goes through the agents, which call llama-swap themselves.

---

## What the audience sees (DDD demo)

**Screen layout:** Open WebUI on the left, terminal tailing NATS / llama-swap logs on the right.

**Demo 1 — Architect review:**
Rich selects "Architect Agent (Align)" from the model dropdown. Types: "Is the selective retrieval decision in ADR-FLEET-002 still defensible given the study-tutor's architecture?" The terminal shows: NATS message published → specialist-agent receives → llama-swap loads architect fine-tune → inference runs → Coach evaluates → response streams back into Open WebUI. The audience sees a structured architecture judgment appear in a clean chat interface.

**Demo 2 — Build pipeline:**
Rich selects "Forge Build Pipeline." Types: "Build a FastAPI CRUD endpoint for a task manager with Pydantic models." The terminal shows: NATS message → forge receives → autobuild stages tick through (planning → coding → review → complete) → code output returned. The audience sees the pipeline progression in real time.

**Demo 3 — Study tutor:**
Rich selects "GCSE Study Tutor." Types a question about Macbeth. The terminal shows: NATS message → study-tutor receives → Player generates response → Coach reviews (attempts=2) → Graphiti writes session state → response streams back. The audience sees a Socratic tutoring exchange.

**The key moment:** Three different agents, three different fine-tuned models, three different orchestration patterns — all accessed through the same chat interface, all running on one box, all communicating over NATS. That's the software factory.

---

## What the hackathon judges see

Same Open WebUI interface, but configured for the education story:
- Model selector shows "GCSE Study Tutor" (primary) plus subject-specific presets
- Lilymay (or Rich as student) has a tutoring session — Socratic questioning, essay feedback, quote analysis
- Terminal briefly shown to prove local inference
- Reachy Mini Scholar (if integration lands) asks "How's Lilymay's revision going?" — Scholar is another NATS consumer reading from Graphiti
- The architecture slide shows the pipeline: curriculum PDFs → Player-Coach data gen → fine-tuning → NATS fleet → Open WebUI

Judges see a student-facing product, not a developer tool. They don't need to understand NATS or MCP or Claude Desktop. They see a chat interface, a tutoring session, and a robot.

---

## ChromaDB: unified approach (both projects)

With everything on GB10, the ChromaDB topology resolves cleanly:

- **PersistentClient on GB10** — co-located with agents and llama-swap
- **Embeddings via llama-swap** — `OpenAIEmbeddingFunction` pointing at `http://localhost:9000/v1/embeddings` with model `nomic-embed-text`
- **No Ollama** — llama-swap is the single inference front door (DECISION-DF-001)
- **Ingestion runs on GB10** — all localhost, zero network hops
- **Specialist-agent ingestion script** — needs updating from Ollama endpoint shape to OpenAI-compatible (`/v1/embeddings`); small patch since the endpoint URL is already parameterised
- **Study-tutor ingestion script** — needs writing; follows the same pattern

Both projects use identical connection code:

```python
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

ef = OpenAIEmbeddingFunction(
    api_base="http://localhost:9000/v1",
    api_key="not-needed",
    model_name="nomic-embed-text",
)
client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_collection(name="<collection>", embedding_function=ef)
```

---

## Implementation work

### Must-build for DDD demo (16 May)

| # | Item | Owner | Estimate | Dependencies |
|---|---|---|---|---|
| 1 | Forge gap features F010.L + F010.M | Claude Code | 3–6 hrs | — |
| 2 | Open WebUI → llama-swap connection on GB10 (Admin → Connections → OpenAI, URL = localhost:9000) | Rich | 15 min | Open WebUI running on GB10 |
| 3 | NATS Pipe Function (manifold: architect, product-owner, forge) | Claude Code | 4–6 hrs | NATS running on GB10, specialist-agent `serve-nats` working |
| 4 | Verify specialist-agent `serve-nats` works on GB10 Docker | Rich / Claude Code | 1–2 hrs | Docker image built |
| 5 | Open WebUI demo presets (system prompts, model display names) | Rich | 30 min | Item 3 |
| 6 | DDD dry runs (Open WebUI + terminal split-screen) | Rich | Half day | Items 1–5 |

### Must-build for hackathon (18 May)

| # | Item | Owner | Estimate | Dependencies |
|---|---|---|---|---|
| 7 | Study-tutor `serve-nats` mode (NATS subscriber calling orchestrator) | Claude Code | 4–6 hrs | nats-core contract, study-tutor orchestrator |
| 8 | Add study-tutor to Pipe Function manifold | Claude Code | 30 min | Item 7 |
| 9 | Reachy SDK hello world + Scenario 1 (Fri–Sun) | Rich / Claude Code | 5–8 hrs | Scholar hardware |
| 10 | Specialist-agent RAG: patch ingestion script (Ollama→llama-swap), run ingest | Claude Code | 1–2 hrs | llama-swap embedding endpoint |
| 11 | Study-tutor RAG: write ingestion script, populate sources, wire CLI | Claude Code | 4–6 hrs | Item 10 pattern |
| 12 | Record hackathon video | Rich | Half day | Items 7–9 |
| 13 | Finalise public repo, README, technical write-up, submit | Rich | 1 day | — |

### Stretch (post-demo)

| Item | Notes |
|---|---|
| Streaming support in Pipe Function | Return `AsyncGenerator` from `pipe()`, agent publishes incremental chunks to NATS reply subject |
| Connection pooling in Pipe Function | Persistent NATS connection rather than connect/close per request |
| Forge pipeline progress events in Open WebUI | Pipe Function subscribes to lifecycle NATS topics, emits status updates as chat events |
| Bridge (Reachy Mini #2) as NATS gateway | Ship's Computer pattern — voice in → NATS → agents → voice out |

---

## What this replaces

| Before | After |
|---|---|
| Claude Desktop as MCP client | Open WebUI as NATS publisher |
| MCP stdio transport to agents | NATS request/reply to agents |
| Claude (the LLM) decides when to call tools | User selects agent from dropdown; Pipe Function routes deterministically |
| Agents run on Mac | Agents run on GB10 (Docker) |
| Cross-network inference (Mac → Tailscale → GB10) | Localhost inference (agent → llama-swap, same box) |
| ChromaDB topology unclear (ASSUM-002) | PersistentClient on GB10, co-located with everything |
| Embeddings via Ollama | Embeddings via llama-swap `/v1/embeddings` |
| Two transports (MCP + NATS) | One transport (NATS everywhere) |

---

## What this does NOT replace

- **Claude Desktop for development.** Rich still uses Claude Desktop + MCP for research, planning, and iterative development sessions. This decision is about the *demo and production surface*, not the development workflow.
- **Claude Code for implementation.** Autonomous runbook execution on GB10 continues unchanged.
- **The agents themselves.** study-tutor, specialist-agent, forge — all preserved. Their orchestration logic, Player-Coach loops, RAG pipelines, Graphiti integration, quality gates — untouched. Only the transport to the user changes.

---

## Risks

| Risk | Mitigation |
|---|---|
| Study-tutor `serve-nats` doesn't land in time | For DDD: demo architect and product-owner via NATS; study-tutor falls back to direct Open WebUI → llama-swap connection (already working for Lilymay). For hackathon: study-tutor via direct connection still tells the story. |
| NATS Pipe Function is new code under demo pressure | The Pipe Function is ~100 lines of Python. The specialist-agent's `serve-nats` is proven. The risk is in the glue, not the components. |
| Open WebUI Pipe Function container can't install `nats.py` | Pipelines container supports `pip install` via requirements; alternatively, use Open WebUI's built-in Workspace Functions which run in the main process. |
| llama-swap model swap latency visible in Open WebUI | Pre-warm models before demo (send a dummy request 2 min before each segment). llama-swap's `/logs/stream` endpoint lets Rich monitor warm-up from the terminal pane. |
| Audience still doesn't understand it's local | Terminal log pane showing llama-swap inference + NATS messages is the proof. Opening line: "Everything you're about to see runs on that box. No cloud, no API keys, no Claude." |

---

## Decision record

**Preferred direction:** Open WebUI + NATS Pipe Functions as the user-facing surface for the software factory, replacing Claude Desktop for demos and production use. Challenge only with new evidence — for example, if NATS Pipe Functions prove unreliable under demo conditions, fall back to Open WebUI → llama-swap direct connection (still better than Claude Desktop for audience perception).

**Decided:** 7 May 2026
**Participants:** Rich Woollcott, Claude (research + analysis)

---

*This document should be reviewed after the DDD Southwest demo (16 May) and updated with lessons learned.*
