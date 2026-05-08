# DDD Southwest Demo Strategy — v4 (Jarvis-Routed)

**Talk:** "2026: The Year of the Software Factory"
**Date:** 16 May 2026 (9 days out)
**Venue:** Engine Shed, Bristol
**Status:** Strategy agreed 7 May 2026 — v4 adds Jarvis as the intent router between Open WebUI and agents
**Companion docs:**
- `openwebui-nats-pipe-architecture.md` — full architecture decision
- `jarvis/features/feat-jarvis-006-nats-chat-gateway/nats-chat-gateway-scope-and-build-plan.md` — Jarvis serve-nats scope
- `study-tutor/features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md` — study-tutor serve-nats scope

---

## Decisions taken (7 May 2026)

| Decision | Outcome | Reasoning |
|---|---|---|
| **Demo surface** | **Open WebUI + NATS Pipe Function → Jarvis** | Claude Desktop makes the audience think "he's just using Claude." Open WebUI is visibly a custom interface. All messages route through Jarvis — the fleet's intent router. |
| **Intent routing** | **Jarvis (Qwen3.6-35B-A3B, 3B active params via llama-swap)** | Jarvis is the bridge between natural language and structured commands — the role Claude played in Claude Desktop. Proven on 4 May: supervisor called `queue_build` with correct structured args via `qwen36-workhorse`. No validation spike needed. |
| **Infrastructure topology** | **Everything on GB10** — Open WebUI, Jarvis, agents (Docker), NATS, llama-swap, ChromaDB, all localhost | Dark factory thesis: one box, zero cross-network hops. Mac is just a browser over Tailscale. |
| **Transport protocol** | **NATS everywhere** — MCP removed from demo/production path | NATS is the fleet backbone. Pipe Function → Jarvis → agents, all via NATS. Claude Desktop + MCP remains the development workflow. |
| **Embeddings** | **llama-swap `/v1/embeddings`** — NOT Ollama | Single inference front door (DECISION-DF-001). |
| **ChromaDB** | **PersistentClient on GB10** — co-located with agents and llama-swap | Resolves ASSUM-002. |
| **Architect demo content** | Study-tutor architecture (own IP) — NOT FinProxy | Client-confidential. |
| **AutoBuild demo** | Pre-created FastAPI feature, live NATS notifications | Real autobuild on stage is a coin flip. |
| **Reachy Mini at DDD** | Slide/clip only — NOT live on stage | Transport + conference WiFi risk. |
| **Reachy Mini at hackathon** | Live in video if integration lands by 10 May | Scholar is the killer differentiator. |

---

## The architecture in one diagram

```
Browser (Mac / any device)
    │
    │ Tailscale
    ▼
┌──────────────────────────────────────────────────────────────┐
│  GB10 (promaxgb10-41b1) — everything runs here               │
│                                                               │
│  Open WebUI (:3000)                                           │
│    │ Model selector shows: "Jarvis"                           │
│    ▼                                                          │
│  NATS Pipe Function (fleet-gateway, ~60 lines of Python)      │
│    │                                                          │
│    │ nats.request("agents.command.jarvis", user_message)       │
│    ▼                                                          │
│  Jarvis (serve-nats, Qwen3.6-35B-A3B, 3B active)             │
│    │ Supervisor understands intent                             │
│    │ Calls dispatch_by_capability or queue_build               │
│    │ Constructs structured CommandPayload                      │
│    ▼                                                          │
│  NATS JetStream (:4222)                                       │
│    │                     │                     │              │
│    ▼                     ▼                     ▼              │
│  specialist-agent      study-tutor           forge             │
│  (Docker, dual-role)   (serve-nats)          (pipeline)        │
│  ├─ architect           │                     │              │
│  └─ product-owner       │                     │              │
│    │                     │                     │              │
│    ▼                     ▼                     ▼              │
│  llama-swap (:9000) ◄───┘─────────────────────┘              │
│    ├─ qwen36-workhorse (Jarvis routing, 3B active, always-on) │
│    ├─ architect-agent (Gemma 4 MoE fine-tune, 26B)            │
│    ├─ gcse-tutor-gemma4-moe (tutor fine-tune, 26B)            │
│    ├─ nomic-embed-text (/v1/embeddings, always-on)            │
│    └─ Coder-Next / GPT-OSS-120B (swappable)                  │
└──────────────────────────────────────────────────────────────┘
```

Two LLM calls per request: one small (3B routing) and one large (26B specialist). Both local. Both via llama-swap. Zero cloud.

---

## What we're trying to show

The audience should see a user question go through intent routing, structured dispatch, specialist inference, and response — all on one box. The demo proves three things: (1) fine-tuned domain models match frontier quality at zero marginal cost; (2) agent orchestration handles routing, quality gates, and knowledge graphs; (3) the whole thing runs on a box under the desk.

**Stage setup:** Open WebUI on the left (the product surface), terminal tailing NATS / llama-swap logs on the right (the factory floor). The model selector shows one entry: **Jarvis**.

---

## Three demos

### Demo 1 — "Ask the architect"

User types a question about architecture in Open WebUI → Pipe Function publishes to `agents.command.jarvis` → Jarvis's supervisor (3B routing model) decides to call `dispatch_by_capability(agent_id="architect-agent", command="align", ...)` → NATS → specialist-agent (architect role) → llama-swap loads fine-tuned Gemma 4 MoE → structured review returned → Jarvis formats and returns via NATS → Open WebUI displays.

**What the audience sees:** A question goes in, and a structured architecture review comes out. The terminal shows: Jarvis routing decision, NATS dispatch, model swap, specialist inference, response.

**Content:** Study-tutor architecture — the "always-on RAG vs selective retrieval" decision (ADR-FLEET-002). Own IP, narrative loop with Demo 3.

**Status:** 🔶 Agent logic proven via CLI REPL on 4 May. Needs: Jarvis serve-nats (FEAT-JARVIS-006) + Pipe Function deployed + specialist-agent verified on GB10.

**Fallback:** Jarvis CLI on GB10 via terminal. Still shows intent routing + dispatch + specialist inference; just not through the Open WebUI surface.

### Demo 2 — "Build something"

User types a build request → Jarvis's supervisor calls `queue_build(feature_id="FEAT-DEMO", ...)` → JetStream publish → forge picks up → autobuild stages execute → lifecycle notifications appear in the terminal.

**Content:** Pre-created FastAPI CRUD endpoint feature spec. Pipeline progression is the interesting bit, not the code output.

**Status:** 🔶 `queue_build` proven on 4 May (Forge consumed + acked). Autobuild needs F010.L (model retargeting) + F010.M (async result bridge). Being worked on.

**Fallback:** Slide walkthrough of the pipeline. Demos 1 + 3 carry the live weight.

### Demo 3 — "Teach a student"

User types a GCSE question → Jarvis's supervisor calls `dispatch_by_capability(agent_id="gcse-tutor", command="tutor_turn", ...)` → NATS → study-tutor (serve-nats) → Player-Coach loop → Socratic response with Coach quality gate → Graphiti write → response returned.

**Content:** Macbeth question. Coach revision visible in logs (`attempts=2`).

**Status:** 🔶 Agent logic proven via MCP. Needs: study-tutor serve-nats (FEAT-NATS-001) + Jarvis serve-nats (FEAT-JARVIS-006).

**Fallback:** Open WebUI → llama-swap direct connection (already working for Lilymay). Fine-tuned tutoring behaviour visible; Player-Coach loop and Graphiti not visible in fallback.

---

## Demo script (stage sequence)

**Opening (slides, 5 min):** Solow Paradox framing.

**Demo 1 — Architect review (Open WebUI + logs, 5 min):**
"Here's a real architecture decision from a tutoring system I'm building."
→ Type question into Open WebUI → terminal shows: Jarvis receives message, routing model decides `dispatch_by_capability`, NATS publish to architect-agent, llama-swap loads fine-tune, inference runs, response flows back
→ "Two models just worked together. The first — three billion active parameters — figured out who to ask. The second — twenty-six billion, fine-tuned on architecture books — gave the answer. Both on that box."

**Slides (5 min):** Pipeline diagram, NATS architecture, the two-layer principle.

**Demo 2 — Build pipeline (Open WebUI + logs, 5 min):**
"Now let me ask the factory to build something."
→ Type build request → terminal shows: Jarvis calls `queue_build`, JetStream publish, forge picks up, autobuild stages tick through
→ Flash code output briefly.

**Demo 3 — Study tutor (Open WebUI + logs, 5 min):**
"Fine-tuned models aren't just for code."
→ Type a Macbeth question → terminal shows: Jarvis dispatches to tutor, Player generates, Coach revises (`attempts=2`), Graphiti write
→ Slide/clip of Reachy Mini Scholar: "The same student model powers an embodied companion."

**Closing (slides, 5 min):**
"Three specialists, three fine-tuned models, all routed by a 3B intent model, all on one box, all talking over NATS. The marginal cost of the next build is the electricity."

---

## Hackathon video structure

Same architecture as DDD. Open WebUI + Jarvis + NATS for the tutoring demo. Reachy Mini Scholar (if integration lands) reading from Graphiti. Video sequence unchanged from v3.

**Fallback if Jarvis serve-nats doesn't land:** Open WebUI → llama-swap direct connection for the tutoring session (already working for Lilymay). The hackathon video is about the tutor and the student experience, not the routing architecture.

---

## Reachy Mini integration timeline

Unchanged from v3. Scholar → Graphiti reader → verbal progress report. Scholar does NOT go through Jarvis for the hackathon (direct Graphiti read is simpler and sufficient).

| Date | Milestone |
|---|---|
| **Friday 8 May** | Build robots. Bonus: Scholar on WiFi. |
| **Saturday 9 May** | SDK hello world. Go/no-go. |
| **Sunday 10 May** | Hard integration deadline. Scenario 1 via Claude Code. |
| **Mon–Wed 11–13 May** | Video shoot + DDD dry runs. |
| **Thu–Fri 14–15 May** | DDD final prep. |
| **Saturday 16 May** | DDD Southwest. |
| **Sunday 18 May** | Hackathon submission. |

---

## Dev work remaining (prioritised)

### Must-have for DDD (16 May)

| # | Item | Owner | Estimate |
|---|---|---|---|
| 1 | Forge gap F010.L (autobuild model retargeting to llama-swap) | Claude Code | 1–2 hrs |
| 2 | Forge gap F010.M (async result bridge / lifecycle emitter) | Claude Code | 2–4 hrs |
| 3 | **FEAT-JARVIS-006: Jarvis `serve-nats`** (NATS subscriber → supervisor → response) | Claude Code | 3–4 hrs |
| 4 | Verify specialist-agent `serve-nats` on GB10 Docker (dual-role compose) | Rich / Claude Code | 1–2 hrs |
| 5 | **Study-tutor `serve-nats` Phase 1** (FEAT-NATS-001) | Claude Code | 4–6 hrs |
| 6 | Open WebUI → llama-swap connection on GB10 + deploy Pipe Function | Rich | 30 min |
| 7 | DDD dry runs (Open WebUI + terminal split-screen, all three demos) | Rich | Half day |

### Must-have for hackathon (18 May)

| # | Item | Owner | Estimate |
|---|---|---|---|
| 8 | Reachy SDK hello world (Saturday 9 May) | Rich | 1–2 hrs |
| 9 | Reachy Scenario 1 integration via Claude Code (Sunday 10 May) | Claude Code | 4–6 hrs |
| 10 | Specialist-agent RAG: patch ingestion script (Ollama → llama-swap), run ingest | Claude Code | 1–2 hrs |
| 11 | Study-tutor RAG: write ingestion script, populate sources, wire CLI | Claude Code | 4–6 hrs |
| 12 | Record hackathon video | Rich | Half day |
| 13 | Finalise public repo, README, technical write-up, submit | Rich | 1 day |

### Already done

- Jarvis supervisor + dispatch infrastructure: ✅ FEAT-004/005 complete, proven 4 May
- Architect fine-tune: ✅ Validated, comparison methodology documented
- Study-tutor Player-Coach: ✅ Working, Coach revision exercised, Graphiti write confirmed
- Open WebUI deployed on GB10: ✅ Seven subject presets for Lilymay
- Specialist-agent Docker: ✅ `docker-compose.dual-role.yml` exists
- Reachy research: ✅ Conversation starter, Scholar profile in fleet-gateway
- Fleet-gateway repo: ✅ Pipe Function + Scholar profile populated
- nats-core: ✅ 97% test coverage

---

## Risks

| Risk | Mitigation |
|---|---|
| Jarvis `serve-nats` is new code | 3–4 hours of work. All infrastructure exists (AppState, supervisor, NATS client, fleet registration). The new code is a NATS subscriber that calls `session_manager.invoke()`. |
| Study-tutor `serve-nats` doesn't land | Fallback: Open WebUI → llama-swap direct (already working for Lilymay). |
| Routing model makes wrong dispatch decision on stage | Pre-test the exact demo questions in dry runs. Jarvis's supervisor is deterministic given the same input + tool definitions. |
| Two LLM calls = double latency | Routing call is 3B active params (~1–2s). Specialist call is the long pole. Pre-warm both models in llama-swap. Audience sees the routing as "the factory thinking." |
| Forge autobuild doesn't complete (F010.L/M gaps) | Demo 2 becomes a slide walkthrough. Two live demos still strong. |

---

## Superseded decisions

### From v3 (superseded by v4)

- **Pipe Function manifold exposing individual agents:** Replaced by single Jarvis entry. The Pipe Function doesn't need to know about architects or tutors — Jarvis routes.
- **Per-agent argument mappers in Pipe Function:** Eliminated entirely. Jarvis's supervisor handles natural language → structured args via tool calling. This was the insight that unlocked v4.

### From v2 (superseded by v3)

- Claude Desktop as demo surface → Open WebUI
- MCP transport → NATS
- Agents on Mac → GB10

### From v1 (superseded by v2)

- Telegram adapters → Not building
- FinProxy content → Own IP
- Reachy live at DDD → Slide/clip only

---

*Strategy v4: 7 May 2026*
*Supersedes: v3 (agent manifold), v2 (Claude Desktop), v1 (conversation starter)*
