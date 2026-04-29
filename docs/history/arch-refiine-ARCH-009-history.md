
/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md


I'll start the architecture decision refinement targeting ADR-ARCH-009. Let me load the ADR and context files in parallel.

Bash Find ADR-ARCH-009 file
IN
ls docs/architecture/decisions/ADR-ARCH-009*

OUT
docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
Read graphiti.yaml
Read graphiti-latency-spike-results.md
Read phase-1-scope.md
Read ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
I have the target ADR loaded along with both context files. Let me check the architecture index and related ADRs that reference SR-08/SR-09 to understand how the cross-cutting concerns are currently structured.

Read ARCHITECTURE.md
Bash List all ADRs
IN
ls docs/architecture/decisions/

OUT
ADR-ARCH-001-ddd-structural-pattern.md
ADR-ARCH-002-three-layer-architecture.md
ADR-ARCH-003-async-graphiti-writeback.md
ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
ADR-ARCH-005-defer-dockerfile-to-phase-1.md
ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
ADR-ARCH-007-graphiti-split-topology.md
ADR-ARCH-008-mcp-only-agent-access.md
ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
ADR-ARCH-010-pydantic-at-boundary-validation.md
ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
ADR-ARCH-013-middleware-level-gamification-engine-future.md
ADR-ARCH-014-single-user-scalability-posture.md
ADR-ARCH-015-uk-on-device-data-residency.md
ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
ADR-ARCH-017-tutor-start-session-sync-classification.md
ADR-ARCH-009 is loaded — it currently elevates SR-01 through SR-07 plus CC-08 (fire-and-forget) to load-bearing cross-cutting concerns. The Phase 1 scope adds SR-08 (Graphiti write-back asynchrony) and SR-09 (Runtime LLM parameters explicit), and the latency spike confirms SR-08 is critical (add_episode median 78.98s — catastrophically over the 5s threshold).

Skipping disambiguation per --adr=ADR-ARCH-009. Proceeding to refinement Q&A.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 REFINING: ADR-ARCH-009 — Six parity surfaces (LES1) as load-bearing cross-cutting concerns
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current decision (summary):
  Context: LES1 documented six parity surfaces → SR-01–SR-07. Plus CC-08
           (fire-and-forget + poll above 30s).
  Decision: Promote to CC-01 through CC-08, first-class cross-cutting
           concerns, with per-feature checklist + parity tests.
  Status: Accepted (Phase 0, 2026-04-18)
Based on the two context files (graphiti-latency-spike-results.md and phase-1-scope.md), the refinement direction reads as:

Phase 1 scope adds two new SRs to the load-bearing set: SR-08 (Graphiti write-back asynchrony) and SR-09 (runtime LLM parameters explicit & asserted).
The latency spike confirms SR-08 is CRITICAL, not merely defensive — add_episode median 78.98s means async write-back is load-bearing at multiple write points (not just tutor_session_end per ADR-ARCH-003).
CC-08's framing in ARCHITECTURE.md ("fire-and-forget + poll above 30s") is now generic; with measured numbers, it specialises to a Graphiti-specific concern.
Before I capture the refinement, can you confirm the four inputs so I can proceed:

Q1. What has changed that requires refining this decision?
My read: Phase 1 scope introduces two additional structural requirements (SR-08, SR-09); the 27 Apr latency spike empirically confirms SR-08 is load-bearing (78.98s) and re-shapes CC-08 from a generic threshold rule into a Graphiti-specific async-write-back invariant. Confirm or correct?

Q2. What is the new decision?
My read: Extend the cross-cutting concerns set to include SR-08 (Graphiti write-back asynchrony — applied at every write point, not just session-end) and SR-09 (runtime LLM parameters — Modelfile num_ctx/num_predict explicit and asserted via smoke test). Map them as new CC codes that don't collide with the existing CC-09–CC-12 (safeguarding/copyright/event bus/async subagent boundary). Confirm or correct?

Q3. What alternatives were considered?
Candidates: (a) leave SR-08/SR-09 as Phase 1 scope-doc lore only; (b) inline the changes into ADR-ARCH-003 (async write-back) instead of refining ADR-ARCH-009; (c) supersede the SR series entirely with a new "LES1+Phase 1 lessons" combined ADR. Anything else to record as considered?

Q4. What are the consequences?
My read: every Phase 1 feature must honour SR-08/SR-09 structurally (write-back fire-and-forget at every Graphiti write point; Modelfile parameter smoke test in CI/manual); ADR-ARCH-003's "session-end boundary" framing becomes too narrow and will need follow-up refinement; CC numbering must accommodate two more codes without colliding with the existing CC-09–CC-12. Confirm or amend?

Please answer Q1–Q4 (or say "your read is correct" to accept my reads), and I'll proceed to impact analysis and ADR generation.

phase-0-build-plan.md
Q1: correct, Q2: correct, Q3:nothing further, Q4:confirm
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Determine if C4 diagram re-review is required (likely no — cross-cutting only)

Offer Graphiti seeding commands for both ADRs
Bash Find files referencing ADR-ARCH-009/CC-08/SR-08/SR-09
IN
grep -rln "ADR-ARCH-009\|CC-08\|SR-08\|SR-09" docs/ src/ 2>/dev/null | head -40

OUT
docs/research/ideas/phase-1-build-plan.md
docs/research/ideas/graphiti-latency-spike-results.md
docs/research/ideas/phase-2-scope.md
docs/research/ideas/cross-repo-rag-impact-analysis-2026-04-24.md
docs/research/ideas/phase-0-build-plan.md
docs/research/ideas/phase-1-scope.md
docs/design/contracts/API-mcp-transport.md
docs/planning/feature-roadmap.md
docs/design/models/DM-mcp-transport.md
docs/architecture/assumptions.yaml
docs/architecture/domain-model.md
docs/architecture/ARCHITECTURE.md
docs/architecture/decisions/ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
docs/history/command-history.md
docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
docs/history/system-arch-history.md
docs/history/system-design-phase-0-history.md
docs/history/system-plan-history.md
docs/reviews/architecture/claude-desktop-review-system-arch-output.md
Bash Find architecture artefacts directly referencing ADR-ARCH-009 or CC codes
IN
grep -ln "ADR-ARCH-009\|CC-08\b\|CC-09\b\|CC-10\b\|CC-11\b\|CC-12\b" docs/architecture/ docs/design/ -r 2>/dev/null

OUT
docs/architecture/domain-model.md
docs/architecture/ARCHITECTURE.md
docs/architecture/container.md
docs/architecture/assumptions.yaml
docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
docs/architecture/decisions/ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
docs/design/README.md
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
docs/design/contracts/API-tutoring.md
docs/design/events-schema.yaml
docs/design/contracts/API-mcp-transport.md
docs/design/contracts/API-inference-runtime.md
docs/design/models/DM-mcp-transport.md
Bash Check ADR-003 and ADR-017 for related content
IN
grep -n "SR-08\|SR-09\|CC-08\|fire-and-forget\|async.*write\|num_ctx\|num_predict" docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md 2>/dev/null

OUT
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:17:(CC-08 / LES1 row 10 ⚠️).
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:19:LES1 §4 (fire-and-forget + poll above 30s) explicitly flags this
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:48:  latency to every turn; violates p95 <10s and CC-08.
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:56:- **Per-turn async fire-and-forget (per turn).** Considered for
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:64:- Aligns with CC-08 and LES1 §4 prescriptions.
docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md:85:- deepagents 0.5.3 `AsyncSubAgent` — native fire-and-forget tool set
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md:16:1. **The Phase 0 implementation never satisfied the long-running protocol.** [src/study_tutor/mcp/adapter.py:49–68](../../../src/study_tutor/mcp/adapter.py) returns `{"session_id": "..."}` synchronously in well under 1s; the LLM warm-up runs as a fire-and-forget `asyncio.create_task`. There is no still-running task to poll, and no `_status`/`_cancel` companion tool exists. This is a current SR-07 violation: the registered tool description says "Long-running, returns session_id immediately" but the handler exposes none of the long-running protocol's affordances.
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md:33:| `tutor_start_session` | **sync** | < 1s; warm-up is fire-and-forget |
docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md:36:| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |
Bash Check domain-model, container, assumptions for direct refs
IN
grep -n "ADR-ARCH-009\|CC-08\|SR-08\|SR-09" docs/architecture/domain-model.md docs/architecture/container.md docs/architecture/assumptions.yaml 2>/dev/null

OUT
docs/architecture/assumptions.yaml:201:    related_adr: ADR-ARCH-009
docs/architecture/domain-model.md:324:transport-layer rules (SR-01, SR-02, SR-07, CC-08).
docs/architecture/domain-model.md:351:- **Long-running tools return a `session_id` in ≤1s** (CC-08 — LES1 §4
Bash Check downstream design artefacts
IN
grep -n "CC-08\|SR-08\|SR-09\|fire-and-forget\|async.*write" docs/design/contracts/API-mcp-transport.md docs/design/contracts/API-tutoring.md docs/design/contracts/API-inference-runtime.md docs/design/models/DM-mcp-transport.md docs/design/events-schema.yaml docs/design/README.md 2>/dev/null

OUT
docs/design/contracts/API-mcp-transport.md:12:MCP Transport is a **thin façade** owning the external protocol surface for AI agents. It enforces transport-layer invariants (SR-01 / SR-02 / SR-07 / CC-08) and turns the tutor into a discoverable, invokable system. The tools themselves and their behavioural contracts belong to **Tutoring** — see `API-tutoring.md`.
docs/design/contracts/API-mcp-transport.md:59:3. **Long-running tools return a tracking ID in ≤ 1s** (CC-08). P0 has none after [decision D2 (2026-04-26)](../../research/ideas/phase-0-build-plan.md) reclassified `tutor_start_session` as sync.
docs/design/contracts/API-mcp-transport.md:60:4. **Phase-1 background work uses deepagents AsyncSubAgent.** Hand-rolled `asyncio.create_task(...)` is acceptable for the Phase-0 warm-up case (warm-up is fire-and-forget, not user-observable), but the Coach (P1) **must** use AsyncSubAgent (CC-12) per ADR-ARCH-012.
docs/design/contracts/API-mcp-transport.md:73:| `tutor_session_end` | sync | `MCPAdapter.tutor_session_end` (P1: triggers async Graphiti write inside; classification unchanged) |
docs/design/contracts/API-tutoring.md:34:| Classification | **sync** (warm-up LLM call is fire-and-forget; not a polled task) |
docs/design/contracts/API-tutoring.md:119:| Classification | **sync** (Phase 0); P1 adds an async Graphiti write-back inside the handler — does not change the classification because the write is fire-and-forget |
docs/design/contracts/API-tutoring.md:133:**Phase 1 evolution:** TODO comment at `adapter.py:122` — async Graphiti write-back per ADR-ARCH-003. SR-07 invariant: this side effect must **not** appear in the tool description (kept implementation-internal).
docs/design/events-schema.yaml:185:    Single-user posture (ADR-ARCH-014) plus async Graphiti write-back at
docs/design/models/DM-mcp-transport.md:45:The closed set per SR-07. Adding a third class (e.g. `"streaming"`) is a contract change requiring `/design-refine` because it changes the latency-classification gate that underpins CC-08.
docs/design/models/DM-mcp-transport.md:85:| I-MCP5 | Sync tools complete in < 30s end-to-end; long-running tools return tracking ID in ≤ 1s | latency-band sampling; current adapter has no long-running tools after D2 (CC-08) |
docs/design/README.md:55:| **D2** | `tutor_start_session` classified **`sync`** (not `long-running`). | Live behaviour: returns `session_id` synchronously; warm-up is fire-and-forget, not a polled task. **Resolved 2026-04-27 by ADR-ARCH-017** (partially supersedes ADR-ARCH-008 SR-07 table); downstream artefacts (`domain-model.md §7.1`, `phase-0-scope.md §SR-07`, `container.md`, MCP adapter/server code) all updated. |
Bash Check container.md for refs
IN
grep -n "ADR-ARCH-009\|CC-08\|SR-08\|SR-09\|fire-and-forget" docs/architecture/container.md 2>/dev/null

OUT
30:        Container(mcp, "MCP Adapter", "Python / mcp SDK", "Registers 4 tools, all sync per SR-07 (ADR-ARCH-017): tutor_start_session (sync; warm-up fire-and-forget), tutor_turn (sync), tutor_session_status (sync), tutor_session_end (sync; async Graphiti write-back in P1).")
Read assumptions.yaml (lines 191-215)
Impact analysis complete. Here's the scope:


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ DOWNSTREAM IMPACT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Superseding ADR-ARCH-009 affects the following downstream artefacts:

ADRs (textually reference CC-08 / ADR-ARCH-009):
  ⚠️  docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md
       — frames CC-08 generically; will need follow-up refinement now
         that latency spike (78.98s) shows write-back must apply at
         multiple write points, not only session-end (out of scope here;
         flag as stale).
  ⚠️  docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
       — references CC-08; review only.
  ⚠️  docs/architecture/decisions/ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
       — references ADR-ARCH-009 only; review only.
  ⚠️  docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
       — references fire-and-forget; review only.

Architecture index / domain / containers:
  ⚠️  docs/architecture/ARCHITECTURE.md §6 — CC table (12 rows) needs
       SR-08 row updated + new SR-09 row, ADR index gets ADR-ARCH-018.
  ⚠️  docs/architecture/domain-model.md §324, §351 — CC-08 references.
  ⚠️  docs/architecture/container.md — CC-08-aligned tool descriptions.
  ⚠️  docs/architecture/assumptions.yaml ASSUM-012 — points at ADR-ARCH-009;
       update related_adr to ADR-ARCH-018.

Design contracts (will be flagged stale, not edited here):
  ⚠️  docs/design/contracts/API-mcp-transport.md — 4 CC-08 refs.
  ⚠️  docs/design/contracts/API-tutoring.md — fire-and-forget refs.
  ⚠️  docs/design/models/DM-mcp-transport.md — CC-08 in invariants table.
  ⚠️  docs/design/events-schema.yaml — async write-back ref.
  ⚠️  docs/design/README.md — D2 closure note.

Out of scope (no direct CC-08 / SR-08 / SR-09 dependence):
  ✓  C4 system-context.md / container.md structure unchanged — refining
     a cross-cutting concern does not add or remove containers / external
     systems. C4 re-review gate is NOT triggered.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan:

  1. Edit ADR-ARCH-009 in place: status → superseded, superseded_by →
     ADR-ARCH-018. Body unchanged so prior reasoning is preserved.
  2. Create ADR-ARCH-018 — extends LES1 cross-cutting concerns with
     SR-08 (Graphiti async write-back, confirmed CRITICAL by 27 Apr
     spike) and SR-09 (runtime LLM parameters explicit & asserted).
     New CC codes: CC-13 (SR-08 specialisation; CC-08 generalises) and
     CC-14 (SR-09). Avoids colliding with existing CC-09 through CC-12.
  3. Update ARCHITECTURE.md §6 (CC table grows 12→14) and §9 (ADR
     index gains ADR-ARCH-018; ADR-ARCH-009 row marked superseded).
  4. Update assumptions.yaml ASSUM-012 related_adr → ADR-ARCH-018.
  5. Flag stale: ADR-ARCH-003 (needs separate /arch-refine) and the
     5 design contracts (will be detected by /system-design).
  6. No C4 re-review (structure unchanged).
  7. Offer Graphiti seeding commands for both ADRs.

[A]pprove and apply changes
[R]evise the plan
[C]ancel
Approve to proceed?

[A]pprove
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Update assumptions.yaml ASSUM-012 related_adr

Offer Graphiti seeding commands for both ADRs
Edit ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
Added 1 line
Now create the new ADR-ARCH-018.

Write ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
96 lines
# ADR-ARCH-018 — Extend load-bearing cross-cutting concerns with SR-08 (Graphiti async write-back) and SR-09 (runtime LLM parameters explicit)

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1
**Supersedes:** [ADR-ARCH-009](ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md) — Six parity surfaces (LES1) as load-bearing cross-cutting concerns
**Related:** LES1, CC-01 through CC-08, CC-13, CC-14, ADR-ARCH-003, [phase-1-scope.md §SR-08 / §SR-09](../../research/ideas/phase-1-scope.md), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)

## Context

ADR-ARCH-009 promoted the six LES1 parity surfaces (SR-01 through SR-07) plus CC-08 ("fire-and-forget + poll above 30s") to first-class cross-cutting concerns in Phase 0. Two new pieces of evidence have arrived since:

1. **[phase-1-scope.md](../../research/ideas/phase-1-scope.md) introduces two additional structural requirements** that are intended to be load-bearing across every Phase 1 feature, not just scope-doc lore:
   - **SR-08** — Graphiti episode creation and entity updates are fire-and-forget from the tutor's caller-facing path. `tutor_session_end` returns within 2 seconds regardless of Graphiti write latency; write failures are logged but do not surface to the MCP caller.
   - **SR-09** — Every Ollama Modelfile used by the tutor must set explicit `num_ctx` (≥16384 for RAG-enabled personas) and `num_predict` (≥1500 for tutoring responses), with smoke-test assertions via `ollama show <model> --modelfile | grep PARAMETER` and via the runner log line `llama_new_context_with_model: n_ctx = N` from a real inference call.

2. **The 27 April 2026 Graphiti latency spike** ([graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)) measured the post-21-Apr vLLM-on-GB10 stack and found:

   | Operation | Median (s) |
   |---|---:|
   | `add_episode` | **78.98** |
   | `search_nodes` | 0.07 |
   | `search_memory_facts` | 0.08 |

   `add_episode` median is 78.98s — over 15× the 5s threshold the Phase 1 scope used as the SR-08 trigger. CC-08's original framing ("fire-and-forget + poll above 30s") is generic; with measured numbers it now specialises to a Graphiti-write-specific invariant that is load-bearing at every write point in the tutor, not just `tutor_session_end`.

   Conversely, `search_nodes` at 0.07s confirms ADR-ARCH-017's sync classification of `tutor_start_session` (and similarly the other read-path tools) — the read side is not the load-bearing one.

SR-09 is unrelated to latency but emerged from the [23 April OpenWebUI RAG empirical findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md): Ollama's default `num_ctx=2048` silently truncates tutoring responses mid-sentence when RAG is active. This is a structural failure mode rather than a per-feature concern, so it belongs alongside the parity-surface set.

## Decision

The load-bearing cross-cutting concerns set is extended from **eight** (CC-01 through CC-08) to **fourteen**, retaining CC-09 through CC-12 unchanged from ARCHITECTURE.md §6:

- **CC-01 through CC-07** — unchanged from ADR-ARCH-009; LES1 parity surfaces SR-01 through SR-07.
- **CC-08** — *Generic* fire-and-forget + poll-above-30s discipline (LES1 §4). Retained as the cross-agent rule; specialised below.
- **CC-09 through CC-12** — unchanged (safeguarding boundary, copyright/provenance boundary, in-process event bus vocabulary, async-capable subagent boundary).
- **CC-13 (NEW) — Graphiti write-back is asynchronous from every caller-facing path (SR-08).** Specialises CC-08 with measurement: with `add_episode` median 78.98s, the rule is not just "above 30s" — Graphiti writes are *always* async-from-caller, *every* write point (session-end, mid-session episodes, misconception logs, topic-confidence updates), and write failures are logged-only.
- **CC-14 (NEW) — Runtime LLM parameters are explicit and asserted (SR-09).** Every Modelfile sets explicit `num_ctx` and `num_predict`; smoke tests assert both via `ollama show` *and* via runner log inspection on a real inference call.

The CC numbering avoids colliding with the existing CC-09–CC-12 (which were promoted by ADR-ARCH-010 through ADR-ARCH-013) by placing the new codes at the end of the sequence.

Every Phase 1 feature honours CC-13 and CC-14 structurally:
- **CC-13** — every Graphiti write site goes through helpers that run the work as a background task (deepagents `AsyncSubAgent` per ADR-ARCH-012, or a plain `asyncio.create_task` for simple writes). Caller-facing handlers complete without awaiting Graphiti acknowledgement. Write failures emit a structured log line; they do not raise from the MCP handler.
- **CC-14** — a smoke test (per Modelfile change) runs `ollama show` and parses runner-log output to confirm `num_ctx` and `num_predict` reach the runner at expected values. Regression trips the test.

LES1 remains the evidence base for CC-01–CC-08; the [Phase 1 scope document](../../research/ideas/phase-1-scope.md) and the [27 Apr latency spike](../../research/ideas/graphiti-latency-spike-results.md) are the evidence base for CC-13; the [23 Apr OpenWebUI RAG findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) are the evidence base for CC-14.

## Alternatives considered

- **Leave SR-08 / SR-09 as Phase 1 scope-doc lore only.** Rejected. The Phase 0 lesson from ADR-ARCH-009 was that promoting parity surfaces to first-class CCs ensures every feature audits against them. Repeating the same elevation for SR-08 / SR-09 keeps the discipline consistent, and the latency spike makes SR-08 too consequential to leave at scope-doc level.
- **Inline the SR-08 changes into ADR-ARCH-003 (async Graphiti write-back) instead of refining ADR-ARCH-009.** Rejected. ADR-ARCH-003 is a *single-write-point* decision (session-end boundary). The latency spike shows write-back must apply at *every* write point, which is a cross-cutting concern, not a session-boundary policy. ADR-ARCH-003 will need its own follow-up `/arch-refine` to broaden its scope (flagged stale by this ADR; not modified here).
- **Supersede the SR series entirely with a new "LES1 + Phase 1 lessons" combined ADR.** Rejected. The LES1 parity surfaces and the Phase 1 additions have different evidence bases (cross-agent monorepo lore vs measured Graphiti latency / OpenWebUI empirical findings); collapsing them would obscure the chain of evidence. Keeping the supersession surgical (one ADR-ARCH-009 → one ADR-ARCH-018) preserves traceability.

## Consequences

**Positive:**
- Every Phase 1 feature has a 14-row checklist to audit against, not just the 8 from Phase 0. The two new rows are exactly the ones the Phase 1 scope identified as load-bearing.
- CC-13 forces Graphiti write-back patterns to be uniform across the tutor: session-end, mid-session, planner updates, Coach-observed misconceptions all go through the same fire-and-forget shape. No per-feature ad-hoc await of Graphiti.
- CC-14 closes a known silent failure mode (Modelfile param defaults overriding intended runtime configuration) before it can corrupt RAG-enabled persona behaviour.
- The latency spike's measurement (78.98s median) is now load-bearing in an architecture artefact, not just a research note — future agents reading the architecture see why CC-13 is non-negotiable.

**Negative:**
- ADR-ARCH-003 (async Graphiti write-back at session-end boundary) becomes too narrow in framing. It is flagged stale by this refinement and will need a separate `/arch-refine` to broaden to "every write point" semantics. Until that refinement, ADR-ARCH-003's scope statement is a strict subset of CC-13's; the two are consistent but not coextensive.
- Five design contracts (`API-mcp-transport`, `API-tutoring`, `DM-mcp-transport`, `events-schema.yaml`, `design/README.md`) that reference CC-08 in its generic form are flagged stale. Their CC-08 references remain *correct*; they just no longer enumerate CC-13 / CC-14. `/system-design` will detect and report these on next run.
- Adding a smoke test for CC-14 introduces a small per-Modelfile-change CI/manual cost. Accepted as cheap relative to the silent-truncation regression class it prevents.

## Downstream artefacts flagged stale

The following artefacts reference the previous (8-CC) framing and should be updated when convenient:

- **ADR-ARCH-003** — single-write-point framing; needs `/arch-refine` to broaden to every-write-point.
- `docs/architecture/domain-model.md` §324, §351 — CC-08 references only; correct but not mentioning CC-13.
- `docs/architecture/container.md` — tool-description rows for the MCP adapter; CC-08-aligned but not updated for CC-13's every-write-point semantics.
- `docs/design/contracts/API-mcp-transport.md` — 4 CC-08 references in invariants and adapter table.
- `docs/design/contracts/API-tutoring.md` — fire-and-forget references in classification rows.
- `docs/design/models/DM-mcp-transport.md` — CC-08 in invariants table.
- `docs/design/events-schema.yaml` — async write-back reference.
- `docs/design/README.md` — D2 closure note.

ADR-ARCH-009 itself remains queryable as the historical first-elevation decision; only its `Status` is updated to `superseded`. No content rewrite of ADR-ARCH-009.

## References

- [ADR-ARCH-009](ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md) — superseded predecessor.
- [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — single-write-point async decision (now narrower than CC-13).
- [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) — `AsyncSubAgent` is the preferred mechanism for CC-13 conformance in Phase 1.
- [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) — sync classification corroborated by `search_nodes` 0.07s in the same spike.
- [phase-1-scope.md](../../research/ideas/phase-1-scope.md) — SR-08 and SR-09 origins.
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — measured Graphiti latency, 27 Apr 2026.
- [openwebui-rag-empirical-findings-2026-04-23.md](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — SR-09 origin.
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` (LES1) — origin of CC-01 through CC-08.
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Update assumptions.yaml ASSUM-012 related_adr

Offer Graphiti seeding commands for both ADRs
Edit ARCHITECTURE.md
Added 2 lines
Edit ARCHITECTURE.md
Added 1 line
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Update assumptions.yaml ASSUM-012 related_adr

Offer Graphiti seeding commands for both ADRs
Edit assumptions.yaml
Added 3 lines
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Update assumptions.yaml ASSUM-012 related_adr

Offer Graphiti seeding commands for both ADRs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DECISION REFINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ADR-ARCH-009: Status → "Superseded by ADR-ARCH-018 on 2026-04-27"
  ADR-ARCH-018: Created (supersedes ADR-ARCH-009)

Updated files:
  ├── docs/architecture/decisions/ADR-ARCH-009-…-crosscutting.md          (status superseded)
  ├── docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md  (new)
  ├── docs/architecture/ARCHITECTURE.md                                   (CC table 12→14; ADR index +ADR-ARCH-018; ADR-ARCH-009 marked superseded)
  └── docs/architecture/assumptions.yaml                                  (ASSUM-012 related_adr → ADR-ARCH-018)

Stale artefacts (not edited; recorded in ADR-ARCH-018 §"Downstream artefacts flagged stale"):
  ⚠️ ADR-ARCH-003                 — needs separate /arch-refine to broaden write-back scope
  ⚠️ docs/architecture/domain-model.md §324, §351
  ⚠️ docs/architecture/container.md
  ⚠️ docs/design/contracts/API-mcp-transport.md
  ⚠️ docs/design/contracts/API-tutoring.md
  ⚠️ docs/design/models/DM-mcp-transport.md
  ⚠️ docs/design/events-schema.yaml
  ⚠️ docs/design/README.md

C4 diagrams: re-review NOT required (cross-cutting concern refinement, no
container or external-system structural change).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Graphiti is enabled: true in .guardkit/graphiti.yaml, but I cannot directly run guardkit shell commands without your approval. Proposed seeding commands:


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --group architecture_decisions
Run these now? [Y/n]

Next steps after seeding:

Review the new ADR: docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Refine ADR-ARCH-003 separately to broaden "session-end" → "every write point": /arch-refine --adr=ADR-ARCH-003 --context docs/research/ideas/graphiti-latency-spike-results.md
Run /system-design to detect and report the 5 stale design contracts.
N
Update Todos

Run impact analysis — find downstream artefacts referencing ADR-ARCH-009 / SR-08 / SR-09

Present impact scope to user for approval

Mark ADR-ARCH-009 as superseded; create new ADR-ARCH-018

Update ARCHITECTURE.md cross-cutting concerns table + ADR index

Update assumptions.yaml ASSUM-012 related_adr

Offer Graphiti seeding commands for both ADRs
Graphiti seeding skipped. Markdown artefacts are written; knowledge graph not updated. Re-run the seeding commands above whenever you're ready (or use /arch-refine again — re-applying with the same ADRs is idempotent for the upsert).

Refinement summary:

ADR-ARCH-009 marked superseded by ADR-ARCH-018 (body preserved for historical traceability).
ADR-ARCH-018 created — extends load-bearing cross-cutting concerns from CC-01–CC-12 to CC-01–CC-14, adding CC-13 (Graphiti async write-back at every write point, SR-08, evidence: add_episode 78.98s) and CC-14 (runtime LLM params explicit, SR-09).
ARCHITECTURE.md §6 (CC table 12→14) and §9 (ADR index +ADR-ARCH-018, ADR-ARCH-009 marked superseded).
assumptions.yaml ASSUM-012 related_adr → ADR-ARCH-018.
8 downstream artefacts (ADR-ARCH-003, domain-model, container, 5 design contracts) are recorded as stale inside ADR-ARCH-018 §"Downstream artefacts flagged stale" — not auto-flagged in Graphiti since seeding was declined.
Suggested next: /arch-refine --adr=ADR-ARCH-003 --context docs/research/ideas/graphiti-latency-spike-results.md to broaden ADR-ARCH-003's single-write-point scope to match CC-13.