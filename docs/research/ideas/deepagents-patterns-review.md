# DeepAgents Patterns Review: Applicability to Study Tutor

**Date:** 12 April 2026
**Author:** Rich Woollcott
**Repo:** study-tutor
**Context:** Assessing which existing DeepAgents templates and patterns apply to the Study Tutor Phase 2 architecture (custom DeepAgents harness with Graphiti)

---

## 1. Existing Patterns and Templates

The GuardKit ecosystem has produced several proven DeepAgents patterns through the agentic-dataset-factory and architect-agent work. These patterns are documented, tested, and in some cases templated.

### 1.1 Player-Coach Adversarial Loop

**Source:** `deepagents-player-coach-exemplar` → `langchain-deepagents` template
**Current use:** Agentic dataset factory (training data generation)

**Pattern:**
- Two separate `create_deep_agent()` instances with different system prompts
- Player generates, Coach validates with structured JSON rejection schema
- Coach has `tools=[]` — evaluates only, never writes
- Configurable Coach model via `coach-config.yaml` (local vLLM or API)
- Turn limit before discard
- AGENTS.md boundaries (ALWAYS/NEVER/ASK per agent)

**Applicability to Study Tutor:** HIGH — but in a different role.

In the dataset factory, Player-Coach generates training data. In the Study Tutor, the same pattern can serve two functions:

1. **Tutoring quality gate** — a Coach agent monitors the Tutor agent's responses in real-time, checking for curriculum accuracy, assessment objective alignment, grade-appropriate language, and pedagogical soundness. The Coach doesn't interact with the student — it's a background quality monitor.

2. **Session planning** — a Player agent proposes a session plan based on the Graphiti student model (weakest topics, streak status, daily challenges available), and a Coach agent validates it against pedagogical principles before the session begins.

### 1.2 Domain-Agnostic Config (`GOAL.md` + `sources/`)

**Source:** agentic-dataset-factory architecture
**Current use:** Dataset generation domains

**Pattern:**
- `domains/{name}/GOAL.md` — goal, source docs, generation guidelines, evaluation criteria, output schema, layer routing
- `domains/{name}/sources/` — input PDFs processed by Docling
- No code changes to add a new domain — config-only

**Applicability to Study Tutor:** DIRECT — same pattern, different purpose.

Each GCSE subject becomes a domain:
```
domains/
├── gcse-english/
│   ├── GOAL.md          ← tutoring behaviour for English
│   └── sources/         ← curriculum materials (user-provided)
├── gcse-maths/
│   ├── GOAL.md          ← tutoring behaviour for Maths
│   └── sources/
├── gcse-french/
│   ├── GOAL.md
│   └── sources/
```

The GOAL.md for the tutor would define:
- Subject-specific tutoring style (Maths is more procedural; English is more analytical)
- Assessment objectives for that subject
- Question types to practice
- Common misconceptions to address
- Grade boundary guidance

### 1.3 Two-Layer Architecture (Behaviour + Knowledge)

**Source:** Architectural principle from Daniel Bourke / Queensland AI Meetup
**Current use:** Agentic dataset factory output routing

**Pattern:**
- `train.jsonl` (behaviour layer) → fine-tuning via Unsloth → teaches HOW the model responds
- `knowledge.jsonl` (knowledge layer) → ChromaDB RAG → provides WHAT the model draws from
- `layer` field in metadata drives routing
- Independently updatable: retrain behaviour without changing knowledge, or update knowledge without retraining

**Applicability to Study Tutor:** FOUNDATIONAL — this is the core architecture.

The Study Tutor extends this with a third layer:
- **Layer 1: Fine-tuned behaviour** — tutoring style, Socratic questioning, AO alignment (Gemma 4 31B Dense LoRA)
- **Layer 2: RAG knowledge** — curriculum content, mark schemes, example answers (ChromaDB)
- **Layer 3: Student model** — individual student's progress, topic confidence, misconceptions, gamification state (Graphiti)

The three-layer model was already described in the Architect Agent design. The Study Tutor is its first consumer.

### 1.4 Structured Uncertainty Handling

**Source:** `structured-uncertainty-handling.md` research doc
**Current use:** AutoBuild pipeline (assumptions as first-class citizens)

**Pattern:**
- Player declares assumptions before implementation
- Confidence levels: high / medium / low
- Graphiti coverage scoring gates decisions
- Dead man's switch: default state is "paused pending confirmation"
- Approved assumptions feed back into Graphiti

**Applicability to Study Tutor:** MEDIUM — adapted for pedagogical confidence.

The tutor agent needs to handle uncertainty about the student's understanding. When the student gives an ambiguous answer, the tutor should:
- Explicitly assess confidence in its understanding of the student's level
- If low confidence: ask a clarifying question rather than assuming
- If medium confidence: offer a scaffolded response that tests the assumption
- If high confidence: proceed with targeted teaching

This maps to the structured uncertainty pattern: make the tutor's pedagogical assumptions explicit rather than relying on the model's implicit assessment.

### 1.5 Research-to-Implementation Handoff Template

**Source:** `research-to-implementation-template.md`
**Current use:** All feature specs across GuardKit repos

**Pattern:**
- Phase 1 (Claude Desktop, extended thinking) makes all decisions
- Phase 2 (local LLM, AutoBuild) executes without choosing
- Decision Log → ADRs → Graphiti seeding
- Warnings & Constraints as high-priority Graphiti nodes
- Task breakdown with exact acceptance criteria

**Applicability to Study Tutor:** DIRECT — use this template for every Study Tutor feature.

The Study Tutor's Phase 2 features (DeepAgents harness, Graphiti integration, gamification engine) should each be specified using this template before implementation begins. The template ensures that the GB10's local model never has to make architectural decisions during build.

### 1.6 AgentManifest Pattern (from nats-core)

**Source:** `nats-core` design session
**Current use:** Fleet agent registration

**Pattern:**
- Single Pydantic model as source of truth for agent capabilities
- Derives both MCP tool definitions and NATS fleet registration from same schema
- Zero refactoring when transport changes

**Applicability to Study Tutor:** HIGH — the tutor agent needs a manifest.

The Study Tutor agent will be a member of the Ship's Computer fleet. Its AgentManifest would declare:
- Capabilities: tutoring, quiz generation, essay feedback, progress reporting
- Subjects: English (initially), Maths, French, Spanish (planned)
- Interfaces: CLI, Open WebUI (Phase 1), custom DeepAgents harness (Phase 2), Reachy Mini voice (future)
- Dependencies: vLLM, ChromaDB, Graphiti

This means the tutor is discoverable and orchestratable by the Jarvis intent router from day one.

---

## 2. New Patterns Needed for the Study Tutor

### 2.1 Gamification State Machine

No existing pattern covers persistent gamification. The tutor needs:

- **State storage in Graphiti** — XP, level, streak, achievement progress, topic confidence
- **Event-driven state transitions** — session completion triggers XP award, streak check, achievement evaluation, level-up check
- **Query patterns** — "what achievements is the student close to?", "what's the recommended next session?", "what's the current streak?"

This is a new pattern that could be extracted as a reusable template for any gamified agent.

### 2.2 Session Orchestration Agent

The dataset factory's Player-Coach is a batch process — it generates training data overnight. The tutor's agent harness is interactive — it responds to student input in real-time.

New pattern needed:
- **Session lifecycle** — start session → select topic (from Graphiti recommendations or student choice) → interactive tutoring loop → session summary → gamification update → Graphiti persistence
- **Turn-level reasoning** — each student message triggers: RAG retrieval → model inference → response quality check → gamification event check
- **Adaptive difficulty** — Graphiti topic confidence scores adjust question difficulty and scaffolding level within a session

### 2.3 Multi-Interface Agent

The tutor will be accessed through multiple interfaces simultaneously:
- Open WebUI (text chat, Phase 1)
- Custom web UI with gamification dashboard (Phase 2)
- Reachy Mini voice interface (future)
- Parent reporting interface (future)

The AgentManifest pattern handles capability declaration, but the runtime needs an interface adapter layer that the current fleet architecture doesn't explicitly cover.

---

## 3. Recommended Architecture for Phase 2

Based on the pattern review, the Study Tutor's DeepAgents harness should be structured as:

```
study-tutor/
├── src/
│   ├── agents/
│   │   ├── tutor_agent.py          ← main tutoring agent (from Player-Coach pattern)
│   │   ├── session_planner.py      ← plans sessions from Graphiti state
│   │   └── quality_monitor.py      ← background Coach for response quality
│   │
│   ├── gamification/
│   │   ├── engine.py               ← XP, levels, achievements, streaks
│   │   ├── models.py               ← Pydantic models (from January design)
│   │   └── graphiti_store.py       ← Graphiti persistence for game state
│   │
│   ├── knowledge/
│   │   ├── rag_retrieval.py        ← ChromaDB retrieval (from dataset factory)
│   │   └── student_model.py        ← Graphiti queries for student state
│   │
│   ├── interfaces/
│   │   ├── cli.py                  ← Terminal interface
│   │   ├── api.py                  ← REST/WebSocket for web UI
│   │   └── reachy_adapter.py       ← Reachy Mini voice interface (future)
│   │
│   ├── config/
│   │   ├── agent_manifest.py       ← AgentManifest (from nats-core pattern)
│   │   └── tutor_config.yaml       ← Model, deployment, subject config
│   │
│   └── domains/                    ← Domain configs (from dataset factory pattern)
│       ├── gcse-english/
│       │   └── GOAL.md
│       ├── gcse-maths/
│       │   └── GOAL.md
│       └── ...
│
├── docs/
│   ├── research/
│   │   └── ideas/                  ← Research docs (this file lives here)
│   └── adr/                        ← Architecture Decision Records
│
├── tests/
├── pyproject.toml
├── AGENTS.md                       ← ALWAYS/NEVER/ASK boundaries
└── README.md
```

### Key Reuse Points

| Component | Reused From | Adaptation Needed |
|-----------|-------------|-------------------|
| Agent creation pattern | `deepagents-player-coach-exemplar` | Interactive not batch; single-turn not multi-turn generation |
| GOAL.md domain config | `agentic-dataset-factory` | Tutoring behaviour spec, not training data spec |
| RAG retrieval tool | `agentic-dataset-factory/tools/rag_retrieval.py` | Same ChromaDB pattern; different collection per subject |
| Coach quality check | `agentic-dataset-factory/agents/coach.py` | Background monitor, not turn-based reviewer |
| Agent manifest | `nats-core` | Tutor-specific capabilities declared |
| Feature spec template | `research-to-implementation-template.md` | Direct reuse for all Phase 2 features |
| Uncertainty handling | `structured-uncertainty-handling.md` | Adapted for pedagogical confidence |

---

## 4. What to Build First

For the hackathon submission (18 May deadline), the priority is demonstrating the architecture, not building everything. Recommended order:

1. **Gamification Pydantic models** — clean up from January session, commit to repo (1 day)
2. **GOAL.md for English** — write the tutoring behaviour specification using only freely referenceable curriculum info (1 day)
3. **Session orchestration skeleton** — DeepAgents harness that wraps vLLM inference with session lifecycle (2-3 days)
4. **Graphiti student model** — basic entity types for topic confidence and session history (2-3 days)
5. **Dashboard mockup** — React artifact showing gamification UI (1 day)

Items 1-2 are needed regardless. Items 3-5 are Phase 2 stretch goals — valuable for the submission but not required if time is tight with DDD prep.

---

*Prepared: 12 April 2026*
*For: study-tutor/docs/research/ideas/*
