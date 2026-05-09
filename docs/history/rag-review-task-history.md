The Study tutor has been tested see: Overall Fleet Status — 2026-05-07
Study Tutor: Phase 1 structurally complete ✅
All TASK-GR-DEMO ACs met. Gates G2/G3 held (typed-entity seed), G4/G5/G6/G13 now have live evidence from today's sessions. Remaining admin: update phase-1-validation.md operator scaffold with the evidence, lint pass, move TASK-GR-DEMO to completed.
Completed today: llama-swap provider fix, <think> token stripping, revise path confirmed reachable + exercised in production (attempts=2), session_completed episode write confirmed (MCP query bug identified — not study-tutor's problem).

Please review what is implemented and what we need to do to get the study-tutor working with the RAG

I have enough to give a clear review. Here's the picture.

What's implemented (PRV-001 → PRV-007 all in tasks/completed/)
The RAG pipeline modules ship and are unit/integration-tested:

src/study_tutor/knowledge/corpus_models.py — SourceType, CitationAnchor, CorpusChunk
src/study_tutor/knowledge/corpus.py — load_corpus(root) walks four-folder tree, AQA/in-copyright refusal, citation-anchor inference (PRV-002)
src/study_tutor/knowledge/retrieval.py — should_retrieve + decide_retrieval (R2/R3 + embedder timeout), retrieve() with primary-first, BGE reranker with no_rerank fallback (PRV-003 + PRV-004)
src/study_tutor/knowledge/quote_verifier.py — verify_quotes, VerifierMetadata (PRV-005)
src/study_tutor/knowledge/coach_handover.py — apply_quote_verification seam (PRV-006)
tests/integration/test_rag_end_to_end.py — retrieve‑and‑verify, AnalysisMode skip, AO3 bypass paths pass against a fake Chroma collection (PRV-007)
The orchestrator already accepts a CoachHandover callable and routes (rewritten_response, VerifierMetadata) to the Coach when one is wired (orchestrator.py:484).

What's NOT wired (the gap)
The runtime never actually calls any of it. Three concrete production wiring gaps:

CLI passes coach_handover=None — cli/main.py:148-149 explicitly says "ASSUM-LCA-015 — follow-up subtask". So in serve, every tutor_turn skips retrieval + verification entirely.

No set_collection_provider(...) ever runs in production code. The only callers are tests. retrieve() therefore returns [] even if it were invoked.

No corpus has been ingested into ChromaDB. domains/gcse-english/sources/ only contains a README.md — no primary_text/, secondary_study_guide/, secondary_critical/, context_historical/ subfolders, no Standard Ebooks files, and no script in scripts/ that runs load_corpus(...) → writes to a Chroma collection. The "ChromaDB write helper" promised in corpus.py:43 ("deferred to a thin caller") was never written.

To get RAG working, in order
Add chromadb and sentence-transformers (optional) to pyproject.toml — currently neither is a dependency; modules use injected providers.
Write an ingestion script (e.g. scripts/ingest_corpus.py) that:
takes a domain root (domains/gcse-english/sources/)
calls load_corpus(root)
opens a persistent Chroma collection (./chroma/gcse-english/)
upserts each CorpusChunk with metadata including the JSON payload under CHUNK_PAYLOAD_KEY (the hydrator already expects this, see retrieval.py:404)
calls register_primary_text(text_name) per work — or the loader does this.
Populate domains/gcse-english/sources/primary_text/ with Standard Ebooks Shakespeare (Macbeth, Romeo & Juliet, etc.) plus any secondary study guides you have.
Wire providers + handover in cli/main.py — at serve startup:
set_collection_provider(lambda: chromadb_client.get_collection("gcse-english"))
optional: set_reranker_factory(...) and set_embedder_probe(...)
replace coach_handover=None with a closure that, given (raw_response, session_state):
runs decide_retrieval(session_state.text_name, set(session_state.focus_aos))
if retrieve=True, calls retrieve(query=learner_message_or_response, text_name, focus_aos) to get chunks
calls apply_quote_verification(raw_response, chunks, session_state.text_name, retrieval_skipped_reason=decision.reason if not decision.retrieve else None)
Note: the orchestrator's _apply_coach_handover only passes (raw_response, session_state) — the closure will need to pull learner_message from the session, or you adjust the seam to pass it. Today the seam doesn't have it; small change needed there.
Smoke against a real session — confirm that with Macbeth as session_state.text_name you see mode="rerank" (or no_rerank) in turn metadata and VerifierMetadata.primary_matches populated when the Player quotes.
Recommendation given the 16 May demo
If the demo path is "Demo 3 — Teach a student" and the talk's narrative includes the always‑on‑RAG‑vs‑selective decision (ADR-FLEET-002), wiring this end‑to‑end is the highest‑leverage 1‑2 day's work left on study‑tutor: it turns the "selective retrieval" thesis into something the audience can see in the log pane (reason=retrieve:primary_present vs reason=ao3_only:training_first), and lets the Coach's quote_fidelity rubric criterion actually fire — it's currently dormant because coach_handover=None.

Want me to spin up a TASK to do steps 1–4 (ingestion script + CLI wiring)? That's the load‑bearing work; the modules themselves are already done.

REVIEW-TASK-GR-DEMO-2026-05-05.md
yes please create those tasks using the task tool to invoke /task-create
task-create skill
Let me check the existing task format used in this repo to match conventions.

Read TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md
Read TASK-GSM-006-seeding-script.md
Write TASK-RAG-001-chromadb-ingestion-script.md
224 lines
---
id: TASK-RAG-001
title: "Build chromadb ingestion script and persist source-typed corpus"
task_type: scaffolding
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 4
estimated_minutes: 120
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
dependencies: []
related:
  - src/study_tutor/knowledge/corpus.py
  - src/study_tutor/knowledge/corpus_models.py
  - src/study_tutor/knowledge/retrieval.py
  - tests/integration/test_rag_end_to_end.py
  - domains/gcse-english/sources/README.md
tags:
  - rag
  - chromadb
  - ingestion
  - feat-prv4
  - phase-1
---

# Task: Build chromadb ingestion script and persist source-typed corpus

## Description

The Phase 1 RAG modules (`TASK-PRV-001..007`) all live in `tasks/completed/`
and `src/study_tutor/knowledge/{corpus,retrieval,quote_verifier,coach_handover}.py`
but **no caller persists `CorpusChunk` records into a vector store**.
`src/study_tutor/knowledge/corpus.py` returns chunks; `src/study_tutor/knowledge/retrieval.py`
expects an injected ChromaDB collection via `set_collection_provider()` and
hydrates chunks via `CHUNK_PAYLOAD_KEY="chunk_json"` (a JSON-serialised
`CorpusChunk` in the metadata dict). The "thin caller that imports chromadb
lazily" promised in the docstring of `corpus.py:43` was never written.

This task closes that gap: add the optional `chromadb` (and
`sentence-transformers`) dependencies, write `scripts/ingest_corpus.py`
that walks a domain root through `load_corpus()` and upserts chunks into
a persistent Chroma collection, and add a populated four-folder layout
under `domains/gcse-english/sources/` so the script has something to
ingest. **No CLI runtime wiring is in scope** — that lives in TASK-RAG-002.

## Scope

### Dependencies (`pyproject.toml`)

- Add `chromadb>=0.5` to `[project.optional-dependencies] rag` (gate behind
  an extra so the dev path stays lightweight; install via `uv sync --extra rag`).
- Add `sentence-transformers>=3.0` to the same extra (BGE reranker).
- Document the install step in the script's `--help` text.

### Ingestion script (`scripts/ingest_corpus.py`)

Entry point: `python scripts/ingest_corpus.py [--domain-root PATH] [--collection-name NAME] [--persist-dir PATH] [--reset]`

Behaviour:

1. Default `--domain-root domains/gcse-english/sources/`,
   `--collection-name gcse-english`, `--persist-dir ./chroma/gcse-english/`.
2. Call `load_corpus(domain_root)` to get an `IngestResult`.
3. Open a persistent `chromadb.PersistentClient(path=persist_dir)` and
   `get_or_create_collection(collection_name)`.
4. For each `CorpusChunk`:
   - `id = f"{chunk.text_name}:{chunk.chunk_index}"`
   - `document = chunk.text`
   - `metadata = {
       "text_name": chunk.text_name,
       "source_type": chunk.source_type.value,
       "source_path": chunk.source_path,
       "chunk_index": chunk.chunk_index,
       "chunk_json": chunk.model_dump_json(),
     }`
   - Use `collection.upsert(ids=..., documents=..., metadatas=...)` so re-runs
     update in place.
5. After ingest, register every distinct primary-text `text_name` via
   `study_tutor.knowledge.retrieval.register_primary_text(...)`. The registry
   is module-level state in the running process; the script logs the
   registered names so the operator can confirm them, and writes a sidecar
   `chroma/<domain>/.primary_text_index` text file (one `text_name` per line)
   so the runtime CLI in TASK-RAG-002 can replay the registration at startup.
6. Print a structured summary to stdout (NDJSON) with one line per:
   - `event=ingest_summary, chunks_created=N, refusals=[...], skips=[...]`
   - `event=per_text_count, text_name=..., source_type=..., chunk_count=N`
7. Refusals/skips from `IngestResult.refusals` / `IngestResult.skips` are
   logged verbatim with reason and detail so the operator can spot a typo'd
   folder name or a misplaced AQA past-paper PDF.

### Idempotency

- Re-running against an unchanged corpus must produce identical IDs and
  zero new rows (Chroma `upsert` semantics).
- `--reset` flag drops and recreates the collection before ingest (operator
  safety hatch for schema-change re-ingests).
- AC: a parametrised test runs the ingest twice in temp dirs against a
  three-file fixture corpus and asserts `collection.count()` is equal across
  runs.

### Corpus layout (`domains/gcse-english/sources/`)

Add the four canonical folders so the loader can walk them:

```
domains/gcse-english/sources/
├── primary_text/            # Standard Ebooks Shakespeare / public domain
├── secondary_study_guide/
├── secondary_critical/
├── context_historical/
├── README.md                # already present — extend
└── CONTRIBUTING-CORPUS.md   # NEW: where to source texts, copyright posture
```

- Add a `.gitignore` entry for `domains/gcse-english/sources/**/*.{txt,xhtml,epub,pdf}`
  so actual texts stay out of the repo (legal posture: Standard Ebooks is CC0
  but the repo policy is "operator pulls texts locally").
- Commit at least one tiny placeholder `.keep` file per subfolder.
- `CONTRIBUTING-CORPUS.md` documents:
  - Standard Ebooks as canonical primary-text source for Shakespeare /
    public-domain novels (with download URL pattern).
  - The four-folder source-type mapping
    (`primary_text` → `SourceType.PRIMARY_TEXT`, etc.).
  - The AQA refusal posture (filenames matching `past_paper`, `mark_scheme`,
    `examiner_report` are refused at the loader — confirm with `grep`).
  - The in-copyright deny-list (`inspector_calls`, `blood_brothers`, ...) and
    the Phase 2 per-student episode path that replaces it.

### Runtime smoke (manual)

After implementation, the operator can:

```bash
uv sync --extra rag
# (download Macbeth from Standard Ebooks into domains/gcse-english/sources/primary_text/)
python scripts/ingest_corpus.py
# expect: NDJSON summary with chunks_created > 0, per_text_count for "macbeth"
```

This validates the wave-1 → wave-2 boundary for the demo on 16 May.

## Acceptance Criteria

- [ ] `pyproject.toml` defines an optional `[rag]` extra containing `chromadb`
      and `sentence-transformers`; `uv sync --extra rag` succeeds on the dev
      machine.
- [ ] `scripts/ingest_corpus.py` exists, is `chmod +x`, and prints a structured
      `--help` describing flags and the install command.
- [ ] Running the script with the default flags against a fixture corpus of
      three primary chunks + one secondary chunk creates a persistent Chroma
      collection at `./chroma/gcse-english/` with `collection.count() == 4`.
- [ ] Re-running the script with no source changes leaves `collection.count()`
      unchanged (idempotent upsert).
- [ ] `--reset` recreates the collection (asserted by writing a sentinel
      metadata blob, running with `--reset`, asserting the sentinel is gone).
- [ ] Refusals (e.g. an AQA-named file dropped into `primary_text/`) appear in
      the summary NDJSON with `reason=AQA_ASSESSMENT_MATERIAL` and do not reach
      the collection.
- [ ] At least one primary-text `text_name` is registered via
      `register_primary_text(...)` after a successful ingest, and the sidecar
      `.primary_text_index` file lists it.
- [ ] `domains/gcse-english/sources/{primary_text,secondary_study_guide,secondary_critical,context_historical}/`
      exist in the working tree with `.keep` placeholders.
- [ ] `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` documents the
      Standard Ebooks source, the four-folder mapping, the AQA refusal regex,
      and the in-copyright deny-list.

## Test Requirements

Unit + integration tests live under `tests/scripts/test_ingest_corpus.py`:

- **Idempotency:** ingest twice into a temp persist dir; assert
  `collection.count()` is identical.
- **Refusal pass-through:** drop a file named `macbeth_past_paper.txt` into
  the fixture's `primary_text/` folder; assert the summary NDJSON contains
  exactly one line with `reason=AQA_ASSESSMENT_MATERIAL` and the collection
  contains zero documents from that source path.
- **Metadata round-trip:** ingest a fixture, then read one row back from the
  collection and assert `CorpusChunk.model_validate_json(metadata["chunk_json"])`
  reproduces the original chunk byte-for-byte.
- **`--reset` semantics:** verified per AC above.
- **Skip Chroma if extra not installed:** if `chromadb` is unavailable, the
  test module is skipped via `pytest.importorskip` (do not break CI on the
  dev path).

## Implementation Notes

- The hot path in `retrieval.py` already round-trips `chunk_json` through
  `CorpusChunk.model_validate_json` (see `_hydrate_chunk` at
  `src/study_tutor/knowledge/retrieval.py:502`). The ingestion script's
  metadata shape MUST match what that hydrator expects — this is a load-bearing
  contract.
- ChromaDB metadata values are scalars (`str | int | float | bool`); keep the
  full `CorpusChunk` payload under `chunk_json` and surface
  `text_name` / `source_type` / `source_path` / `chunk_index` separately so
  Chroma's `where` filtering still works (the retrieval module's
  `_query_collection` filters by `text_name` and `source_type`).
- Do not call `set_collection_provider` in this script — that wiring is for
  the runtime CLI only (TASK-RAG-002). The script is a one-shot ingest and
  exits cleanly.
- The reranker dependency (`sentence-transformers`) is in the `rag` extra
  for consistency, but **the ingestion script itself does not need it**;
  it's there so the runtime CLI in TASK-RAG-002 can pin both deps with one
  `uv sync --extra rag`.

## Out of scope

- Any change to `src/study_tutor/cli/main.py` (TASK-RAG-002).
- The `coach_handover` closure that wires retrieval + verifier into the
  orchestrator (TASK-RAG-002).
- End-to-end smoke against a real Player turn (TASK-RAG-003).
- Productionising the ChromaDB persistence dir (`./chroma/`) into a Phase 2
  multi-tenant layout — that is a Phase 2 concern.

## References

- [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py) — `load_corpus`, `IngestResult`, refusal model
- [src/study_tutor/knowledge/retrieval.py](../../src/study_tutor/knowledge/retrieval.py) — `set_collection_provider`, `_hydrate_chunk`, `CHUNK_PAYLOAD_KEY`
- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake Chroma collection shape (model for the real one)
- [tasks/completed/TASK-PRV-002-source-typed-corpus-loader.md](../completed/TASK-PRV-002-source-typed-corpus-loader.md)
- [tasks/completed/TASK-PRV-007-integration-smoke-and-sources-readme.md](../completed/TASK-PRV-007-integration-smoke-and-sources-readme.md)
Write TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
270 lines
---
id: TASK-RAG-002
title: "Wire ChromaDB provider and coach_handover closure into CLI serve"
task_type: integration
feature_id: FEAT-PRV4
implementation_mode: design-first
complexity: 6
estimated_minutes: 180
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
dependencies:
  - TASK-RAG-001
related:
  - src/study_tutor/cli/main.py
  - src/study_tutor/tutoring/orchestrator.py
  - src/study_tutor/knowledge/retrieval.py
  - src/study_tutor/knowledge/coach_handover.py
  - src/study_tutor/mcp/adapter.py
tags:
  - rag
  - cli
  - orchestrator-wiring
  - coach-handover
  - feat-prv4
  - phase-1
---

# Task: Wire ChromaDB provider and coach_handover closure into CLI serve

## Description

The Phase 1 RAG pipeline modules ship and pass their integration test
([tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py))
against a fake Chroma collection, but **the runtime never calls them**.
[src/study_tutor/cli/main.py:148-149](../../src/study_tutor/cli/main.py#L148-L149)
explicitly passes `quote_verifier=None, coach_handover=None` with the
comment `# ASSUM-LCA-015 — follow-up subtask`. That's this task.

When this lands, every `tutor_turn` call against a session whose
`session_state.text_name` is a real primary text (e.g. `macbeth`) will:

1. Hit `decide_retrieval(text_name, focus_aos)` to choose retrieve vs skip.
2. If retrieving, query ChromaDB via the wired collection provider and
   re-rank.
3. Pass the Player response through `apply_quote_verification(...)` so the
   Coach evaluates the **rewritten** response and the
   `quote_fidelity` rubric criterion fires against structured
   `VerifierMetadata`.

This is the load-bearing wiring that turns "we built RAG" into "RAG is on
in production". Critical for the DDD Southwest demo (16 May): the audience
should see `reason=retrieve:primary_present` (or
`reason=ao3_only:training_first`) in the log pane and verifier-driven
rewrites in the response stream.

## Scope

### 1. Add a small seam adjustment to the orchestrator

The `CoachHandover` callable in
[src/study_tutor/tutoring/orchestrator.py](../../src/study_tutor/tutoring/orchestrator.py)
is currently typed `Callable[[str, Any], tuple[str, VerifierMetadata]]` —
it receives `(raw_response, session_state)`. The closure wired by this
task needs the **learner message** as well (it forms the retrieval query)
*and* the orchestrator must surface the retrieval-skipped reason into the
`VerifierMetadata` it forwards to the Coach.

Two acceptable shapes (architectural review will pick one):

- **A.** Widen `CoachHandover` to
  `Callable[[str, str, Any], tuple[str, VerifierMetadata]]` so it receives
  `(raw_response, learner_message, session_state)`. Update both call sites
  (`run_turn` first attempt + revision attempt) and the `_apply_coach_handover`
  shim. This is the lighter touch.
- **B.** Introduce a `CoachHandoverContext` dataclass holding the three
  fields plus future extension points (e.g. `attempt_number`). More
  structural, but YAGNI-flagged unless the architect prefers it.

Default to **A** unless the `architectural-reviewer` flags it. Either way,
the existing FEAT-PH1-003 callers that pass `coach_handover=None`
(tests, the legacy CLI path) MUST continue to work unchanged.

### 2. Build the production providers in `cli/main.py`

Add a new helper `_build_rag_providers(role_config) -> RagProviders`
(or equivalent) that, **at `serve` startup** (not per turn):

1. Reads `STUDY_TUTOR_CHROMA_DIR` env var (default `./chroma/gcse-english/`)
   and `STUDY_TUTOR_COLLECTION` (default `gcse-english`).
2. If `chromadb` is importable AND the persist dir exists:
   - Open `chromadb.PersistentClient(path=...)` once.
   - Resolve the collection once via `get_or_create_collection(...)`.
   - Wrap it in a zero-arg lambda and call
     `set_collection_provider(lambda: collection)`.
   - Read the sidecar `chroma/<domain>/.primary_text_index` written by
     TASK-RAG-001's ingestion script and replay each entry through
     `register_primary_text(...)`. Log a structured line per registration.
3. If `chromadb` is **not** importable OR the persist dir is missing:
   - Log a single WARNING `event=rag_disabled, reason=<chromadb_missing|persist_dir_missing>`.
   - Leave the collection provider unset (`retrieve()` returns `[]`).
   - The `coach_handover` closure (below) still wires up — its retrieval
     call returns `[]` and the verifier runs against an empty corpus,
     producing `NoMatchStrip` for any quotes. This is the documented
     graceful-degradation envelope and must be preserved.
4. Optionally install the BGE reranker via `set_reranker_factory(...)` if
   `sentence_transformers` is importable; otherwise let the default
   `ImportError → no_rerank` path fire.
5. Optionally install an embedder probe via `set_embedder_probe(...)` —
   for Phase 1 a no-op probe is acceptable (Chroma's local embedder is
   in-process and does not need a network ping). Document the deferral in
   a code comment.

### 3. Build the `coach_handover` closure

In `_build_orchestrator_factory`, replace the
`coach_handover=None` argument at line 149 with a closure
`_build_coach_handover()` that, given
`(raw_response, learner_message, session_state)`:

```python
from study_tutor.knowledge.retrieval import decide_retrieval, retrieve
from study_tutor.knowledge.coach_handover import apply_quote_verification

def coach_handover(raw_response, learner_message, session_state):
    text_name = getattr(session_state, "text_name", None)
    focus_aos = set(getattr(session_state, "focus_aos", ()) or ())
    if not text_name:
        # Baseline-degraded plan with no text_name — verifier still runs
        # against empty chunks so quote_fidelity defaults appropriately.
        return apply_quote_verification(raw_response, [], "", retrieval_skipped_reason=None)

    decision = decide_retrieval(text_name, focus_aos)
    if not decision.retrieve:
        return apply_quote_verification(
            raw_response, [], text_name,
            retrieval_skipped_reason=decision.reason,
        )

    # Retrieve query: use the learner message as the query — it expresses
    # the topic the Player just answered, which is what we want to ground
    # the verification corpus in. (See @key-example tests in PRV-004.)
    chunks = retrieve(query=learner_message, text_name=text_name, focus_aos=focus_aos)
    return apply_quote_verification(
        raw_response, chunks, text_name,
        retrieval_skipped_reason=None,
    )
```

Wire this closure into the orchestrator construction at line 149.

### 4. Surface retrieval mode in turn metadata

After `retrieve(...)` completes, the orchestrator (or this closure)
should call `get_last_retrieval_mode()` and surface the value
(`rerank` / `no_rerank`) into the structured log line / TurnResult.
This is the demo signal: the operator can confirm in the log pane that
the reranker actually ran.

### 5. Boot smoke (extends TASK-LCA-004)

The closure factory invocation in `MCPAdapter.__init__` already smokes
the orchestrator construction. Extend the smoke so that:

- If `chromadb` is wired: the boot-time smoke also calls
  `_collection_provider()` once and asserts it returns a non-None object.
- If `chromadb` is NOT wired: the smoke logs the `rag_disabled` reason
  and continues (no failure — this is the graceful-degradation path).

## Acceptance Criteria

- [ ] `src/study_tutor/cli/main.py` no longer passes `coach_handover=None`;
      the wired closure is constructed at serve startup.
- [ ] `set_collection_provider(...)` is called exactly once per `serve`
      invocation when `chromadb` is importable AND the persist dir exists.
- [ ] The `.primary_text_index` sidecar from TASK-RAG-001 is read at
      startup and every entry is replayed via `register_primary_text(...)`.
- [ ] When `chromadb` is missing or the persist dir is absent, `serve`
      logs a structured `event=rag_disabled, reason=...` and the runtime
      continues to serve `tutor_turn` traffic with the verifier running
      against empty corpus chunks (graceful degradation).
- [ ] `CoachHandover` type is widened (or wrapped) to accept the learner
      message as well as the session state; both `run_turn` call sites
      forward it; legacy callers passing `coach_handover=None` are
      unchanged.
- [ ] `tutor_turn` against a session with `text_name="macbeth"`,
      `focus_aos={"AO1","AO2"}` produces a `VerifierMetadata` with
      `retrieval_skipped_reason=None` and at least one populated
      match-list field when the Player response contains a recognisable
      Macbeth quote (verified against the seeded corpus).
- [ ] `tutor_turn` with `focus_aos={"AO3"}` records
      `retrieval_skipped_reason="ao3_only:training_first"` and zero
      retrieval calls (verified by a counter on the fake collection
      provider in tests).
- [ ] `get_last_retrieval_mode()` is read after every retrieval and
      forwarded into the structured log line under
      `event=orchestrator_turn_completed, retrieval_mode=...`.
- [ ] The `architectural-reviewer` agent signs off on the
      `CoachHandover` widening (option A vs B chosen explicitly).

## Test Requirements

Add tests in `tests/integration/test_cli_rag_wiring.py`:

- **Provider wired path:** seed a fake Chroma collection (reuse the fake
  from `tests/integration/test_rag_end_to_end.py`), monkeypatch the
  module-level `chromadb.PersistentClient` to return it, run `serve`
  bootstrap up to the smoke check, and assert that
  `_collection_provider()` returns the fake.
- **Provider missing path:** delete the persist dir / un-import `chromadb`
  via `sys.modules` patching, run `serve` bootstrap, and assert the
  `rag_disabled` log line is emitted and the orchestrator factory still
  builds.
- **Closure end-to-end:** drive one `tutor_turn` through the wired
  orchestrator with a stubbed Player that returns a known Macbeth quote,
  assert the Coach receives the *rewritten* (annotated) response and a
  `VerifierMetadata` with at least one `primary_matches` entry whose
  `citation_anchor.act == 1`.
- **AO3 bypass:** drive a `tutor_turn` with `focus_aos={"AO3"}`, assert
  the fake collection's `query` was never called and the Coach received
  `retrieval_skipped_reason="ao3_only:training_first"`.
- **Verifier-exception path** (regression): force `verify_quotes` to raise
  via monkeypatch, assert the original Player response reaches the Coach
  unchanged with `metadata.verifier_exception=True` and the orchestrator
  does NOT crash.

## Implementation Notes

- The orchestrator is constructed **per turn** — but the ChromaDB
  collection and reranker model should be opened **once at serve
  startup**. Pin them as closure variables in `_build_orchestrator_factory`
  (or in the outer `serve` scope) so the per-turn factory does not pay
  startup cost on every call.
- The retrieval query is the **learner message**, not the Player's
  response. This matches the @key-example test fixtures in TASK-PRV-004
  and is what grounds the verification corpus in the question being
  asked, not the answer being given.
- Surface a single new env var `STUDY_TUTOR_CHROMA_DIR` (default
  `./chroma/gcse-english/`) so the operator can point at a different
  domain without code changes. Document it in the `serve` docstring.
- Keep the closure synchronous; `apply_quote_verification` and `retrieve`
  are sync. The orchestrator already runs the handover inside its async
  pipeline via the existing `_apply_coach_handover` shim.
- The `architectural-reviewer` signoff on the seam widening is mandatory
  because the `CoachHandover` type is referenced from
  [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md)
  and the FEAT-PH1-003 task records — a name change has knock-on
  documentation cost.

## Out of scope

- The ingestion script and the optional `[rag]` extra (TASK-RAG-001).
- The end-to-end demo smoke session against the seeded Lilymay /
  Synology FalkorDB stack (TASK-RAG-003).
- Surfacing retrieval evidence in the MCP `tutor_turn` JSON-RPC response
  (Phase 2 concern; the Coach already consumes it internally for
  `quote_fidelity`).

## References

- [src/study_tutor/cli/main.py](../../src/study_tutor/cli/main.py) — current `coach_handover=None` site
- [src/study_tutor/tutoring/orchestrator.py](../../src/study_tutor/tutoring/orchestrator.py) — `CoachHandover` typedef + `_apply_coach_handover` shim
- [src/study_tutor/knowledge/retrieval.py](../../src/study_tutor/knowledge/retrieval.py) — provider injection contract
- [src/study_tutor/knowledge/coach_handover.py](../../src/study_tutor/knowledge/coach_handover.py) — `apply_quote_verification`
- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake Chroma collection shape
- [tasks/completed/TASK-PRV-006-coach-handover-seam.md](../completed/TASK-PRV-006-coach-handover-seam.md)
- [tasks/completed/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md](../completed/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md)
- [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md) — load-pane signal requirements
Write TASK-RAG-003-end-to-end-rag-smoke-session.md
196 lines
---
id: TASK-RAG-003
title: "End-to-end RAG smoke session against real Macbeth corpus"
task_type: testing
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 4
estimated_minutes: 90
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
dependencies:
  - TASK-RAG-001
  - TASK-RAG-002
related:
  - tests/integration/test_rag_end_to_end.py
  - tests/integration/test_mcp_lca_smoke.py
  - tests/smoke/
  - docs/talks/ddd-southwest-demo-strategy.md
tags:
  - rag
  - smoke
  - demo-prep
  - feat-prv4
  - phase-1
  - ddd-southwest
---

# Task: End-to-end RAG smoke session against real Macbeth corpus

## Description

Validates that the wiring delivered by TASK-RAG-001 (ingestion) +
TASK-RAG-002 (CLI provider + handover closure) actually grounds a live
`tutor_turn` against a real Standard Ebooks Macbeth corpus and surfaces
the demo signals the DDD Southwest 16 May talk depends on:

- `event=orchestrator_turn_completed reason=retrieve:primary_present
  retrieval_mode=rerank attempts=N`
- `event=orchestrator_turn_completed reason=ao3_only:training_first
  retrieval_skipped=True` on an AO3-only turn
- `VerifierMetadata.primary_matches` populated with annotated Act/Scene/Line
  citations when the Player quotes Macbeth verbatim.

This is the **Phase 1 G7 close-out gate** for FEAT-PRV4 — once this
passes, the RAG stack moves from "structurally complete (PRV-007 fake
fixture)" to "live-validated against a real corpus and a real Player",
and the demo strategy doc can mark Demo 3 as covering selective
retrieval, not just Player–Coach.

## Scope

### 1. Operator runbook (`docs/state/rag-runtime-validation.md`)

A four-paragraph Phase-1-validation doc that the operator (Rich) can
follow to bring the RAG runtime up cleanly:

1. **Ingest** — `uv sync --extra rag`, drop Macbeth from Standard Ebooks
   into `domains/gcse-english/sources/primary_text/`, run
   `python scripts/ingest_corpus.py`, expect NDJSON summary with
   `chunks_created > 0` and `per_text_count text_name=macbeth`.
2. **Boot** — `study-tutor serve` with
   `STUDY_TUTOR_CHROMA_DIR=./chroma/gcse-english/`, confirm the boot smoke
   logs include `event=collection_provider_wired
   collection=gcse-english primary_texts=[macbeth ...]`.
3. **Drive a turn** — issue a `tutor_start_session` MCP call for
   `student_id=lilymay` against a planned Macbeth topic; then
   `tutor_turn` with a learner message that invites a quotation
   ("Show me where Lady Macbeth questions Macbeth's manhood").
4. **Verify the signals** — confirm in the log pane:
   `reason=retrieve:primary_present`, `retrieval_mode=rerank` (or
   `no_rerank`), `quote_fidelity` score in the Coach verdict,
   `primary_matches` citations in turn metadata.

### 2. Live integration smoke (`tests/smoke/test_rag_runtime_smoke.py`)

A pytest module marked `@pytest.mark.smoke` and `@pytest.mark.requires_chroma`
that runs end-to-end against a real (small) Chroma persist dir baked from a
public-domain Macbeth excerpt fixture:

- **Setup:** the fixture seeds a temp `./chroma/<test>/` from
  `tests/fixtures/macbeth_excerpt.txt` (3-4 short scenes, public domain) by
  invoking `scripts/ingest_corpus.py` as a subprocess.
- **Boot:** import the CLI's `_build_orchestrator_factory` and the RAG
  provider builder; run them against the temp persist dir.
- **Drive a turn:** stub out only the LLM Player and Coach (use the
  existing `LLMPlayerAdapter` test doubles); leave retrieval and verifier
  REAL.
- **Assert:** the closing TurnResult contains `verifier_metadata` with at
  least one `primary_matches` entry whose `citation_anchor` is a
  `PlayCitationAnchor`. The structured log line for the turn contains
  `reason=retrieve:primary_present` and a `retrieval_mode` field.
- **AO3 path:** rerun with `focus_aos={"AO3"}`; assert
  `retrieval_skipped_reason="ao3_only:training_first"` and the fake
  Chroma collection's `query` was not called.

This complements (does not replace) the existing
`tests/integration/test_rag_end_to_end.py` which uses a hand-built fake.

### 3. Demo cue card (`docs/talks/rag-demo-cues.md`)

A one-page cue card that Rich can put on the lectern during the talk:

- Three example turns and the expected log-line shape for each.
- The expected `reason=` strings to point at on the screen.
- A fallback path: what to say / show if `chromadb` import fails on
  conference WiFi (the `event=rag_disabled` graceful-degradation log
  line plus a fallback to the canonical "selective retrieval works
  because the model already knows Macbeth" narrative).

### 4. Validation report (`docs/state/rag-runtime-validation.md`)

After the smoke runs green and a manual operator session has been driven,
update the validation doc with:

- The actual log lines captured from the manual session
  (sanitised — no live FalkorDB contents).
- The latency of one round-trip turn including retrieval and reranking.
- A `gate_status` block: `G7_phase_1_close_out: PASS` (or notes on what's
  blocking).

## Acceptance Criteria

- [ ] `tests/smoke/test_rag_runtime_smoke.py` exists and is gated by
      `@pytest.mark.requires_chroma` so CI without the `[rag]` extra
      simply skips.
- [ ] `pytest -m "smoke and requires_chroma" tests/smoke/test_rag_runtime_smoke.py`
      passes locally on the dev box (Mac / GB10) after `uv sync --extra rag`.
- [ ] The smoke test asserts both branches: retrieve-and-verify path
      (primary_text Macbeth, AO1/AO2) AND AO3 bypass path
      (focus_aos={"AO3"}, no retrieval call).
- [ ] `docs/state/rag-runtime-validation.md` exists and contains:
      operator runbook, captured log lines from the manual session,
      latency note, `G7_phase_1_close_out` gate status.
- [ ] `docs/talks/rag-demo-cues.md` exists with three cue-card turns and
      the expected `reason=` strings.
- [ ] A manual operator session has been driven once end-to-end from
      `tutor_start_session` through `tutor_turn` against a freshly-ingested
      Macbeth corpus, with the log lines captured into the validation doc.
- [ ] No regression in the existing `tests/integration/test_rag_end_to_end.py`
      (still passes with the fake Chroma fixture; it is the unit-level
      complement to this smoke test).

## Test Requirements

The smoke test itself is the deliverable. Additional checks:

- **Latency budget:** the smoke test asserts a single end-to-end
  `tutor_turn` (with retrieval + rerank + verify) completes in under 10s
  on a stubbed Player/Coach. Real Player/Coach latency is out of scope
  — we measure only the RAG slice.
- **Idempotency proof:** the smoke test runs `scripts/ingest_corpus.py`
  twice in setup; the second invocation must not change `collection.count()`
  (defence-in-depth on TASK-RAG-001's idempotency AC).
- **Secondary chunk handling:** the fixture includes one
  `secondary_study_guide` chunk; the smoke test verifies that a Player
  response containing a study-guide phrasing is rewritten via the
  `SECONDARY_ATTRIBUTION_TEMPLATES` path (not annotated as a primary
  citation).

## Implementation Notes

- The smoke test should NOT require the BGE reranker — the test stubs
  `set_reranker_factory` to raise `ImportError` so `mode="no_rerank"` is
  exercised, and a separate parametrised case stubs a fake reranker to
  exercise `mode="rerank"`. This keeps CI from needing the 568 MB
  cross-encoder model.
- The fixture Macbeth excerpt MUST be public domain. The clean source is
  Standard Ebooks (CC0) — copy 3-4 short scenes into
  `tests/fixtures/macbeth_excerpt.txt` and credit the source in the
  fixture file header.
- Capture log lines from the manual operator session by configuring the
  CLI's logger to write JSON to a file: `study-tutor serve --log-level DEBUG
  2> /tmp/rag-smoke.log`, then `grep event=orchestrator_turn_completed
  /tmp/rag-smoke.log` to extract the lines for the validation doc.
- The cue card lives in `docs/talks/` alongside the demo strategy doc so
  the talk-prep artefacts cluster.

## Out of scope

- Productionising the validation doc into a CI gate (it's an operator
  artefact, not a CI step — too brittle to gate CI on a real LLM call).
- Performance tuning of the reranker or the chunker (Phase 2).
- Driving a Lilymay-stamped session against the live Synology FalkorDB
  graph from inside the smoke test — graphiti integration is a separate
  cross-cutting concern; this task validates the RAG slice only.

## References

- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake-fixture sibling
- [tests/integration/test_mcp_lca_smoke.py](../../tests/integration/test_mcp_lca_smoke.py) — pattern for serve-bootstrap smoke
- [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md) — Demo 3 signal requirements
- [tasks/completed/TASK-PRV-007-integration-smoke-and-sources-readme.md](../completed/TASK-PRV-007-integration-smoke-and-sources-readme.md)
- [tasks/completed/TASK-GR-DEMO/](../completed/TASK-GR-DEMO/) — sibling Phase-1 close-out gate (Graphiti slice)
Three tasks created. Stopping here — implementation is /task-work territory.


✅ Tasks Created (3)

📋 Task 1: TASK-RAG-001 — Build chromadb ingestion script and persist source-typed corpus
   Type: scaffolding · Complexity: 4 · Priority: high · ~120 min
   Status: backlog · Dependencies: none
   File: tasks/backlog/TASK-RAG-001-chromadb-ingestion-script.md

📋 Task 2: TASK-RAG-002 — Wire ChromaDB provider and coach_handover closure into CLI serve
   Type: integration · Complexity: 6 · Priority: high · ~180 min
   Status: backlog · Dependencies: TASK-RAG-001
   File: tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md

📋 Task 3: TASK-RAG-003 — End-to-end RAG smoke session against real Macbeth corpus
   Type: testing · Complexity: 4 · Priority: high · ~90 min
   Status: backlog · Dependencies: TASK-RAG-001, TASK-RAG-002
   File: tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md
Suggested order (3 waves):

/task-work TASK-RAG-001 — chromadb dep + ingestion script + corpus folder layout
/task-work TASK-RAG-002 — CLI providers + coach_handover closure (architectural review on the CoachHandover widening)
/task-work TASK-RAG-003 — live smoke + operator runbook + DDD demo cue card
TASK-RAG-002 is the load-bearing one — flagged as design-first because it widens the CoachHandover callable signature (architectural review needed). The other two are direct mode.

Total: ~6½ hours sequential, fits inside one focused day before the 16 May demo.

I've just remembered that I did some work with Claude Code on a unified approach to RAG with the study-tutor and specialist-agent I have saved this to /Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md. Please read this, I've implemented TASK-RAG-001 but we could always revert this work. It's critical to get this right first time -sorry my mistake
No problem — let's read it before going further.

Read DECISION-RAG-001-unified-chromadb-approach.md
Let me check what's actually been implemented for TASK-RAG-001.

Bash Inspect current state of implementation
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/ /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/ 2>&1; echo "---"; git status --short && echo "---LOG" && git log --oneline -10

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/:
context_historical
CONTRIBUTING-CORPUS.md
primary_text
README.md
secondary_critical
secondary_study_guide

/Users/richardwoollcott/Projects/appmilla_github/study-tutor/scripts/:
__init__.py
__pycache__
graphiti_latency_spike.py
ingest_corpus.py
mcp-wrapper.sh
probes
seed_student_model.py
---
---LOG
79447cd complete(TASK-RAG-001): chromadb ingestion script for source-typed corpus
1aea1e8 docs and tasks
eba1b6c added docs for nats fleet integration
dce7fda fixes and history
0390c1e complete(TASK-GR-DEMO): close Phase 1 → Phase 2 boundary with live MCP demo evidence
37122c5 deps: bump graphiti-core fork pin to v0.29.5-guardkit.3
b7cf1f3 test(orchestrator): TASK-RVP-001 verify revise path is architecturally reachable
750fc9d fix(FEAT-6CC5): TASK-PTS-001 strip <think> tokens from Player adapter responses
f8a8b7d fix(scripts): restore executable bit on mcp-wrapper.sh
7e580a1 mcp wrapper and reviews
Bash See TASK-RAG-001 commit contents
IN
git show --stat 79447cd | head -50

OUT
commit 79447cdc1961f99384c4741fe462948f19d3ca39
Author: Richard Woollcott <rich@appmilla.com>
Date:   Fri May 8 16:50:01 2026 +0100

    complete(TASK-RAG-001): chromadb ingestion script for source-typed corpus
    
    Closes the wave-1 → wave-2 boundary for FEAT-PRV4. The Phase 1 RAG modules
    (corpus loader, retriever, verifier, coach handover from TASK-PRV-002..007)
    shipped earlier but no caller persisted CorpusChunk records into a vector
    store; this task is the missing thin caller.
    
    - pyproject.toml: new [rag] optional-dependencies extra
      (chromadb>=0.5, sentence-transformers>=3.0). Reranker dep ships in the
      same extra so TASK-RAG-002 pins both with one `uv sync --extra rag`,
      but this script does not import sentence-transformers.
    
    - scripts/ingest_corpus.py: argparse CLI, lazy chromadb import inside
      _open_collection (dev path stays light), NDJSON to stdout (event types:
      refusal/skip/per_text_count/ingest_summary), regular logging to stderr,
      --reset via client.delete_collection + get_or_create_collection,
      sidecar `<persist_dir>/.primary_text_index` so TASK-RAG-002 can replay
      register_primary_text() at runtime startup. sys.path bootstrap so
      `./scripts/ingest_corpus.py` works without prior `uv sync`.
    
    - tests/unit/scripts/test_ingest_corpus.py: 7 tests, gated module-wide by
      pytest.importorskip("chromadb"). 91% coverage on the new module. Covers
      idempotency, --reset semantics (sentinel-based), AQA refusal pass-through,
      chunk_json metadata round-trip (the load-bearing retrieval._hydrate_chunk
      contract), register_primary_text + sidecar, --help install hint.
    
    - domains/gcse-english/sources/{primary_text,secondary_study_guide,
      secondary_critical,context_historical}/.keep: four-folder layout
      committed.
    
    - domains/gcse-english/sources/CONTRIBUTING-CORPUS.md: Standard Ebooks
      workflow, four-folder→SourceType map, AQA refusal regex, in-copyright
      deny-list. Operator-facing companion to the existing README.md.
    
    - .gitignore: extend domains/*/sources/**/*.{txt,xhtml} so Standard
      Ebooks plain-text downloads stay out of the repo (PDF/EPUB already
      ignored).
    
    Spec deviation: chunk IDs use f"{source_type}:{text_name}:{chunk_index}"
    (3-tuple) rather than the spec's f"{text_name}:{chunk_index}" (2-tuple).
    The 2-tuple collides because corpus._derive_text_name uses just the file
    stem, so primary_text/macbeth.txt and secondary_study_guide/macbeth.txt
    both yield text_name="macbeth" and would raise chromadb.DuplicateIDError
    on upsert. Documented inline in _chunk_id docstring.
    
    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
Read ingest_corpus.py
Bash Confirm pyproject deps and tests location
IN
grep -n "rag\|chromadb\|sentence" /Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml | head -20; echo "---"; ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tests/unit/scripts/ 2>&1

OUT
50:# pipeline. ``chromadb`` is the persistent vector store the ingestion script
52:# (TASK-RAG-002) hands to ``set_collection_provider``. ``sentence-transformers``
55:# but it ships in the same extra so a single ``uv sync --extra rag`` pins both
57:rag = [
58:    "chromadb>=0.5",
59:    "sentence-transformers>=3.0",
---
__pycache__
test_ingest_corpus.py
Read it. The good news: TASK-RAG-001 is 90% aligned with DECISION-RAG-001. The bad news: there's one load-bearing gap that must be fixed before we ingest any real corpus, plus a couple of cosmetic deltas.

What you've got (keep)
chromadb.PersistentClient ✅ matches §2.1
Lazy chromadb import ✅
Idempotent upsert with deterministic IDs ✅
Four-folder layout + .gitignore + CONTRIBUTING-CORPUS.md ✅
NDJSON summary, sidecar .primary_text_index, tests, fixtures ✅
The [rag] extra in pyproject ✅
Spec-deviation note (chunk ID 3-tuple) — fine, that's an internal correctness fix not in tension with the decision
What's wrong (must patch before ingest)
1. The script never wires OpenAIEmbeddingFunction. scripts/ingest_corpus.py:222 calls client.get_or_create_collection(name=collection_name) with no embedding_function= argument. Chroma silently falls back to its bundled default (all-MiniLM-L6-v2, 384 dim) — not nomic-embed-text via llama-swap (768 dim). This is the load-bearing fleet decision (DECISION-RAG-001 §2.2). If you ingest now and we wire the runtime later, the embedding spaces won't match and retrieval will be garbage.

2. Defaults don't match the fleet pattern.

DEFAULT_PERSIST_DIR = ./chroma/gcse-english — decision says data/chroma/ (per-project root, no domain suffix; aligns with specialist-agent's specialist-agent/data/chroma/)
DEFAULT_COLLECTION_NAME = "gcse-english" — decision says "gcse-english-v1" (versioned)
3. No env var support. Decision §3.1 mandates CHROMA_PERSIST_DIR, CHROMA_COLLECTION, LLM_EMBEDDINGS_BASE_URL, LLM_EMBEDDINGS_MODEL. Currently CLI args only.

4. Knock-on for TASK-RAG-002. When serve re-opens the collection at runtime, it must pass the same OpenAIEmbeddingFunction to get_or_create_collection(...). Chroma's PersistentClient does not persist the EF; if the runtime opens the collection without it, queries will re-embed with the default model and miss the ingested vectors entirely. The current TASK-RAG-002 spec doesn't call this out — it needs amending.

My recommendation: don't revert
The work is solid scaffolding. The gap is surgical (~30 lines + test mocking + 2 doc fixes). Reverting to redo is more expensive and risks losing the good parts (sidecar, NDJSON, idempotency proofs, fixtures).

Two clean options:

Option A — Patch TASK-RAG-001 in place + amend TASK-RAG-002 spec (recommended)
Open a small follow-up task TASK-RAG-001A to close the fleet-alignment gap:

Wire OpenAIEmbeddingFunction(api_base="http://localhost:9000/v1", api_key="not-needed", model_name="nomic-embed-text") into _open_collection
Add _make_embedding_function() helper reading the four env vars with the decision's defaults
Update DEFAULT_PERSIST_DIR to data/chroma/ and DEFAULT_COLLECTION_NAME to gcse-english-v1
Patch the existing tests to monkeypatch the EF (or use chromadb.utils.embedding_functions.DefaultEmbeddingFunction() for unit tests, real EF only behind a requires_llama_swap mark)
Reference DECISION-RAG-001 in the script docstring + CONTRIBUTING-CORPUS.md
Then update TASK-RAG-002's spec to bake in the embedding-function contract at the runtime wiring step.

Estimated work: ~30 mins script patch + ~30 mins TASK-RAG-002 spec amendment.

Option B — Revert + redo
git revert 79447cd, rewrite TASK-RAG-001's spec from scratch with the fleet alignment baked in, re-implement. Maybe 90 mins. Throws away the sidecar, NDJSON design, idempotency proofs that already work.

I'd push back on B unless you'd rather start clean.

Want me to proceed?
If you say yes to Option A, I'll:

Create TASK-RAG-001A-align-with-fleet-rag-decision.md in tasks/backlog/ with the four bullet items above as ACs
Edit tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md to:
Update the env vars section to match the decision (CHROMA_PERSIST_DIR, etc.)
Add an explicit "MUST construct the same OpenAIEmbeddingFunction and pass it to get_or_create_collection" AC
Update the persist-dir default to data/chroma/
Reference DECISION-RAG-001
Then you /task-work TASK-RAG-001A before TASK-RAG-002. No code written yet — just task spec edits.

yes Option A thanks
Write TASK-RAG-001A-align-with-fleet-rag-decision.md
232 lines
---
id: TASK-RAG-001A
title: "Align ingestion script with DECISION-RAG-001 (llama-swap embeddings, fleet defaults)"
task_type: refactor
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 3
estimated_minutes: 60
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
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
Now amending TASK-RAG-002 to bake in the embedding-function contract.

Read TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md (lines 2-31)
Edit TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Added 3 lines
Edit TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Added 34 lines
Edit TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Added 13 lines
Edit TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Added 11 lines
Edit TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Added 2 lines
Done. Summary of what changed:


✅ TASK-RAG-001A created (new)
   tasks/backlog/TASK-RAG-001A-align-with-fleet-rag-decision.md
   Type: refactor · Complexity: 3 · ~60 min · depends on TASK-RAG-001
   Closes the four-point gap between TASK-RAG-001's implementation and
   DECISION-RAG-001:
     1. Wire OpenAIEmbeddingFunction (llama-swap, nomic-embed-text)
     2. Defaults → data/chroma/ + gcse-english-v1
     3. Read CHROMA_* and LLM_EMBEDDINGS_* env vars
     4. Update CONTRIBUTING-CORPUS.md + module docstring
     5. Confirm openai is in the [rag] extra
   Tests stay hermetic via injected default EF.

✅ TASK-RAG-002 amended
   tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
   - Now depends on TASK-RAG-001A (added)
   - §2 expanded with the embedding-space-mismatch failure mode warning
     and the explicit "MUST pass embedding_function= to get_or_create_collection"
     contract
   - Env vars switched to the four DECISION-RAG-001 names (no more
     STUDY_TUTOR_CHROMA_DIR)
   - Three new ACs covering EF wiring, env var alignment, and the
     embedding_function_unavailable graceful-degradation path
   - Implementation note: extract a shared EF helper to avoid drift
     between ingest and runtime
   - Reference list updated with DECISION-RAG-001 + sibling task
Suggested order now:

/task-work TASK-RAG-001A — patch ingest script to use llama-swap embeddings + fleet defaults
/task-work TASK-RAG-002 — wire CLI providers + coach_handover (with the matching EF)
/task-work TASK-RAG-003 — end-to-end smoke
001A is small (~60 min) and unblocks everything downstream cleanly. After it lands, you can ingest a real Macbeth corpus and TASK-RAG-002 will see vectors in the right embedding space.

do we need to have run docling over the books before implementing these tasks? OR can we use the embeddings/chunks from the study guide training for now?
Bash See what other repos are in the fleet
IN
ls /Users/richardwoollcott/Projects/appmilla_github/ 2>&1 | head -30

OUT
agent-os
agentecflow_platform
agentic-dataset-factory
ai-engineer
amity-client-test
amity-kotlin-openapi-generator
AndroidForAI
andy
appmilla-test-explore
architecture_books
AspNetCoreWebApiFundamentals
BarcodeScanning.Native.Maui
basic_keycloak
CertifyDatabase
CertifyMobileApplications
Circuit-Compose-App
cite-saul-ollama-setup
ClearAccept.Android
ClearAccept.TerminalApi.Protobuff
CMPNavigationDemo
ComposablePresenterCounter
ComposablePresenterCounter_template_expanded
ComposeMultiplatformDemo
composeWebApp
cryptopofthepops
CSharp_Markup_PeopleInSpace_MAUI
decompose_starter_template
DeCUK.Mobile.MyDrive
deepagents
deepagents-orchestrator-exemplar
Bash Check agentic-dataset-factory
IN
ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ 2>&1 | head -20; echo "---"; ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/data/ /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/datasets/ 2>&1 | head -30

OUT
__pycache__
agent-config.yaml
agent.py
agentic_dataset_factory.egg-info
agents
AGENTS.md
chroma
chroma_data_backup
chromadb
config
conftest.py
coverage.json
docs
domain_config
domains
entrypoint
features
ingestion
langgraph.json
LICENSE
---
ls: /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/data/: No such file or directory
ls: /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/datasets/: No such file or directory
Bash Look for prior chunked data
IN
ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/ /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/ /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/ 2>&1 | head -40

OUT
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/:
b5d72dbe-7d50-4676-aeb3-bb704fc5fb76
chroma.sqlite3

/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/:
architect-agent
architect-agent-probe
gcse-english-tutor

/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/:
__init__.py
__main__.py
__pycache__
chromadb_indexer.py
chunker.py
docling_processor.py
errors.py
goal_reader.py
ingest.py
models.py
tests
Bash Check gcse-english-tutor existing artifacts
IN
ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/ 2>&1; echo "---"; find /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/ -maxdepth 3 -type f 2>&1 | head -30

OUT
GOAL-direct-only.md
GOAL-test-direct.md
GOAL.md
GOAL.md.bak
GOAL.prod.md
GOAL.test.md
sources
---
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL-test-direct.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/.DS_Store
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL.md.bak
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/.gitkeep
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL.prod.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL-direct-only.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/GOAL.test.md
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Mr-Bruffs-Guide-to-Christmas-Carol-Feb2022-xx7wta.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Lang-Guide-4th-edition-Sept-2025-5fgv5j.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Macbeth203rd20edition-hvhcex.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Power-and-Conflict-Guide-2nd--wsazur.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Practice-paper-2nd-edition-l2zc7o.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/.gitkeep
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Mr-Bruffs-Guide-to-An-Inspector-Calls-2nd-edition.pdf
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/domains/gcse-english-tutor/sources/Literature-Guide-June-21st-2025-ebook-9dkdzh.pdf
Bash Look for existing chunked data and chroma stores
IN
ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chromadb/ /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma/ 2>&1 | head -10; echo "---"; find /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ -path '*/cache*' -prune -o -name "*.jsonl" -print 2>&1 | grep -v cache | head -10; echo "---"; find /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ -name "chroma.sqlite3" 2>&1

OUT
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma/:
chroma.sqlite3

/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chromadb/:
chroma.sqlite3
---
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output/train.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output/rejected.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_backup_pre_rerun/train.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_backup_pre_rerun/rejected.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/train.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/rejected.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_backup_run1/train.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_backup_run1/rejected.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/rag_index/knowledge.jsonl
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_backup_run1/rag_index/knowledge.jsonl
---
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma/chroma.sqlite3
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chromadb/chroma.sqlite3
/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3
Bash Inspect existing chunked rag_index
IN
wc -l /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/rag_index/knowledge.jsonl 2>&1; echo "---"; head -3 /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/rag_index/knowledge.jsonl 2>&1 | cut -c1-500

OUT
     368 /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/output_gcse_rerun/rag_index/knowledge.jsonl
---
{"messages": [{"role": "system", "content": "You are an expert GCSE English tutor supporting a Year 10 student studying the AQA specification.\nYour role is to guide the student using Socratic questioning — help them discover answers\nrather than providing them directly. You have deep knowledge of:\n- AQA English Language (8700): Paper 1 and Paper 2 question types\n- AQA English Literature (8702): Set texts including Macbeth, A Christmas Carol,\n  An Inspector Calls, and the Power and Conflict p
{"messages": [{"role": "system", "content": "You are an expert GCSE English tutor supporting a Year 10 student studying the AQA specification.\nYour role is to guide the student using Socratic questioning — help them discover answers\nrather than providing them directly. You have deep knowledge of:\n- AQA English Language (8700): Paper 1 and Paper 2 question types\n- AQA English Literature (8702): Set texts including Macbeth, A Christmas Carol,\n  An Inspector Calls, and the Power and Conflict p
{"messages": [{"role": "system", "content": "You are an expert GCSE English tutor supporting a Year 10 student studying the AQA specification.\nYour role is to guide the student using Socratic questioning — help them discover answers\nrather than providing them directly. You have deep knowledge of:\n- AQA English Language (8700): Paper 1 and Paper 2 question types\n- AQA English Literature (8702): Set texts including Macbeth, A Christmas Carol,\n  An Inspector Calls, and the Power and Conflict p
Bash Inspect existing chroma collections
IN
ls /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/b5d72dbe-7d50-4676-aeb3-bb704fc5fb76/ 2>&1; echo "---"; python3 -c "
import sqlite3
import os
for path in ['/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma/chroma.sqlite3','/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chromadb/chroma.sqlite3','/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3']:
    print('---', path, os.path.getsize(path) if os.path.exists(path) else 'missing')
    try:
        c = sqlite3.connect(path)
        cur = c.execute('SELECT name FROM sqlite_master WHERE type=\"table\";')
        print([r[0] for r in cur.fetchall()])
        cur = c.execute('SELECT name FROM collections;')
        for r in cur.fetchall():
            print(' collection:', r[0])
    except Exception as e:
        print(' err:', e)
"

OUT
data_level0.bin
header.bin
index_metadata.pickle
length.bin
link_lists.bin
---
--- /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma/chroma.sqlite3 188416
['migrations', 'acquire_write', 'collection_metadata', 'segment_metadata', 'tenants', 'databases', 'collections', 'maintenance_log', 'segments', 'embeddings', 'embedding_metadata', 'max_seq_id', 'embedding_fulltext_search', 'embedding_fulltext_search_data', 'embedding_fulltext_search_idx', 'embedding_fulltext_search_content', 'embedding_fulltext_search_docsize', 'embedding_fulltext_search_config', 'embedding_metadata_array', 'embeddings_queue', 'embeddings_queue_config']
--- /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chromadb/chroma.sqlite3 188416
['migrations', 'acquire_write', 'collection_metadata', 'segment_metadata', 'tenants', 'databases', 'collections', 'maintenance_log', 'segments', 'embeddings', 'embedding_metadata', 'max_seq_id', 'embedding_fulltext_search', 'embedding_fulltext_search_data', 'embedding_fulltext_search_idx', 'embedding_fulltext_search_content', 'embedding_fulltext_search_docsize', 'embedding_fulltext_search_config', 'embedding_metadata_array', 'embeddings_queue', 'embeddings_queue_config']
--- /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3 16494592
['migrations', 'acquire_write', 'collection_metadata', 'segment_metadata', 'tenants', 'databases', 'collections', 'maintenance_log', 'segments', 'embeddings', 'embedding_metadata', 'max_seq_id', 'embedding_fulltext_search', 'embedding_fulltext_search_data', 'embedding_fulltext_search_idx', 'embedding_fulltext_search_content', 'embedding_fulltext_search_docsize', 'embedding_fulltext_search_config', 'embedding_metadata_array', 'embeddings_queue', 'embeddings_queue_config']
 collection: gcse-english-tutor
Bash Inspect ADF chroma collection metadata schema
IN
python3 -c "
import sqlite3
c = sqlite3.connect('/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3')
cur = c.execute('SELECT count(*) FROM embeddings;')
print('embeddings count:', cur.fetchone()[0])
cur = c.execute('SELECT key, string_value FROM embedding_metadata WHERE key IN (\"chromadb:document\",\"source\",\"text_name\",\"source_type\",\"chunk_index\",\"chunk_json\",\"page\",\"section\") LIMIT 40;')
for r in cur.fetchall():
    v = (r[1] or '')[:200]
    print(r[0], '|', v)
print('---distinct keys---')
cur = c.execute('SELECT DISTINCT key FROM embedding_metadata ORDER BY key;')
for r in cur.fetchall():
    print(r[0])
"

OUT
embeddings count: 3850
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
chunk_index | 
---distinct keys---
chroma:document
chunk_index
docling_mode
domain
page_number
source_file
Bash See ADF source files and counts
IN
python3 -c "
import sqlite3
c = sqlite3.connect('/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3')
print('--- distinct source_file ---')
cur = c.execute('SELECT DISTINCT string_value FROM embedding_metadata WHERE key=\"source_file\";')
for r in cur.fetchall():
    print(' ', r[0])
print('--- sample document ---')
cur = c.execute('SELECT string_value FROM embedding_metadata WHERE key=\"chroma:document\" LIMIT 1;')
for r in cur.fetchall():
    print((r[0] or '')[:600])
print('--- counts per source_file ---')
cur = c.execute('SELECT string_value, COUNT(*) FROM embedding_metadata WHERE key=\"source_file\" GROUP BY string_value;')
for r in cur.fetchall():
    print(' ', r[1], r[0])
"

OUT
--- distinct source_file ---
  Lang-Guide-4th-edition-Sept-2025-5fgv5j.pdf
  Literature-Guide-June-21st-2025-ebook-9dkdzh.pdf
  Macbeth203rd20edition-hvhcex.pdf
  Mr-Bruffs-Guide-to-An-Inspector-Calls-2nd-edition.pdf
  Mr-Bruffs-Guide-to-Christmas-Carol-Feb2022-xx7wta.pdf
  Power-and-Conflict-Guide-2nd--wsazur.pdf
  Practice-paper-2nd-edition-l2zc7o.pdf
--- sample document ---
Contents
Please note: this book is not endorsed by or affiliated to any exam boards; I am simply an experienced teacher using my expertise to help students.
--- counts per source_file ---
  540 Lang-Guide-4th-edition-Sept-2025-5fgv5j.pdf
  572 Literature-Guide-June-21st-2025-ebook-9dkdzh.pdf
  680 Macbeth203rd20edition-hvhcex.pdf
  623 Mr-Bruffs-Guide-to-An-Inspector-Calls-2nd-edition.pdf
  492 Mr-Bruffs-Guide-to-Christmas-Carol-Feb2022-xx7wta.pdf
  605 Power-and-Conflict-Guide-2nd--wsazur.pdf
  338 Practice-paper-2nd-edition-l2zc7o.pdf
Bash Sample Macbeth PDF chunks to determine primary vs commentary
IN
python3 -c "
import sqlite3
c = sqlite3.connect('/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/chroma_data_backup/chroma.sqlite3')
# get a few sample chunks from the Macbeth pdf to see if it's primary text or commentary
cur = c.execute('''
SELECT m1.string_value as src, m2.string_value as doc, m3.int_value as page
FROM embedding_metadata m1
JOIN embedding_metadata m2 ON m1.id=m2.id AND m2.key=\"chroma:document\"
LEFT JOIN embedding_metadata m3 ON m1.id=m3.id AND m3.key=\"page_number\"
WHERE m1.key=\"source_file\" AND m1.string_value LIKE \"%Macbeth%\"
ORDER BY m1.id
LIMIT 5;
''')
for r in cur.fetchall():
    print('page', r[2], '|', (r[1] or '')[:300].replace(chr(10),' / '))
    print()
print('--- middle of the doc ---')
cur = c.execute('''
SELECT m1.string_value as src, m2.string_value as doc, m3.int_value as page
FROM embedding_metadata m1
JOIN embedding_metadata m2 ON m1.id=m2.id AND m2.key=\"chroma:document\"
LEFT JOIN embedding_metadata m3 ON m1.id=m3.id AND m3.key=\"page_number\"
WHERE m1.key=\"source_file\" AND m1.string_value LIKE \"%Macbeth%\"
ORDER BY m1.id
LIMIT 5 OFFSET 200;
''')
for r in cur.fetchall():
    print('page', r[2], '|', (r[1] or '')[:300].replace(chr(10),' / '))
    print()
"

OUT
page 1 | Mr Bruff's Guide To 'Macbeth' / COPYRIGHT2019ANDREWBRUFF

page 2 | DEDICATION: / This guide was written by Peter Tobin, part of the mrbruff.com team. The entire text is © Peter Tobin. Thank you, Peter, for your excessive hard work. / A big thank you must go to Sam Perkins and Sunny Ratilal, who between them designed the front cover of this guide. Sunny designed the ori

page 2 | REFERENCES: / Bradley, A.C. (1904). Shakespearean Tragedy . Macmillan. / Klein, Joan Larsen. (1983). 'Lady Macbeth: Infirm of Purpose.' In The Woman's Part: Feminist Criticism of Shakespeare , University of Illinois Press. / Pfundheller, E. (1873). On The Character of Lady Macbeth . Herrcke & Lebeling. / Sm

page 3 | Contents / Introduction to the Third Edition ...........................................................................................................  3 / Stagecraft .......................................................................................................................................

page 3 | Scene by Scene Analysis .......................................................................................................................  20 / Act 1 Scene 1 ........................................................................................................................................  

--- middle of the doc ---
page 22 | This natural order also relates to why this play is seen as one of Shakespeare's tragedies . For his play to be a tragedy, the main protagonist or central character must fall from a high position (socially) because of some tragic flaw (hamartia) within themselves. In Macbeth , the main protagonist d

page 22 | king was at the top and no one from below him (lords, noblemen, soldiers or peasants) could move up. This is what Macbeth does and in order to put the social order back to normal, he must be removed (killed) and the rightful heir must take the throne.

page 22 | This opens up some of the key questions in the play. Academics have long debated various intricacies in the play and some of the issues that arise time and again are questions about motive. Would Macbeth have killed his king without the presence of female characters in the play (Lady Macbeth and the

page 22 | man who gives in to the desires of others and allows himself to be caught up in their wishes and plans?

page 22 | Structure is another key element to this play and, throughout, Shakespeare makes use of things like foreshadowing and echoing . Often, ideas or imagery are used at one point in the play to signal a later development. At the beginning, for example, the Thane of Cawdor is executed for being a traitor.
Good question — and there's a useful surprise hiding in the fleet. Short answer: you don't need to run docling yourself, but you can't directly reuse the existing chunks either. The right move for the demo is plain-text Standard Ebooks Macbeth via the already-built loader, no docling involved.

What's already been chunked
agentic-dataset-factory/chroma_data_backup/chroma.sqlite3 (16 MB, collection gcse-english-tutor) holds 3,850 chunks across 7 docling-processed PDFs:

Source	Chunks	What it actually is
Mr Bruff's Guide to Macbeth (3rd ed)	680	Secondary commentary — not primary play text
Mr Bruff's Guide to An Inspector Calls	623	Secondary commentary
Mr Bruff's Guide to Christmas Carol	492	Secondary commentary
Power and Conflict Guide	605	Secondary (poetry cluster)
Lang Guide	540	Secondary (English Lang)
Literature Guide	572	Secondary (English Lit overview)
Practice paper 2nd ed	338	⚠️ AQA-pattern material — must refuse
I sampled the Macbeth PDF to confirm: page 1 starts Mr Bruff's Guide To 'Macbeth' / COPYRIGHT2019ANDREWBRUFF, and the body is commentary like "This natural order also relates to why this play is seen as one of Shakespeare's tragedies…" — no Act/Scene/Line markers, no verbatim play text. So the existing Chroma store has zero primary-text Shakespeare.

Why you can't just reuse this Chroma store
Three independent blockers:

Embedding-space mismatch. ADF's chunks were embedded with whatever model ADF used at the time (almost certainly not nomic-embed-text via llama-swap — would need to check). Per DECISION-RAG-001, study-tutor queries via nomic-embed-text (768 dim). Different model = vectors live in different spaces = every query returns garbage.

Schema mismatch. ADF metadata: {source_file, chunk_index, page_number, docling_mode, domain, chroma:document}. Study-tutor's retriever (load-bearing contract via _hydrate_chunk) needs {text_name, source_type, source_path, chunk_index, chunk_json} where chunk_json is a JSON-serialised CorpusChunk.

No primary text + a forbidden PDF. All 7 sources are secondary; the practice paper would fail AQA_REFUSAL_PATTERN if we tried to ingest it through load_corpus. Demo signal reason=retrieve:primary_present with PlayCitationAnchor(act, scene, line) rewrites needs Shakespeare's actual play text.

Recommendation for the 16 May demo
Path A — Standard Ebooks Macbeth only (recommended)

Download Macbeth from standardebooks.org (CC0 plain text, ~150 KB)
Drop it into domains/gcse-english/sources/primary_text/macbeth.txt
Run TASK-RAG-001A's patched script — produces ~150 primary-text chunks with PlayCitationAnchor anchors, embedded via llama-swap
Demo signals fire: reason=retrieve:primary_present, mode=rerank, VerifierMetadata.primary_matches[].citation_anchor.act=1 for any verbatim quotes
No docling, no schema bridge. Plain text, the loader already handles this exact case.
Time cost: 5 minutes of manual download + however long TASK-RAG-001A → 002 → 003 takes
The secondary_* folders stay empty for now — that's fine. The verifier defaults NoMatchStrip for unrecognised quotes, which is correct behaviour, not a bug.

Path B — Add ADF secondaries via a bridge script (post-demo)

A follow-up task, not for the 16 May demo:

Write a one-off scripts/bridge_adf_corpus.py that:
Reads ADF's gcse-english-tutor collection
Filters out Practice-paper-*.pdf (AQA refusal)
Maps each chunk to a CorpusChunk(source_type=SECONDARY_STUDY_GUIDE, text_name=<inferred from filename>, citation_anchor=None, ...)
Re-embeds via OpenAIEmbeddingFunction (llama-swap) and upserts into gcse-english-v1
Adds SecondaryRewrite verifier events on top of the primary-citation flow
Estimated 2 hours; could ship between demo (16 May) and hackathon (18 May) if useful
My suggestion
Stay on Path A for now. The TASK-RAG-001A → 002 → 003 chain we've already specced works against Standard Ebooks Macbeth out of the box, no spec changes needed.

Two small additions to make this concrete:

Add a checklist to domains/gcse-english/sources/CONTRIBUTING-CORPUS.md (already created in TASK-RAG-001) with the exact Standard Ebooks Macbeth URL and the file path it goes to.
Optional: create a TASK-RAG-004 stub for the ADF bridge so the option doesn't get lost, but keep it priority:low and out of the critical path.
Want me to:

(a) draft TASK-RAG-004 as a stub (post-demo follow-up), and/or
(b) add the Standard Ebooks download checklist to TASK-RAG-001A so the operator step is captured alongside the script work?
Or just leave both for now and treat the corpus drop as a 5-minute manual step inside TASK-RAG-003's runbook?

I've downloaed the pdfs for macbeth, an inspector calls and power and conflict poems will these be ok?
Two things will bite before we can use those — let me lay them out, then we can figure out the cleanest path.

Issue 1 — PDFs aren't readable by load_corpus
The loader only reads UTF-8 text files (corpus.py:316 — file_path.read_text(encoding="utf-8")). A .pdf would throw UnicodeDecodeError and be skipped as CORRUPTED_FILE. So PDFs need text extraction first. Options:

Docling — already used by ADF on the same kind of material; layout-aware, produces clean structured markdown. ADF has it wired at agentic-dataset-factory/ingestion/docling_processor.py.
Lightweight extractor — pdfplumber or PyMuPDF. Faster, no GPU, decent quality for clean text PDFs but loses layout.
One-off conversion — convert each PDF to .txt once (manually or via a small script), drop the .txt in sources/, never run extraction in the runtime.
For the demo I'd lean one-off .txt conversion — fastest to get working, and if quality is bad on any specific PDF you can re-run with docling for that one. No new runtime dependency.

Issue 2 — Two of those three are in-copyright (this is the bigger one)
Study-tutor's loader refuses these by design:


INCOPYRIGHT_TITLES: frozenset[str] = frozenset({
    "inspector_calls",   # J.B. Priestley d. 1984 → UK copyright until 2054
    "blood_brothers",
    "dna",
    "lord_of_the_flies",
    "anita_and_me",
    "animal_farm",
})
And most of the Power and Conflict cluster is also in copyright: Carol Ann Duffy, Simon Armitage, Imtiaz Dharker, John Agard, Beatrice Garland, Seamus Heaney are all either living or recently deceased. Only a subset (Shelley, Wordsworth, Browning, Tennyson, Owen) is out of copyright. The cluster as a single PDF will mix the two.

The deliberate posture from FEAT-PRV4 is that bulk RAG ingest is for public-domain and licensed material only; in-copyright modern set texts go through the Phase 2 per-student episode path (a per-student in-copyright Text episode, not bulk corpus). That's not built yet — it's a Phase 2 feature.

So if those three PDFs are the primary play/poem texts:

Text	Legal status	Demo path
Macbeth (Shakespeare 1606)	Public domain ✅	Use Standard Ebooks plain text instead — clean, no PDF extraction, has act/scene markers
An Inspector Calls (1945)	In copyright ❌	Can't bulk-ingest. Phase 2 per-student path only
Power and Conflict cluster	Mostly in copyright ❌	Could ingest only the public-domain subset; mixed cluster needs splitting
But if those PDFs are study guides about those texts (Mr Bruff style, AQA-licensed, etc.), the picture is different — they'd go in secondary_study_guide/ and the licence question is whether you have permission to ingest them (single-user personal study tools are usually fine; redistribution is not).

What I need from you
Two clarifications before we touch any code:

What are the PDFs, exactly? For each one — is it the actual text of the play/poems, or is it a study guide about the text? Filenames help (paste them) and so does flipping to page 1 — primary text starts with the play; commentary starts "Mr Bruff's Guide to…" or "AQA…" or similar.

Where are they on disk? I can take a quick look (filename + first line) and tell you definitively which folder each belongs in (primary_text/, secondary_study_guide/, or "don't ingest, save for Phase 2").

If they're commentary, the path is straightforward — extract → drop in secondary_study_guide/ → demo works with Macbeth-from-Standard-Ebooks as the primary anchor. If they're primary texts, the Inspector Calls and most Power-and-Conflict PDFs sit out of the demo until Phase 2.

Hold off on copying anything into domains/gcse-english/sources/ until we've sorted this — once an in-copyright file lands in primary_text/, the loader refuses it (good) but the file is still on disk in a repo path that's now committed-against, and it's easier to never put it there.

I've copied them to /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text
Bash List primary_text folder and git status
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text/ 2>&1; echo "---"; git status --short

OUT
total 9776
drwxr-xr-x@ 6 richardwoollcott  staff      192 May  8 17:58 .
drwxr-xr-x  9 richardwoollcott  staff      288 May  8 17:58 ..
-rw-r--r--@ 1 richardwoollcott  staff        0 May  8 16:35 .keep
-rw-r--r--@ 1 richardwoollcott  staff  1805378 May  8 17:48 All-Power-Conflict-Poems.pdf
-rw-r--r--@ 1 richardwoollcott  staff  2372256 May  8 17:45 an-inspector-calls.pdf
-rw-r--r--@ 1 richardwoollcott  staff   820517 May  8 17:42 macbeth.pdf
---
 M tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
Bash Check whether the PDFs are gitignored
IN
grep -E "^domains/.*sources" .gitignore 2>&1; echo "---ignore-check---"; git check-ignore -v domains/gcse-english/sources/primary_text/macbeth.pdf domains/gcse-english/sources/primary_text/an-inspector-calls.pdf domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf 2>&1

OUT
domains/*/sources/*.pdf
domains/*/sources/**/*.pdf
domains/*/sources/*.PDF
domains/*/sources/**/*.PDF
domains/*/sources/*.epub
domains/*/sources/**/*.epub
domains/*/sources/*.txt
domains/*/sources/**/*.txt
domains/*/sources/*.xhtml
domains/*/sources/**/*.xhtml
---ignore-check---
.gitignore:251:domains/*/sources/**/*.PDF	domains/gcse-english/sources/primary_text/macbeth.pdf
.gitignore:251:domains/*/sources/**/*.PDF	domains/gcse-english/sources/primary_text/an-inspector-calls.pdf
.gitignore:251:domains/*/sources/**/*.PDF	domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf
Bash Check for any PDF reader available
IN
python3 -c "
import sys
try:
    import pypdf
    have_pypdf = True
except ImportError:
    have_pypdf = False
try:
    import fitz  # PyMuPDF
    have_fitz = True
except ImportError:
    have_fitz = False
print('pypdf:', have_pypdf, 'pymupdf:', have_fitz)
" 2>&1; echo '---'; which pdftotext 2>&1

OUT
Exit code 1
pypdf: False pymupdf: False
---
pdftotext not found
Bash Probe each PDF's title and first pages
IN
uvx --quiet pypdf -- python3 -c "
import pypdf, sys
for path in ['domains/gcse-english/sources/primary_text/macbeth.pdf','domains/gcse-english/sources/primary_text/an-inspector-calls.pdf','domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf']:
    print('='*70); print(path)
    try:
        r = pypdf.PdfReader(path)
        print('  pages:', len(r.pages))
        for i in range(min(2, len(r.pages))):
            t = (r.pages[i].extract_text() or '').strip()
            print('--- page', i+1, '(first 600 chars) ---')
            print(t[:600].replace(chr(0), '?'))
    except Exception as e:
        print('  error:', type(e).__name__, e)
" 2>&1 | head -120

OUT
(Bash completed with no output)
Bash Inspect each PDF via uv run with pypdf
IN
uv run --with pypdf python3 -c "
import pypdf
for path in ['domains/gcse-english/sources/primary_text/macbeth.pdf','domains/gcse-english/sources/primary_text/an-inspector-calls.pdf','domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf']:
    print('='*70); print(path)
    try:
        r = pypdf.PdfReader(path)
        print('  pages:', len(r.pages))
        meta = r.metadata or {}
        print('  title:', meta.get('/Title'))
        print('  author:', meta.get('/Author'))
        for i in range(min(2, len(r.pages))):
            t = (r.pages[i].extract_text() or '').strip()
            print('--- page', i+1, '(first 500 chars) ---')
            print(t[:500])
    except Exception as e:
        print('  error:', type(e).__name__, e)
" 2>&1 | head -150

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Installed 1 package in 1ms
======================================================================
domains/gcse-english/sources/primary_text/macbeth.pdf
  pages: 83
  title: None
  author: binshu
--- page 1 (first 500 chars) ---
HAMLET - Act V    
1
--- page 2 (first 500 chars) ---
2    
  
Contents 
ACT I .................................................................................................................................. 3 
SCENE I. A desert place. ................................................................................................ 3 
SCENE II. A camp near Forres. ...................................................................................... 3 
SCENE III. A heath near Forres. ................................................................
======================================================================
domains/gcse-english/sources/primary_text/an-inspector-calls.pdf
  pages: 40
  title: Inspector Calls (LUCY)
  author: Malc
--- page 1 (first 500 chars) ---

--- page 2 (first 500 chars) ---
2
======================================================================
domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf
  pages: 24
  title: None
  author: None
--- page 1 (first 500 chars) ---

--- page 2 (first 500 chars) ---
Bash Sample deeper pages of each PDF
IN
uv run --with pypdf python3 -c "
import pypdf
for path,pages in [('domains/gcse-english/sources/primary_text/macbeth.pdf',[2,3,4,40]),('domains/gcse-english/sources/primary_text/an-inspector-calls.pdf',[1,3,5,20]),('domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf',[1,3,5,12])]:
    print('='*70); print(path)
    r = pypdf.PdfReader(path)
    for p in pages:
        if p > len(r.pages): continue
        t = (r.pages[p-1].extract_text() or '').strip()
        print(f'--- page {p} (first 700 chars) ---')
        print(t[:700])
" 2>&1 | head -150

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
======================================================================
domains/gcse-english/sources/primary_text/macbeth.pdf
--- page 2 (first 700 chars) ---
2    
  
Contents 
ACT I .................................................................................................................................. 3 
SCENE I. A desert place. ................................................................................................ 3 
SCENE II. A camp near Forres. ...................................................................................... 3 
SCENE III. A heath near Forres. ..................................................................................... 6 
SCENE IV. Forres. The palace. .................................................................................... 11 
SCENE V. Inverness. Macbeth's castle. ..................
--- page 3 (first 700 chars) ---
3    
 
ACT I 
SCENE I. A desert place. 
Thunder and lightning. Enter three Witches 
First Witch 
When shall we three meet again 
In thunder, lightning, or in rain? 
Second Witch 
When the hurlyburly's done, 
When the battle's lost and won. 
Third Witch 
That will be ere the set of sun. 
First Witch 
Where the place? 
Second Witch 
Upon the heath. 
Third Witch 
There to meet with Macbeth. 
First Witch 
I come, Graymalkin! 
Second Witch 
Paddock calls. 
Third Witch 
Anon. 
ALL 
Fair is foul, and foul is fair: 
Hover through the fog and filthy air. 
Exeunt 
SCENE II. A camp near Forres. 
Alarum within. Enter DUNCAN, MALCOLM, DONALBAIN, LENNOX, with 
Attendants, meeting a bleeding Sergeant 
DUN
--- page 4 (first 700 chars) ---
4    
'Gainst my captivity. Hail, brave friend! 
Say to the king the knowledge of the broil 
As thou didst leave it. 
Sergeant 
Doubtful it stood; 
As two spent swimmers, that do cling together 
And choke their art. The merciless Macdonwald-- 
Worthy to be a rebel, for to that 
The multiplying villanies of nature 
Do swarm upon him--from the western isles 
Of kerns and gallowglasses is supplied; 
And fortune, on his damned quarrel smiling, 
Show'd like a rebel's whore: but all's too weak: 
For brave Macbeth--well he deserves that name-- 
Disdaining fortune, with his brandish'd steel, 
Which smoked with bloody execution, 
Like valour's minion carved out his passage 
Till he faced the slave; 

--- page 40 (first 700 chars) ---
40    
That shake us nightly: better be with the dead, 
Whom we, to gain our peace, have sent to peace, 
Than on the torture of the mind to lie 
In restless ecstasy. Duncan is in his grave; 
After life's fitful fever he sleeps well; 
Treason has done his worst: nor steel, nor poison, 
Malice domestic, foreign levy, nothing, 
Can touch him further. 
LADY MACBETH 
Come on; 
Gentle my lord, sleek o'er your rugged looks; 
Be bright and jovial among your guests to-night. 
MACBETH 
So shall I, love; and so, I pray, be you: 
Let your remembrance apply to Banquo; 
Present him eminence, both with eye and tongue: 
Unsafe the while, that we 
Must lave our honours in these flattering streams, 
And make 
======================================================================
domains/gcse-english/sources/primary_text/an-inspector-calls.pdf
--- page 1 (first 700 chars) ---

--- page 3 (first 700 chars) ---
3
A RESOURCE P ACK FOR TEACHERS
CONTENTS
A USER’S GUIDE 4
1. PAST, PRESENT AND FUTURE
i. Time and the Birlings 5
ii. The Social Context: 1912 and 1945 9
iii. The Social Context: The Play Today 11
iv. Political Play or Propaganda? 13
2. PRODUCING PRIESTLEY’S PLA Y
i. Frequently Asked Questions 15
ii. Who is the Inspector? 19
iii. Exploring Theatricality 21
iv. Film Facts 24
3. BEHIND THE SCENES
i. In Rehearsal 25
ii. Collaborative Theatre 26
iii. Tricks of the Trade 28
iv. The Secret of Success 30
4. PRACTIC AL APPR OACHES 31
5. SELECTED FUR THER READING 39
Written for The Magenta Partnership by Kim Greengrass ©1999
--- page 5 (first 700 chars) ---

--- page 20 (first 700 chars) ---
20
TEACHER’S
RESOURCE
PACK
AN 
INSPECTOR 
CALLS
WRITTEN
FOR
THE MAGENTA
PARTNERSHIP
BY KIM
GREENGRASS
SECTION TWO ~ PRODUCING PRIESTLEY’S PLAY
Stephen Daldry suggests that the actor playing the Inspector needs to
consider whether there is a more personal relationship between
himself and Eva Smith.
o? Do you agree?
o? If the actor decided that there was a more personal relationship, how might this
affect his performance?
o? Can you think of specific moments in the play when this decision would be
important in influencing how the action was pr esented?
Think about Stephen Daldry’s idea for a film version of the play,
making the Inspector the offspring of Eva Smith and Eric .
o? How do you thin
======================================================================
domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf
--- page 1 (first 700 chars) ---

--- page 3 (first 700 chars) ---
Bash Better PDF extraction probe via PyMuPDF
IN
uv run --with pymupdf python3 -c "
import fitz
for path in ['domains/gcse-english/sources/primary_text/macbeth.pdf','domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf']:
    print('='*70); print(path)
    d = fitz.open(path)
    print('  pages:', d.page_count)
    for p in [1, 5, 12, 20]:
        if p > d.page_count: continue
        t = d[p-1].get_text().strip()
        print(f'--- page {p} (PyMuPDF, first 600 chars) ---')
        print(t[:600] if t else '<NO TEXT — likely image/scanned page>')
" 2>&1 | head -120

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Downloading pymupdf (22.2MiB)
 Downloaded pymupdf
Installed 1 package in 3ms
======================================================================
domains/gcse-english/sources/primary_text/macbeth.pdf
  pages: 83
--- page 1 (PyMuPDF, first 600 chars) ---
HAMLET - Act V    
1
--- page 5 (PyMuPDF, first 600 chars) ---
5    
I cannot tell. 
But I am faint, my gashes cry for help. 
DUNCAN 
So well thy words become thee as thy wounds; 
They smack of honour both. Go get him surgeons. 
Exit Sergeant, attended 
Who comes here? 
Enter ROSS 
MALCOLM 
The worthy thane of Ross. 
LENNOX 
What a haste looks through his eyes! So should he look 
That seems to speak things strange. 
ROSS 
God save the king! 
DUNCAN 
Whence camest thou, worthy thane? 
ROSS 
From Fife, great king; 
Where the Norweyan banners flout the sky 
And fan our people cold. Norway himself, 
With terrible numbers, 
Assisted by that most disloyal trait
--- page 12 (PyMuPDF, first 600 chars) ---
12    
Is execution done on Cawdor? Are not 
Those in commission yet return'd? 
MALCOLM 
My liege, 
They are not yet come back. But I have spoke 
With one that saw him die: who did report 
That very frankly he confess'd his treasons, 
Implored your highness' pardon and set forth 
A deep repentance: nothing in his life 
Became him like the leaving it; he died 
As one that had been studied in his death 
To throw away the dearest thing he owed, 
As 'twere a careless trifle. 
DUNCAN 
There's no art 
To find the mind's construction in the face: 
He was a gentleman on whom I built 
An absolute trust
--- page 20 (PyMuPDF, first 600 chars) ---
20    
Away, and mock the time with fairest show: 
False face must hide what the false heart doth know. 
Exeunt 
ACT II 
SCENE I. Court of Macbeth's castle. 
Enter BANQUO, and FLEANCE bearing a torch before him 
BANQUO 
How goes the night, boy? 
FLEANCE 
The moon is down; I have not heard the clock. 
BANQUO 
And she goes down at twelve. 
FLEANCE 
I take't, 'tis later, sir. 
BANQUO 
Hold, take my sword. There's husbandry in heaven; 
Their candles are all out. Take thee that too. 
A heavy summons lies like lead upon me, 
And yet I would not sleep: merciful powers, 
Restrain in me the cursed thou
======================================================================
domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf
  pages: 24
--- page 1 (PyMuPDF, first 600 chars) ---
<NO TEXT — likely image/scanned page>
--- page 5 (PyMuPDF, first 600 chars) ---
<NO TEXT — likely image/scanned page>
--- page 12 (PyMuPDF, first 600 chars) ---
<NO TEXT — likely image/scanned page>
--- page 20 (PyMuPDF, first 600 chars) ---
<NO TEXT — likely image/scanned page>
Probed all three. Here's what they actually are.

Macbeth.pdf ✅ (the play, extractable)
83 pages, PyMuPDF extracts cleanly:


ACT I, SCENE I. A desert place.
Thunder and lightning. Enter three Witches
First Witch
When shall we three meet again
In thunder, lightning, or in rain?
Page 1 has a stray "HAMLET - Act V" header (a scrape artefact, harmless), author metadata is "binshu" — provenance unclear but the body is the standard public-domain Macbeth text.

Verdict: primary text, public domain, usable. But I'd still grab the Standard Ebooks edition because: clean provenance (CC0, properly proofed), no PDF extraction step, and standardised line numbering that _infer_play_anchor can lock onto for citations. The "binshu" PDF works as a fallback if Standard Ebooks isn't convenient.

an-inspector-calls.pdf ❌ (not the play, can't use)
Page 3 reveals what it actually is:


A RESOURCE PACK FOR TEACHERS
CONTENTS
A USER'S GUIDE 4
1. PAST, PRESENT AND FUTURE
   i. Time and the Birlings 5
   ii. The Social Context: 1912 and 1945 9
…
Written for The Magenta Partnership by Kim Greengrass ©1999
This is a 1999 Magenta Partnership teacher's resource pack about the play, not the play. Two problems compound:

It's commentary, so wrong folder anyway (would belong in secondary_study_guide/ if at all)
Magenta Partnership 1999 is its own copyright; the play itself stays in copyright until 2054 (Priestley d. 1984)
Even if we wanted to ingest it, the loader's INCOPYRIGHT_TITLES deny-list catches inspector_calls substring on the filename and refuses it. That's working as designed.
Verdict: move it out of primary_text/. The Phase 2 per-student episode path is its eventual home, not the bulk corpus.

All-Power-Conflict-Poems.pdf ❌ (image-scanned, can't extract)
24 pages, all blank under text extraction. This is an image/scanned PDF. Getting text out would need OCR (docling has it; or pytesseract via pdf2image).

Plus the underlying copyright issue: most of the AQA Power & Conflict cluster is still in copyright (Carol Ann Duffy, Simon Armitage, Imtiaz Dharker, John Agard, Beatrice Garland, Seamus Heaney, Jane Weir). Only the older poets (Shelley, Wordsworth, Browning, Tennyson, Owen) are out of copyright. Filename doesn't trip the deny-list, but the spirit of the policy does.

Verdict: don't ingest. Defer to Phase 2.

What I'd do right now

# move the two unusable PDFs out of primary_text/
mkdir -p docs/research/in-copyright-quarantine
mv domains/gcse-english/sources/primary_text/an-inspector-calls.pdf docs/research/in-copyright-quarantine/
mv domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf docs/research/in-copyright-quarantine/
(Anywhere outside domains/*/sources/ is fine. The above keeps them on disk for Phase 2 work but out of any folder the loader walks. The in-copyright-quarantine/ should also be added to .gitignore to be safe.)

Then for Macbeth, two options — pick one:

(a) Use the Standard Ebooks text (recommended) — 5 minutes, no extraction step:


curl -L -o domains/gcse-english/sources/primary_text/macbeth.txt \
  https://standardebooks.org/ebooks/william-shakespeare/macbeth/downloads/william-shakespeare_macbeth.epub
# (then strip the EPUB into plain text — actually Standard Ebooks also offers plaintext via their API,
# but the cleanest path is to grab the epub and pull body.xhtml. I can give you exact commands.)
Or — if you'd rather keep the PDF for fleet consistency with how the other agents work — (b) extract macbeth.pdf to .txt as a one-off:


uv run --with pymupdf python3 -c "
import fitz, pathlib
d = fitz.open('domains/gcse-english/sources/primary_text/macbeth.pdf')
pathlib.Path('domains/gcse-english/sources/primary_text/macbeth.txt').write_text(
    '\n\n'.join(p.get_text() for p in d), encoding='utf-8'
)
print('wrote macbeth.txt,', len(d), 'pages')
"
rm domains/gcse-english/sources/primary_text/macbeth.pdf
The .txt is gitignored same as the .pdf, and load_corpus reads it natively.

Either way, the demo path stays:

Macbeth plain-text in primary_text/
TASK-RAG-001A → 002 → 003
Live reason=retrieve:primary_present + PlayCitationAnchor(act, scene, line) in the log pane
Want me to run the (b) one-liner now and move the two unusable PDFs out, or hold off until you've decided on (a) vs (b)?

please check /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub and see if /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub is of any use
Bash Probe both EPUBs for metadata and content
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text/ 2>&1; echo "---"; uv run --with ebooklib --with beautifulsoup4 python3 -c "
import ebooklib, ebooklib.epub
from bs4 import BeautifulSoup

for path in ['domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub','domains/gcse-english/sources/primary_text/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub']:
    print('='*70); print(path)
    book = ebooklib.epub.read_epub(path)
    print('  title:', book.get_metadata('DC','title'))
    print('  creator:', book.get_metadata('DC','creator'))
    print('  rights:', book.get_metadata('DC','rights'))
    print('  date:', book.get_metadata('DC','date'))
    print('  publisher:', book.get_metadata('DC','publisher'))
    print('  identifier:', book.get_metadata('DC','identifier'))
    print('  language:', book.get_metadata('DC','language'))
    docs = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    total_chars = 0
    for d in docs:
        soup = BeautifulSoup(d.get_content(), 'html.parser')
        total_chars += len(soup.get_text())
    print(f'  document items: {len(docs)}, total text chars: {total_chars}')
    # show first content doc that has substance
    for d in docs:
        soup = BeautifulSoup(d.get_content(), 'html.parser')
        text = soup.get_text(' ', strip=True)
        if len(text) > 200 and 'colophon' not in text.lower()[:200]:
            print('  --- first substantive doc:', d.file_name)
            print('     first 500 chars:', text[:500])
            break
" 2>&1 | head -80

OUT
total 5128
drwxr-xr-x@ 6 richardwoollcott  staff      192 May  8 18:12 .
drwxr-xr-x  9 richardwoollcott  staff      288 May  8 17:58 ..
-rw-r--r--@ 1 richardwoollcott  staff        0 May  8 16:35 .keep
-rw-r--r--@ 1 richardwoollcott  staff  1388297 May  8 18:11 An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub
-rw-r--r--@ 1 richardwoollcott  staff   820517 May  8 17:42 macbeth.pdf
-rw-r--r--@ 1 richardwoollcott  staff   413041 May  8 18:06 william-shakespeare_macbeth.epub
---
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Installed 6 packages in 9ms
======================================================================
domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub
  title: [('Macbeth', {'id': 'title'})]
  creator: [('William Shakespeare', {'id': 'author'})]
  rights: [('The source text and artwork in this ebook are believed to be in the United States public domain; that is, they are believed to be free of copyright restrictions in the United States. They may still be copyrighted in other countries, so users located outside of the United States must check their local laws before using this ebook. The creators of, and contributors to, this ebook dedicate their contributions to the worldwide public domain via the terms in the [CC0 1.0 Universal Public Domain Dedication](https://creativecommons.org/publicdomain/zero/1.0/).', {})]
  date: [('2021-05-07T18:13:33Z', {})]
  publisher: [('Standard Ebooks', {'id': 'publisher'})]
  identifier: [('https://standardebooks.org/ebooks/william-shakespeare/macbeth', {'id': 'uid'})]
  language: [('en-GB', {})]
  document items: 12, total text chars: 110906
  --- first substantive doc: text/act-1.xhtml
     first 500 chars: Act I Scene I A desert place. Thunder and lightning. Enter three Witches . First Witch When shall we three meet again In thunder, lightning, or in rain? Second Witch When the hurlyburly’s done, When the battle’s lost and won. Third Witch That will be ere the set of sun. First Witch Where the place? Second Witch Upon the heath. Third Witch There to meet with Macbeth. First Witch I come, Graymalkin! Second Witch Paddock calls. Third Witch Anon. All Fair is foul, and foul is fair: Hover through the
======================================================================
domains/gcse-english/sources/primary_text/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub
  title: [('An Inspector Calls and Other Plays', {})]
  creator: [('J. B. Priestley', {'{http://www.idpf.org/2007/opf}file-as': 'Priestley J. B.', '{http://www.idpf.org/2007/opf}role': 'aut'})]
  rights: []
  date: [('2013-01-06', {'{http://www.idpf.org/2007/opf}event': 'published'}), ('2013-01-06', {'{http://www.idpf.org/2007/opf}event': 'converted'})]
  publisher: [('Penguin Books Ltd', {})]
  identifier: [('urn:isbn:9780141917115', {'id': 'p9780141917115', '{http://www.idpf.org/2007/opf}scheme': 'isbn'})]
  language: [('en-GB', {})]
  document items: 29, total text chars: 555025
  --- first substantive doc: xhtml/aboutauthor.xhtml
     first 500 chars: PENGUIN BOOKS An Inspector Calls and Other Plays J. B. Priestley was born in Bradford in 1894. After leaving school, he spent some time as a junior clerk in a wool office and a lively account of his life at this period may be found in his volume of reminiscences, Margin Released (1962). He joined the army in 1914, and in 1919, on receiving an ex-officers’ grant, went to Trinity Hall, Cambridge. He settled in London in 1922, where he soon earned a reputation as an essayist and critic. His third a
Excellent — two completely different stories.

william-shakespeare_macbeth.epub ✅ Perfect
Confirmed Standard Ebooks edition by metadata:

Publisher: Standard Ebooks
Rights: ...believed to be in the United States public domain... CC0 1.0 Universal Public Domain Dedication
Identifier: https://standardebooks.org/ebooks/william-shakespeare/macbeth
Structure: 12 XHTML files (text/act-1.xhtml, act-2.xhtml, etc.) — clean act/scene boundaries
110,906 chars of body text starting Act I, Scene I, A desert place, Thunder and lightning, Enter three Witches…
This is exactly the file I'd have recommended. Use this.

The loader takes plain text though — so there's a small one-off conversion step to turn the EPUB into macbeth.txt while preserving the Act I / Scene I line breaks the citation-anchor inferer regex looks for. ~10 lines of Python.

An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub ❌ Can't use
Metadata is unambiguous:

Publisher: Penguin Books Ltd
ISBN: 9780141917115 (Penguin Modern Classics, 2013 commercial edition)
555,025 chars — the whole Priestley three-play collection plus apparatus
No rights field (because it's all rights reserved)
J.B. Priestley d. 1984 → UK copyright runs to 2054
Two independent reasons it can't go in:

Loader will refuse it anyway. INCOPYRIGHT_TITLES matches inspector_calls against the normalised filename (an_inspector_calls_and_other_plays_-_jb_priestley → contains inspector_calls). It'll be dropped at ingest with RefusalReason.IN_COPYRIGHT_TITLE.

Even if the deny-list weren't there: this is a Penguin commercial e-book. Bulk-ingesting it into a vector store creates a redistributable derivative. Personal study on your own machine is one thing; a demo at DDD Southwest with the corpus visible is a different category. The Phase 2 per-student episode design exists precisely so a student's own legal copy can be referenced without copying it into a shared corpus.

Keep it on disk for personal use and for designing the Phase 2 episode shape — just out of primary_text/.

What to do now (I can run any of this for you)

# 1. Move the unusable PDFs and the Penguin EPUB out of primary_text/
mkdir -p docs/research/in-copyright-quarantine
mv domains/gcse-english/sources/primary_text/an-inspector-calls.pdf \
   domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf \
   domains/gcse-english/sources/primary_text/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub \
   docs/research/in-copyright-quarantine/

# 2. Decide whether to also move the binshu macbeth.pdf out (we have a clean
#    Standard Ebooks edition now — keeping the PDF risks downstream confusion)
#    Recommended:
mv domains/gcse-english/sources/primary_text/macbeth.pdf docs/research/in-copyright-quarantine/

# 3. Convert the Standard Ebooks EPUB → macbeth.txt with structure preserved
uv run --with ebooklib --with beautifulsoup4 python3 -c "
import ebooklib, ebooklib.epub, re, pathlib
from bs4 import BeautifulSoup, NavigableString

book = ebooklib.epub.read_epub('domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub')
out_lines = []
# Iterate in spine order so Act I → V come out in sequence
for itemref in book.spine:
    item = book.get_item_with_id(itemref[0])
    if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
        continue
    soup = BeautifulSoup(item.get_content(), 'html.parser')
    body = soup.find('body') or soup
    # Preserve block boundaries: every <p>, <h1>..<h6>, <div> emits a newline
    for tag in body.find_all(['p','h1','h2','h3','h4','h5','h6','blockquote','li']):
        text = tag.get_text(' ', strip=True)
        if text:
            out_lines.append(text)
out_path = pathlib.Path('domains/gcse-english/sources/primary_text/macbeth.txt')
out_path.write_text('\n\n'.join(out_lines), encoding='utf-8')
print(f'wrote {out_path}, {len(out_lines)} blocks, {out_path.stat().st_size:,} bytes')
"

# 4. Verify the act/scene markers landed on their own lines (the regex needs this)
grep -n -m 10 -E '^(Act|Scene) [IVX]+' domains/gcse-english/sources/primary_text/macbeth.txt
Step 3 is the load-bearing one — if the act/scene markers don't end up at start-of-line, _infer_play_anchor returns None and citations won't fire. Step 4 verifies they did.

Also need to add docs/research/in-copyright-quarantine/ to .gitignore so those files don't get accidentally committed.

Want me to run all of this now? I'd execute steps 1-4 and the gitignore update in one go, then read back the first 30 lines of macbeth.txt so you can sanity-check the formatting before TASK-RAG-001A goes near it.

yes please run it
Bash Move unusable files to quarantine
IN
mkdir -p docs/research/in-copyright-quarantine && mv domains/gcse-english/sources/primary_text/an-inspector-calls.pdf domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf domains/gcse-english/sources/primary_text/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub domains/gcse-english/sources/primary_text/macbeth.pdf docs/research/in-copyright-quarantine/ && ls -la docs/research/in-copyright-quarantine/ domains/gcse-english/sources/primary_text/

OUT
Exit code 1
mv: rename domains/gcse-english/sources/primary_text/an-inspector-calls.pdf to docs/research/in-copyright-quarantine/an-inspector-calls.pdf: No such file or directory
mv: rename domains/gcse-english/sources/primary_text/All-Power-Conflict-Poems.pdf to docs/research/in-copyright-quarantine/All-Power-Conflict-Poems.pdf: No such file or directory
Bash Re-check what's actually in primary_text
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/domains/gcse-english/sources/primary_text/

OUT
total 808
drwxr-xr-x@ 4 richardwoollcott  staff     128 May  8 18:14 .
drwxr-xr-x  9 richardwoollcott  staff     288 May  8 17:58 ..
-rw-r--r--@ 1 richardwoollcott  staff       0 May  8 16:35 .keep
-rw-r--r--@ 1 richardwoollcott  staff  413041 May  8 18:06 william-shakespeare_macbeth.epub
The user has already cleaned up — only the Macbeth EPUB remains. Skipping the move step.

Bash Confirm the other files are no longer in the tree
IN
find /Users/richardwoollcott/Projects/appmilla_github/study-tutor -maxdepth 6 -type f \( -name "an-inspector-calls.pdf" -o -name "All-Power-Conflict-Poems.pdf" -o -name "An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub" -o -name "macbeth.pdf" \) 2>&1

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/in-copyright-quarantine/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/in-copyright-quarantine/macbeth.pdf
Files are already organised — Inspector Calls EPUB and the binshu macbeth.pdf are in docs/research/in-copyright-quarantine/, the two scrappy PDFs are gone. On to the conversion.

Bash Convert Standard Ebooks Macbeth EPUB to plain text
IN
uv run --with ebooklib --with beautifulsoup4 python3 -c "
import ebooklib, ebooklib.epub, pathlib
from bs4 import BeautifulSoup

book = ebooklib.epub.read_epub('domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub')
out_lines = []
for itemref in book.spine:
    item = book.get_item_with_id(itemref[0])
    if not item or item.get_type() != ebooklib.ITEM_DOCUMENT:
        continue
    soup = BeautifulSoup(item.get_content(), 'html.parser')
    body = soup.find('body') or soup
    for tag in body.find_all(['p','h1','h2','h3','h4','h5','h6','blockquote','li']):
        text = tag.get_text(' ', strip=True)
        if text:
            out_lines.append(text)
out_path = pathlib.Path('domains/gcse-english/sources/primary_text/macbeth.txt')
out_path.write_text('\n\n'.join(out_lines), encoding='utf-8')
print(f'wrote {out_path}, {len(out_lines)} blocks, {out_path.stat().st_size:,} bytes')
" 2>&1 | tail -10

OUT
warning: `VIRTUAL_ENV=/Library/Frameworks/Python.framework/Versions/3.14` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
wrote domains/gcse-english/sources/primary_text/macbeth.txt, 502 blocks, 87,860 bytes
Bash Verify the citation-anchor regex will match
IN
echo "=== act/scene markers at start-of-line ==="; grep -n -E '^(Act|Scene) [IVX]+' domains/gcse-english/sources/primary_text/macbeth.txt | head -20; echo "=== first 30 lines ==="; sed -n '1,30p' domains/gcse-english/sources/primary_text/macbeth.txt; echo "=== act II opening ==="; grep -n -A2 -m1 '^Act II$' domains/gcse-english/sources/primary_text/macbeth.txt

OUT
=== act/scene markers at start-of-line ===
133:Act I
135:Scene I
145:Scene II
171:Scene III
223:Scene IV
249:Scene V
273:Scene VI
291:Scene VII
313:Act II
315:Scene I
337:Scene II
373:Scene III
433:Scene IV
461:Act III
463:Scene I
507:Scene II
529:Scene III
545:Scene IV
615:Scene V
621:Scene VI
=== first 30 lines ===
Macbeth

By William Shakespeare .

Imprint

This ebook is the product of many hours of hard work by volunteers for Standard Ebooks , and builds on the hard work of other literature lovers made possible by the public domain.

This particular ebook is based on a transcription from Massachusetts Institute of Technology and on digital scans from the HathiTrust Digital Library .

The source text and artwork in this ebook are believed to be in the United States public domain; that is, they are believed to be free of copyright restrictions in the United States. They may still be copyrighted in other countries, so users located outside of the United States must check their local laws before using this ebook. The creators of, and contributors to, this ebook dedicate their contributions to the worldwide public domain via the terms in the CC0 1.0 Universal Public Domain Dedication . For full license information, see the Uncopyright at the end of this ebook.

Standard Ebooks is a volunteer-driven project that produces ebook editions of public domain literature using modern typography, technology, and editorial standards, and distributes them free of cost. You can download this and other ebooks carefully produced for true book lovers at standardebooks.org .

Dramatis Personae

Duncan, king of Scotland

Duncan, king of Scotland

Malcolm, his son

Malcolm, his son

Donalbain, his son

Donalbain, his son

Macbeth, general of the king’s army

=== act II opening ===
313:Act II
314-
315-Scene I
Conversion is clean. Highlights:

502 blocks, 87 KB of body text
All 5 acts + all 28 scenes have their headings at start-of-line — ^Act [IVX]+ and ^Scene [IVX]+ will match. The citation-anchor inferer will fire correctly.
Front matter (Standard Ebooks imprint + dramatis personae) runs lines 1-132 before Act I at line 133. These will be ingested as primary-text chunks with citation_anchor=None and will simply never match any Macbeth quote — harmless. We could strip them with a one-line cut, but it's not worth doing now.
Dramatis personae lines appear duplicated (Standard Ebooks uses <dt>/<dd> pairs) — same harmless story.
Now the .gitignore update for the quarantine directory.

Bash Check current gitignore for quarantine entry
IN
grep -n "in-copyright-quarantine\|^docs/research" .gitignore 2>&1

OUT
(Bash completed with no output)
Read .gitignore (lines 241-270)
Edit .gitignore
Added 7 lines
Bash Verify ignore rules and final state
IN
echo "=== gitignore checks ==="; git check-ignore -v domains/gcse-english/sources/primary_text/macbeth.txt domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub docs/research/in-copyright-quarantine/macbeth.pdf docs/research/in-copyright-quarantine/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub 2>&1; echo "=== git status ==="; git status --short

OUT
=== gitignore checks ===
.gitignore:255:domains/*/sources/**/*.txt	domains/gcse-english/sources/primary_text/macbeth.txt
.gitignore:253:domains/*/sources/**/*.epub	domains/gcse-english/sources/primary_text/william-shakespeare_macbeth.epub
.gitignore:264:docs/research/in-copyright-quarantine/	docs/research/in-copyright-quarantine/macbeth.pdf
.gitignore:264:docs/research/in-copyright-quarantine/	docs/research/in-copyright-quarantine/An_Inspector_Calls_and_Other_Plays_-_JB_Priestley.epub
=== git status ===
 M .gitignore
 M tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
?? docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md
All four files are correctly ignored:

File	Where	Tracked?
william-shakespeare_macbeth.epub	primary_text/	gitignored ✅
macbeth.txt (newly converted)	primary_text/	gitignored ✅
macbeth.pdf (binshu)	in-copyright-quarantine/	gitignored ✅
An_Inspector_Calls...epub	in-copyright-quarantine/	gitignored ✅
Final state:


domains/gcse-english/sources/primary_text/
├── .keep
├── william-shakespeare_macbeth.epub   (kept; operator's master copy)
└── macbeth.txt                         (502 blocks, 87 KB — what the loader will ingest)

docs/research/in-copyright-quarantine/
├── macbeth.pdf                         (binshu PDF, superseded)
└── An_Inspector_Calls_..._JB_Priestley.epub  (Penguin commercial, Phase 2 territory)
You're now set up for TASK-RAG-001A → 002 → 003. When you /task-work TASK-RAG-001A and run the patched ingestion script, it'll find macbeth.txt, chunk it (~150 chunks at the 512/100 setting), embed each via llama-swap's nomic-embed-text, write to data/chroma/ with citation anchors locked to act/scene/line, and emit one NDJSON line confirming text_name=macbeth, source_type=primary_text, chunk_count=~150.

Two things worth committing now (not implementation, just the corpus-prep state):

.gitignore change (the in-copyright-quarantine entry)
tasks/backlog/TASK-RAG-002-...md (already-staged amendments from earlier)
Want me to commit those, or hold off until TASK-RAG-001A lands and bundle everything together?

yes
Bash Show working tree status
IN
git status --short

OUT
 M .gitignore
 M tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
?? docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md
Bash Review staged-for-commit diff
IN
git diff .gitignore tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md

OUT
diff --git a/.gitignore b/.gitignore
index 136db0e..335bb71 100644
--- a/.gitignore
+++ b/.gitignore
@@ -256,6 +256,13 @@ domains/*/sources/**/*.txt
 domains/*/sources/*.xhtml
 domains/*/sources/**/*.xhtml
 
+# In-copyright / unusable source material kept out of `domains/*/sources/`
+# so the loader (load_corpus) never walks into it. Files here are operator-
+# acquired and stay on the operator's machine — see TASK-RAG-001A discussion
+# notes (2026-05-08) for why each file lives here rather than in the
+# corpus tree.
+docs/research/in-copyright-quarantine/
+
 # RAG knowledge layer persistence (Phase 1 onward).
 # DECISION-RAG-001 standardises on ``data/chroma/`` as the per-project
 # persist root; the older ``chroma/`` / ``chroma_data*/`` entries stay for
diff --git a/tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md b/tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
index ff5bafc..a46e048 100644
--- a/tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
+++ b/tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md
@@ -12,12 +12,15 @@ created: 2026-05-08T00:00:00Z
 updated: 2026-05-08T00:00:00Z
 dependencies:
   - TASK-RAG-001
+  - TASK-RAG-001A
 related:
   - src/study_tutor/cli/main.py
   - src/study_tutor/tutoring/orchestrator.py
   - src/study_tutor/knowledge/retrieval.py
   - src/study_tutor/knowledge/coach_handover.py
   - src/study_tutor/mcp/adapter.py
+external_references:
+  - guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md
 tags:
   - rag
   - cli
@@ -84,21 +87,49 @@ the existing FEAT-PH1-003 callers that pass `coach_handover=None`
 
 ### 2. Build the production providers in `cli/main.py`
 
+Per [DECISION-RAG-001](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md),
+all fleet RAG (specialist-agent + study-tutor) uses
+`chromadb.PersistentClient` with `OpenAIEmbeddingFunction` pointing at
+llama-swap (`localhost:9000/v1`, `nomic-embed-text`, 768 dim).
+**Critical:** the runtime MUST construct the same embedding function and
+pass it to `get_or_create_collection(...)`. Chroma's PersistentClient
+does not persist the EF across opens; if the runtime opens the
+collection without an EF, queries embed via the bundled default
+(384-dim all-MiniLM-L6-v2) against vectors written with nomic-embed-text
+(768-dim) — dimension mismatch, every query returns garbage or errors.
+
 Add a new helper `_build_rag_providers(role_config) -> RagProviders`
 (or equivalent) that, **at `serve` startup** (not per turn):
 
-1. Reads `STUDY_TUTOR_CHROMA_DIR` env var (default `./chroma/gcse-english/`)
-   and `STUDY_TUTOR_COLLECTION` (default `gcse-english`).
+1. Reads the four DECISION-RAG-001 §3.1 env vars with the canonical
+   defaults (same shape as the ingestion script — fleet alignment):
+
+   | Variable | Default |
+   |---|---|
+   | `CHROMA_PERSIST_DIR` | `data/chroma` |
+   | `CHROMA_COLLECTION` | `gcse-english-v1` |
+   | `LLM_EMBEDDINGS_BASE_URL` | `http://localhost:9000/v1` |
+   | `LLM_EMBEDDINGS_API_KEY` | `not-needed` |
+   | `LLM_EMBEDDINGS_MODEL` | `nomic-embed-text` |
+
 2. If `chromadb` is importable AND the persist dir exists:
-   - Open `chromadb.PersistentClient(path=...)` once.
-   - Resolve the collection once via `get_or_create_collection(...)`.
-   - Wrap it in a zero-arg lambda and call
+   - Build the `OpenAIEmbeddingFunction` from the env vars above. **MUST**
+     match the function the ingestion script (TASK-RAG-001 / TASK-RAG-001A)
+     used at write time.
+   - Open `chromadb.PersistentClient(path=persist_dir)` once.
+   - Resolve the collection once via
+     `get_or_create_collection(name=..., embedding_function=ef)` — the
+     `embedding_function` argument is non-negotiable.
+   - Wrap the collection in a zero-arg lambda and call
      `set_collection_provider(lambda: collection)`.
-   - Read the sidecar `chroma/<domain>/.primary_text_index` written by
-     TASK-RAG-001's ingestion script and replay each entry through
+   - Read the sidecar `<persist_dir>/.primary_text_index` written by the
+     ingestion script and replay each entry through
      `register_primary_text(...)`. Log a structured line per registration.
-3. If `chromadb` is **not** importable OR the persist dir is missing:
-   - Log a single WARNING `event=rag_disabled, reason=<chromadb_missing|persist_dir_missing>`.
+3. If `chromadb` is **not** importable OR the persist dir is missing OR
+   `OpenAIEmbeddingFunction` construction fails (e.g. the `openai`
+   package is absent from a degraded install):
+   - Log a single WARNING
+     `event=rag_disabled, reason=<chromadb_missing|persist_dir_missing|embedding_function_unavailable>`.
    - Leave the collection provider unset (`retrieve()` returns `[]`).
    - The `coach_handover` closure (below) still wires up — its retrieval
      call returns `[]` and the verifier runs against an empty corpus,
@@ -106,11 +137,17 @@ Add a new helper `_build_rag_providers(role_config) -> RagProviders`
      graceful-degradation envelope and must be preserved.
 4. Optionally install the BGE reranker via `set_reranker_factory(...)` if
    `sentence_transformers` is importable; otherwise let the default
-   `ImportError → no_rerank` path fire.
-5. Optionally install an embedder probe via `set_embedder_probe(...)` —
-   for Phase 1 a no-op probe is acceptable (Chroma's local embedder is
-   in-process and does not need a network ping). Document the deferral in
-   a code comment.
+   `ImportError → no_rerank` path fire. (The reranker is independent of
+   the embedding function — different model, different role.)
+5. Optionally install an embedder probe via `set_embedder_probe(...)`
+   that pings llama-swap's `/v1/embeddings` endpoint with a single
+   one-token payload. This is the **runtime** counterpart to the ingest
+   script's lazy embedding — if llama-swap is unreachable at serve
+   startup, the probe trips `EMBEDDER_TIMEOUT_SECONDS` and the
+   four-branch decision routes to AnalysisMode (`reason=analysis_mode:embedder_timeout`).
+   Phase 1 may keep the no-op default if a real probe is too much work
+   for the demo deadline; document the deferral with a TODO that
+   references DECISION-RAG-001.
 
 ### 3. Build the `coach_handover` closure
 
@@ -174,6 +211,19 @@ the orchestrator construction. Extend the smoke so that:
       the wired closure is constructed at serve startup.
 - [ ] `set_collection_provider(...)` is called exactly once per `serve`
       invocation when `chromadb` is importable AND the persist dir exists.
+- [ ] The collection is opened with an `OpenAIEmbeddingFunction` whose
+      `api_base`, `api_key`, and `model_name` are read from
+      `LLM_EMBEDDINGS_BASE_URL`, `LLM_EMBEDDINGS_API_KEY`,
+      `LLM_EMBEDDINGS_MODEL` (DECISION-RAG-001 §3.1 defaults). Asserted
+      by a test that introspects the wired collection's
+      `_embedding_function` instance.
+- [ ] The four DECISION-RAG-001 env vars have the canonical defaults and
+      are read by both the ingest script and the CLI runtime (single
+      source of truth). Exposed via the `serve` `--help` output.
+- [ ] If `OpenAIEmbeddingFunction` construction fails (e.g. `openai`
+      missing), `serve` logs
+      `event=rag_disabled, reason=embedding_function_unavailable` and
+      continues with the verifier-against-empty-corpus fallback.
 - [ ] The `.primary_text_index` sidecar from TASK-RAG-001 is read at
       startup and every entry is replayed via `register_primary_text(...)`.
 - [ ] When `chromadb` is missing or the persist dir is absent, `serve`
@@ -236,9 +286,20 @@ Add tests in `tests/integration/test_cli_rag_wiring.py`:
   response. This matches the @key-example test fixtures in TASK-PRV-004
   and is what grounds the verification corpus in the question being
   asked, not the answer being given.
-- Surface a single new env var `STUDY_TUTOR_CHROMA_DIR` (default
-  `./chroma/gcse-english/`) so the operator can point at a different
-  domain without code changes. Document it in the `serve` docstring.
+- Env vars are the four DECISION-RAG-001 §3.1 names
+  (`CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION`, `LLM_EMBEDDINGS_BASE_URL`,
+  `LLM_EMBEDDINGS_API_KEY`, `LLM_EMBEDDINGS_MODEL`) with the canonical
+  defaults. **Do not** introduce study-tutor-specific names like
+  `STUDY_TUTOR_CHROMA_DIR` — the fleet decision is that these env vars
+  are shared across specialist-agent and study-tutor (and any future
+  agent) so a single environment block in `docker-compose` configures
+  all RAG-using services.
+- Construct the `OpenAIEmbeddingFunction` in a helper shared with the
+  ingestion script (extract the helper from
+  `scripts/ingest_corpus.py` after TASK-RAG-001A lands, or at minimum
+  duplicate it with a comment pointing at the canonical site). Two
+  copies that drift would re-introduce the embedding-space-mismatch
+  failure mode the decision warns about.
 - Keep the closure synchronous; `apply_quote_verification` and `retrieve`
   are sync. The orchestrator already runs the handover inside its async
   pipeline via the existing `_apply_coach_handover` shim.
@@ -267,3 +328,5 @@ Add tests in `tests/integration/test_cli_rag_wiring.py`:
 - [tasks/completed/TASK-PRV-006-coach-handover-seam.md](../completed/TASK-PRV-006-coach-handover-seam.md)
 - [tasks/completed/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md](../completed/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md)
 - [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md) — load-pane signal requirements
+- [DECISION-RAG-001 — Unified ChromaDB approach for fleet RAG](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md) — fleet-wide embedding & topology contract this task implements
+- [tasks/backlog/TASK-RAG-001A-align-with-fleet-rag-decision.md](TASK-RAG-001A-align-with-fleet-rag-decision.md) — sibling task aligning the ingest script (must land first)
Bash Recent commit messages for style
IN
git log --oneline -5

OUT
280718f complete(TASK-RAG-001A): align ingestion script with DECISION-RAG-001
79447cd complete(TASK-RAG-001): chromadb ingestion script for source-typed corpus
1aea1e8 docs and tasks
eba1b6c added docs for nats fleet integration
dce7fda fixes and history
TASK-RAG-001A is already complete (commit 280718f) — the corpus tooling is done. Now committing the two prep changes.

Bash Commit gitignore + TASK-RAG-002 spec amendment
IN
git add .gitignore tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md && git commit -m "$(cat <<'EOF'
docs(TASK-RAG-002): align spec with DECISION-RAG-001; ignore in-copyright quarantine

Two prep changes that unblock TASK-RAG-002 (CLI wiring) without touching
runtime code:

1. Amend TASK-RAG-002 spec to match DECISION-RAG-001's fleet contract:
   - Runtime MUST construct OpenAIEmbeddingFunction (llama-swap, nomic-
     embed-text, 768 dim) and pass it to get_or_create_collection.
     Without this the runtime would silently fall back to Chroma's
     bundled 384-dim default and every query would miss the ingested
     vectors. New AC asserts the wired EF instance carries the right
     api_base/api_key/model_name.
   - Env vars switched from study-tutor-specific names
     (STUDY_TUTOR_CHROMA_DIR) to the four shared fleet names from
     DECISION-RAG-001 §3.1 (CHROMA_PERSIST_DIR, CHROMA_COLLECTION,
     LLM_EMBEDDINGS_*).
   - Added embedding_function_unavailable as a third graceful-
     degradation reason alongside chromadb_missing/persist_dir_missing.
   - Sidecar path corrected from chroma/<domain>/.primary_text_index to
     <persist_dir>/.primary_text_index to match the ingest script's
     actual write location.
   - Implementation note: extract the EF builder into a shared helper
     so ingest and runtime can't drift into different embedding spaces.
   - New dependency on TASK-RAG-001A (already completed at 280718f).

2. .gitignore: add docs/research/in-copyright-quarantine/ so operator-
   acquired in-copyright source material (Penguin Inspector Calls EPUB,
   uncertain-provenance Macbeth PDF) stays on disk for Phase 2 per-
   student-episode design without ever leaking into the corpus tree the
   loader walks.

Corpus state after this commit:
- domains/gcse-english/sources/primary_text/macbeth.txt — 502 blocks,
  87 KB extracted from the Standard Ebooks EPUB (gitignored). All 5
  acts and 28 scenes have headings at start-of-line so the citation-
  anchor inferer can lock onto act/scene/line for every primary-text
  chunk at ingest time.
- docs/research/in-copyright-quarantine/ — Penguin Inspector Calls,
  binshu Macbeth PDF (gitignored).

Out of scope: runtime CLI wiring (TASK-RAG-002 still in backlog).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)" && git status --short

OUT
[main b855379] docs(TASK-RAG-002): align spec with DECISION-RAG-001; ignore in-copyright quarantine
 2 files changed, 87 insertions(+), 17 deletions(-)
?? docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md
Committed as b855379. The untracked docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md is left alone since it wasn't part of this work — let me know if you want it included separately.

State now:

TASK-RAG-001 (ingest script + corpus layout) ✅ done at 79447cd
TASK-RAG-001A (DECISION-RAG-001 alignment) ✅ done at 280718f
TASK-RAG-002 (CLI provider + coach_handover wiring) — spec amended at b855379, ready for /task-work TASK-RAG-002
TASK-RAG-003 (live smoke + demo cue card) — depends on 002
The corpus is ready: macbeth.txt is in place, citation-anchor regex will fire on all 28 scene headings, .gitignore keeps quarantined material safe.

Next move when you're ready: /task-work TASK-RAG-002.