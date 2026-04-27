# ADR-ARCH-009 — Six parity surfaces (LES1) as load-bearing cross-cutting concerns

## Status

Superseded by [ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) on 2026-04-27.

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** LES1, CC-01 through CC-08, phase-0-scope.md §Structural Requirements
**Superseded by:** ADR-ARCH-018 (extends the SR series with SR-08 / SR-09 and re-grades CC-08 against measured Graphiti latency).

## Context

`specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
(LES1) documents six parity surfaces learned the hard way during
TASK-REV-B8E4. These are the minimum gate before first-merge for any
cross-agent codebase in the appmilla_github monorepo. The Phase 0
scope elevates these to SR-01 through SR-07 (structural requirements)
and declares them do-not-change.

LES1 itself is declared authoritative with a named suffix (LES1 →
future LES2 if a new class of findings emerges). The lessons are
specifically annotated for study-tutor's profile: MCP-only; latency
classification ⚠️; no NATS.

## Decision

The six parity surfaces become **first-class cross-cutting concerns**
in Study Tutor's architecture. Promoted as CC-01 through CC-07 in
`ARCHITECTURE.md §6`:

- **CC-01** — MCP stdio discipline (SR-01)
- **CC-02** — Launcher CWD abs-path (SR-02)
- **CC-03** — Provider resolution at the factory (SR-03)
- **CC-04** — `[providers]` extra completeness (SR-04)
- **CC-05** — Dockerfile literal-match venv install (SR-05; **paused**
  in Phase 0 per ADR-ARCH-005; reactivates on first Dockerfile)
- **CC-06** — `.env` hygiene — no real-looking keys committed (SR-06)
- **CC-07** — Tool description ≡ implementation contract (SR-07)

Plus CC-08 — fire-and-forget + poll above 30s (LES1 §4; distinct from
SR-07's contract rule).

Every feature from the first commit honours these structurally:
- Test cases exist for CC-01 (`tests/unit/mcp/test_stdio_discipline.py`)
  and CC-03 (`tests/unit/llm/test_provider_resolution.py`) in Phase 0.
- `.env.example` linted for CC-06 (grep for `=sk-` / `=AIza` / `=AKIA`).
- SR-07 tool-contract test per tool.
- LES1 itself is referenced in each affected ADR as the evidence base.

## Alternatives considered

- **Leave the parity surfaces as coding-guide lore.** Rejected. LES1
  is already guide material; promoting them to cross-cutting concerns
  ensures every feature has to address them, not just the first one.
- **Only adopt the rows that bit specialist-agent hardest.** Rejected.
  All six are cheap to get right from day one and expensive to
  retrofit (demonstrated by LES1 itself).

## Consequences

**Positive:**
- Every feature review has a standard checklist to audit against.
- Phase 0 success criteria include "SR-01 through SR-07 all green" as
  a gated deliverable.
- Future agents in the monorepo have a pattern to inherit from.

**Negative:**
- Slight overhead per feature (a few test cases) to keep CC-01/CC-03
  structurally intact. Accepted as the cost of not re-learning LES1.
- CC-05 dormancy in Phase 0 may cause confusion ("we have a CC but no
  mitigation"). Mitigated by ADR-ARCH-005's explicit reactivation
  trigger.

## References

- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
  (LES1).
- `docs/research/ideas/phase-0-scope.md §Structural Requirements`.
- All SR-related source tasks: TASK-MDF-MCPB, PORT, PMEV, LCOI, DKRX,
  POLR, CRMV, ORPH, PRVS.
