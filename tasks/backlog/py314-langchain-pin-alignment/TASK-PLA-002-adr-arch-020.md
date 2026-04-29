---
id: TASK-PLA-002
title: File `ADR-ARCH-020` — LangChain ecosystem 1.x pinning + Python 3.14 alignment
status: backlog
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
parent_feature: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
complexity: 2
tags: [adr, documentation, pinning, langchain-1x, FA04-followup]
estimated_effort: "10-20 minutes (lift §5 of the review report into a new ADR file; verify cross-references)"
dependencies: []
parallel_safe: true  # touches only docs/architecture/decisions/ADR-ARCH-020-...md (new file); no overlap with PLA-001 or PLA-003
conductor_workspace: py314-langchain-pin-alignment-wave1-2
related_tasks:
  - TASK-REV-57BD  # parent review — its §5 contains the verbatim ADR text this task lifts
  - TASK-PLA-001   # sibling — applies the diff this ADR documents
  - TASK-PLA-003   # sibling — README pointer that references this ADR by filename
related_external_reviews:
  - ".claude/reviews/TASK-REV-57BD-report.md"  # source content for the new ADR (§5)
  - "jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md"  # rev2 — the cross-repo precedent ADR-ARCH-020 references in its body
test_results:
  status: pending
  coverage: null
  last_run: null
---

# File `ADR-ARCH-020` — LangChain ecosystem 1.x pinning + Python 3.14 alignment

## Context

`TASK-REV-57BD` §5 contains a fully-drafted ADR documenting the pin recipe
that **TASK-PLA-001** applies to `pyproject.toml`. The review delegates the
final filing of that ADR to this task because:

- The review's role is to *generate* the recommendation; landing it as a
  durable architectural artefact is implementation work.
- Filing it as its own ADR file (rather than embedding it in the review
  report) makes it discoverable from `docs/architecture/decisions/` —
  which is where future maintainers reading study-tutor's ADR sequence will
  expect to find it.
- The Jarvis precedent (ADR-ARCH-010 rev2) lives in Jarvis's own
  `docs/architecture/decisions/` — mirroring that placement here keeps
  cross-repo navigation symmetric.

This task is **mechanical**: lift the verbatim ADR text from the review's §5
into a new file. No re-drafting, no interpretation. The review's §5 has the
final wording; the verified-versions table is already populated from the
empirical run.

The ADR numbering rationale: existing ADRs run `ARCH-001` through
`ARCH-019` (verified by `ls docs/architecture/decisions/` at review time);
`ARCH-020` is the next free slot.

## Current state (read directly from `docs/architecture/decisions/` — pre-task snapshot)

```bash
$ ls docs/architecture/decisions/ | tail -5
ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
ADR-ARCH-017-tutor-start-session-sync-classification.md
ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
ADR-ARCH-019-async-graphiti-writeback-every-write-point.md
# (no ADR-ARCH-020 — this task creates it)
```

`.claude/reviews/TASK-REV-57BD-report.md` §5 (source content, lines
beginning with the fenced markdown block):

```markdown
# ADR-ARCH-020 — LangChain ecosystem 1.x pinning + Python 3.14 alignment
## Status
...
## References
```

The fenced block contains the complete ADR — Status declaration, Context,
Decision, "What this ADR deliberately does NOT change", verified-versions
table, Alternatives considered, Consequences, References. **Lift verbatim.**

## Goal

Create `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`
containing the ADR text from `.claude/reviews/TASK-REV-57BD-report.md` §5.

**No GuardKit, Jarvis, forge, agentic-dataset-factory, or specialist-agent
changes — fixes live in this repo.**

## Source artefacts

- This repo: `.claude/reviews/TASK-REV-57BD-report.md` §5 (the verbatim ADR
  text); `docs/architecture/decisions/` (existing ADRs to confirm the
  ARCH-020 number is free and the file-naming convention)
- Cross-repo (read-only, link target): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
  rev2 — referenced from the new ADR's "Related" line; existence verified
  during the review
- Cross-repo (read-only, link target): `guardkit/docs/guides/portfolio-python-pinning.md`
  — referenced from the new ADR's "Related" line; existence verified
  during the review
- Cross-repo (read-only, link target): `guardkit/.claude/reviews/TASK-REV-FA04-report.md`
  — referenced from the new ADR's "Related" line; existence verified
  during the review

## Implementation steps

1. Open `.claude/reviews/TASK-REV-57BD-report.md` and locate §5
   ("Draft ADR"). The ADR content begins with a triple-backtick-fenced
   markdown block whose first line is `# ADR-ARCH-020 — LangChain
   ecosystem 1.x pinning + Python 3.14 alignment`.
2. Copy everything **inside** the fenced markdown block — from
   `# ADR-ARCH-020 …` through the final `## References` section's last bullet.
3. Write to a new file at:
   ```
   docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md
   ```
4. Verify cross-references resolve:
   - `appmilla_github/jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md`
     — exists (read during the review).
   - `appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md` —
     exists (read during the review).
   - `appmilla_github/guardkit/.claude/reviews/TASK-REV-FA04-report.md` —
     exists (read during the review).
   - `.claude/reviews/TASK-REV-57BD-report.md` — exists (this repo).
5. Confirm no other ADRs are touched (this is a strictly-additive change).

## Acceptance criteria

- [ ] New file at `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`.
- [ ] Content matches `.claude/reviews/TASK-REV-57BD-report.md` §5
      byte-for-byte (allowing for the source-side fenced-block delimiters
      to be stripped).
- [ ] Frontmatter / status declaration present (`Status: Accepted`,
      `Date: 2026-04-29`, `Phase: Phase 0` — exactly as drafted).
- [ ] All four cross-references in the "References" section point to
      existing files (manual verification: open each path).
- [ ] No existing ADR file modified.
- [ ] No file outside `docs/architecture/decisions/ADR-ARCH-020-...md`
      modified.
- [ ] No GuardKit, Jarvis, forge, agentic-dataset-factory, or
      specialist-agent changes.

## Out of scope

- Applying the `pyproject.toml` diff — covered by **TASK-PLA-001**.
- Adding the README pinning-policy pointer — covered by **TASK-PLA-003**
  (which references the ADR-ARCH-020 filename created by this task).
- Re-deriving the ADR content — the review's §5 is the source of truth;
  this task copies it.
- Modifying ADR-ARCH-004 or ADR-ARCH-012 (the deepagents-related ADRs).
  The drift between those and `pyproject.toml` is tracked in
  **TASK-IMP-B7E0**, not this task.
- Updating the ADR index file (if one exists). At review time none was
  located; if one is added later it can absorb ADR-ARCH-020.

## Suggested workflow

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
git checkout -b feat/py314-langchain-pin-alignment-adr

# Use the Read tool / your editor to extract §5 from the review report,
# then write to:
#   docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md

# Sanity-check: the new file's first H1 should be the ADR title; the
# References section should list four bullets, all valid paths.
head -1 docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md
# → "# ADR-ARCH-020 — LangChain ecosystem 1.x pinning + Python 3.14 alignment"

# Verify cross-refs (each must exist):
ls ../jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md
ls ../guardkit/docs/guides/portfolio-python-pinning.md
ls ../guardkit/.claude/reviews/TASK-REV-FA04-report.md
ls .claude/reviews/TASK-REV-57BD-report.md

# Stage and commit
git add docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md
git commit -m "docs(adr): file ADR-ARCH-020 — LangChain 1.x pinning + Py3.14 alignment

Captures the pin recipe TASK-PLA-001 implements, with empirical
verified-versions table from the TASK-REV-57BD diagnostic run on
Python 3.14.2 (23/23 pytest passing, zero langchain-runtime failures).

Cross-repo precedent: Jarvis ADR-ARCH-010 rev2.
Source content: .claude/reviews/TASK-REV-57BD-report.md §5."
```

Complexity 2 + direct mode means no architectural review gate is triggered;
the cross-reference check is the verification step.

## References

- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §5 (the
  verbatim ADR text) and §1.3 (the verified-versions table the ADR cites)
- Cross-repo precedent (linked from the new ADR): `jarvis/docs/architecture/decisions/ADR-ARCH-010-python-312-and-deepagents-pin.md` rev2
- Portfolio policy (linked from the new ADR): `guardkit/docs/guides/portfolio-python-pinning.md`
- ADR numbering convention: existing files in `docs/architecture/decisions/`
  (ARCH-001 through ARCH-019)
- Sibling tasks: TASK-PLA-001 (the pin diff), TASK-PLA-003 (README pointer
  that references the ADR filename created here)
