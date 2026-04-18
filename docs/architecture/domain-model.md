# Study Tutor — Domain Model

**Status:** Phase 0 canonical.
**Generated:** 2026-04-18 by `/system-arch`.
**Authoritative sources:** `domains/gcse-english/GOAL.md`, `docs/gamification/design.md`, `decisions-log-2026-04-17.md`.

---

## 1. Pattern: Domain-Driven Design over six bounded contexts

Study Tutor's domain decomposes into six bounded contexts, two shared
kernels, and one anti-corruption layer. See `ADR-ARCH-001`.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Kernel A                             │
│              Domain Taxonomy (curriculum)                        │
│  Subject · Paper · Text · AssessmentObjective · Topic ·          │
│  GradeTarget · ConfidenceBand                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ used by ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Tutoring   │  │ Knowledge &  │  │   Student    │
    │              │──│  Curriculum  │──│    Model     │
    │ (TutorSession│  │ (Text, AO,   │  │ (Student,    │
    │   aggregate) │  │ Collection)  │  │ Confidence)  │
    └──────┬───────┘  └──────────────┘  └──────┬───────┘
           │                                    │
           │  emits/consumes                   │
           └────────────────┬───────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Kernel B                             │
│              Session Event Vocabulary                            │
│  session.started · session.turn_completed · session.completed ·  │
│  achievement.unlocked · quest.completed · quest.expired ·        │
│  boss_battle.completed                                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    ┌──────────────┐
                    │ Gamification │
                    │              │
                    │(StudentProg, │
                    │ Achievement, │
                    │ Quest)       │
                    └──────────────┘

    ┌──────────────────────┐      ┌──────────────────────┐
    │   MCP Transport      │─────→│ Inference Runtime    │
    │                      │      │  (anti-corruption    │
    │  (McpAdapter, 4      │      │   layer — LLMClient) │
    │   tools, SR-07       │      │                      │
    │   classified)        │      │ Ollama|Bedrock|API   │
    └──────────────────────┘      └──────────────────────┘
```

---

## 2. Bounded Context 1 — Tutoring

**Purpose.** Owns the session lifecycle and the tutor's interactive
behaviour. Everything the student experiences turn-by-turn happens here.

**Location (P0):** `src/study_tutor/session/tutor_session.py`,
`src/study_tutor/mcp/adapter.py` (partial — handler façade),
`roles/tutor/role.yaml`, `domains/gcse-english/GOAL.md`.

### 2.1 Aggregate root: `TutorSession`

| Field | Type | Invariant |
|---|---|---|
| `session_id` | UUID | Immutable |
| `student_id` | str | Immutable; references Student in Student Model context |
| `subject` | Subject enum | Immutable after session start |
| `paper` | Paper enum (optional) | Immutable after session start |
| `topic` | Topic (optional) | Mutable — student can switch mid-session |
| `grade_target` | GradeTarget enum (4–9) | Mutable; planner recalibrates |
| `state` | SessionState enum | State machine — see below |
| `turns` | list[Turn] | Append-only |
| `started_at` | datetime | Immutable |
| `ended_at` | datetime (nullable) | Settable exactly once |

**State machine:**

```
 initialised ──► planning ──► active ──► summarising ──► ended
                    │            │                         ▲
                    │            └──────── (abandonment) ──┘
                    └──────── (skip planning) ─────────────┘
```

**Invariants:**
- No turns accepted when `state == ended`.
- `state` transitions are monotonic (no going back).
- A session abandoned before completing a single turn emits no
  `session.completed` event (gamification §2.1: no XP for <2-min
  abandons).

### 2.2 Value objects in this context

- `Turn` — `{index, role, content, timestamp, aos_scaffolded, rag_chunks_used}`.
  Append-only.
- `TurnFeedback` (P1) — Coach-produced quality score per AO.
- `SessionSummary` (P1) — end-of-session synthesis with per-topic
  confidence-delta proposals (capped ±0.1 per session — `design.md §6.2`).

### 2.3 References

- → Student Model (by `student_id` only — no cross-context object
  references).
- → Knowledge & Curriculum (by `Topic`/`AO`/`Text` ID only).
- → Inference Runtime (via `LLMClient` injection).

### 2.4 Events emitted

- `session.started {session_id, student_id, subject, topic}` — on
  transition to `planning` or `active`.
- `session.turn_completed {session_id, turn_index, ao_scaffolded}` — per
  turn. Consumers: Coach (P1, evaluates); Student Model (P1, may append
  misconception).
- `session.completed {session_id, duration, topic, aos_touched,
  quality_score}` — on transition to `ended`. Consumers: Gamification
  (P2), Student Model (P1).

---

## 3. Bounded Context 2 — Knowledge & Curriculum

**Purpose.** Owns the curriculum taxonomy and RAG retrieval. Provides the
*what* that the Tutoring context teaches.

**Location:** `domains/gcse-english/GOAL.md` (P0 authoritative),
`domains/gcse-english/sources/` (P1 BYOS input), `src/study_tutor/knowledge/`
(P1 runtime).

### 3.1 Aggregate roots

- **`CurriculumCollection`** — per domain, per subject. Phase 1+ ChromaDB
  collection. Aggregate state: `{subject, ingestion_timestamp,
  source_fingerprints, embedding_model}`.
- **`Text`** — named set text or cluster (`Macbeth`, `Power & Conflict
  poetry`, etc.). `{text_id, title, type, paper_mapping}`. Identity is
  `text_id`.
- **`AssessmentObjective`** — the six AOs from `GOAL.md §3`. Identity is
  `ao_id ∈ {AO1, AO2, AO3, AO4, AO5, AO6}`. Immutable.

### 3.2 Value objects

- `Topic` — a studyable unit within a Text (e.g. `macbeth:act1:witches`,
  `power_and_conflict:ozymandias`). Identity is `topic_id`.
- `SourceDocument` — a user-provided PDF (Mr Bruff, CGP, etc.). Not
  shipped in repo (CC-10). Phase 1+ ingested via Docling.

### 3.3 Invariants

- `SourceDocument` files are never committed to git (enforced by
  `.gitignore` — CC-10).
- The short-quotation rule (`GOAL.md §6.1`) is enforced at output time by
  the Tutoring context, not by this context — this context owns the data,
  not its downstream use.

### 3.4 Phase 0 status

Taxonomy declared in `GOAL.md §3–§4`. No runtime code in Phase 0. ChromaDB
wiring + Docling ingestion are Phase 1 (FEAT-PO-001-roadmap onwards).

---

## 4. Bounded Context 3 — Student Model

**Purpose.** Owns per-student state — who they are, what they know,
what they've misunderstood, how they've progressed. Layer 3 of the
three-layer architecture.

**Location:** `src/study_tutor/student/` (P1), Graphiti group IDs
`student:{id}` and `subject:gcse-english`.

### 4.1 Aggregate root: `Student`

| Field | Type | Invariant |
|---|---|---|
| `student_id` | str | Immutable |
| `name` | str (optional) | Mutable |
| `scoped_group_id` | `student:{student_id}` | Derived, immutable |
| `subjects_studied` | set[Subject] | Append-only |
| `current_level` | int (1–15) | Monotonic increase |
| `total_xp` | int ≥ 0 | Monotonic increase |
| `current_streak` | int ≥ 0 | Can reset to 0 |
| `longest_streak` | int ≥ 0 | Monotonic increase |
| `created_at` | datetime | Immutable |

**Invariants:**
- `total_xp` never decreases (design.md §11).
- `current_level` never decreases (mastery unlocks are sticky — §5).
- `longest_streak >= current_streak` always.

### 4.2 Value objects / sub-entities

- **`TopicConfidence`** — per `(student_id, topic_id)`. Scalar `0.0 ≤ c
  ≤ 1.0`. Band (`Struggling`, `Developing`, `Secure`, `Mastered`) derived
  from thresholds in `design.md §6`. Invariant: per-session delta capped
  at ±0.1.
- **`Misconception`** — flagged by Coach during `session.turn_completed`
  (Phase 1+). `{student_id, misconception_id, topic_id, first_seen,
  last_seen, recurrence_count}`.
- **`SessionEpisode`** — one per completed session. `{session_id,
  student_id, topic_id, duration, xp_earned, aos_touched, quality_score,
  ended_at}`.
- **`AssessmentObjectiveProgress`** — per `(student_id, ao_id)`. Roll-up
  of scaffolded turns over time.

### 4.3 Events consumed

- `session.started` → create SessionEpisode head.
- `session.turn_completed` → may append `Misconception` (P1 Coach).
- `session.completed` → close SessionEpisode; update `TopicConfidence`
  (bounded ±0.1); update `AssessmentObjectiveProgress`.

### 4.4 Phase 0 status

Schema declared here and in `GOAL.md §11`. No runtime code in Phase 0.
Phase 1: Graphiti wiring + entity extraction via Gemini + embeddings via
GB10 nomic-embed.

---

## 5. Bounded Context 4 — Gamification

**Purpose.** Owns the engagement layer — XP, levels, achievements,
streaks, Boss Battle unlock gating, daily challenges, quests.

**Location:** `docs/gamification/design.md` (P0 authoritative economy);
`src/study_tutor/gamification/` (P2 runtime engine).

### 5.1 Aggregate roots

- **`StudentProgress`** — per student. `{student_id, level_title (e.g.
  "Scholar"), total_xp, current_streak, longest_streak,
  daily_sweep_state, active_quest_ids, trophies}`.
- **`Achievement`** — enumerated set from `design.md §5`. Identity is
  `achievement_id`. Sticky — once unlocked, always unlocked.
- **`Quest`** — active and historical. `{quest_id, student_id, shape,
  target, progress, expires_at, completed_at (nullable)}`. One
  concurrent at Level <9; two at Level ≥9.
- **`BossBattle`** — unlocked at Level 8. `{boss_id, student_id, paper,
  duration, trophy_id, first_completed_at, practice_completions}`.

### 5.2 Invariants (from `design.md`)

- Level 1→2 at 100 XP; full 15-level curve per §3.1. Monotonic.
- Mastery achievements at 80% confidence (§5.2).
- Streak resets to 0 at midnight of any day without a session completion
  (§4.1).
- Weekly Boss Battle: first completion per calendar week awards XP;
  subsequent completions unlock practice mode (no XP).
- Unlock gates (§3.2) are one-way.

### 5.3 Events consumed

- `session.completed` → XP delta (180 Macbeth / 60 short / 120 std / +30
  quotation / +40 review; 1.25× for Grade 8–9); streak delta; achievement
  check; daily-challenge check.
- `achievement.unlocked` (self-emitted) → XP bonus per `design.md §5`;
  Reachy celebration trigger (P2 stretch).
- `boss_battle.completed` → XP + trophy; confidence delta via Coach.

### 5.4 Events emitted

- `achievement.unlocked {student_id, achievement_id, xp_reward}`
- `quest.completed`, `quest.expired`
- `boss_battle.completed {student_id, paper, trophy_id}`

### 5.5 Phase 0 status

Design complete (`docs/gamification/design.md`). No runtime code. Phase 2
implements the state engine. See `ADR-ARCH-013` — the engine may be
implemented as a deepagents custom middleware reacting to events.

---

## 6. Bounded Context 5 — Inference Runtime

**Purpose.** Provider abstraction — normalises Ollama, AWS Bedrock, and
API providers (OpenAI, Anthropic, Gemini) behind a single interface. Is
the anti-corruption layer for the rest of the domain.

**Location:** `src/study_tutor/llm/client.py`.

### 6.1 Aggregate root: `LLMClient`

**Factory-resolved** from `AGENT_MODELS__REASONING_MODEL` env var (CC-03 /
SR-03). No handler hard-codes a provider.

| Provider label | Endpoint | Phase |
|---|---|---|
| `local` | Ollama on GB10 (Tailscale) | P0 primary (default) |
| `bedrock` | AWS Bedrock Custom Model Import | P0 validation; P1+ primary for demo week |
| `openai` | OpenAI API | Declared, reserved for Coach / fallback |
| `anthropic` | Anthropic API | Declared, reserved |
| `gemini` | Google Gemini API | Declared; also used by Graphiti (outside `LLMClient`) |

### 6.2 Invariants

- Provider resolved at factory, not at handler (CC-03 — LES1
  PMEV/CRMV evidence).
- Every provider named in code appears in `pyproject.toml`
  `[providers]` extra (CC-04 — LES1 LCOI).
- `LLMClient.invoke(messages, **opts)` is the sole public interface.
  Upstream contexts never construct `ChatOllama`, `ChatBedrock`, etc.
  directly.

### 6.3 Anti-corruption seam

All provider-specific knowledge (Bedrock ARNs, Ollama URLs, API retry
semantics, model IDs) stays inside this context. Upstream code speaks
only the `LLMClient.invoke(messages, **opts)` vocabulary.

---

## 7. Bounded Context 6 — MCP Transport

**Purpose.** Owns the external protocol surface. Turns the tutor into a
discoverable, invokable system. Enforces the six parity surfaces'
transport-layer rules (SR-01, SR-02, SR-07, CC-08).

**Location:** `src/study_tutor/mcp/adapter.py`,
`src/study_tutor/cli/main.py`, `scripts/mcp-wrapper.sh`.

### 7.1 Aggregate root: `McpAdapter`

Registers the following tools at startup:

| Tool | Classification (SR-07) | Target latency |
|---|---|---|
| `tutor_start_session` | long-running (returns `session_id` ≤ 1s; poll via `tutor_session_status`) | ≤ 1s return |
| `tutor_turn` | sync (< 30s) | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync — triggers async Graphiti write-back (P1) | < 2s |

### 7.2 Invariants

- **stdout exclusively MCP JSON-RPC** — all diagnostics via
  `click.echo(..., err=True)` (CC-01 / SR-01).
- **Bash wrapper `cd`s to an absolute path** before `exec` (CC-02 /
  SR-02).
- **Every tool description matches handler behaviour** — verified by
  `tests/unit/mcp/test_stdio_discipline.py` and the tool-contract test
  (CC-07 / SR-07).
- **Long-running tools return a `session_id` in ≤1s** (CC-08 — LES1 §4
  POLR evidence).
- **Phase 1+ leverages deepagents 0.5.3 `AsyncSubAgent` for Coach** rather
  than hand-rolling fire-and-forget (CC-12).

---

## 8. Shared kernels

### 8.1 Shared Kernel A — Domain Taxonomy

Definitions live in `domains/gcse-english/GOAL.md §3` (AOs) and `§4`
(texts/topics), and `docs/gamification/design.md §6` (confidence bands).
Code location (Phase 1+): `src/study_tutor/domain/taxonomy.py` (Pydantic
enums).

```python
class Subject(StrEnum):
    ENGLISH_LANGUAGE = "English Language"
    ENGLISH_LITERATURE = "English Literature"

class Paper(StrEnum):
    PAPER_1 = "Paper 1"
    PAPER_2 = "Paper 2"

class AssessmentObjective(StrEnum):
    AO1 = "AO1"  # Identify and interpret explicit/implicit information
    AO2 = "AO2"  # Language and structure
    AO3 = "AO3"  # Compare writers' ideas and perspectives
    AO4 = "AO4"  # Evaluate texts critically
    AO5 = "AO5"  # Communicate clearly, effectively, imaginatively
    AO6 = "AO6"  # Technical accuracy

class GradeTarget(IntEnum):
    G4 = 4; G5 = 5; G6 = 6; G7 = 7; G8 = 8; G9 = 9

class ConfidenceBand(StrEnum):
    STRUGGLING = "struggling"     # 0.0 ≤ c < 0.4
    DEVELOPING = "developing"     # 0.4 ≤ c < 0.6
    SECURE = "secure"             # 0.6 ≤ c < 0.8
    MASTERED = "mastered"         # 0.8 ≤ c ≤ 1.0
```

Consumer contexts: Tutoring, Knowledge, Student Model, Gamification.

### 8.2 Shared Kernel B — Session Event Vocabulary

Names and minimal payloads. Stable across phases; consumers opt in.

```python
session.started         { session_id, student_id, subject, topic }
session.turn_completed  { session_id, turn_index, ao_scaffolded }
session.completed       { session_id, duration, topic, aos_touched,
                          quality_score }
achievement.unlocked    { student_id, achievement_id, xp_reward }
quest.completed         { student_id, quest_id }
quest.expired           { student_id, quest_id }
boss_battle.completed   { student_id, paper, trophy_id }
```

Producer: Tutoring. Consumers: Student Model (P1), Gamification (P2),
Reachy (P2 stretch).

---

## 9. Domain event flow (Phase 1+)

```
 Student (via Open WebUI or Claude Desktop)
       │
       ▼
 McpAdapter.tutor_start_session
       │ create TutorSession
       ▼
 TutorSession ──── emits: session.started ────┐
       │                                       ▼
       │                            Student Model (P1)
       │                            (creates SessionEpisode head)
       ▼
 McpAdapter.tutor_turn (×N)
       │
       ▼
 TutorSession.advance()
       │ emits: session.turn_completed
       ▼
 ┌─────┴──────────┐
 │                │
 ▼                ▼ (async, deepagents AsyncSubAgent)
 Player          Coach
 (LLMClient)     (evaluates quality)
 returns text    writes TurnFeedback
                 │
                 ▼ at session-end only
                 Student Model (P1)
                 (appends Misconception if any)

 ... session ends ...
       │
       ▼
 TutorSession.end()
       │ emits: session.completed
       │
 ┌─────┴──────────┬──────────────┐
 ▼                ▼              ▼
 Student Model   Gamification    (future: Reachy celebration)
 (update         (XP + streak +
  TopicConf'     achievement
  via Coach-     check)
  proposed
  delta, ≤±0.1)
```

**Consistency model:** the `session.completed` event fan-out is async —
the tutor can return control to the student while Graphiti write-back and
gamification updates proceed in the background. This is deliberate
(ADR-ARCH-003).

---

## 10. Evolutionary notes

### Why DDD over Modular Monolith

Evaluated during Category 1 of the `/system-arch` session. DDD wins on
three grounds: (a) the three-layer architecture in
`deepagents-patterns-review.md §1.3` is explicit in the research and
maps directly to bounded contexts; (b) Phase 1/2 add genuine new
contexts (Student Model, Gamification Engine) that benefit from the
ubiquitous-language vocabulary; (c) specialist-agent's role-aware
pattern is already DDD-flavoured and Study Tutor inherits that
scaffolding. See `ADR-ARCH-001`.

### Why the student model is its own context

`TopicConfidence`, `Misconception`, and `SessionEpisode` have their own
lifecycle, their own persistence (Graphiti, not the session-scoped
in-memory dict), and their own consumers (Gamification, Reachy, future
Session Planner). Collapsing them into Tutoring would muddle read vs
write responsibilities at session-end boundary.

### Why Gamification is a context, not a feature

Gamification has its own aggregate roots (StudentProgress, Quest,
BossBattle), its own invariants (monotonic XP/level, sticky
achievements, weekly Boss Battle XP semantics), and its own event
vocabulary consumption. It is also delivered in a distinct phase (P2),
making the boundary naturally visible.

---

*Generated 2026-04-18. Changes to sections §2–§7 are breaking changes
and require re-running downstream commands (`/system-design`,
`/feature-spec`). Changes to §8 shared-kernel definitions require
migration planning for any entities already seeded in Graphiti.*
