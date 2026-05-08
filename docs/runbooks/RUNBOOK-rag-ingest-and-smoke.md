# RUNBOOK — RAG ingest + serve-time smoke

**Audience**: operators running the study-tutor MCP server with the
primary-text-RAG pipeline wired (TASK-RAG-002).
**Last verified**: 2026-05-08 (TASK-RAG-002 demo smoke against
`promaxgb10-41b1`).
**Related**: `guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md`,
`tasks/completed/TASK-RAG-002/TASK-RAG-002.md`.

This runbook covers the two operational tasks required to put a study
tutor session on the wired RAG path:

1. Ingesting a source-typed corpus into the persistent ChromaDB store.
2. Verifying at runtime that `serve` opens that store, registers the
   primary texts, and routes per-turn retrieval correctly.

The wiring is graceful-degradation by design: if any prerequisite is
missing, the runtime continues to serve traffic with the verifier
running against an empty corpus. The operator still wants to see the
**wired path** demonstrably firing before a demo or live session — that
is what the smoke is for.

---

## 0. Topology recap

The fleet RAG topology is fixed by DECISION-RAG-001 §3.1:

```
study-tutor (Mac/Linux)            GB10 (promaxgb10-41b1)
  ┌──────────────────────┐           ┌────────────────────┐
  │ chromadb.PersistentClient ◄──────┤  data/chroma/      │
  │  (in-process)        │           │  (sqlite + index)  │
  │                      │           └────────────────────┘
  │ OpenAIEmbeddingFunction          ┌────────────────────┐
  │  HTTP POST  ────────────────────►│ llama-swap :9000   │
  │  /v1/embeddings                  │  nomic-embed alias │
  │                      │           │  (768-dim)         │
  └──────────────────────┘           └────────────────────┘
```

There is **no Chroma server process** and **no cross-host vector
database**. ChromaDB is opened in-process against a local sqlite +
index folder; only the embedding round-trip leaves the host (to
llama-swap on the GB10). DECISION-RAG-001 §2 documents the rationale.

---

## 1. Prerequisites

### 1.1 `[rag]` extra installed

```bash
uv sync --extra rag
```

Pulls in `chromadb>=0.5`, `sentence-transformers>=3.0`, `openai>=1.0`.
Without this extra, both ingest and serve will log
`event=rag_disabled reason=embedding_function_unavailable` (or
`reason=chromadb_missing`) and degrade.

### 1.2 llama-swap reachable

Confirm the GB10 endpoint serves the embedding model:

```bash
curl -sS -m 5 http://promaxgb10-41b1:9000/v1/models | jq -r '.data[].id'
# Expect: nomic-embed (among others — gemma4-tutor, qwen-graphiti, ...)

# Probe a real embed:
curl -sS -m 8 -X POST http://promaxgb10-41b1:9000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed","input":"smoke probe"}' \
  | jq '.data[0].embedding | length'
# Expect: 768
```

If unreachable, check Tailscale (`tailscale status` should show
`promaxgb10-41b1` active) and the llama-swap service on the GB10.

### 1.3 Environment variables

The four DECISION-RAG-001 §3.1 env vars carry shared defaults; override
only what the deployment differs on:

| Variable | Canonical default | When to override |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `data/chroma` | Different on-disk location |
| `CHROMA_COLLECTION` | `gcse-english-v1` | New corpus version |
| `LLM_EMBEDDINGS_BASE_URL` | `http://localhost:9000/v1` | **Always override on Mac dev — point at GB10** |
| `LLM_EMBEDDINGS_API_KEY` | `not-needed` | If a downstream auth proxy is added |
| `LLM_EMBEDDINGS_MODEL` | `nomic-embed` | Different llama-swap alias |

> **Note on the model alias.** DECISION-RAG-001 §3.1 was originally
> drafted with `nomic-embed-text` (the upstream HuggingFace id —
> `nomic-ai/nomic-embed-text-v1.5`). The canonical GB10 deployment
> registers it under the shorter alias `nomic-embed`. Both
> `study_tutor.knowledge.embedding_function.DEFAULT_EMBEDDINGS_MODEL`
> and `scripts.ingest_corpus.DEFAULT_EMBEDDINGS_MODEL` ship the
> alias-matching `nomic-embed` so an unconfigured run against the
> canonical deployment Just Works. If a future deployment standardises
> on `nomic-embed-text` (or any other alias), set
> `LLM_EMBEDDINGS_MODEL` accordingly — both the writer (ingest) and
> the reader (`build_openai_embedding_function`) read the same env
> var, so a single export aligns them.

For Mac dev a `.env`-style export is enough:

```bash
export LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1
# everything else takes the canonical default
```

---

## 2. Ingest

The ingestion script is a one-shot writer. It walks
`domains/<domain>/sources/{primary_text, secondary_study_guide,
secondary_critical, context_historical}/`, chunks every readable file,
embeds via llama-swap, and upserts into the persistent collection.
Re-runs are idempotent (deterministic chunk IDs + `upsert`).

### 2.1 Dry-run / status check

```bash
ls domains/gcse-english/sources/
# primary_text/  secondary_study_guide/  secondary_critical/  context_historical/

ls domains/gcse-english/sources/primary_text/
# .keep  macbeth.txt
```

Empty `.keep` files are skipped with a structured `skip` event. Binary
files (e.g. `.epub`) are skipped as `corrupted_file` because the corpus
loader reads as UTF-8 — convert to plaintext first.

### 2.2 Run the ingest

```bash
LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1 \
uv run python scripts/ingest_corpus.py \
  --domain-root domains/gcse-english/sources
```

Expected NDJSON output (last lines):

```json
{"event": "skip", "path": "...", "reason": "EMPTY_FILE"}
{"event": "per_text_count", "source_type": "PRIMARY_TEXT", "text_name": "macbeth", "chunk_count": 210}
{"event": "ingest_summary", "chunks_created": 210, "refusals": 0, "skips": 5, "primary_text_names": ["macbeth"], "primary_text_index_sidecar": "data/chroma/.primary_text_index"}
```

### 2.3 Verify on-disk state

```bash
ls -la data/chroma/
# .primary_text_index   # sidecar, one text_name per line
# chroma.sqlite3         # ChromaDB metadata + vector store
# <uuid>/                # per-collection vector index folder

cat data/chroma/.primary_text_index
# macbeth
```

### 2.4 Re-ingest after a corpus change

Because chunk IDs are deterministic (`<source_type>:<text_name>:<chunk_index>`),
running ingest again upserts changed chunks in place without
duplicates. Use `--reset` only after a schema-affecting code change
(chunker tuning, citation-anchor format, etc.):

```bash
uv run python scripts/ingest_corpus.py \
  --domain-root domains/gcse-english/sources \
  --reset
```

### 2.5 Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `could not find suitable inference handler for nomic-embed-text` | llama-swap doesn't have a model registered under that exact alias | Set `LLM_EMBEDDINGS_MODEL=nomic-embed` (or whatever the deployment registers) |
| `Connection refused` to localhost:9000 | llama-swap not running locally | Set `LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1` |
| `corrupted_file` on a `.epub` | Binary file in `primary_text/` | Convert to plaintext (Project Gutenberg `.txt` works) |
| `corpus.citation_anchor.inference_failed` warnings | Loader couldn't infer Act/Scene/Line for a chunk | Non-fatal — chunks still ingested with a generic anchor; verifier just won't carry the structured (act, scene, line) tuple for those chunks |

---

## 3. Smoke

Two smokes worth running before a live demo: the **bootstrap smoke**
(no traffic, just startup wiring) and the **per-turn smoke** (drive
the closure end-to-end).

### 3.1 Bootstrap smoke — wired path

```bash
LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1 \
uv run python -c "
import logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
    format='%(levelname)s %(name)s: %(message)s')
for n in ('httpx', 'httpcore', 'sentence_transformers', 'transformers', 'huggingface_hub'):
    logging.getLogger(n).setLevel(logging.WARNING)

from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.roles.loader import load_role
build_rag_providers(load_role('tutor'))
" 2>&1 | grep "event="
```

Expected output:

```
INFO study_tutor.cli.rag_wiring: event=rag_wiring_resolved persist_dir=data/chroma collection=gcse-english-v1
INFO study_tutor.cli.rag_wiring: event=rag_wired collection=gcse-english-v1 persist_dir=data/chroma primary_texts=1
```

The `event=rag_wired` line is the load-bearing demo signal — it
confirms ChromaDB opened, the embedding function constructed, and the
sidecar replay registered the primary text(s).

### 3.2 Bootstrap smoke — degraded path (intentional)

To verify the graceful-degradation envelope (operator should see this
fire if `data/chroma/` is missing or `chromadb` is uninstalled):

```bash
# Temporarily move the corpus aside (don't delete!):
mv data/chroma /tmp/chroma-staged

uv run python -c "
import logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
    format='%(levelname)s %(name)s: %(message)s')
from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.roles.loader import load_role
build_rag_providers(load_role('tutor'))
" 2>&1 | grep "event="

# Expected:
# INFO event=rag_wiring_resolved persist_dir=data/chroma collection=gcse-english-v1
# WARNING event=rag_disabled reason=persist_dir_missing path=data/chroma

# Restore:
mv /tmp/chroma-staged data/chroma
```

The runtime must continue serving `tutor_turn` traffic on this path —
the verifier runs against an empty corpus and produces `NoMatchStrip`
annotations for any quotes. That's the documented degradation envelope
(per AC: "graceful degradation").

### 3.3 Per-turn smoke — closure end-to-end

This drives the production closure against a real Macbeth retrieve and
surfaces the per-turn structured log:

```bash
LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1 \
uv run python -c "
import logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
    format='%(levelname)s %(name)s: %(message)s')
for n in ('httpx', 'httpcore', 'sentence_transformers', 'transformers', 'huggingface_hub'):
    logging.getLogger(n).setLevel(logging.WARNING)

from types import SimpleNamespace
from study_tutor.cli.rag_wiring import build_rag_providers
from study_tutor.cli.main import _build_coach_handover
from study_tutor.roles.loader import load_role

build_rag_providers(load_role('tutor'))

ch = _build_coach_handover()
ss = SimpleNamespace(text_name='macbeth', focus_aos=('AO1','AO2'))
rewritten, metadata = ch(
    'Macbeth says: I have no spur to prick the sides of my intent.',
    'How does Shakespeare present ambition in Act 1?',
    ss,
)
print(f'primary_matches={len(metadata.primary_matches)} '
      f'secondary_rewrites={len(metadata.secondary_rewrites)} '
      f'verifier_exception={metadata.verifier_exception}')
"
```

Expected log + stdout:

```
INFO study_tutor.cli.main: event=orchestrator_turn_completed text_name=macbeth retrieval_mode=rerank chunks=6
primary_matches=N secondary_rewrites=M verifier_exception=False
```

`retrieval_mode=rerank` confirms the BGE-reranker-v2-m3 model loaded
from HuggingFace (or local cache) and reranked the candidate list. If
you see `retrieval_mode=no_rerank`, the `sentence-transformers` import
failed — usually because `[rag]` extra isn't installed or the local
HuggingFace cache lacks the model.

### 3.4 Per-turn smoke — AO3 bypass

```bash
# (with build_rag_providers already wired in the same Python session,
# or repeat the wiring as in 3.3, just change focus_aos:)
ss = SimpleNamespace(text_name='macbeth', focus_aos=('AO3',))
rewritten, metadata = ch('any response text', 'any learner message', ss)
# Expected log line:
# INFO event=orchestrator_turn_completed text_name=macbeth retrieval_mode=skipped reason=ao3_only:training_first
# Expected metadata.retrieval_skipped_reason == "ao3_only:training_first"
```

The AO3-only branch must NOT call `retrieve()` (per the four-branch
decision in `decide_retrieval`). The fake-collection counter test in
`tests/integration/test_cli_rag_wiring.py::test_ao3_bypass` confirms
this in CI.

### 3.5 Test-suite smoke (offline)

The integration tests exercise the same wiring against an in-memory
fake collection — no GB10 needed:

```bash
uv run pytest tests/integration/test_cli_rag_wiring.py \
              tests/integration/test_rag_end_to_end.py -v
# Expected: 8 passed
```

This is the right smoke for CI / dev environments without llama-swap
access.

---

## 4. Live `serve` against the wired path

Once the bootstrap smoke is green, start the MCP server normally:

```bash
LLM_EMBEDDINGS_BASE_URL=http://promaxgb10-41b1:9000/v1 \
AGENT_MODELS__REASONING_MODEL=gemma4-tutor \
uv run study-tutor serve --role tutor
```

The server logs everything to **stderr** (stdout is reserved for MCP
JSON-RPC). Watch for these lines on a successful boot:

```
[study-tutor] Serving role 'tutor' over stdio (provider resolved per-request via AGENT_MODELS__REASONING_MODEL; graphiti=...).
event=rag_wiring_resolved persist_dir=data/chroma collection=gcse-english-v1
event=rag_wired collection=gcse-english-v1 persist_dir=data/chroma primary_texts=1
```

Per `tutor_turn`, you should see one of:

```
event=orchestrator_turn_completed text_name=<n> retrieval_mode=rerank chunks=<count>
event=orchestrator_turn_completed text_name=<n> retrieval_mode=skipped reason=ao3_only:training_first
event=orchestrator_turn_completed text_name=<n> retrieval_mode=skipped reason=analysis_mode:no_primary_text
event=orchestrator_turn_completed text_name= retrieval_mode=skipped reason=no_text_name
```

For DDD Southwest 16 May, the demo log pane is filtered on
`event=orchestrator_turn_completed` — that's the audience signal for
"RAG just fired".

---

## 5. Troubleshooting

| Symptom | Diagnosis | Fix |
|---|---|---|
| `event=rag_disabled reason=chromadb_missing` | `[rag]` extra not installed | `uv sync --extra rag` |
| `event=rag_disabled reason=persist_dir_missing path=data/chroma` | Ingest never run | Run §2 |
| `event=rag_disabled reason=embedding_function_unavailable` | `openai` package missing (rare; usually transitive via `[rag]`) | `uv sync --extra rag` |
| `event=rag_wired primary_texts=0` | Sidecar present but empty / corrupt | Re-run ingest with `--reset` |
| `retrieval_mode=no_rerank` on every turn | `sentence-transformers` failed to load reranker | Confirm `[rag]` extra installed; check HF cache at `~/.cache/huggingface/hub/` |
| `retrieval_mode=skipped reason=analysis_mode:no_primary_text` for a real text | Sidecar replay didn't register that `text_name`. Check session_state | Compare `session_state.text_name` (case-sensitive) against `cat data/chroma/.primary_text_index` |
| Verifier returns `primary_matches=[]` even when the Player response contains a known verbatim quote | Chunk boundary may have split the quote, or text differs in punctuation/whitespace from the corpus | TASK-PRV-005 (verifier) territory — beyond the wiring layer. Check `macbeth.txt` against the response text. |

---

## 6. Reference

- **Code**:
  - `src/study_tutor/cli/rag_wiring.py` — `build_rag_providers()`
  - `src/study_tutor/cli/main.py:_build_coach_handover` — closure factory
  - `src/study_tutor/knowledge/embedding_function.py` — shared EF helper
  - `src/study_tutor/knowledge/retrieval.py` — `decide_retrieval`, `retrieve`, `get_last_retrieval_mode`
  - `scripts/ingest_corpus.py` — one-shot ingest writer
- **Decision**: `guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md`
- **Task**: `tasks/completed/TASK-RAG-002/TASK-RAG-002.md`
- **Plan**: `docs/state/TASK-RAG-002/implementation_plan.md`
- **Tests**:
  - `tests/integration/test_cli_rag_wiring.py` — 5 wiring tests
  - `tests/integration/test_rag_end_to_end.py` — 3 retrieval/verifier tests
- **Related runbooks**:
  - `docs/research/ideas/RUNBOOK-open-webui-tutor-access.md` — llama-swap on GB10
