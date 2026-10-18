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
   the Player quoted them correctly — the literal raw output (Python `repr`, from the deployed Player on the Dell) was
   `'In Act 1 Scene 7, Macbeth says:\n\n"I have no spur\nTo prick the sides of my intent, but only\nVaulting ambition,
   which o\'erleaps itself\nAnd falls on the other."'` (line breaks, **no** slashes — the " / " in earlier notes was
   editorial) and the corpus chunk reads `… I have no spur To prick the sides of my intent, but only Vaulting ambition,
   which o'erleaps itself And falls on the other.` (Codex R2) — and the learner received only the neutral text. Cause: retrieval is queried with the **learner's message**, and the one chunk that
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

**Per-reply, stable outcomes (Codex R1).** The streaming path re-verifies the growing reply at every boundary and once
more at the end, so the lookup is **reply-scoped and memoised**: production builds one `QuoteLookup` object per reply
(per verifier-factory call on the streaming path; per handover call — i.e. per Player attempt — on the non-streaming
path) holding a cache `span → chunks` and the budget counter. A span seen again gets the cached chunks (including an
empty result, an exception — cached as empty — or "over budget" — cached as empty) and never a second lookup. Each span
is matched against **the session's retrieved chunks plus its own lookup chunks only**, never another span's, so its
outcome depends only on `(span, session chunks, its own cached lookup)` and is identical on every pass: a later lookup
can never reclassify a span that was already released. The text handed to the Coach is unchanged in definition (what
the learner received).

Production wiring (`cli/main.py`, both the non-streaming handover closure and the streaming verifier factory) passes
`lookup = lambda span: retrieve(span, text_name=retrieval_text_name, focus_aos=(), subject=subject)` — the same subject,
text scope (the set text, or all of the subject's texts when there is none) and source filter as the session's own
retrieval, with the span itself as the query. No lookup is passed when the subject has no corpus (nothing to find).
A lookup that raises or returns nothing simply leaves the span unmatched (redacted) — fail closed.

**Event loop (Codex R3).** The lookup does network I/O (embedding) and runs the reranker. Neither production path is
off the loop today: `run_turn` calls `_apply_coach_handover` synchronously for the first response and every revision
(`orchestrator.py:556-558, 655-657`, closure call at `:1040`; HTTP `cli/main.py:973-984` and MCP `mcp/adapter.py:272-292`
await `run_turn` directly), and `run_turn_stream_verified` calls `verify(...)` directly at each boundary and at the end.
Both are changed to `await asyncio.to_thread(...)` (the handover for first response and revisions; each streaming
`verify` call), awaited in the same order, so ordering and the released-prefix invariant are unchanged.

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
* Stability (R1), streaming path: a reply with two quotes across several boundaries asserts the total lookup count
  (one per distinct unmatched span), that an earlier span's decision never changes on later passes (including when a
  later span's lookup returns the earlier span's chunk), that the output after each boundary is complete, and that the
  Coach input equals the concatenated learner deltas; budget exhaustion is likewise stable across passes.
* Incident fixture (R2): the literal Player output above, with the session's retrieved chunks lacking the "no spur"
  chunk and the lookup returning it, survives with its 1.7 citation through both paths; controls — the same span with
  one invented line substituted, and the incident's fabricated "Remorse … trống" line — are still redacted.
* Off-loop (R3): the handover (first attempt and a revision) and every streaming `verify` call run in a worker thread
  (asserted via the calling thread), on both production paths.
* Runtime on the Dell: the same robot-shaped probe returns the real "no spur" lines with their citation, and a request
  that elicits a misquotation still returns the neutral text.
