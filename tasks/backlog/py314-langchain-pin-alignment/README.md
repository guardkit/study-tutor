# FEAT-7BDP — Python 3.14 + LangChain 1.x pin alignment

**Parent review**: [TASK-REV-57BD](../../in_progress/TASK-REV-57BD-portfolio-py314-langchain-1x-alignment.md)
**Review report**: [.claude/reviews/TASK-REV-57BD-report.md](../../../.claude/reviews/TASK-REV-57BD-report.md)
**Cross-repo precedent**: Jarvis ADR-ARCH-010 rev2 (FA04 trapdoor remediation)
**Status**: backlog (3 tasks, all parallel-safe; bundled single-PR recommended)
**Constraint**: DDD South West demo (autobuild builds jarvis/study-tutor/forge for the demo)

---

## Problem

GuardKit AutoBuild stalled for 33 minutes on Jarvis FEAT-J004-702C
(2026-04-27) due to two coupled pin issues:

1. A stale `requires-python = ">=3.12,<3.13"` cap on Jarvis excluded the
   active `/usr/local/bin/python3` (3.14, since 2025-10-07).
2. Open-floor LangChain ecosystem pins (`langchain-core>=0.3`, etc.) let the
   resolver pick mismatched 0.x / 1.x pairs and produce runtime
   `ModuleNotFoundError` from a deleted compat helper.

Jarvis's remediation (ADR-ARCH-010 rev2): `requires-python = ">=3.11"` +
coherent 1.x with `<2` caps on the LangChain ecosystem. The portfolio guide
([`guardkit/docs/guides/portfolio-python-pinning.md`](../../../../guardkit/docs/guides/portfolio-python-pinning.md))
codifies the rationale.

The portfolio rollout was paused while orchestrator-side issues were resolved.
With Jarvis stable end-to-end, this is study-tutor's catch-up.

## What the review found

study-tutor is **already 80% aligned**:

- ✓ `requires-python = ">=3.11"` (already correct).
- ✓ `langchain>=1.2.11`, `langchain-core>=1.2.18` (already 1.x runtime floor).
- ✓ `pydantic>=2.0,<3.0` (already capped).
- ✓ Empirically verified: fresh 3.14.2 venv, 23/23 tests passing in 6.84s,
  zero langchain-runtime failures (cleaner baseline than Jarvis on rev2).
- ✓ `langgraph` not imported in source (transitive only via `langchain`) —
  intentional; not a Jarvis-style direct dep.
- ✓ `deepagents` not in `pyproject.toml` and not imported in source —
  Phase 0 codebase doesn't use it yet (ADR-ARCH-004/012 declare it for
  Phase 1 but that's a separate follow-up).

**The 20% gap**:

- ✗ Runtime LangChain pins (`langchain`, `langchain-core`) lack `<2` caps.
- ✗ All five `[providers]` packages are completely unpinned (zero floor,
  zero cap). This is the FA04 forward-protection gap.

## Solution approach

A small, mechanical, three-task bundle. All forward-protection only —
no runtime behaviour change.

| # | Task | What it does |
|---|------|--------------|
| 1 | [TASK-PLA-001](TASK-PLA-001-pyproject-pin-updates.md) | `pyproject.toml`: add `<2` caps to runtime LangChain deps; add explicit floors+caps to all five `[providers]`. ~9 line diff. Re-verifies the 23/23 empirical baseline. |
| 2 | [TASK-PLA-002](TASK-PLA-002-adr-arch-020.md) | New file `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md` containing the decision rationale + verified-versions table. Content already drafted in review §5 — lift verbatim. |
| 3 | [TASK-PLA-003](TASK-PLA-003-readme-pinning-policy.md) | `README.md`: add a brief "Pinning policy" section pointing to ADR-ARCH-020 and the GuardKit portfolio guide for in-repo discoverability. |

### Verified pin set (Python 3.14.2, 2026-04-29)

The floors in TASK-PLA-001 match the resolved versions from the review's
empirical run. These are the same versions Jarvis verified on 3.14
(rev2 §"Empirical test on Python 3.14"):

```
langchain                 1.2.15
langchain-anthropic       1.4.2     (Jarvis: 1.4.1 — one patch ahead)
langchain-aws             1.4.5     (study-tutor only)
langchain-core            1.3.2
langchain-google-genai    4.2.2
langchain-ollama          1.1.0     (study-tutor only)
langchain-openai          1.2.1
langgraph                 1.1.10    (transitive — not a direct dep)
```

## Why this is high-priority but lower-risk than Jarvis was

**High priority**: study-tutor is DDD South West demo-critical (autobuild
builds jarvis/study-tutor/forge for the demo).

**Lower risk than Jarvis was**: Jarvis on rev2 went from 25 failures to 7
failures (none of which were langchain-runtime); study-tutor today is
**already at 0 failures** on the verified version set. This feature
locks in that state — it doesn't fix a broken state.

## What this feature deliberately doesn't do

- ✗ Add `deepagents` or `langgraph` direct deps (review §2, §3 — would
  diverge from actual code imports for zero protection).
- ✗ Touch `requires-python`, `pydantic`, `mcp`, or any non-LangChain pin
  (already correct or unrelated to FA04 mechanism).
- ✗ Resolve the ADR-ARCH-004/012 vs `pyproject.toml` deepagents drift
  (review §6) — that's been promoted to its own backlog task,
  [TASK-IMP-B7E0](../TASK-IMP-B7E0-deepagents-adr-pyproject-drift.md),
  which depends on this feature landing first (see its `dependencies`
  field). Not in this feature's scope.
- ✗ Touch GuardKit, Jarvis, or any sibling repo (review's explicit
  out-of-scope list).
- ✗ Add CI matrix entries, lockfile policy doc, or pin-tracking guard
  tests (Jarvis has the latter; the review §10 R5 placeholder mentions
  this could be a future addition but isn't part of this feature).

## Downstream task

- [TASK-IMP-B7E0 — Resolve deepagents ADR/pyproject drift](../TASK-IMP-B7E0-deepagents-adr-pyproject-drift.md)
  (depends on this feature; backlog).

## How to execute

Read [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for the full
execution plan, including the bundled-single-PR recommendation, the
parallel-via-Conductor alternative, and the sequencing note around
TASK-PLA-003 referencing ADR-ARCH-020 by filename.

TL;DR: three small mechanical tasks, all parallel-safe, ideally bundled
into a single review-bundle PR that captures the recipe + the diff + the
discoverability pointer in one coherent change.
