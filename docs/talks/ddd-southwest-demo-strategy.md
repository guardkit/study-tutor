# DDD Southwest Demo Strategy — v3 (Open WebUI + NATS)

**Talk:** "2026: The Year of the Software Factory"
**Date:** 16 May 2026 (9 days out)
**Venue:** Engine Shed, Bristol
**Status:** Strategy agreed 7 May 2026 — updated to v3 same day after architecture realignment
**Companion doc:** `openwebui-nats-pipe-architecture.md` (full architecture decision)

---

## Decisions taken (7 May 2026)

| Decision | Outcome | Reasoning |
|---|---|---|
| **Demo surface** | **Open WebUI + NATS Pipe Functions** — agents appear as named models in the dropdown | Claude Desktop makes the audience think "he's just using Claude." Open WebUI is visibly a custom interface backed by local models. NATS Pipe Functions connect the UI to the existing agent fleet — no MCP, no tool calling, no intermediary router. |
| **Infrastructure topology** | **Everything on GB10** — Open WebUI, agents (Docker), NATS, llama-swap, ChromaDB, all localhost | Dark factory thesis made concrete: one box, zero cross-network hops for internal operations. Mac is just a browser over Tailscale. |
| **Transport protocol** | **NATS everywhere** — MCP removed from the demo/production path | NATS is already the fleet backbone. The Pipe Function is another NATS publisher. One transport, not two. Claude Desktop + MCP remains the development workflow. |
| **Embeddings** | **llama-swap `/v1/embeddings`** — NOT Ollama | llama-swap is the single inference front door (DECISION-DF-001). nomic-embed-text served via llama-swap. Both projects use `OpenAIEmbeddingFunction` pointing at localhost:9000. |
| **ChromaDB topology** | **PersistentClient on GB10** — co-located with agents and llama-swap | Resolves ASSUM-002. No Chroma server process, no extra port. Ingestion and queries are all localhost. |
| **Telegram adapter** | Not building | Dev time better spent on Pipe Function and Reachy integration |
| **Architect demo content** | Study-tutor architecture (own IP) — NOT FinProxy | FinProxy is a client startup — cannot demo their docs publicly |
| **AutoBuild demo approach** | Pre-created FastAPI feature, live NATS notifications, pre-baked code output | Real autobuild on stage is a coin flip; pipeline progression is the interesting bit, not the code output |
| **Reachy Mini at DDD** | Slide/clip only — NOT live on stage | Transporting to Bristol + conference WiFi risk is not justified |
| **Reachy Mini at hackathon** | Live in video if integration lands by 10 May | Filming at home, own network, multiple takes; Scholar is the killer differentiator |

---

## What we're trying to show

The talk's thesis is that fine-tuned domain models + agent orchestration + local inference = a software factory where marginal build cost approaches zero. The demo needs to make this tangible, not theoretical. The audience should see a message go in and watch work come out — with the receipts visible at every stage.

**Stage setup:** Split-screen presenter layout — **Open WebUI on the left** (the product surface), **terminal tailing NATS / llama-swap logs on the right** (the factory floor). The audience sees named agents in a clean chat interface, not Claude. The terminal shows every NATS message, every model load, every Coach revision — visible proof that this is local infrastructure, not a cloud API call.

**The key visual:** Three different agents, three different fine-tuned models, three different orchestration patterns — all accessed through the same chat dropdown, all running on one box under the desk, all communicating over NATS. That's the software factory.

---

## How Open WebUI connects to the agents

Open WebUI does **not** call the fine-tuned models directly. The agents (study-tutor, specialist-agent, forge) contain all the intelligence: Player-Coach loops, quality gates, Graphiti integration, RAG pipelines. Open WebUI is the glass; the agents are the product.

The connection is a **NATS Pipe Function** — a single Python class registered in Open WebUI that:

1. Exposes each agent as a named model in the dropdown (`pipes()` manifold)
2. When the user sends a message, publishes it to the selected agent's NATS topic
3. Awaits the agent's response on the NATS reply subject
4. Returns the response to Open WebUI for display

The Pipe Function is ~100 lines of Python. It doesn't contain any agent logic. It's a transport adapter between Open WebUI's chat protocol and the NATS message bus.

The specialist-agent already has `serve-nats` mode (see `docker-compose.dual-role.yml` — both architect and product-owner roles subscribe to NATS topics). The study-tutor needs a `serve-nats` mode adding (scoped separately).

See `openwebui-nats-pipe-architecture.md` for the full architecture, code shape, and design rationale.

---

## Three demos

### Demo 1 — "Ask the architect"

User selects **"Architect Agent"** from the Open WebUI model dropdown → types a question → Pipe Function publishes to NATS → specialist-agent (architect role, Docker on GB10) receives → calls llama-swap for fine-tuned Gemma 4 MoE inference → Player-Coach loop runs → structured architecture judgment returned via NATS → displayed in Open WebUI.

**What the audience sees:** A named agent in a clean chat interface produces a structured architecture review. The terminal shows the NATS message flow, llama-swap loading the fine-tune, inference running, Coach evaluation.

**Content:** Study-tutor architecture — the "always-on RAG vs selective retrieval" decision (ADR-FLEET-002). Uses Rich's own IP, creates a narrative loop with Demo 3.

**Evidence:** Baseline comparison — 3/4 sessions comparable quality to GPT-5.5, one session stricter, all without RAG. Methodology shown on slide without FinProxy content.

**Status:** 🔶 Agent logic proven via Claude Desktop MCP. Needs: Open WebUI → NATS Pipe Function → specialist-agent `serve-nats` path verified end-to-end on GB10.

**Fallback if Pipe Function not ready:** specialist-agent CLI on GB10, triggered from terminal. Still shows the agent working; just not through the Open WebUI surface. Audience still sees the fine-tuned model producing a structured review.

### Demo 2 — "Build something"

User selects **"Forge Build Pipeline"** from dropdown → types a build request → Pipe Function publishes to NATS → forge receives → autobuild stages execute → lifecycle notifications appear in the terminal as the build progresses → final result returned.

**Content:** Pre-created feature spec for a Python FastAPI CRUD endpoint with Pydantic models. Safe and predictable.

**Demo approach:** Hybrid — live NATS notifications (audience sees stage-complete events in the terminal), with pre-baked code output ready to show briefly. Transparent: "The build is running now — let me show you what the pipeline produces."

**Status:** 🔶 Forge NATS pipeline works. AutoBuild needs F010.L (model retargeting) + F010.M (async result bridge). Being worked on now.

**Fallback if forge gap features don't land:** Demo 2 becomes a slide walkthrough ("here's what the pipeline does") with Demos 1 + 3 carrying the live demo weight. Two live demos is still strong.

### Demo 3 — "Teach a student"

User selects **"GCSE Study Tutor"** from dropdown → types a question about Macbeth → Pipe Function publishes to NATS → study-tutor receives → Player-Coach loop runs → Socratic response with Coach quality gate → Graphiti knowledge graph update → response returned via NATS → displayed in Open WebUI.

**What the audience sees:** A tutoring session with a fine-tuned Gemma 4 model. The Coach revises the Player's response (visible `attempts=2` in the terminal). The model's behaviour was taught by fine-tuning; the curriculum knowledge comes from RAG. Two layers, cleanly separated.

**Evidence:** Working sessions — 5 turns, Coach revision observed, `<think>` tokens stripped, confidence progression 55→58%, session_completed episode written.

**Status:** 🔶 Agent logic proven via Claude Desktop MCP. Needs: study-tutor `serve-nats` mode + Pipe Function path verified. This is the biggest new piece of work.

**Fallback if study-tutor `serve-nats` not ready:** Open WebUI → llama-swap direct connection (already working for Lilymay's seven subject presets). The audience sees a tutoring session in Open WebUI backed by the fine-tuned model. The Player-Coach loop and Graphiti write-back aren't visible in this fallback, but the fine-tuned tutoring behaviour is. The terminal shows llama-swap inference running locally.

---

## Demo script (stage sequence)

**Opening (slides, 5 min):** Solow Paradox framing. "We have the tools but productivity hasn't moved. Why? Because the build layer and the planning layer are still separate."

**Demo 1 — Architect review (Open WebUI + logs, 5 min):**
"Here's a real architecture decision from a tutoring system I'm building. Should this agentic pipeline use always-on retrieval or selective retrieval?"
→ Select "Architect Agent" from dropdown → type question → terminal shows NATS publish, specialist-agent receiving, llama-swap loading fine-tune, inference running on GB10, Coach evaluation → structured judgment appears in Open WebUI
→ Show comparison methodology on slide (GPT-5.5 vs local model)
→ "Same quality, zero marginal cost, runs on that box under my desk."

**Slides (5 min):** Pipeline diagram, the NATS architecture, how agents are orchestrated, the two-layer principle.

**Demo 2 — Build pipeline (Open WebUI + logs, 5 min):**
"But the factory isn't just for reviews. Let me show you what happens when I ask it to build something."
→ Select "Forge Build Pipeline" → type build request → terminal shows NATS routing, forge picking up the task, autobuild stage-complete notifications arriving
→ "That build just ran on local inference. No API key, no cloud dependency."
→ Flash the code output on screen briefly.

**Demo 3 — Study tutor (Open WebUI + logs, 5 min):**
"One more. Fine-tuned models aren't just for code. Here's a GCSE tutor built with the same pipeline."
→ Select "GCSE Study Tutor" → type a Macbeth question → terminal shows NATS message, Player generating, Coach revising (`attempts=2`), Graphiti write → Socratic response appears in Open WebUI
→ "The model's tutoring behaviour was taught by fine-tuning. The curriculum knowledge comes from RAG. Two layers, cleanly separated."
→ Slide/clip of Reachy Mini Scholar: "And here's where it gets interesting — the same student model powers an embodied robot companion that reports progress, celebrates achievements, and keeps a teenager coming back."

**Closing (slides, 5 min):**
"Three agents, three fine-tuned models, three different jobs — all through the same interface, all on one box, all talking over NATS. No cloud. No API keys. The marginal cost of the next build is the electricity."
→ Cost comparison, DECISION-DF-001 thesis, what's next, Q&A.

---

## Hackathon video structure

**Surface:** Same Open WebUI + NATS setup as DDD, configured for the education story + Reachy Mini Scholar if integration lands.

**Video sequence (3–5 min):**

1. **The problem (30s):** GCSE students need personalised tutoring; human tutors cost £30–50/hr; AI tutors send data to the cloud; revision guides gather dust because they're passive.

2. **The solution (30s):** Fine-tuned Gemma 4 running on a box under the desk, with gamification designed to make a teenager want to come back.

3. **The pipeline (30s):** Brief overview of Player-Coach adversarial data generation. How the training data was made, why it matters.

4. **The demo (60–90s):** Lilymay (or Rich as student) using the tutor via Open WebUI — the model dropdown shows "GCSE Study Tutor." Show a Macbeth session with Socratic questioning, essay feedback, quote analysis. Terminal alongside showing inference on GB10 and NATS messages flowing.

5. **The companion (30–60s):** If Reachy ready — "How's Lilymay's revision going?" → Scholar responds with real Graphiti data (streak, level, near-unlockable achievements). If Reachy not ready — gamification dashboard mockup or pre-recorded future-vision segment (per submission plan §6.4).

6. **The architecture (30s):** Slide showing the full pipeline: Docling → Player-Coach → Unsloth → Gemma 4 → NATS → Open WebUI + Reachy. Two-layer principle. Replicable for any subject, any exam board, any country.

7. **What's next (15s):** Multi-subject expansion, adaptive Graphiti student model, Boss Battle exam mode.

**Fallback if Reachy integration doesn't land by 10 May:** The video is still strong without Scholar. Open WebUI session + pipeline walkthrough + gamification design slides + architecture diagram.

---

## Reachy Mini integration timeline

**Hardware status:** Both robots (Scholar + Bridge) arrived Tuesday 6 May 2026. ✅

| Date | Milestone | Go/no-go? |
|---|---|---|
| **Friday 8 May** | Build robots after school (family time). Bonus: Scholar on WiFi, dashboard reachable from MacBook. | — |
| **Saturday 9 May** | SDK hello world. Antenna wiggle, Daemon reachable from MacBook. | ✅/❌ Go/no-go criterion 2 |
| **Sunday 10 May** | Hard integration deadline. Dedicated Claude Code thread → Scenario 1: `external_content/` profile, `QueryStudentModelTool` reading Graphiti, Scholar speaks a progress report. | ✅/❌ Integration go/no-go |
| **Mon–Wed 11–13 May** | Video shoot window. Hackathon video with Open WebUI + Scholar. DDD dry runs. | — |
| **Thu–Fri 14–15 May** | DDD final prep, slides, full dry runs. | — |
| **Saturday 16 May** | DDD Southwest. | — |
| **Sunday 18 May** | Hackathon submission deadline (23:59 UTC). | — |

**If SDK hello world fails Saturday:** Stop Reachy work. Fall back to pre-recorded future-vision segment. No sunk-cost continuation.

**Reachy is NOT going to Bristol.** Slide/clip only.

---

## Dev work remaining (prioritised)

### Must-have for DDD (16 May)

| # | Item | Owner | Status | Estimate |
|---|---|---|---|---|
| 1 | Forge gap F010.L (autobuild model retargeting to llama-swap) | Claude Code | In progress | 1–2 hrs |
| 2 | Forge gap F010.M (async result bridge / lifecycle emitter) | Claude Code | In progress | 2–4 hrs |
| 3 | Open WebUI → llama-swap connection on GB10 (Admin → Connections → OpenAI, URL = localhost:9000) | Rich | Not started | 15 min |
| 4 | Verify specialist-agent `serve-nats` works on GB10 Docker (dual-role compose, `AGENT_MODELS__REASONING_MODEL=local`) | Rich / Claude Code | Not started | 1–2 hrs |
| 5 | **NATS Pipe Function** — manifold exposing architect, product-owner, forge as Open WebUI models; publishes to NATS, returns response | Claude Code | Not started | 4–6 hrs |
| 6 | Open WebUI demo presets — display names, system prompt context for each agent model | Rich | Not started | 30 min |
| 7 | Pre-create FastAPI feature spec for Demo 2 | Rich | Not started | 30 min |
| 8 | Prepare architect-align input using study-tutor architecture (ADR-FLEET-002) | Rich | Not started | 30 min |
| 9 | Set up split-screen presenter layout (Open WebUI + terminal tailing NATS / llama-swap logs) | Rich | Not started | 30 min |
| 10 | Dry run all three demos end-to-end via Open WebUI | Rich | After 1–9 | Half day |

### Must-have for hackathon (18 May)

| # | Item | Owner | Status | Estimate |
|---|---|---|---|---|
| 11 | **Study-tutor `serve-nats` mode** — NATS subscriber calling the orchestrator's session lifecycle | Claude Code | Not started | 4–6 hrs |
| 12 | Add study-tutor to Pipe Function manifold | Claude Code | Not started | 30 min |
| 13 | Reachy SDK hello world (Saturday 9 May) | Rich | Not started | 1–2 hrs |
| 14 | Reachy Scenario 1 integration via Claude Code (Sunday 10 May) | Claude Code | Not started | 4–6 hrs |
| 15 | Specialist-agent RAG: patch ingestion script (Ollama → llama-swap endpoint), run ingest on GB10 | Claude Code | Not started | 1–2 hrs |
| 16 | Study-tutor RAG: write ingestion script, populate sources, wire CLI | Claude Code | Not started | 4–6 hrs |
| 17 | Record hackathon video (Mon–Wed 11–13 May) | Rich | Not started | Half day |
| 18 | Finalise public repo, README, technical write-up | Rich | Partially done | 1 day |
| 19 | Kaggle submission | Rich | Not started | 1 hour |

### Already done (no further dev work)

- Architect agent logic: ✅ Fine-tuned model validated, comparison methodology documented, `serve-nats` mode exists in specialist-agent
- Study tutor agent logic: ✅ Player-Coach pipeline working, `<think>` stripping, revise path exercised, Graphiti write-back confirmed
- Open WebUI deployed on GB10: ✅ Seven subject presets for Lilymay, Docker container running
- Specialist-agent Docker: ✅ `docker-compose.dual-role.yml` exists, architect + product-owner in same container
- Reachy research: ✅ Conversation starter written, `external_content/` architecture designed, `QueryStudentModelTool` skeleton exists
- Hackathon submission plan: ✅ Full plan with deliverables mapping, timeline, risk assessment
- nats-core contract library: ✅ Shared Pydantic schemas, NATS client, 97% test coverage

### Parallel workstreams (Rich, not Claude Code)

- Slides and talk narrative
- Hackathon video scripting and recording
- Public repo preparation

---

## Risks

| Risk | Mitigation |
|---|---|
| **NATS Pipe Function is new code under demo pressure** | ~100 lines of Python. specialist-agent `serve-nats` is proven. Risk is in the glue, not the components. If Pipe Function fails: fall back to terminal-triggered demos (still via NATS, just not through Open WebUI). |
| **Study-tutor `serve-nats` doesn't land in time** | For DDD: demo architect + product-owner via NATS Pipe Function; study-tutor falls back to direct Open WebUI → llama-swap connection (already working for Lilymay). For hackathon: same fallback — still a strong video. |
| **Forge gap features don't land in time** | Demo 2 becomes a slide walkthrough. Demos 1 + 3 carry the live demo weight. Two live demos is still strong. |
| **llama-swap model swap latency on stage** | Pre-warm models before going on stage (send dummy request 2 min before each demo). llama-swap `/logs/stream` lets Rich monitor warm-up from terminal pane. |
| **GB10 unreachable from Bristol (network)** | Pre-check Tailscale before leaving home; mobile hotspot as backup; all demos rehearsed over Tailscale beforehand. Open WebUI is accessed via browser — any network path works. |
| **Open WebUI container needs `nats.py` installed** | Pipelines container supports pip install via requirements. Alternatively, use Open WebUI Workspace Functions (run in main process). Test during item 5. |
| **Reachy SDK doesn't cooperate Saturday** | Hard stop. Fall back to future-vision segment. |
| **Reachy integration doesn't complete Sunday** | Same fallback. Gamification dashboard mockup fills the visual slot. |

---

## Superseded decisions

### From v2 (superseded by v3)

- **Claude Desktop as demo surface:** Replaced by Open WebUI + NATS Pipe Functions. Audience perception problem ("he's just using Claude") was the driver. Claude Desktop remains the development workflow tool.
- **Split-screen with Claude Desktop:** Replaced by split-screen with Open WebUI. Same concept, different UI surface.
- **MCP as the connection to agents:** Replaced by NATS. MCP solved the wrong problem (tool discovery and routing for general-purpose assistants). Purpose-built agents don't need tool discovery — the user selects the agent from a dropdown.
- **Agents running on Mac:** Moved to GB10 (Docker). Co-location eliminates cross-network inference calls and aligns with the dark factory thesis.
- **ChromaDB topology undecided (ASSUM-002):** Resolved — PersistentClient on GB10, embeddings via llama-swap.
- **Ollama for embeddings:** Replaced by llama-swap `/v1/embeddings`. One inference front door.

### From v1 (superseded by v2, still superseded)

- Option B/C/D (Telegram adapters): Not building.
- FinProxy as architect demo content: Client-confidential.
- Real autobuild on stage: Too fragile.
- Reachy live on stage at DDD: Transport + conference WiFi risk.

---

*Strategy v3: 7 May 2026*
*Supersedes: v2 (Claude Desktop surface), v1 (conversation starter)*
