# DDR-001 — MCP tool descriptions do not enumerate Graphiti write side-effects

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 0 (rule); Phase 1 (operative as write sites land)
**Bounded context:** MCP Transport
**Related:** [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md), [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-13), [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md), CC-07 (SR-07), CC-13 (SR-08), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md), [API-mcp-transport.md §5 / §6](../contracts/API-mcp-transport.md), [DM-mcp-transport.md §6 I-MCP9](../models/DM-mcp-transport.md).

## Context

[ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) broadens async Graphiti write-back from the session-end boundary (the prior ARCH-003 framing) to **every write point** in the tutor — `tutor_turn` (mid-session: Coach-observed misconceptions, planner topic-confidence updates) and `tutor_session_end` (session-end episode). The empirical anchor is the 2026-04-27 Graphiti latency spike: `add_episode` median **78.98s** (`search_nodes` median 0.07s).

This raises a design question that ARCH-019 itself does not settle: **should the registered MCP tool description string mention the new write side-effects?** Three positions are possible:

1. Enumerate every write site in the tool description so integrators (Claude Desktop, the demo script, future agents) can see them.
2. Mention writes generically ("triggers Graphiti persistence") without enumerating specific sites.
3. Keep the description silent on Graphiti entirely — writes are implementation-internal and the description describes only user-visible behaviour.

Today's live `tutor_session_end` description is exactly **"Marks session ended."** ([src/study_tutor/mcp/server.py](../../../src/study_tutor/mcp/server.py)) — i.e. position (3) in the absence of an explicit rule. As Phase 1 lands additional write sites, the temptation will be to drift toward (1) or (2) on a per-PR basis. Without a recorded rule, that drift is invisible until a Claude Desktop integrator sees a "Graphiti write may be in flight" string in the tool list and starts changing call patterns to accommodate something they have no protocol affordance for.

ADR-ARCH-019 already says write failures are log-only and never surface to the MCP caller. SR-07 (CC-07) says the tool description ≡ user-visible contract. ARCH-018's CC-13 makes async-from-caller a structural invariant. The design-level rule that follows from those three is recorded here.

## Decision

**MCP tool description strings registered via the FastMCP `add_tool(...)` call do not enumerate Graphiti write side-effects, even after CC-13 broadens fire-and-forget writes to every write point in `tutor_turn` and `tutor_session_end`.**

Concretely:

- The registered `description=` argument for each MCP tool describes only the **user-visible contract**: input shape, return shape, latency band, classification (sync / long-running per SR-07).
- Graphiti writes (and any future persistence side-effects that are fire-and-forget by CC-13 / ARCH-019) are **implementation-internal**. They live in code comments, in this contract / data-model documentation, and in the architecture decisions — but **not** in the MCP description string.
- The same rule extends to other implementation-internal effects already on the same footing: warm-up `asyncio.create_task` (`tutor_start_session`), the in-process Events bus emit (`session.completed` etc., once wired in P1), and any planner / RAG read paths that happen behind the handler.
- The design-artefact `description` field in `docs/design/mcp-tools.json` may carry **richer rationale** (for human readers of the design) without violating this rule — that field documents the design contract, not the registered tool string. The two remain distinct deliberately: design artefact = full rationale; live registered description = minimal user-visible contract.

The rule is enforced by **invariant I-MCP9** in `DM-mcp-transport.md §6` and surfaced as a recommended substring test in `API-mcp-transport.md §10`:

> Assert that no MCP tool description string registered on the FastMCP server contains the substrings "graphiti", "falkor", "episode", or "write-back" (case-insensitive).

## Rationale

- **SR-07 protects integrators from implementation drift.** The tool description is a contract. Side-effects that are fire-and-forget by architectural commitment (CC-13 / ARCH-019) and never surface to the caller are *not* part of that contract. Including them invites integrators to write code that depends on them — exactly the situation TASK-MDF-POLR (4-minute Claude Desktop timeout from a long-running/sync mismatch) warns about.
- **The 78.98s `add_episode` median makes (1) and (2) actively harmful.** Once a description hints at "Graphiti persistence", a thoughtful integrator may try to wait for it (poll? retry? assume durability before exit?). There is no protocol affordance for any of those — the writes are fire-and-forget, the failures are log-only. The honest description is silence.
- **Position (3) matches today's behaviour.** The live `tutor_session_end` description is already "Marks session ended." This DDR codifies the existing implicit rule rather than introducing new behaviour, so the cost of adoption is zero — the cost of *not* recording the rule is the per-PR drift risk in Phase 1.
- **Symmetric with the events bus.** The Tutoring contract (`API-tutoring.md §5`) already keeps the in-process event vocabulary off the MCP tool descriptions for the same reason: events are an internal contract, not a user-visible one. CC-13 writes follow the same shape; they should follow the same rule.

## Alternatives considered

- **Position (1) — enumerate every write site in the tool description.** Rejected. Forces the description to grow with each new Phase 1 write site (Coach misconceptions, planner topic-confidence, future per-AO trackers). Each addition is an MCP-visible description change with no protocol affordance behind it. Maximises drift surface, minimises integrator value.

- **Position (2) — generic "triggers Graphiti persistence" without enumeration.** Rejected. Same drift risk as (1) in disguise — the line gets edited every time a write site changes shape ("triggers Graphiti persistence" → "may trigger Graphiti persistence" → "asynchronous Graphiti persistence may be in flight"). Worse, it implies the caller can reason about a write contract that does not exist (writes are fire-and-forget; failures never surface).

- **Defer the rule to per-PR review.** Rejected. The cost of inconsistency is asymmetric: a single accidental mention in a Phase 1 PR exports an apparent contract to every Claude Desktop integrator on the next demo, and rolling it back is itself a description change that integrators see. Recording the rule once, with a substring test as enforcement, is cheaper than re-litigating each PR.

- **Bind the rule to ARCH-019 alone (not its own DDR).** Rejected. ARCH-019 is an architectural commitment about *write topology* (where writes happen, async-from-caller). The MCP-description rule is a *design-level* artefact about *how the protocol surface presents* that topology. Conflating them obscures the chain of evidence and makes the design-level rule invisible to anyone reading only `docs/design/`.

## Consequences

**Positive:**
- The MCP tool description set stays stable across Phase 1 even as multiple write sites land. Demo-script and Claude Desktop integrators see no spurious description changes.
- The substring test (I-MCP9) catches accidental SR-07 leakage as a CI failure rather than as a post-merge integrator surprise.
- The chain of evidence is explicit: latency spike (78.98s) → CC-13 (ARCH-018) → every-write-point (ARCH-019) → silent descriptions (DDR-001) → enforcement (I-MCP9).
- Aligns with the existing implicit treatment of warm-up tasks and Events emit — one rule for all fire-and-forget side effects.

**Negative:**
- Anyone debugging a missing Graphiti write by reading the MCP tool description will not find it there. Mitigated by the design artefacts (`API-mcp-transport.md §6` table, `DM-mcp-transport.md §6` I-MCP8) calling out the writes explicitly, and by the code comments at the write sites.
- The richer description in `docs/design/mcp-tools.json` may be mistaken for the registered tool string by a casual reader. Mitigated by the §6 table in `API-mcp-transport.md` distinguishing them and by the `source_of_truth` field in `mcp-tools.json` pointing at `src/study_tutor/mcp/adapter.py`.
- The substring test is a heuristic — it catches the obvious leakage strings ("graphiti", "falkor", "episode", "write-back") but not phrasing like "may persist context for later sessions." Recommend a brief code-review checklist item for MCP description changes alongside the test.

## Affected artefacts

- [`docs/design/contracts/API-mcp-transport.md §5 (invariant 5) + §6 + §10 (open question 4)`](../contracts/API-mcp-transport.md) — references this DDR, surfaces the recommended substring test.
- [`docs/design/models/DM-mcp-transport.md §6 (invariants I-MCP8, I-MCP9)`](../models/DM-mcp-transport.md) — encodes the rule and its enforcement.
- [`docs/design/mcp-tools.json`](../mcp-tools.json) — `design_decisions` block references this DDR; the `description` field for `tutor_session_end` carries design rationale only and explicitly notes side effects are not part of the user-visible contract.
- [`src/study_tutor/mcp/server.py`](../../../src/study_tutor/mcp/server.py) — the registered tool descriptions remain minimal; this DDR is the rule that keeps them so.

## References

- [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md) — sync classification + Phase 1 reversion-conditional rule.
- [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — CC-13 / CC-14 promotion.
- [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — every-write-point async commitment.
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — the 78.98s `add_episode` median that makes silent descriptions non-negotiable.
- LES1 row 19 (SR-07 latency classification) and TASK-MDF-POLR — `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
