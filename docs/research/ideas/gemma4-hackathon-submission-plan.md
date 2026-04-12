# Gemma 4 Good Hackathon — Submission Plan

**Competition:** The Gemma 4 Good Hackathon (Kaggle × Google DeepMind)
**Track:** Future of Education
**Prize Pool:** $200,000 USD
**Deadline:** 18 May 2026, 23:59 UTC
**Start Date:** 2 April 2026

---

## 1. Project Title (Working)

**"GCSE Study Tutor: A Fine-Tuned, On-Device AI Tutor for UK Secondary Education"**

Alternatives:
- "Scholar: Personalised GCSE Revision with Gemma 4 on Consumer Hardware"
- "Scholar: Gamified, Adaptive GCSE Tutoring with Fine-Tuned Gemma 4 — Entirely On-Device"

---

## 2. The Pitch

A fine-tuned Gemma 4 31B Dense model that acts as a personalised GCSE tutor, running entirely on-device on a Dell DGX Spark (GB10). The system combines:

- **Fine-tuned behaviour** (via Unsloth) — the model knows *how* to tutor: Socratic questioning, AQA assessment objective alignment, grade-appropriate scaffolding, `<think>` reasoning blocks
- **RAG knowledge** (via ChromaDB) — the model draws from *what* it needs: AQA specifications, past papers, mark schemes, examiner reports, and curated study guides
- **Agentic dataset generation** — training data is produced by a Player-Coach adversarial loop (LangChain DeepAgents), not hand-crafted
- **Gamification engine** — XP, levels, achievements, streaks, daily challenges, and Boss Battle exam mode designed to keep a teenager coming back. Built for a single user, not a classroom — personal growth replaces leaderboards
- **Adaptive student model** (via Graphiti) — persistent knowledge graph tracks topic confidence, misconceptions, session history, and achievement progress across sessions. The tutor remembers what was covered last week and what needs work

The tutor is being built for a real student (Year 10, Robert Blake School, Bridgwater) studying real exams (AQA English Language 8700, English Literature 8702), with multi-subject expansion planned (Maths, French, Spanish).

**Why this matters for the hackathon:** This isn't a chatbot with a system prompt. It's a complete pipeline — from curriculum PDFs to fine-tuned model to gamified, adaptive on-device deployment — that could be replicated for any exam board, any subject, any country. The model runs locally, the student's data never leaves the house, and the entire methodology (not the data) is open-source. The gamification layer addresses the real problem: not whether AI *can* tutor, but whether a teenager will actually *use* it.

---

## 3. Strategic Alignment to Judging Criteria

| Criterion | How We Score |
|-----------|-------------|
| **Real-world impact** | Built for a real student, real exams, real curriculum. Not hypothetical. Lilymay uses it for actual GCSE revision. |
| **Technical execution** | Fine-tuned Gemma 4 31B Dense (not prompted). Unsloth + TRL SFTTrainer. Player-Coach adversarial data generation. Two-layer architecture (behaviour + knowledge). Graphiti-backed adaptive student model. |
| **Gemma 4 usage** | The model IS Gemma 4. Fine-tuned, not wrapped. Demonstrates what the 31B Dense can do when properly specialised. |
| **Working prototype** | Running on GB10 today via Ollama + Open WebUI. Lilymay can use it over Tailscale. |
| **Offline / privacy** | Entirely on-device. No cloud. No data exfiltration. Family home network only. |
| **Student engagement** | Full gamification engine: XP, 15 named levels, 6 achievement categories, daily challenges, Boss Battle exam mode, Reachy Mini as AI companion. Designed for a single user — personal growth, not competition. |
| **Unsloth special mention** | Unsloth is the fine-tuning framework. First run completed: ~1,736 examples, ~2h 5min, final loss 0.7015. |
| **Ollama special mention** | Ollama is the deployment runtime. GGUF export (Q4_K_M) already produced. |

---

## 4. Architecture: Two Phases, One Story

### Phase 1: Pragmatic Deployment (NOW — what Lilymay uses today)

```
AQA PDFs ──► Docling ──► ChromaDB (knowledge layer)
                              │
GOAL.md ──► Player-Coach ──► train.jsonl (behaviour layer)
                              │
                        Unsloth fine-tune
                              │
                        Gemma 4 31B Dense LoRA
                              │
                        GGUF export (Q4_K_M)
                              │
                        Ollama + Open WebUI
                              │
                        Lilymay (via Tailscale)
```

**Purpose:** Get a working tutor into Lilymay's hands quickly. Feedback loop drives dataset improvements. Open WebUI provides a familiar chat interface. This is the "it works today" story.

### Phase 2: Principled Architecture (TARGET — what the submission demonstrates)

```
AQA PDFs ──► Docling ──► ChromaDB (knowledge layer)
                              │
GOAL.md ──► Player-Coach ──► train.jsonl (behaviour layer)
                              │
                        Unsloth fine-tune
                              │
                        Gemma 4 31B Dense LoRA
                              │
                        vLLM (on GB10)
                              │
                   Custom DeepAgents Harness
                     │         │          │
              Graphiti KG   ChromaDB   Gamification
              (student       RAG        Engine
               model)     (curriculum)  (XP, levels,
                     │         │        achievements)
                     └────┬────┘            │
                    Tutor Agent ◄────────────┘
                     (orchestrated)
                          │
                    Student Interface
                    (+ Reachy Mini "Scholar")
```

**What Phase 2 adds:**

- **Graphiti knowledge graph** — builds a persistent student model: topic confidence scores, misconceptions encountered, assessment objectives needing work, session history, streak data, XP totals, and achievement progress. This is the "adaptive" in adaptive tutoring. Everything the gamification engine needs to make decisions persists here.
- **Gamification engine** — orchestrated by the DeepAgents harness, powered by Graphiti state:
  - **XP system** — sessions, challenges, and achievements all award XP
  - **15-level progression** — Beginner → Novice → Apprentice → Student → Learner → Scholar → Academic → Intellectual → Expert → Master → Sage → Virtuoso → Luminary → Prodigy → Grandmaster. Each level unlocks features (daily challenges at Level 2, exam questions at Level 6, Boss Battle at Level 8, Teaching Mode at Level 10)
  - **6 achievement categories** — Consistency (streaks), Mastery (topic coverage), Growth (improvement over time), Exploration (breadth), Challenge (timed/hard tasks), Milestone (XP thresholds)
  - **Named achievements** — "Quote Champion" (10 embedded quotations), "Macbeth Master" (80% confidence), "Fortnight Force" (14-day streak), "Poetry Pioneer" (Power & Conflict coverage), "Exam Ready" (Boss Battle completion)
  - **Daily challenges** — rotating mini-goals: complete a session (+50 XP), practice quotation analysis (+30 XP), review yesterday's mistakes (+40 XP)
  - **Boss Battle mode** — timed, exam-style challenges framed as "final boss" encounters. Tests everything learned under exam conditions. 1,000 XP + Exam Ready trophy
  - **Topic mastery dashboard** — visual confidence bars per text/topic with colour-coded status (Struggling → Developing → Secure → Mastered)
- **Custom DeepAgents harness** — the tutor becomes an agent, not just an inference endpoint. It can plan revision sessions, retrieve targeted practice questions, adjust difficulty based on the student model, reason about pedagogical strategy, and drive the gamification logic (which quest to offer next, when to suggest a Boss Battle, which near-unlockable achievement to highlight).
- **vLLM inference** — proper serving with batching, rather than Ollama's simpler runtime. Enables the agent harness to make structured calls.
- **Reachy Mini "Scholar"** — embodied interface (physical robot with expressive eyes, head tracking, voice). Acts as the gamification companion: verbally reports progress, reacts to achievements, suggests targeted sessions. Addresses the single-user isolation problem by creating an AI companion that responds to the student's progress.

**The single-user gamification insight:** Traditional gamification (Duolingo-style) relies on social pressure — leaderboards, friends' streaks, competitive pressure. With a single user, those mechanics fall flat. The design principle here is that gamification for a solo learner must focus on personal growth: beating your past self, unlocking achievements, building streaks, and having an AI companion (Reachy) that reacts to your progress. This can be as motivating as leaderboards — arguably more so, because the progress is always meaningful to you personally.

**Why both phases matter for the submission:** Phase 1 proves the pipeline works end-to-end and the model is already in use. Phase 2 shows architectural ambition — not just a fine-tuned model behind a chat box, but a genuine intelligent tutoring system with adaptive behaviour and engagement mechanics designed to solve the real problem: will a teenager actually use it?

---

## 5. Gamification Design: The Engagement Layer

*Source: Ideation session 30 January 2026 ([conversation link](https://claude.ai/chat/d9b1df40-7fba-471e-884b-905f40593cd1)). Previously extracted to `GCSE_Gamification_Research.docx` on 17 March 2026.*

### 5.1 The Core Problem

AI tutors fail not because they can't answer questions, but because teenagers don't open them. Traditional revision guides gather dust. Duolingo-style gamification works because of social pressure — leaderboards, friends' streaks, competitive urgency. With a single user at home, those social mechanics fall flat.

**Design principle:** Gamification for a solo learner focuses on personal growth, not competition. Beating your past self, building streaks, unlocking achievements, and having an AI companion that reacts to your progress.

### 5.2 Mechanics Summary

| Mechanic | Description | Persistence |
|----------|-------------|-------------|
| **XP** | Awarded per session, challenge, and achievement. Session XP scales with difficulty and performance. | Graphiti entity |
| **Levels (15)** | Beginner → Grandmaster. Named titles provide identity. Each level unlocks features (daily challenges, exam questions, Boss Battle, Teaching Mode). | Graphiti entity |
| **Streaks** | Consecutive study days tracked. Longest streak recorded. Streak-based achievements at 3, 7, 14, 30 days. | Graphiti entity |
| **Achievements (6 categories)** | Consistency, Mastery, Growth, Exploration, Challenge, Milestone. Named examples: "Quote Champion", "Macbeth Master", "Fortnight Force", "Poetry Pioneer", "Exam Ready". | Graphiti entities |
| **Daily Challenges** | Rotating mini-goals: complete a session (+50 XP), practise quotation analysis (+30 XP), review yesterday's mistakes (+40 XP). | Graphiti episode |
| **Quests** | Weekly goals with expiry timers. E.g. "Complete 2 sessions on Power & Conflict Poetry" — 3-day timer, 500 XP + Poetry Pioneer badge. | Graphiti entity |
| **Boss Battle** | Timed exam-style challenges. Unlocked at Level 8. Framed as "final boss" — tests everything under exam conditions. 1,000 XP + Exam Ready trophy. | Graphiti episode |
| **Topic Mastery** | Confidence bars per text/topic (Struggling → Developing → Secure → Mastered). Drives adaptive session recommendations. | Graphiti entity |

### 5.3 Reachy Mini as Gamification Companion

The Reachy Mini robot "Scholar" is the social workaround for single-user isolation. Rather than a static dashboard, Reachy:

- **Reports progress verbally** — "You're on a 12-day streak, your longest yet!"
- **Highlights near-unlockable achievements** — "You need just 2 more days for Fortnight Force"
- **Suggests targeted sessions** — "You're at 76% on Macbeth — one more session could push you to Macbeth Master"
- **Celebrates milestones** — level-ups, achievement unlocks, streak records
- **Provides parent visibility** — Rich can ask "How's Lilymay's revision going?" and Reachy reports naturally

This creates a social-feeling dimension without requiring other users. The companion reacts to *your* progress, which makes it meaningful.

### 5.4 Why This Matters for the Hackathon

Most education-track submissions will demonstrate that an AI model can answer curriculum questions. That's table stakes. The gamification layer answers the harder question: **how do you get a 15-year-old to voluntarily open a revision tool on a Tuesday evening?**

The combination of fine-tuned tutoring behaviour + adaptive Graphiti student model + gamification engagement + embodied Reachy companion is genuinely novel. It's an intelligent tutoring *system*, not a chatbot with a system prompt.

### 5.5 What's Needed for the Submission

| Element | Status | Effort for Submission |
|---------|--------|----------------------|
| Gamification design document | ✅ Complete (`GCSE_Gamification_Research.docx`) | Include in technical write-up |
| Python data models (Pydantic) | ✅ Sketched in January session | Clean up for repo |
| Graphiti integration | 🔶 Phase 2 | Describe in architecture section of write-up |
| Dashboard UI mockups | ✅ ASCII art from January session | Convert to proper mockup for video/write-up |
| Reachy interaction scripts | ✅ Scenario scripts written | Include in demo video as vision segment |
| Working gamification engine | 🔶 Phase 2 | Not required for submission — design + architecture is the contribution |

**Key point:** The gamification *design* is complete and compelling. The *implementation* is Phase 2. For the hackathon submission, the design document and architecture diagrams carry the weight. If time allows, a simple dashboard mockup (React artifact or static HTML) showing the XP/level/achievement UI would be powerful visual material for the video.

---

## 6. Submission Deliverables Mapped to Existing Assets

### 6.1 Working Demo ✅ (Required)

**What exists today:**
- Fine-tuned Gemma 4 31B Dense running via Ollama on GB10
- ~1,736 training examples from first production run
- GGUF Q4_K_M export ready
- Accessible over Tailscale

**What needs to happen:**
- [ ] Record a screen capture of Lilymay (or Rich acting as student) using the tutor for real GCSE revision
- [ ] Show the tutor handling multiple question types: essay feedback, quote analysis, Socratic questioning, exam technique
- [ ] Demonstrate the offline/on-device nature (show it running on the GB10, no cloud calls)
- [ ] If Phase 2 agent harness is ready: show Graphiti student model being built across a session
- [ ] If gamification dashboard mockup is built: show XP earning, level progression, achievement tracking, topic mastery bars
- [ ] Include Reachy Mini "Scholar" demo if robots have arrived — even a brief clip of verbal progress reporting

### 6.2 Public Code Repository ✅ (Required)

**What exists today:**
- `guardkit/agentic-dataset-factory` — the pipeline repo (private)
- Training scripts, domain configs, GOAL.md, tools, prompts all written

**What needs to happen:**
- [ ] Create a public repo (e.g. `appmilla/gcse-study-tutor` or `appmilla/gemma4-gcse-tutor`)
- [ ] Include: dataset factory pipeline code (the methodology), fine-tuning scripts, deployment configs
- [ ] Include: gamification engine Pydantic models and design document
- [ ] Exclude: the actual training data (copyrighted source materials), API keys, personal configs
- [ ] Include: a well-documented `domains/gcse-english-tutor/GOAL.md` as the exemplar domain config
- [ ] Include: the Docling ingestion pipeline
- [ ] Write a proper README with architecture diagrams, setup instructions, and replication guide
- [ ] Aligns with existing strategy: open-source the pipeline, not the data

### 6.3 Technical Write-Up ✅ (Required)

**What exists today:**
- Extensive research docs across multiple repos
- Fine-tuning guide (`docs/research/ideas/fine-tuning-getting-started.md`)
- Agentic dataset factory conversation starter (architecture, design decisions, pipeline stages)
- GCSE English Training Data Plan
- GCSE English AI Tutor Proposal

**What needs to happen:**
- [ ] Synthesise into a single, coherent technical write-up covering:
  - The two-layer principle: fine-tuning teaches behaviour, RAG provides knowledge
  - Player-Coach adversarial data generation (why this produces better training data than manual curation)
  - Domain-agnostic pipeline design (how to replicate for any subject/exam board/country)
  - Fine-tuning methodology: Unsloth, 75/25 `<think>` ratio, ShareGPT format
  - On-device deployment: GB10 → Ollama → GGUF, zero cloud dependency
  - Phase 2 architecture: DeepAgents + Graphiti for adaptive tutoring
  - Gamification design: single-user engagement mechanics, the personal-growth-not-competition principle, Reachy as AI companion, level progression, achievement system
  - How Graphiti underpins both the adaptive tutoring AND the gamification state
  - Evaluation approach and results
- [ ] Frame around the hackathon's education track: personalised, offline, privacy-preserving, and — critically — *engaging enough that a teenager will actually use it*

### 6.4 Demo Video ✅ (Required)

**What exists today:**
- YouTube channel infrastructure and content strategy
- Joby GorillaPod + sleeve adapter for walk-and-talk content

**What needs to happen:**
- [ ] Script a 3-5 minute video showing:
  1. The problem: GCSE students need personalised tutoring; human tutors cost £30-50/hr; AI tutors send data to the cloud; revision guides gather dust because they're passive
  2. The solution: fine-tuned Gemma 4 running on a box under the desk, with gamification that makes a teenager want to come back
  3. The pipeline: how training data is generated (30-second overview of Player-Coach)
  4. The demo: Lilymay using the tutor for real revision (screen recording) — show a Macbeth session earning XP, a daily challenge, achievement progress
  5. The gamification: topic mastery dashboard, streak tracking, near-unlockable achievements, Boss Battle mode concept
  6. The companion: Reachy Mini "Scholar" reporting progress (even if mocked up — "How's revision going?" scenario)
  7. The vision: multi-subject expansion, Graphiti adaptive model, the system getting smarter over time
- [ ] This video doubles as YouTube content — fits the "building in public" narrative perfectly
- [ ] The gamification UI mockups from the January session are visual gold for the video — even static screenshots of the dashboard design tell a story

---

## 7. Multi-Subject Expansion (Strengthens Submission)

The domain-agnostic pipeline design means adding subjects is a config change, not a code change. Each subject gets a `domains/{subject}/` directory with a `GOAL.md` and `sources/`.

| Subject | Status | Notes |
|---------|--------|-------|
| English Language (AQA 8700) | ✅ First run complete | ~1,736 examples, fine-tuned |
| English Literature (AQA 8702) | ✅ Covered in first run | Same domain config |
| Maths (AQA) | 🔶 Planned | Needs ~500-600 additional behaviour examples; different pedagogical style |
| French (AQA 8652) | 🔶 Planned | New spec, first exams summer 2027; specimen papers only |
| Spanish (AQA 8692) | 🔶 Planned | New spec, first exams summer 2027; specimen papers only |

**For the submission:** Even if only English is fully fine-tuned, showing the domain config for Maths and describing the expansion path demonstrates the pipeline's generality. This is the "template for future social impact applications" the hackathon values.

---

## 8. Timeline: Dual-Track with DDD Southwest

The DDD Southwest talk (16 May, Engine Shed, Bristol) focuses on the Architect Agent. The hackathon submission (18 May) focuses on the study tutor. Different projects, but shared infrastructure knowledge.

### Week of 14-20 April
- [ ] Decide: enter the hackathon (Y/N)
- [ ] If yes: create the public repo, structure it, write the README skeleton
- [ ] Begin synthesising the technical write-up from existing docs
- [ ] Clean up gamification Pydantic models from January session for inclusion in repo

### Week of 21-27 April
- [ ] Run evaluation on existing fine-tuned model (golden set, Claude-as-judge)
- [ ] If Maths domain is ready: kick off a second training run with merged dataset
- [ ] Begin the Phase 2 DeepAgents harness (if time allows — this is the stretch goal)
- [ ] Build a gamification dashboard mockup (React artifact or static HTML) — XP, levels, topic mastery, achievements. Visual material for video and write-up.
- [ ] Script the demo video

### Week of 28 April - 4 May
- [ ] DDD Southwest prep takes priority (Architect Agent demo)
- [ ] In parallel: Lilymay uses the tutor; capture screen recordings for demo video
- [ ] Draft technical write-up (including gamification design section)

### Week of 5-11 May
- [ ] Finalise DDD Southwest talk and slides
- [ ] Record and edit demo video
- [ ] Finalise technical write-up

### Week of 12-18 May
- [ ] 16 May: DDD Southwest talk
- [ ] 17-18 May: Final submission polish, ensure repo is clean, submit to Kaggle
- [ ] Submit before 23:59 UTC on 18 May

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Time squeeze with DDD prep | High | Medium | Tutor submission is packaging existing work, not new development. Keep scope to Phase 1 + Phase 2 design doc. |
| Phase 2 (DeepAgents + Graphiti) not ready | Medium | Low | Phase 1 (Ollama deployment) is the working demo. Phase 2 is presented as architecture/roadmap. Still a strong submission. |
| Multi-subject fine-tuning not ready | Medium | Low | English-only is sufficient. Pipeline generality demonstrated via GOAL.md configs, not necessarily trained models. |
| Public repo exposes proprietary methods | Low | Medium | Pipeline methodology is open; training data and source PDFs are excluded. This aligns with existing strategy. |
| Demo video quality | Low | Medium | Rich has YouTube infrastructure. A genuine screen recording of Lilymay using the tutor is more compelling than polish. |
| Lilymay doesn't want to be on camera | Medium | Low | Rich can demo as the student. Or record just the screen, not the person. |

---

## 10. What Makes This Submission Stand Out

1. **It's real.** Not a weekend hack. Built over months for a real student with real exams in summer 2027.

2. **It solves the engagement problem, not just the intelligence problem.** Most AI tutor demos prove the model can answer questions. This one asks: will a teenager actually open it on a Tuesday evening? The gamification engine — XP, levels, achievements, daily challenges, Boss Battle mode — is designed around that question. The single-user insight (personal growth, not competition) is a genuine design contribution.

3. **The pipeline is the product.** The methodology — agentic dataset generation, two-layer architecture, domain-agnostic config — is more valuable than any single model checkpoint. It's replicable by any school, any country.

4. **It runs on owned hardware.** A £3,500 box under a desk. No cloud bills. No data leaving the house. This is the hackathon's thesis made concrete.

5. **The stack matches the special mentions.** Unsloth for fine-tuning, Ollama for deployment. Not forced — these were chosen independently because they're the right tools.

6. **Graphiti does double duty.** The same knowledge graph that powers adaptive tutoring (topic confidence, misconception tracking, session history) also stores the gamification state (XP, streaks, achievement progress). One persistence layer, two functions. This is architecturally clean and practically powerful.

7. **The embodied companion addresses isolation.** Reachy Mini "Scholar" isn't a gimmick — it's the answer to the single-user gamification problem. A robot that verbally celebrates your streak, suggests which achievement you're close to unlocking, and reports your progress to your parent in natural speech creates the social-feeling dimension that leaderboards would otherwise provide.

8. **It has a genuine roadmap.** Graphiti student modelling, DeepAgents adaptive harness, Reachy Mini embodied interface, multi-subject expansion, Boss Battle exam mode. The submission shows where this goes, not just where it is.

9. **The open-source strategy is principled.** Pipeline and methodology: open. Training data and copyrighted sources: excluded. This is legally clean and strategically sound.

---

## 11. Decision Point

**Enter?** The incremental effort is ~2 weeks of packaging and polish on top of existing work. The downside is distraction from DDD prep. The upside is a $200K prize pool, a portfolio piece, YouTube content, and public validation of the methodology.

**Recommendation:** Yes, enter. But scope the submission to Phase 1 (working Ollama deployment) as the demo, with Phase 2 (DeepAgents + Graphiti) presented as architecture and roadmap. Don't let the hackathon scope-creep into building Phase 2 under deadline pressure.

---

*Prepared: 12 April 2026*
*For: Rich Woollcott / Appmilla*
