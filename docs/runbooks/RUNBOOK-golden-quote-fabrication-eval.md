# RUNBOOK — Golden-quote fabrication eval (the S2 measurement harness)

Lane 2 step 3 receipt venue. This harness measures the mission's S2 bar
and ADR-ARCH-022 D1's gate on THIS repo's runtime closure
(`_build_coach_handover` → retrieval → `apply_quote_verification`). It is a
**per-ingest / per-Player-model regression gate for this repo** — it is
deliberately NOT part of the sibling `fleet-evals` judging estate
(model-vs-model comparisons) and NOT a `qa/gates` black-box `:8110` probe;
do not consolidate it into either.

---

## 0. PRE-REGISTRATION (read and honour BEFORE any measured run)

Registered 2026-08-07, before any measured (generated-response) run has
ever been executed. The T2 smoke of 2026-08-07 (evidence dir) is a path
proof over constructed responses, not a measured run.

**The frozen bar (ADR-ARCH-022 D1, verbatim):** *"Gate: measure against
the golden-quote eval harness (fabrication rate target < 5% Phase A /
< 1% Phase B). The lexical path must not raise the verifier's
false-correction rate."* The mission (S2) freezes the same Phase A bar:
**fabrication < 5%, per subject with a corpus.** These numbers are frozen
here and may not be adjusted retroactively to fit a result.

**Re-run triggers (both mandatory):**
1. every Player-model change (fine-tune iteration, model swap, serving
   change), and
2. every corpus ingest (any `ingest_corpus.py` run that touches a wired
   collection).

**Metrics (frozen definitions):**

- **Fabrication rate** *(the target metric)* = extracted quoted strings
  with no ≥ 95% fuzzy match against the session text's corpus chunks ÷
  total extracted quoted strings. Extraction is INDEPENDENT of the runtime
  verifier: straight `"…"` and curly `“…”` double quotes, markdown
  block-quote runs (`> …` lines joined as one span), the `/` verse
  linebreak convention neutralised at match time; spans under 4 words
  ignored.
- **The fuzzy metric, precisely** (rapidfuzz is NOT a project dependency —
  checked `pyproject.toml`/lockfile 2026-08-07 — so the spec's
  `rapidfuzz.partial_ratio >= 95` is implemented in stdlib): normalise
  both sides (`/`→space, curly→straight quotes, whitespace runs collapsed,
  surrounding punctuation stripped, lower-case); slide word windows of
  size `n−2 … n+2` (n = quote word count) over each chunk; score each
  window with `difflib.SequenceMatcher(None, quote, window).ratio()`
  (= `2·M/T`, M = matching characters, T = total characters of both
  strings); a quote **matches** iff its best ratio ≥ **0.95** (an exact
  normalised substring short-circuits to 1.0). This is a character-ratio
  metric, not token-set partial_ratio — close but not identical to
  rapidfuzz; the 0.95 threshold is frozen with the metric.
- **Citation coverage** = verified matches (primary + fuzzy) that carry a
  citation anchor ÷ all verified matches, computed from the additive
  `VerifierMetadata.anchorless_*` counters. Against the shipped
  581/581-anchorless store this is honestly **0%** until Track B lands.
- **False-correction scaffold** = verifier rewrites (fuzzy corrections AND
  no-match strips) whose ORIGINAL span had a ≥ 95% match anywhere in the
  corpus (any text). Counted and itemised, not yet a bar. **Honest
  limits:** it can only see editions that are IN the corpus. A quote that
  is correct in an edition absent from the store (e.g. Folger wording the
  2026-05-10 docling-VLM ingest dropped at page breaks) is scored
  *fabricated* by the rate metric and is invisible to this scaffold; and a
  fuzzy "correction" toward a store typo (see `qf-poems-brains-ache`) is
  flagged only because the original ALSO near-matches the store. Judged
  adjudication of flags (reusing the `judge_prepare`/`judge_resolve`
  blinding) is a possible future tier; nothing judged runs today.

**Golden set:** `scripts/eval/golden_quotes.jsonl` — 29 items across all
three texts (`macbeth` 12, `an_inspector_calls` 8,
`power_and_conflict_poems` 9), including the four rag-grounding-design §4
seed cases VERBATIM (pinned by test). Every item carries a `source_check`
note recording its verbatim verification against the shipped store
(read-only sqlite, `immutable=1`, 2026-08-07). Extensions are additive
only; the four seeds are immutable; every new item must be
store-verified the same way and must NEVER contain AQA assessment
material (law 4 — the schema validator rejects assessment-material
markers; poem items quote only public-domain poets' text).

**Store-truth findings recorded at registration** (they shape expected
results and are themselves Lane 2 findings): the shipped store is missing
canonical lines at docling page breaks — `qf-macbeth-unsex` ("unsex me
here", best ratio 0.52), `qf-macbeth-damned-spot` ("Out, damned spot",
0.60) and `qf-inspector-own-business` (0.81) are ABSENT; 
`qf-macbeth-innocent-flower` is split by a page-number artifact (0.958 —
above threshold, but verifier edit distance 4 → stripped at runtime);
`qf-poems-brains-ache` carries a store typo ("merciles … knife" for
Owen's "merciless … knive", 0.976). Items are categorised
(`recall` / `control` / `fabrication_bait` / `store_gap` /
`edition_variant`) so measured runs can be read per class: a `store_gap`
"fabrication" is a corpus defect, not a Player lie — report both numbers,
never silently exclude.

---

## 1. Harness inventory

| piece | path |
|---|---|
| Golden set | `scripts/eval/golden_quotes.jsonl` |
| Runner (T1/T2, verify-only or `--generate`) | `scripts/eval/run_fabrication_eval.py` |
| Scorer (markdown table, frozen bar) | `scripts/eval/score_fabrication.py` |
| Hermetic tests | `tests/unit/knowledge/test_fabrication_harness.py` |
| Evidence | `docs/runbooks/evidence/golden-quote-fabrication-eval/` |

## 2. T1 — hermetic tier (CI-safe, no network)

Fake in-memory collection wired via `retrieval.set_collection_provider` +
ImportError reranker factory (the `tests/integration/test_cli_rag_wiring.py`
pattern); the fake corpus is built from the golden set itself with
`citation_anchor=None` chunks, mirroring the shipped store's anchorless
reality. Verifies the harness plumbing + verifier semantics, not the real
store.

```bash
uv run python scripts/eval/run_fabrication_eval.py \
  --tier t1 --responses <responses.jsonl> --out /tmp/t1_results.jsonl
uv run python scripts/eval/score_fabrication.py /tmp/t1_results.jsonl
```

`<responses.jsonl>` is one `{"id": ..., "response": ...}` per line. The
same flow runs inside the hermetic test suite (T1 end-to-end tests).

## 3. T2 — in-process vs the REAL baked store + real embedder (primary tier)

No deploy, no container touched. Requirements: llama-swap `:9000` serving
`embed`; the pre-warmed HF cache at `/opt/study-tutor/hf-cache`.

Env pins (the runner sets these defaults itself if unset — outside
docker-compose the embedding-function module defaults are WRONG for the
1024-dim baked store):

```
LLM_EMBEDDINGS_MODEL=embed
LLM_EMBEDDINGS_BASE_URL=http://localhost:9000/v1
HF_HOME=/opt/study-tutor/hf-cache
HF_HUB_OFFLINE=1
```

Store access is READ-ONLY by discipline: the fabrication-metric corpus is
read via sqlite `immutable=1`; the retrieval path opens the store through
`CHROMA_PERSIST_DIR` (`--persist-dir`). Two sanctioned ways to point at
the baked store from a worktree (which has no `data/chroma/`):

1. **Scratch copy (recommended, what the smoke did):** `cp -r` the store
   (~7 MB) to a scratch dir and pass that — absolute isolation; verify
   sha256 equality to prove you measured the real bytes.
2. **Symlink** `data/chroma` → the main checkout's `data/chroma`
   (gitignored, must never be committed) — accepts chroma's own sqlite
   bookkeeping writes against the real store; never run ingest/reset
   against it.

Verify-only (default):

```bash
uv run python scripts/eval/run_fabrication_eval.py \
  --tier t2 --persist-dir <store> \
  --responses <responses.jsonl> --out results.jsonl
```

Measured run (generation ON — this is what the frozen bar judges):

```bash
uv run python scripts/eval/run_fabrication_eval.py \
  --tier t2 --persist-dir <store> \
  --generate --model gemma4-tutor --endpoint http://localhost:9000/v1 \
  --out results.jsonl
uv run python scripts/eval/score_fabrication.py results.jsonl --out RESULTS-<date>.md
```

Generation uses the tutor system prompt = `roles/tutor/prompts/player.md`
minus its leading HTML comment, via the A/B harness's client
(`scripts/eval/run_ab_eval.generate`, `<think>` blocks stripped). Note the
verifier judges quotes against the **retrieved top-6** (production
behaviour), while the fabrication metric matches against the **whole
text's chunks** — a genuine quote the retriever missed shows up as a
strip flagged by the scaffold, which is exactly the signal wanted.

## 4. T3 — LIVE `:8100` corroboration (OPERATOR-ONLY, named, optional)

Named here per the build order; **operators only** (it writes real
sessions to the deployed server): `POST /api/sessions/start` then a turn
`POST`, bearer auth in table mode; the wire response carries only
`tutor_response` (no `VerifierMetadata` crosses the frozen §7 contract),
so the only observable is the rewritten text — low yield; use T2 for
metadata-bearing measurement. Never run this from a build lane.

## 5. T2 smoke receipt (2026-08-07)

`evidence/golden-quote-fabrication-eval/T2-SMOKE-2026-08-07.md` — N=4
seed items, verify-only, through the REAL closure against a byte-identical
copy of the baked store: the correct Macbeth quotes returned as
**anchorless primary matches WITHOUT citation (not a strip, not an
exception)** — the Track A fix proven on the production path; the known
fabrication stripped + counted; the innocent-flower store-artifact strip
flagged by the false-correction scaffold.

## 6. Track B deferral receipt (anchors — content work, GATED, DEFERRED)

The shipped store is 581/581 anchorless (2026-05-10 docling-VLM re-ingest
regression; the anchoring code itself is correct and was receipted 95%
(201/210) on Standard Ebooks Macbeth at `f7f0cdb0`). Restoring anchors is
content work whose tail is re-ingest ⇒ re-embed ⇒ image rebuild ⇒
redeploy — **gated on Rich, deferred by this lane** with costs from the
design pass:

- **B1 — Macbeth via Standard Ebooks plain text: the cheapest next win.**
  The play inferer is already proven at 95% on that edition; lights 253
  chunks, and would also restore the canonical lines the VLM dropped at
  page breaks (`unsex me here`, `Out, damned spot` — both currently
  scored fabricated for correct students).
- **B2 — poetry anchors: needs a design decision first.**
  `PoemCitationAnchor(poem_title, line)` + a third router arm + per-poem
  splitting; a new union member is a schema change ⇒ `--reset` re-ingest;
  ~0.5–1 day.
- **B3 — Inspector act headings: uncertain, least rewarding.** Re-derive
  via docling layout mode or post-processing; ~0.5 day.

Until B lands, citation coverage reads 0% by construction and the
`anchorless_*` counters are the honest measure of verified-but-uncited
quotes.
