---
id: TASK-PLA-002
title: File ADR-ARCH-020 — LangChain ecosystem 1.x pinning + Python 3.14 alignment
status: completed
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
feature_id: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
priority: high
complexity: 2
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
completed: 2026-04-29T00:00:00Z
completed_location: tasks/completed/TASK-PLA-002/
organized_files: ["TASK-PLA-002.md"]
tags: [adr, documentation, pinning, langchain-1x, FA04-followup]
dependencies: []
parallel_safe: true
conductor_workspace: py314-langchain-pin-alignment-wave1-2
test_results:
  status: n/a
  note: "Documentation-only task (new ADR file); no code change to test."
  coverage: null
  last_run: null
---

# File ADR-ARCH-020 — LangChain ecosystem 1.x pinning + Python 3.14 alignment

## Context

Implementation subtask from **TASK-REV-57BD** (Python 3.14 + langchain-1.x
portfolio alignment review). The review's §5 contains the full draft ADR text;
this task is a write-and-commit-to-disk task — the content is already
finalised in the review report. Use that text verbatim, lifted into its own
file at `docs/architecture/decisions/`.

The numbering rationale: existing ADRs run ARCH-001 through ARCH-019;
ARCH-020 is the next free slot.

## Goal

Create `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`
containing the ADR drafted in `.claude/reviews/TASK-REV-57BD-report.md` §5.

## Steps

1. Open `.claude/reviews/TASK-REV-57BD-report.md`.
2. Locate §5 ("Draft ADR") — starts with the filename declaration and the
   ADR opens with a triple-backtick-fenced markdown block.
3. Copy the ADR content (everything inside the fenced markdown block —
   header through `## References`).
4. Write to `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`.
5. Verify cross-references resolve:
   - `appmilla_github/jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
     (cross-repo, read-only — exists)
   - `appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md` (cross-repo,
     read-only — exists)
   - `appmilla_github/guardkit/.claude/reviews/TASK-REV-FA04-report.md` (cross-repo,
     read-only — exists)
   - `.claude/reviews/TASK-REV-57BD-report.md` (this repo — exists once the
     review is accepted)

## Acceptance criteria

- [ ] New file at `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`.
- [ ] Content matches the §5 draft byte-for-byte (allowing for the fenced
      block delimiters being stripped).
- [ ] Frontmatter / status declaration present (`Status: Accepted`,
      `Date: 2026-04-29`, etc.).
- [ ] All cross-references in the "References" section point to existing
      files.
- [ ] No other files in the repo are modified.

## Out of scope

- The actual `pyproject.toml` pin update (TASK-PLA-001).
- README pinning-policy reference (TASK-PLA-003).
- Resolving the ADR-ARCH-004 / ADR-ARCH-012 deepagents drift (review §6 —
  separate follow-up).
- Modifying any existing ADR (ARCH-001 through ARCH-019). The new ADR
  *references* ARCH-004 and ARCH-012 in its "Related" line but doesn't
  amend them.

## Verification

```bash
ls -la docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md
diff <(awk '/^# ADR-ARCH-020/,/^## References/' .claude/reviews/TASK-REV-57BD-report.md \
      | sed -n '/^# ADR-ARCH-020/,/^## References/p') \
     <(awk '/^# ADR-ARCH-020/,/^## References/' docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md)
# (No diff = pass.)
```

## References

- Source content: `.claude/reviews/TASK-REV-57BD-report.md` §5.
- Cross-repo precedent (linked-from): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`.
- ADR numbering convention: existing files in `docs/architecture/decisions/`.

## Implementation Summary

Wrote `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`
containing the ADR drafted in `.claude/reviews/TASK-REV-57BD-report.md` §5,
lifted from the fenced markdown block byte-for-byte. Verified via:

```bash
diff <(awk '/^# ADR-ARCH-020/,/^## References/' .claude/reviews/TASK-REV-57BD-report.md) \
     <(awk '/^# ADR-ARCH-020/,/^## References/' docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md)
# (no diff — content matches §5 byte-for-byte)
```

All five acceptance criteria pass:
- File created at the prescribed path (7,189 bytes).
- Content matches §5 byte-for-byte (header through `## References`).
- `Status: Accepted` and `Date: 2026-04-29` present at the top.
- All four cross-references (Jarvis ADR-ARCH-010-rev2, GuardKit portfolio
  guide, GuardKit FA04 review, in-repo TASK-REV-57BD report) resolve to
  existing files.
- No other files in the repo modified by this task.

## Notes

Approach: pure file-write task — copied §5 content verbatim from the review
report. Numbering rationale held: ARCH-019 was the latest existing ADR;
ARCH-020 is the next free slot.

Lessons:
- The `awk`-based byte-for-byte diff against the source review §5 is a
  cheap, repeatable verification recipe for "lift this draft into its own
  file" tasks. Use it for TASK-PLA-003 (CLAUDE.md pinning policy paragraph)
  if the source paragraph is similarly fenced in §7 of the review.
- The deepagents ADR/code drift (review §6, F4) remains an open follow-up
  — ADR-ARCH-020 references but does not resolve it; Phase 1 work that
  introduces `AsyncSubAgent` will need to pick it up.
