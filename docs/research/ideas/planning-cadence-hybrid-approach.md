# Planning Cadence — Hybrid Approach

**Date:** 17 April 2026
**Audience:** Rich (self) + DDD Southwest talk material (16 May 2026)
**Status:** Approach decision — informs how every subsequent phase pair is produced

---

## The decision in one sentence

Write the next phase in full (scope + build plan), sketch the phase after that (scope only), leave anything further deferred until hardware, data, or measurements make the sketch meaningful — and add an explicit re-validation gate at each phase transition to catch plans that aged badly against reality.

## Why this is worth naming

The question "do we plan upfront or discover as we go" is one of those software engineering dichotomies that pretends to be binary but isn't. Pure waterfall has a specific set of failure modes; pure agile has a different specific set. The interesting move is to pick which failure mode you can live with for the specific project in front of you, and then instrument against the other one.

For Study Tutor, built to a hard 31-day deadline on top of an architectural vocabulary that's already been exercised twice (specialist-agent and agentic-dataset-factory), the failure modes are asymmetric. Uncertainty about *what we're building* is low. Uncertainty about *what measurements will say* when we build it is high. That asymmetry drives the cadence choice.

---

## What specialist-agent actually did

Looking at `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/research/ideas/` there are eight scope+build-plan pairs: Phase 0, 1, 1B, 1C, 2, 3, F, G. All present simultaneously. All consumed in sequence by the GuardKit pipeline (`/system-arch` → `/system-design` → `/system-plan` → per-feature `/feature-spec` → `/feature-plan`).

So a surface reading is "that's waterfall." But two details complicate that reading.

**Phase 1B and 1C didn't exist when Phase 1 was drafted.** They emerged as refactors and gaps surfaced *during* Phase 1's execution. The unified-agent-harness insight (70% structural / 30% role-specific) became a documented phase because Phase 1 learning made it visible. The domain-fidelity gap became its own phase because a validation run scored lower than expected. That's not waterfall — that's "we plan ahead when we can, and insert new phases when learning demands it."

**TASK-DEPG-A3F2 Decision #2 claimed "near-full parity" for PO over MCP.** This was written during Phase 2 planning based on the adapter shape visible at the time. It stayed in place through three subsequent milestones. The TASK-REV-B8E4 walkthrough in April 2026 falsified it in specific enumerable ways (architect handlers were wired but Orchestrator methods were missing; PO handlers hard-coded `player_model="claude"`; PO tool descriptions promised fire-and-forget but the implementation was synchronous await). None of the workflow layers between "plan written" and "plan falsified" caught it. That's a real cost of front-loaded planning, and LES1 §8 explicitly records it: *"Decision records must be revalidated at each major milestone."*

The honest reading: specialist-agent's approach was front-loaded planning with opportunistic new-phase insertion, and it was missing an explicit re-validation gate. The gate wasn't needed until a deployment walkthrough forced a re-read of decisions made months earlier. By then, three things had drifted.

## The two failure modes

**Plan-too-late (pure agile).** Finish Phase 0, pause, spend 2–3 days planning Phase 1. In a 31-day burn that's ~10% of the budget spent on planning per phase transition. Three transitions = ~30% of the budget on planning. You also lose the compounding benefit specialist-agent demonstrated: Phase 1B existed as a concept while Phase 1 was still building, which meant Phase 1 code was written with Phase 1B's eventual shape in mind. That context-carrying is free if you've already sketched the next phase; expensive if you haven't.

**Plan-too-early (pure waterfall).** Draft Phase 1, 2, and the Reachy phase now, based on what you think will be true after Phase 0 ships. Phase 0 turns up three things you didn't expect — maybe the three-hop Graphiti latency is 8 seconds not 2, maybe Bedrock's output quality diverges from Ollama, maybe Scholar doesn't arrive until 10 May. Now Phase 1 scope has decisions hard-coded against wrong premises and Phase 2 depends on outputs that aren't what you assumed. This is the TASK-DEPG-A3F2 failure mode in its textbook form.

Neither failure mode is fatal. Both cost time. The question is which one you're better equipped to catch.

## The hybrid cadence, explicitly

Three rules. Each phase transition follows them.

### Rule 1 — Write the next phase in full

Scope and build plan both. Consumable by `/system-arch` on day one of that phase's weekend. Day-by-day plan with review gates. This is the part that looks like waterfall.

Justification: we know our architectural vocabulary. Three-layer architecture, Player-Coach, MCP, Graphiti student model, session lifecycle, gamification state machine — every one of these is exercised in specialist-agent or agentic-dataset-factory. Planning a phase that uses these patterns isn't speculation; it's composition against known primitives.

### Rule 2 — Sketch the phase after that — scope only, no build plan

Features named, dependencies clear, do-not-change list present, success criteria provisional. But no day-by-day execution plan. Explicit note in the doc: "build plan deferred to [previous phase]'s Thursday prep."

Justification: scope is about *what we're building*; that's stable. Build plan is about *how long each piece takes and what order resolves risk fastest*; that depends on measurements we don't have yet. Phase 1 latency spike will tell us whether Phase 2's session-event handling can be synchronous. Phase 1's Coach tuning will tell us whether Phase 2's gamification triggers can attach directly to Coach output or need an intermediate layer. You can't plan these days until you know.

### Rule 3 — Add a re-validation gate at each phase transition

First half-hour of the new phase: open the previous phase's scope and build plan. Read the success criteria. Mark each one green, yellow, or red against what actually shipped. Mark each assumption in the previous phase's do-not-change list as "held", "drifted", or "falsified". Update the new phase's scope to reflect any drift before starting work.

Output: a short `phase-N-validation.md` in `docs/research/ideas/` for each transition. Four headings, each one paragraph: "What held. What drifted. What was falsified. What this changes in the current phase."

Justification: this is the direct response to LES1's TASK-DEPG-A3F2 lesson. Specialist-agent didn't have this formally. Adding it here turns the lesson into process.

### What falls outside all three rules

No planning at all for anything more than two phases out. The Reachy integration is exactly the right example: we have a conversation starter doc but no scope, because we don't have the hardware yet and wouldn't know what to put in the scope. When the 4 May gate is reached (or Scholar arrives, whichever is first), we scope it then, as "the next phase." Rule 1 kicks in at that point.

## When this cadence breaks down

Three conditions would flip the recommendation.

**If the architectural vocabulary is unfamiliar.** First specialist-agent attempt, first DeepAgents project, first Player-Coach loop — thinner planning, more discovery. We're not in that condition; we're in the opposite.

**If the deadline is soft.** If 18 May could slip a week, Phase 1 scope could be written after Phase 0 ships without cost. The deadline is not soft. The cadence adapts to the deadline constraint.

**If the known unknowns outweigh the knowns.** If Study Tutor needed to discover whether Ollama can host the 31B model, whether Graphiti can represent student state, whether the fine-tuned model tutors competently — pure agile. But those are already known. The unknowns are measurement-level, not architecture-level. Hybrid fits.

## Compared to "just write it all upfront"

What pure waterfall would produce right now: Phase 1, 2, and a Reachy phase, all fully scoped and build-planned before any of Phase 0 ships. Plus probably a Phase 3 (multi-subject) speculative scope.

Cost: roughly one full day of planning, delivered in three days (Thursday 18 – Saturday 20 April) instead of eight hours Thursday + eight hours Sunday-evening-of-Phase-1. The quality of Phase 2 and Reachy scopes would be materially worse — Phase 2 build plan would assume latency numbers we don't have, Reachy scope would assume hardware we haven't plugged in.

The hybrid saves the lower-quality planning for the moments when it would be most speculative. Phase 2 gets its build plan on Thursday 23 April once Phase 1's Graphiti spike has produced latency numbers. Reachy gets its scope when Scholar ships.

## Compared to "plan nothing ahead"

What pure agile would produce right now: Phase 0 scope + build plan only. Phase 1 gets planned after Phase 0 ships. Phase 2 after Phase 1. Reachy when the hardware arrives.

Cost: roughly 2–3 days per phase transition spent on planning, inside a 31-day budget. Three transitions = 7–9 days, ~25–30% of the build budget. Momentum-breaking. Also loses the context-carrying benefit: Phase 0 code would be written without reference to Phase 1's shape, and every Phase 1 decision would be re-examined from scratch. The specialist-agent evidence showed this context-carrying is real and valuable.

The hybrid preserves momentum by writing the next-phase plan ahead, while protecting against speculative waste by leaving the phase-after-that at sketch level.

## The re-validation gate as first-class process

One of the outputs of this hybrid approach is that re-validation becomes a named artefact, not an aside. The doc produced at each transition — `phase-N-validation.md` — is a one-page record with four paragraphs:

**What held.** Assumptions and success criteria from the previous phase that were still true when we looked.

**What drifted.** Things that moved but didn't invalidate anything — adjusted XP numbers, revised latency budgets, swapped library versions. Acknowledged, noted, moved on.

**What was falsified.** Decisions that were provably wrong in retrospect. Named explicitly. The failure mode that caused them should be added to the lessons doc (LES2 round) so the next project doesn't repeat it.

**What this changes in the current phase.** Concrete scope or build plan edits. Made before the current phase's code work begins.

The specialist-agent workflow had the first two implicitly, handled the third only when a deployment walkthrough forced it, and never produced the fourth until TASK-REV-B8E4. Making this an explicit gate is specifically what catches the "Decision records must be revalidated at each major milestone" lesson (LES1 §8).

## Relationship to the GuardKit pipeline

GuardKit's pipeline is strictly sequential: `/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan` → `/feature-build`. Each command consumes the previous command's output.

The hybrid cadence doesn't change the pipeline — it changes *when the scope docs feeding the pipeline are written*. Phase 1's scope doc feeds Phase 1's `/system-arch`. Phase 2's scope (written now) feeds Phase 2's `/system-arch` after Phase 1's validation gate. Reachy's scope (written later) feeds its own `/system-arch` when hardware arrives.

The validation gate output (`phase-N-validation.md`) doesn't feed the GuardKit pipeline directly. It's a Claude-Desktop-readable record that informs whether the next phase's scope needs edits before `/system-arch` runs.

## DDD Southwest talk framing

For the "2026: The Year of the Software Factory" talk, this cadence is worth a slide or two because it addresses a specific audience objection.

The objection: "Your software factory agents produce plans too far ahead — they hallucinate the future, then you build against plans that age badly."

The answer: the factory can produce any granularity; the human operator chooses the cadence. Here's the one we chose for a known architectural vocabulary under a hard deadline. It's not waterfall and it's not agile. It plans where planning compounds and defers where deferral protects quality. And it adds a validation gate that turns a lesson from a previous project into process for this one.

Concrete evidence on the slide: two scope+build-plan pairs already committed (Phase 0 done, Phase 1 on deck); one scope-only sketch (Phase 2); one conversation starter (Reachy) that's not yet a phase. Four artefacts at four different maturity levels, chosen deliberately.

The talk's broader thesis is that Jira-style PM tools are a category error for AI-assisted development. This cadence is a small instance of that argument: the planning artefact is directly machine-readable (feeds `/system-arch`) and directly human-readable (narrative, decisions, re-validation). The artefact doesn't need to be translated through a ticket system; the ticket system can be derived from it.

## One honest caveat

This cadence is still plan-heavier than someone coming from a pure XP or Lean Startup background would choose. The trade-off is accepted deliberately because the deadline is hard and the architecture is familiar. If either condition flipped — deadline softens, architecture becomes unfamiliar — the cadence should flip with it. Don't treat the hybrid as the right answer for all projects. Treat it as the right answer for projects shaped like Study Tutor.

---

## Summary for the talk slide

| | Pure waterfall | **Hybrid (this approach)** | Pure agile |
|---|---|---|---|
| Plan depth | All phases fully planned upfront | Next phase full, phase-after sketch, further deferred | Only current phase planned |
| Momentum cost | Low between phases | Low between phases | 10% of budget per phase transition |
| Speculative waste | High (later phases planned against unmeasured reality) | Low (sketched phases don't commit to day-by-day) | Zero |
| Re-validation | Implicit, often missed | Explicit gate per phase transition | Implicit, but shorter planning horizon reduces the need |
| Best for | Stable requirements, long timelines | Known vocabulary, hard deadlines, measurable risk | Uncertain requirements, short feedback loops |
| Evidence here | — | `phase-0-*` + `phase-1-*` + `phase-2-scope` + Reachy conversation starter | — |

---

*Related:*
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` §8 — "Decision records must be revalidated at each major milestone"
- `decisions-log-2026-04-17.md` — the decision records that this cadence protects against drift in
- `state-of-the-project-and-phase-recommendation.md` — the context that made this cadence choice necessary
