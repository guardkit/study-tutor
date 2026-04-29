---
id: TASK-PLA-003
title: Add Pinning policy pointer to `README.md`
status: backlog
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-57BD
parent_feature: FEAT-7BDP
feature_slug: py314-langchain-pin-alignment
wave: 1
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: medium
complexity: 1
tags: [docs, pinning, discoverability, ddd-southwest-demo]
estimated_effort: "5-10 minutes (one paragraph addition; no code change)"
dependencies: []
parallel_safe: true  # touches only README.md; no overlap with PLA-001 (pyproject) or PLA-002 (new ADR file)
conductor_workspace: py314-langchain-pin-alignment-wave1-3
related_tasks:
  - TASK-REV-57BD  # parent review §7 — recommendation to add this pointer
  - TASK-PLA-001   # sibling — applies the pin diff this README section explains
  - TASK-PLA-002   # sibling — files the ADR this README section references by filename
related_external_reviews:
  - ".claude/reviews/TASK-REV-57BD-report.md"  # parent review §7 (the recommendation + suggested wording)
  - "guardkit/docs/guides/portfolio-python-pinning.md"  # the policy this README points to
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Add Pinning policy pointer to `README.md`

## Context

`TASK-REV-57BD` §7 surfaced that study-tutor's `README.md` and `AGENTS.md`
do **not** cross-reference GuardKit's portfolio-pinning guide. The next
maintainer who edits `pyproject.toml` therefore has no in-repo signpost
explaining:

- Why `requires-python = ">=3.11"` has no upper bound (and shouldn't get
  one — that's the FA04 trapdoor mechanism).
- Why the LangChain ecosystem has explicit `<2` caps and floor pins
  (the recipe applied by **TASK-PLA-001**, documented by **TASK-PLA-002**'s
  ADR).
- Where to look for the verified-versions table when bumping floors.

This task closes that gap with a small, mechanical addition. It targets
**`README.md`** specifically — *not* `.claude/CLAUDE.md` (which is the
GuardKit default-template content, generic across all consumer projects)
and *not* `AGENTS.md` (which is for tutor-agent ALWAYS/NEVER/ASK rules,
not maintainer policy). Verbatim from review §7:

> Recommendation: Yes, but lightly. Adding a one-paragraph "When changing
> `requires-python` or LangChain ecosystem pins, see
> `guardkit/docs/guides/portfolio-python-pinning.md`" pointer would make
> the constraint discoverable in-repo.

This is the lightest possible change that achieves the discoverability
benefit. If a `CONTRIBUTING.md` is added later, that file can absorb (and
expand on) the pointer; this task is the interim signpost.

## Current state (read directly from `README.md` — pre-task snapshot)

`README.md` is 46 lines, focused on Claude Desktop setup + the wrapper
script rationale (SR-02). There is **no** pinning policy section, no
reference to ADR-ARCH-020 (which doesn't exist yet — gets filed by
**TASK-PLA-002**), and no reference to the GuardKit portfolio guide.

Relevant landmarks for the addition's placement:

```bash
$ wc -l README.md
46 README.md

$ grep -n "^##" README.md
8:## Claude Desktop setup
30:## Why the wrapper?
```

The new section can land at the bottom of the file (after the existing
content), or under a new `## Maintenance` heading if the maintainer
prefers. Placement is a minor style call — the content is the constraint.

## Goal

Add a brief "Pinning policy" section to `README.md` pointing to:

1. `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`
   (filed by **TASK-PLA-002**) for the verified-versions table and per-pin
   rationale.
2. `appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md` for
   the portfolio-wide rationale on why `requires-python` has no upper
   bound.

**No GuardKit, Jarvis, forge, agentic-dataset-factory, or specialist-agent
changes — fixes live in this repo.**

## Source artefacts

- This repo: `README.md` (the file to edit), `AGENTS.md` (read for tone
  reference — this addition should match the matter-of-fact tone of the
  rest of the docs)
- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §7 (the
  recommendation + suggested wording)
- Cross-repo (read-only, pointed-to): `guardkit/docs/guides/portfolio-python-pinning.md`
- This-repo (pointed-to, lands via TASK-PLA-002): `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`

## Suggested addition

Verbatim wording from `.claude/reviews/TASK-REV-57BD-report.md` §7 — adapt
for tone consistency with the rest of `README.md` if the matter-of-fact
prose around the wrapper script suggests a slightly different register:

```markdown
## Pinning policy

When changing `requires-python` or any LangChain ecosystem pin in
`pyproject.toml`, see:

- **`docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`**
  — the verified-versions table and the rationale for each cap, with
  empirical evidence from a Python 3.14 install + test run.
- **`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`**
  — the portfolio-wide guidance on why `requires-python` should not have
  a closed upper bound (origin incident: TASK-REV-FA04, the 33-minute
  autobuild stall caused by a stale `<3.13` cap excluding the active
  `/usr/local/bin/python3` 3.14).

Short version: open upper bound on Python; coherent same-major caps on
the LangChain ecosystem; verified versions table lives in the ADR and
gets updated when floors are lifted.
```

## Acceptance criteria

- [ ] `README.md` contains a new `## Pinning policy` section (or an
      equivalently-named heading the implementer prefers, e.g.
      `## Maintenance / Pinning`) with two reference links.
- [ ] The reference to ADR-ARCH-020 uses a relative in-repo path
      (`docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`).
- [ ] The reference to the GuardKit portfolio guide uses a sibling-repo
      path (`appmilla_github/guardkit/docs/guides/portfolio-python-pinning.md`)
      consistent with how cross-repo refs are written elsewhere in
      study-tutor's docs.
- [ ] No changes to `.claude/CLAUDE.md`, `AGENTS.md`, or any other file.
- [ ] No GuardKit, Jarvis, forge, agentic-dataset-factory, or
      specialist-agent changes.
- [ ] `wc -l README.md` shows ~10–15 additional lines (sanity check —
      keeps the addition lightweight, per review §7's "lightly").

## Sequencing note (relevant if running this task in isolation)

This task references `docs/architecture/decisions/ADR-ARCH-020-...md` by
filename. That file is created by **TASK-PLA-002**. If the three tasks are
merged in *separate* commits to `main`, do TASK-PLA-002 before TASK-PLA-003
to avoid a transient broken-link state on `main`. If they merge as a
single bundled commit (recommended — see the feature
[IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)), the order doesn't
matter.

## Out of scope

- The `pyproject.toml` diff — covered by **TASK-PLA-001**.
- Filing the ADR file itself — covered by **TASK-PLA-002**.
- Resolving the deepagents ADR/code drift — covered by
  **TASK-IMP-B7E0**.
- Adding a `CONTRIBUTING.md` — explicitly deferred per review §7
  ("Suggested addition … this task is the lightest possible signpost; if
  a contributing doc gets added later it can absorb this pointer").
- Cross-repo doc updates (Jarvis, forge, etc. should each make their own
  decision about adding equivalent pointers; not this task's
  responsibility).
- Reformatting / restructuring the rest of `README.md`. Strictly additive.

## Suggested workflow

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
git checkout -b feat/py314-langchain-pin-alignment-readme

# Edit README.md to append the new ## Pinning policy section (see
# "Suggested addition" block above for verbatim wording).

# Sanity check
diff <(git show HEAD:README.md | wc -l) <(wc -l < README.md)
# → expect ~10–15 line increase

git add README.md
git commit -m "docs(readme): add Pinning policy pointer to ADR-020 and GuardKit guide

Discoverability fix per TASK-REV-57BD §7. Gives a future maintainer
editing pyproject.toml an in-repo signpost for the pin recipe (ADR-020)
and the portfolio-wide rationale on Python upper-bound stance (GuardKit
portfolio-python-pinning guide).

Strictly additive — no other README content changed."
```

Complexity 1 + direct mode means no architectural review gate; the
acceptance-criteria checklist is the verification step.

## References

- Parent review: `.claude/reviews/TASK-REV-57BD-report.md` §7 (the
  recommendation and suggested wording)
- Cross-repo policy (linked from the new section): `guardkit/docs/guides/portfolio-python-pinning.md`
- This-repo ADR (linked from the new section, lands via TASK-PLA-002):
  `docs/architecture/decisions/ADR-ARCH-020-langchain-1x-pinning-and-py314-alignment.md`
- Sibling tasks: TASK-PLA-001 (the pin diff), TASK-PLA-002 (the ADR file)
