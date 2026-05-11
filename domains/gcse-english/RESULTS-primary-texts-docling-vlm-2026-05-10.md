# RESULTS: Ingest Primary Texts via Docling VLM → study-tutor Chroma

**Date:** 2026-05-10 (afternoon — single end-to-end run)
**Operator:** Claude Code (Opus 4.7, 1M context) — interactive execution of [`RUNBOOK-primary-texts-docling-vlm.md`](RUNBOOK-primary-texts-docling-vlm.md)
**Machine:** GB10 (`promaxgb10-41b1`) — single-host, all-local (study-tutor + llama-swap + vllm-docling + Chroma persist all on `localhost`)
**study-tutor HEAD:** `14c13db` (clean tree, doc-only file changes pre-existing)
**docling-dgx-spark-scripts HEAD:** `56e6a85`
**VLM:** `ibm-granite/granite-docling-258M` (revision `untied`) via `vllm` on `localhost:8002`
**Embeddings:** `nomic-embed` via llama-swap on `localhost:9000`
**Companion file:** [`RUNBOOK-primary-texts-docling-vlm.md`](RUNBOOK-primary-texts-docling-vlm.md)

**Outcome:** ✅ **CORPUS LANDED.** 3 PDFs → 3 markdown files via Granite Docling VLM (zero `<loc_X>` leakage), → 581 chunks ingested into ChromaDB `gcse-english-v1` with 0 refusals, sidecar index registers all three `text_name`s, smoke retrieval returns the dagger soliloquy as top hit for "Is this a dagger which I see before me" with `text_name=macbeth, source_type=PRIMARY_TEXT`. RAG end-to-end is wired and queryable.

**Caveat:** Every chunk (581/581) failed `citation_anchor` inference. Retrieval works; per-chunk citation anchors do not. Two systemic causes — VLM output flattens act/scene line-leaders into prose (Macbeth), and `_infer_citation_anchor` has no schema for poetry (Power & Conflict). Detail in **Findings → F2** below.

**Followups before this is "demo-ready" for citation work:** see **Followups** section. None of them block retrieval; all of them block crisp Act/Scene/Line citation rendering.

---

## Phase × gate summary

| Phase | Gate | Outcome | Evidence |
|---|---|---|---|
| 0.1 | 3 source PDFs present at `~/docling/english/actual_texts/` | ✅ `macbeth.pdf` 820 KB, `An_Inspector_Calls_-_JB_Priestley.pdf` 225 KB, `All-Power-Conflict-Poems.pdf` 1.8 MB | `ls -la` |
| 0.2 | docling scripts + venv | ✅ `docling-process.sh`, `vllm-docling.sh` present; `~/.venv/docling/bin/python` exists from prior runs | — |
| 0.3 | Docker + GPU | ✅ docker ok; NVIDIA GB10 listed | `nvidia-smi` |
| 0.4 | llama-swap embeddings | ✅ `nomic-embed` present (alongside `architect-agent`, `gemma4-tutor`, `qwen36-workhorse`, `qwen-graphiti`) | `/v1/models` |
| 0.5 | study-tutor target dir | ✅ `domains/gcse-english/sources/primary_text/` empty (just `.keep`) | `ls -la` |
| 1 | Start `vllm-docling` container, model loads | ✅ container `vllm-docling` started; health endpoint up after polling; `/v1/models` lists `granite-docling-258M` `max_model_len=8192` | `docker logs`, `curl /health`, `curl /v1/models` |
| 2 | Docling VLM processing of 3 PDFs | ✅ 3/3 succeeded, 0 failed, **392.8s total** (52.6s + 140.5s + 199.7s) | [`processing_manifest.json`](#evidence-index) |
| 2.1a | Output count | ✅ 3 .md files in `~/docling/english/actual_texts_md/` | `ls -la` |
| 2.1b | `<loc_X>` tag check (bug-#2868 workaround) | ✅ **0** in every file | `grep -c 'loc_[0-9]' *.md` |
| 2.1c | Macbeth structural markers | ⚠️ ACT/SCENE present in *prose* (search-matches: 6) but only 1 line *starts* with ACT (the table-of-contents line). VLM flattened the act/scene headings into flowed paragraphs. | `grep -cE '^\s*(ACT\|Act)\s+[IVX0-9]'` = 1; `grep -cE '(ACT\|Act)\s+[IVX0-9]'` = 6 |
| 2.1d | Inspector Calls structural markers | ⚠️ **0** structural ACT line-leaders, **0** ACT substring matches at all (Priestley's "ACT ONE"/"ACT TWO"/"ACT THREE" headings absent in VLM output) | `grep -cE '(ACT\|Act)\s+(ONE\|TWO\|THREE\|I\|II\|III\|1\|2\|3)'` = 0 |
| 2.1e | Poems anthology readability | ✅ each of the 15 AQA Power & Conflict poems is identifiable by name in-text (Ozymandias, London, The Prelude, My Last Duchess, Charge of the Light Brigade, Exposure, Storm on the Island, Bayonet Charge, Remains, …) | `head -60` |
| 3 | Copy with corpus-friendly names | ✅ `macbeth.md`, `an_inspector_calls.md`, `power_and_conflict_poems.md` in `domains/gcse-english/sources/primary_text/` | `ls -la` |
| 4.0 | `uv sync --extra rag` | ✅ env solved; chromadb / sentence-transformers / torch / transformers / openai stack in place | (background task, ~3 min cold) |
| 4.1 | `python scripts/ingest_corpus.py` | ✅ `chunks_created=581`, `refusals=0`, `skips=4` (the four `.keep` placeholders — expected); per-text counts: `an_inspector_calls=274`, `macbeth=253`, `power_and_conflict_poems=54` | [`/tmp/ingest-corpus.log`](#evidence-index) — `ingest_summary` line |
| 4.1' | Citation anchor inference | ❌ **581 / 581 chunks** logged `corpus.citation_anchor.inference_failed` — see Finding F2 | `grep -c citation_anchor.inference_failed` = 581 |
| 4.2a | Chroma persist artefacts | ✅ `data/chroma/chroma.sqlite3` 6.0 MB + UUID-named subdir `ad796eac-37cf-4c4d-a7a2-b2e0e3fc2ac5/` | `ls -la data/chroma/` |
| 4.2b | Sidecar index | ✅ `.primary_text_index` lists exactly `an_inspector_calls`, `macbeth`, `power_and_conflict_poems` (3 lines, 52 bytes) | `cat data/chroma/.primary_text_index` |
| 4.3 | Smoke retrieval (corrected — runbook example was stale, see F1) | ✅ k=3 hits for "Is this a dagger which I see before me" all `text_name=macbeth, source_type=SourceType.PRIMARY_TEXT`. **Top-1** hit is the actual soliloquy: *"…Is this a dagger which I see before me, The handle toward my hand?…"*. Hits 2-3 are Lady Macbeth's dismissal ("…the very painting of your fear: This is the air-drawn dagger which, you said, Led you to Duncan…") and Macbeth's continuation ("…shall'st me the way that I was going; And such an instrument I was to use…"). | inline `python -c` via `uv run` |
| 5 | Stop VLM container | ✅ `docker ps --filter name=vllm-docling` empty after stop | — |

## Findings

### F1 — Runbook §4.2 smoke-test snippet is stale (DOCS BUG)

**Symptom:** Following [`RUNBOOK §4.2`](RUNBOOK-primary-texts-docling-vlm.md#L222-L232) verbatim:

```python
from study_tutor.knowledge.retrieval import build_retriever
r = build_retriever()
hits = r.retrieve('Is this a dagger which I see before me', k=3)
for h in hits:
    print(h.metadata.get('text_name'), '|', h.metadata.get('source_type'), '|', h.page_content[:80])
```

raises `ImportError: cannot import name 'build_retriever' from 'study_tutor.knowledge.retrieval'`.

**Cause:** The `retrieval` module no longer exposes a `build_retriever` factory or a langchain-style retriever-with-`.metadata`/`.page_content` shape. The current API ([`src/study_tutor/knowledge/retrieval.py:688`](../../src/study_tutor/knowledge/retrieval.py#L688)) is a module-level `retrieve(query, text_name, focus_aos, top_k)` returning `list[CorpusChunk]`, where `CorpusChunk` exposes attributes `text`, `source_type`, `source_path`, `text_name`, `citation_anchor`, `chunk_index`. Collection wiring is owned by [`src/study_tutor/cli/rag_wiring.py:92`](../../src/study_tutor/cli/rag_wiring.py#L92) (`build_rag_providers`) — which the runbook example skips entirely, and which is *required* (otherwise `_collection_provider is None` short-circuits to `[]` at [`retrieval.py:738`](../../src/study_tutor/knowledge/retrieval.py#L738)).

**Working replacement** (verified during this run):

```python
from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.knowledge.retrieval import retrieve

build_rag_providers(role_config=None)  # role_config currently unused
hits = retrieve(
    'Is this a dagger which I see before me',
    text_name='macbeth',
    focus_aos=set(),
    top_k=3,
)
for h in hits:
    print(h.text_name, '|', h.source_type, '|', h.text[:120].replace('\n', ' '))
```

Also note: the runbook says `python scripts/ingest_corpus.py` and `python -c …`, but `python` isn't on `PATH` in this env (`uv sync` puts the interpreter inside `.venv/`). The working invocation is `uv run python …`. Worth a one-line footnote in the runbook so a fresh operator doesn't trip on it.

**Fix:** Patch §4.2 with the snippet above and prefix all `python …` invocations with `uv run`. Repository scope: study-tutor (this runbook).

### F2 — Citation anchor inference fails for **every** chunk (RETRIEVAL OK, CITATIONS DEGRADED)

**Symptom:** Ingestion log emits exactly **581** `corpus.citation_anchor.inference_failed` warnings — one per chunk created. Stored chunks have `citation_anchor=None` across the board. Retrieval still works (vector similarity is independent of anchor); generated turns won't be able to render Act/Scene/Line citations on this corpus.

**Mechanism** ([`src/study_tutor/knowledge/corpus.py:427-512`](../../src/study_tutor/knowledge/corpus.py#L427)):

`_infer_citation_anchor` routes by structural pattern:
1. If `_ACT_PATTERN.search(file_text)` matches anywhere → `_infer_play_anchor`. The play inferer then walks the file *line-by-line* with `_ACT_PATTERN.match(stripped)` — i.e., it requires ACT/SCENE markers to **start a line**.
2. Else if `_CHAPTER_PATTERN.search` matches → `_infer_novel_anchor` (analogous chapter+paragraph state machine).
3. Else → `None` (poetry has no schema in `_infer_citation_anchor`).

Per-text per-mechanism breakdown:

| `text_name` | Chunks | Failures | Why |
|---|---|---|---|
| `macbeth` | 253 | 253 | VLM output flattens the play into long flowed paragraphs. ACT/SCENE markers exist *inline* (6 substring matches with `(ACT\|Act)\s+[IVX0-9]`) but only 1 line *starts* with `ACT` — the giant first-line table-of-contents (`"Contents ACT I ......... 3 SCENE I. ......... 3 …"` all on one wrapped line). `_ACT_PATTERN.search` fires, so the file routes to the play branch — but the line-by-line state machine sees no ACT line-leaders inside the body, so `act` never advances past `None` and every chunk returns `None`. |
| `an_inspector_calls` | 274 | 274 | VLM output contains **zero** ACT substring matches at all (0 with `(ACT\|Act)\s+(ONE\|TWO\|THREE\|I\|II\|III\|1\|2\|3)`). Priestley's "ACT ONE / ACT TWO / ACT THREE" headings didn't survive the VLM render. `_ACT_PATTERN.search` doesn't fire; `_CHAPTER_PATTERN.search` doesn't fire (it's not a novel); top-level `_infer_citation_anchor` returns `None` for every chunk. |
| `power_and_conflict_poems` | 54 | 54 | Poetry: no acts, no chapters. There is currently **no anchor inferer for poetry** in [`corpus.py`](../../src/study_tutor/knowledge/corpus.py) — `_infer_citation_anchor` has only `_infer_play_anchor` and `_infer_novel_anchor`. A poem-anchor schema (e.g., `(poem_title, line_number)` or `(poem_title, stanza, line)`) would be a new feature, not a fix. |

**Fix options** (none are one-liners; pick by priority):

- **(A) Macbeth — switch to Standard Ebooks plain-text** as [`RUNBOOK Troubleshooting §B`](RUNBOOK-primary-texts-docling-vlm.md#L264-L270) anticipates. The Standard Ebooks edition preserves `Act I`/`Scene I.` as line-leading headings, which the existing `_infer_play_anchor` is built for. Keeps Macbeth on the play schema and lights up 253 chunks. Repository scope: study-tutor (corpus content, not code).
- **(B) Inspector Calls — re-derive structural headings.** Either re-run docling with a layout option that preserves the act headings as a separate token stream, or post-process the markdown to re-insert `## ACT ONE`/`## ACT TWO`/`## ACT THREE` at the right offsets (the act boundaries are findable from stage directions). Without (B), `an_inspector_calls` stays anchorless. Repository scope: study-tutor (corpus content, plus possibly a small post-processor).
- **(C) Add a poetry anchor inferer** to `_infer_citation_anchor`. Smallest sane schema: `PoemCitationAnchor(poem_title: str, line: int)` — pattern-match on `^[A-Z][A-Za-z' ]+$`-style poem-title line-leaders followed by numbered or unnumbered verse. The current `power_and_conflict_poems.md` has each poem's title as its own line (visible in the head-60 preview). This would land all 54 chunks. Repository scope: study-tutor (`knowledge/corpus.py` — new feature, requires DECISION-RAG-style sign-off).
- **(D) Split the Power & Conflict anthology into 15 per-poem files** (already flagged as a future task in [`RUNBOOK §3 note`](RUNBOOK-primary-texts-docling-vlm.md#L182-L186)). This makes `text_name=ozymandias`, `text_name=london`, etc., so the `text_name` itself carries the poem-level citation; line-anchor schema (C) then only needs to count lines within the file. (D) and (C) are complementary, not exclusive.

**Recommended order:** (A) for the Macbeth quick win → (D) to refactor poems → (C) to add the poetry anchor. (B) is the least-rewarding (one play, requires manual heading reinsertion) but unavoidable if Inspector Calls citations matter for the demo.

### F3 — `processing_manifest.json` and run timings (informational)

VLM throughput on the GB10 with `--gpu-memory-utilization 0.05` (i.e., a small slice of total GPU memory):

| File | Chars | Seconds | Chars/sec |
|---|---|---|---|
| `All-Power-Conflict-Poems.md` | 22,240 | 52.6 | 423 |
| `An_Inspector_Calls_-_JB_Priestley.md` | 112,983 | 140.5 | 804 |
| `macbeth.md` | 104,186 | 199.7 | 522 |
| **Total** | **239,409** | **392.8** | **609** |

Inspector Calls is the fastest per-character despite being the smallest after the poems — likely because the scanned-paperback layout has fewer table/figure regions than Macbeth's multi-column play layout. All three under 4 minutes/file matches the runbook's "~3-4 min/file" expectation.

---

## What's working — the corpus-to-RAG path is end-to-end green

- **VLM container lifecycle** — start/stop scripts work, health endpoint becomes live within ~60s, `<loc_X>` post-hoc stripping (Docling bug-#2868 workaround) catches every output. Zero leakage.
- **Docling VLM 258M model** is sufficient for these three formats. No OOM, no nvrtc errors, no `CUDA_VISIBLE_DEVICES` weirdness.
- **`scripts/ingest_corpus.py`** ran cleanly first try: chunked all three files, registered `text_name`s in the sidecar, persisted Chroma, called the embeddings backend successfully (single embeddings POST succeeded with HTTP 200 against `localhost:9000`).
- **AQA refusal regex** correctly *did not* fire — none of the three filenames match `past_paper|mark_scheme|examiner_report` (Phase 3 renames are deliberately neutral, per the runbook's design).
- **Retrieval semantic quality** is good — top-1 for the dagger soliloquy *is* the dagger soliloquy. The reranker ([`retrieval.py:494`](../../src/study_tutor/knowledge/retrieval.py#L494) loads its weights through `sentence-transformers`/HF Hub at first call; one-time download warning observed) re-orders per-text candidates correctly.

The "ingest one new GCSE primary text" loop is ~5 minutes wall-clock once the operator knows the runbook (Phase 2 is the only slow phase). The 3-PDF run took ~22 minutes including container cold-start, processing, ingestion, and verification.

---

## Followups (in priority order)

1. **Patch [`RUNBOOK §4.2`](RUNBOOK-primary-texts-docling-vlm.md#L222-L232)** with the working smoke-test snippet from F1, and prefix all `python …` calls with `uv run`. Smallest, fastest fix; unblocks the next operator. (See also runbook §4 line 199 — `python scripts/ingest_corpus.py`.) Repository scope: study-tutor.
2. **Decide the citation-anchor strategy** (F2 fix options A-D). For a demo where citation anchors matter, recommend (A) immediately for Macbeth and bundle (D)+(C) as a single follow-up task for the AQA poetry anthology. Inspector Calls (B) is the awkward middle case — mark as known-degraded if no demo turn requires citing it precisely.
3. **Add a regression check to ingestion** that fails (or at minimum logs at WARNING level with a count, not 581 separate WARNINGs) when *all* chunks of a `text_name` come back with `citation_anchor=None`. Today the situation is invisible past the per-chunk warning spam. A one-line summary at the end (`event=citation_anchor_summary text_name=… anchored=0 unanchored=253`) would make the gap obvious from the ingest output. Repository scope: study-tutor (`scripts/ingest_corpus.py` and/or `knowledge/corpus.py`).
4. **Consider committing `domains/gcse-english/sources/primary_text/*.md`** (or, more likely, *not* — the corpus guide says no source files commit). Either way, document the policy in [`CONTRIBUTING-CORPUS.md`](sources/CONTRIBUTING-CORPUS.md) so the gitignored-content rule is explicit. Today the `.gitignore` does the work but the runbook never says "and we don't commit these".

## Hygiene flags (non-blocking)

- **`VIRTUAL_ENV=/usr` warning from `uv run`** appears on every invocation. Cosmetic — `uv` ignores the host env and uses `.venv/` as it should. Could be silenced with `--active` on every call or by clearing `VIRTUAL_ENV` in the operator's shell profile, but neither is necessary.
- **`HF_TOKEN` not set** — the reranker download path emitted a "you are sending unauthenticated requests to the HF Hub" warning at first use. The model is small and unauthenticated downloads are not rate-limited at this volume; setting a token is nice-to-have, not required.
- **`pgrep` shows residual `vllm-docling` python process at PID 71086** during the run (the container's main process). Stops cleanly on `./scripts/vllm-docling.sh stop`; `docker ps --filter name=vllm-docling` empty after.

---

## Evidence index

Captured under `/tmp/` (ephemeral) and `~/docling/english/actual_texts_md/` (durable):

- [`/tmp/docling-vlm-run.log`](/tmp/docling-vlm-run.log) — full Phase 2 stdout (`Complete: 3 succeeded, 0 failed. Total: 239,409 characters in 392.8s`).
- [`/tmp/ingest-corpus.log`](/tmp/ingest-corpus.log) — full Phase 4 NDJSON + the 581 `citation_anchor.inference_failed` warnings + the final `ingest_summary` line.
- [`~/docling/english/actual_texts_md/processing_manifest.json`](~/docling/english/actual_texts_md/processing_manifest.json) — per-file timings table (data source for the F3 throughput table).
- [`~/docling/english/actual_texts_md/macbeth.md`](~/docling/english/actual_texts_md/macbeth.md), `An_Inspector_Calls_-_JB_Priestley.md`, `All-Power-Conflict-Poems.md` — the VLM markdown outputs (also copied with renames to [`domains/gcse-english/sources/primary_text/`](sources/primary_text/)).
- [`data/chroma/chroma.sqlite3`](../../data/chroma/chroma.sqlite3) — 6.0 MB persistent ChromaDB; collection `gcse-english-v1`; UUID subdir `ad796eac-37cf-4c4d-a7a2-b2e0e3fc2ac5/`.
- [`data/chroma/.primary_text_index`](../../data/chroma/.primary_text_index) — sidecar registry: `an_inspector_calls`, `macbeth`, `power_and_conflict_poems` (52 bytes, one per line).
