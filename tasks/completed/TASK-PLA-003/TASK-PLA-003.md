---
id: TASK-PLA-003
title: Add Pinning policy pointer to README.md
status: completed
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
feature_id: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
priority: medium
complexity: 1
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
implemented: 2026-04-29T00:00:00Z
completed: 2026-04-29T00:00:00Z
completed_location: tasks/completed/TASK-PLA-003/
organized_files:
  - TASK-PLA-003.md
tags: [docs, pinning, discoverability]
dependencies: []
parallel_safe: true
conductor_workspace: py314-langchain-pin-alignment-wave1-3
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  note: docs-only task, no test gates
---

# Add Pinning policy pointer to README.md

## Context

Implementation subtask from **TASK-REV-57BD** review §7. The review surfaced
that study-tutor's README doesn't cross-reference the GuardKit portfolio
pinning guide, so a new maintainer touching `pyproject.toml` has no in-repo
signpost telling them why `requires-python` is open-bound or why the
LangChain ecosystem has `<2` caps. This is a small discoverability fix.

**Targeting README.md**, not `.claude/CLAUDE.md` (which is the GuardKit
default-template content, generic across all consumer projects) and not
`AGENTS.md` (which is for tutor-agent ALWAYS/NEVER/ASK rules, not maintainer
policy).

## Goal

Add a brief "Pinning policy" section to `README.md` pointing to ADR-ARCH-020
(when it lands via TASK-PLA-002) and to the GuardKit portfolio guide.

## Suggested addition

Place near the bottom of `README.md` (after the current setup/usage content),
or as a new section under a "Maintenance" / "Contributing" heading if one
gets added later. Suggested wording — adapt as needed for tone consistency
with the rest of the README:

```markdown
## Pinning policy

When changing `requires-python` or any LangChain ecosystem pin in
`pyproject.toml`, see:

- **`docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`**
  — the verified-versions table and the rationale for each cap, with
  empirical evidence from a Python 3.14 install + test run.
- **`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`**
  — the portfolio-wide guidance on why `requires-python` should not have a
  closed upper bound (origin incident: TASK-REV-FA04, the 33-minute
  autobuild stall caused by a stale `<3.13` cap excluding the active
  `/usr/local/bin/python3` 3.14).

Short version: open upper bound on Python; coherent same-major caps on
the LangChain ecosystem; verified versions table lives in the ADR and
gets updated when floors are lifted.
```

## Acceptance criteria

- [ ] `README.md` has a new section (or paragraph) referencing ADR-ARCH-020
      and the GuardKit portfolio guide.
- [ ] The reference to ADR-ARCH-020 is a relative in-repo path
      (`docs/architecture/decisions/ADR-ARCH-020-...`).
- [ ] The reference to the GuardKit guide is a sibling-repo path
      (`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`)
      and matches how other cross-repo refs are written elsewhere in the
      study-tutor docs.
- [ ] No changes to `.claude/CLAUDE.md`, `AGENTS.md`, or any other file.
- [ ] No GuardKit, Jarvis, or sibling-repo changes.

## Out of scope

- Adding a `CONTRIBUTING.md` (deferred — this task is the lightest possible
  signpost; if a contributing doc gets added later it can absorb this
  pointer).
- Cross-repo updates (Jarvis, forge, etc. should each make their own
  decision about adding equivalent pointers; not this task's responsibility).
- The actual ADR file (TASK-PLA-002).
- The actual `pyproject.toml` diff (TASK-PLA-001).

## Sequencing note

This task is parallel-safe with TASK-PLA-001 and TASK-PLA-002 (different
files). However, the README content references ADR-ARCH-020 by filename,
which means the reference becomes a *broken link* until TASK-PLA-002 lands.
Acceptable trade-off: the three tasks are designed to merge as a single
bundle (see IMPLEMENTATION-GUIDE.md). If you implement them sequentially in
separate commits, do TASK-PLA-002 first or land all three in one commit.

## References

- Review report: `.claude/reviews/TASK-REV-57BD-report.md` §7.
- ADR-ARCH-020 source content (lives in §5 of the same review).

## Implementation Summary

Added a "Pinning policy" section at the bottom of `README.md` (lines 48-64)
pointing to two resources: ADR-ARCH-020 via a relative in-repo path, and
the GuardKit portfolio-python-pinning guide via a sibling-repo
`appmilla_github/...` path matching the style used elsewhere in
study-tutor docs and in TASK-PLA-002. Wording adapted from the suggested
addition in this task spec; the "short version" trailer kept verbatim
because it is the load-bearing summary.

At completion time the bundle state is: TASK-PLA-001 already in
`tasks/completed/`, TASK-PLA-002 still in `backlog/` but its deliverable
(`docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`)
is already on disk, so the README link is not a broken link at the time
this task is marked completed.

## Implementation Notes

- Single-file change: `README.md` only. No edits to `.claude/CLAUDE.md`,
  `AGENTS.md`, or any other file (per acceptance criteria).
- Verified the ADR file path the README references matches the actual
  filename on disk before committing the cross-reference.
- Cross-repo path style (`appmilla_github/guardkit/docs/guides/...`)
  chosen to match TASK-PLA-002's frontmatter (line 54 of that task)
  rather than the absolute-path style seen in some research-stage docs.

## Notes

Lessons:

- For docs-only signpost tasks, verify the linked target exists *now*
  rather than assuming the bundle will land atomically — bundles can
  partially land (PLA-001 done, PLA-002 still in backlog) and the
  resulting README state can still be coherent if the deliverable file
  is on disk regardless of the task-status bookkeeping.
- The sibling-repo `appmilla_github/...` path style is the right call
  for portfolio-wide guides because it mirrors how cross-repo refs are
  written in adjacent task specs; absolute `/Users/.../` paths in older
  research docs are an artefact of that earlier era and shouldn't be
  copied for new documentation.
