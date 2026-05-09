---
id: TASK-RAG-CC2
title: "Add .md to .gitignore source-file rules so docling output is not accidentally committed"
task_type: bugfix
feature_id: FEAT-PRV4
parent_task: TASK-RAG-CC1
implementation_mode: direct
complexity: 1
estimated_minutes: 10
status: backlog
priority: low
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
related:
  - .gitignore
  - domains/gcse-english/sources/CONTRIBUTING-CORPUS.md
tags:
  - rag
  - corpus
  - gitignore
  - course-correction
  - feat-prv4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add `.md` to .gitignore source-file rules

## Provenance

TASK-RAG-CC1 added `.md` to the **example block** in
`domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` §4 to document that
docling-produced markdown should be gitignored. But the **actual**
`.gitignore` at repo root was not updated, so `.md` source files
currently show as "Untracked" instead of being ignored.

Surfaced during the TASK-RAG-CC1 smoke run when the reconstructed Mr
Bruff `.md` files appeared in `git status` as untracked. They are
in-copyright commercial study guides and **must not** be committed.

## Bug

The current `.gitignore` block (around line 248-257) covers `.pdf`,
`.PDF`, `.epub`, `.txt`, `.xhtml` but not `.md`:

```
domains/*/sources/*.pdf
domains/*/sources/**/*.pdf
domains/*/sources/*.PDF
domains/*/sources/**/*.PDF
domains/*/sources/*.epub
domains/*/sources/**/*.epub
domains/*/sources/*.txt
domains/*/sources/**/*.txt
domains/*/sources/*.xhtml
domains/*/sources/**/*.xhtml
```

## Fix

Add two lines for `.md`:

```
domains/*/sources/*.md
domains/*/sources/**/*.md
```

Update the surrounding comment block (around line 241-247) to reflect
TASK-RAG-CC1's docling-output integration — mention that `.md` is the
docling-produced shape that joins the existing extension list.

## Acceptance criteria

- [ ] `.gitignore` includes `domains/*/sources/*.md` and
      `domains/*/sources/**/*.md`.
- [ ] The leading comment block references TASK-RAG-CC1 (or the docling
      workflow) as the reason `.md` was added.
- [ ] `git status` shows zero "Untracked" entries under
      `domains/gcse-english/sources/` after this lands (assumes the
      reconstructed `.md` files are present locally).
- [ ] No other `.gitignore` lines change.

## Out of scope

- Removing files from git history that may have been committed
  pre-fix (none have been; check via `git log --all -- 'domains/*/sources/*.md'`).
- Extending the rule to other domain trees beyond `gcse-english/` (the
  existing `domains/*/sources/` pattern already covers them generically).

## References

- [tasks/completed/TASK-RAG-CC1/TASK-RAG-CC1.md](../completed/TASK-RAG-CC1/TASK-RAG-CC1.md) — parent task that introduced `.md` ingestion
- [domains/gcse-english/sources/CONTRIBUTING-CORPUS.md](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md) §4 — the docs that should match the `.gitignore` reality
