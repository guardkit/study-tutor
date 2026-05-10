# Runbook: Ingest Primary Texts via Docling VLM → study-tutor Chroma

**Purpose:** Convert three GCSE English primary-text PDFs to markdown using the
Granite Docling VLM pipeline, then ingest them into the study-tutor's
ChromaDB collection (`gcse-english-v1`) for RAG retrieval.

**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`). Everything runs locally
on this host — the study-tutor service, llama-swap (embeddings), the VLM
container, and ChromaDB persist directory all share `localhost`. Zero
network hops.

**Source PDFs** (already on GB10 at `~/docling/english/actual_texts/`):

| File | Size | Why VLM mode |
|---|---|---|
| `macbeth.pdf` | 820 KB | Multi-column play layout; preserve act/scene structure for citation anchors |
| `An_Inspector_Calls_-_JB_Priestley.pdf` | 225 KB | Scanned paperback — VLM is the documented choice (CONTRIBUTING-CORPUS §3a) |
| `All-Power-Conflict-Poems.pdf` | 1.8 MB | Poetry layout — line breaks and stanza breaks are semantically load-bearing |

**Duration:** ~15-25 minutes total
- VLM container cold start: 1-2 min
- Docling + VLM processing: ~10-15 min (3-4 min/file at ~80-90% GPU)
- Ingestion + Chroma persist: ~1-2 min

**Scripts:** [`~/Projects/appmilla_github/docling-dgx-spark-scripts/`](../../../../docling-dgx-spark-scripts/) — already cloned, includes the working VLM bug-#2868 workaround (strips `<loc_X>` tags post-hoc).

---

## Phase 0: Pre-flight

### 0.1 Verify source PDFs

```bash
ls -la ~/docling/english/actual_texts/
# Expect: 3 PDFs (macbeth, An_Inspector_Calls, All-Power-Conflict-Poems)
```

### 0.2 Verify docling scripts and venv

```bash
ls ~/Projects/appmilla_github/docling-dgx-spark-scripts/scripts/
# Expect: docling-process.sh, vllm-docling.sh

# venv may already exist from prior runs; the script auto-creates it if not
ls ~/.venv/docling/bin/python 2>/dev/null && echo "venv: present" || echo "venv: will be created on first run"
```

### 0.3 Verify Docker + GPU access

```bash
docker info >/dev/null 2>&1 && echo "docker: ok" || echo "docker: FAIL"
nvidia-smi --query-gpu=name,memory.free --format=csv,noheader
# Expect: GB10 GPU listed with several GB free
```

### 0.4 Verify llama-swap (embeddings backend)

The ingestion step calls `nomic-embed-text` via llama-swap on port 9000.

```bash
curl -s http://localhost:9000/v1/models | python3 -c "
import sys, json
ids = [m['id'] for m in json.load(sys.stdin).get('data', [])]
print('nomic-embed-text:', 'present' if any('nomic' in i for i in ids) else 'MISSING')
"
```

If missing, start llama-swap before continuing — see the architect runbook
for the canonical startup procedure.

### 0.5 Confirm study-tutor target dirs

```bash
cd ~/Projects/appmilla_github/study-tutor
ls domains/gcse-english/sources/primary_text/
# Expect: empty (apart from .keep) — the corpus guide says no source files
# are committed, so this directory is gitignored content territory.
```

---

## Phase 1: Start the Granite Docling VLM container

```bash
cd ~/Projects/appmilla_github/docling-dgx-spark-scripts
./scripts/vllm-docling.sh
```

Expected: `Container started: vllm-docling` then guidance to watch logs.

### 1.1 Wait for the model to be ready

```bash
# Watch loading (Ctrl+C once you see "Uvicorn running on http://0.0.0.0:8000")
docker logs -f vllm-docling
```

### 1.2 Health check

```bash
curl -s http://localhost:8002/health && echo " : ok"
curl -s http://localhost:8002/v1/models | python3 -m json.tool
# Expect: granite-docling-258M listed
```

---

## Phase 2: Process PDFs through Docling VLM

Output goes to a staging dir first so we can inspect quality before
dropping files into the study-tutor corpus.

```bash
mkdir -p ~/docling/english/actual_texts_md
cd ~/Projects/appmilla_github/docling-dgx-spark-scripts

./scripts/docling-process.sh \
  --vlm \
  --output ~/docling/english/actual_texts_md/ \
  ~/docling/english/actual_texts/
```

**Run-time expectations:**
- ~3-4 minutes per file at ~80-90% GPU utilisation
- The script prints `[i/3] Processing: <name>` and a per-file char count
- Final summary line: `Complete: 3 succeeded, 0 failed`
- `processing_manifest.json` written into the output dir with timings

**If you want to survive SSH disconnect**, prefix with tmux/nohup:

```bash
tmux new -s docling-vlm
# (then run the docling-process.sh command above)
# Ctrl+B then D to detach; re-attach with: tmux attach -t docling-vlm
```

### 2.1 Verify VLM output

```bash
ls -la ~/docling/english/actual_texts_md/
wc -l ~/docling/english/actual_texts_md/*.md

# Confirm the bug-#2868 workaround actually stripped the <loc_X> tags
grep -c 'loc_[0-9]' ~/docling/english/actual_texts_md/*.md
# Expect: 0 for every file. If any file shows non-zero, see Troubleshooting §A.

# Spot-check structure
head -40 ~/docling/english/actual_texts_md/macbeth.md
head -40 ~/docling/english/actual_texts_md/An_Inspector_Calls_-_JB_Priestley.md
head -40 ~/docling/english/actual_texts_md/All-Power-Conflict-Poems.md
```

For Macbeth, look for act/scene markers — these feed `_infer_play_anchor`
in `study_tutor/knowledge/corpus.py` for citation anchors. If they're
absent or mangled, see Troubleshooting §B.

---

## Phase 3: Move into study-tutor corpus with corpus-friendly names

The file stem becomes the chunk's `text_name`. Per
[CONTRIBUTING-CORPUS.md](sources/CONTRIBUTING-CORPUS.md) §1, prefer
lowercase, simple identifiers. The original PDF filenames are not great
`text_name`s, so rename on copy:

```bash
cd ~/Projects/appmilla_github/study-tutor

cp ~/docling/english/actual_texts_md/macbeth.md \
   domains/gcse-english/sources/primary_text/macbeth.md

cp ~/docling/english/actual_texts_md/An_Inspector_Calls_-_JB_Priestley.md \
   domains/gcse-english/sources/primary_text/an_inspector_calls.md

cp ~/docling/english/actual_texts_md/All-Power-Conflict-Poems.md \
   domains/gcse-english/sources/primary_text/power_and_conflict_poems.md

ls -la domains/gcse-english/sources/primary_text/
# Expect: 3 .md files + the .keep placeholder
```

> **Note on Power & Conflict:** the AQA anthology is 15 separate poems.
> A future task may split this into 15 individual `.md` files (one per
> poem) so each chunk's `text_name` resolves to the actual poem rather
> than the aggregate. For now the single-file form ingests cleanly and
> Chroma's similarity search will still surface the right stanzas.

---

## Phase 4: Run study-tutor corpus ingestion

```bash
cd ~/Projects/appmilla_github/study-tutor

# Make sure the rag extras are installed
uv sync --extra rag

# Ingest — emits NDJSON to stdout, one event per line
python scripts/ingest_corpus.py
```

**Expected stdout** (key lines, per CONTRIBUTING-CORPUS.md):

```json
{"event": "ingest_summary", "chunks_created": <N>, "refusals": 0, "skips": 0}
{"event": "per_text_count", "text_name": "macbeth", "source_type": "PRIMARY_TEXT", "chunk_count": <n1>}
{"event": "per_text_count", "text_name": "an_inspector_calls", "source_type": "PRIMARY_TEXT", "chunk_count": <n2>}
{"event": "per_text_count", "text_name": "power_and_conflict_poems", "source_type": "PRIMARY_TEXT", "chunk_count": <n3>}
```

### 4.1 Confirm Chroma persist + sidecar index

```bash
ls -la data/chroma/
# Expect: chroma.sqlite3 and one or more uuid-named subdirs

cat data/chroma/.primary_text_index 2>/dev/null
# Expect: 3 lines — macbeth, an_inspector_calls, power_and_conflict_poems
```

### 4.2 Smoke-test retrieval

```bash
python -c "
from study_tutor.knowledge.retrieval import build_retriever
r = build_retriever()
hits = r.retrieve('Is this a dagger which I see before me', k=3)
for h in hits:
    print(h.metadata.get('text_name'), '|', h.metadata.get('source_type'), '|', h.page_content[:80])
"
# Expect: top hit is text_name=macbeth, source_type=PRIMARY_TEXT, with the soliloquy text
```

---

## Phase 5: Stop the VLM container

The VLM container holds ~1-2 GB VRAM at idle. Stop it once ingestion is
verified so the GPU memory is free for other workloads:

```bash
cd ~/Projects/appmilla_github/docling-dgx-spark-scripts
./scripts/vllm-docling.sh stop
```

```bash
docker ps --filter "name=vllm-docling"
# Expect: empty
```

---

## Troubleshooting

### A. `<loc_X>` tags appear in the markdown

The script's regex post-processor in `process_with_vlm_pipeline()` should
strip these. If grep finds any, the most likely cause is a script change
that broke the regex. Re-run with the upstream bash script and re-check;
if still present, file an issue against `docling-dgx-spark-scripts` —
this is the Docling bug #2868 workaround scope.

### B. Macbeth has no act/scene markers

The Standard Ebooks `.txt` edition is the canonical source for
Shakespeare (CONTRIBUTING-CORPUS §1) precisely because it preserves
act/scene/line markers cleanly. If the docling output is mangled,
prefer downloading the Standard Ebooks plain-text edition for Macbeth
and skipping VLM for that one file. The other two have no Standard
Ebooks alternative — they remain VLM-route only.

### C. VLM container OOM or crash mid-run

```bash
docker logs vllm-docling --tail 200
nvidia-smi
```

Common causes:
- Another model spinning up via llama-swap consumed the headroom.
  `vllm-docling` runs at `--gpu-memory-utilization 0.05` so it's small
  but can lose its slice. Restart with `./scripts/vllm-docling.sh`.
- ARM64 nvrtc CUDA-JIT issue — the bash script forces
  `CUDA_VISIBLE_DEVICES=""` for PDF rasterisation precisely to avoid
  this. If the error mentions nvrtc, ensure you're running the latest
  `docling-process.sh`.

### D. Ingestion script refusal

```
{"event": "refusal", "reason": "AQA assessment material", ...}
```

None of these three files match the AQA refusal regex
(`past_paper|mark_scheme|examiner_report`), so this should not fire.
If it does, check your filename — Phase 3 renames are deliberately
neutral.

### E. Embeddings unreachable

```
chromadb: ConnectError ... :9000
```

llama-swap isn't running or the embedding model isn't warm. Start
llama-swap, hit the `/v1/models` endpoint to confirm `nomic-embed-text`
is listed, then re-run `python scripts/ingest_corpus.py`. The ingestion
script is idempotent at the `text_name` level — re-running won't double-
insert chunks for an already-registered text.

---

## What this runbook does *not* cover

- **Splitting Power & Conflict into 15 per-poem files** — deferred to a
  separate task (see Phase 3 note).
- **Re-ingestion after corpus edits** — `scripts/ingest_corpus.py`
  semantics for replacing an existing `text_name` are owned by the
  study-tutor repo's RAG documentation, not this runbook.
- **Standard-mode docling** for the Mr Bruff study guides — those are
  already in the dataset-factory's `domains/gcse-english-tutor/sources/`
  and should be processed via the standard (non-VLM) pipeline; that's a
  different runbook.
