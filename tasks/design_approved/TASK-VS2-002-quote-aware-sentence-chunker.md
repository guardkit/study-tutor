---
complexity: 7
dependencies: []
feature_id: FEAT-VOICE-002
id: TASK-VS2-002
implementation_mode: task-work
parent_review: TASK-REV-F732
status: design_approved
task_type: feature
title: Quote-aware sentence chunker + ADR-ARCH-027 chunk-boundary verification gate
  (fail-closed)
wave: 1
---

## Description

New pure module `src/study_tutor/tutoring/sentence_chunker.py`: the
sentence-chunk buffer at the design §5.3 pin (~15–25 words, breaks only at
sentence boundaries; an answer shorter than one chunk is a single chunk —
ASSUM-001) with the ADR-ARCH-027 verification gate.

**Quote-aware boundaries (the ADR-027 straddling obligation, concretely):**
`verify_quotes` (`knowledge/quote_verifier.py`) only recognises a quotation
once its *closing* mark is seen, so a chunk boundary must be deferred past its
nominal word-count target while an odd number of quote marks is pending in the
buffer — never close a chunk mid-quote.

**Verification gate:** on each candidate chunk close, call the existing
`apply_quote_verification` (`knowledge/coach_handover.py:61`) against the
**full accumulated text so far** (never the isolated chunk); release only the
newly-completed, verified suffix. Released text is never retroactively altered.

**ASSUM-007 fail-closed — deliberate policy divergence:** the existing
`apply_quote_verification` swallows verifier exceptions and returns the
unannotated response with `metadata.verifier_exception=True` (graceful
degradation for the non-streaming path). This streaming gate must inspect that
flag and **fail closed** — raise, ending the turn — rather than yield the
unverified chunk. Do **not** modify `coach_handover.py` or
`quote_verifier.py`; this is new streaming-only policy layered on the existing
pure functions.

## Acceptance Criteria

- [ ] Token stream with a quotation whose opening mark falls in the final words of a nominal chunk and closing mark in the next: chunk is NOT released until the quote closes and verification passes, and `apply_quote_verification` is invoked with accumulated text, not the isolated chunk substring
- [ ] Idempotent-prefix test: previously-released chunk text is never retroactively altered by any later verification pass
- [ ] Forcing `verifier_exception=True` on a mid-stream chunk makes the generator raise/stop rather than yield the unannotated chunk (ASSUM-007 fail-closed)
- [ ] Answer shorter than one chunk's worth of words yields exactly one chunk covering the whole answer (ASSUM-001); multi-sentence answers break only at sentence boundaries with each chunk roughly 15–25 words
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "An unverifiable quotation is corrected before it is shown or spoken" (@smoke)
- "A short answer is spoken as a single chunk"
- "A long answer is spoken in complete-sentence chunks of roughly the pinned size"
- "A quotation straddling a chunk boundary is still verified as one quotation"
- "Quote verification cannot complete for a sentence"

## Seam Tests

No transport/LLM/TTS boundary crossed (pure module). The produced
`VERIFIED_CHUNK_ITERATOR` contract is pinned here for consumers:

```python
"""Seam test: verify VERIFIED_CHUNK_ITERATOR contract for TASK-VS2-003/007."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("VERIFIED_CHUNK_ITERATOR")
async def test_chunker_yields_verified_chunks_with_seq():
    """Contract: async generator yielding (chunk_text: str, seq: int) per
    VERIFIED chunk only, seq strictly increasing from 0; raises on
    verifier_exception=True. Producer: TASK-VS2-002 (this task);
    consumers: TASK-VS2-003 (token frames), TASK-VS2-007 (TTS trigger).
    """
    chunks = [c async for c in chunk_stream(fake_tokens(), verifier=passing_verifier)]
    assert [seq for _, seq in chunks] == list(range(len(chunks)))
    assert all(isinstance(text, str) and text for text, _ in chunks)
```

## References

- ADR-ARCH-027 (straddling-quote obligation) · design §5.3/§5.4 · ASSUM-001/007 · `knowledge/coach_handover.py:61` (`verifier_exception` flag) · `knowledge/quote_verifier.py:593` · review report Material Findings 1 & 4