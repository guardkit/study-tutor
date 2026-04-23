# Phase 1 Scope — Three-Layer Architecture + Student Model

## For: Claude Code `/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan` → AutoBuild
## Date: 17 April 2026 (last updated 23 April 2026)
## Status: Ready to consume — execute starting Saturday 26 April (weekend 2 of the 31-day burn)
## Predecessor: `phase-0-scope.md`, `phase-0-build-plan.md` (Phase 0 completes Friday 24 April), `rag-grounding-design.md`, `openwebui-rag-empirical-findings-2026-04-23.md`
## Successor: `phase-2-scope.md` (sketch exists; build plan written Phase 1 Thursday 30 April per hybrid cadence)
## Context: The load-bearing phase. Turns the Phase 0 MCP-accessible tutor into a genuinely three-layer adaptive system: fine-tuned behaviour (Layer 1, already in Phase 0) + curriculum RAG (Layer 2, now with source-typed grounding — see FEAT-PH1-004) + Graphiti student model (Layer 3, newly built) + DeepAgents tutoring loop with Player-Coach quality monitor orchestrating all three.

---

## Post-empirical update — 2026-04-23

An interim OpenWebUI + RAG deployment was stood up for Lilymay on 23 Apr to support immediate GCSE revision while Phase 1 is built. The session produced ten empirical findings (captured in [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md)) and six R-numbered recommendations that this scope doc now absorbs:

- **R1 (source-typed quote verifier), R2 (dynamic retrieval decision), R3 (AO3 retrieval-bypass), R4 (Standard Ebooks over Gutenberg)** → now captured as new feature **FEAT-PH1-004** below.
- **R5 (runtime-param smoke assertion)** → new structural requirement **SR-09** below.
- **R6 (AO-labelled exemplars in next fine-tune)** → noted in "Future fine-tune inputs" at the bottom; not a Phase 1 deliverable.

Headline finding informing the Phase 1 architecture: *for primary texts the fine-tune has memorised (Shakespeare), direct Ollama beats RAG; retrieval must be selective, source-typed, and primary-text-inclusive to add value. Always-on retrieval against a secondary-sources-only corpus actively degrades quality.*

This means Phase 1's curriculum RAG layer (Layer 2) is not a "retrieve-everything" layer; it is a *selective, source-aware* layer that the tutoring loop consults conditionally.

---

## Motivation

Phase 0 produces an MCP-accessible tutor that talks to the fine-tuned Gemma 4 model through a single LLM call per turn. It's submittable-standalone, but it doesn't demonstrate the three-layer architecture that makes Study Tutor an intelligent tutoring *system* rather than a chat box behind a system prompt.

Phase 1 is where the architecture becomes real. Three layers operating together, with a live Coach evaluating pedagogical quality in the background, and a persistent student model that remembers what Lilymay studied last week and adapts this session to it. This is the primary judging criterion for the hackathon's "engagement + personalisation" dimension — the thing that separates Study Tutor from any other Gemma 4 fine-tune wrapped in a chat UI.

Phase 1 is also where the decisions log's open measurements get resolved. DEC-02 (Graphiti topology across Synology + Gemini + GB10) and DEC-08 (Gemini entity-extraction latency posture) both require end-to-end latency measurement before the MCP tool shapes from Phase 0 can be confirmed. The Graphiti spike on Saturday morning is therefore the single most important first-task of the phase — everything downstream depends on what it measures.

Phase 1 explicitly does NOT include gamification, dashboard, or Reachy. Those are Phase 2 and the gated stretch phase respectively. Phase 1's discipline is to make the three-layer architecture work end-to-end on a single learner's session; Phase 2 layers retention mechanics on top; the stretch phase adds embodiment.

---

## Scope: Three Features + Continuing Structural Requirements

The seven structural requirements from Phase 0 (SR-01 through SR-07) remain load-bearing. Every Phase 1 feature maintains them. The Graphiti latency spike adds one new structural consideration — **SR-08: Graphiti write-back is asynchronous from the caller's perspective** — which is notionally deferred work but is decided early in Phase 1 based on measurement.

### SR-08: Graphiti write-back asynchrony

**Requirement.** Graphiti episode creation and entity updates are fire-and-forget from the tutor's `tutor_session_end` handler. The caller receives a success acknowledgement as soon as the session is marked complete; Graphiti write completion happens on a background task that can fail independently without affecting the session outcome.

**Evidence from LES1 §4 + DEC-02 + DEC-08.** Three-hop Graphiti write path (MacBook → Synology FalkorDB + MacBook → Gemini entity extraction + MacBook → GB10 embeddings) is load-bearing latency. If any hop is slow, synchronous write-back blocks the tutor's response-critical path. Async write-back is the LES1-compliant shape.

**Acceptance.** `tutor_session_end` returns within 2 seconds regardless of Graphiti write latency. Graphiti write failures are logged but do not surface to the MCP caller. Subsequent `tutor_start_session` calls tolerate a not-yet-written previous session by treating it as absent rather than erroring.

**Coupling to the spike.** If the Saturday morning spike shows end-to-end Graphiti write latency under 2 seconds consistently, SR-08 is still the right shape (defensive) but the "real" impact is small. If latency exceeds 5 seconds, SR-08 is load-bearing and shapes every feature.

### SR-09: Runtime LLM parameters are explicit and asserted

**Requirement.** Every Ollama Modelfile used by the tutor must set explicit `num_ctx` (≥16384 for RAG-enabled personas) and `num_predict` (≥1500 for tutoring responses). The smoke-test suite must assert both values match expectation via `ollama show <model> --modelfile | grep PARAMETER` and via the runner log line `llama_new_context_with_model: n_ctx = N` observed during a real inference call.

**Evidence from [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](./openwebui-rag-empirical-findings-2026-04-23.md).** Ollama's default `num_ctx=2048` silently truncates tutoring responses mid-sentence when RAG is active — no error surfaces, just a chopped reply. The model loaded from a Modelfile with the wrong default, and OpenWebUI's Advanced Params can also override at request time.

**Acceptance.** A task-level smoke test (post-Modelfile-change) runs `ollama show` + parses log output to confirm `num_ctx` and `num_predict` reach the runner at expected values. Any regression trips the test.

---

### FEAT-PH1-001: Graphiti Student Model

**Problem.** Phase 0's `tutor_turn` has no memory. Every turn is a stateless LLM call. The tutor can't know that Lilymay struggled with metaphor identification last Tuesday, that her Macbeth topic confidence is at 62%, or that she has a 9-day streak. Without persistent student state, the whole personalisation story is absent.

Graphiti is the chosen persistence layer per DEC-02: FalkorDB on the Synology NAS, Gemini for entity extraction, nomic-embed-text-v1.5 on GB10 port 8001 for embeddings. MacBook runs the tutor and talks to all three over Tailscale.

**Changes required.**

#### 1. Latency spike (Saturday morning deliverable)

Before any schema work, measure the three-hop latency end-to-end. This resolves DEC-02 / DEC-08 ambiguity and locks SR-08 + the Phase 0 MCP tool classification.

Specifically:
- Time a single `add_episode` call from the MacBook against FalkorDB on Synology with Gemini entity extraction and GB10 embeddings. Expected range: 1–3s if Gemini is fast, 5–8s if not.
- Time a `search_nodes` query by group_id with a topic-confidence filter. Expected range: 0.5–2s.
- Time a `search_memory_facts` query. Expected range: 0.5–2s.
- Run each three times, record min/median/max.

Output: `docs/research/ideas/graphiti-latency-spike-results.md`. Two paragraphs max plus the measurements table.

Decisions the spike unblocks:
- If add_episode median > 5s: SR-08 async write-back is critical, possibly fire-and-forget from multiple points not just session-end
- If search_nodes median > 3s: `tutor_start_session` stays long-running (Phase 0 classification holds)
- If search_nodes median < 1s: `tutor_start_session` could be reclassified as sync, simplifying the MCP tool shape

The spike is also a forcing function for confirming every Graphiti dependency works (graphiti-core installed, FalkorDB reachable over Tailscale, Gemini API key configured, embedder responsive).

#### 2. Student model schema

Define the Pydantic entity types that represent Lilymay's learning state. Reused pattern from specialist-agent's Graphiti integration (per-role group IDs, episode types, relationship semantics) but with education-specific entities not documented elsewhere.

**Entities:**

| Entity | Identifies | Key attributes |
|---|---|---|
| `Student` | A single learner | `name`, `year_group`, `exam_specification` (e.g. "AQA-8700"), `target_grade` |
| `Subject` | GCSE subject | `name` ("English Language", "English Literature"), `specification_code` |
| `Text` | A specific literary text | `title`, `author`, `subject`, `period` ("Shakespeare", "19th century novel", etc.) |
| `Topic` | A revisable unit within a subject or text | `name`, `parent_subject_or_text`, `aqa_reference` (AO mapping where applicable) |
| `AssessmentObjective` | AO1–AO6 | `code`, `description`, `subject` (Language vs Literature use different weightings) |
| `Misconception` | A documented misunderstanding | `description`, `topic`, `seen_count`, `last_seen` |
| `TopicConfidence` | Per-student, per-topic confidence level | `student`, `topic`, `confidence_band` (struggling/developing/secure/mastered), `percentage`, `last_updated` |

**Relationships:**

| Source | Relationship | Target | Semantics |
|---|---|---|---|
| `Student` | STUDIES | `Subject` | Lilymay's enrolled subjects |
| `Student` | WORKING_ON | `Text` | Currently revising |
| `Student` | HAS_CONFIDENCE | `TopicConfidence` | Per-topic mastery state |
| `Student` | HAS_SHOWN | `Misconception` | Misconceptions observed in past sessions |
| `Topic` | TESTS | `AssessmentObjective` | Which AOs this topic contributes to |
| `Topic` | BELONGS_TO` | `Subject` or `Text` | Topic hierarchy |

**Group IDs:**

- `student:lilymay` — student-specific episodes and entities
- `subject:gcse-english` — curriculum-level (not per-student)
- `fleet:appmilla` — cross-product/cross-role knowledge (rare writes from the tutor)

**Episode types** (matching specialist-agent's episode vocabulary):

- `session_completed` — logged at `tutor_session_end`. Payload: turns taken, topics covered, AOs exercised, XP awarded (Phase 2 will consume this), misconceptions surfaced, session summary.
- `topic_confidence_updated` — logged when a Topic's confidence changes. Payload: old band, new band, triggering session.
- `misconception_observed` — logged when the Coach identifies a misconception in a Player response. Payload: description, topic, AO.

#### 3. Graphiti seeding

Initial population of the student model with Lilymay's known state. Done via a one-off seeding script, not via the tutor. Target: realistic baseline from which the first Phase 1 tutoring session continues naturally rather than starting from zero.

Seeding sources:
- Lilymay's current Macbeth progress (approximate — human estimate, refined over subsequent sessions)
- Her current streak (from existing Ollama-based usage, if logged; otherwise start at 0)
- Her target grade (from Rich's knowledge)
- The subject and text list for AQA 8700 / 8702 Year 10

Seeding script: `scripts/seed_student_model.py`. Read by `tutor_start_session` is read-only; seeding is a separate concern.

#### 4. Graphiti query helpers

Thin Python wrappers around Graphiti's search_nodes / search_memory_facts / add_episode patterns, specialised for this schema. Per the specialist-agent pattern (`src/specialist_agent/tools/graphiti_query.py`) use lazy import so the module loads even when graphiti-core isn't installed (graceful degradation per LES1 §3 `.env` hygiene concerns).

Required helpers:
- `get_student_state(student_id) -> StudentState` — aggregates the student entity plus all TopicConfidence, recent Misconceptions, current streak info, most recent session episode
- `get_topic_recommendations(student_id, count=3) -> list[Topic]` — used by the session planner; prioritises weak or recently-missed topics, respects per-topic revisit cooldowns
- `record_session_completion(student_id, session_summary)` — async write-back per SR-08

**Dependencies:** FEAT-PO-001 (Phase 0 domain contract) — the GOAL.md's AO table and topic names are the source of truth for what entities and relationships exist in Graphiti. Phase 1 schema must be consistent with Phase 0 domain documents; no drift.

---

### FEAT-PH1-002: Session Planner

**Problem.** Phase 0's `tutor_start_session` takes a topic from the caller's arguments — it's externally-chosen. The whole adaptive-tutoring story requires the tutor to propose topics based on student state. Without a planner, Graphiti persistence is data that doesn't influence behaviour.

**Changes required.**

#### 1. Planner agent or deterministic function?

Two plausible shapes. First: an LLM-backed planner agent that reads student state and reasons about what to study next. Second: a deterministic rules-based planner that ranks topics by weakness and recency.

**Phase 1 decision: deterministic first, upgradeable later.** The planner logic in `deepagents-patterns-review.md §2.2` is clearly rules-based ("weakest topics, recent sessions, streak opportunities, available challenge types"). A deterministic planner is cheaper to test, faster to run, produces explainable decisions, and doesn't add a third LLM to the critical path (tutor + Coach already make two). If Phase 2 gamification demands probabilistic topic variety, the deterministic planner is the scoring function that a stochastic sampler wraps.

**Planner inputs:** student_id, optional student-provided topic override.

**Planner outputs:** a `SessionPlan` object with `topic`, `suggested_duration_minutes`, `focus_aos` (list of AssessmentObjective codes to exercise), `related_misconceptions` (list to watch for), `opening_prompt` (a seed question or task the tutor starts with).

**Planner logic (ranked):**
1. If student provided a topic override, use it. Skip ranking.
2. Active quest or daily challenge matching an available topic (Phase 2 — not in Phase 1)
3. Topic with lowest TopicConfidence percentage, not revised in the last 48 hours
4. Topic where a recent Misconception was recorded, not yet revisited
5. Text or topic that unlocks a near-unlockable achievement (Phase 2 — not in Phase 1)
6. Random selection from `developing` confidence band

In Phase 1, rules 1, 3, 4 are implemented. Rules 2 and 5 are explicitly stubbed with a `# TODO(phase-2)` comment.

#### 2. Planner integration with `tutor_start_session`

The MCP handler `_start_tutor_session` calls the planner after session_id generation, before returning. The returned session_id carries the plan; subsequent `tutor_turn` calls reference the plan's opening_prompt and focus_aos.

Session state (still in-memory for Phase 1, per Phase 0 — persistence beyond Graphiti episode write-back is Phase 2 work if needed):

```python
class TutorSession:
    session_id: str
    student_id: str
    plan: SessionPlan
    turns: list[TutorTurn]
    started_at: datetime
    status: Literal["active", "completed", "cancelled"]
```

**Dependencies:** FEAT-PH1-001 (Graphiti helpers). The planner calls `get_student_state` and `get_topic_recommendations`.

---

### FEAT-PH1-003: DeepAgents Tutoring Loop with Coach Quality Monitor

**Problem.** Phase 0's `tutor_turn` is a single LLM call. No quality gate. The Coach pattern from agentic-dataset-factory (Player-Coach with `tools=[]` on Coach, configurable rubric, structured JSON rejection schema) is exactly what separates curriculum-accurate tutoring from confident-but-wrong tutoring. Phase 1 introduces it.

This is the load-bearing feature of the whole build. If FEAT-PH1-003 isn't working by 10 May, the submission demos Phase 0 + Graphiti-only. That's credible but weaker than the full story.

**Changes required.**

#### 1. Tutoring as a Player-Coach loop

The Player is the fine-tuned Gemma 4 31B tutor. It generates the response to the student's turn, grounded in the session plan's focus AOs and the session transcript so far.

The Coach is a separate agent (different provider recommended — Gemini 2.5 Pro if Gemini latency is acceptable per DEC-08, otherwise OpenAI gpt-5.4). It evaluates the Player's proposed response against the rubric established in Phase 0 FEAT-PO-001 item 3 (Coach criteria skeleton).

**Coach rubric (scored 0.0–1.0 per criterion, weighted):**

| Criterion | Weight | What it checks |
|---|---|---|
| `curriculum_accuracy` | 0.25 | Claims match GCSE AQA Literature / Language content and the text in question |
| `ao_alignment` | 0.25 | Response exercises the focus_aos named in the session plan |
| `scaffolding_depth` | 0.20 | Response uses Socratic questioning / guided discovery rather than telling |
| `grade_appropriate_language` | 0.15 | Vocabulary and sentence complexity suitable for a Year 10 target grade student |
| `constructive_feedback` | 0.15 | When responding to a student answer, response names what to improve and how |

Acceptance threshold: 0.7 weighted score. Below threshold triggers Player revision (max 3 attempts, then surface lowest-scoring reply with a silent log marker).

#### 2. Coach ≠ second tutor

Explicit constraint from FEAT-PO-006 roadmap: *"Coach must remain evaluative and not become a second student-facing tutor."* Coach output is never shown to the student. Coach reasoning is logged for session-end review.

#### 3. Latency budget

Hard constraint: tutor_turn p95 < 30 seconds end-to-end, measured from MCP call to response emission. Breakdown:

- Player response generation: target 8–15 seconds (fine-tuned 31B model on Ollama, Q4_K_M quantisation)
- Coach evaluation: target 3–7 seconds (Gemini 2.5 Pro)
- Worst-case revision loop (1 rejection + 1 re-generation): doubles Player time, target <30 seconds total still

If Phase 1 measurement shows the loop consistently exceeds 30 seconds, the fallback is accept-first-revise-later: surface the Player's first response immediately, run the Coach asynchronously, log concerns for session-end review without blocking the turn. This fallback is acceptable for demo purposes but ideologically weaker than real-time quality gating.

#### 4. Coach-observed misconceptions write to Graphiti

When Coach rejects a turn for `curriculum_accuracy < 0.5` or identifies a misconception in a student answer that the Player addressed, record a `misconception_observed` episode per FEAT-PH1-001 item 2. Async per SR-08.

This is how the student model gets richer over time without requiring explicit misconception tagging by the Player.

#### 5. Session-end summary generation

On `tutor_session_end`, generate a short summary episode recording:
- Topics covered (from session plan + turn-level topic tags)
- AOs exercised (from Coach evaluations of each turn)
- Turns taken and duration
- Any misconceptions surfaced
- A two-sentence narrative summary for future context (e.g. "Lilymay worked through the witches' role in Macbeth Act 1. Strong AO2 analysis but confused about dramatic irony definition.")

Written to Graphiti as a `session_completed` episode, asynchronously per SR-08.

**Dependencies:** FEAT-PH1-001 (Graphiti helpers for write-back + misconception recording), FEAT-PH1-002 (session plan provides focus_aos and opening_prompt), FEAT-PH1-004 (quote verifier is a Coach rubric criterion).

---

### FEAT-PH1-004: Primary-Text RAG + Source-Typed Quote Verification

**Problem.** The interim OpenWebUI deployment (23 Apr) surfaced a subtle failure mode: when the RAG corpus contains only secondary material (study guides, critical essays), a strict "only quote verbatim from context" rule *suppresses* the model's own verbatim primary-text knowledge and forces paraphrase. The tutor degrades below the no-RAG baseline. Phase 1's curriculum RAG layer must be source-typed and selective to avoid this.

This feature operationalises R1–R4 from [openwebui-rag-empirical-findings-2026-04-23.md §4](./openwebui-rag-empirical-findings-2026-04-23.md).

**Changes required.**

#### 1. Source-typed corpus ingestion

Every chunk in the corpus carries a `source_type` metadata label: one of `primary_text` (the play or novel itself), `secondary_study_guide` (Mr Bruff, CGP, York Notes, etc.), `secondary_critical` (essays, academic commentary), `context_historical` (Jacobean, Edwardian, Victorian context material — optional, see R3 below). Ingestion pipeline (reused from the Phase 0 BYOS README and `agentic-dataset-factory`) is extended with a source-type classifier or explicit per-directory labelling.

Corpus layout (file-system-first):

```
domains/gcse-english/sources/
├── primary_text/
│   ├── macbeth_shakespeare_1606.txt      (Standard Ebooks)
│   ├── christmas_carol_dickens_1843.txt  (Standard Ebooks)
│   └── jekyll_hyde_stevenson_1886.txt    (Standard Ebooks)
├── secondary_study_guide/
│   ├── mr_bruff_macbeth.pdf
│   └── cgp_inspector_calls.pdf
├── secondary_critical/
└── context_historical/
    └── jacobean_james_i_witchcraft.md    (curated, optional)
```

Public-domain primary texts use Standard Ebooks as the canonical source (R4 — cleaner than Gutenberg, no project boilerplate, canonical line numbering). In-copyright modern texts (An Inspector Calls, Blood Brothers, DNA) remain out of the corpus per the rag-grounding-design §1a Analysis-Mode-Only policy, with the Phase 2 per-student Graphiti `Text` episode as the future path for user-licensed copies.

#### 2. Dynamic retrieval decision (R2)

Before each `tutor_turn`, the tutoring loop asks: *"For this query, does the corpus contain primary-text evidence relevant to the student's current `Text` (from the session plan)?"* Decision logic:

- If yes → retrieve (source_type filter: `primary_text` first, then `secondary_*` as supplement), ground the response, pass chunks through to the Coach rubric's quote verifier.
- If no → skip retrieval entirely, let Player answer from training knowledge, flag session metadata `retrieval_skipped: true` with reason.

This means retrieval is NOT always-on. An unrevised Shakespeare session with the primary text in the corpus → retrieves. An unrevised An Inspector Calls session (in-copyright, no primary text) → does not retrieve, uses Analysis Mode instead.

#### 3. AO3 retrieval-bypass (R3)

AO3 (context — Jacobean/Victorian/Edwardian history, not themes) is explicitly a training-data-first category. The planner tags whether a turn is addressing AO3 (from the session plan's `focus_aos`); if so, retrieval either uses the optional `context_historical` sub-corpus OR skips entirely and relies on model training. AO3 never retrieves against `primary_text` or `secondary_study_guide` — those are AO1/AO2 evidence categories.

#### 4. Source-typed quote verifier (R1) — integrates with Coach

Coach's rubric (FEAT-PH1-003) gains a new criterion: `quote_fidelity`. For every quoted string in the Player's response:

- If the quote appears verbatim in a `primary_text` corpus chunk → annotate with attribution (*"Macbeth 5.1.35"* from Standard Ebooks line numbering), score pass.
- If the quote appears verbatim ONLY in a `secondary_*` chunk and is presented as if it were the primary author's words → strip the quotation marks, rewrite as paraphrase with *"as one critic observes"* or similar, log a `secondary_source_laundering` event.
- If the quote does not appear in any corpus chunk (fabricated or training-recalled without verification) → for primary texts we attempt fuzzy match (≤3 edit distance) and correct; for in-copyright texts the verifier strips and paraphrases per rag-grounding-design §1a.

This is the Phase A plan from [rag-grounding-design.md](./rag-grounding-design.md), extended with the source-type distinction that today's empirical work proved necessary.

#### 5. Deliverables

- `src/study_tutor/knowledge/corpus.py` — chunk metadata types, source-type enum, corpus loader with per-directory source-type inference
- `src/study_tutor/knowledge/retrieval.py` — dynamic retrieval decision + source-filtered search
- `src/study_tutor/knowledge/quote_verifier.py` — corpus-matcher with primary/secondary distinction (invoked by Coach)
- `domains/gcse-english/sources/README.md` — updated BYOS instructions with the source-type directory structure (replaces the Phase 0 tail item)
- Unit tests for each of the three modules; an integration test that exercises the full retrieval-decision + quote-verification flow end-to-end.

**Dependencies:** FEAT-PH1-001 (student model's `Text` entity tells the retrieval decision which primary text to target), FEAT-PH1-002 (planner's `focus_aos` tells the retrieval decision whether AO3 is active). **FEAT-PH1-003 depends on this**: the Coach's `quote_fidelity` rubric criterion calls into the quote verifier.

**Out of scope (Phase 2 or later):**

- User-supplied in-copyright texts cached in a per-student Graphiti `Text` episode (rag-grounding-design §1a posture 2)
- Embedding-based pre-generation grounding (rag-grounding-design Phase B) — Phase 1 stays post-hoc-verification-only
- Reranker tuning beyond the `BAAI/bge-reranker-v2-m3` baseline proven in the 23 Apr session

---

## Do-Not-Change

These decisions are closed for Phase 1. Reopenable only per `decisions-log-2026-04-17.md §Revision policy`.

- **The six parity surfaces from LES1 remain load-bearing.** SR-01 through SR-07 apply to every Phase 1 change. New code can not regress them.
- **Graphiti topology per DEC-02** — FalkorDB on Synology, Gemini for entity extraction, GB10 for embeddings. No alternative hosting evaluated in Phase 1.
- **Graphiti write-back is always async from the caller's perspective** — SR-08. Even if the spike shows low latency.
- **Planner is deterministic, not LLM-backed.** LLM-backed planner is a Phase 2 consideration if gamification demands probabilistic variety.
- **Coach uses a different provider than Player.** Two-provider separation is an explicit invariant from agentic-dataset-factory. Both on Gemma 4 via Ollama is not acceptable even if cheaper.
- **No gamification state in Phase 1.** XP numbers from `docs/gamification/design.md` are documented but not emitted from Phase 1 code. `session_completed` episodes include turn count and topic data; Phase 2 gamification engine reads them.
- **No Reachy integration in Phase 1.** Stretch phase, separate conversation starter, 4 May gate.
- **In-memory session state only for Phase 1.** If a session_id spans an MCP server restart it's lost. Persistent session state is a Phase 2 consideration if UX requires it.
- **Single student.** Lilymay is the only student_id in Phase 1. Multi-student is post-hackathon even though the schema supports it.
- **Bedrock from Phase 0 remains the demo-week inference backup.** Phase 1 doesn't rebuild the Bedrock import; it only extends the LLM client with per-provider dispatch (which was done in Phase 0 FEAT-PO-004).
- **Retrieval is selective, not always-on.** The dynamic retrieval decision (FEAT-PH1-004 item 2) is not optional — every `tutor_turn` passes through it. Always-on retrieval is explicitly rejected based on 23 Apr empirical findings.
- **In-copyright primary texts are not in the corpus.** Analysis Mode Only per rag-grounding-design §1a. No workarounds (no DRM-ripped Kindle, no unauthorised Scribd/archive.org copies). Phase 2 per-student Text episodes are the only future legitimate path.
- **Quote verification is post-hoc, not pre-generation.** Phase B embedded-context grounding is explicitly deferred. Phase 1 ships only the post-hoc verifier (Phase A MVP shape).

---

## Success Criteria

Phase 1 is complete when all of the following are true:

1. **Graphiti latency spike published.** `docs/research/ideas/graphiti-latency-spike-results.md` exists, contains real measurements from the Saturday morning spike, and informs the tool classification decisions.

2. **Student model populated for Lilymay.** Seeding script run; `get_student_state("lilymay")` returns a realistic baseline matching current known state (topic confidence for Macbeth, streak count, target grade).

3. **Session planner produces explainable plans.** `get_topic_recommendations("lilymay", count=3)` returns three topics with a brief rationale per topic (lowest confidence; recent misconception; etc.). Human review confirms the ranking matches intuition for a few test cases.

4. **Player-Coach tutoring loop runs end-to-end.** A full session (start → 5+ turns → end) completes with Coach evaluations recorded for each turn. At least one rejection-and-regeneration observed in testing. p95 turn latency under 30 seconds.

5. **Session completion writes to Graphiti.** A completed session produces a `session_completed` episode with topic coverage, AO list, turn count, and a narrative summary. Subsequent sessions for the same student benefit from the prior context.

6. **The demo flow works end-to-end.** From Open WebUI or Claude Desktop: start a session → have 3–5 turns with the tutor → end the session → start a new session → observe the planner recommending a different topic informed by the first session's state change.

7. **Six parity surfaces still green.** SR-01 through SR-07 pass their acceptance criteria against Phase 1 code.

8. **Technical write-up has content, not stubs.** `docs/submission/technical-writeup.md` now has real paragraphs in the three-layer architecture section, the Graphiti student model section, and the Player-Coach loop section.

9. **Phase 2 build plan drafted.** Thursday evening work produces `phase-2-build-plan.md` based on what Phase 1 measured and shipped. Pre-weekend-3 setup complete.

10. **Phase 1 validation gate run for Phase 0.** `phase-0-validation.md` produced early in Phase 1 reviewing what held, what drifted, what was falsified in the Phase 0 plan. Per the hybrid cadence approach doc.

11. **Source-typed corpus ingested.** `domains/gcse-english/sources/` has the four-way source-type directory structure; at least Macbeth (primary) and one study guide (secondary) populated. Ingestion produces chunk metadata with `source_type` set correctly.

12. **Quote verifier operational in Coach loop.** A demo session shows (a) a primary-text quote correctly attributed with act/scene, (b) a secondary-source phrase correctly rewritten as paraphrase with *"as one critic notes"*-style attribution, (c) a fabricated quote correctly stripped. Logged events visible in session summary.

13. **Dynamic retrieval decision observable.** At least one session where the planner targets Shakespeare triggers retrieval; at least one where the planner targets An Inspector Calls (in-copyright) skips retrieval and logs `retrieval_skipped: analysis_mode`.

14. **SR-09 smoke assertion passes.** `ollama show` and runner log grep both confirm `num_ctx` and `num_predict` reach the runner at Modelfile-declared values. Regression test added to CI (or manual walkthrough if CI absent in Phase 1).

---

## Knock-on to Phase 2

Phase 2 scope (separate doc) depends on outcomes from Phase 1. Key Phase-2-shaping questions the build is expected to answer:

- **Claude Design output quality for the dashboard.** Can the frontend-design skill produce submission-quality static HTML when given a session-export JSON? If yes, FEAT-PO-009 is a 1-day task; if no, Phase 2 needs a different dashboard approach.
- **Graphiti write latency in practice.** Affects whether gamification state engine reads live or polls with a cache.
- **Coach evaluation quality.** Phase 2 gamification triggers attach to Coach output (topic mastery changes, AO coverage patterns). If Coach is unreliable, gamification rules attach to simpler session-metric signals instead.
- **Session-export JSON shape.** Phase 1 must define this (it's the handoff format for dashboard and gamification). Phase 2 scope references it; Phase 2 build plan depends on it being fixed.

---

## Relationship to the roadmap

The Phase 1 features map to the existing 13-feature roadmap in `docs/product/roadmap/roadmap.md`:

| Phase 1 feature | Roadmap feature | Notes |
|---|---|---|
| FEAT-PH1-001 Graphiti Student Model | FEAT-PO-004 roadmap | Same scope, Phase 1 ships it |
| FEAT-PH1-002 Session Planner | FEAT-PO-005 roadmap | Same scope, deterministic-first per scope-doc decision |
| FEAT-PH1-003 DeepAgents Tutoring Loop + Coach | FEAT-PO-006 roadmap | Same scope, with latency-budget constraint added from LES1 |
| FEAT-PH1-004 Primary-Text RAG + Source-Typed Quote Verification | TASK-PO02F-001 promoted (new roadmap row) | Operationalises rag-grounding-design Phase A + 23 Apr empirical R1–R4 |

Three Phase 0 features that continue to live through Phase 1 without changes: FEAT-PO-001 (domain contract), FEAT-PO-002 (MCP transport), FEAT-PO-004 (Bedrock path). Phase 1 extends each minimally (domain contract gets AO-level detail used by Coach; MCP gets fire-and-forget properly implemented; Bedrock remains as backup).

---

## Future fine-tune inputs (not a Phase 1 deliverable)

Captured from 23 Apr findings (R6) for when the next fine-tune round is scheduled:

- **AO-labelled exemplars.** AO mis-labelling (especially theme-as-AO3) is a pretraining/fine-tune gap, not a prompt-engineering problem. Current Modelfile SYSTEM block patches it at runtime; future fine-tune datasets should include AO-correctly-labelled responses so the behaviour is baked in. Likely dataset source: AQA specimen papers and mark schemes, where AO attribution is explicit.
- **Verbatim quote attribution exemplars.** Fine-tune exemplars that pair primary-text quotes with act/scene citations would reinforce the attribution habit the Coach currently enforces post-hoc.
- **Socratic-close exemplars.** Already present in the current fine-tune and working well; preserve on retrain.

---

*Phase 1 scope: 17 April 2026 (last updated 23 April 2026 with 23 Apr empirical findings)*
*Consuming: `phase-0-scope.md`, `decisions-log-2026-04-17.md`, `planning-cadence-hybrid-approach.md`, `deepagents-patterns-review.md`, `cross-agent-lessons-from-specialist-agent.md`, `rag-grounding-design.md`, `openwebui-rag-empirical-findings-2026-04-23.md`*
*Produced alongside: `phase-1-build-plan.md` (day-by-day for 26 April – 2 May)*
*Successor: `phase-2-scope.md` (sketch, build plan deferred to Phase 1 Thursday)*
