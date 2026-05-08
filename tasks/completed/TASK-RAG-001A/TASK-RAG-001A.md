---
id: TASK-RAG-001A
title: "Align ingestion script with DECISION-RAG-001 (llama-swap embeddings, fleet defaults)"
task_type: refactor
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 3
estimated_minutes: 60
status: completed
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
completed: 2026-05-08T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-RAG-001A/
state_transition_reason: "All acceptance criteria met; 9/9 tests pass at 92% coverage"
dependencies:
  - TASK-RAG-001
related:
  - scripts/ingest_corpus.py
  - tests/unit/scripts/test_ingest_corpus.py
  - domains/gcse-english/sources/CONTRIBUTING-CORPUS.md
  - pyproject.toml
external_references:
  - guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md
tags:
  - rag
  - chromadb
  - fleet-alignment
  - llama-swap
  - feat-prv4
  - phase-1
---

# Task: Align ingestion script with DECISION-RAG-001 (llama-swap embeddings, fleet defaults)

## Description

[DECISION-RAG-001 (Unified ChromaDB approach for fleet RAG)](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md)
was accepted on 2026-05-07 — the day before TASK-RAG-001 landed. The
ingestion script delivered by TASK-RAG-001 (commit `79447cd`) is
structurally correct (PersistentClient, idempotent upsert, NDJSON, sidecar,
four-folder layout) but **does not yet conform to the fleet decision** in
three places:

1. It does **not** wire `OpenAIEmbeddingFunction` into the collection.
   Chroma silently falls back to its bundled default (all-MiniLM-L6-v2,
   384 dim) instead of `nomic-embed-text` via llama-swap (768 dim).
   This is load-bearing: if any corpus is ingested before this is fixed,
   the runtime query path (TASK-RAG-002) would either re-embed with the
   default model and miss every ingested vector, or be forced to re-embed
   with `OpenAIEmbeddingFunction` against vectors that live in a different
   embedding space — both produce garbage retrieval.
2. The default persist directory is `./chroma/gcse-english/`; the decision
   mandates `data/chroma/` (per-project root, no domain suffix; aligns
   with `specialist-agent/data/chroma/`).
3. The default collection name is `gcse-english`; the decision mandates
   `gcse-english-v1` (versioned).
4. The script reads only CLI args; the decision §3.1 specifies four env
   vars with sensible defaults that downstream tooling (TASK-RAG-002,
   the docker-compose mounts, the operator runbook) will reference.

This task closes the gap before any real corpus is ingested. No
behavioural changes are needed beyond the embedding wiring + defaults +
env var support.

## Scope

### 1. Wire `OpenAIEmbeddingFunction` in `scripts/ingest_corpus.py`

Add a helper:

```python
def _make_embedding_function() -> Any:
    """Build the OpenAIEmbeddingFunction per DECISION-RAG-001 §2.2."""
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    return OpenAIEmbeddingFunction(
        api_base=os.environ.get("LLM_EMBEDDINGS_BASE_URL", "http://localhost:9000/v1"),
        api_key=os.environ.get("LLM_EMBEDDINGS_API_KEY", "not-needed"),
        model_name=os.environ.get("LLM_EMBEDDINGS_MODEL", "nomic-embed-text"),
    )
```

Pass the result to `get_or_create_collection(name=..., embedding_function=ef)`
in `_open_collection`. Tests inject a stub via a new `embedding_function`
parameter (see §4 below).

### 2. Update defaults to match DECISION-RAG-001 §3.1

```python
DEFAULT_DOMAIN_ROOT: Path = Path("domains/gcse-english/sources")
DEFAULT_COLLECTION_NAME: str = "gcse-english-v1"   # was "gcse-english"
DEFAULT_PERSIST_DIR: Path = Path("data/chroma")    # was "./chroma/gcse-english"
```

The persist dir change is the cosmetic one — `data/chroma/` is the
fleet-aligned per-project root. Multiple collections (e.g. a future
`gcse-maths-v1`) live as separate collections inside the same persist
directory; that's how Chroma is designed to work.

### 3. Read decision-§3.1 env vars as default overrides

For each of the three CLI flags (`--collection-name`, `--persist-dir`,
plus the new embedding-function flags above), read the corresponding env
var as the default *before* falling back to the hard-coded constant. CLI
flags still win over env vars.

| Variable | Default | Effect |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `data/chroma` | overrides `--persist-dir` default |
| `CHROMA_COLLECTION` | `gcse-english-v1` | overrides `--collection-name` default |
| `LLM_EMBEDDINGS_BASE_URL` | `http://localhost:9000/v1` | EF api_base |
| `LLM_EMBEDDINGS_API_KEY` | `not-needed` | EF api_key (llama-swap doesn't auth) |
| `LLM_EMBEDDINGS_MODEL` | `nomic-embed-text` | EF model_name |

### 4. Patch tests (`tests/unit/scripts/test_ingest_corpus.py`)

The existing tests must not start hitting `localhost:9000` during CI. Two
acceptable approaches:

- **Preferred:** add an `embedding_function` parameter to `_open_collection`
  with a default of `None` meaning "build the production
  `OpenAIEmbeddingFunction`". Tests pass
  `chromadb.utils.embedding_functions.DefaultEmbeddingFunction()` (the
  bundled in-process model — slow on first run, cached after) so tests
  run hermetically.
- **Alternative:** monkeypatch `_make_embedding_function` to return the
  default. Same effect; fewer surface changes to the script signature.

Pick whichever the architectural reviewer prefers; both are valid.

Add one new test:

- `test_make_embedding_function_uses_decision_defaults`: monkeypatch the
  three env vars to known values, call `_make_embedding_function`, assert
  the constructed EF carries those values (introspect via attribute
  access — chromadb exposes `_api_base` / `_model_name` on the function
  instance).

### 5. Update `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md`

Add a short section "Embeddings & topology" linking to
[DECISION-RAG-001](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md)
and stating:
- Embeddings flow through llama-swap at `localhost:9000/v1`
  (`nomic-embed-text`, 768 dim)
- Persist dir is `data/chroma/` (override via `CHROMA_PERSIST_DIR`)
- Collection is `gcse-english-v1` (override via `CHROMA_COLLECTION`)
- Ingestion runs on the GB10 (where llama-swap and the persist dir are
  localhost)

### 6. Reference DECISION-RAG-001 in the script's module docstring

One paragraph at the top of `scripts/ingest_corpus.py` pointing at
DECISION-RAG-001 so a future engineer reading the file sees the fleet
context, not just the per-script contract.

### 7. Verify the `openai` transitive dep

DECISION-RAG-001 §7 notes `OpenAIEmbeddingFunction` requires the `openai`
Python package and asserts ChromaDB bundles it. Run `uv tree --extra rag |
grep -i openai` and confirm it's pinned in the lock file. If not, add
`openai` to the `[rag]` extra explicitly.

## Acceptance Criteria

- [ ] `_open_collection` (or its caller) constructs an
      `OpenAIEmbeddingFunction` and passes it to
      `get_or_create_collection(...)` on every ingest.
- [ ] The four DECISION-RAG-001 env vars (`CHROMA_PERSIST_DIR`,
      `CHROMA_COLLECTION`, `LLM_EMBEDDINGS_BASE_URL`,
      `LLM_EMBEDDINGS_MODEL`) are read with the decision's defaults; CLI
      flags still override env vars.
- [ ] `LLM_EMBEDDINGS_API_KEY` defaults to `"not-needed"` and is read
      from env (so a future deployment that does require auth can flip
      one env var).
- [ ] `DEFAULT_COLLECTION_NAME == "gcse-english-v1"` and
      `DEFAULT_PERSIST_DIR == Path("data/chroma")`.
- [ ] All existing tests in `tests/unit/scripts/test_ingest_corpus.py`
      still pass without contacting `localhost:9000` (use the bundled
      default EF or monkeypatch).
- [ ] One new test verifies env-var → EF wiring.
- [ ] `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` references
      DECISION-RAG-001 and documents the embeddings/topology choices.
- [ ] `scripts/ingest_corpus.py` module docstring references
      DECISION-RAG-001.
- [ ] `openai` is confirmed present (transitively or explicitly) in the
      `[rag]` extra; `uv tree --extra rag | grep openai` returns a hit.

## Test Requirements

- Existing 7 tests still pass; coverage stays ≥ 90% on the script.
- New test `test_make_embedding_function_uses_decision_defaults`
  parametrises three env-var settings and asserts the EF instance
  carries each.
- Optional integration smoke (gated `@pytest.mark.requires_llama_swap`)
  that skips on CI but runs on the dev box: ingests a 2-line fixture
  against a real llama-swap, confirms the embedding dimension is 768
  (i.e. proves we hit `nomic-embed-text`, not the 384-dim default).

## Implementation Notes

- DECISION-RAG-001 §7 calls out that `OpenAIEmbeddingFunction` swallows
  embedding failures into ChromaDB-level errors. If llama-swap is down at
  ingest time, the script should surface that with a clear error message
  (current `_open_collection` catches `Exception` only on `--reset`
  delete; the embed-time failure is at `upsert`-call time, propagating
  up). One sentence in the script docstring noting this is sufficient
  — no special handling required.
- Do NOT remove the existing `[rag]` extra wholesale even though
  DECISION-RAG-001 doesn't mandate `sentence-transformers` for ingest.
  The reranker is still wanted at retrieval time (TASK-RAG-002 will load
  it via `set_reranker_factory`), and pinning both deps with one
  `uv sync --extra rag` is the operator ergonomic the original task
  specified.
- The `--reset` semantics are unchanged. The drop-and-recreate sequence
  doesn't touch the embedding function.

## Out of scope

- Runtime CLI wiring (TASK-RAG-002 — being amended separately).
- End-to-end smoke session against a real Macbeth corpus (TASK-RAG-003).
- Migrating any existing ingested data — there is none yet
  (TASK-RAG-001 was structural; no real corpus has been ingested).
- Any change to specialist-agent. That repo's alignment work is
  tracked separately per DECISION-RAG-001 §4.1.

## References

- [DECISION-RAG-001 — Unified ChromaDB approach for fleet RAG](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md) — the parent decision
- [scripts/ingest_corpus.py](../../scripts/ingest_corpus.py) — file under refactor
- [tests/unit/scripts/test_ingest_corpus.py](../../tests/unit/scripts/test_ingest_corpus.py) — test module to patch
- [tasks/completed/TASK-RAG-001 (commit 79447cd)](../../scripts/ingest_corpus.py) — predecessor
- [tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md](TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md) — consumer; spec being amended in parallel
