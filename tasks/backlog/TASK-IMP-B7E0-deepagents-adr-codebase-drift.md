---
id: TASK-IMP-B7E0
title: Resolve ADR-ARCH-004 / ADR-ARCH-012 vs pyproject.toml deepagents drift (Phase 1 prerequisite)
status: backlog
task_type: implementation
parent_review: TASK-REV-57BD
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: medium
complexity: 4
tags: [phase-1-prep, deepagents, adr-alignment, pre-existing-drift]
estimated_effort: "60-120 minutes (depends on Phase 1 architecture decision)"
related_tasks:
  - TASK-REV-57BD  # Diagnostic review where this drift was surfaced (finding F4)
  - TASK-PLA-001   # Sibling (FEAT-7BDP): pyproject pin updates — must land first
  - TASK-PLA-002   # Sibling (FEAT-7BDP): ADR-ARCH-020
  - TASK-PLA-003   # Sibling (FEAT-7BDP): README pinning policy
parent_feature: null  # deliberately not part of FEAT-7BDP — separate Phase 1 architecture concern, kept out so /system-arch routing isn't conflated with pin policy
related_external_reviews:
  - "jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md"  # rev2 deepagents pin recipe (>=0.5.3, <0.6)
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Resolve ADR-ARCH-004 / ADR-ARCH-012 vs pyproject.toml deepagents drift

## Context

`TASK-REV-57BD` (diagnostic review, 2026-04-29) surfaced a pre-existing drift between architectural decisions and the codebase, **orthogonal to the pin alignment work** in `FEAT-7BDP` (`tasks/backlog/py314-langchain-pin-alignment/` — TASK-PLA-001/002/003):

- `docs/architecture/decisions/ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md` lists `deepagents >= 0.5.3` in the framework table, annotated "Declared in `[providers]` extra".
- `docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md` decision text: "Pin `deepagents >= 0.5.3` in `pyproject.toml` `[providers]` extra (CC-04) from Phase 0 for SR-04 smoke-test compliance, even though Phase 0 code does not import deepagents yet."
- Current `pyproject.toml`: **no** `deepagents` declaration anywhere.
- Current `src/`, `tests/`: **no** `deepagents` imports.

Verbatim from `.claude/reviews/TASK-REV-57BD-report.md` §3:

> Two interpretations:
> 1. The ADRs are aspirational and Phase 1 will add the dep. In that case, when deepagents gets added it should be pinned coherently with the Jarvis recipe: `deepagents>=0.5.3,<0.6`.
> 2. The Phase 1 architecture has changed and the ADRs need updating. This is a separate decision the review can't make on the user's behalf.

This task forces the decision — but it does **not** prescribe which one. The architectural decision-maker (likely you, in a `/system-arch` or `/design-refine` session) needs to pick the interpretation, then this task captures the bookkeeping that follows.

## Goal

Reach a single coherent state across:
- `pyproject.toml`
- `ADR-ARCH-004` (planned stack table)
- `ADR-ARCH-012` (deepagents AsyncSubAgent Coach pin)
- Phase 1 implementation plans (if interpretation 2 forces them)

…such that a future portfolio review (analogue of TASK-REV-57BD for Phase 1) sees no drift.

## Two paths (pick exactly one)

### Path A — Interpretation 1: ADRs are correct, codebase is behind

**Decision**: Phase 1 will use `deepagents` `AsyncSubAgent` Coach + `CompositeBackend` per the existing ADRs. The pin should be added now-or-when-Phase-1-starts, matching the Jarvis recipe (which is empirically validated on the same Python 3.14 the demo machine uses).

**Implementation**:
1. Add to `pyproject.toml` `[project.optional-dependencies].providers`:
   ```toml
   "deepagents>=0.5.3,<0.6",
   ```
   (cap matches Jarvis ADR-ARCH-010 rev2 §Decision; `<0.6` is the gating boundary for `AsyncSubAgent` API stability per Jarvis ADR-ARCH-025).
2. Run `uv lock` and verify the pin resolves cleanly with the `langchain` 1.x ecosystem (Jarvis verified this works on 3.14 in rev2).
3. Run the empirical revalidation step (same recipe as TASK-PLA-001's verification block — fresh 3.14 venv, `uv pip install -e ".[dev,providers]"`, `pytest`).
4. No ADR changes required — the existing ADRs are now reflected in `pyproject.toml`.

### Path B — Interpretation 2: ADRs are stale, supersede them

**Decision**: Phase 1 architecture has shifted away from `deepagents.AsyncSubAgent`. Determine the actual Phase 1 design (likely a `/system-arch` or `/design-refine` session output), then update the ADRs to match.

**Implementation**:
1. Run `/design-refine` or `/system-arch` to record the new Phase 1 architecture decision. (Outside this task's scope — flag a checkpoint here.)
2. File a superseding ADR (`ADR-ARCH-021` — assumes FEAT-7BDP / TASK-PLA-002 has landed and taken `ADR-ARCH-020`) marking ADR-ARCH-012 as **Superseded**.
3. Update ADR-ARCH-004's framework table to remove the `deepagents` row (or annotate it as deferred / removed).
4. No `pyproject.toml` change.

### Why these paths can't be auto-decided

The pin alignment review (TASK-REV-57BD) deliberately stayed out of the Phase 1 architecture question — that's `/system-arch` territory, not pin-policy territory. Folding this into the pin-alignment commit would conflate two different decisions and make future bisection harder.

## Acceptance criteria

- [ ] One of Path A or Path B is explicitly selected (record the choice in the task's resolution notes).
- [ ] After implementation, no drift remains between `pyproject.toml`, ADR-ARCH-004 framework table, and ADR-ARCH-012 decision text.
- [ ] If Path A: `pyproject.toml` includes `deepagents>=0.5.3,<0.6`; `uv lock` succeeds; empirical 3.14 venv `uv pip install -e ".[dev,providers]"` resolves cleanly; `pytest` still passes.
- [ ] If Path B: ADR-ARCH-012 marked `Superseded by ADR-ARCH-XXX`; ADR-ARCH-004 framework table updated; the new ADR records the architecture decision and rationale.
- [ ] No proposed changes to `guardkit/` or `jarvis/` repos — fixes live in this repo only.

## Suggested workflow

This is genuinely a decision-and-implement task — full workflow recommended, **not** micro-mode:

```bash
/task-work TASK-IMP-B7E0
```

Phase 1.6 (Clarifying Questions) and Phase 2.6 (Human Checkpoint) are appropriate here — the Path A vs Path B choice is exactly the kind of architectural decision that benefits from a checkpoint. Complexity 4 should auto-route to QUICK_OPTIONAL review mode; bump to FULL_REQUIRED if Path B is chosen (because then this becomes a `/system-arch` follow-up).

## Out of scope

- Pin alignment for the langchain ecosystem — covered by **FEAT-7BDP** (`tasks/backlog/py314-langchain-pin-alignment/`, TASK-PLA-001/002/003).
- Phase 1 implementation work proper (`AsyncSubAgent` Coach scaffolding, `CompositeBackend` routing, etc.) — gated behind whichever path this task selects.

## References

- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §3 + §6 (the drift finding) + §10 R5 (the recommendation).
- Sibling feature (must land first): `tasks/backlog/py314-langchain-pin-alignment/` (FEAT-7BDP) — see its [README](py314-langchain-pin-alignment/README.md) and [IMPLEMENTATION-GUIDE](py314-langchain-pin-alignment/IMPLEMENTATION-GUIDE.md).
- Existing ADRs: `docs/architecture/decisions/ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md`, `docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md`
- Cross-repo deepagents pin recipe (read-only): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md` rev2
