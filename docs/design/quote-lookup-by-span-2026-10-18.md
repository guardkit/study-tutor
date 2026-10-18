# Design — look up each unmatched quote by its own words before redacting it

2026-10-18 · follow-on to [quote-law3-no-unverified-quote-2026-10-18.md](quote-law3-no-unverified-quote-2026-10-18.md)
(merged `0ea2103`, deployed on the Dell). Rich's instruction (18 Oct): work the remaining items with `cross-model-build`.

## What the live deploy showed

Two findings on the Dell after the law-3 deploy, 18 Oct:

1. **Retrieval had been dead on the Dell since the move.** The corpus (`data/chroma`, built 10 May with `nomic-embed`,
   768-dim) no longer matched the Dell's `embed` alias (Qwen3-Embedding 0.6B, 1024-dim): every Chroma query raised
   `InvalidArgumentError: Collection expecting embedding with dimension of 768, got 1024`, which `_query_collection`
   turns into an empty result (`retrieval.query_failed`, detail only in `extra`). **Fixed operationally** the same day by
   the RAG runbook's own re-ingest (`scripts/ingest_corpus.py --reset`, same 581 chunks, now 1024-dim; old corpus backed
   up at `~/backups/study-tutor-chroma-nomic768-20261018` on the Dell); the image was rebuilt and redeployed;
   `chunks=6` per turn now.
2. **Strict mode now over-redacts genuine quotes.** A robot-shaped session asked for Macbeth 1.7's "no spur" lines;
   the Player quoted them correctly (`"I have no spur / To prick the sides of my intent, but only / Vaulting ambition,
   which o'erleaps itself / And falls on the other."` — identical to the corpus text bar line breaks), and the learner
   received only the neutral text. Cause: retrieval is queried with the **learner's message**, and the one chunk that
   holds those lines was not among the 6 returned (all 6 were other Macbeth chunks). The verifier only ever sees the
   retrieved chunks, so a correct quote becomes `NoMatch` and is redacted.

Law 3 holds (nothing unverified is released), but the tutor can rarely quote at all — that defeats the point.

## The fix — Q3: a quote-anchored lookup, strict mode only

`verify_quotes` / `apply_quote_verification` gain an optional keyword `lookup: Callable[[str], Sequence[CorpusChunk]]
| None = None`. In strict mode, for each span that the existing matcher leaves unmatched (a `NoMatch`, or a short span
with no exact match), the verifier calls `lookup(span)` once, merges the returned chunks with the session's retrieved
chunks, and re-runs the **same** matcher (exact / fuzzy / cross-text rules unchanged). Only a span still unmatched after
that is redacted. At most `MAX_QUOTE_LOOKUPS_PER_REPLY = 4` lookups per reply; any unmatched span beyond that is redacted
without a lookup (bounded latency).

Production wiring (`cli/main.py`, both the non-streaming handover closure and the streaming verifier factory) passes
`lookup = lambda span: retrieve(span, text_name=retrieval_text_name, focus_aos=(), subject=subject)` — the same subject,
text scope (the set text, or all of the subject's texts when there is none) and source filter as the session's own
retrieval, with the span itself as the query. No lookup is passed when the subject has no corpus (nothing to find).
A lookup that raises or returns nothing simply leaves the span unmatched (redacted) — fail closed.

**Event loop.** The lookup does network I/O (embedding) and the reranker. The non-streaming handover already runs off the
loop. On the streaming path the per-boundary and final `verify(...)` calls in `run_turn_stream_verified` are made
directly on the event loop today; with a lookup wired they are moved to `asyncio.to_thread`, preserving their order and
the released-prefix invariant.

### Not chosen

* **Bigger `n_results`** for the learner-message query: still misses quotes far from the question's wording.
* **Exact match over the whole corpus in memory**: catches only verbatim quotes and needs a corpus cache; the lookup
  covers fuzzy too, through the existing matcher.
* **Robot sending a set text**: helps ranking but not the learner-message-vs-quote mismatch.

## Acceptance

* Hermetic suite green; existing law-3 tests unchanged (default `lookup=None` keeps today's behaviour).
* New tests (both production paths where applicable, asserting every emitted delta and Coach input == learner text):
  a correct quote absent from the session's retrieved chunks but returned by the lookup survives (with its citation);
  a fabricated quote whose lookup returns unrelated chunks is still redacted; a lookup that raises fails closed; the
  per-reply cap redacts the fifth unmatched span without a lookup; the lookup uses the session's subject and text scope;
  the streaming path calls `verify` off the event loop when a lookup is wired.
* Runtime on the Dell: the same robot-shaped probe returns the real "no spur" lines with their citation, and a request
  that elicits a misquotation still returns the neutral text.
