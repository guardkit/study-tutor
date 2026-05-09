---
id: TASK-PRV-008
title: "Bug: citation-anchor inference gate uses ^-anchored regex without re.MULTILINE; fails for any primary text with front matter"
task_type: bugfix
feature_id: FEAT-PRV4
parent_review: TASK-REV-RAG4
implementation_mode: task-work
complexity: 2
estimated_minutes: 45
status: completed
priority: medium
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
completed: 2026-05-09T00:00:00Z
completed_location: tasks/completed/TASK-PRV-008/
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied; ready to ship"
organized_files:
  - TASK-PRV-008-citation-anchor-multiline-regex.md
related:
  - src/study_tutor/knowledge/corpus.py
  - tests/unit/knowledge/test_corpus.py
  - domains/gcse-english/sources/primary_text/macbeth.txt
  - .guardkit/reviews/TASK-REV-RAG4-review-report.md
tags:
  - bug
  - rag
  - corpus
  - citation-anchor
  - feat-prv4
  - phase-1
test_results:
  status: passing
  coverage: null
  last_run: 2026-05-09T00:00:00Z
  notes: |
    tests/unit/knowledge/test_corpus.py — 20/20 passing (incl. 2 new
    front-matter regression tests: test_play_with_front_matter_still_yields_play_anchor,
    test_novel_with_front_matter_still_yields_novel_anchor). Loader-only smoke
    against domains/gcse-english/sources/primary_text/macbeth.txt: 201/210
    primary chunks now carry citation_anchor (was 0/210 before fix). The 9
    remaining anchor=None chunks are at chunk_index 0-6 (front matter, ≤2,802
    char Standard Ebooks editorial header) and 208-209 (end matter / colophon)
    — none fall inside the play body.
---

# Task: Citation-anchor inference fails for primary text with front matter

## Provenance

Surfaced incidentally during the TASK-RAG-CC1 smoke run on 2026-05-09 — once
real Standard Ebooks Macbeth content was ingested for the first time, all 210
primary chunks emitted `corpus.citation_anchor.inference_failed` and shipped
with `citation_anchor=None`. The bug pre-dates CC1; it was masked by tests
using fixtures that start with `ACT I` directly (no front matter).

## Bug

[corpus.py:463-465](../../src/study_tutor/knowledge/corpus.py#L463-L465)
compiles the structural-marker patterns:

```python
_ACT_PATTERN = re.compile(r"^\s*act\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)
_SCENE_PATTERN = re.compile(r"^\s*scene\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)
_CHAPTER_PATTERN = re.compile(r"^\s*chapter\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)
```

[corpus.py:476-482](../../src/study_tutor/knowledge/corpus.py#L476-L482)
uses these patterns as the *gate* for picking play vs novel inference:

```python
def _infer_citation_anchor(file_text: str, char_offset: int) -> CitationAnchor | None:
    """Pick the right anchor inferer based on the file's structural markers."""
    if _ACT_PATTERN.search(file_text):
        return _infer_play_anchor(file_text, char_offset)
    if _CHAPTER_PATTERN.search(file_text):
        return _infer_novel_anchor(file_text, char_offset)
    return None
```

Without `re.MULTILINE`, `^` is start-of-string, not start-of-line.
`_ACT_PATTERN.search(file_text)` therefore only matches if the *whole file*
starts with optional whitespace then "act". The Standard Ebooks Macbeth `.txt`
has 2,802 chars of editorial front matter (title, author, imprint, etc.)
before the first `Act I`, so the gate returns `None` and `_infer_play_anchor`
is never called — even though it works correctly when invoked directly.

The same bug affects `_CHAPTER_PATTERN` for novels.

The internal walker `_infer_play_anchor`
([corpus.py:485-523](../../src/study_tutor/knowledge/corpus.py#L485-L523))
uses `_ACT_PATTERN.match(stripped)` per stripped line, so it works correctly
once it's actually called.

## Impact

Every primary text file with front matter ships chunks with
`citation_anchor=None`. This breaks the quote-fidelity rubric for plays and
novels — primary chunks lose their Act/Scene/Line (or Chapter/Paragraph)
provenance, so `VerifierMetadata.primary_matches` cannot carry annotated
citations.

Discovered via TASK-RAG-CC1 smoke against `domains/gcse-english/sources/primary_text/macbeth.txt`:
- 210/210 primary chunks had no anchor.
- Direct call to `_infer_play_anchor(text, offset)` produced correct anchors
  (e.g., `offset=80000 → kind='play' act=5 scene=7 line=9`).
- Adding `re.MULTILINE` to the gate pattern restores correct gating.

## Reproduction

```python
from pathlib import Path
import sys; sys.path.insert(0, "src")
from study_tutor.knowledge.corpus import _ACT_PATTERN, _infer_citation_anchor

text = Path("domains/gcse-english/sources/primary_text/macbeth.txt").read_text()
print(_ACT_PATTERN.search(text))     # → None  (BUG)
print(_infer_citation_anchor(text, 50000))  # → None  (BUG: never reaches walker)

import re
ml = re.compile(r"^\s*act\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE | re.MULTILINE)
print(ml.search(text))  # → <re.Match span=(2802, 2808) match='\nAct I'>  (correct)
```

## Fix

Add `re.MULTILINE` to all three compiled patterns:

```python
_ACT_PATTERN = re.compile(
    r"^\s*act\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE | re.MULTILINE
)
_SCENE_PATTERN = re.compile(
    r"^\s*scene\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE | re.MULTILINE
)
_CHAPTER_PATTERN = re.compile(
    r"^\s*chapter\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE | re.MULTILINE
)
```

Adding `re.MULTILINE` does not break the existing per-line `.match(stripped)`
calls inside `_infer_play_anchor` / `_infer_novel_anchor` — those operate on
single stripped lines where MULTILINE has no effect.

## Acceptance criteria

- [x] All three regex compiles in `corpus.py` carry
      `re.IGNORECASE | re.MULTILINE`.
- [x] A new unit test in `tests/unit/knowledge/test_corpus.py` uses a
      play-shaped fixture **with realistic front matter** (title, author,
      imprint paragraph, then `\nAct I\nScene 1\n...`) and asserts that
      primary chunks past the front matter carry a `PlayCitationAnchor`
      with the correct `act`/`scene`/`line`. Mirror with a novel fixture
      asserting `NovelCitationAnchor`.
- [x] Existing `MACBETH_FIXTURE` and `CHRISTMAS_CAROL_FIXTURE` tests still
      pass unchanged.
- [x] Re-running the loader-only smoke against
      `domains/gcse-english/sources/primary_text/macbeth.txt` shows
      `Primary chunks with citation_anchor` > 0 (most should be set;
      front-matter-region chunks may legitimately remain `None`).
- [x] No new `corpus.citation_anchor.inference_failed` warnings for chunks
      whose offset clearly falls inside the play body.

## Implementation Summary

Added `re.MULTILINE` to all three structural-marker compiles in
`corpus.py:414-422` (`_ACT_PATTERN`, `_SCENE_PATTERN`,
`_CHAPTER_PATTERN`) so the `_infer_citation_anchor` gate matches
`Act I` / `Chapter 1` headings anywhere in the file, not only at
start-of-string. Added two front-matter regression fixtures and tests
in `tests/unit/knowledge/test_corpus.py`
(`test_play_with_front_matter_still_yields_play_anchor`,
`test_novel_with_front_matter_still_yields_novel_anchor`) — each
fixture mirrors the Standard Ebooks shape (title / author / imprint
paragraph, blank lines, then `Act I` or `Chapter 1`).

**Verification**:
- Unit tests: 20/20 corpus tests pass (incl. 2 new front-matter regression tests)
- Loader-only smoke on real `domains/gcse-english/sources/primary_text/macbeth.txt`:
  201/210 primary chunks now carry `citation_anchor` (was 0/210 before fix).
  The 9 remaining anchor=None chunks land at chunk_index 0-6 (≤2,802 char
  Standard Ebooks editorial header) and 208-209 (end-matter / colophon)
  — none fall inside the play body, satisfying AC #5.
- 5 unrelated pre-existing failures (`test_coach_handover.py`,
  `test_graphiti_client_wiring.py`) confirmed pre-existing on `main` via
  stash.

## Notes / Lessons

- The bug was masked for the entire FEAT-PRV4 phase-1 because the unit
  fixtures (`MACBETH_FIXTURE`, `CHRISTMAS_CAROL_FIXTURE`) start with the
  structural marker on the very first non-blank line. The new
  front-matter fixtures close that test-coverage hole — any future
  re-introduction of the same `^`-anchored gate would now fail in CI.
- The internal walkers (`_infer_play_anchor`, `_infer_novel_anchor`)
  use `_ACT_PATTERN.match(stripped)` per stripped line, where MULTILINE
  has no effect, so adding the flag is safe for those call sites.
- Standard Ebooks layouts also have non-trivial *end* matter (colophon,
  about-the-author). Two end-matter chunks legitimately have no
  citation anchor; this is acceptable per AC and out of scope here.

## Out of scope

- Header-aware markdown chunker (separate follow-up — out of scope per
  TASK-REV-RAG4 review).
- Improving `_infer_play_anchor`'s line-counting strategy (e.g., Standard
  Ebooks line numbering vs. inferred line counts).
- Reconstructed Mr Bruff `.md` files in `secondary_study_guide/` —
  citation anchors are intentionally `None` for non-primary content.

## References

- TASK-RAG-CC1 (smoke run that surfaced this):
  [tasks/completed/TASK-RAG-CC1/TASK-RAG-CC1.md](../../tasks/completed/TASK-RAG-CC1/TASK-RAG-CC1.md)
- TASK-REV-RAG4 (parent review, links the incidental finding):
  [tasks/completed/TASK-REV-RAG4-course-correct-rag-docling-integration.md](../../tasks/completed/TASK-REV-RAG4-course-correct-rag-docling-integration.md)
- Affected loader: [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
- Affected tests: [tests/unit/knowledge/test_corpus.py](../../tests/unit/knowledge/test_corpus.py)
