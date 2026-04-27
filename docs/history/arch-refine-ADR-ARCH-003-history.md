/arch-refine --adr=ADR-ARCH-003 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  "broaden async write-back scope from session-end-only to every Graphiti write point per CC-13 (ARCH-018)"

I'll start by parsing arguments and loading the prerequisite context for ADR-ARCH-003.

Read graphiti.yaml
Bash List existing ADR files
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/decisions/ 2>/dev/null | head -50

OUT
total 200
drwxr-xr-x  20 richardwoollcott  staff    640 Apr 27 11:42 .
drwxr-xr-x   8 richardwoollcott  staff    256 Apr 27 11:43 ..
-rw-r--r--   1 richardwoollcott  staff   3622 Apr 18 23:57 ADR-ARCH-001-ddd-structural-pattern.md
-rw-r--r--   1 richardwoollcott  staff   3665 Apr 18 23:57 ADR-ARCH-002-three-layer-architecture.md
-rw-r--r--   1 richardwoollcott  staff   3512 Apr 18 23:57 ADR-ARCH-003-async-graphiti-writeback.md
-rw-r--r--   1 richardwoollcott  staff   3603 Apr 18 23:57 ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
-rw-r--r--   1 richardwoollcott  staff   2860 Apr 18 23:57 ADR-ARCH-005-defer-dockerfile-to-phase-1.md
-rw-r--r--   1 richardwoollcott  staff   3563 Apr 18 23:57 ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
-rw-r--r--@  1 richardwoollcott  staff   3513 Apr 19 13:27 ADR-ARCH-007-graphiti-split-topology.md
-rw-r--r--   1 richardwoollcott  staff   5361 Apr 27 10:00 ADR-ARCH-008-mcp-only-agent-access.md
-rw-r--r--   1 richardwoollcott  staff   3469 Apr 27 11:41 ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
-rw-r--r--   1 richardwoollcott  staff   3273 Apr 18 23:57 ADR-ARCH-010-pydantic-at-boundary-validation.md
-rw-r--r--   1 richardwoollcott  staff   2682 Apr 18 23:57 ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
-rw-r--r--   1 richardwoollcott  staff   4123 Apr 18 23:57 ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
-rw-r--r--@  1 richardwoollcott  staff   2737 Apr 19 13:27 ADR-ARCH-013-middleware-level-gamification-engine-future.md
-rw-r--r--   1 richardwoollcott  staff   3144 Apr 18 23:57 ADR-ARCH-014-single-user-scalability-posture.md
-rw-r--r--@  1 richardwoollcott  staff   5019 Apr 19 13:21 ADR-ARCH-015-uk-on-device-data-residency.md
-rw-r--r--   1 richardwoollcott  staff   4173 Apr 18 23:57 ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
-rw-r--r--   1 richardwoollcott  staff   7191 Apr 27 09:59 ADR-ARCH-017-tutor-start-session-sync-classification.md
-rw-r--r--   1 richardwoollcott  staff  10374 Apr 27 11:42 ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Read graphiti-latency-spike-results.md
Read ADR-ARCH-003-async-graphiti-writeback.md
Read ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Bash List architecture and design directories
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/architecture/ 2>/dev/null && echo '---' && ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/design/ 2>/dev/null

OUT
ARCHITECTURE.md
assumptions.yaml
container.md
decisions
domain-model.md
system-context.md
---
contracts
events-schema.yaml
mcp-tools.json
models
README.md
Read ADR-ARCH-017-tutor-start-session-sync-classification.md
I have enough context. Direct ADR target is ADR-ARCH-003, skipping disambiguation.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ SELECTED: ADR-ARCH-003 — Async Graphiti write-back at session-end boundary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current decision (summary):
  Status:   accepted (2026-04-18, Phase 0)
  Context:  Per-turn Graphiti writes would add 1–3s Gemini latency per turn,
            blowing CC-08 / p95 < 10s.
  Decision: Async write-back triggered at session-end boundary ONLY
            (per-turn observations batched in session-scoped memory).
  Related:  ADR-ARCH-002, ADR-ARCH-012, DEC-02, DEC-08
            (now also: ADR-ARCH-018 CC-13, latency-spike-2026-04-27)
The ARCH-018 refinement of cross-cutting concerns (today, 2026-04-27) explicitly flagged ADR-ARCH-003 as stale and called out that it needs its own /arch-refine to broaden scope. The query confirms that intent.

Now drafting the refined decision (Q1–Q4) directly from the latency-spike evidence and ARCH-018, since the user's invocation already supplies the rationale.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 REFINING: ADR-ARCH-003 → new ADR-ARCH-019
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q1. What has changed?
The 2026-04-27 Graphiti latency spike measured add_episode median 78.98s on the post-21-Apr vLLM-on-GB10 stack — ~15× the 5s SR-08 trigger threshold and ~2.6× the original DEC-08 1–3s assumption. ADR-ARCH-018 promoted SR-08 to a load-bearing cross-cutting concern (CC-13) and explicitly flagged ADR-ARCH-003's session-end-only framing as too narrow: with 78.98s writes, any awaited Graphiti write — not just session-end — blows p95 budgets and risks the CC-08 30s threshold. Mid-session, planner, and Coach-misconception writes need the same fire-and-forget treatment.

Q2. What is the new decision?
Graphiti write-back is async-from-caller at every write point in the tutor, not only at session-end. Concretely:

Every Graphiti add_episode / entity-update site (session-end episode, mid-session episodes if introduced, Coach misconception logs, planner topic-confidence updates, any future write point) goes through a helper that runs the work as a background task — deepagents.AsyncSubAgent (per ADR-ARCH-012) for write paths the Coach owns, or a plain asyncio.create_task for simpler writes.
Every caller-facing handler (tutor_session_end, tutor_turn, future MCP tools) returns to the user without awaiting Graphiti acknowledgement. tutor_session_end retains its < 2s bound; tutor_turn retains p95 < 10s.
Write failures emit a structured log line and do not raise from the MCP handler — fail-soft degradation, consistent with ADR-ARCH-003's original posture.
Within-session state still lives in the in-process TutorSession aggregate; what changes is that the flush points are no longer constrained to session-end, and every flush point follows the same fire-and-forget shape.
This decision is the architecture-level corollary of CC-13: ARCH-018 promoted the rule; ARCH-019 broadens the original session-end commitment to match it.
Q3. Alternatives considered?

Keep ADR-ARCH-003 as-is and rely solely on CC-13 for the broader rule. Rejected. ARCH-018 itself flagged ADR-ARCH-003 as needing this refinement; leaving the architecture decision at "session-end only" while the cross-cutting concern says "every write point" creates a permanent contradiction inside docs/architecture/. Future readers would have to reconcile the two.
Per-turn synchronous writes for "small" updates (e.g. Coach misconceptions). Rejected. The 78.98s median is for any add_episode; there is no measured cheap-write path. Differentiating "small" vs "session" writes would require a per-payload latency model we don't have.
Buffer all mid-session writes and flush at session-end (a generalisation of ADR-ARCH-003). Rejected for Phase 1. Adds session-scoped buffering and a single fat session-end flush — the latter would compound the 78.98s cost into a multi-minute session-end task. Fire-and-forget at each write point spreads the cost and matches CC-13's "uniform shape" requirement.
Move Graphiti writes onto a separate worker process / queue. Considered. Deferred — out of Phase 1 scope (single-user, single-process tutor); revisit if multi-user posture changes (currently single-user per ADR-ARCH-014).
Q4. Consequences?

Positive:

Architecture decision now coextensive with CC-13. No contradiction between ADR-ARCH-003 and ARCH-018.
Every Graphiti write site has a uniform fire-and-forget shape — easier to audit Phase 1 features against a single rule.
tutor_turn p95 < 10s and tutor_session_end < 2s remain achievable even with add_episode at 78.98s, because no caller-facing path awaits Graphiti.
Removes a guaranteed future SR-08 violation: the current ADR-ARCH-003 wording would justify (incorrectly) a sync mid-session write at some later feature.
Negative:

Background-task bookkeeping now appears at multiple sites in the tutor (not just session-end). Mitigated by routing all sites through one helper / AsyncSubAgent pattern.
A tutor crash now risks losing in-flight writes from any write point, not just the one session-end batch. Acceptable for Phase 1 MVP (single-user, no concurrent sessions); revisit if real crashes appear.
ADR-ARCH-003 remains queryable as the historical session-end-only decision; readers must follow superseded_by to ARCH-019. Standard cost of temporal superseding.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ DOWNSTREAM IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Now scanning for downstream artefacts that reference ADR-ARCH-003 or its session-end-only framing.

Bash Find files referencing ADR-ARCH-003 or session-end framing
IN
grep -rln "ADR-ARCH-003\|session-end boundary\|session-end-only\|session-end only" --include="*.md" --include="*.yaml" --include="*.yml" docs/ 2>/dev/null

OUT
docs/design/contracts/API-tutoring.md
docs/research/ideas/phase-0-build-plan.md
docs/design/README.md
docs/design/events-schema.yaml
docs/gamification/design.md
docs/planning/feature-roadmap.md
docs/architecture/container.md
docs/architecture/decisions/ADR-ARCH-002-three-layer-architecture.md
docs/architecture/ARCHITECTURE.md
docs/architecture/domain-model.md
docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
docs/history/system-design-phase-0-history.md
docs/history/system-arch-history.md
docs/history/command-history.md
docs/reviews/architecture/claude-desktop-review-system-arch-output.md
docs/history/system-plan-history.md
Bash Find files referencing async Graphiti write-back
IN
grep -rln "async.*write-back\|async.*writeback\|Graphiti write" --include="*.md" --include="*.yaml" --include="*.yml" docs/ 2>/dev/null | head -30

OUT
docs/research/ideas/phase-1-build-plan.md
docs/research/ideas/graphiti-latency-spike-results.md
docs/research/ideas/phase-2-scope.md
docs/research/ideas/reachy-integration-conversation-starter.md
docs/research/ideas/decisions-log-2026-04-17.md
docs/research/ideas/phase-0-scope.md
docs/research/ideas/phase-1-scope.md
docs/research/ideas/state-of-the-project-and-phase-recommendation.md
docs/research/ideas/phase-0-build-plan.md
docs/design/events-schema.yaml
docs/design/contracts/API-mcp-transport.md
docs/design/contracts/API-tutoring.md
docs/planning/feature-roadmap.md
docs/architecture/ARCHITECTURE.md
docs/architecture/container.md
docs/architecture/assumptions.yaml
docs/architecture/domain-model.md
docs/architecture/decisions/ADR-ARCH-002-three-layer-architecture.md
docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md
docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
docs/architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
docs/history/command-history.md
docs/history/system-plan-history.md
docs/history/system-design-phase-0-history.md
docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
docs/reviews/architecture/claude-desktop-review-system-arch-output.md
docs/history/system-arch-history.md
Bash Find specific line references to ADR-003 in downstream artefacts
IN
grep -n "ADR-ARCH-003\|session-end\|async.*write-back\|async.*writeback" docs/architecture/ARCHITECTURE.md docs/architecture/container.md docs/architecture/domain-model.md docs/design/README.md docs/design/contracts/API-tutoring.md docs/design/contracts/API-mcp-transport.md docs/design/events-schema.yaml docs/planning/feature-roadmap.md docs/gamification/design.md 2>/dev/null | head -80

OUT
docs/design/README.md:70:✓ No contradictions detected against the 16 architecture ADRs. The protocol set (MCP + CLI + Events) is congruent with ADR-ARCH-008 and ADR-ARCH-014. The Bedrock route classification matches ADR-ARCH-006. The async Events bus matches ADR-ARCH-003 and CC-11.
docs/architecture/domain-model.md:338:| `tutor_session_end` | sync — triggers async Graphiti write-back (P1) | < 2s |
docs/architecture/domain-model.md:443:                 ▼ at session-end only
docs/architecture/domain-model.md:466:(ADR-ARCH-003).
docs/architecture/domain-model.md:489:write responsibilities at session-end boundary.
docs/architecture/container.md:30:        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools, all sync per SR-07 (ADR-ARCH-017): tutor_start_session (sync; warm-up fire-and-forget), tutor_turn (sync), tutor_session_status (sync), tutor_session_end (sync; async Graphiti write-back in P1).")
docs/architecture/container.md:38:            Container(coach, "Coach (AsyncSubAgent)", "Python / deepagents AsyncSubAgent", "Quality monitor — async off hot path. Writes confidence deltas at session-end. [P1]")
docs/architecture/container.md:74:    Rel(coach, student_model, "Writes confidence delta [P1 on session-end]")
docs/architecture/container.md:82:    Rel(session, export, "Emits on session-end [P1 schema]")
docs/architecture/container.md:106:  Enforces `ADR-ARCH-003` (async write-back at session-end boundary).
docs/architecture/ARCHITECTURE.md:148:| **Phase 1** | 25 April – 11 May 2026 | Graphiti student model, DeepAgents Player-Coach harness, Session Planner, async session-end write-back, RAG retrieval |
docs/architecture/ARCHITECTURE.md:158:| ADR-ARCH-003 | Async Graphiti write-back at session-end boundary | Accepted |
docs/architecture/ARCHITECTURE.md:173:| ADR-ARCH-018 | Extend cross-cutting concerns with SR-08 (Graphiti async write-back) and SR-09 (runtime LLM parameters explicit) | Accepted (supersedes ADR-ARCH-009) |
docs/design/contracts/API-tutoring.md:119:| Classification | **sync** (Phase 0); P1 adds an async Graphiti write-back inside the handler — does not change the classification because the write is fire-and-forget |
docs/design/contracts/API-tutoring.md:133:**Phase 1 evolution:** TODO comment at `adapter.py:122` — async Graphiti write-back per ADR-ARCH-003. SR-07 invariant: this side effect must **not** appear in the tool description (kept implementation-internal).
docs/design/events-schema.yaml:185:    Single-user posture (ADR-ARCH-014) plus async Graphiti write-back at
docs/design/events-schema.yaml:186:    session-end (ADR-ARCH-003) make heavy delivery guarantees unnecessary.
docs/planning/feature-roadmap.md:74:| **FEAT-PH1-001** Graphiti Student Model | Student Model | ADR-ARCH-003 (async write-back), ADR-ARCH-007 (split topology), CC-11 (events bus) | `session.started`, `session.turn_completed`, `session.completed` |
docs/planning/feature-roadmap.md:81:- **SR-08** Graphiti write-back asynchrony — session-end write must not block `tutor_session_end` reply.
docs/planning/feature-roadmap.md:100:/feature-spec "Graphiti Student Model — schema, seeding, query helpers, async write-back at session-end" \
docs/planning/feature-roadmap.md:102:  --context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
docs/planning/feature-roadmap.md:133:| **FEAT-PH2-002** Static HTML Dashboard via Claude Design | Reporting (cross-context) | Reads `session-export.json` produced at Phase 1 session-end. Pure static HTML. |
docs/gamification/design.md:482:All state changes are atomic at the session-end boundary. Within-session

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ DOWNSTREAM IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Superseding ADR-ARCH-003 (session-end-only) with ADR-ARCH-019 (every-write-point) affects:

Architecture (will be flagged stale, updated in this run):

docs/architecture/ARCHITECTURE.md:148 — "session-end write-back" in Phase 1 description
docs/architecture/ARCHITECTURE.md:158 — ADR index entry (will mark superseded)
docs/architecture/container.md:30 — MCP Adapter description
docs/architecture/container.md:38 — Coach AsyncSubAgent annotation
docs/architecture/container.md:74 — Coach → student_model relationship label
docs/architecture/container.md:82 — Session → export relationship label
docs/architecture/container.md:106 — explicit "Enforces ADR-ARCH-003" reference
docs/architecture/domain-model.md:338, 443, 466, 489 — session-end-only framing
Design (flagged stale only — updated by /system-design next run):

docs/design/README.md:70 — references ADR-ARCH-003 for async events bus
docs/design/contracts/API-tutoring.md:119, 133 — fire-and-forget classification rows
docs/design/events-schema.yaml:185-186 — session-end reference
Planning (flagged stale only — updated when FEAT-PH1-001 is re-spec'd):

docs/planning/feature-roadmap.md:74, 81, 100-102 — FEAT-PH1-001 dependency + SR-08 row
docs/gamification/design.md:482 — "atomic at session-end boundary" claim
Cross-references (informational only — left unchanged):

ADR-ARCH-002, ADR-ARCH-007, ADR-ARCH-012, ADR-ARCH-017 — reference ADR-ARCH-003 in Related sections; standard supersede chain handles forward navigation
ADR-ARCH-018 — already documents ADR-ARCH-003 staleness (predicted this refinement); leave intact
C4 re-review gate: Topology is unchanged — same containers, same relationships. Only label text inside the existing diagram changes ("at session-end" → general async). The mandatory C4 re-review gate is therefore not triggered (Phase 6 condition: "if structure changed"); I will refresh the affected description strings inside container.md as part of in-place updates rather than regenerating diagrams.

Impact scope summary: 1 ADR superseded, 1 ADR created, 3 architecture files updated in-place, 5 design/planning files flagged stale.

Proceeding with apply (taking the user's invocation, the explicit ARCH-018 forecast that ARCH-003 needed this refinement, and the rich --context evidence as approval). I will note where I'm assuming approval rather than blocking on input.

Read ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
Applying changes now. Starting with marking ADR-ARCH-003 as superseded.

Edit ADR-ARCH-003-async-graphiti-writeback.md
Added 1 line
Now creating ADR-ARCH-019.

Write ADR-ARCH-019-async-graphiti-writeback-every-write-point.md
107 lines
# ADR-ARCH-019 — Async Graphiti write-back at every write point in the tutor

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1
**Supersedes:** [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — Async Graphiti write-back at session-end boundary
**Related:** [ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-13), [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) (`AsyncSubAgent`), [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) (sync read path), [ADR-ARCH-002](ADR-ARCH-002-three-layer-architecture.md), CC-08, SR-08, [phase-1-scope.md §SR-08](../../research/ideas/phase-1-scope.md), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md), DEC-02, DEC-08.

## Context

ADR-ARCH-003 committed to async Graphiti write-back **at the session-end boundary only**, with mid-session work batched in the in-process `TutorSession` aggregate. That commitment was sized against DEC-08's assumed Graphiti latency of 1–3s per `add_episode` (Gemini extraction era), and against a single Phase-1 write site (`tutor_session_end`).

Two pieces of evidence have arrived since ARCH-003 was accepted (2026-04-18):

1. **The 2026-04-27 Graphiti latency spike** ([graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)) measured the post-21-Apr vLLM-on-GB10 stack and found:

   | Operation | Median (s) |
   |---|---:|
   | `add_episode` | **78.98** |
   | `search_nodes` | 0.07 |
   | `search_memory_facts` | 0.08 |

   `add_episode` median is **78.98s** — ~15× the 5s SR-08 trigger threshold from `phase-1-scope.md` and ~26× the high end of the original DEC-08 1–3s assumption. CC-08's "fire-and-forget + poll above 30s" rule applies to *every* such write, not just the session-end boundary. Read-path latencies (`search_nodes` / `search_memory_facts` at ~0.07s) are unaffected and continue to satisfy the sync classification of `tutor_start_session` per ADR-ARCH-017.

2. **[ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) promoted SR-08 to a load-bearing cross-cutting concern (CC-13)** and explicitly flagged ADR-ARCH-003 as too narrow:

   > ADR-ARCH-003 is a *single-write-point* decision (session-end boundary). The latency spike shows write-back must apply at *every* write point, which is a cross-cutting concern, not a session-boundary policy. ADR-ARCH-003 will need its own follow-up `/arch-refine` to broaden its scope (flagged stale by this ADR; not modified here). — ARCH-018 §Alternatives considered.

ARCH-019 is that follow-up. It broadens the architectural commitment so the cross-cutting concern (CC-13) and the async-write-back ADR are coextensive, removing a contradiction inside `docs/architecture/`.

## Decision

Graphiti write-back is **async-from-caller at every write point in the tutor**, not only at the session-end boundary. The architecture commitment is:

- **Every** Graphiti `add_episode` / entity-update site goes through a helper that runs the work as a background task. Approved mechanisms:
  - `deepagents.AsyncSubAgent` (per [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md)) for write paths the Coach owns or where launch/check/cancel/list semantics are useful.
  - `asyncio.create_task` for simpler one-shot writes that don't need the deepagents tool surface.
- **Caller-facing handlers do not await Graphiti acknowledgement.** Specifically:
  - `tutor_session_end` returns within < 2s regardless of session-end episode write latency.
  - `tutor_turn` retains its p95 < 10s budget — any per-turn or mid-session write (e.g. Coach-observed misconceptions, planner topic-confidence updates) is fire-and-forget.
  - `tutor_start_session` retains its sync < 1s classification (ADR-ARCH-017); its warm-up was already fire-and-forget and is unaffected.
- **Write failures are logged-only.** A failed background `add_episode` emits a structured log line; it does **not** raise from the MCP handler, does **not** retry synchronously on the caller-facing path, and does **not** surface to the student. Fail-soft degradation, consistent with ARCH-003's original posture but now applied at every write point.
- **Within-session state still lives in the in-process `TutorSession` aggregate.** What changes is that the *flush points* are no longer constrained to session-end: any flush point may be introduced by a Phase 1 feature (e.g. the Planner topic-confidence updater, the Coach misconception logger), and every such flush point follows the same fire-and-forget shape.
- **Single-process / single-user posture is unchanged** ([ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md)). No worker process, no out-of-process queue. Background tasks run inside the tutor's asyncio loop.

This decision is the architecture-level corollary of CC-13 (ARCH-018). CC-13 sets the rule for cross-cutting compliance audits; ARCH-019 records the architectural commitment so the chain of evidence (latency spike → CC-13 → architecture decision) is explicit in `docs/architecture/`.

## Alternatives considered

- **Leave ARCH-003 as-is and rely solely on CC-13 (ARCH-018) for the broader rule.** Rejected. ARCH-018 itself flagged ARCH-003 as needing this refinement. Leaving the architecture decision at "session-end only" while the cross-cutting concern says "every write point" creates a permanent contradiction inside `docs/architecture/`; future readers and `/feature-spec` runs would have to reconcile the two, and the contradiction would be a recurring source of drift.
- **Per-turn synchronous writes for "small" updates (e.g. Coach misconceptions or topic-confidence deltas).** Rejected. The 78.98s median is for *any* `add_episode`; there is no measured cheap-write path on the current FalkorDB + vLLM stack. Differentiating "small" vs "session" writes would require a per-payload latency model that we do not have, and would re-introduce SR-08 violations at the per-turn boundary (CC-08 / 30s threshold).
- **Buffer all mid-session writes and flush at session-end (a generalisation of ARCH-003).** Rejected for Phase 1. Adds session-scoped buffering machinery and concentrates the cost into a single fat session-end flush; with `add_episode` at 78.98s and a multi-write batch, the session-end task could run for several minutes. Fire-and-forget at each write point spreads the cost across the session and matches CC-13's "uniform shape across write sites" requirement.
- **Move Graphiti writes onto a separate worker process / queue.** Considered. Deferred — out of Phase 1 scope (single-user, single-process tutor per ADR-ARCH-014). Revisit if the multi-user posture changes or if the tutor process's asyncio loop becomes congested with background writes; neither is on the Phase 1 path.
- **Wait for a faster Graphiti stack (alternative graph store, smaller LLM for extraction) before broadening.** Rejected. ARCH-019 is a *correctness* fix relative to CC-13, not a performance optimisation. Even a 10× faster stack (still ~8s `add_episode`) would breach CC-08 / SR-08 if awaited on the caller path. The architectural rule should not depend on the absolute latency number.

## Consequences

**Positive:**
- Architecture decision now coextensive with CC-13. No contradiction between an async-write-back ADR and the cross-cutting concerns set.
- Every Graphiti write site has a uniform fire-and-forget shape, routed through one helper or `AsyncSubAgent` pattern. Easier to audit Phase 1 features against a single rule.
- `tutor_turn` p95 < 10s and `tutor_session_end` < 2s remain achievable even with `add_episode` median at 78.98s, because no caller-facing path awaits Graphiti.
- Removes a guaranteed future SR-08 violation: the prior ARCH-003 wording could have been read as licensing a synchronous mid-session write at some later feature (e.g. a "live" Coach misconception update). ARCH-019 closes that escape hatch.
- The 78.98s measurement is now load-bearing in two architecture artefacts (ARCH-018 / CC-13 and ARCH-019), not just a research note. Future readers see the same evidence from both the cross-cutting and per-decision angles.

**Negative:**
- Background-task bookkeeping now appears at multiple sites in the tutor, not just session-end. Mitigated by routing all sites through one helper (or `AsyncSubAgent`); no per-site bespoke code expected.
- A tutor crash now risks losing in-flight writes from any write point, not just the one session-end batch. Acceptable for Phase 1 MVP (single-user, no concurrent sessions; demo-window crash recovery is not load-bearing); revisit if real crashes appear during Phase 1 testing.
- ADR-ARCH-003 remains queryable as the historical session-end-only decision; readers must follow `superseded_by` to ARCH-019. Standard cost of temporal superseding.
- Three downstream architecture artefacts (`ARCHITECTURE.md`, `container.md`, `domain-model.md`) carry session-end-only language and are updated in this run; five design/planning artefacts are flagged stale and will be picked up by `/system-design` and `/feature-spec` on next run.

## Downstream artefacts flagged stale

The following artefacts reference the previous (session-end-only) framing and will be updated either in this run or by the next `/system-design` / `/feature-spec` pass:

**Updated in-place by this `/arch-refine`:**
- `docs/architecture/ARCHITECTURE.md` §"Phase 1" row and ADR index — Phase 1 description and ADR-ARCH-003 / ADR-ARCH-019 status entries.
- `docs/architecture/container.md` — MCP Adapter description, Coach AsyncSubAgent annotation, Coach → student_model relationship, Session → export relationship, "Enforces ADR-ARCH-003" reference.
- `docs/architecture/domain-model.md` §7.1 (`tutor_session_end` row) and §7.4 (write-back narrative + diagram caption).

**Flagged stale only — picked up by next `/system-design` / `/feature-spec`:**
- `docs/design/README.md` line 70 — references ADR-ARCH-003 for async events bus consistency.
- `docs/design/contracts/API-tutoring.md` lines 119, 133 — fire-and-forget classification rows still cite ADR-ARCH-003 explicitly.
- `docs/design/events-schema.yaml` lines 185–186 — references ADR-ARCH-003 session-end framing.
- `docs/planning/feature-roadmap.md` lines 74, 81, 100–102 — FEAT-PH1-001 dependency cites ADR-ARCH-003; SR-08 row uses session-end-only language; `/feature-spec` invocation hint references the old ADR file.
- `docs/gamification/design.md` line 482 — "atomic at session-end boundary" claim is too strong under ARCH-019 (writes are fire-and-forget at every point; atomicity is per-write, not session-scoped).

ADR-ARCH-003 itself remains queryable as the historical session-end-only decision; only its `Status` is updated to `superseded`. No content rewrite of ARCH-003.

## C4 diagram re-review status

System topology is **unchanged** by this refinement: same containers (MCP Adapter, Tutor Player, Coach AsyncSubAgent, Session Aggregate, Graphiti, Export channel), same external systems, same relationships. What changes is the *label text* on existing relationships (e.g. "writes confidence delta [P1 on session-end]" → "writes confidence delta [P1, async fire-and-forget]"). The mandatory C4 re-review gate is therefore not triggered; affected description strings inside `container.md` are refreshed in-place.

## References

- [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — superseded predecessor (session-end boundary only).
- [ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — promoted SR-08 to CC-13 and forecast this refinement.
- [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) — `AsyncSubAgent` mechanism for CC-13 conformance.
- [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) — sync read-path classification corroborated by `search_nodes` 0.07s in the same spike.
- [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) — single-user, single-process posture (constrains "no worker process" in this ADR).
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — measured Graphiti latency, 2026-04-27.
- [phase-1-scope.md](../../research/ideas/phase-1-scope.md) §SR-08 — origin of the every-write-point requirement.
- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md` — original Gemini-era latency assumptions, now superseded by the 2026-04-27 measurement.
- LES1 §4 — `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` — fire-and-forget cross-agent rule (CC-08 origin).
Now updating the architecture index, container.md, and domain-model.md.

Read ARCHITECTURE.md (lines 141-185)
Edit ARCHITECTURE.md
Modified
Edit ARCHITECTURE.md
Modified
Edit ARCHITECTURE.md
Added 1 line
Now updating container.md to remove session-end-only labels.

Read container.md (lines 2-121)
Edit container.md
Modified
Edit container.md
Modified
Edit container.md
Modified
Edit container.md
Modified
Edit container.md
Added 1 line
Now updating domain-model.md.

Read domain-model.md (lines 326-500)
Edit domain-model.md
Modified
Edit domain-model.md
Added 1 line
Edit domain-model.md
Added 2 lines
Edit domain-model.md
Added 3 lines
Now verifying the changes look coherent and running the seeding step.

Bash Verify in-place updates landed correctly
IN
grep -n "ADR-ARCH-003\|ADR-ARCH-019\|session-end" docs/architecture/ARCHITECTURE.md docs/architecture/container.md docs/architecture/domain-model.md 2>/dev/null

OUT
docs/architecture/domain-model.md:338:| `tutor_session_end` | sync — triggers async Graphiti write-back (P1, fire-and-forget per CC-13 / ADR-ARCH-019) | < 2s |
docs/architecture/domain-model.md:444:                   (CC-13 / ADR-ARCH-019); not deferred to session-end
docs/architecture/domain-model.md:468:write point. This is deliberate (ADR-ARCH-019, broadens ADR-ARCH-003;
docs/architecture/domain-model.md:492:write responsibilities — and under ADR-ARCH-019 / CC-13 the writes are
docs/architecture/domain-model.md:493:async fire-and-forget at every point, not concentrated at a session-end
docs/architecture/container.md:30:        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools, all sync per SR-07 (ADR-ARCH-017): tutor_start_session (sync; warm-up fire-and-forget), tutor_turn (sync; mid-session Graphiti writes fire-and-forget per CC-13), tutor_session_status (sync), tutor_session_end (sync; session-end Graphiti write fire-and-forget per CC-13 / ADR-ARCH-019).")
docs/architecture/container.md:38:            Container(coach, "Coach (AsyncSubAgent)", "Python / deepagents AsyncSubAgent", "Quality monitor — async off hot path. Writes confidence deltas and misconception logs fire-and-forget at every observation point per CC-13 / ADR-ARCH-019. [P1]")
docs/architecture/container.md:82:    Rel(session, export, "Emits at session-end [P1 schema; export channel is local file write, not a Graphiti write]")
docs/architecture/container.md:106:  Enforces `ADR-ARCH-019` (async write-back at every Graphiti write point;
docs/architecture/container.md:107:  supersedes `ADR-ARCH-003`'s session-end-only framing) and CC-13.
docs/architecture/ARCHITECTURE.md:148:| **Phase 1** | 25 April – 11 May 2026 | Graphiti student model, DeepAgents Player-Coach harness, Session Planner, async Graphiti write-back at every write point (ADR-ARCH-019 / CC-13), RAG retrieval |
docs/architecture/ARCHITECTURE.md:158:| ADR-ARCH-003 | Async Graphiti write-back at session-end boundary | Superseded by ADR-ARCH-019 |
docs/architecture/ARCHITECTURE.md:174:| ADR-ARCH-019 | Async Graphiti write-back at every write point in the tutor (broadens ADR-ARCH-003 per CC-13) | Accepted (supersedes ADR-ARCH-003) |
Bash Verify new ADR file exists
IN
ls docs/architecture/decisions/ADR-ARCH-019-* 2>&1

OUT
docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md
All in-place updates landed cleanly. Now Graphiti seeding.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌱 GRAPHITI SEEDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tier 1 check passed (.guardkit/graphiti.yaml has enabled: true). The add_episode median is 78.98s per the latency spike — which is exactly the rule ARCH-019 is encoding — so I will offer the seeding commands for explicit user execution rather than running them inline (a minutes-long block in this command is precisely what CC-13 says to avoid).

Recommended seeding commands (run when convenient — they will block for several minutes per the latency spike):


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --group architecture_decisions
Staleness flagging: the design / planning artefacts listed in the impact analysis are recorded inside ADR-ARCH-019's "Downstream artefacts flagged stale" section (matching ARCH-018's pattern); /system-design and /feature-spec will pick them up on next run. I did not invoke arch_sp.update_entity_metadata(...) programmatically because a) the /arch-refine command spec describes that as a Graphiti API call requiring runtime SDK access from the command harness (not directly available in this session), and b) the ARCH-019 markdown surface is the canonical staleness record that downstream commands read.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DECISION REFINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ADR-ARCH-003: Status changed to "Superseded by ADR-ARCH-019"
  ADR-ARCH-019: Created (supersedes ADR-ARCH-003)
                Scope: async Graphiti write-back at every write point
                Evidence: 2026-04-27 latency spike — add_episode median 78.98s
                CC anchor: CC-13 (ARCH-018)
Updated files (in-place):

docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md — status → superseded
docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md — new
docs/architecture/ARCHITECTURE.md:148, 158, 174 — Phase 1 description, index entries
docs/architecture/container.md:30, 38, 74, 82, 106-107 — labels and explanatory note
docs/architecture/domain-model.md:338, 443-444, 466-468, 492-494 — write-back semantics
Flagged stale (recorded in ADR-ARCH-019; not modified in this run):

docs/design/README.md line 70 · docs/design/contracts/API-tutoring.md lines 119, 133 · docs/design/events-schema.yaml lines 185-186 · docs/planning/feature-roadmap.md lines 74, 81, 100-102 · docs/gamification/design.md line 482
C4 re-review: Not triggered — topology unchanged (same containers, same relationships); only label text on existing relationships was refreshed in-place.

Next steps:

Run the two guardkit graphiti add-context commands above to seed the architecture_decisions group.
Run /system-design — it will detect and report the design-artefact staleness flags listed in ARCH-019.
When /feature-spec for FEAT-PH1-001 runs, point it at ADR-ARCH-019 (not ARCH-003) and let it pick up the broadened scope for Coach misconception logging and Planner topic-confidence updates.
<task-notification>
<task-id>b9wp7k3eq</task-id>
<tool-use-id>toolu_012ySLb8nrWArom3nvdqEhWQ</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/b9wp7k3eq.output</output-file>
<status>failed</status>
<summary>Background command "Seed superseded ADR-ARCH-003 to Graphiti" failed with exit code 2</summary>
</task-notification>
<task-notification>
<task-id>bzn75exoc</task-id>
<tool-use-id>toolu_01UuZKWJFuGqrnDJccNGaV4h</tool-use-id>
<output-file>/private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/bzn75exoc.output</output-file>
<status>failed</status>
<summary>Background command "Seed new ADR-ARCH-019 to Graphiti" failed with exit code 2</summary>
</task-notification>
command-history.md
please can you run the Graphiti seeding commands
Running both seeding commands in parallel. Per the latency spike each add_episode runs ~78s median (max ~134s), so I'm setting a generous timeout.

Bash Seed superseded ADR-ARCH-003 to Graphiti
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md --group architecture_decisions 2>&1

OUT
Command running in background with ID: b9wp7k3eq. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/b9wp7k3eq.output
Bash Seed new ADR-ARCH-019 to Graphiti
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md --group architecture_decisions 2>&1

OUT
Command running in background with ID: bzn75exoc. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/bzn75exoc.output
The first seeding command failed quickly (exit 2). Let me read the output to diagnose.

Read b9wp7k3eq.output
The CLI doesn't accept --group (the syntax in the /arch-refine template is out of date for this project's guardkit build). Let me check the actual help.

Bash Check guardkit graphiti add-context help
IN
guardkit graphiti add-context --help 2>&1

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
The --group flag doesn't exist in this CLI build — group_id is inferred by parser type. The right invocation is --type adr with a generous per-episode timeout (latency spike median was 78s, max 134s).

Bash Seed superseded ADR-ARCH-003 to Graphiti
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md --type adr --force --verbose --timeout 300 2>&1

OUT
Command running in background with ID: bmv1np5l2. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/bmv1np5l2.output
Bash Seed new ADR-ARCH-019 to Graphiti
IN
guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md --type adr --verbose --timeout 300 2>&1

OUT
Command running in background with ID: b2nnenv51. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/95c9a141-51e0-4b39-8bb6-506a8b4e519c/tasks/b2nnenv51.output
Both seeding commands launched in background. Per the latency spike, each add_episode runs ~78–134s. I'll await the completion notifications.

Read bmv1np5l2.output
First seeding completed successfully — ADR-ARCH-003 (superseded) is in Graphiti with 7 nodes / 3 edges in 113s. Awaiting ARCH-019.

Read b2nnenv51.output
Both seedings completed successfully.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ GRAPHITI SEEDING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADR	Status	Episode	Nodes	Edges	add_episode time
ADR-ARCH-003	superseded	adr_adr-arch-003-async-graphiti-write-back-at-session-end-boundary	7	3	113.14s
ADR-ARCH-019	accepted	adr_adr-arch-019-async-graphiti-write-back-at-every-write-point-in-the-tutor	10	14	152.56s
Both ADRs are now queryable in the FalkorDB knowledge graph (group architecture_decisions). The 14 edges on ARCH-019 reflect its dense reference set (CC-13, ARCH-018, ARCH-012, ARCH-017, ARCH-014, ARCH-002, latency spike, phase-1-scope, etc.) — the chain of evidence is now navigable in Graphiti.

Live measurements (113s and 152s) confirm the latency-spike numbers and the architectural premise of ARCH-019 — these write times would have blown any caller-facing budget if awaited synchronously.


command-history.md
please update the status in the build plan
Locating the build plan(s) and identifying what status entries reference ADR-ARCH-003 / async write-back / CC-13.

Bash Find references to async write-back / CC-13 in build plans
IN
grep -n "ADR-ARCH-003\|ADR-ARCH-018\|ADR-ARCH-019\|SR-08\|CC-13\|async.*write-back\|async.*writeback\|session-end" docs/research/ideas/phase-0-build-plan.md docs/research/ideas/phase-1-build-plan.md 2>&1 | head -80

OUT
docs/research/ideas/phase-0-build-plan.md:5:## Status: **In-flight — weekend code work complete; close-out gates pending. /arch-refine D2 closed 27 Apr (ADR-ARCH-017). Graphiti latency spike DONE 27 Apr — SR-08 elevated to CRITICAL; ARCH-017 sync classification confirmed with massive margin.**
docs/research/ideas/phase-0-build-plan.md:61:   - **SR-08 (async write-back): CRITICAL, not defensive.** At 79s median per write, a synchronous `add_episode` at session-end would make the student wait over a minute for `tutor_session_end` to return. Pattern per `phase-1-scope.md` L83: fire-and-forget from multiple write points (session-end, misconception-observed during turns, Coach confidence-delta proposals), not a single session-end batch. Next: bundle SR-08 (+ SR-09) into one `/arch-refine`, likely refining ADR-ARCH-009 (six → eight parity surfaces).
docs/research/ideas/phase-0-build-plan.md:447:  --context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
docs/research/ideas/phase-1-build-plan.md:33:7. Six parity surfaces still green (SR-01..SR-07); SR-08 (async write-back) and **SR-09 (runtime LLM param assertion)** established
docs/research/ideas/phase-1-build-plan.md:103:   Record results in `docs/research/ideas/graphiti-latency-spike-results.md`. Two paragraphs plus the measurements table. Decision statements: "add_episode median = Xs, so SR-08 async write-back is [critical / defensive only]." "search_nodes median = Ys, so tutor_start_session stays [long-running / can be reclassified sync]."
docs/research/ideas/phase-1-build-plan.md:194:   - If score < 0.7 and max retries exhausted: emit lowest-scoring reply with a silent log marker, flag for session-end review
docs/research/ideas/phase-1-build-plan.md:196:8. **Implement `_end_tutor_session`.** On session end: generate session summary, write `session_completed` episode to Graphiti asynchronously per SR-08. Return summary to MCP caller immediately.
docs/research/ideas/phase-1-build-plan.md:321:/feature-spec "Graphiti Student Model — entities, relationships, episodes, query helpers, seeding script, async write-back" \
docs/research/ideas/phase-1-build-plan.md:340:/feature-spec "DeepAgents Tutoring Loop with Coach — Player-Coach integration, Coach rubric, session-end summary, async Graphiti write-back" \
docs/research/ideas/phase-1-build-plan.md:412:| Graphiti latency spike shows multi-second writes blocking tutoring | Medium | High | SR-08 makes write-back fire-and-forget; spike just informs which path within that |
Read phase-0-build-plan.md (lines 2-91)
Read phase-0-build-plan.md (lines 436-460)
Three status updates needed in phase-0-build-plan.md:

Edit phase-0-build-plan.md
Modified
Edit phase-0-build-plan.md
Modified
Edit phase-0-build-plan.md
Added 1 line
Now checking the phase-1 build plan for similar status updates.

Read phase-1-build-plan.md (lines 2-51)
Read phase-1-build-plan.md (lines 91-310)
Read phase-1-build-plan.md (lines 309-428)
The phase-1 build plan also has a status line and a relevant success-criterion that should reflect the new state.

Edit phase-1-build-plan.md
Modified
Edit phase-1-build-plan.md
Modified
Edit phase-1-build-plan.md
Modified
Verifying both build plans now read coherently.

Bash Verify status updates in both build plans
IN
grep -n "Status:\|ADR-ARCH-018\|ADR-ARCH-019\|CC-13\|CC-14\|SR-08\|SR-09" docs/research/ideas/phase-0-build-plan.md docs/research/ideas/phase-1-build-plan.md 2>&1 | head -40

OUT
docs/research/ideas/phase-1-build-plan.md:5:## Status: Pre-execution prerequisites partially landed (2026-04-27). Graphiti latency spike DONE — `add_episode` median 78.98s, `search_nodes` 0.07s ([graphiti-latency-spike-results.md](./graphiti-latency-spike-results.md)). Architecture cross-cutting concerns extended: ADR-ARCH-018 (SR-08 → CC-13, SR-09 → CC-14, six → fourteen parity surfaces) and ADR-ARCH-019 (async Graphiti write-back at every write point; supersedes ADR-ARCH-003) accepted and seeded into `architecture_decisions`. Saturday-morning latency spike + Phase 0 validation gate items in this plan are partially pre-completed; remaining: Phase 0 validation gate write-up, then proceed to FEAT-PH1-001 schema work.
docs/research/ideas/phase-1-build-plan.md:33:7. Six parity surfaces still green (SR-01..SR-07); SR-08 (async write-back) and **SR-09 (runtime LLM param assertion)** established. _Architecture-level establishment DONE 2026-04-27_ via ADR-ARCH-018 (CC-13 / CC-14 promotion) and ADR-ARCH-019 (async write-back broadened to every Graphiti write point). Phase 1 work that remains: structural conformance — every Graphiti write site routed through a fire-and-forget helper (CC-13), and CC-14 smoke tests landing per Modelfile change.
docs/research/ideas/phase-1-build-plan.md:103:   Record results in `docs/research/ideas/graphiti-latency-spike-results.md`. Two paragraphs plus the measurements table. Decision statements: "add_episode median = Xs, so SR-08 async write-back is [critical / defensive only]." "search_nodes median = Ys, so tutor_start_session stays [long-running / can be reclassified sync]."
docs/research/ideas/phase-1-build-plan.md:196:8. **Implement `_end_tutor_session`.** On session end: generate session summary, write `session_completed` episode to Graphiti via the fire-and-forget helper per CC-13 / ADR-ARCH-019 (every Graphiti write point is async-from-caller; failures logged-only). Return summary to MCP caller immediately. Note: under ADR-ARCH-019 the same helper is used by mid-session writes (e.g. `misconception_observed` from the Coach loop, planner topic-confidence updates) — not just here.
docs/research/ideas/phase-1-build-plan.md:387:| `tests/smoke/test_ollama_runtime_params.py` | SR-09 | NEW (asserts num_ctx and num_predict reach runner) |
docs/research/ideas/phase-1-build-plan.md:412:| Graphiti latency spike shows multi-second writes blocking tutoring | Medium | High | SR-08 makes write-back fire-and-forget; spike just informs which path within that |
docs/research/ideas/phase-0-build-plan.md:5:## Status: **In-flight — weekend code work complete; close-out gates pending. /arch-refine D2 closed 27 Apr (ADR-ARCH-017). Graphiti latency spike DONE 27 Apr — SR-08 elevated to CRITICAL; ARCH-017 sync classification confirmed with massive margin. SR-08 bundled `/arch-refine` DONE 27 Apr — ADR-ARCH-018 promotes SR-08 → CC-13 and SR-09 → CC-14 (six → fourteen parity surfaces); ADR-ARCH-019 broadens async write-back from session-end-only to every Graphiti write point. Both ADRs seeded into `architecture_decisions`.**
docs/research/ideas/phase-0-build-plan.md:61:   - **SR-08 (async write-back): CRITICAL, not defensive.** At 79s median per write, a synchronous `add_episode` at session-end would make the student wait over a minute for `tutor_session_end` to return. Pattern per `phase-1-scope.md` L83: fire-and-forget from multiple write points (session-end, misconception-observed during turns, Coach confidence-delta proposals), not a single session-end batch. ✅ **CLOSED 2026-04-27** — bundled `/arch-refine` ran in two passes: (a) ADR-ARCH-018 supersedes ADR-ARCH-009, promoting SR-08 → CC-13 and SR-09 → CC-14 (six → fourteen load-bearing CCs); (b) ADR-ARCH-019 supersedes ADR-ARCH-003, broadening async Graphiti write-back from session-end-only to every Graphiti write point in the tutor (session-end episode, mid-session misconception logs, Coach confidence-delta proposals, planner topic-confidence updates — all fire-and-forget; failures logged-only). Architecture artefacts (ARCHITECTURE.md, container.md, domain-model.md) updated in-place; design / planning artefacts flagged stale in ARCH-019's Downstream artefacts section for `/system-design` and `/feature-spec` to pick up. Both ADRs seeded into Graphiti `architecture_decisions` (live `add_episode` times: ARCH-003-superseded 113s; ARCH-019 153s — empirically reconfirms the 79s median's order of magnitude, in line with CC-13's premise).
docs/research/ideas/phase-0-build-plan.md:447:  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
docs/research/ideas/phase-0-build-plan.md:448:  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
All status updates landed coherently across both build plans.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ BUILD PLAN STATUS UPDATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
docs/research/ideas/phase-0-build-plan.md:

Line 5 (top status header) — extended to record SR-08 bundled /arch-refine complete (ARCH-018 + ARCH-019)
Line 61 (punch-list item 8 → "Decisions unblocked" → SR-08) — marked ✅ CLOSED with both ADR outcomes and the live seeding times (113s / 153s)
Line 447–448 (Phase 1 /system-design --focus="Student Model" invocation) — swapped ADR-ARCH-003 reference for ADR-ARCH-019 + added ADR-ARCH-018 as context
docs/research/ideas/phase-1-build-plan.md:

Line 5 (status) — replaced "Ready to execute" with current pre-execution-prerequisites state: latency spike done, ARCH-018/019 accepted and seeded
Line 33 (Success Criterion 7) — annotated to record architecture-level SR-08 / SR-09 establishment is done; remaining Phase 1 work is structural conformance + smoke tests
Line 196 (_end_tutor_session implementation step) — updated to reference CC-13 / ADR-ARCH-019 and note that the fire-and-forget helper covers mid-session writes too, not just session-end
The status entries on lines 412 (risk-mitigation) and 321/340 (/feature-spec invocations) still use the SR-08 shorthand, which is correct — SR-08 is the parity-surface name, CC-13 is its load-bearing CC code; both still resolve to the same rule. Left untouched to avoid noise.