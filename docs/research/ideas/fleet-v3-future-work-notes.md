# Study Tutor — Future Work Notes from Fleet v3 Alignment

> **Date:** 19 April 2026
> **Status:** Future-work notes — not requiring `/system-arch` re-run
> **Context:** Fleet v3 framing session (see `forge/docs/research/ideas/fleet-architecture-v3-coherence-via-flywheel.md`)
> **Parent:** Study Tutor ARCHITECTURE.md (unchanged)

---

## Why This Note Exists

On 19 April 2026, Rich and Claude worked through the ecosystem-level architectural framing that produced "Fleet Architecture v3 — Coherence via Flywheel." That session identified two tactical enhancements the Study Tutor should adopt when it reaches the relevant phases — but neither requires re-running `/system-arch` or changing the core ARCHITECTURE.md.

This document captures those enhancements so they don't get forgotten and so they can be absorbed naturally during the appropriate later phase.

---

## Enhancement 1: Async Subagents for Background Paper Generation

### What

DeepAgents 0.5.3+ exposes `AsyncSubAgent` — a preview feature that lets a supervisor launch subagents that run concurrently without blocking the main reasoning loop. See Forge's ADR-ARCH-031 for the parallel decision and full context.

### Why this fits Study Tutor

The Tutor's default interaction is sync-conversational — student asks a question, tutor responds, student asks follow-up. That's sync `task()` territory. But there are *background* jobs that fit the async pattern naturally:

- **Fetching and Docling-processing a past paper PDF** while the student continues talking
- **Generating practice questions** from specification coverage gaps without interrupting the current session
- **Pre-scoring attempted answers** for later feedback while the student works on the next question
- **Streaming TTS on Reachy "Scholar"** while the reasoning for the next response continues

The shape: student's conversational experience stays sync and responsive; work that doesn't need to block the conversation runs async.

### When to build

When implementing any of these specific capabilities. The first one to arrive (likely background paper-gen) is the right place to establish the pattern. Subsequent background jobs inherit the pattern.

### How it integrates

Same shape as Forge's ADR-ARCH-031:

- Register the background-work graphs in `langgraph.json` alongside the main tutor supervisor
- Use ASGI transport (co-deployed) by default
- Supervisor system prompt teaches the reasoning model when to launch async (non-blocking background work) vs call sync `task()` (immediate reasoning subtask)
- Launched tasks tracked in `async_tasks` state channel — survives context compaction

### Trace-richness applies

Per ADR-FLEET-001, the background subagents' traces write to the tutor's `tutor_teaching_history` Graphiti group. This means the `tutor.learning` module can see which kinds of background work succeed (and compound priors for future sessions).

---

## Enhancement 2: Memory Store for Cross-Session Recall

### What

LangGraph's **Memory Store** is a built-in primitive for cross-thread persistent memory — distinct from Graphiti (which stores structured relationships and decisions). Memory Store is the right home for recall that spans sessions but doesn't need entity-relationship modelling.

### Why this fits Study Tutor

The phrase that matters: **"Last session we struggled with projectile motion."**

That's not a fact about the student (which would be RAG territory), not a structured decision (which would be Graphiti territory), and not a per-subject corpus lookup (which is ChromaDB per-subject RAG). It's conversational recall of *what we were doing together* — and that's exactly what Memory Store is for.

Other examples of Memory Store content:
- "We agreed to focus on trigonometry until the mock exam"
- "She gets frustrated with multi-step algebra; break those down more"
- "He prefers visual explanations over word problems"
- "Last week's practice test scored 62% — up from 48%"

This is relationship context that accumulates session-by-session and shapes how the tutor opens each new session.

### When to build

As soon as the Tutor is delivering multi-session teaching to any student. Earlier than you might think — even internal testing benefits from Memory Store because it proves the pattern works before you're optimising it.

### How it integrates

Memory Store is a LangGraph primitive with its own API. The supervisor:

- Reads Memory Store at session start (informs opening)
- Writes to Memory Store at session end (captures what happened)
- Queries Memory Store during session for contextual references ("Remember when we did X?")

Memory Store is **per-student**. The thread scope is student × time window (a "session"). Each student's Memory Store is separate; no cross-student bleed.

### Relationship to Graphiti

Memory Store and Graphiti complement, not compete:

| Content type | Store |
|---|---|
| "Last session we worked on X" | Memory Store |
| "Student Y's weakness is projectile motion" (structured student profile) | Graphiti `tutor_teaching_history` |
| "Teaching pattern: when struggling with algebra, use visual aids" (learned pattern) | Graphiti `tutor_teaching_history` via `tutor.learning` |
| "GCSE Physics specification, topic 4.5, section 3" | ChromaDB per-subject RAG |
| "Topic 4.5 includes these sub-topics and these past paper questions" | ChromaDB per-subject RAG |

All four stores coexist in the Tutor. They answer different questions.

---

## Enhancement 3 (Implicit): Trace-Richness for `tutor_teaching_history`

Per ADR-FLEET-001 — applies fleet-wide from day one. When `tutor_teaching_history` is implemented as part of the `tutor.learning` module, it uses the fleet-wide trace-rich schema (see ADR-FLEET-001 §Required fields). Not strictly a "future work" item — it's a standard to adopt *at the time of first `tutor_teaching_history` write*.

---

## What This Note Does *Not* Change

The Study Tutor's ARCHITECTURE.md, ADRs, and `/system-arch` output are all unchanged. The enhancements above:

- Don't require re-running `/system-arch`
- Don't contradict any existing ADR
- Are additive, not replacement
- Each maps to a specific later phase (paper-gen, multi-session deployment, learning module implementation)

When the time comes to implement each, reference this note + the fleet-wide docs (fleet v3, ADR-FLEET-001, Forge ADR-ARCH-031) as context.

---

## Source Documents

| Source | Contribution |
|---|---|
| `forge/docs/research/ideas/fleet-architecture-v3-coherence-via-flywheel.md` | Keystone fleet framing — D40-D46 |
| `forge/docs/research/ideas/ADR-FLEET-001-trace-richness.md` | Fleet-wide trace schema |
| `forge/docs/architecture/decisions/ADR-ARCH-031-async-subagents-for-long-running-work.md` | Parallel async-subagents decision for Forge |
| DeepAgents 0.5.3 docs — Memory Store, Async subagents | SDK capability reference |
| 19 April 2026 conversation (Rich + Claude) — fleet v3 framing session | Originating context |

---

*19 April 2026 · Study Tutor future-work notes from fleet v3 alignment*
