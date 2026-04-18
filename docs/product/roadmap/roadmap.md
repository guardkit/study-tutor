# ideas -- Product Roadmap

## Mode

idea

## Epics

### EPIC-001: Hackathon-Ready English Tutor Core

**Bounded Context:** Tutoring Behaviour BC

Establish the minimum credible product for the 18 May 2026 hackathon: a working GCSE English tutor for Lilymay that demonstrates specialised tutoring behaviour, safe curriculum boundaries, and a public-repo-friendly packaging strategy. This epic turns the existing basic Ollama deployment into a clearly productised English tutoring experience with explicit subject configuration and demonstrable educational value.

**Features:**
  - FEAT-PO-001: GCSE English domain configuration and tutoring contract
  - FEAT-PO-002: Fine-tuned English tutoring runtime over local deployment
  - FEAT-PO-003: Bring-your-own-sources public repo packaging

### EPIC-002: Adaptive Session Orchestration and Student Memory

**Bounded Context:** Student Model BC

Introduce the DeepAgents + Graphiti architecture that makes the tutor adaptive rather than stateless. This epic captures persistent knowledge about Lilymay's progress, drives better session selection, and creates the foundation for gamification and later multi-subject expansion.

**Features:**
  - FEAT-PO-004: Graphiti student profile and topic confidence model
  - FEAT-PO-005: Session planner using Graphiti recommendations
  - FEAT-PO-006: DeepAgents tutoring loop with quality monitor

### EPIC-003: Single-User Gamification Engine

**Bounded Context:** Gamification BC

Create the engagement layer that makes a teenager return voluntarily, using personal progress rather than classroom competition. This epic adds persistent XP, levels, streaks, achievements, and challenge logic powered by Graphiti and surfaced through a dashboard and future companion interfaces.

**Features:**
  - FEAT-PO-007: Gamification state model and event engine
  - FEAT-PO-008: Adaptive challenge and boss battle generation
  - FEAT-PO-009: Student progress dashboard and achievement surfacing

### EPIC-004: Multi-Subject Expansion Foundation

**Bounded Context:** Subject Domain BC

Prepare the architecture so English is the first subject, not the last. This epic formalises the reusable subject-domain pattern and the agent capability manifest needed to extend into Maths, French, and Spanish without rewriting the system.

**Features:**
  - FEAT-PO-010: Subject-domain template for additional GCSE subjects
  - FEAT-PO-011: Tutor AgentManifest and multi-interface capability declaration

### EPIC-005: Hackathon Submission Assets and Evidence

**Bounded Context:** Submission Delivery BC

Turn the product and roadmap into a compelling hackathon submission with clear evidence, narrative, and demo assets. This epic ensures the work is judged as a complete system—working tutor plus principled roadmap—rather than as a loose collection of technical experiments.

**Features:**
  - FEAT-PO-012: Hackathon demo narrative and evidence capture
  - FEAT-PO-013: Technical write-up with provenance and architecture decisions

## Priority Rationale

The roadmap starts with the English tutor core because the user already has a real student using a basic version and the hackathon deadline makes packaging existing strengths more valuable than broad new implementation. Next comes Graphiti-backed adaptation because the student model is the enabling dependency for meaningful personalisation and for the gamification engine to react to real progress. Gamification follows once persistent state exists, since XP, streaks, achievements, and boss battles are most compelling when tied to actual tutoring outcomes rather than bolted on superficially. Multi-subject work is deliberately sequenced after the English-first product foundation so the architecture proves config-led expansion without diluting the immediate hackathon story. Submission assets come last in dependency terms, but they should be developed in parallel once the core packaging, demo path, and minimal dashboard evidence are stable.

## Constraints and Dependencies

- Hackathon submission deadline is 18 May 2026, so roadmap ordering favours packaging and demonstrable value over ambitious breadth.
- English is the first production subject because Lilymay is already using a basic version for AQA English Language and Literature.
- AQA assessment materials must not be used in training or publicly redistributed; only factual curriculum references such as assessment objectives are assumed acceptable.
- Public repository must exclude copyrighted/private assets including Mr Bruff PDFs, ChromaDB collections, train.jsonl, and fine-tuned weights.
- Current runtime path is Ollama-based and working; vLLM and custom DeepAgents harness are target-state dependencies, not preconditions for hackathon entry.
- Graphiti student model is a prerequisite for robust session planning, adaptive gamification, and meaningful progress recommendations.
- Gamification state engine depends on persisted student state to avoid shallow reward mechanics.
- Multi-subject expansion depends on stable subject-domain templates and manifest-driven capability declaration.

## Open Questions

- Whether the final hackathon rules behind Kaggle login impose any additional provenance or model-distribution requirements that would force the cleaner fallback training option.
- How much of the DeepAgents + Graphiti architecture must be fully implemented versus shown as a high-fidelity roadmap for the submission to remain credible.
- Whether the student-facing dashboard for hackathon purposes should be a functional thin slice over real state or a mockup connected to partial real data.
- Whether Reachy Mini is in scope for the hackathon demo as a vision segment only, or as part of the implemented interface strategy.

## Feature Spec Inputs

### FEAT-PO-001: GCSE English domain configuration and tutoring contract

**Bounded Context:** Tutoring Behaviour BC

**Description:**
Create a `domains/gcse-english/GOAL.md` that defines the tutor's behavioural contract for AQA English Language and Literature using factual curriculum structure, assessment objectives, grade-appropriate scaffolding, and Socratic questioning patterns. The specification must describe how the tutor handles essay feedback, quotation analysis, exam technique coaching, and uncertainty about a student's understanding so that generated feature specs can produce concrete acceptance scenarios.

**Source Documents:** deepagents-patterns-review.md, copyright-training-data-analysis.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must avoid use of AQA assessment materials in training or public assets
  - Must support AQA English Language and Literature framing for Lilymay's current use case
  - Must be specific enough to drive future subject configs without code changes

**Suggested Context Files:** domains/gcse-english/GOAL.md, src/domains/gcse-english/, docs/adr/

### FEAT-PO-002: Fine-tuned English tutoring runtime over local deployment

**Bounded Context:** Tutoring Runtime BC

**Description:**
Wrap the existing Gemma 4 31B fine-tuned tutoring behaviour in a stable local runtime that Lilymay can use consistently through the current Ollama-based path while preserving the option to migrate to vLLM later. The runtime must support key GCSE English interactions such as asking analytical questions, receiving scaffolded essay feedback, and practising exam responses in language appropriate for a Year 10 student.

**Source Documents:** gemma4-hackathon-submission-plan.md, copyright-training-data-analysis.md

**Constraints:**
  - Must remain on-device/offline-friendly
  - Must use existing private model assets without publishing weights
  - Must work with the current basic version already used via Ollama

**Suggested Context Files:** src/runtime/, src/interfaces/cli.py, src/interfaces/api.py, README.md

**Depends On:** FEAT-PO-001

### FEAT-PO-003: Bring-your-own-sources public repo packaging

**Bounded Context:** Submission Packaging BC

**Description:**
Package the tutor as an open-source methodology rather than an open-source dataset by separating clean pipeline code from private curriculum materials, ChromaDB collections, training data, and fine-tuned weights. The repository must explain how a user can supply licensed study materials into the ingestion pipeline, while making it explicit which assets stay private for copyright and hackathon compliance reasons.

**Source Documents:** copyright-training-data-analysis.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must not publish Mr Bruff PDFs, AQA materials, train.jsonl, ChromaDB collections, or private adapters
  - Must support hackathon requirement for a public repository
  - Must document provenance and compliance posture transparently

**Suggested Context Files:** README.md, domains/gcse-english/sources/README.md, docs/adr/, LICENSE

**Depends On:** FEAT-PO-001

### FEAT-PO-004: Graphiti student profile and topic confidence model

**Bounded Context:** Student Model BC

**Description:**
Model the student in Graphiti as persistent entities and relationships covering subject, text, topic, assessment objective, misconception, session history, confidence level, and recent activity. The model must remember what Lilymay studied previously, which English topics are secure or weak, and which misconceptions need revisiting so later tutoring turns can adapt to her actual revision history rather than starting from scratch.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must support English first but be extensible to Maths, French, and Spanish
  - Must represent topic confidence and misconception tracking explicitly
  - Must persist enough state to drive recommendations and gamification

**Suggested Context Files:** src/knowledge/student_model.py, src/gamification/graphiti_store.py, docs/adr/

**Depends On:** FEAT-PO-001, FEAT-PO-002

### FEAT-PO-005: Session planner using Graphiti recommendations

**Bounded Context:** Session Orchestration BC

**Description:**
Build a session planning component that proposes the next revision activity from the student model, taking into account weakest topics, recent sessions, streak opportunities, and available challenge types. The planner must turn Graphiti state into a concrete English revision plan such as quotation practice, essay planning, AO2 language analysis, or literature theme revision before the tutoring conversation begins.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must work for both tutor-suggested and student-chosen sessions
  - Must be grounded in persisted student state, not random topic selection
  - Must support future gamification triggers

**Suggested Context Files:** src/agents/session_planner.py, src/knowledge/student_model.py, src/config/tutor_config.yaml

**Depends On:** FEAT-PO-004

### FEAT-PO-006: DeepAgents tutoring loop with quality monitor

**Bounded Context:** Session Orchestration BC

**Description:**
Implement an interactive tutoring harness where the tutor generates a response, a background Coach evaluates pedagogical quality, and the system can refine or flag low-quality guidance before it reaches the student or before it is stored as a successful turn. The loop must enforce behaviours already established in the Player-Coach pattern—curriculum accuracy, AO alignment, grade-appropriate language, and scaffold-first teaching—while operating in a live session rather than a batch dataset factory.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Coach must remain evaluative and not become a second student-facing tutor
  - Must be compatible with current local serving path and later vLLM migration
  - Must not introduce latency that makes sessions unusable for a teenager

**Suggested Context Files:** src/agents/tutor_agent.py, src/agents/quality_monitor.py, src/knowledge/rag_retrieval.py

**Depends On:** FEAT-PO-002, FEAT-PO-004, FEAT-PO-005

### FEAT-PO-007: Gamification state model and event engine

**Bounded Context:** Gamification BC

**Description:**
Define Pydantic models and domain logic for XP, levels, streaks, achievements, quests, daily challenges, and boss battles, then wire those state transitions to tutoring events such as session completion, quote usage, topic mastery gains, and timed practice. The engine must behave like a deterministic rules layer over the student model so the product can consistently award progress and unlocks instead of relying on ad hoc LLM judgement.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must be designed for a single learner, not leaderboards
  - Must persist state in Graphiti or a Graphiti-backed store
  - Must be clean enough to include in the public repo

**Suggested Context Files:** src/gamification/models.py, src/gamification/engine.py, src/gamification/graphiti_store.py

**Depends On:** FEAT-PO-004

### FEAT-PO-008: Adaptive challenge and boss battle generation

**Bounded Context:** Gamification BC

**Description:**
Generate daily challenges and exam-style boss battles from the student's current revision state so that the engagement loop reinforces real learning rather than superficial clicking. Challenges must be tied to English behaviours the tutor can observe—such as quotation embedding, AO2 analysis, or reviewing yesterday's mistakes—and boss battles must feel like high-stakes exam practice unlocked through progression.

**Source Documents:** gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must align rewards to authentic learning tasks
  - Must use topic mastery and prior performance to choose challenge content
  - Must support a hackathon-demo-friendly subset even if full implementation is deferred

**Suggested Context Files:** src/gamification/engine.py, src/agents/session_planner.py, src/knowledge/student_model.py

**Depends On:** FEAT-PO-005, FEAT-PO-007

### FEAT-PO-009: Student progress dashboard and achievement surfacing

**Bounded Context:** Gamification UI BC

**Description:**
Provide a student-facing dashboard that shows XP, current level, streak status, topic mastery, active challenges, and near-unlocked achievements in a way a teenager can understand at a glance. The dashboard must connect tutoring outcomes to visible progress so that a Macbeth session or quotation drill immediately feels like movement toward named goals such as 'Quote Champion' or 'Macbeth Master'.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must visualise personal growth rather than competition
  - Must be suitable for hackathon demo video and screenshots
  - Can begin as a mockup or thin UI over real state if time is limited

**Suggested Context Files:** src/interfaces/api.py, web/, docs/mockups/, README.md

**Depends On:** FEAT-PO-007, FEAT-PO-008

### FEAT-PO-010: Subject-domain template for additional GCSE subjects

**Bounded Context:** Subject Domain BC

**Description:**
Create a reusable subject package pattern where each GCSE subject provides its own `GOAL.md`, source-material conventions, pedagogical style, and assessment-objective mapping while sharing the same tutoring harness. The template must make it straightforward to add Maths, French, or Spanish as configuration-led extensions, while preserving the fact that English is more analytical and other subjects may require very different tutoring behaviours.

**Source Documents:** deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must require minimal or no core code changes for a new subject
  - Must separate subject pedagogy from runtime orchestration
  - Must support future subject-specific source acquisition rules

**Suggested Context Files:** src/domains/, domains/gcse-maths/GOAL.md, domains/gcse-french/GOAL.md, domains/gcse-spanish/GOAL.md

**Depends On:** FEAT-PO-001

### FEAT-PO-011: Tutor AgentManifest and multi-interface capability declaration

**Bounded Context:** Agent Capability BC

**Description:**
Define a single manifest for the tutor agent that declares supported subjects, interfaces, dependencies, and capabilities such as tutoring, quiz generation, essay feedback, and progress reporting. This gives the product a stable contract for Open WebUI today, custom web UI next, and future voice or fleet integration later without refactoring the tutor's identity each time transport or interface changes.

**Source Documents:** deepagents-patterns-review.md

**Constraints:**
  - Must be the source of truth for capability exposure
  - Must cover English immediately and planned subjects explicitly
  - Must support future custom web UI and Reachy/voice adapters

**Suggested Context Files:** src/config/agent_manifest.py, src/config/tutor_config.yaml, docs/adr/

**Depends On:** FEAT-PO-002, FEAT-PO-010

### FEAT-PO-012: Hackathon demo narrative and evidence capture

**Bounded Context:** Submission Delivery BC

**Description:**
Build a repeatable demo flow that shows the current working English tutor, on-device deployment, a real revision interaction, and the future-facing adaptive and gamified architecture in a coherent story. The demo must capture both practical proof—Lilymay or a stand-in using the tutor—and product vision, including how Graphiti memory and gamification change the student's experience over time.

**Source Documents:** gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must be achievable before 18 May 2026
  - Must avoid showing prohibited copyrighted source materials
  - Must work even if Phase 2 is partly mockup rather than fully implemented

**Suggested Context Files:** docs/submission/demo-script.md, docs/submission/video-outline.md, README.md

**Depends On:** FEAT-PO-002, FEAT-PO-003, FEAT-PO-009

### FEAT-PO-013: Technical write-up with provenance and architecture decisions

**Bounded Context:** Submission Delivery BC

**Description:**
Produce a technical write-up that explains the two-layer and three-layer architecture, agentic dataset generation, Graphiti student modelling, gamification design, local deployment, and the public/private asset boundary. The write-up must document why the repo is open while source materials, ChromaDB data, training data, and model weights remain private, and it must present the roadmap as an intentional product strategy rather than unfinished work.

**Source Documents:** copyright-training-data-analysis.md, deepagents-patterns-review.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must be transparent about copyright and provenance posture
  - Must align with hackathon judging criteria and repo contents
  - Must explain Phase 1 working state and Phase 2 roadmap without over-claiming implementation

**Suggested Context Files:** docs/submission/technical-writeup.md, README.md, docs/adr/

**Depends On:** FEAT-PO-003, FEAT-PO-011, FEAT-PO-012

## Source Documents

| Document | Contribution |
| --- | --- |
| copyright-training-data-analysis.md | Provided the compliance and provenance constraints that shape the public/private asset boundary, especially the need to avoid AQA assessment materials and keep source PDFs, training data, vector stores, and weights private. It also grounded the 'bring your own sources' packaging strategy and the hackathon-safe use of the existing private model. |
| deepagents-patterns-review.md | Provided the strongest architectural grounding for bounded contexts, including the Player-Coach quality gate, subject-domain GOAL.md pattern, Graphiti student model, gamification state machine, session orchestration, and AgentManifest approach. It directly informed the dependency structure across tutoring, orchestration, gamification, and multi-interface expansion. |
| gemma4-hackathon-submission-plan.md | Provided the product vision, hackathon framing, real user context, Phase 1 vs Phase 2 roadmap, gamification mechanics, and demo/submission deliverables. It grounded the ordering toward an English-first, hackathon-ready tutor with Graphiti and gamification as the differentiating system layers. |

## Assumptions

| # | Category | Assumption | Confidence | Impact if Wrong |
| --- | --- | --- | --- | --- |
| ASM-001 | scope | The immediate submission scope should focus on English as the only fully supported subject, with multi-subject support demonstrated through architecture and templates rather than fully trained subject models. | high | Attempting to fully implement multiple subjects before the deadline would likely reduce quality of the English tutor and weaken the hackathon submission. |
| ASM-002 | technology | The existing Ollama-based deployment is sufficient as the working runtime for the hackathon, even if the long-term architecture targets vLLM plus a custom DeepAgents harness. | high | If Ollama cannot support a credible demo, additional runtime engineering would become critical-path work and compress time available for packaging and evidence capture. |
| ASM-003 | integration | Graphiti can serve as the persistence layer for both adaptive tutoring state and gamification state without introducing an architectural split before the hackathon. | medium | A second persistence mechanism would need to be introduced, increasing complexity and delaying session planning and gamification features. |
| ASM-004 | constraints | AQA assessment objectives and curriculum structure can be referenced in GOAL.md and public documentation as factual curriculum information, while AQA assessment materials themselves remain excluded from training and public artefacts. | medium | The English domain configuration and public documentation would need to be rewritten to avoid even curriculum-structure references, weakening specificity and subject alignment. |
| ASM-005 | team | The most realistic path before 18 May 2026 is to package and evidence existing work plus a thin slice of Phase 2, rather than completing the full adaptive gamified system. | high | If a fuller Phase 2 build is unexpectedly required, the roadmap would understate implementation effort and create schedule risk near submission. |
| ASM-006 | constraints | The hackathon rules will allow a public repository containing the methodology while keeping training data, source materials, vector stores, and private model weights undistributed. | medium | If the rules require broader asset distribution or stricter provenance disclosure, a fallback clean training run and altered repo strategy may be needed. |
