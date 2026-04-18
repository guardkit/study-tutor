# Study Tutor — State of the Project and Phase Recommendation

**Date:** 17 April 2026
**Author:** Rich / Claude Desktop
**Audience:** Rich (self) and future Claude sessions picking up this work
**Status:** Draft — supersedes ad-hoc planning threads; to be reviewed before any `/system-arch` call
**Deadline anchor:** Gemma 4 Good Hackathon submission, 18 May 2026, 23:59 UTC

---

## 1. Why this document exists

We are further along on Study Tutor than recent conversation threads suggest. A full stocktake of the existing artefacts was run before drafting any new scope or build plan, because the baseline analysis of the `po_extract` run (`po-extract-1862adb2-baseline-analysis.md` in `specialist-agent/docs/reviews/claude-desktop-mcp-runs/`) showed that jumping to a roadmap without first grounding in existing material produces generic output. That finding applies equally to human planning: write the Phase 1 scope doc first and you inherit your own blind spots.

This document is the grounding step. It catalogues what actually exists across the three repos relevant to Study Tutor, maps it to the 13-feature roadmap already produced, folds in the six parity-surface lessons from `specialist-agent`, and ends with a concrete recommendation for the phase sequence to the 18 May deadline.

---

## 2. What exists today

### 2.1 The `study-tutor` repository

Repo state: README stub (two lines), empty `migrations/` directory, LICENSE, `.gitignore`. No `src/`, no `pyproject.toml`, no code. All current material is in `docs/`.

**Product thinking (already produced by the Product Owner agent):**

| Artefact | Location | Content |
|---|---|---|
| Full roadmap | `docs/product/roadmap/roadmap.md` | 13 features across 5 epics, Phase 1/Phase 2 split, 6 assumptions, 4 open questions |
| Per-feature spec inputs | `docs/product/roadmap/feature_spec_inputs/FEAT-PO-001.md` … `FEAT-PO-013.md` | Each feature as a standalone markdown, ready for `/feature-spec` consumption |
| Scoped roadmap (earlier, narrower) | `docs/product/scope/roadmap-scoped.md` | 4 features across 2 epics — cut too aggressively; treat as historical |

The roadmap already covers: GCSE English domain contract, fine-tuned runtime, BYOS packaging, Graphiti student model, session planner, DeepAgents loop with quality monitor, gamification state + event engine, adaptive challenges + Boss Battle, dashboard, multi-subject template, AgentManifest, demo narrative, technical write-up.

**Research / grounding docs:**

| File | Contribution |
|---|---|
| `GCSE_English_AI_Tutor_Proposal.md` | Product scope, AQA AOs (AO1–AO6), hardware (GB10 + Reachy), software stack |
| `GCSE_Gamification_Research.md` | XP economy with concrete values, 6 achievement categories, named achievements, Boss Battle mechanics |
| `deepagents-patterns-review.md` | Three-layer architecture, Player-Coach quality gate, session lifecycle, domain-as-config, AgentManifest, Phase 2 directory structure |
| `copyright-training-data-analysis.md` | AQA vs Mr Bruff provenance policy, three-layer synthetic transformation framework, public/private asset matrix |
| `gemma4-hackathon-submission-plan.md` | 15-level progression with unlock gates, topic mastery taxonomy, Phase 1 vs Phase 2 deployment reality, real-student context (Lilymay, AQA 8700 + 8702) |
| `po-extract-roadmap-1862adb2.md` | Snapshot of the PO agent run that produced the roadmap (coverage score 0.9, later assessed as ~0.4 specification fidelity) |

### 2.2 The existing fine-tuned model and pipeline (per memory and operational state)

These exist on GB10 today and are **not blockers** for the hackathon:

- **Fine-tuned model:** Gemma 4 31B Dense LoRA, ~1,736 training examples, ~2h 5min training time, final loss 0.7015. Merged 16-bit weights + Q4_K_M GGUF persisted at `~/fine-tuning/output/gcse-tutor-gemma4-31b/`.
- **Serving path:** Ollama on GB10, accessible over Tailscale. Lilymay has been using this.
- **Knowledge pipeline:** Docling fully validated on GB10 (standard + VLM modes). ChromaDB available.
- **Dataset factory:** `agentic-dataset-factory` proven at 94.8% acceptance on the GCSE run, Player-Coach adversarial loop working.

What this means: the Layer 1 (behaviour) and Layer 2 (knowledge) of the three-layer architecture are already in production for a single user. What's missing for the hackathon submission is Layer 3 (Graphiti student model), the DeepAgents harness that orchestrates the three layers in a live session, and the gamification engine that makes the experience retention-worthy.

### 2.3 What `specialist-agent` just taught us (and what carries over)

The specialist-agent walkthrough (TASK-REV-B8E4) and the resulting cross-agent lessons document (`specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`) are the single most important input to Study Tutor's Phase 0 plan. Key points that apply here:

**Six parity surfaces** — the minimum gate before first merge:

1. **Transport** — stdout MCP discipline; banner to stderr; absolute CWD in launcher
2. **Provider** — env-resolved at the factory; smoke test each declared provider
3. **Packaging** — `[providers]` extra lists every LangChain integration; Dockerfile literal-match
4. **Handler** — every listed tool has a method at every layer
5. **Tooling** — fire-and-forget + poll for anything that can exceed 30s; tool description matches behaviour
6. **Ops** — `.env` hygiene, provisioning not self-healing, orphan containers documented

**The study-tutor-specific rows in the pre-implementation checklist:**

- NATS rows (3–5, 12, 13, 16) are marked "—" for study-tutor: it can ship MCP-only
- Row 10 (fire-and-forget above 30s) is marked ⚠️ — confirm the tutor has no generation loop, quiz, or multi-turn evaluation exceeding 30s
- Row 19 (latency classification) same warning — tutoring turn may be short, but a full session is long
- Row 21 (accumulated-latency surfaces) is ticked ✅ — multi-turn tutoring session is the exact shape the lessons doc flags as load-bearing for Study Tutor

**What this changes from my earlier thinking:** Phase 0 cannot be "package existing work." It must include MCP transport hygiene, the fire-and-forget pattern for tutoring sessions, and the provider/packaging rigour that specialist-agent learned the hard way. We are not starting from zero — we are starting from a lessons doc that was written specifically so we don't repeat those mistakes.

### 2.4 The `specialist-agent` pattern we're inheriting

The phase + scope + build plan pattern used on specialist-agent is directly applicable:

- `docs/research/ideas/phase-{N}-scope.md` — what's in scope, what's out, success criteria, do-not-change list
- `docs/research/ideas/phase-{N}-build-plan.md` — feature breakdown, dependency chain, task order, risk register
- `command_history.md` at repo root — shell log capturing `/system-arch`, `/system-design`, `/system-plan`, `/feature-spec`, `/feature-plan`, `/feature-build` invocations with their output
- `/feature-spec` consumes scope + build plan via `--context`, plus relevant source files

Scope docs in specialist-agent are 8–20KB; build plans are 12–30KB. Pairs exist for Phase 1, 1B, 1C, 2, 3, F, G. This is the target format.

---

## 3. Gap analysis — where the roadmap meets the lessons doc

The 13-feature roadmap was produced before the lessons doc. Cross-referencing them surfaces gaps the roadmap doesn't cover:

| Gap | Source | Where in Study Tutor? |
|---|---|---|
| MCP transport hygiene (stdio discipline, stderr banner, CWD trap) | Lessons §1 | Not in roadmap — must be Phase 0 AC |
| Fire-and-forget + poll for long tools | Lessons §4 | Not in roadmap — tutoring session shape makes this load-bearing |
| Provider env resolution at factory | Lessons §3 | Not in roadmap — must be built in, not bolted on |
| `[providers]` extra + Dockerfile literal-match | Lessons §3 | Not in roadmap — applies from first merge |
| `.env` hygiene (no placeholder secrets) | Lessons §3 | Not in roadmap — CI pre-merge check |
| Six parity-surface audit before first merge | Lessons §§1–7 | Not in roadmap — must be a Phase 0 definition-of-done |
| Tool description ≡ implementation contract | Lessons §4 | Not in roadmap — relevant when MCP tools are registered |
| Live verification on clean machine before canonical freeze | Lessons §5 | Not in roadmap — relevant for demo prep |

None of these are features in the product sense — they are cross-cutting constraints that need to be structural properties of the codebase from day one. They will show up in the Phase 0 build plan as **definition-of-done criteria**, not as separate features.

---

## 4. The feasibility question you raised

> Given we have just got the specialist agent working via MCP and NATS we could feasibly get the fine tuned model + rag + graphiti + deep agent working with say Ollama and openwebui in time for the submission.

Let me walk through this seriously rather than just agreeing.

### 4.1 What's genuinely reusable

The specialist-agent delivery gave us, as engineering leverage:

- **Working MCP adapter pattern** — `src/specialist_agent/mcp/adapter.py` with stdio discipline, fire-and-forget + poll for PO, architect-style synchronous for feasibility. The Study Tutor MCP server should be architecturally similar: expose `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` as MCP tools.
- **Role-aware CommandRouter** — though Study Tutor is single-role, the pattern of instance-level command maps, `for_role()` factory, and strict dispatch matrices applies.
- **Provider resolution pattern** — `_default_player_model()` reading `AGENT_MODELS__REASONING_MODEL` is directly copyable.
- **Graphiti wiring** — session write-back, group IDs (`project_decisions`, `task_outcomes`, per-role prefixes), KV patterns. Tutor writes to `student:{id}:topic_confidence`, `student:{id}:session:{date}`, etc.
- **DeepAgents Player-Coach pattern** — two `create_deep_agent()` instances with different prompts, Coach at `tools=[]`, configurable coach model, turn limit. Copy directly from `agentic-dataset-factory`.
- **Domain-as-config pattern** — `domains/{name}/GOAL.md` + `sources/` — copy directly from dataset factory; swap "training data generation" for "tutoring behaviour."
- **All 6 parity-surface lessons** — codify from day one, don't re-learn them.

### 4.2 What's new for Study Tutor

- **Interactive tutoring harness** — specialist-agent's Player-Coach is batch; tutor is interactive. Session lifecycle (start → topic select → interactive loop → summary → gamification update → persistence) is new work.
- **Graphiti student model entities** — not just "sessions I've run," but `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence` with per-student scoping. New schema.
- **Gamification state machine** — XP awards, streak tracking, achievement evaluation, level-up checks, Boss Battle unlock gating. Deterministic rules layer; does not exist yet.
- **Open WebUI integration** — MCP-over-something (SSE? stdio via a bridge?) to Open WebUI. The MCP adapter is trivially reusable; the Open WebUI bridge is new.
- **Dashboard** — FEAT-PO-009. React / static HTML mockup for the demo video; real data binding is a stretch goal.

### 4.3 The 31-day burn from here

Today is 17 April 2026. Deadline is 18 May 2026. That's **31 calendar days**.

Constraints on those 31 days from memory and the `gemma4-hackathon-submission-plan.md`:

- 16 May is DDD Southwest (Bristol) — a day out, plus prep in the preceding days. Effectively lose ~4 days to DDD prep + travel + day.
- Final 17–18 May is submission polish (repo clean, video upload, Kaggle submission) — not build time.
- Weekends are working time but with reduced throughput.

Realistic build days: ~**22 working days** before submission week starts, minus DDD overhead. Call it **18 working days of actual build**.

### 4.4 Can Phase 0 + Phase 1 (three-layer + Graphiti) fit in 18 days?

**Honest assessment: yes, if Phase 0 is narrow and ruthless about reuse.**

The non-negotiables for 18 May:

1. A public repo that passes the six parity surfaces (demonstrated in a clean walkthrough) — Phase 0
2. The working fine-tuned tutor accessible to Lilymay and demoable on video (already exists on Ollama — just needs packaging) — Phase 0
3. The three-layer architecture **visible and credibly instantiated** — fine-tuning (done), RAG (already working via ChromaDB on GB10), Graphiti student model (new) — Phase 1
4. At least a thin slice of the interactive DeepAgents harness with Player-Coach quality monitor, proving the architecture runs end-to-end — Phase 1
5. Technical write-up covering methodology, provenance, architecture, and roadmap — Phase 0

**Not non-negotiable:**

- Full gamification engine (Phase 2) — can ship as "design complete, Pydantic models in repo, dashboard mockup" and still score well on the engagement criterion. Fully-wired Boss Battle is a stretch.
- Multi-subject expansion (Phase 3) — design complete, one additional GOAL.md as proof-of-pattern. Not implemented.
- Reachy integration — vision segment in the demo video; not code.
- Open WebUI bridge — use the existing Ollama + Open WebUI setup on GB10 for the demo; the new DeepAgents harness can be demonstrated via a minimal custom interface or CLI.

### 4.5 Where the risk concentrates

The hardest piece is **FEAT-PO-006: DeepAgents tutoring loop with quality monitor** — because this is where all three architectural ideas (three-layer, Player-Coach, interactive session lifecycle) converge. If this is still unwritten on 12 May, the submission risks demoing the existing Ollama tutor + architecture slides only, which is weaker than the full story but still a credible entry.

Secondary risk: **Graphiti student model schema design** (FEAT-PO-004). Underspecified Pydantic models here ripple into session planner, gamification engine, and write-back. Worth over-investing in the schema design day.

Lesser risk: **session planner** (FEAT-PO-005). Once the student model exists, the planner is a small amount of rule-based code selecting a topic from Graphiti state. Not technically demanding; only risky if the student model is late.

---

## 5. Recommended phase sequence

### Phase 0 — Hackathon Floor + Parity Hygiene (Week 1: 21–27 April)

**Goal:** a clean, public-repo-ready project skeleton that passes the six parity surfaces, wraps the existing Ollama deployment as a working MCP-accessible tutor, and documents the provenance and architecture in a way that could be submitted on its own if Phase 1 slips.

**Features from roadmap:** FEAT-PO-001 (English domain config), FEAT-PO-002 (fine-tuned runtime over local deployment), FEAT-PO-003 (BYOS packaging), FEAT-PO-013 (technical write-up — start early, polish throughout).

**Parity surface deliverables** (not features, but structural requirements):

- MCP adapter skeleton with stdio discipline and stderr banner
- Bash MCP wrapper with absolute-path `cd`
- Provider resolution at the factory via `AGENT_MODELS__REASONING_MODEL`
- `[providers]` extra in `pyproject.toml` listing every LangChain integration actually used
- Dockerfile literal-matches documented extras (if Dockerfile ships in Phase 0; defer if not)
- `.env.example` only — no `.env` with placeholder keys
- Tool descriptions match handler behaviour

**Exit criteria:** a clean-machine walkthrough reproduces the tutor from the public repo README + BYOS sources, hits `tutor_turn` over MCP, gets a response from the fine-tuned model, no stdout noise, no provider surprises.

### Phase 1 — Three-Layer Architecture + Student Model (Weeks 2–3: 28 April – 11 May)

**Goal:** make the three-layer architecture real. Fine-tuned Gemma 4 (Layer 1, exists) + ChromaDB curriculum RAG (Layer 2, exists) + Graphiti student model (Layer 3, new) orchestrated by a DeepAgents tutoring harness with a Player-Coach quality monitor.

**Features from roadmap:** FEAT-PO-004 (Graphiti student profile + topic confidence), FEAT-PO-005 (session planner), FEAT-PO-006 (DeepAgents tutoring loop with quality monitor).

**What "working" means for the submission:**

- Lilymay starts a session; the planner queries Graphiti and suggests a topic based on weakest confidence
- The tutor takes multiple turns with her, Player generates responses, Coach evaluates each turn's pedagogical quality, low-quality turns are flagged (or regenerated in a stretch implementation)
- At session end, Graphiti is updated: topic confidence, session episode, any misconceptions surfaced
- Next session, the planner knows what was covered and adapts

**Fire-and-forget + poll pattern:** `tutor_start_session` returns `session_id` immediately. `tutor_turn` is synchronous per-turn (likely sub-10s). `tutor_session_status` returns current state, turns taken, XP accrued. This splits the "short sync turn" path from the "long session-lifecycle" path correctly per Lessons §4.

**Exit criteria:** a recorded session where the tutor demonstrably uses state from a prior session. Video-captureable in the demo.

### Phase 2 — Gamification Thin Slice + Demo Assets (Week 4: 12–16 May)

**Goal:** the engagement layer visible in the demo, even if not fully wired to all events. The demo narrative needs XP, streak, an achievement unlock, and a visible level progression.

**Features from roadmap:** FEAT-PO-007 (state model + event engine — ship Pydantic models and core rules; wire to session completion and streak-checking events minimally), FEAT-PO-009 (dashboard — can be React artifact or static HTML mockup binding to real Graphiti state where possible, mocked where not), FEAT-PO-012 (demo narrative + evidence capture — video, screen recordings).

**Explicitly deferred:**

- FEAT-PO-008 (Boss Battle generation) — show as design slide only, not implemented
- FEAT-PO-010 (subject template) — one extra `GOAL.md` as proof, not fine-tuned
- FEAT-PO-011 (AgentManifest) — design doc only
- Reachy interaction — vision segment in video

**Exit criteria:** demo video captured, written submission drafted, repo frozen Friday 15 May for final polish.

### Phase 3 — Submission (17–18 May)

Final polish, video edit, Kaggle submission before 23:59 UTC Sunday 18 May. Repo tagged. ADRs annotated "as of commit X." Guide copy-paste blocks live-verified per Lessons §8.

---

## 6. What we should NOT do

**Re-extract the roadmap.** We have a 13-feature roadmap already. The `po_extract` run that produced it scored 0.9 per the Coach and ~0.4 per human review against source docs. But the gaps the human review identified are things we know about and can manually inject into the scope docs — there's no value in running another extract.

**Write Phase 0 scope + build plan docs before answering the open decisions below.** The specialist-agent pattern works because scope docs capture already-made decisions, not pending ones. Writing a scope doc over open decisions reopens them.

**Build a new fine-tuning run for the hackathon.** The existing model works. Spending a week on `train.jsonl` improvements is time not spent on the Graphiti student model. The copyright analysis document already argues the existing model is hackathon-appropriate.

**Build multi-subject support before the deadline.** The architecture must *support* it (FEAT-PO-010 design, FEAT-PO-011 manifest), but implementing Maths or French before 18 May dilutes English quality with no corresponding judging benefit.

**Skip the six parity surfaces because "it's just a hackathon."** Those lessons were paid for. Study Tutor ships MCP-only, which drops half the NATS rows, but the other half are load-bearing and cheap to get right from day one.

---

## 7. Open decisions that need resolution before Phase 0 scope

These are the decisions I can't make for you. They need settling before the `/system-arch` call, because the scope doc will hard-code their answers as do-not-reopen entries.

1. **MCP-only, or MCP + something else for the demo?** Open WebUI on GB10 is the most visible interface for Lilymay today. Demoing through it keeps the story simple. But it means the MCP adapter is infrastructure, not the user-facing product. Decision needed: is the demo video shot against Open WebUI (keeps existing path working) or against a custom minimal UI (shows the DeepAgents harness more directly)?

2. **Graphiti deployment target.** FalkorDB on GB10 (already operational per memory), or something closer to the tutor's runtime? If GB10, the tutor needs a network path to it; if Tailscale, that's fine for single-user Lilymay but awkward for a hackathon demo video shot on a MacBook.

3. **The 15-level progression and 6-category achievement taxonomy** — the roadmap treats these as implementation detail inside FEAT-PO-007. Are they? Or is the specific XP economy (Scholar at L14, Boss Battle at L15, Macbeth Master at 80% confidence, Fortnight Force at 14 days) part of the public-repo content you want in the submission? This is a write-up decision as much as a code decision.

4. **AQA assessment objective handling.** The copyright doc says AO names and descriptions are acceptable (factual curriculum structure); AQA past paper questions and mark schemes are not. In the GOAL.md for English, how explicit should the AO scaffolding be? Per-AO behavioural guidance is a first-class product decision.

5. **Dashboard — functional or mockup?** FEAT-PO-009 says "Can begin as a mockup or thin UI over real state if time is limited." A React artifact bound to Graphiti is a stretch; a static HTML rendering of a real session export is the realistic middle path; pure mockup is the cheap path. Decision: which of the three is the demo target?

6. **Reachy Mini vision segment — include or skip?** If the robots have arrived by early May, a 30-second clip of Scholar verbally reporting Lilymay's progress is compelling demo content. If not, the submission needs to not depend on it.

---

## 8. Proposed next action

Before drafting `phase-0-scope.md` and `phase-0-build-plan.md`, resolve the open decisions in §7 — ideally in a short session where each is answered with a one-line decision log entry.

Once those are settled:

1. Draft `phase-0-scope.md` in this folder, matching the specialist-agent format (Motivation, Scope, Do-Not-Change, Success Criteria). Scope should cover FEAT-PO-001, -002, -003, -013 plus the parity surface deliverables as a cross-cutting requirements section.
2. Draft `phase-0-build-plan.md` alongside it (Prerequisites, Feature Summary, per-feature Build Order, Risk Mitigation, Expected Timeline).
3. Initialise `command_history.md` at the repo root.
4. Run `/system-arch` with those two docs plus the existing research ideas as context.

The specialist-agent workflow then takes over: `/system-arch` → `/system-design` → `/system-plan` → per-feature `/feature-spec` → `/feature-plan` → `/feature-build` or `/task-work`.

Phase 1 scope + build plan can be drafted in parallel with Phase 0 build, because the feature dependencies are clear and the Phase 1 decisions are largely settled by the research docs (three-layer architecture, Graphiti student model, Player-Coach loop — all specified in `deepagents-patterns-review.md`).

---

## 9. One-paragraph summary

Study Tutor is not a greenfield project. The fine-tuned Gemma 4 31B, the ChromaDB curriculum layer, Docling ingestion, and the Ollama deployment all exist and are working for Lilymay. The 13-feature roadmap exists. The gamification design is specified in concrete mechanics. The lessons doc from specialist-agent tells us which pitfalls to avoid structurally. What's missing is Layer 3 (Graphiti student model) and the DeepAgents harness that orchestrates all three layers in a live interactive session — plus the parity hygiene that lets the public repo walkthrough pass on a clean machine. Those two pieces, plus packaging, plus a visible gamification slice, plus a written submission, is a feasible 31-day burn if we scope ruthlessly, reuse aggressively from `specialist-agent` and `agentic-dataset-factory`, and settle the six open decisions in §7 before the first `/system-arch` call.

---

*Related documents:*
- `docs/product/roadmap/roadmap.md` — 13-feature roadmap
- `docs/research/ideas/deepagents-patterns-review.md` — Phase 2 architectural grounding
- `docs/research/ideas/gemma4-hackathon-submission-plan.md` — submission strategy
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` — the six parity surfaces
- `specialist-agent/docs/reviews/claude-desktop-mcp-runs/po-extract-1862adb2-baseline-analysis.md` — why we grounded before drafting

---

## Appendix A — Template selection

Added 17 April 2026 after reviewing the GuardKit template store, the shipped `langchain-deepagents*` templates, the `deepagents-player-coach-exemplar` and `deepagents-orchestrator-exemplar` source projects, and the GuardKit guide on creating local templates (https://guardkit.ai/guides/creating-local-templates/).

### A.1 What exists in the template store today

GuardKit ships three DeepAgents-family templates at `installer/core/templates/`:

| Template | Shipped source | Adversarial shape | Evaluation | Status |
|---|---|---|---|---|
| `langchain-deepagents` | `deepagents-tutor-exemplar` (per manifest) | Player-Coach | Binary accept/reject | Reference, complexity 10/10, 96.67% confidence |
| `langchain-deepagents-weighted-evaluation` | `deepagents-tutor-exemplar` (per manifest) | Player-Coach | Weighted multi-criteria with thresholds and intensity modes | Reference, extends base, 95% confidence |
| `langchain-deepagents-orchestrator` | `deepagents-orchestrator-exemplar` | Two-model reasoning + implementation | N/A (pipeline, not adversarial) | `production_ready: false`, `learning_resource: true`, 77.5/100 quality |

None of these is a fit as-is for Study Tutor. Specifically:

- **None include the MCP adapter pattern** (stdio discipline, fire-and-forget + poll, tool registration). That pattern was built in `specialist-agent` and is not yet templatised.
- **None include the NATS fleet integration or AgentManifest wiring.** Again, specialist-agent work, untemplatised.
- **None include Graphiti write-back or the role-aware CommandRouter.** Same story.
- **None include an interactive session lifecycle.** The weighted-evaluation template is batch (data generation / architecture generation). The tutor is turn-based with accumulated-session latency — the exact shape Lessons §4 flags as load-bearing.
- **None include Ollama + vLLM runtime abstraction.** Study Tutor needs both: Ollama for Phase 1 (working today), vLLM as Phase 2 target.
- **None include the three-layer architecture made concrete.** The existing templates are single-layer from an artefact perspective (behaviour only).

The GuardKit template philosophy explicitly addresses this: *"Your production code is better than any generic template. Create templates from what you've proven works."* The shipped templates are evaluation resources, not the starting point for real projects.

### A.2 What `specialist-agent` actually proved works (post-TASK-REV-B8E4)

The specialist-agent repo contains, as of today:

- Player-Coach weighted evaluation loop (inherited from the base pattern, extended with domain fidelity and role awareness)
- MCP adapter with stdio discipline, stderr banner, fire-and-forget + poll for long-running PO handlers, synchronous for architect handlers
- Role-aware CommandRouter (`for_role(role_id)` factory, instance-level command maps, strict `(role, command)` dispatch matrix)
- Provider resolution at the factory (`_default_player_model()` reading `AGENT_MODELS__REASONING_MODEL`, `[providers]` extra with `langchain-openai`/`langchain-anthropic`/`langchain-google-genai`)
- NATS fleet adapter with AgentManifest registration, heartbeat, command/result messaging on `agents.command.<id>` / `agents.result.<id>`
- Graphiti integration: query-at-startup, session write-back, group IDs per role, artefact typing
- Dockerfile matching documented venv extras, `.env.example` hygiene
- `roles/{role}/role.yaml` domain-as-config pattern with criteria, prompts, mode inference, fleet tool declarations
- Task-review discipline: TASK-REV task type, walkthrough logs, the six parity surfaces as a pre-merge gate

**None of this is in any shipped GuardKit template.** It is the "lessons paid for" content of `cross-agent-lessons-from-specialist-agent.md`.

### A.3 What `agentic-dataset-factory` adds that specialist-agent doesn't have

- `domains/{name}/GOAL.md` + `sources/` pattern, proven at scale (94.8% acceptance on GCSE English run)
- Docling ingestion pipeline (standard + VLM modes, both validated on GB10)
- ChromaDB seeding from ingested sources
- `<think>` block reasoning format (75/25 ratio) in generated outputs
- Format gate handling (whitespace key bug, `<think>` leakage monitoring)
- Output archiving between runs (`agent.py` wipes `output/train.jsonl` on each run)

These are the Layer 2 (RAG knowledge) and data-pipeline pieces that Study Tutor inherits but that specialist-agent never needed.

### A.4 What Study Tutor needs that neither has

- **Interactive session lifecycle** — start → plan → turn × N → summary → gamification update → persistence. Neither specialist-agent (batch generation) nor dataset-factory (batch generation) exercises this shape.
- **Graphiti student model schema** — `Student`, `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence` entities with per-student group IDs. Specialist-agent writes task/project decisions to Graphiti but has no student-model-equivalent schema.
- **Gamification state machine** — XP awards, streak tracking, achievement evaluation, level-up checks, Boss Battle unlock gating as deterministic rules. Novel to Study Tutor.
- **Ollama runtime path** — specialist-agent is API-provider-backed. The tutor runs locally on GB10 via Ollama today.
- **Open WebUI compatibility** — the existing user-facing interface for Lilymay.

### A.5 Decision: build a new exemplar, cut a template from it

Three options on the table:

**Option 1: Use `langchain-deepagents-weighted-evaluation` as-is.** Fastest start, but misses all six parity surfaces, MCP, NATS, Graphiti, and the interactive session shape. We would re-derive the lessons in a second walkthrough. **Rejected — this is exactly the failure mode the lessons doc exists to prevent.**

**Option 2: Fork `specialist-agent` and adapt.** Closer to right, but specialist-agent has the wrong bounded context (architecture / product-owner roles, not tutoring). The adaptation work equals building a new repo and the fork creates a confusing parent relationship. **Rejected — the role model doesn't transfer cleanly.**

**Option 3: Build `deepagents-tutor-exemplar` as a new exemplar repo, cut a `langchain-deepagents-tutor` template from it after Phase 1.** This is the GuardKit-idiomatic path per the template philosophy ("create templates from what you've proven works"). The exemplar becomes Study Tutor itself during Phase 1 — the hackathon submission IS the exemplar. Post-hackathon, `/template-create` extracts the template. **Recommended.**

### A.6 What the new exemplar combines

Drawn from the deepagents-patterns-review document and the source projects:

| Subsystem | Source | What carries over |
|---|---|---|
| Player-Coach weighted evaluation | `langchain-deepagents-weighted-evaluation` template + `specialist-agent` | Base Player-Coach loop, weighted criteria, adversarial intensity modes, but adapted from batch to interactive |
| Role-aware CommandRouter | `specialist-agent` | Single-role instance here (tutor), but the pattern stays so a future subject-specialist split is cheap |
| MCP adapter | `specialist-agent` | Fire-and-forget + poll for `tutor_start_session`; synchronous for `tutor_turn` if sub-10s, async if not |
| Provider resolution | `specialist-agent` | Factory-level resolution supporting Ollama (local), vLLM (local, Phase 2), and API fallback |
| Graphiti integration | `specialist-agent` | Write-back pattern reused, schema redesigned for student-model entities |
| Domain-as-config | `agentic-dataset-factory` | `domains/gcse-english/GOAL.md` + `sources/` for ingestion and tutoring behaviour |
| Docling + ChromaDB ingestion | `agentic-dataset-factory` | Copy the pipeline directly; same scripts, different target (curriculum RAG, not training data) |
| Session lifecycle + gamification state machine | **New** | Built in Study Tutor; extracted to template post-hackathon |
| AgentManifest | `nats-core` pattern (per memory) | Tutor declares capabilities (subject, interface, tools) for future fleet integration |

### A.7 Proposed naming and repository structure

- **Exemplar repo**: `deepagents-tutor-exemplar` at `/Users/richardwoollcott/Projects/appmilla_github/deepagents-tutor-exemplar` — or, more pragmatically, **let `study-tutor` itself be the exemplar**. The hackathon submission is already public; there is no reason to maintain a separate private exemplar that shadows it. Post-hackathon, extract the template from the study-tutor repo directly.
- **Template name (when extracted)**: `langchain-deepagents-tutor` — sibling to `langchain-deepagents`, `langchain-deepagents-weighted-evaluation`, `langchain-deepagents-orchestrator`.
- **Extension relationship**: `extends: langchain-deepagents-weighted-evaluation` (inherits the weighted Player-Coach, adds interactive session + student model + MCP + Graphiti + Ollama runtime).

### A.8 When to cut the template

Not before the hackathon. The specialist-agent story is the cautionary tale: cutting a template from unproven patterns bakes in the mistakes. The workflow is:

1. **Pre-hackathon (Phase 0–2):** Build Study Tutor directly, referencing the specialist-agent and dataset-factory source code for patterns. Copy code into study-tutor when useful, don't try to abstract prematurely.
2. **Hackathon submission (Phase 3):** Ship the working exemplar as the submission.
3. **Post-hackathon (late May / early June):** Run `/template-create` in the study-tutor repo with `--validate`. Cut `langchain-deepagents-tutor` into `installer/core/templates/` (or `installer/local/templates/` initially for private team use).
4. **Round-2 lessons doc:** Update `cross-agent-lessons-from-specialist-agent.md` (or write `LES2`) with anything new that surfaced during the Study Tutor build — the prompt calls for another lessons-learned pass.

### A.9 Implications for Phase 0 scope

This decision changes the Phase 0 scope doc in concrete ways:

- **Do not** start with `guardkit init langchain-deepagents-weighted-evaluation`. The template misses too much; it would generate structure we then have to fight.
- **Do** scaffold `study-tutor` manually, using the specialist-agent and dataset-factory directory structures as the reference shape. The GuardKit workflow (`/system-arch`, `/system-design`, `/system-plan`, `/feature-spec`, etc.) applies regardless of whether a template was used to bootstrap.
- **Do** copy `AGENTS.md`, `.mcp.json` scaffolding, `pyproject.toml` extras pattern, and the `roles/` directory layout directly from specialist-agent on day one.
- **Do** include "template-extraction-readiness" as a non-functional requirement in the Phase 0 scope. Naming conventions, placeholder hygiene (`{{ProjectName}}`, `{{Namespace}}`), boundary sections (ALWAYS/NEVER/ASK) should be structural from the first commit, not retrofitted.

### A.10 Follow-on work identified

Two pieces of follow-on work fall out of this analysis, neither blocking Phase 0:

1. **Round-2 lessons doc (LES2)** — the prompt explicitly asks for another update. Most of this can be captured during and after the Study Tutor build. Recommend writing LES2 in the same style as LES1 at the end of Phase 1, folding in any new parity surfaces discovered (likely candidates: Ollama provider resolution, Graphiti student-model schema drift, session-lifecycle timeout handling).
2. **Template cut decision log** — before cutting `langchain-deepagents-tutor`, document decisions about what stays in the template vs what stays study-tutor-specific. GCSE English curriculum references stay in study-tutor; the interactive session shape + gamification state machine + Graphiti student-model pattern go into the template.

---

*Appendix A related documents:*
- https://guardkit.ai/templates/ — template store index
- https://guardkit.ai/guides/creating-local-templates/ — local template workflow
- https://guardkit.ai/guides/template-philosophy/ — why templates are learning resources
- `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/templates/langchain-deepagents*/manifest.json` — shipped template manifests
- `/Users/richardwoollcott/Projects/appmilla_github/deepagents-player-coach-exemplar/` — the source exemplar for the weighted-evaluation template
- `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/` — post-TASK-REV-B8E4 production patterns
- `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/` — batch data generation pipeline
