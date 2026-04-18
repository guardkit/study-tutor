# Study Tutor — Decisions Log

**Date:** 17 April 2026
**Status:** Canonical — these decisions are do-not-reopen inputs to Phase 0 scope and build plan
**Supersedes:** ad-hoc planning threads
**Referenced by:** `phase-0-scope.md`, `phase-0-build-plan.md` (when drafted)

---

## Purpose

The specialist-agent workflow treats scope documents as capturing already-made decisions, not pending ones. Writing a scope doc over open decisions reopens them. This log captures every decision that shapes Phase 0 scope so the scope doc can hard-code their answers and move on.

Each decision has a one-line resolution, the options considered, and the reasoning for the chosen path. Decisions are numbered so they can be referenced from downstream docs as `DEC-01` through `DEC-08`.

---

## DEC-01 — Demo surface strategy

**Decision:** Open WebUI primary (Phase 1 working surface for Lilymay) + MCP architecture reveal (terminal or Claude Desktop tool invocation) in the demo video.

**Options considered:**
- (a) Open WebUI only — keeps existing path, hides the DeepAgents harness
- (b) Custom minimal UI over MCP — shows architecture directly but costs build time
- (c) **Open WebUI + MCP reveal — chosen**

**Reasoning:** Lilymay is already using Open WebUI; it's the honest "working today" story for the first 30 seconds of the video. Cutting to a terminal or Claude Desktop invocation that shows the session planner querying Graphiti and the Coach evaluating a turn demonstrates the three-layer architecture directly. Both surfaces are already built or trivial to wire. No new UI work.

**Implications for Phase 0:**
- MCP adapter must exist in Phase 0 (not deferred)
- Tools can be minimal: `tutor_start_session`, `tutor_turn`, `tutor_session_status`
- Open WebUI → Ollama path stays unchanged (zero new work)

---

## DEC-02 — Graphiti deployment topology

**Decision:** Synology NAS hosts FalkorDB; Google Gemini handles entity extraction LLM; GB10 serves embeddings only (nomic-embed-text-v1.5 on port 8001). MacBook reaches all three over Tailscale.

**Options considered:**
- (a) Everything on GB10 (per earlier memory and `deepagents-patterns-review.md`) — conflicts with GB10 being reserved for training runs
- (b) **Split topology with Synology + Gemini + GB10 — chosen (reflects actual state as of 16 April 2026)**
- (c) Local FalkorDB on MacBook — creates drift risk between demo and production

**Reasoning:** GB10 needs to be available for two sequential training runs during the build (see DEC-07). Offloading FalkorDB to the Synology NAS and the Graphiti entity extraction LLM to Google Gemini frees GB10 without disrupting tutor operation. Tailscale is proven (1ms RTT direct, non-DERP-relayed per TASK-REV-B8E4 walkthrough). The embedder stays on GB10 because the model is small enough not to block training.

**Implications for Phase 0:**
- Three-hop Graphiti latency (MacBook → Synology FalkorDB + MacBook → Gemini + MacBook → GB10 embeddings) needs a one-day spike in early Phase 1 to measure end-to-end session-turn latency
- If end-to-end Graphiti latency exceeds ~2s per operation, MCP `tutor_turn` must be fire-and-forget rather than synchronous (Lessons §4)
- `.env` must declare `FALKORDB_HOST=<synology-tailscale-name>`, `GRAPHITI_LLM_PROVIDER=gemini`, `EMBEDDER_URL=http://promaxgb10-41b1:8001/v1`

---

## DEC-03 — XP economy publication

**Decision:** Publish the full gamification economy — 15 named levels with unlock gates, 6 achievement categories, concrete XP values, named achievements, topic mastery taxonomy. Lives in `docs/gamification/design.md` and referenced from `domains/gcse-english/GOAL.md`.

**Options considered:**
- (a) Keep as implementation detail inside FEAT-PO-007
- (b) Publish a summary only
- (c) **Publish the full economy — chosen**

**Reasoning:** Judges comparing many AI tutor submissions will reward the one that clearly thought through engagement mechanics to the level of named level titles and specific XP values. It's differentiator content. The demo video needs these specifics anyway. The cost of "having to update numbers if they change during build" is trivial compared to the cost of a generic-sounding submission. Directly addresses the specification-loss failure mode identified in the PO baseline analysis.

**Implications for Phase 0:**
- `docs/gamification/design.md` is a Phase 0 deliverable, not Phase 2
- It can be authored in a single session from `GCSE_Gamification_Research.md` + `gemma4-hackathon-submission-plan.md §5`
- It becomes source of truth for FEAT-PO-007 when that feature lands in Phase 2

---

## DEC-04 — AQA assessment objective scaffolding

**Decision:** Explicit per-AO scaffolding in `domains/gcse-english/GOAL.md`. AO1–AO6 enumerated with behavioural guidance per AO. The Coach's evaluation rubric references AOs explicitly.

**Options considered:**
- (a) Generic "GCSE English" framing
- (b) Middle ground — AOs listed but not woven into behaviour
- (c) **Explicit per-AO scaffolding — chosen**

**Reasoning:** Copyright analysis already settled that AO names and descriptions are factual curriculum structure, not restricted AQA content. The PO baseline analysis flagged AO absence as a major specification gap. The Coach in FEAT-PO-006 needs explicit AO criteria to evaluate "AO alignment" meaningfully — without per-AO guidance, the Coach rubber-stamps. Per-AO behaviour is what separates this tutor from a generic LLM chat.

**Implications for Phase 0:**
- FEAT-PO-001 (GCSE English domain configuration) is the owner of this
- The GOAL.md must include an AO table matching the proposal's AO1–AO6 enumeration with behavioural guidance
- No AQA past-paper questions or mark scheme wording. Specifications and assessment objective definitions only.

---

## DEC-05 — Primary user interface

**Decision:** Open WebUI is Lilymay's primary interface (unchanged from today). Reachy Mini is the target stretch surface (see DEC-06). Static HTML dashboard generated via Claude Design is secondary demo content only.

**Explicitly out of scope for the hackathon:** Flutter/mobile app, custom web app, Reachy-first interaction as primary surface.

**Options considered:**
- (a) Flutter mobile app — correct target long-term, infeasible by 18 May
- (b) Custom React web app — costs build time we should spend on the student model
- (c) **Open WebUI primary + Reachy stretch + static dashboard for video — chosen**

**Reasoning:** Lilymay uses Open WebUI today; it's the honest primary surface. A React dashboard wrapped around the session would cost 3–4 days of build time and would still be secondary to Open WebUI for actual use. A static HTML dashboard generated via Claude Design (one evening of work) bound to a session-export JSON serves the video perfectly without pretending to be a real primary interface. Mobile is the right long-term target but won't ship in 31 days; post-hackathon work.

**Implications for Phase 0:**
- No custom UI work in Phase 0. Open WebUI configuration only.
- FEAT-PO-009 (dashboard) becomes a 1-day Phase 2 task, generated via Claude Design, rendered from a session-export JSON
- Session-export JSON schema is a Phase 1 deliverable (needed regardless for Graphiti write-back; dashboard consumes the same export)

---

## DEC-06 — Reachy Mini integration

**Decision:** Stretch phase, scoped via a separate conversation starter. Hard sequencing rule: Reachy work cannot block Phases 0–2. Go/no-go gate at 4 May (12 days before submission). Fallback: pre-recorded future-vision segment.

**Options considered:**
- (a) Include as a full feature in the hackathon roadmap — too much unknown
- (b) Skip entirely, future-vision only — leaves a genuine differentiator on the table
- (c) **Stretch phase with hard go/no-go gate — chosen**

**Reasoning:** Reachy Mini is a genuine judging differentiator — few if any submissions will have an embodied companion. Scholar ordered ~25 January with 90-day delivery puts expected arrival at ~25 April; Bridge followed a week later. Pollen Robotics have been running late across the industry so delivery before early May is not guaranteed. Integration effort is unknown — Raspberry Pi 4 onboard, Python SDK, network-reachable from MacBook, but the Graphiti-state → verbal-speech pipeline hasn't been designed. Scoping this properly requires a dedicated research session with the Reachy SDK docs in hand.

**Implications for Phase 0:**
- Write `docs/research/ideas/reachy-integration-conversation-starter.md` as part of the Phase 0 documentation deliverables
- The conversation starter describes scope, integration shape, demo-moment minimum, fallback, and the go/no-go gate criteria
- When Scholar arrives (or on 4 May, whichever comes first), spin up a dedicated Claude Desktop thread against that conversation starter
- Phase 0, 1, 2 scope docs include a `reachy_dependency: none` note so sequencing is unambiguous

**Go/no-go gate criteria (4 May):**
- Scholar has arrived and is operational on the home network
- Python SDK has been exercised end-to-end (at least "hello world" verbal output)
- Tailscale or local-network path from MacBook to Scholar confirmed

If all three green, proceed with a scoped integration; if any red, fall back to pre-recorded future-vision segment.

---

## DEC-07 — GB10 compute scheduling

**Decision:** GB10 runs three sequential workloads during the build, with explicit scheduling rather than concurrent execution. Study-tutor inference migrates off GB10 before demo week to remove the conflict entirely.

**Workload sequence:**

1. **Study-tutor training dataset expansion** — additional subjects (Maths, possibly French/Spanish specimen) via agentic-dataset-factory
2. **Study-tutor fine-tune** — Gemma 4 31B LoRA via Unsloth, incorporating the expanded dataset
3. **Architect-agent training dataset + fine-tune** — for DDD Southwest demo (16 May); architect-agent target June–July per specialist-agent `phaseF` docs but the DDD demo may accelerate a first run
4. **Demo-week inference hosting** — GB10 becomes available once architect training completes

**Tutor inference hosting during GB10-busy periods:**

AWS Bedrock Custom Model Import. Validates the pipeline as a Phase 1 deliverable, frees GB10 for training, and — critically — removes the GB10-availability dependency from demo week entirely. Scale-to-zero serverless hosting, cold start 30–60s acceptable, cost ~$1.50–3.00 per 5-minute billing window for ~31B model (per existing memory).

**Product-owner agent:** Stays on GPT-5.4 (cloud API). No GB10 involvement.

**Options considered:**
- (a) Run training and inference concurrently on GB10 — not feasible for 31B-scale workloads
- (b) Pause training during demo recording — fragile, requires exact scheduling
- (c) **Migrate inference to Bedrock, free GB10 entirely — chosen**

**Reasoning:** The Bedrock validation is paid-for learning regardless (memory already flags it as a Phase 2 deliverable). Moving it earlier to Phase 1 removes the scheduling conflict and de-risks demo week. OpenWebUI can point at Bedrock via an OpenAI-compatible proxy (LiteLLM, OpenRouter, or similar) — one evening of configuration, not a build task.

**Implications for Phase 0:**
- Bedrock Custom Model Import becomes a **Phase 1 deliverable**, not Phase 2
- Week 1 (Phase 0) keeps Ollama + GB10 for Lilymay's day-to-day use
- Week 2 (Phase 1) validates Bedrock with the existing fine-tuned model; OpenWebUI reconfigured to point at Bedrock via proxy
- From Week 2 onward, GB10 is free for the training sequence
- Architect-agent training sequence gets the GB10 from Week 3 onward

---

## DEC-08 — Gemini-based Graphiti performance posture

**Decision:** Proceed with Gemini as Graphiti entity-extraction LLM without pre-validating latency. Treat Gemini response time as a monitored variable during Phase 1 Graphiti spike; switch back to a local model on GB10 only if latency materially degrades session experience.

**Options considered:**
- (a) Benchmark Gemini before Phase 1 — delays the Phase 0 kickoff for uncertain benefit
- (b) **Monitor during Phase 1 spike, act on measurement — chosen**
- (c) Revert to local Graphiti LLM on GB10 — conflicts with DEC-07 training schedule

**Reasoning:** Rich is paying for Gemini, so cost-per-call is not a factor. Gemini 2.5 Pro latency is typically 1–3s per extraction call, which is within the fire-and-forget budget for Graphiti write-back (async to the tutoring turn). If the Phase 1 spike shows latency > 5s consistently, revisit. Don't pre-optimise.

**Implications for Phase 0:**
- Phase 1 includes a Graphiti spike as an explicit deliverable with end-to-end latency measurement
- Graphiti write-back is async (fire-and-forget from the tutor's perspective) regardless of Gemini latency
- No Phase 0 blocker; no Phase 0 action required

---

## Derived scope changes (summary)

These flow from the decisions above and will be reflected in the Phase 0 scope doc:

| Area | Change from earlier plan |
|---|---|
| Phase 0 deliverables | Add `docs/gamification/design.md` (DEC-03), `docs/research/ideas/reachy-integration-conversation-starter.md` (DEC-06); MCP adapter stays in Phase 0 (DEC-01) |
| Phase 1 deliverables | Add Bedrock Custom Model Import validation (DEC-07), explicit Graphiti spike with latency measurement (DEC-02 + DEC-08); session-export JSON schema (DEC-05) |
| Phase 2 deliverables | Dashboard becomes 1-day Claude-Design-generated task (DEC-05); Reachy if go/no-go passes (DEC-06); compute scheduling no longer a concern (DEC-07 resolved it) |
| Out of scope | Mobile/Flutter app, custom React web app (DEC-05); concurrent GB10 training + inference (DEC-07) |
| Decision-dependencies on hardware arrival | Only Reachy (DEC-06), and it has a clear fallback |

---

## What's still genuinely uncertain

These were not decided here and will need answers during the build, but they don't block Phase 0:

- **Session lifecycle timeout budget** — depends on Phase 1 Graphiti latency spike (DEC-02, DEC-08)
- **Reachy go/no-go** — depends on hardware arrival and SDK spike (DEC-06)
- **Bedrock proxy choice for OpenWebUI** — LiteLLM vs OpenRouter vs other (DEC-07); evening's work during Phase 1
- **Architect-agent training first-run timeline** — depends on DDD Southwest talk prep cadence (DEC-07); separate from this plan

---

## Revision policy

These decisions are do-not-reopen unless new evidence materially changes the picture. Examples of material evidence:

- Reachy Mini confirmed non-deliverable before submission (triggers DEC-06 fallback)
- Bedrock Custom Model Import proves unworkable during Phase 1 (triggers DEC-07 reconsideration — likely reverting to Ollama-on-GB10 with training-run scheduling)
- Gemini Graphiti latency exceeds 5s consistently (triggers DEC-08 reconsideration — likely reverting to a local model hosted on something other than GB10)
- Kaggle hackathon rules (finally read) impose a constraint not anticipated (may trigger multiple decisions)

If a decision is reopened, the log is updated in place with a new dated revision rather than regenerated. The phase docs then re-read the updated log.

---

*Related documents:*
- `docs/research/ideas/state-of-the-project-and-phase-recommendation.md` — the analysis that surfaced these decisions
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` — LES1, the six parity surfaces
- `specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md` — the MacBook walkthrough evidencing Tailscale + specialist-agent reliability
- `docs/research/ideas/gemma4-hackathon-submission-plan.md` — the roadmap these decisions refine
