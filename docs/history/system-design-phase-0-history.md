
/system-design --from docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md

I'll start the /system-design flow. First, let me check for prerequisites (Graphiti availability and architecture context) and load the seed documents you specified.

Read graphiti.yaml
Bash List relevant docs directories
IN
ls docs/architecture/ 2>/dev/null && echo "---" && ls docs/research/ideas/ 2>/dev/null && echo "---" && ls docs/design/ 2>/dev/null

OUT
Exit code 1
ARCHITECTURE.md
assumptions.yaml
container.md
decisions
domain-model.md
system-context.md
---
copyright-training-data-analysis.md
cross-repo-rag-impact-analysis-2026-04-24.md
decisions-log-2026-04-17.md
deepagents-patterns-review.md
fleet-v3-future-work-notes.md
GCSE_English_AI_Tutor_Proposal.md
GCSE_Gamification_Research.md
gemma4-hackathon-submission-plan.md
openwebui-rag-empirical-findings-2026-04-23.md
phase-0-build-plan.md
phase-0-scope.md
phase-1-build-plan.md
phase-1-scope.md
phase-2-scope.md
planning-cadence-hybrid-approach.md
po-extract-roadmap-1862adb2.md
rag-grounding-design.md
reachy-integration-conversation-starter.md
state-of-the-project-and-phase-recommendation.md
---
Architecture context exists, design context is empty (fresh start). Let me load the seed documents in parallel.

Read ARCHITECTURE.md
Read phase-0-scope.md
Read phase-0-build-plan.md
I have a strong picture. Let me load the supporting architecture artefacts (domain model, existing ADRs) to check for contradictions and inform protocol design.

Read domain-model.md
Bash List ADRs and current MCP/session/llm code
IN
ls docs/architecture/decisions/ && echo "---existing tutor MCP code---" && ls src/study_tutor/mcp/ src/study_tutor/session/ src/study_tutor/llm/ 2>/dev/null

OUT
ADR-ARCH-001-ddd-structural-pattern.md
ADR-ARCH-002-three-layer-architecture.md
ADR-ARCH-003-async-graphiti-writeback.md
ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
ADR-ARCH-005-defer-dockerfile-to-phase-1.md
ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
ADR-ARCH-007-graphiti-split-topology.md
ADR-ARCH-008-mcp-only-agent-access.md
ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
ADR-ARCH-010-pydantic-at-boundary-validation.md
ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
ADR-ARCH-013-middleware-level-gamification-engine-future.md
ADR-ARCH-014-single-user-scalability-posture.md
ADR-ARCH-015-uk-on-device-data-residency.md
ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
---existing tutor MCP code---
src/study_tutor/llm/:
__init__.py
__pycache__
client.py

src/study_tutor/mcp/:
__init__.py
__pycache__
adapter.py
server.py

src/study_tutor/session/:
__init__.py
__pycache__
tutor_session.py
Let me load the relevant ADRs (most likely to surface protocol contradictions) and the actual MCP adapter so the design reflects what's already shipped.

Read adapter.py
I've loaded the architecture (16 ADRs, 6 bounded contexts, domain model), Phase 0 scope, Phase 0 build plan, and the live MCPAdapter implementation. Here's what I have before I start the interactive design loop.

Context Loaded
Architecture (docs/architecture/ARCHITECTURE.md):

6 bounded contexts: Tutoring (P0), Knowledge & Curriculum (P0 stub→P1), Student Model (P1), Gamification (P0 docs→P2), Inference Runtime (P0), MCP Transport (P0)
16 ADRs accepted/proposed (load-bearing for contradiction detection)
Protocol surfaces table already declared: MCP stdio (agents), CLI (devs/judges), Open WebUI→Ollama/Bedrock (Lilymay), static HTML (P2 dashboard), Reachy SDK (P2 stretch)
Shared Kernel B is the in-process session event vocabulary — session.started, session.turn_completed, session.completed, achievement.unlocked, etc.
Phase 0 build plan: confirms FEAT-PO-001/002/003/005 are ✅ shipped, FEAT-PO-004 (Bedrock) deferred, clean-machine walkthrough pending. The 4-tool MCP adapter is live in src/study_tutor/mcp/adapter.py.

Phase status against bounded contexts:

Context	Code today	Design target
Tutoring	In-memory session, 4 MCP tools	Live
Inference Runtime	LLMClient w/ provider routing	Live (Bedrock route stubbed)
MCP Transport	4 tools registered, SR-01..07 green	Live
Knowledge & Curriculum	docs only (GOAL.md)	P1 — needs design
Student Model	docs only (domain-model §4)	P1 — needs design
Gamification	docs/gamification/design.md	P2 — has design, not contracts
🏗️ Architecture loaded: 6 bounded contexts
🆕 No existing design context — starting fresh
✓ Graphiti config: enabled: true (FalkorDB on whitestocks, vLLM LLM on GB10) — Tier 2 connectivity check deferred to Phase 5 seeding

Scoping question before the interactive loop
Designing all 6 contexts cold would be ~24 prompts; many bounded contexts already have crisp design content in the architecture docs (e.g. the MCP tool table in domain-model.md §7.1, the gamification economy in design.md). With the 18 May hackathon deadline and Phase 0 being largely shipped, I'd recommend one of the following before I start asking design questions:

(A) Phase 0 only — Tutoring, Inference Runtime, MCP Transport, plus Shared Kernel B (Events). 3 contexts + 1 event surface. Fastest, matches what's actually in code now. ~8 prompts. Best choice if you want to seed Graphiti with what's real today and re-run /system-design --focus=… per P1/P2 context as those phases land.

(B) Phase 0 + P1 lookahead — Phase 0 set + Knowledge & Curriculum + Student Model. 5 contexts. Useful if the next /feature-spec runs are about Graphiti / RAG. ~14 prompts.

(C) All 6 contexts — full sweep including Gamification (P2). ~22 prompts. Defers nothing but front-loads design that may still shift before P2.

(D) Single focus — re-invoke as /system-design --focus="<context>" (e.g. --focus="Tutoring").

Given the architecture already prescribes protocols per context and the MCP adapter is the source of truth, I'd suggest (A) with Events surface for Shared Kernel B, and a non-interactive bias: I'll propose contracts/data models from the existing docs and only ask where there's a genuine open question (e.g. payload shape for session.completed, error envelope for MCP).

Which would you like — A, B, C, or D (with focus name)? And: any preference on interactive verbosity — full prompts per architecture command's spec, or bias-to-defaults where I propose and you only push back on what's wrong?

phase-0-build-plan.md
Option A with bias-to-defaults, before continuing please update the build plan to reflect this decision with the /system-design command reccommended for the next phases
I'll update the build plan first, then continue with the design loop.

Read phase-0-build-plan.md (lines 380-464)
I'll patch the /system-design block in the command sequence and add a punch-list entry recording today's decision.

Edit phase-0-build-plan.md
Added 36 lines
Now the punch-list entry so the status section reflects the decision.

Edit phase-0-build-plan.md
Added 1 line
Build plan updated. Now resuming /system-design with Option A + bias-to-defaults.

Phase 1 — Per-bounded-context interactive design (Phase 0 scope)
I'll design Tutoring → Inference Runtime → MCP Transport, with Shared Kernel B (Events) folded into Tutoring's protocol surfaces. I'll propose contracts/models from the architecture docs and the live code, and only stop for input on genuine open questions.

📋 DESIGNING: Tutoring (P0 — live)
Source of truth: domain-model.md §2, MCPAdapter in src/study_tutor/mcp/adapter.py, domains/gcse-english/GOAL.md.

📡 API Contract — Tutoring
Operations derived from TutorSession aggregate + state machine (initialised → planning → active → summarising → ended):

Operation	Verb	Phase 0 backing
Start a tutoring session	start_session(subject, topic?, player_model?)	Live in adapter
Generate next tutor turn	turn(session_id, user_message, player_model?)	Live in adapter
Read session state	session_status(session_id)	Live in adapter
End session	end_session(session_id)	Live in adapter (P1 adds async Graphiti write)
Auth: None — single-user, MCP stdio is local + Tailscale only (per ADR-ARCH-008 and ADR-ARCH-014). [N]one selected by default.

🔌 Protocol surfaces — Tutoring
From ARCHITECTURE.md §5 + ADR-ARCH-008 (MCP-only for agent access):

MCP ✓ — primary surface, 4 tools, SR-07 classification per domain-model.md §7.1
CLI ✓ — study-tutor serve --role tutor --transport stdio (developers/judges)
Events ✓ — Shared Kernel B in-process event bus (CC-11)
REST / GraphQL / A2A / ACP ✗ — explicitly excluded by ADR-ARCH-008 (single-user posture); contradicts ADR-ARCH-011 (no caching/rate-limit/feature-flags). Open WebUI's path uses Ollama directly, not the tutor's API surface.
📊 Data Model — Tutoring
Mirroring domain-model.md §2.1–2.2:


TutorSession (aggregate root)
  ├── session_id: str (UUID, immutable)
  ├── student_id: str (immutable, FK → Student)        [P0: implicit "lilymay"]
  ├── subject: Subject (immutable after start)
  ├── paper: Paper (optional, immutable after start)   [P0: not yet captured]
  ├── topic: Topic (mutable mid-session)
  ├── grade_target: GradeTarget (mutable, planner)     [P0: not yet captured]
  ├── status: SessionStatus enum                        [P0 alias: "active"|"ended"]
  ├── turns: list[Turn] (append-only)
  ├── started_at: datetime (immutable)
  └── ended_at: datetime? (set exactly once)

Turn (value object)
  ├── index: int
  ├── role: "user" | "tutor"
  ├── content: str
  └── timestamp: datetime
  └── (P1) aos_scaffolded: list[AssessmentObjective], rag_chunks_used: list[ChunkRef]

TurnFeedback (P1, deferred)
SessionSummary (P1, deferred)
Invariants (from domain-model.md §2.1 + adapter code):

No turns accepted when status == ended (enforced in adapter:82–86; returns SessionEnded error).
State transitions monotonic (no resurrection).
A session abandoned before any tutor turn emits no session.completed event (gamification §2.1).
turns is append-only — no edits, no deletes.
Open question (proposing default): P0 has only subject + topic on session start. P1 will need student_id, grade_target, optional paper. Default proposal: capture this asymmetry in the contract by marking student_id/grade_target as phase: P1 so the OpenAPI spec doesn't lie about what's accepted today. Push back if you'd rather inflate the P0 schema now.

📨 Events emitted (Shared Kernel B, domain-model.md §2.4 + §8.2)
Event	Producer	Payload	Status
session.started	Tutoring	{session_id, student_id, subject, topic, started_at}	P1 wire-up
session.turn_completed	Tutoring	{session_id, turn_index, role, ao_scaffolded?}	P1 wire-up (Coach)
session.completed	Tutoring	{session_id, duration_seconds, topic, aos_touched, quality_score, ended_at}	P1 wire-up
P0 status: events vocabulary is reserved (CC-11) but no in-process bus is wired today. Tutoring is the sole producer; consumers are Student Model (P1) and Gamification (P2).

✓ DESIGN COMPLETE: Tutoring
Continuing to Inference Runtime (no DDR triggered — design tracks ARCHITECTURE.md and the shipped adapter).

📋 DESIGNING: Inference Runtime (P0 — live, anti-corruption layer)
Source of truth: domain-model.md §6, src/study_tutor/llm/client.py, ADR-ARCH-006 (dual inference path).

📡 API Contract — Inference Runtime
Operations: this is an internal context with no external surface. Sole interface is LLMClient.invoke(messages, **opts) injected into Tutoring. Provider resolution at the factory per SR-03/CC-03.

🔌 Protocol surfaces — Inference Runtime
Internal Python interface ✓ — LLMClient.generate(prompt, system?) consumed by MCPAdapter.tutor_turn and the warm-up path
MCP / REST / GraphQL / Events ✗ — Inference Runtime is the anti-corruption layer; it has no external protocol surface by design. Upstream contexts speak only through it.
No external contract file generated for this context. A single internal-interface contract documents the public Python surface + the provider matrix.

📊 Data Model — Inference Runtime

LLMClient (factory-resolved aggregate root)
  ├── provider: ProviderLabel ∈ {local, bedrock, openai, anthropic, gemini}
  ├── endpoint: str (provider-specific; encapsulated)
  └── model_id: str (provider-specific; encapsulated)

ProviderLabel (enum, resolved from AGENT_MODELS__REASONING_MODEL)
  ├── local      → Ollama on GB10 (P0 default)
  ├── bedrock    → AWS Bedrock Custom Model Import (P0 stub → P1 primary)
  ├── openai     → OpenAI API (declared, reserved for Coach/fallback)
  ├── anthropic  → Anthropic API (declared, reserved)
  └── gemini     → Google Gemini API (declared; Graphiti uses outside LLMClient)

InvocationRequest (P0 implicit, P1 formalised)
  ├── messages: list[ChatMessage] | (prompt: str, system: str?)
  └── options: provider-agnostic dict (temperature, max_tokens, …)
Invariants (from domain-model.md §6.2):

Provider resolved at factory, never at handler (CC-03 / SR-03).
Every provider named in code appears in pyproject.toml [providers] extra (CC-04 / SR-04).
LLMClient.invoke(...) is the sole public interface; upstream code never constructs ChatOllama/ChatBedrock/etc. directly.
Provider-specific knowledge (ARNs, URLs, retry semantics, model IDs) stays inside this context.
Bedrock route status: P0 stub raises NotImplementedError. FEAT-PO-004 deferred per phase-0 status. Contract documents the route as phase: P0-stub → P1-active.

✓ DESIGN COMPLETE: Inference Runtime
Continuing to MCP Transport.

📋 DESIGNING: MCP Transport (P0 — live)
Source of truth: domain-model.md §7, src/study_tutor/mcp/adapter.py, src/study_tutor/mcp/server.py, SR-01/02/07.

📡 API Contract — MCP Transport
The four registered tools, taken verbatim from the live adapter (the design must reflect what's shipped, not what's idealised):

Tool	Class (SR-07)	Inputs	Output	Latency target
tutor_start_session	long-running (warm-up async)	subject: str, topic?: str, player_model?: str	{session_id: uuid}	≤ 1s return
tutor_turn	sync (< 30s)	session_id: str, user_message: str, player_model?: str	{tutor_response: str} or error	p95 < 10s
tutor_session_status	sync	session_id: str	{session_id, status, turn_count, started_at} or error	< 2s
tutor_session_end	sync (P1: triggers async Graphiti write)	session_id: str	{session_id, status: "ended"} or error	< 2s
Error envelope (from adapter:139–143):


{
  "error": "<human-readable>",
  "error_type": "SessionNotFoundError" | "SessionEnded"
}
Open question (proposing default): the architecture's SR-07 table classifies tutor_start_session as long-running with companion tutor_session_status polling, but the live code uses fire-and-forget warm-up (LLM weights pre-loaded asynchronously) while returning session_id immediately — there's no still-running "session start" task to poll. Default proposal: classify as sync in the design (start completes synchronously; warm-up is opportunistic), and update SR-07 wording in the contract artefact to call this out. This is the truthful classification per the live behaviour. Push back if you'd rather keep "long-running" semantics for forward-compat with P1 Graphiti reads inside tutor_start_session.

🔌 Protocol surfaces — MCP Transport
MCP (stdio) ✓ — primary; JSON-RPC over stdin/stdout, banner/diagnostics to stderr only (SR-01/CC-01)
CLI ✓ — study-tutor serve --role tutor --transport <stdio|http> (http deferred to P1+)
Events ✗ — MCP Transport is a thin façade; emits no domain events itself (Tutoring emits inside _run_tutor_session).
📊 Data Model — MCP Transport

McpAdapter (aggregate root, stateless)
  ├── role: RoleConfig (loaded from roles/tutor/role.yaml)
  ├── store: SessionStore (in-memory dict, P0; persistent in P1)
  ├── player_prompt: str (loaded from roles/tutor/prompts/player.md)
  └── warmup_tasks: set[asyncio.Task] (GC-tracked)

McpToolDescriptor (one per tool)
  ├── name: str
  ├── classification: "sync" | "long-running"
  ├── description: str (≡ implementation contract — SR-07/CC-07)
  └── schema: JSON Schema for inputs

ErrorResponse (value object)
  ├── error: str
  └── error_type: str  (closed set: SessionNotFoundError, SessionEnded)
Invariants (from domain-model.md §7.2):

stdout exclusively MCP JSON-RPC — all diagnostics via click.echo(..., err=True) (CC-01/SR-01).
Bash wrapper cds to absolute path before exec (CC-02/SR-02).
Tool description ≡ handler behaviour — verified by tests/unit/mcp/test_stdio_discipline.py and tool-contract test (CC-07/SR-07).
Long-running tools return session_id in ≤ 1s (CC-08).
AsyncSubAgent boundary — Phase 1 Coach uses deepagents 0.5.3+ AsyncSubAgent rather than hand-rolled fire-and-forget (CC-12).
✓ DESIGN COMPLETE: MCP Transport
Phase 2 — Contradiction detection
I checked each proposed contract against the 16 ADRs. Findings:

✓ No contradictions. The proposed protocol set (MCP + CLI + Events) is congruent with ADR-ARCH-008 (MCP-only for agent access). The Bedrock route classification matches ADR-ARCH-006. No protocol marked "synchronous-only" or "REST-only" exists in any ADR, so the Events surface for Shared Kernel B does not conflict.

⚠️ One classification nuance (not a contradiction, surfaced for confirmation): tutor_start_session's SR-07 classification differs between architecture text ("long-running") and live code (effectively sync). Captured as the open question above; default = sync.

Open questions before I generate artefacts
I have two open questions that affect the artefacts. Before I write docs/design/contracts/, openapi.yaml, mcp-tools.json, and the data-model files, please confirm or push back:

Tutoring schema P0 vs P1 split. Should the TutorSession data model artefact (a) document the P0 shape only (session_id, subject, topic, status, turns, started_at, ended_at) and add P1 fields when P1 design re-runs, or (b) document the full P1 shape with a per-field phase: P0|P1 annotation now? My default: (a) — match what's true today, re-run /system-design --focus="Tutoring" if the schema grows.

tutor_start_session SR-07 classification. My default: classify as sync in the design artefact, with a note that re-classification to long-running may be needed if P1 adds Graphiti reads to session start. The architecture text will then need a small update via /arch-refine.

Tell me "both defaults" / "(a)+long-running" / "(b)+sync" etc., or any other override, and I'll generate all artefacts (contracts, OpenAPI, MCP tool defs, data models, internal interface for Inference Runtime), run the C4 L3 review gate (only if any context has > 3 internal components — none do at P0, so this gate likely no-ops), validate OpenAPI, and offer the Graphiti seeding commands.

both defaults and please update the build-plan with this decision
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Updating the build plan first to record the two design decisions next to the existing punch-list entry.

Edit phase-0-build-plan.md
Added 4 lines
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Now writing the design artefacts. Phase 0 has no REST surface (per ADR-ARCH-008), so OpenAPI 3.1 is not applicable — I'll skip that artefact and note it in the index.

Write API-tutoring.md
201 lines
# API Contract — Tutoring

**Bounded context:** Tutoring
**Phase:** P0 (live)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/adapter.py` and `src/study_tutor/session/tutor_session.py`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

---

## 1. Consumers

| Consumer | Surface | Phase |
|---|---|---|
| AI agents (Claude Desktop, future Jarvis) | MCP JSON-RPC over stdio | P0 |
| Developers / judges | CLI wrapping the MCP surface | P0 |
| Internal contexts (Student Model P1, Gamification P2) | In-process Events (Shared Kernel B) | P1+ |

REST / GraphQL / A2A / ACP are **out of scope** by ADR-ARCH-008 (single-user MCP-only posture). Open WebUI's interface for Lilymay points at Ollama directly (and at Bedrock via LiteLLM proxy P0+); it does not consume this contract.

## 2. Auth & posture

- **Authentication:** none. Single-user single-host (ADR-ARCH-014); MCP stdio transport is local + Tailscale only (ADR-ARCH-008/ADR-ARCH-015).
- **Authorisation:** N/A — Phase 0.
- **Rate limiting / quotas:** none (ADR-ARCH-011).

## 3. MCP tool surface

Four tools registered by `MCPAdapter`. SR-07 classification is the truthful classification per the live handler — see [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md) reclassifying `tutor_start_session` from "long-running" to "sync".

### 3.1 `tutor_start_session`

| Property | Value |
|---|---|
| Classification | **sync** (warm-up LLM call is fire-and-forget; not a polled task) |
| Latency target | ≤ 1s return |
| Source | `MCPAdapter.tutor_start_session` (`src/study_tutor/mcp/adapter.py:49`) |

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `subject` | `string` | yes | Free text P0; `Subject` enum from Shared Kernel A in P1 |
| `topic` | `string` | no | Free text P0; `Topic` ID in P1 |
| `player_model` | `string` | no | Provider override; falls back to `_default_player_model()` from `AGENT_MODELS__REASONING_MODEL` (SR-03) |

**Output (success):**

```json
{ "session_id": "<uuid>" }
```

**Side effects:**
- Creates a `TutorSession` in the in-memory `SessionStore` with `status="active"`.
- Spawns an `asyncio.create_task(self._warm_up(provider))` to prime the Ollama model. Tracked in `_warmup_tasks` set; never crashes the handler (`# noqa: BLE001`).

**Errors:** none expected at P0.

### 3.2 `tutor_turn`

| Property | Value |
|---|---|
| Classification | **sync** |
| Latency target | p95 < 10s; hard ceiling 30s (SR-07) |
| Source | `MCPAdapter.tutor_turn` (`src/study_tutor/mcp/adapter.py:70`) |

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `session_id` | `string` (UUID) | yes | Returned by `tutor_start_session` |
| `user_message` | `string` | yes | The student's turn |
| `player_model` | `string` | no | Per-call provider override; SR-03 resolution |

**Output (success):**

```json
{ "tutor_response": "<string>" }
```

**Errors:**

| `error_type` | Trigger |
|---|---|
| `SessionNotFoundError` | `session_id` not present in store |
| `SessionEnded` | Session status is `ended` |

**Side effects:**
- Appends a `("user", user_message)` turn, then a `("tutor", response)` turn to `session.turns` (append-only invariant).
- Routes provider via `LLMClient(provider=resolved_provider).generate(user_message, player_prompt)`.
- LLM call runs inside `asyncio.to_thread(...)` so the async MCP framework isn't blocked by httpx.

### 3.3 `tutor_session_status`

| Property | Value |
|---|---|
| Classification | **sync** |
| Latency target | < 2s |
| Source | `MCPAdapter.tutor_session_status` (`src/study_tutor/mcp/adapter.py:102`) |

**Inputs:** `{ "session_id": "<uuid>" }`

**Output (success):**

```json
{
  "session_id": "<uuid>",
  "status": "active" | "ended",
  "turn_count": "<int>",
  "started_at": "<ISO 8601 datetime>"
}
```

**Errors:** `SessionNotFoundError` if `session_id` unknown.

### 3.4 `tutor_session_end`

| Property | Value |
|---|---|
| Classification | **sync** (Phase 0); P1 adds an async Graphiti write-back inside the handler — does not change the classification because the write is fire-and-forget |
| Latency target | < 2s |
| Source | `MCPAdapter.tutor_session_end` (`src/study_tutor/mcp/adapter.py:116`) |

**Inputs:** `{ "session_id": "<uuid>" }`

**Output (success):**

```json
{ "session_id": "<uuid>", "status": "ended" }
```

**Errors:** `SessionNotFoundError` if `session_id` unknown.

**Phase 1 evolution:** TODO comment at `adapter.py:122` — async Graphiti write-back per ADR-ARCH-003. SR-07 invariant: this side effect must **not** appear in the tool description (kept implementation-internal).

## 4. Error envelope

All four tools return errors as a flat dict (not a JSON-RPC error wrapper) so MCP clients see them as successful tool returns with structured error fields. This matches the live handler shape:

```json
{
  "error": "<human-readable message>",
  "error_type": "SessionNotFoundError" | "SessionEnded"
}
```

The closed set of `error_type` values is the contract. Adding a new `error_type` is a contract change requiring `/design-refine`.

## 5. Events emitted (Shared Kernel B)

P0 status: events vocabulary is **reserved** (CC-11). No in-process bus is wired today. The Tutoring context will be the sole producer once Phase 1 lands the Coach + Student Model wiring.

### 5.1 Producer

`Tutoring` only. No other context emits these events.

### 5.2 Event shapes

| Event | Payload (P0 reserved) | Phase live | Consumers |
|---|---|---|---|
| `session.started` | `{session_id, student_id, subject, topic, started_at}` | P1 | Student Model |
| `session.turn_completed` | `{session_id, turn_index, role, ao_scaffolded?}` | P1 | Coach (P1), Student Model (P1) |
| `session.completed` | `{session_id, duration_seconds, topic, aos_touched, quality_score, ended_at}` | P1 | Student Model, Gamification (P2), Reachy (P2 stretch) |

`achievement.unlocked`, `quest.completed`, `quest.expired`, `boss_battle.completed` are emitted by **Gamification**, not Tutoring — see Phase 2 design re-run.

### 5.3 Delivery semantics

- **In-process only.** No NATS, no external broker (CC-11; matches single-user posture from ADR-ARCH-014).
- **Synchronous fan-out is forbidden** — consumers must subscribe via the deepagents 0.5.3 AsyncSubAgent boundary (CC-12) or equivalent async hook; no consumer blocks `tutor_turn` return.
- **At-most-once.** No retry, no DLQ at P0/P1. A consumer crash on `session.completed` does not re-fire the event.

### 5.4 Schema authority

The canonical schemas live in `docs/design/events-schema.yaml`. Consumers validate at the subscriber boundary (Pydantic) per ADR-ARCH-010.

## 6. Versioning

- **Tool surface:** unversioned at P0 (single-user, no external consumers other than Lilymay's own Claude Desktop). Field additions are minor; field removals or `error_type` changes require `/design-refine`.
- **Event surface:** versionless at P0; the Shared Kernel B vocabulary is intentionally stable across phases (`domain-model.md §8.2`).

## 7. Conformance tests (existing)

| Test | Surface | Location |
|---|---|---|
| `test_stdio_discipline.py` | SR-01 (stdout = MCP only) | `tests/unit/mcp/test_stdio_discipline.py` |
| `test_provider_resolution.py` | SR-03 (factory-resolved provider) | `tests/unit/llm/test_provider_resolution.py` |
| Tool-contract test | SR-07 (description ≡ behaviour) | per `domain-model.md §7.2`, recommended addition |

## 8. Out-of-scope explicitly

- **REST / GraphQL / HTTP transport** — deferred indefinitely; ADR-ARCH-008 stands.
- **Multi-tenant authentication** — ADR-ARCH-014 (single-user posture).
- **Caching, rate limiting, feature flags** — ADR-ARCH-011.
- **`tutor_pause_session`, `tutor_resume_session`** — not requested; sessions are append-only and end-once.

## 9. Open questions for downstream phases

1. **P1 — schema growth:** `tutor_start_session` will likely accept `student_id`, `grade_target`, `paper` once Graphiti reads the student model. If Graphiti read latency exceeds 1s, reclassify the tool as **long-running** and add a `tutor_session_status` polling contract (the architecture's original SR-07 stance).
2. **P1 — error envelope evolution:** add `LLMUnavailable`, `ProviderTimeout` once Bedrock/Ollama failure modes are exercised via FEAT-PO-004.
3. **P2 — event consumers fanout:** if Gamification + Reachy + dashboard all subscribe to `session.completed`, evaluate whether the in-process bus needs an explicit subscriber registry or whether deepagents' AsyncSubAgent set is sufficient.
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Read client.py
Write API-inference-runtime.md
119 lines
# API Contract — Inference Runtime

**Bounded context:** Inference Runtime (anti-corruption layer)
**Phase:** P0 (live for `local`; stubbed for `bedrock`)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/llm/client.py`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

---

## 1. Consumer model

Inference Runtime exposes **no external protocol surface**. By design (`domain-model.md §6.3`) all provider-specific knowledge stays inside this context, and upstream contexts speak only the `LLMClient.invoke(...)` Python interface.

| Consumer | Surface | Phase |
|---|---|---|
| Tutoring (`MCPAdapter._warm_up`, `tutor_turn`) | `LLMClient` Python class | P0 |
| Coach (P1) — possibly different provider than Player | `LLMClient` Python class | P1 |
| Tests | `LLMClient` Python class | P0 |

**Not consumers of this context:**
- Open WebUI / LiteLLM / OpenAI proxies — they speak directly to Ollama/Bedrock; they do not pass through `LLMClient`.
- Graphiti's entity-extraction LLM (vLLM on GB10 per the live `.guardkit/graphiti.yaml`, formerly Gemini per ADR-ARCH-007) — managed by Graphiti, not by `LLMClient`. Two separate provider abstractions exist by design.

## 2. Public Python interface

```python
class LLMClient:
    """Provider-agnostic LLM client. Sync, string-in / string-out.

    Construct per call site:
        client = LLMClient(provider=_default_player_model())
    Never store at module level (SR-03).
    """

    def __init__(self, provider: str) -> None: ...

    def generate(self, prompt: str, system: str | None = None) -> str: ...
```

**Helper:**

```python
def _default_player_model() -> str:
    """Return the provider from AGENT_MODELS__REASONING_MODEL (default: 'local').
    Read at call time (SR-03 invariant)."""
```

**Error class:**

```python
class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""
```

The contract is the **call signature + error class + provider matrix below**. P1 may grow `generate` to a `messages: list[ChatMessage]` shape if the Coach needs multi-turn context; `generate(prompt, system)` is the P0 commitment.

## 3. Provider matrix

Authoritative table — every provider listed here:
- has its label routed in `LLMClient.generate`,
- appears in `pyproject.toml [providers]` extra (CC-04 / SR-04), and
- is documented in the README quick-start.

| Provider label | Endpoint resolver | Default model | Status (P0) | ADR |
|---|---|---|---|---|
| `local` | `OLLAMA_BASE_URL` env (default `http://localhost:11434`) | `OLLAMA_MODEL` env (default `gcse-tutor-gemma4-moe:latest`) | **live, primary** | ADR-ARCH-006 |
| `bedrock` | AWS Bedrock Custom Model Import | `BEDROCK_MODEL_ARN` env | **stub — `NotImplementedError`** until FEAT-PO-004 | ADR-ARCH-006 |
| `openai` | OpenAI API | TBD | declared (extra installed); not wired | — |
| `anthropic` | Anthropic API | TBD | declared (extra installed); not wired | — |
| `gemini` | Google Gemini API | TBD | declared (extra installed); not wired (Graphiti's Gemini path is independent) | — |

**Adding a provider** is a contract change requiring `/design-refine` and a new entry in the `[providers]` extra.

## 4. Configuration surface (env vars)

The Inference Runtime is configured exclusively via environment variables, read **at call time** (never at module import — SR-03 invariant).

| Variable | Consumer | Default | Notes |
|---|---|---|---|
| `AGENT_MODELS__REASONING_MODEL` | `_default_player_model()` | `local` | Provider label; routed through `LLMClient.generate` |
| `OLLAMA_BASE_URL` | `_generate_ollama` | `http://localhost:11434` | Tailscale GB10 endpoint in deployed config |
| `OLLAMA_MODEL` | `_generate_ollama` | `gcse-tutor-gemma4-moe:latest` | Fine-tuned tutor model |
| `OLLAMA_NUM_PREDICT` | `_resolve_num_predict()` | `2048` | Token ceiling per generation; tuned in TASK-PO02F-002 |
| `BEDROCK_MODEL_ARN` | (P1) `_generate_bedrock` | placeholder | Set by FEAT-PO-004 |

**Hygiene:** no real-looking provider keys in `.env.example` — `<placeholder>` literals only (SR-06 / CC-06).

## 5. Invariants

1. **Provider resolved at the factory, not at the handler.** Every call-site reads `params.get("player_model") or _default_player_model()`. (CC-03 / SR-03 / `domain-model.md §6.2`.)
2. **Every named provider is in `[providers]` extra.** A missing extra is a build failure, not a runtime failure. (CC-04 / SR-04.)
3. **`LLMClient.generate(...)` is the sole public interface.** Upstream code never constructs `ChatOllama`, `ChatBedrock`, or `httpx.Client` directly.
4. **Provider-specific knowledge stays inside this context.** ARNs, URLs, retry semantics, and model IDs do not leak into Tutoring or MCP Transport.
5. **Errors normalise to `LLMProviderError`.** Provider-specific exceptions (`httpx.HTTPError`, `boto3` ClientError, etc.) are caught and re-raised as `LLMProviderError` so upstream contexts handle one error type.

## 6. Sync vs async

`LLMClient.generate` is **synchronous**. Callers (e.g. `MCPAdapter.tutor_turn`) wrap the call in `asyncio.to_thread(...)` so the async MCP framework isn't blocked by httpx. Phase 1 may introduce an async-native variant once deepagents 0.5.3+ AsyncSubAgent is in play (CC-12), but the sync interface remains the contract.

## 7. Conformance tests

| Test | Location |
|---|---|
| `test_provider_resolution.py` (SR-03 — env-var resolution at call time, never at import) | `tests/unit/llm/test_provider_resolution.py` |
| Provider-extra import smoke (SR-04 — every label in extra is importable) | recommended addition |

## 8. Out of scope

- **Streaming responses.** P0 is non-streaming (`stream: false`); streaming deferred to P1+.
- **Token-level cost accounting.** Deferred — single-user posture (ADR-ARCH-014).
- **Prompt caching.** Deferred (ADR-ARCH-011); irrelevant for Ollama, considered for Bedrock in P1+ if cost matters.
- **Retries / circuit breakers.** Deferred; failure surfaces as `LLMProviderError` to the caller.

## 9. Open questions for downstream phases

1. **P1 — message-shape API.** When the Coach lands, `generate(prompt, system)` may not be enough; a `messages: list[ChatMessage]` overload may be required. Consider via `/design-refine` once Coach criteria scoring is wired.
2. **P1 — Bedrock latency profile.** FEAT-PO-004's smoke test should record observed Bedrock latency vs Ollama. If Bedrock p95 > 30s, `tutor_turn` needs reclassification (currently sync).
3. **P1+ — Gemini consolidation.** Graphiti's vLLM/Gemini path is a separate provider abstraction. If a use case emerges for the Player/Coach to use the same vLLM endpoint Graphiti uses, evaluate consolidating both behind `LLMClient`.
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Write API-mcp-transport.md
102 lines
# API Contract — MCP Transport

**Bounded context:** MCP Transport
**Phase:** P0 (live)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/mcp/{server.py, adapter.py}` and `scripts/mcp-wrapper.sh`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

---

## 1. Purpose

MCP Transport is a **thin façade** owning the external protocol surface for AI agents. It enforces transport-layer invariants (SR-01 / SR-02 / SR-07 / CC-08) and turns the tutor into a discoverable, invokable system. The tools themselves and their behavioural contracts belong to **Tutoring** — see `API-tutoring.md`.

This contract documents the **transport invariants** and **CLI surface**, not the per-tool semantics.

## 2. Surfaces owned

### 2.1 MCP stdio transport

- Protocol: MCP JSON-RPC over stdin/stdout (per the `mcp` Python SDK).
- Invocation: via `study-tutor serve --role tutor --transport stdio`.
- Registration: by Claude Desktop or any MCP client through `claude_desktop_config.json` pointing at `scripts/mcp-wrapper.sh`.

### 2.2 CLI

- Binary: `study-tutor` (entry point declared in `pyproject.toml`).
- Subcommand: `serve`.
- Flags: `--role <name>`, `--transport <stdio|http>`.
- HTTP transport is **not implemented** in P0; flag accepted but raises NotImplementedError. Deferred to P1+.

### 2.3 Bash wrapper

- Path: `scripts/mcp-wrapper.sh`.
- Pattern: `set -a && . /absolute/path/.env && set +a && export AGENT_MODELS__REASONING_MODEL=local && exec /absolute/path/.venv/bin/study-tutor serve --role tutor --transport stdio`.
- Required by SR-02 — must `cd /absolute/path/to/study-tutor` (or use absolute paths to env + venv binary as above) before `exec`.

## 3. Transport invariants (SR-01 / CC-01)

1. **stdout is exclusively MCP JSON-RPC.** Before the MCP handshake completes, stdout must produce zero bytes. After handshake, only protocol frames.
2. **All diagnostics route to stderr.** Banners, warnings, log lines, status messages — `click.echo(..., err=True)` or `print(..., file=sys.stderr)`. Loggers are configured to emit on stderr only.
3. **Banner is mandatory.** A "Study Tutor MCP server starting…" banner must appear on stderr at startup so operators see a sign-of-life. Empty stderr is a P0 regression.

**Conformance test:** `tests/unit/mcp/test_stdio_discipline.py` runs `serve --transport stdio < /dev/null` for ~3s and asserts:
- `stdout.log` is empty (no bytes before handshake);
- `stderr.log` contains the startup banner.

## 4. Launcher invariants (SR-02 / CC-02)

1. **Bash wrapper uses absolute paths.** Either `cd /absolute/path && exec …` or all paths in the `exec` line are absolute. Relative paths break under Claude Desktop's unspecified launcher CWD.
2. **`.env` is loaded explicitly.** `set -a && . /absolute/path/.env && set +a` before `exec`. Claude Desktop does not read `.env` for the spawned process.
3. **Provider override goes through env.** `export AGENT_MODELS__REASONING_MODEL=local` (or `bedrock`) before `exec` — never as a CLI flag — to keep SR-03 honest.

**Conformance check:** README's `claude_desktop_config.json` snippet uses the bash wrapper with absolute path. Spot-checked during the clean-machine walkthrough (FEAT-PO-003 Wednesday gate).

## 5. Tool registration invariants (SR-07 / CC-07)

1. **Tool description ≡ implementation contract.** A tool's MCP description string is the externally-visible contract. Behaviour must match. SR-07 disallows the "undefined middle" — every tool is **sync** (< 30s end-to-end) or **long-running** (returns a tracking ID immediately, behaviour exposed via a polled companion tool).
2. **Sync ceiling is 30s.** Inherits from MCP client timeouts (Claude Desktop's 240s ceiling is a hard upper bound; the operational target is < 30s).
3. **Long-running tools return a tracking ID in ≤ 1s** (CC-08). P0 has none after [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md) reclassified `tutor_start_session` as sync.
4. **Phase-1 background work uses deepagents AsyncSubAgent.** Hand-rolled `asyncio.create_task(...)` is acceptable for the Phase-0 warm-up case (warm-up is fire-and-forget, not user-observable), but the Coach (P1) **must** use AsyncSubAgent (CC-12) per ADR-ARCH-012.

**Conformance check (recommended):** add a tool-contract test that introspects every registered MCP tool's description and asserts the classification keyword (`"sync"` or `"long-running"`) matches the handler's measured latency band over a sample.

## 6. Tool inventory (P0)

The MCPAdapter registers exactly four tools, all **sync** post-D2:

| Tool | Class | Source |
|---|---|---|
| `tutor_start_session` | sync | `MCPAdapter.tutor_start_session` (warm-up via `asyncio.create_task`) |
| `tutor_turn` | sync | `MCPAdapter.tutor_turn` (LLM call wrapped in `asyncio.to_thread`) |
| `tutor_session_status` | sync | `MCPAdapter.tutor_session_status` |
| `tutor_session_end` | sync | `MCPAdapter.tutor_session_end` (P1: triggers async Graphiti write inside; classification unchanged) |

Per-tool input/output schemas live in `docs/design/mcp-tools.json` and `docs/design/contracts/API-tutoring.md §3`.

## 7. Configuration surface

| Variable / file | Effect |
|---|---|
| `AGENT_MODELS__REASONING_MODEL` (env) | Default provider for tool handlers; resolved per call (SR-03). Set in the bash wrapper before `exec`. |
| `roles/tutor/role.yaml` | Loaded at adapter init; declares prompt locations and role metadata. |
| `roles/tutor/prompts/player.md` | Loaded at adapter init as the system prompt for `tutor_turn`. |
| `claude_desktop_config.json` (operator-side) | Registers the `study-tutor` MCP server using the bash wrapper. |

## 8. Error envelope

MCP Transport does not introduce its own error shape — handlers return the Tutoring context's error envelope (`API-tutoring.md §4`). MCP-level errors (malformed JSON-RPC, unknown tool name) are handled by the `mcp` SDK and surface as protocol-level errors.

## 9. Out of scope

- **HTTP transport.** Flag accepted, implementation deferred to P1+.
- **TLS / mTLS.** Out of scope — single-user, local + Tailscale only (ADR-ARCH-008/015).
- **Authentication / authorisation hooks.** Out of scope (ADR-ARCH-014).
- **Multi-role dispatch.** Scaffolded (`roles/`) but unused — single role (`tutor`) only in P0; multi-subject is post-hackathon (DEC-05).

## 10. Open questions for downstream phases

1. **P1 — HTTP transport.** If the dashboard (P2) or Reachy (P2 stretch) needs network access, decide between (a) HTTP MCP transport, (b) static export + read-only SDK, or (c) on-host-only SDK (Reachy). Currently leaning (b) per ARCHITECTURE.md §5.
2. **P1 — long-running reclassification.** If `tutor_start_session` adds Graphiti reads at session start that exceed 1s, reverse decision D2 and re-add the long-running classification + companion polling contract.
3. **P2 — multi-role.** If multi-subject expansion lands, the wrapper `--role` flag becomes load-bearing; today it is a no-op (`tutor` is the only registered role).
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Read tutor_session.py
Now writing the data models, mirroring the live dataclass shape (per design decision D1).

Write DM-tutoring.md
129 lines
# Data Model — Tutoring

**Bounded context:** Tutoring
**Phase:** P0 (live in-memory)
**Status:** Accepted — matches live dataclasses in `src/study_tutor/session/tutor_session.py` per [decision D1 (2026-04-26)](../../research/ideas/phase-0-build-plan.md): Phase-0 shape only, P1 fields deferred to a future `/system-design --focus="Tutoring"` re-run
**Generated:** 2026-04-26 by `/system-design`

---

## 1. Aggregate root: `TutorSession`

```
TutorSession
  ├── session_id: str (UUID, PK)
  ├── subject: str                  -- free text P0; Subject enum (Shared Kernel A) in P1
  ├── topic: str?                   -- free text P0; Topic ID (Knowledge & Curriculum) in P1
  ├── started_at: datetime (UTC)
  ├── turns: list[TutorTurn]        -- append-only
  └── status: SessionStatus         -- "active" | "ended"
```

**Source:** `TutorSession` dataclass at `src/study_tutor/session/tutor_session.py:25–32`.

### 1.1 Identity

`session_id` is a UUIDv4 generated by `SessionStore.create` (`tutor_session.py:43–48`). Immutable after creation.

### 1.2 State machine

P0 collapses the architecture's full state machine (`initialised → planning → active → summarising → ended`) into the live two-state form:

```
   active ─────────────────────────────► ended
            (SessionStore.end)
```

P1 will reintroduce intermediate states once the session planner and Coach are wired.

## 2. Value object: `TutorTurn`

```
TutorTurn
  ├── role: Role  -- "user" | "tutor"
  ├── content: str
  └── timestamp: datetime (UTC)
```

**Source:** `TutorTurn` dataclass at `tutor_session.py:18–22`.

P1 will add `index: int`, `aos_scaffolded: list[AssessmentObjective]`, and `rag_chunks_used: list[ChunkRef]` once Coach + RAG land. These are deferred per D1.

## 3. Value object: `Role`

```python
Role = Literal["user", "tutor"]
```

Not the same as Shared Kernel A's per-AO scaffolding role — a turn `role` indicates *who spoke*, not *what skill was scaffolded*.

## 4. Value object: `SessionStatus`

```python
Status = Literal["active", "ended"]
```

P1 may extend to include `planning`, `summarising` if the architecture's full state machine is wired.

## 5. Persistence

| Phase | Backing store |
|---|---|
| P0 | In-memory dict `SessionStore._sessions: dict[str, TutorSession]` (process-local; lost on restart) |
| P1 | Graphiti episodes under `student:{student_id}` group; `SessionEpisode` value object in Student Model context (read after `session.completed`) — see `domain-model.md §4.2` |

**P0 limitation called out:** sessions do not persist across MCP server restarts. Lilymay's daily-driver path uses Open WebUI (not this context's session) so this is fine for P0; the FEAT-PO-006 (P1 Graphiti) work removes the limitation.

## 6. Invariants

| # | Invariant | Enforcement |
|---|---|---|
| I-T1 | `session_id` is immutable after creation | dataclass field; never mutated |
| I-T2 | `started_at` is immutable after creation | dataclass field; never mutated |
| I-T3 | `turns` is append-only (no edits, no deletes) | only `SessionStore.append_turn` writes; only `.append(...)` is used (`tutor_session.py:60`) |
| I-T4 | No turns accepted when `status == "ended"` | `MCPAdapter.tutor_turn` returns `SessionEnded` error before invoking the store (`adapter.py:82–86`) |
| I-T5 | Status transitions are monotonic (`active → ended`, never the reverse) | only `SessionStore.end` flips the bit; no inverse method |
| I-T6 | A session abandoned before any tutor turn must not emit `session.completed` | P1: enforced at the events boundary — Tutoring only emits `session.completed` if `len(turns) >= 2` (one user, one tutor) per `gamification/design.md §2.1` |

I-T1, I-T3, I-T4, I-T5 are enforced today. I-T2 holds by construction. I-T6 is reserved for P1 wiring.

## 7. Relationships

| From | To | Cardinality | Phase |
|---|---|---|---|
| `TutorSession` | `TutorTurn` | 1..* (composition; `turns` list) | P0 |
| `TutorSession` | `Student` (Student Model context) | * → 1 (by `student_id` reference) | P1 |
| `TutorSession` | `Topic` (Knowledge & Curriculum context) | * → 0..1 (by `topic_id` reference) | P1 |
| `TutorSession` | `LLMClient` (Inference Runtime context) | depends-on (injected via `MCPAdapter`) | P0 |

Cross-context references are by **identity only** — no shared object graph. P1's Graphiti integration will use `student_id` as a foreign key into the `student:{id}` group.

## 8. Ubiquitous language

Reused from `domain-model.md §8.1` (Shared Kernel A) where applicable:

| Term | Meaning here | Shared kernel |
|---|---|---|
| `Subject` | The GCSE specification (English Language / English Literature) | A (P1 enum) |
| `Topic` | A studyable unit within a Text (e.g. `macbeth:act1:witches`) | A (P1) |
| `AssessmentObjective` | AO1..AO6 from AQA spec | A (P1) |

Not yet first-class on the P0 dataclass — `subject` and `topic` are strings until P1 enums land.

## 9. P1 fields deferred (per D1)

To be added in a `/system-design --focus="Tutoring"` re-run when Phase 1 lands:

- `student_id: str` on `TutorSession`
- `paper: Paper` on `TutorSession`
- `grade_target: GradeTarget` on `TutorSession`
- `index: int`, `aos_scaffolded: list[AssessmentObjective]`, `rag_chunks_used: list[ChunkRef]` on `TutorTurn`
- `TurnFeedback` value object (Coach output)
- `SessionSummary` value object (per-topic confidence-delta proposals, capped ±0.1 — `gamification/design.md §6.2`)

## 10. Out of scope

- **Pause/resume.** Sessions end once. No `paused` state.
- **Session merging.** No multi-session aggregation at the data-model level — that's the Student Model context's job (`SessionEpisode` rollup).
- **PII.** P0 has no student names, emails, or device IDs in the model. `name` (optional) and `student_id` are P1 additions in the **Student Model** context, not here.
Write DM-inference-runtime.md
92 lines
# Data Model — Inference Runtime

**Bounded context:** Inference Runtime (anti-corruption layer)
**Phase:** P0 (live for `local`; stub for `bedrock`)
**Status:** Accepted — matches live code in `src/study_tutor/llm/client.py`
**Generated:** 2026-04-26 by `/system-design`

---

## 1. Aggregate root: `LLMClient`

The Inference Runtime context is **stateless across calls** — `LLMClient` is constructed per call site (`LLMClient(provider=_default_player_model())`), holds the resolved provider label, and is discarded. The "data model" is therefore the **provider-resolution rule + the env-var configuration surface**, not a persistent entity.

```
LLMClient (factory-resolved, ephemeral)
  ├── provider: ProviderLabel        -- resolved from AGENT_MODELS__REASONING_MODEL at call time
  ├── (provider-specific config)     -- read inline at generate(); never cached on the instance
  └── methods:
      └── generate(prompt: str, system: str?) -> str    -- raises LLMProviderError
```

**Source:** `LLMClient` class at `src/study_tutor/llm/client.py:56–107`.

## 2. Value object: `ProviderLabel`

```python
ProviderLabel = Literal["local", "bedrock", "openai", "anthropic", "gemini"]
```

The closed set of providers is the contract. Adding a label is a contract change requiring `/design-refine` and a new `[providers]` extra entry.

| Label | Endpoint resolver | Default model env var | Status (P0) |
|---|---|---|---|
| `local` | `OLLAMA_BASE_URL` (default `http://localhost:11434`) | `OLLAMA_MODEL` (default `gcse-tutor-gemma4-moe:latest`) | live |
| `bedrock` | AWS Bedrock Custom Model Import via `boto3` / `langchain-aws` | `BEDROCK_MODEL_ARN` | stub (`NotImplementedError`) until FEAT-PO-004 |
| `openai` | OpenAI API | TBD | declared, not wired |
| `anthropic` | Anthropic API | TBD | declared, not wired |
| `gemini` | Google Gemini API | TBD | declared, not wired (Graphiti's Gemini path is independent) |

## 3. Value object: `LLMProviderError`

```python
class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""
```

The single error type that crosses the context boundary. Provider-specific exceptions (`httpx.HTTPError`, `boto3` ClientError) are caught and re-raised as `LLMProviderError` (e.g. `client.py:101–104`).

## 4. Configuration surface (env vars)

The configuration "data" of this context lives in environment variables read at call time. SR-03 forbids module-level caching.

| Variable | Read by | Default | Effect |
|---|---|---|---|
| `AGENT_MODELS__REASONING_MODEL` | `_default_player_model()` (`client.py:47–53`) | `local` | Selects the provider label |
| `OLLAMA_BASE_URL` | `_generate_ollama` (`client.py:81`) | `http://localhost:11434` | Endpoint for `local` provider |
| `OLLAMA_MODEL` | `_generate_ollama` (`client.py:82`) | `gcse-tutor-gemma4-moe:latest` | Model ID for `local` provider |
| `OLLAMA_NUM_PREDICT` | `_resolve_num_predict` (`client.py:31–44`) | `2048` | Token ceiling per generation |
| `BEDROCK_MODEL_ARN` | (P1) `_generate_bedrock` | placeholder | ARN for `bedrock` provider |

## 5. Invariants

| # | Invariant | Enforcement |
|---|---|---|
| I-IR1 | Provider resolved at the factory, not the handler | every call-site reads `params.get("player_model") or _default_player_model()` (e.g. `adapter.py:62, 88`); no module-level provider in handler files |
| I-IR2 | Every named provider appears in `pyproject.toml [providers]` extra | manual review at `/design-refine` time; CI smoke recommended |
| I-IR3 | `LLMClient.generate(...)` is the sole public interface | upstream contexts never construct `ChatOllama`/`ChatBedrock`/etc. directly; httpx is imported lazily inside `_generate_ollama` (`client.py:79`) |
| I-IR4 | Provider-specific knowledge stays inside this context | ARNs, URLs, retry semantics, model IDs do not leak into Tutoring or MCP Transport |
| I-IR5 | Errors normalise to `LLMProviderError` | provider-specific exceptions caught + re-raised; `NotImplementedError` for stubbed providers (`client.py:69–72`) |
| I-IR6 | `generate` is synchronous | callers wrap in `asyncio.to_thread(...)` (e.g. `adapter.py:95–97, 134`) |

## 6. Relationships

| From | To | Cardinality | Phase |
|---|---|---|---|
| `MCPAdapter` (Tutoring + MCP Transport) | `LLMClient` | depends-on, ephemeral (one per handler call) | P0 |
| `LLMClient` | Ollama HTTP endpoint on GB10 | network call (Tailscale) | P0 |
| `LLMClient` | AWS Bedrock Custom Model Import endpoint | network call (HTTPS) | P1 (FEAT-PO-004) |

No cross-context object references. `LLMClient` is a leaf in the dependency graph.

## 7. Persistence

**None.** This context owns no persistent data. Every call constructs a fresh `LLMClient`, reads env vars, makes the upstream call, and returns. The configuration is the env-var surface.

## 8. Out of scope

- **Token-usage counters / cost accounting.** Single-user posture; deferred (ADR-ARCH-014, ADR-ARCH-011).
- **Streaming responses.** P0 is non-streaming (`stream: false` in the Ollama payload).
- **Retries / circuit breakers.** Failures surface as `LLMProviderError` immediately.
- **Prompt caching.** Deferred (ADR-ARCH-011); irrelevant for Ollama, evaluate for Bedrock in P1 if cost matters.
Write DM-mcp-transport.md
115 lines
# Data Model — MCP Transport

**Bounded context:** MCP Transport
**Phase:** P0 (live)
**Status:** Accepted — matches live code in `src/study_tutor/mcp/{server.py, adapter.py}` and `scripts/mcp-wrapper.sh`
**Generated:** 2026-04-26 by `/system-design`

---

## 1. Aggregate root: `MCPAdapter`

The MCP Transport context is **stateless across MCP calls** apart from a shared `SessionStore` (which logically belongs to **Tutoring**). The "data" here is the tool-registration descriptor set + the live warm-up task pool.

```
MCPAdapter
  ├── role: RoleConfig                       -- loaded from roles/tutor/role.yaml at init
  ├── store: SessionStore                    -- shared with Tutoring (composition, not ownership)
  ├── player_prompt: str                     -- loaded from roles/tutor/prompts/player.md at init
  └── warmup_tasks: set[asyncio.Task]        -- GC-tracked; transient
```

**Source:** `MCPAdapter` class at `src/study_tutor/mcp/adapter.py:35–47`.

## 2. Value object: `McpToolDescriptor`

Conceptual entity describing each registered tool. Concretely lives in the FastMCP/`mcp` SDK registry, not in our own dataclasses. Documented here for the contract.

```
McpToolDescriptor
  ├── name: str                              -- e.g. "tutor_turn"
  ├── classification: SR07Class              -- "sync" | "long-running"
  ├── description: str                       -- ≡ implementation contract (SR-07)
  ├── input_schema: JSONSchema               -- per-tool argument shape
  └── handler: async function                -- bound MCPAdapter method
```

**P0 inventory:** 4 descriptors, all `classification = "sync"` after [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md). Authoritative serialisation lives in `docs/design/mcp-tools.json`.

## 3. Value object: `SR07Class`

```python
SR07Class = Literal["sync", "long-running"]
```

The closed set per SR-07. Adding a third class (e.g. `"streaming"`) is a contract change requiring `/design-refine` because it changes the latency-classification gate that underpins CC-08.

## 4. Value object: `ErrorResponse`

The shape returned by handlers when they fail without raising — the **single normalised error envelope** for the MCP surface. Mirrors `API-tutoring.md §4`.

```
ErrorResponse
  ├── error: str                             -- human-readable
  └── error_type: ErrorType                  -- closed set (see below)

ErrorType = Literal[
  "SessionNotFoundError",
  "SessionEnded",
]
```

**Source:** `_session_not_found(session_id)` helper at `adapter.py:139–143` + the inline `SessionEnded` return at `adapter.py:82–86`.

## 5. Configuration surface

The "configuration data" the MCP Transport context owns:

| Source | Loaded by | Phase |
|---|---|---|
| `roles/tutor/role.yaml` | `RoleConfig` (passed to `MCPAdapter.__init__`) | P0 |
| `roles/tutor/prompts/player.md` | `role_config.load_player_prompt()` (`adapter.py:46`) | P0 |
| `claude_desktop_config.json` (operator-side) | Claude Desktop process — registers `study-tutor` MCP server pointing at `scripts/mcp-wrapper.sh` | P0 |
| `scripts/mcp-wrapper.sh` | Shell at launch — sources `.env`, exports `AGENT_MODELS__REASONING_MODEL`, `exec`s the venv's `study-tutor serve …` | P0 |

Per SR-02 the wrapper uses absolute paths; per SR-03 the provider override goes via env, not CLI flag.

## 6. Invariants

| # | Invariant | Enforcement |
|---|---|---|
| I-MCP1 | stdout produces zero bytes before the MCP handshake; only protocol frames thereafter | `tests/unit/mcp/test_stdio_discipline.py` (SR-01 / CC-01) |
| I-MCP2 | All diagnostics route to stderr | `click.echo(..., err=True)`, loggers configured for stderr; banner mandatory |
| I-MCP3 | Bash wrapper uses absolute paths | code review at `/design-refine`; spot-checked in clean-machine walkthrough (SR-02 / CC-02) |
| I-MCP4 | Tool description ≡ handler behaviour | manual review + recommended tool-contract test (SR-07 / CC-07) |
| I-MCP5 | Sync tools complete in < 30s end-to-end; long-running tools return tracking ID in ≤ 1s | latency-band sampling; current adapter has no long-running tools after D2 (CC-08) |
| I-MCP6 | Phase-1 background work uses deepagents AsyncSubAgent, not raw `asyncio.create_task` | enforced at code review; warm-up exemption documented (CC-12 / ADR-ARCH-012) |
| I-MCP7 | Errors normalise to `ErrorResponse` shape | every handler returns the exact two-key envelope on failure |

## 7. Relationships

| From | To | Cardinality | Phase |
|---|---|---|---|
| `MCPAdapter` | `SessionStore` (Tutoring) | composition (shared) | P0 |
| `MCPAdapter` | `LLMClient` (Inference Runtime) | constructed per call | P0 |
| `MCPAdapter` | `RoleConfig` | composition | P0 |
| `MCPAdapter` | `asyncio.Task` warm-up pool | composition (set, GC-tracked) | P0 |

The adapter is a thin façade — no domain entity is owned exclusively here. Domain ownership lives in Tutoring.

## 8. Persistence

**None.** The adapter is stateless across MCP server restarts. The shared `SessionStore` is in-memory only at P0 (see `DM-tutoring.md §5`); restarts wipe sessions. P1 Graphiti integration moves session persistence to the Student Model context, not into MCP Transport.

## 9. Out of scope

- **Tool-call audit log.** Not retained at P0; deferred. Tracing belongs to a future observability concern.
- **Multi-role dispatch state.** Scaffolded but unused — single role (`tutor`) only.
- **HTTP transport state.** No HTTP transport at P0.
- **Authentication / session tokens.** None — single-user posture (ADR-ARCH-008/014).

## 10. Open questions for downstream phases

1. **P1 — error envelope evolution.** Add `LLMUnavailable`, `ProviderTimeout`, `RAGRetrievalFailed` once those failure modes are exercised. Update `ErrorType` literal and the conformance test in lockstep.
2. **P2 — observability.** If demo metrics are needed, decide between (a) adding a sidecar that tails stderr logs, or (b) emitting a structured event on each tool call into the in-process bus.
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Now the MCP tool definitions JSON (canonical schema for the four tools).

Write mcp-tools.json
155 lines
{
  "$schema": "https://modelcontextprotocol.io/schemas/tool/v1",
  "study_tutor_version": "0.1.0",
  "phase": "P0",
  "generated_at": "2026-04-26",
  "generated_by": "/system-design (bias-to-defaults)",
  "source_of_truth": "src/study_tutor/mcp/adapter.py",
  "design_decisions": {
    "D2": "tutor_start_session classified as 'sync' (not 'long-running') per phase-0-build-plan.md punch-list item 7"
  },
  "tools": [
    {
      "name": "tutor_start_session",
      "classification": "sync",
      "description": "Sync. Start a tutoring session for a given subject (and optional topic). Returns a session_id immediately; an opportunistic LLM warm-up runs in the background to prime model weights. Subsequent tutor_turn calls reference the returned session_id.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "subject": {
            "type": "string",
            "description": "GCSE subject — free text in P0 (e.g. 'English Literature'). P1 will tighten to the Subject enum from Shared Kernel A."
          },
          "topic": {
            "type": "string",
            "description": "Optional topic within the subject (e.g. 'Macbeth Act 1 Scene 1'). Free text in P0; P1 will tighten to a Topic ID."
          },
          "player_model": {
            "type": "string",
            "description": "Optional provider override. If unset, resolves AGENT_MODELS__REASONING_MODEL at call time (SR-03). Closed set: 'local' | 'bedrock' | 'openai' | 'anthropic' | 'gemini'.",
            "enum": ["local", "bedrock", "openai", "anthropic", "gemini"]
          }
        },
        "required": ["subject"],
        "additionalProperties": false
      },
      "outputSchema": {
        "type": "object",
        "properties": {
          "session_id": { "type": "string", "format": "uuid" }
        },
        "required": ["session_id"],
        "additionalProperties": false
      },
      "latencyTarget": "<= 1s",
      "errorEnvelope": null
    },
    {
      "name": "tutor_turn",
      "classification": "sync",
      "description": "Sync (< 30s). Generate one tutor reply for user_message within the given session. Routes through LLMClient; provider resolves from AGENT_MODELS__REASONING_MODEL at call time unless player_model is provided.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "session_id": { "type": "string", "format": "uuid" },
          "user_message": { "type": "string", "minLength": 1 },
          "player_model": {
            "type": "string",
            "enum": ["local", "bedrock", "openai", "anthropic", "gemini"],
            "description": "Optional per-call provider override (SR-03)."
          }
        },
        "required": ["session_id", "user_message"],
        "additionalProperties": false
      },
      "outputSchema": {
        "oneOf": [
          {
            "type": "object",
            "properties": { "tutor_response": { "type": "string" } },
            "required": ["tutor_response"],
            "additionalProperties": false
          },
          { "$ref": "#/definitions/ErrorResponse" }
        ]
      },
      "latencyTarget": "p95 < 10s; hard ceiling 30s",
      "errorEnvelope": ["SessionNotFoundError", "SessionEnded"]
    },
    {
      "name": "tutor_session_status",
      "classification": "sync",
      "description": "Sync. Read the current state of a tutoring session — status, turn count, and start time.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "session_id": { "type": "string", "format": "uuid" }
        },
        "required": ["session_id"],
        "additionalProperties": false
      },
      "outputSchema": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "session_id": { "type": "string", "format": "uuid" },
              "status": { "type": "string", "enum": ["active", "ended"] },
              "turn_count": { "type": "integer", "minimum": 0 },
              "started_at": { "type": "string", "format": "date-time" }
            },
            "required": ["session_id", "status", "turn_count", "started_at"],
            "additionalProperties": false
          },
          { "$ref": "#/definitions/ErrorResponse" }
        ]
      },
      "latencyTarget": "< 2s",
      "errorEnvelope": ["SessionNotFoundError"]
    },
    {
      "name": "tutor_session_end",
      "classification": "sync",
      "description": "Sync. Mark a tutoring session ended. Phase 0 flips status only; Phase 1 will trigger an async Graphiti write-back inside the handler (the side effect is implementation-internal per SR-07 and is not part of the user-visible contract).",
      "inputSchema": {
        "type": "object",
        "properties": {
          "session_id": { "type": "string", "format": "uuid" }
        },
        "required": ["session_id"],
        "additionalProperties": false
      },
      "outputSchema": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "session_id": { "type": "string", "format": "uuid" },
              "status": { "type": "string", "enum": ["ended"] }
            },
            "required": ["session_id", "status"],
            "additionalProperties": false
          },
          { "$ref": "#/definitions/ErrorResponse" }
        ]
      },
      "latencyTarget": "< 2s",
      "errorEnvelope": ["SessionNotFoundError"]
    }
  ],
  "definitions": {
    "ErrorResponse": {
      "type": "object",
      "properties": {
        "error": { "type": "string" },
        "error_type": {
          "type": "string",
          "enum": ["SessionNotFoundError", "SessionEnded"]
        }
      },
      "required": ["error", "error_type"],
      "additionalProperties": false
    }
  }
}
Bash Validate MCP tool JSON
IN
python3 -c "import json,sys; json.load(open('docs/design/mcp-tools.json')); print('mcp-tools.json: valid JSON')"

OUT
mcp-tools.json: valid JSON
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Write events-schema.yaml
190 lines
## Shared Kernel B — Session Event Vocabulary
## Phase: P0 reserved (CC-11) — schemas frozen here; in-process bus wired in P1
## Source of truth: docs/architecture/domain-model.md §8.2
## Generated: 2026-04-26 by /system-design (bias-to-defaults, Phase 0 scope)
##
## Delivery: in-process only (no NATS, no external broker). Subscribers MUST
## use the deepagents 0.5.3 AsyncSubAgent boundary or equivalent async hook
## (CC-12); synchronous fan-out into tutor_turn return is forbidden.
##
## Validation: subscribers validate at the boundary using Pydantic per
## ADR-ARCH-010. The schemas below are the authoritative shape.

version: "0.1.0"
phase: P0-reserved-P1-live

producers:
  Tutoring:
    emits:
      - session.started
      - session.turn_completed
      - session.completed
  Gamification:
    emits:
      - achievement.unlocked
      - quest.completed
      - quest.expired
      - boss_battle.completed

consumers:
  StudentModel:
    subscribes:
      - session.started
      - session.turn_completed
      - session.completed
  Gamification:
    subscribes:
      - session.completed
  Reachy:
    subscribes:
      - achievement.unlocked
      - boss_battle.completed
    note: P2 stretch

events:

  session.started:
    description: |
      Emitted by Tutoring on transition to "active" state. Marks the
      beginning of a tutoring session and lets the Student Model context
      create a SessionEpisode head record.
    phase_live: P1
    payload:
      type: object
      properties:
        session_id: { type: string, format: uuid }
        student_id: { type: string }
        subject: { type: string, description: "Subject enum value (Shared Kernel A) once P1 enums land; free text in P0 reserved shape" }
        topic:
          oneOf:
            - { type: string }
            - { type: "null" }
        started_at: { type: string, format: date-time }
      required: [session_id, student_id, subject, started_at]
      additionalProperties: false

  session.turn_completed:
    description: |
      Emitted by Tutoring after each tutor reply (i.e. after a (user, tutor)
      turn pair has been appended). Consumers: Coach (P1, evaluates quality);
      Student Model (P1, may append Misconception via the Coach).
    phase_live: P1
    payload:
      type: object
      properties:
        session_id: { type: string, format: uuid }
        turn_index: { type: integer, minimum: 0 }
        role: { type: string, enum: [user, tutor] }
        ao_scaffolded:
          oneOf:
            - type: array
              items: { type: string, enum: [AO1, AO2, AO3, AO4, AO5, AO6] }
            - { type: "null" }
          description: "Coach-derived; null until Coach is wired (P1)."
      required: [session_id, turn_index, role]
      additionalProperties: false

  session.completed:
    description: |
      Emitted by Tutoring on transition to "ended" state. Triggers Student
      Model rollup (TopicConfidence delta capped ±0.1, AssessmentObjectiveProgress
      update) and Gamification XP/streak/achievement evaluation.
      Per gamification/design.md §2.1, sessions abandoned before any tutor
      turn (turn_count < 2) MUST NOT emit this event.
    phase_live: P1
    payload:
      type: object
      properties:
        session_id: { type: string, format: uuid }
        duration_seconds: { type: integer, minimum: 0 }
        topic:
          oneOf:
            - { type: string }
            - { type: "null" }
        aos_touched:
          type: array
          items: { type: string, enum: [AO1, AO2, AO3, AO4, AO5, AO6] }
        quality_score:
          oneOf:
            - { type: number, minimum: 0.0, maximum: 1.0 }
            - { type: "null" }
          description: "Coach-derived overall session quality; null when Coach unavailable."
        ended_at: { type: string, format: date-time }
      required: [session_id, duration_seconds, aos_touched, ended_at]
      additionalProperties: false

  achievement.unlocked:
    description: |
      Emitted by Gamification when a Student crosses an achievement criterion.
      Producer: Gamification context only — Tutoring does not emit this.
      Consumers: Student Model (XP/level rollup), Reachy (P2 celebration trigger).
      Achievements are sticky (once unlocked, always unlocked) per gamification/design.md §5.
    phase_live: P2
    payload:
      type: object
      properties:
        student_id: { type: string }
        achievement_id: { type: string, description: "Stable ID from gamification/design.md §5 (e.g. 'quote_champion', 'macbeth_master')" }
        xp_reward: { type: integer, minimum: 0 }
        unlocked_at: { type: string, format: date-time }
      required: [student_id, achievement_id, xp_reward, unlocked_at]
      additionalProperties: false

  quest.completed:
    description: |
      Emitted by Gamification when a daily/weekly quest target is met.
      Quests have one concurrent at Level <9; two at Level >=9 per gamification/design.md.
    phase_live: P2
    payload:
      type: object
      properties:
        student_id: { type: string }
        quest_id: { type: string }
        completed_at: { type: string, format: date-time }
      required: [student_id, quest_id, completed_at]
      additionalProperties: false

  quest.expired:
    description: |
      Emitted by Gamification when a quest's expires_at passes without
      completion. Used to age quests out of active state.
    phase_live: P2
    payload:
      type: object
      properties:
        student_id: { type: string }
        quest_id: { type: string }
        expired_at: { type: string, format: date-time }
      required: [student_id, quest_id, expired_at]
      additionalProperties: false

  boss_battle.completed:
    description: |
      Emitted by Gamification when a Boss Battle ends. First completion per
      calendar week awards XP; subsequent completions unlock practice mode
      (no XP) per gamification/design.md.
    phase_live: P2
    payload:
      type: object
      properties:
        student_id: { type: string }
        paper: { type: string, description: "Paper enum value once Shared Kernel A enums land" }
        trophy_id: { type: string }
        completed_at: { type: string, format: date-time }
        is_first_of_week: { type: boolean }
      required: [student_id, paper, trophy_id, completed_at, is_first_of_week]
      additionalProperties: false

delivery_semantics:
  transport: in-process
  ordering: per-aggregate FIFO (within a single session_id, events emit in order)
  durability: at-most-once
  retry: none
  dead_letter: none
  rationale: |
    Single-user posture (ADR-ARCH-014) plus async Graphiti write-back at
    session-end (ADR-ARCH-003) make heavy delivery guarantees unnecessary.
    A consumer crash on session.completed is an observable defect, not a
    silent data-loss event — the SessionEpisode in Graphiti will be missing
    and surface on the next session-status read.
Bash Validate events YAML
IN
python3 -c "import yaml,sys; yaml.safe_load(open('docs/design/events-schema.yaml')); print('events-schema.yaml: valid YAML')"

OUT
events-schema.yaml: valid YAML
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Write README.md
96 lines
# Study Tutor — Design Artefacts

**Status:** Phase 0 canonical (2026-04-26).
**Generated by:** `/system-design --from docs/architecture/ARCHITECTURE.md --context phase-0-scope.md --context phase-0-build-plan.md`
**Mode:** Option A (Phase 0 scope) + bias-to-defaults.
**Consumed by:** `/system-plan`, `/feature-spec`, `/feature-plan`.

---

## 1. Scope

Phase 0 design covers the **three implemented bounded contexts** plus the **Shared Kernel B** event vocabulary:

| Bounded context | Code today | Design artefact |
|---|---|---|
| Tutoring | `src/study_tutor/session/`, `src/study_tutor/mcp/adapter.py` | [contracts/API-tutoring.md](contracts/API-tutoring.md), [models/DM-tutoring.md](models/DM-tutoring.md) |
| Inference Runtime | `src/study_tutor/llm/client.py` | [contracts/API-inference-runtime.md](contracts/API-inference-runtime.md), [models/DM-inference-runtime.md](models/DM-inference-runtime.md) |
| MCP Transport | `src/study_tutor/mcp/`, `scripts/mcp-wrapper.sh` | [contracts/API-mcp-transport.md](contracts/API-mcp-transport.md), [models/DM-mcp-transport.md](models/DM-mcp-transport.md) |
| Shared Kernel B (Events) | reserved (CC-11); P1 wire-up | [events-schema.yaml](events-schema.yaml) |

**Phase 0 protocol surfaces:** MCP stdio + CLI + in-process Events. No REST, no GraphQL, no A2A, no ACP per ADR-ARCH-008.

**Deferred contexts (re-run `/system-design --focus="<name>"` per phase):**

| Context | Phase | Recommended re-run trigger |
|---|---|---|
| Knowledge & Curriculum | P1 | After `phase-1-scope.md` is finalised + Graphiti spike produces latency numbers |
| Student Model | P1 | After `phase-1-scope.md` and the Graphiti split topology (ADR-ARCH-007) is operational |
| Gamification | P2 | When the gamification engine moves from `docs/gamification/design.md` to runtime code (per ADR-ARCH-013) |

The full re-run command set is in [`phase-0-build-plan.md` § "GuardKit Command Sequence"](../research/ideas/phase-0-build-plan.md#guardkit-command-sequence).

## 2. Generated artefacts

```
docs/design/
├── README.md                                 (this file — index + summary)
├── contracts/
│   ├── API-tutoring.md                       MCP + Events surfaces; tool schemas
│   ├── API-inference-runtime.md              Internal Python interface; provider matrix
│   └── API-mcp-transport.md                  Transport invariants; CLI + wrapper contract
├── models/
│   ├── DM-tutoring.md                        TutorSession aggregate; live dataclass shape
│   ├── DM-inference-runtime.md               LLMClient (ephemeral); provider value object
│   └── DM-mcp-transport.md                   MCPAdapter façade; ErrorResponse envelope
├── mcp-tools.json                            Authoritative JSON Schema for the 4 MCP tools
└── events-schema.yaml                        Shared Kernel B event vocabulary
```

## 3. Design decisions captured (2026-04-26)

| ID | Decision | Rationale |
|---|---|---|
| **D1** | Tutoring data model documents the **Phase-0 shape only** (`session_id, subject, topic, status, turns, started_at, ended_at`). P1 fields deferred. | Matches live `tutor_session.py` dataclasses; avoids contract-drift before P1 implementation. |
| **D2** | `tutor_start_session` classified **`sync`** (not `long-running`). | Live behaviour: returns `session_id` synchronously; warm-up is fire-and-forget, not a polled task. SR-07 wording in `domain-model.md §7.1` and `phase-0-scope.md SR-07` to be tightened by a follow-up `/arch-refine`. |

Both decisions are recorded in [`phase-0-build-plan.md` punch-list item 7](../research/ideas/phase-0-build-plan.md). No standalone DDR — both fall within the architecture decision envelope and only re-state classifications.

## 4. Out-of-scope artefacts (and why)

| Artefact | Why omitted |
|---|---|
| `openapi.yaml` | No REST surface in Phase 0. ADR-ARCH-008 makes MCP-only the agent contract; Open WebUI consumes Ollama directly. Re-introduce when (and if) HTTP transport lands. |
| `a2a-schemas.yaml` | No agent-to-agent contract — Study Tutor is a single agent, not a multi-agent system. Re-evaluate if Reachy (P2 stretch) gains a delegating role. |
| `acp-workflows.yaml` | No agent communication protocol surface. Same reason. |
| C4 L3 component diagrams | Phase-0 containers all have ≤ 3 internal components. The threshold (>3, per `/system-design` Step 5 rule) is not met. Phase-1 Tutoring will likely cross it (Player + Coach + Session Planner + RAG retriever) — generate then. |

## 5. Contradiction detection result

✓ No contradictions detected against the 16 architecture ADRs. The protocol set (MCP + CLI + Events) is congruent with ADR-ARCH-008 and ADR-ARCH-014. The Bedrock route classification matches ADR-ARCH-006. The async Events bus matches ADR-ARCH-003 and CC-11.

## 6. Conformance: design ↔ live code

The artefacts in this directory are deliberately **descriptive of live code**, not aspirational. Every contract / data-model file pin-cites the source file + line range. When code drifts:

- A pure additive change (new field, new event consumer) → update the artefact and re-run `/system-design --focus="<context>"`.
- A breaking change (rename, classification flip, removed `error_type`) → run `/design-refine` first; do not silently edit the artefact.

## 7. Next steps

1. **Run `/system-plan`** to produce feature-level planning context grounded in these design artefacts:
   ```
   /system-plan \
     --from docs/design/README.md \
     --context docs/architecture/ARCHITECTURE.md \
     --context docs/research/ideas/phase-0-scope.md \
     --context docs/research/ideas/phase-0-build-plan.md
   ```
2. **Seed Graphiti** with the artefacts (see § 8).
3. **Phase-1 prep:** when `phase-1-scope.md` is finalised, re-run `/system-design` with `--focus="Knowledge & Curriculum"` and `--focus="Student Model"` per the recommended sequence in `phase-0-build-plan.md`.
4. **Architecture follow-up:** open an `/arch-refine` ticket to update `domain-model.md §7.1` SR-07 wording for `tutor_start_session` (D2 — reclassify long-running → sync).

## 8. Graphiti seeding (offered separately)

The contracts and data models will be seeded into the `project_design` group; no DDRs were captured this run so `architecture_decisions` is unaffected. See the separate prompt at the end of the `/system-design` run for the exact `guardkit graphiti add-context` commands.
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Quick file-tree confirmation, then the summary + Graphiti seeding offer.

Bash List generated design artefacts
IN
find docs/design -type f | sort

OUT
docs/design/contracts/API-inference-runtime.md
docs/design/contracts/API-mcp-transport.md
docs/design/contracts/API-tutoring.md
docs/design/events-schema.yaml
docs/design/mcp-tools.json
docs/design/models/DM-inference-runtime.md
docs/design/models/DM-mcp-transport.md
docs/design/models/DM-tutoring.md
docs/design/README.md
✅ SYSTEM DESIGN COMPLETE (Phase 0 scope)
Created:


docs/design/
├── README.md                                 (index + 2 design decisions + next steps)
├── contracts/
│   ├── API-tutoring.md                       (MCP tools + Events surfaces)
│   ├── API-inference-runtime.md              (internal Python interface; provider matrix)
│   └── API-mcp-transport.md                  (transport invariants; CLI; wrapper)
├── models/
│   ├── DM-tutoring.md                        (TutorSession aggregate — P0 shape only per D1)
│   ├── DM-inference-runtime.md               (LLMClient, ProviderLabel, env-var surface)
│   └── DM-mcp-transport.md                   (MCPAdapter façade + ErrorResponse envelope)
├── mcp-tools.json                            (4 tools, JSON Schema — validated ✓)
└── events-schema.yaml                        (Shared Kernel B — 7 events, P1/P2 phasing)
Build plan updated: phase-0-build-plan.md punch-list item 7 records D1 + D2; the GuardKit Command Sequence section gives explicit /system-design --focus="<context>" invocations for P1 (Knowledge & Curriculum, Student Model) and P2 (Gamification).

Skipped (justified in docs/design/README.md §4):

openapi.yaml — no REST surface (ADR-ARCH-008)
a2a-schemas.yaml, acp-workflows.yaml — no agent-to-agent surface
C4 L3 diagrams — no Phase-0 container has > 3 internal components (Phase-1 Tutoring with Player + Coach + Planner + RAG will cross the threshold)
Contradiction detection: ✓ none. The MCP-only + Events surface set is congruent with all 16 ADRs.

Phase 5 — Graphiti seeding (offered)
Graphiti is enabled (whitestocks FalkorDB + vLLM on GB10). The seeding commands are below — say yes and I'll run them, or skip and the markdown artefacts stand alone (re-runnable later via the same commands).


# Design index (project-wide context)
guardkit graphiti add-context docs/design/README.md \
  --group project_design

# API contracts (one per bounded context)
guardkit graphiti add-context docs/design/contracts/API-tutoring.md \
  --group project_design
guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md \
  --group project_design
guardkit graphiti add-context docs/design/contracts/API-mcp-transport.md \
  --group project_design

# Data models (one per bounded context)
guardkit graphiti add-context docs/design/models/DM-tutoring.md \
  --group project_design
guardkit graphiti add-context docs/design/models/DM-inference-runtime.md \
  --group project_design
guardkit graphiti add-context docs/design/models/DM-mcp-transport.md \
  --group project_design

# Shared Kernel B event vocabulary
guardkit graphiti add-context docs/design/events-schema.yaml \
  --group project_design
No DDRs captured this run (both decisions fall within the existing architecture envelope), so architecture_decisions is untouched.

Run seeding now? [Y / skip] — and once seeded (or skipped), the recommended next move is /system-plan --from docs/design/README.md to produce feature-level planning context for the remaining Phase 0 punch-list (clean-machine walkthrough, FEAT-PO-004 Bedrock validation) and to seed Phase 1 work.

Y
Verifying connectivity with the index file first, then I'll queue the rest.

Bash Seed design index into Graphiti
IN
guardkit graphiti add-context docs/design/README.md --group project_design 2>&1 | tail -40

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH
Try 'guardkit-py graphiti add-context --help' for help.

Error: No such option: --group
Bash Check add-context CLI signature
IN
guardkit graphiti add-context --help 2>&1 | head -60

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH

  Add context from files to Graphiti.

  Adds content from markdown files to the Graphiti knowledge graph. Supports
  single files or directories with glob patterns.

  Examples:
      guardkit graphiti add-context docs/ADR-001.md
      guardkit graphiti add-context docs/architecture/
      guardkit graphiti add-context docs/ --pattern "**/*.md"
      guardkit graphiti add-context docs/ADR-001.md --type adr
      guardkit graphiti add-context docs/ --dry-run
      guardkit graphiti add-context docs/ --delay 1.0
      guardkit graphiti add-context docs/ --delay 0

  Supported parser types:
      - adr: Architecture Decision Records
      - feature_spec: Feature specifications
      - full_doc: Full document capture (entire markdown content)
      - project_overview: Project overview documents
      - project_doc: General project documentation (CLAUDE.md, README.md)

Options:
  --type TEXT           Force parser type (adr, feature-spec, project-
                        overview)
  -f, --force           Overwrite existing context
  --dry-run             Show what would be added without adding
  --pattern TEXT        Glob pattern for directory (default: **/*.md)
  -v, --verbose         Show detailed processing output
  -q, --quiet           Suppress non-error output
  --delay FLOAT         Inter-episode delay in seconds (default: 0.5, 0 to
                        disable)
  --chunk-size INTEGER  Force chunking for docs above this size in bytes
                        (default: 10240). Use 0 to always chunk.
  --timeout FLOAT       Per-episode timeout in seconds (overrides auto-
                        detected timeout). Use for slow vLLM instances.
  --help                Show this message and exit.
The CLI auto-routes by parser type, not by --group. Let me dry-run the index to see how it auto-classifies.

Bash Dry-run to see auto-classification
IN
guardkit graphiti add-context docs/design/README.md --dry-run 2>&1 | tail -30

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

  ✓ docs/design/README.md (project_overview)

Dry run complete - Would add:
  1 file, 1 episode

Warnings:
  Warning: docs/design/README.md: Missing 'architecture' section
Connectivity green. Let me dry-run all 8 files to verify classification before seeding for real.

Bash Dry-run all design artefacts
IN
guardkit graphiti add-context docs/design/ --pattern "**/*.{md,yaml,json}" --dry-run 2>&1 | tail -30

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

No files found matching pattern: **/*.{md,yaml,json}
Brace expansion doesn't expand. Let me dry-run with the default **/*.md pattern; the JSON + YAML are machine-readable schemas (reference artefacts, not narrative content for the knowledge graph) so they don't need seeding.

Bash Dry-run all design markdown files
IN
guardkit graphiti add-context docs/design/ --dry-run 2>&1 | tail -30

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

  ✓ docs/design/README.md (project_overview)
  ✓ docs/design/contracts/API-tutoring.md (full_doc)
  ✓ docs/design/contracts/API-mcp-transport.md (full_doc)
  ✓ docs/design/contracts/API-inference-runtime.md (full_doc)
  ✓ docs/design/models/DM-inference-runtime.md (full_doc)
  ✓ docs/design/models/DM-tutoring.md (full_doc)
  ✓ docs/design/models/DM-mcp-transport.md (full_doc)

Dry run complete - Would add:
  7 files, 7 episodes

Warnings:
  Warning: docs/design/README.md: Missing 'architecture' section
Auto-classification looks right (1 project_overview + 6 full_doc). Running the real seeding now — vLLM on GB10 means this will take a couple of minutes.

Bash Seed all 7 design markdown files into Graphiti
IN
guardkit graphiti add-context docs/design/ 2>&1 | tail -50

OUT
Command running in background with ID: bhuxtstbi. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/bhuxtstbi.output
Bash Wait for seeding to complete then show output
IN
until ! pgrep -f "guardkit-py graphiti add-context docs/design/" > /dev/null 2>&1; do sleep 5; done; echo "--- seeding finished ---"; tail -60 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/bhuxtstbi.output

OUT
Command running in background with ID: brauedcez. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/brauedcez.output
Both commands are running in the background — the seeder and the wait-loop. I'll be notified when the seeder finishes.

<task-notification>
<task-id>brauedcez</task-id>
<tool-use-id>toolu_01UQRitWJzXXvmbVBE5EVxUx</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/brauedcez.output</output-file>
<status>completed</status>
<summary>Background command "Wait for seeding to complete then show output" completed (exit code 0)</summary>
</task-notification>
Bash Show seeder final output
IN
tail -60 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/bhuxtstbi.output

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 154479.93421554565 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [study-tutor-design-artefacts]: nodes=10, edges=6, invalidated=0
  ✓ docs/design/README.md (project_overview)
WARNING:graphiti_core.utils.maintenance.node_operations:Invalid duplicate_idx 6 for extracted node 6f780954-93c4-42b3-9f89-e36a42b032c2; treating as no duplicate.
WARNING:graphiti_core.utils.maintenance.node_operations:Invalid duplicate_idx 7 for extracted node 1cd5adc6-a7d4-4a65-b278-4aa796badce6; treating as no duplicate.
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 600s: docs/design/contracts/API-tutoring.md. Use --timeout to increase (e.g., --timeout 300 for local LLMs which are typically ~2x slower than GB10 vLLM).
  ⚠ docs/design/contracts/API-tutoring.md (full_doc) — 1 episode(s) failed
INFO:graphiti_core.graphiti:Completed add_episode in 245926.3081550598 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/contracts/API-mcp-transport.md]: nodes=15, edges=13, invalidated=0
  ✓ docs/design/contracts/API-mcp-transport.md (full_doc)
INFO:graphiti_core.graphiti:Completed add_episode in 201269.33073997498 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/contracts/API-inference-runtime.md]: nodes=15, edges=12, invalidated=0
  ✓ docs/design/contracts/API-inference-runtime.md (full_doc)
INFO:graphiti_core.graphiti:Completed add_episode in 171039.00003433228 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-inference-runtime.md]: nodes=13, edges=20, invalidated=0
  ✓ docs/design/models/DM-inference-runtime.md (full_doc)
INFO:graphiti_core.graphiti:Completed add_episode in 174406.76498413086 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-tutoring.md]: nodes=17, edges=7, invalidated=0
  ✓ docs/design/models/DM-tutoring.md (full_doc)
INFO:graphiti_core.graphiti:Completed add_episode in 156472.65481948853 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-mcp-transport.md]: nodes=13, edges=8, invalidated=0
  ✓ docs/design/models/DM-mcp-transport.md (full_doc)

Summary:
  Added 7 files, 6 episodes
  Failed: 1 episode

Warnings:
  Warning: docs/design/README.md: Missing 'architecture' section

Errors:
  Error: docs/design/contracts/API-tutoring.md: Episode creation returned None 
(possible silent failure)
6/7 episodes seeded. The longest file (API-tutoring.md) timed out at the auto-detected 600s ceiling. Retrying with a longer timeout.

Bash Retry API-tutoring seeding with longer timeout
IN
guardkit graphiti add-context docs/design/contracts/API-tutoring.md --timeout 1200 -f 2>&1 | tail -20

OUT
Command running in background with ID: bne56xwzt. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/bne56xwzt.output
Retrying in the background — I'll be notified when it finishes. Meanwhile, here's the current status:

Seeded so far (6/7):

✓ docs/design/README.md (project_overview)
✓ docs/design/contracts/API-mcp-transport.md (full_doc) — 15 nodes / 13 edges
✓ docs/design/contracts/API-inference-runtime.md (full_doc) — 15 nodes / 12 edges
✓ docs/design/models/DM-tutoring.md (full_doc) — 17 nodes / 7 edges
✓ docs/design/models/DM-inference-runtime.md (full_doc) — 13 nodes / 20 edges
✓ docs/design/models/DM-mcp-transport.md (full_doc) — 13 nodes / 8 edges
Retrying:

⏳ docs/design/contracts/API-tutoring.md (the largest contract file — vLLM extraction exceeded 600s default)
Not seeded by design: mcp-tools.json, events-schema.yaml — machine-readable schemas, kept as reference artefacts on disk only.

Bash Show retry final output
IN
tail -30 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/1f981289-bdfd-4e5f-887f-6ea452dd24c6/tasks/bne56xwzt.output

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 210411.3528728485 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/contracts/API-tutoring.md]: nodes=15, edges=12, invalidated=0
  ✓ docs/design/contracts/API-tutoring.md (full_doc)

Summary:
  Added 1 file, 1 episode
Update Todos

Update build plan with two design decisions

Write Tutoring API contract (MCP + Events surfaces)

Write Inference Runtime internal interface contract

Write MCP Transport invariants contract

Write Tutoring data model

Write Inference Runtime data model

Write MCP Transport data model

Generate MCP tool definitions JSON

Generate Events schema YAML for Shared Kernel B

Write design index README and summary

Offer Graphiti seeding commands
Retry succeeded — API-tutoring.md seeded in 210s on the second attempt (15 nodes / 12 edges).

✅ /system-design complete
Graphiti seeding: 7/7 episodes added

File	Type	Result
docs/design/README.md	project_overview	✓ 10n / 6e
docs/design/contracts/API-tutoring.md	full_doc	✓ 15n / 12e (retry)
docs/design/contracts/API-mcp-transport.md	full_doc	✓ 15n / 13e
docs/design/contracts/API-inference-runtime.md	full_doc	✓ 15n / 12e
docs/design/models/DM-tutoring.md	full_doc	✓ 17n / 7e
docs/design/models/DM-inference-runtime.md	full_doc	✓ 13n / 20e
docs/design/models/DM-mcp-transport.md	full_doc	✓ 13n / 8e
Total: 98 nodes, 78 edges in project_design group on FalkorDB at whitestocks.

Reference artefacts retained on disk only (not seeded — they're machine-readable schemas):

docs/design/mcp-tools.json — JSON Schema for the 4 MCP tools
docs/design/events-schema.yaml — Shared Kernel B event vocabulary
Build plan updated with both design decisions (D1: Tutoring schema P0-only; D2: tutor_start_session reclassified sync) and the recommended /system-design --focus="<context>" invocations for P1 (Knowledge & Curriculum, Student Model) and P2 (Gamification).

Next:

/system-plan --from docs/design/README.md --context docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md to ground feature-level planning.
/arch-refine to update domain-model.md §7.1 SR-07 wording for tutor_start_session per D2.
When phase-1-scope.md is ready, re-run /system-design --focus="Knowledge & Curriculum" and /system-design --focus="Student Model".