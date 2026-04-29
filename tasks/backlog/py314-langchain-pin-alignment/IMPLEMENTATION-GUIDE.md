# Implementation Guide — FEAT-7BDP: Python 3.14 + LangChain 1.x pin alignment

**Feature ID**: FEAT-7BDP
**Feature slug**: `py314-langchain-pin-alignment`
**Parent review**: [TASK-REV-57BD](../../in_progress/TASK-REV-57BD-portfolio-py314-langchain-1x-alignment.md)
([report](../../../.claude/reviews/TASK-REV-57BD-report.md))
**Cross-repo precedent**: Jarvis ADR-ARCH-010 rev2
**Total subtasks**: 3
**Total waves**: 1 (all parallel-safe)
**Estimated effort**: 30–60 minutes (mechanical changes only, with one fresh-venv pytest run)

---

## What this feature does

Brings study-tutor's `pyproject.toml` and architecture-decision documentation
in line with the **FA04 / ADR-ARCH-010-rev2** portfolio recipe: forward
protection against the LangChain coordinated-major-bump trapdoor that bit
Jarvis on FEAT-J004-702C (33-minute autobuild stall, 2026-04-27).

study-tutor is **already 80% aligned** — its `requires-python = ">=3.11"` is
correct, its runtime LangChain pins are coherent 1.x, and a fresh
Python 3.14 install of the current `pyproject.toml` produces 23/23 passing
tests. This feature closes the remaining gap: the five `[providers]`
extras are completely unpinned, and the runtime LangChain pins lack `<2`
caps. Both are pure forward-protection changes.

## What this feature does NOT do

- Does not add `deepagents` or `langgraph` as direct deps (review §2, §3).
- Does not change `requires-python`, `pydantic`, `mcp`, or any non-LangChain pin.
- Does not resolve the ADR-ARCH-004/012 vs `pyproject.toml` deepagents drift
  (review §6). That's now [TASK-IMP-B7E0](../TASK-IMP-B7E0-deepagents-adr-pyproject-drift.md),
  a separate backlog task that depends on this feature landing first
  (its `dependencies` field lists TASK-PLA-001 and TASK-PLA-002).
- Does not touch GuardKit, Jarvis, forge, agentic-dataset-factory, or
  specialist-agent. All fixes are study-tutor-side.

---

## Wave structure

### Wave 1 (3 tasks, all parallel-safe)

| Task | Title | File touched | Mode | Workspace |
|------|-------|--------------|------|-----------|
| TASK-PLA-001 | Add `<2` caps + provider floors+caps | `pyproject.toml`, `uv.lock` | direct | `py314-langchain-pin-alignment-wave1-1` |
| TASK-PLA-002 | File ADR-ARCH-020 | `docs/architecture/decisions/ADR-ARCH-020-...md` (new) | direct | `py314-langchain-pin-alignment-wave1-2` |
| TASK-PLA-003 | README pinning-policy pointer | `README.md` | direct | `py314-langchain-pin-alignment-wave1-3` |

All three touch **different files**. There are no source-code conflicts.
They can run in parallel via Conductor workspaces, or sequentially in a
single agent session — author's choice.

### Sequencing note (relevant if running sequentially or in separate commits)

TASK-PLA-003 references ADR-ARCH-020 by filename. If the three tasks are
merged in separate commits, do **TASK-PLA-002 before TASK-PLA-003** to
avoid a transient broken-link state on `main`. If they merge as a single
bundled commit (recommended — see "Recommended PR strategy" below), the
order doesn't matter.

---

## Execution

### Recommended path: bundled single PR

The three tasks form a natural single review bundle — they're a coordinated
documentation+code change with shared rationale (ADR-ARCH-020 documents what
TASK-PLA-001 implements, and TASK-PLA-003 points readers to both). The
total diff is small:

- `pyproject.toml`: ~9 lines changed
- `uv.lock`: regenerated (bigger diff, but mechanical)
- `docs/architecture/decisions/ADR-ARCH-020-...md`: new file (~120 lines)
- `README.md`: ~15 lines added

```bash
# From the repo root, sequentially in one branch:
git checkout -b feat/py314-langchain-pin-alignment

# Wave 1, task 1
/task-work TASK-PLA-001
# (apply pin diff; run fresh-venv install + pytest; commit)

# Wave 1, task 2
/task-work TASK-PLA-002
# (lift §5 ADR content into docs/architecture/decisions/; commit)

# Wave 1, task 3
/task-work TASK-PLA-003
# (add README pointer; commit)

# Squash if desired, or keep three commits — both are reasonable.
```

### Alternative: parallel via Conductor

```bash
conductor open .
# Spawn three workspaces from main:
#   py314-langchain-pin-alignment-wave1-1  → /task-work TASK-PLA-001
#   py314-langchain-pin-alignment-wave1-2  → /task-work TASK-PLA-002
#   py314-langchain-pin-alignment-wave1-3  → /task-work TASK-PLA-003
# Merge each back to a shared feature branch when green.
```

For a 3-task feature this small, the bundled path is usually faster end-to-end
(less context-switching cost). Conductor parallelism pays off for 5+ tasks
or for tasks with longer-running test suites; this feature has neither.

---

## Acceptance for the whole feature

Marked complete when all three subtasks have:

- [ ] All listed acceptance-criteria checkboxes ticked in their task files.
- [ ] A clean `pytest` run on a fresh Python 3.14 venv (the same recipe as
      the review's empirical run — captured in TASK-PLA-001's verification
      section).
- [ ] No changes outside `pyproject.toml`, `uv.lock`,
      `docs/architecture/decisions/ADR-ARCH-020-...md`, and `README.md`.
- [ ] No changes to GuardKit, Jarvis, forge, or any other sibling repo.

When all three are green, archive **TASK-REV-57BD** by transitioning
`status: review_complete → completed` with a `decision: implemented`
note in `review_results`.

---

## Reading the review report once before starting

`.claude/reviews/TASK-REV-57BD-report.md` is the single source of truth for
this feature. Read at minimum:

- **§1** — empirical evidence (already-verified clean install + test pass).
- **§4** — the exact pin diff TASK-PLA-001 applies.
- **§5** — the full ADR-ARCH-020 text TASK-PLA-002 lifts.
- **§7** — the README addition TASK-PLA-003 implements.

§3 (deepagents drift) and §6 (ADR/code consistency) are background
context — they explain *why* this feature deliberately doesn't touch
`deepagents` or `langgraph`. Skim them so the new ADR's rationale is
audible to a future maintainer.

---

## Risk and rollback

**Risk**: minimal. The pin tightening codifies versions the resolver already
picks today; no runtime behaviour change. Worst case: `uv lock` produces a
slightly different transitive resolution that breaks a test. Mitigation:
TASK-PLA-001's acceptance criteria require a fresh-venv pytest run before
the task closes.

**Rollback**: `git revert` of the bundled commit (or of the three commits)
restores the prior `pyproject.toml`. The new ADR file can stay or be
removed depending on whether the maintainer wants to keep the
"considered and deferred" record.

---

## Cross-repo coordination

**None required.** This feature is fully self-contained in study-tutor.
The cross-repo references in ADR-ARCH-020 and the new README section are
**read-only links** to existing artefacts in Jarvis and GuardKit — no
sibling-repo PRs are needed.

If equivalent pin alignments are wanted in forge, agentic-dataset-factory,
or specialist-agent, those are separate review tasks in their own repos
(one per repo, mirroring the structure of TASK-REV-57BD here). The
portfolio guide explicitly recommends per-repo decisions, not copy-paste.
