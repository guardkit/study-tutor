# RESULTS — Lane 2 step 1a: the `[rag]` image receipt (2026-08-01)

**Lane 2 step 1a of the plan of record (ungated, the plan's FIRST action).**
Build the `--extra rag` image variant on a branch, measure the image-size
delta and spark memory/cost, run the quote-retrieval smoke locally. This
receipt attaches to ruling-queue item 2 (Rich's `[rag]`-extra go for the
1b redeploy — which stays gated).

Everything below ran on the spark (`spark-fcf6`), 2026-08-01 evening,
against the live llama-swap `:9000`. The live tutor containers were not
touched.

## Verdict in one line

The `[rag]` extra works end-to-end on the spark — quote retrieval passes
3/3 on the full runtime path, at an image cost of **+0.96GB** once built
properly — **but** flipping the extra on alone would NOT light RAG in
prod: the shipped corpus is 768-dim (nomic-embed-era) and the spark's
llama-swap serves only a 1024-dim embedder (`embed` =
Qwen3-Embedding-0.6B; no `nomic-embed` alias). The store must be
re-embedded (demonstrated, ~2 min) or llama-swap must grow a nomic alias.

## 1. The build (branch `lane2/rag-image-1a`, three measured variants)

| Image | Size | Notes |
|---|---|---|
| `study-tutor:latest` (deployed) | 443MB | no `[rag]`; `rag_disabled reason=chromadb_missing` |
| naive `--extra rag` (`448bd2d`) | 10.3GB | ~4.9GB uv wheel cache accidentally baked into the sync layer + ~4.9GB venv |
| + BuildKit cache mount (`135c52c`) | 5.28GB | the honest cost of the naive dependency set |
| + CPU-torch index pin (`e3533f3`) | **1.4GB** | the right shape — smoke passes on this image |

Where the naive venv's ~4.9GB went: `nvidia/*` CUDA libs 2.79GB, `torch`
864MB, `triton` 599MB — **all dead weight**, because the runtime pins the
reranker to CPU (`retrieval.py:510`, `CrossEncoder(..., device="cpu")`)
and nothing else imports torch. Remainder: scipy 92MB, chromadb rust
bindings 52MB, transformers 48MB, onnxruntime 43MB, sklearn 40MB.

The CPU variant declares `torch>=2` in the `[rag]` extra (it was only
transitive before) and routes it through `[tool.uv.sources]` to
`download.pytorch.org/whl/cpu` (`[[tool.uv.index]]`, explicit). The lock
drops every `nvidia-*` package and `triton`; torch moves 2.11.0 →
2.13.0+cpu (the CPU index's version, inside sentence-transformers'
constraint). The retrieval smoke passes 3/3 on this image
(`study-tutor:rag-1a-cpu`, warm cache, `HF_HUB_OFFLINE=1`).

## 2. The embedding-space finding (blocks a naive 1b)

- Shipped store (`data/chroma`, ships in the image): collection
  `gcse-english-v1`, **dimension 768**, 581 chunks
  (sqlite: `SELECT name, dimension FROM collections` → `gcse-english-v1|768`).
  Ingested 2026-05-10 against the GB10-era `nomic-embed` alias.
- Spark llama-swap `/v1/models` today: `coach, embed, gemma4-tutor,
  gpt-oss-120b, granite-vision-4-1-4b, parakeet-tdt-0.6b-v3,
  qwen3-tts-0.6b, recruiter, recruiter-8b, tutor-coach, workhorse` —
  **no `nomic-embed`**. The embedder is `embed` = Qwen3-Embedding-0.6B,
  **1024-dim** (`/opt/llama-swap/config/config.yaml`).
- Consequence: with the extra installed and defaults untouched, wiring
  succeeds (`event=rag_wired` — note the actual event name; the plan
  previously said "rag_enabled", which does not exist in the code) but
  the first query embeds via the default `nomic-embed` model name →
  llama-swap unknown-model error. With `LLM_EMBEDDINGS_MODEL=embed` →
  1024-dim query against a 768-dim store → dimension mismatch. Exactly
  the failure mode DECISION-RAG-001 §3.1 warns about.

**Fix demonstrated:** faithful re-embed of the shipped store through the
spark's `embed` model — all 581 ids/documents/metadatas preserved
byte-for-byte, vectors rewritten at 1024-dim. Ran inside the rag-1a
image in ~2 minutes (73 batched `/v1/embeddings` calls, batches of 8,
respecting the 8192-token/request ceiling in the llama-swap config).
`reembed_done count=581`.

## 3. The quote-retrieval smoke (defined here; PASS 3/3, three runs)

Honesty note: ADR-ARCH-022's "golden-quote eval harness" (fabrication
rate < 5%) was a roadmap item (FEAT-PO-006-T3) and **was never built** —
there is no existing golden-quote artefact to run. What 1a ran instead
is a quote-retrieval smoke — necessary-but-not-sufficient for the S2
bar: one verbatim-quote query per corpus text, asserting the quote's
distinctive substring appears in the returned chunks. Needles were
verified present in the corpus (sqlite FTS) before the run, so a miss
would have meant retrieval failure, not a bad test.

Path exercised end-to-end inside the rag images: `build_rag_providers`
(the same call `serve` startup makes) → `event=rag_wired ...
primary_texts=3` → `retrieval.retrieve()` → chroma query (1024-dim
store) → query embed via llama-swap `embed` → AQA refusal filter →
`BAAI/bge-reranker-v2-m3` CPU rerank → primary-first ordering.

| text_name | query | chunks | needle found | mode | elapsed |
|---|---|---|---|---|---|
| macbeth | "Is this a dagger which I see before me" | 6 | ✅ (top chunk IS the dagger soliloquy) | rerank | 72.8s cold |
| an_inspector_calls | "We are members of one body" | 6 | ✅ | rerank | 8.7s |
| power_and_conflict_poems | "Look on my works ye Mighty and despair" | 6 | ✅ (Ozymandias) | rerank | 9.0s |

Runs 2 (`rag-1a`, warm cache + `HF_HUB_OFFLINE=1`) and 3
(`rag-1a-cpu`, same env): PASS 3/3 both, ~6.6s/turn warm — the offline
flag works once the reranker is cached (matters for prod: without it
every retrieval HEADs huggingface.co).

## 4. Spark memory/cost

- Live baseline: `study_tutor_http` idles at **73MiB**.
- Probe container peak during retrieval: **~1.19GiB** (the reranker
  weights dominate). Host headroom at measurement: 54GB available of
  121GB. The rag stack is comfortably affordable on the spark.
- First-ever retrieval additionally downloads the reranker from HF:
  **2.3GB** into `HF_HOME` (the 72.8s cold turn included this). The
  cache must persist (volume-mount `HF_HOME`, or bake the model into
  the image at +2.3GB) or every container restart repays it.
- **Perf finding for 1b:** `_load_reranker()` (`retrieval.py:494`)
  constructs a fresh `CrossEncoder` on **every** `retrieve()` call — no
  instance cache. Warm-path cost ≈ 3.5s construction + ~5.1s CPU rerank
  of 24 candidates ⇒ **~6.6–9s added per retrieval turn**. A small
  instance cache would cut ~3.5s of that; whether ~5s CPU rerank per
  turn fits the turn-latency budget (the unratified 90s deadlines) is a
  1b consideration. Selective retrieval (ADR-FLEET-002) already limits
  how many turns pay it.
- llama-swap handled the 581-chunk re-embed + all query embeds without
  incident.

## 5. What the gated 1b needs beyond this receipt

1. Rich's go on ruling-queue item 2, with this receipt.
2. A store decision: bake the 1024-dim re-embedded store into the image
   (deterministic, +6MB) vs re-embed at deploy vs add a `nomic-embed`
   alias to llama-swap (operator change; keeps the shipped store as-is).
3. Env block for the deployed container: `LLM_EMBEDDINGS_BASE_URL`
   (`http://host.docker.internal:9000/v1`), `LLM_EMBEDDINGS_MODEL=embed`,
   `HF_HOME` volume + `HF_HUB_OFFLINE=1` after first warm,
   `CHROMA_PERSIST_DIR`/`CHROMA_COLLECTION` if the store moves.
4. The reranker instance-cache fix (small, testable, pre-1b).
5. Prove `event=rag_wired` in the deployed container's logs + re-run
   this smoke against the deployed host (the 1b acceptance from the
   plan, s/rag_enabled/rag_wired/).
6. Explicitly NOT covered by 1a: the fabrication-rate golden-quote eval
   (S2's frozen bar — the harness remains unbuilt; Lane 2 step 3 must
   build it) and the citation-anchor break (581/581 since 2026-05-10 —
   still deferred, per Lane 2 step 3's "fix or explicitly defer").

## Receipts trail

- Branch `lane2/rag-image-1a`: `448bd2d` (--extra rag), `135c52c`
  (cache mount), `e3533f3` (CPU-torch pin + lock).
- Store dimension: sqlite query on `data/chroma/chroma.sqlite3`.
- Served models: `GET :9000/v1/models`, 2026-08-01.
- Re-embed + smoke logs: session transcripts 2026-08-01 evening
  (`reembed_done count=581`; `rag_smoke_verdict pass=true` ×3 runs).
- Size breakdown: `du -sm` inside `study-tutor:rag-1a` site-packages;
  `docker images` for the four size points.
