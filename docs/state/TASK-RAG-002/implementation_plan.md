# Implementation Plan — TASK-RAG-002

**Title**: Wire ChromaDB provider and `coach_handover` closure into CLI `serve`
**Complexity**: 6/10 (multi-module integration with subtle correctness invariants)
**Estimated**: ~3 hours
**Mode**: design-first (per task frontmatter); user chose to stop at Phase 2.8 checkpoint

---

## Architecture Decisions

### AD-1: CoachHandover seam widening (option A — Callable widening)

**Default per task spec** ("Default to A unless the architectural-reviewer flags it"). User confirmed: defer to architect, default A.

**Current shape** (`src/study_tutor/tutoring/orchestrator.py:50`):
```python
CoachHandover = Callable[[str, Any], tuple[str, VerifierMetadata]]
# (raw_response, session_state) -> (response_for_coach, metadata)
```

**New shape**:
```python
CoachHandover = Callable[[str, str, Any], tuple[str, VerifierMetadata]]
# (raw_response, learner_message, session_state) -> (response_for_coach, metadata)
```

**Rationale**:
- The retrieval query is **the learner message** (per task spec: "matches the @key-example fixtures in TASK-PRV-004"). The closure cannot synthesise it from the response and session_state alone.
- A widened `Callable` is the smallest-surface change that satisfies the requirement. Two call sites in `_apply_coach_handover` + the type alias + the tests.
- A `CoachHandoverContext` dataclass (option B) is YAGNI for Phase 1: no second extension point exists today, and adding fields to the dataclass later is the same diff size as widening the Callable.
- Backward compatibility: `coach_handover=None` legacy callers (FEAT-PH1-003 tests, existing CLI Phase 0 path) are unaffected — the orchestrator's `_apply_coach_handover(raw, session_state)` branch returns early on `None` before ever touching the new signature.

### AD-2: Module-level state lifecycle

The retrieval module's `_collection_provider` / `_reranker_factory` / `_PRIMARY_TEXT_INDEX` are **process-scoped singletons** (see `retrieval.py:140`, `:432`, `:461`). They are wired **once** at `serve` startup and live for the process lifetime. The `_build_orchestrator_factory` closure already follows this pattern (`coach_system_prompt` cached once at construction; see `cli/main.py:111`).

**Decision**: Wire ChromaDB bits **before** `_build_orchestrator_factory` is called, in `serve` itself. Reasoning:
- Dependency direction is correct: closure → retrieval module-state, never the other way.
- Boot-smoke (`MCPAdapter.__init__` invoking the factory once) gets to validate the wired collection provider.
- Per-turn factory invocation does not pay setup cost.

### AD-3: Shared embedding-function helper

Per task implementation note: avoid drift between ingest and runtime by extracting `_make_embedding_function`.

**Location**: `src/study_tutor/knowledge/embedding_function.py` (new module — under `knowledge/` because that's where the other RAG-runtime helpers live).

**Public API**:
```python
def build_openai_embedding_function() -> Any:
    """Construct the canonical OpenAIEmbeddingFunction per DECISION-RAG-001 §3.1.

    Reads LLM_EMBEDDINGS_BASE_URL / API_KEY / MODEL with the canonical defaults.
    Raises ImportError if chromadb is not installed (caller decides degradation).
    """
```

Both `scripts/ingest_corpus.py` and `cli/main.py` import this helper. The single source of truth blocks the embedding-space-mismatch failure mode the decision warns against.

### AD-4: Embedder probe — defer to no-op default for Phase 1 demo

Per task spec §2 step 5: "Phase 1 may keep the no-op default if a real probe is too much work for the demo deadline; document the deferral with a TODO that references DECISION-RAG-001."

**Decision**: Defer. The retrieval module's default `_default_embedder_probe` is a sync no-op that always returns "available" within budget — the four-branch decision still routes correctly when llama-swap is reachable (which is the demo state). Add a clearly-flagged TODO at the wiring site referencing DECISION-RAG-001 §3.1 and the failure mode the probe would catch (embedder timeout → `reason=analysis_mode:embedder_timeout`).

This is YAGNI-correct for the 16 May demo. Post-demo, swap the default for an HTTP probe that hits `localhost:9000/v1/embeddings` with a one-token payload.

### AD-5: Reranker — try-import in default factory; no explicit wiring

The retrieval module already lazy-imports `sentence_transformers.CrossEncoder` in `_load_reranker` when no factory is installed (`retrieval.py:497`). The `set_reranker_factory` call is therefore **optional**. We do not call it from `serve` — the production behaviour is "use the default factory which tries the real import, falls back to `mode=no_rerank` on `ImportError`."

This matches the task spec: "Optionally install the BGE reranker via `set_reranker_factory(...)` if `sentence_transformers` is importable; otherwise let the default `ImportError → no_rerank` path fire."

### AD-6: Retrieval-mode surfacing — `event=orchestrator_turn_completed` per-turn log line (revised)

**Original draft proposed a separate `event=orchestrator_retrieval_mode` line. Architect flagged that as a spec deviation — AC literally says "`event=orchestrator_turn_completed, retrieval_mode=...`". Plan revised to match the AC.**

The event `orchestrator_turn_completed` does not currently exist in the codebase (verified via grep — only `orchestrator_turn_flagged` and `orchestrator_latency_over_budget` are emitted). This task introduces it.

**Decision**: emit a single structured log line per turn from the closure, regardless of which decision branch fired:

| Branch | Log line shape |
|---|---|
| Retrieve (rerank or no_rerank) | `event=orchestrator_turn_completed text_name=<n> retrieval_mode=<rerank\|no_rerank> chunks=<count>` |
| AO3 bypass | `event=orchestrator_turn_completed text_name=<n> retrieval_mode=skipped reason=ao3_only:training_first` |
| AnalysisMode (no primary text) | `event=orchestrator_turn_completed text_name=<n> retrieval_mode=skipped reason=analysis_mode:no_primary_text` |
| No `text_name` (baseline-degraded plan) | `event=orchestrator_turn_completed text_name=<empty> retrieval_mode=skipped reason=no_text_name` |

This satisfies the AC literally (one event name, one place to grep), gives the demo log pane a single filter to apply, and side-steps the state-leakage trap where `get_last_retrieval_mode()` returns the previous turn's value when the current turn skipped retrieval (the no-retrieval branches set `retrieval_mode=skipped` explicitly rather than calling `get_last_retrieval_mode()`).

The closure runs inside the orchestrator's `_apply_coach_handover` shim — well-positioned to emit this since it sees both the decision and the retrieval mode. We do not also emit from the orchestrator's `_build_result` (that would double-log).

The `TurnResult` propagation referenced in the task spec ("the structured log line / TurnResult") is deferred to Phase 2 with a TODO at the closure site — the demo signal is the log line, and the AC explicitly says "log line" first.

### AD-7: Primary-text index sidecar replay — fail-soft per entry, log at WARNING

The sidecar (`<persist_dir>/.primary_text_index`, written by ingest) is one-name-per-line, sorted, trailing newline (see `scripts/ingest_corpus.py:356`). At `serve` startup we read each line, strip whitespace, skip empties, and call `register_primary_text(name)`. Any per-line failure (empty after strip → ValueError from `register_primary_text`) is logged at **WARNING** and skipped — a corrupt sidecar must not crash boot, but a silently-missed registration would route `decide_retrieval` to the wrong branch (AnalysisMode for a text that does have primary chunks indexed) with no operator signal. Architect flagged this; WARNING is the right level.

---

## Files

### Create (3)

| Path | Purpose | Estimated LOC |
|---|---|---|
| `src/study_tutor/knowledge/embedding_function.py` | Shared `build_openai_embedding_function()` helper. Single source of truth for the EF construction (DECISION-RAG-001 §3.1). | ~60 |
| `src/study_tutor/cli/rag_wiring.py` | New helper module with `_build_rag_providers(...)` orchestration: opens Chroma, registers primary texts from sidecar, wires `set_collection_provider`. Pure side-effect function, returns nothing; raises only on programmer error (caught at `serve`). | ~130 |
| `tests/integration/test_cli_rag_wiring.py` | Five integration tests per task spec: provider wired path, provider missing path, closure end-to-end, AO3 bypass, verifier-exception regression. Reuses `_FakeCollection` from `test_rag_end_to_end.py` via shared fixture (extracted to `tests/integration/_rag_fixtures.py` if needed, but more likely just a parametrize-from). | ~280 |

### Modify (4)

| Path | Change | Estimated LOC delta |
|---|---|---|
| `src/study_tutor/tutoring/orchestrator.py` | Widen `CoachHandover` type alias to take `learner_message: str` as second arg. Update `_apply_coach_handover` signature and the two call sites in `run_turn` (initial + revision). | ~10 |
| `src/study_tutor/cli/main.py` | Import `_build_rag_providers` and `_build_coach_handover`. Call `_build_rag_providers(role_config)` once before `_build_orchestrator_factory`. Replace `coach_handover=None` at line 149 with the wired closure. Add five env-var documentation lines to `serve --help`. | ~50 |
| `scripts/ingest_corpus.py` | Replace `_make_embedding_function()` body with a call to the shared helper. Keeps the function in place (and its tests) but eliminates the drift surface. | ~5 (net: -10/+15) |
| `src/study_tutor/mcp/adapter.py` | Extend the boot smoke (`__init__` line 187). When the orchestrator factory smoke succeeds AND the collection provider is wired, also invoke the provider once and assert non-None. Logs `event=rag_disabled, reason=...` if not wired. | ~15 |

**Total**: 3 new files (~470 LOC), 4 modified files (~80 LOC delta). Within the 180-minute estimate.

---

## External Dependencies

**No new packages**. `chromadb`, `sentence-transformers`, `openai` are already in the `[rag]` optional extra (see `pyproject.toml:63-66`). The runtime imports them lazily and degrades gracefully when absent — same posture as the ingest script (TASK-RAG-001A).

---

## Phases

### Phase A — Seam widening (AD-1, ~25 min)
1. Update `CoachHandover` type alias in `orchestrator.py:50`.
2. Update `_apply_coach_handover(self, raw_response, learner_message, session_state)` signature.
3. Update both `_apply_coach_handover` call sites in `run_turn` (initial response site at line 484 + revision site at line 561) to forward `learner_message`.
4. Update `__all__` (no rename, just signature change — list unchanged).
5. Run unit tests for orchestrator (`tests/unit/tutoring/test_orchestrator*.py`) — they currently pass `coach_handover=None` or use simple stubs, both should keep working since the optional `None` branch in `_apply_coach_handover` short-circuits before dispatch.

### Phase B — Shared embedding-function helper (AD-3, ~20 min)
1. Create `src/study_tutor/knowledge/embedding_function.py` with `build_openai_embedding_function()`.
2. Refactor `scripts/ingest_corpus.py:_make_embedding_function` to delegate to the helper.
3. Verify ingest still runs idempotently with no behavioural change.

### Phase C — RAG wiring helper (AD-2, AD-4, AD-5, AD-7, ~45 min)
1. Create `src/study_tutor/cli/rag_wiring.py` with:
   - `RAG_PERSIST_DIR_ENV`, `RAG_COLLECTION_ENV` constants (the four DECISION-RAG-001 env vars + canonical defaults).
   - `_resolve_persist_dir()`, `_resolve_collection_name()` helpers that read env vars with the canonical defaults.
   - `_replay_primary_text_index(persist_dir)` that reads the sidecar and replays each entry through `register_primary_text(...)` with per-entry try/except.
   - `_build_rag_providers(role_config)` that:
     - Resolves env vars (logs values for the demo log pane).
     - Tries `import chromadb` → catches `ImportError` → logs `rag_disabled reason=chromadb_missing` → returns.
     - If persist dir doesn't exist → logs `rag_disabled reason=persist_dir_missing` → returns.
     - Tries `build_openai_embedding_function()` → catches `ImportError` (e.g. openai missing) → logs `rag_disabled reason=embedding_function_unavailable` → returns.
     - Opens `chromadb.PersistentClient(path=str(persist_dir))`.
     - Calls `client.get_or_create_collection(name=..., embedding_function=ef)`.
     - Calls `set_collection_provider(lambda: collection)`.
     - Calls `_replay_primary_text_index(persist_dir)`.
     - Logs `event=rag_wired collection=... persist_dir=... primary_texts=N`.
2. Inline the embedder-probe TODO referencing DECISION-RAG-001 §3.1 with the deferred-from-Phase-1 reason.

### Phase D — coach_handover closure (~25 min)
1. In `cli/main.py`, add module-level `_build_coach_handover()` that returns the closure exactly as specified in the task description, except:
   - Closure signature: `(raw_response, learner_message, session_state)` matching widened `CoachHandover`.
   - Per AD-6 (revised in v2): emit `event=orchestrator_turn_completed` from the closure on every branch with branch-specific `retrieval_mode={rerank|no_rerank|skipped}` — see AD-6 for the per-branch log line shapes.
2. In `_build_orchestrator_factory` constructor: call `_build_coach_handover()` once (closure is process-scoped — same lifecycle as `coach_system_prompt`) and pass it to `PlayerCoachOrchestrator(coach_handover=...)` at line 149.

### Phase E — `serve` integration (~15 min)
1. In `serve()`, after `role_config = load_role(role)` and before `_build_orchestrator_factory`:
   ```python
   _build_rag_providers(role_config)
   ```
2. Update `serve --help` to document the five DECISION-RAG-001 env vars (canonical defaults).

### Phase F — boot smoke extension (~10 min)
1. In `MCPAdapter.__init__` (after the existing factory smoke at line 187):
   ```python
   from study_tutor.knowledge.retrieval import _collection_provider as _cp_sentinel
   # Read via the public retrieval API instead — see code for actual seam.
   ```
2. The cleanest seam is to expose a public `get_collection_provider()` accessor in `retrieval.py` (4 LOC, mirrors the existing `set_collection_provider`/`reset_collection_provider` pair) and have the adapter call it. Logs `event=rag_disabled` (if None) or asserts the provider returns non-None.

### Phase G — Tests (~40 min)
Write the five integration tests per the task spec:

1. **Provider wired path**: monkeypatch `chromadb.PersistentClient` (sys.modules-level) to return a fake; assert `_collection_provider()` returns the fake after `_build_rag_providers` runs.
2. **Provider missing path**: delete persist dir from `tmp_path`; run `_build_rag_providers`; capture log records via `caplog`; assert `event=rag_disabled reason=persist_dir_missing` was emitted; assert `_build_orchestrator_factory` still constructs.
3. **Closure end-to-end**: set up `_FakeCollection` (reused from `test_rag_end_to_end.py`), wire it via `set_collection_provider`, register `Macbeth`, build the closure with `_build_coach_handover()`, drive one synthetic turn through it (passing `(raw_response, learner_message, session_state)`), assert the rewritten string carries the citation annotation and the metadata has at least one `primary_matches` entry whose `citation_anchor.act == 1`.
4. **AO3 bypass**: drive the closure with a session_state whose `focus_aos = {"AO3"}`, instrument the fake collection with a query-call counter, assert counter == 0 after the call and the returned metadata's `retrieval_skipped_reason == "ao3_only:training_first"`.
5. **Verifier-exception regression**: monkeypatch `verify_quotes` to raise `RuntimeError`, drive the closure, assert it returns `(raw_response, metadata)` with `metadata.verifier_exception is True` and no exception bubbles up to the caller.

Test infrastructure notes:
- Reuse `_FakeCollection` from `test_rag_end_to_end.py`. If extracting to `tests/integration/_rag_fixtures.py` is too disruptive, copy-paste with a comment pointing at the canonical site (mirrors the AQA filter regex precedent in `retrieval.py:395`).
- All tests get the autouse `_isolate_retrieval_state`-style fixture (clear primary text index, reset collection provider, reset reranker factory, reset embedder probe).

### Phase H — Smoke runs (~10 min)
1. `uv run pytest tests/unit/tutoring/ tests/integration/test_rag_end_to_end.py tests/integration/test_cli_rag_wiring.py -v` — all green.
2. `uv run python -c "from study_tutor.cli.main import _build_rag_providers; from study_tutor.roles.loader import load_role; _build_rag_providers(load_role('tutor'))"` — observe either `event=rag_wired` (if `data/chroma/` exists from a prior ingest) or `event=rag_disabled reason=persist_dir_missing` (clean checkout).

---

## Test Strategy

| Test | Type | Source |
|---|---|---|
| 5 new integration tests in `test_cli_rag_wiring.py` | Integration | This task |
| Existing `test_rag_end_to_end.py` (3 tests) | Regression | Must still pass |
| Existing `test_orchestrator*.py` unit suite | Regression | Must still pass — seam widening is additive for `coach_handover=None` callers |
| Existing `test_mcp_lca_smoke.py` | Regression | Boot-smoke extension must not break LCA-004 contract |

**Coverage target**: the new `cli/rag_wiring.py` module has six branches (chromadb missing / persist dir missing / EF construction failure / happy path / sidecar missing / sidecar with bad entries). Each branch has at least one test or is a deliberately-untested log-only branch (sidecar empty file).

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Embedding-space mismatch (writer EF ≠ reader EF) | 🔴 High | Single-source helper (`build_openai_embedding_function()`); test asserts `collection._embedding_function` is non-None and is `OpenAIEmbeddingFunction`. |
| `set_collection_provider` called from a test but never reset | 🟡 Medium | Autouse fixture with `reset_collection_provider`/`reset_reranker_factory`/`clear_primary_text_index` (mirrors `test_rag_end_to_end.py` pattern). |
| Boot-smoke regression breaks LCA-004 / LCA-008 | 🟡 Medium | Read-only check; only adds a logger call when provider is unset. The factory smoke at line 187 stays untouched. |
| Documentation drift on env-var names | 🟢 Low | Canonical defaults defined as module-level constants in `cli/rag_wiring.py`, imported by ingest helper. `--help` text references the constants. |
| Closure called with `session_state.text_name = ""` (baseline-degraded plan) | 🟢 Low | Closure short-circuits on `not text_name` and routes to `apply_quote_verification(raw, [], "", retrieval_skipped_reason=None)` — already specified in task description. |
| Per-turn closure called many times → log-volume noise | 🟢 Low | Log at INFO when retrieval succeeds, no log when AO3 bypass / no-text. Demo log pane filters by event prefix. |

No 🔴 risks remain after mitigations.

---

## Deferred / Out of scope

Per task §"Out of scope" — confirmed:
- Optional `[rag]` extra packaging (TASK-RAG-001).
- DDD demo smoke session against Lilymay/Synology FalkorDB (TASK-RAG-003).
- Surfacing retrieval evidence in the MCP `tutor_turn` JSON-RPC response (Phase 2; Coach already consumes internally).

Additionally deferred from this task with TODO references:
- Real embedder probe (AD-4). TODO at the `set_embedder_probe` site references DECISION-RAG-001 §3.1.
- Threading `retrieval_mode` into `TurnResult` (AD-6). Phase 2 concern; today the demo signal is the structured log line.

---

## Knowledge Graph Context

No Graphiti context retrieved at planning time (project knowledge graph not available in this session — graceful degradation envelope per CLAUDE.md). Plan derives from:
- The exhaustive task spec at `tasks/in_progress/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md`.
- DECISION-RAG-001 §3.1 (referenced from task; embedding contract).
- Direct code reads of the five related files at task-spec § "References".

---

## Acceptance Criteria Mapping

| AC | Plan element | Status |
|---|---|---|
| `coach_handover=None` removed from `cli/main.py` | Phase D | ✅ |
| `set_collection_provider` called once per `serve` | Phase C, Phase E | ✅ |
| `OpenAIEmbeddingFunction` wired with canonical env vars | Phase B (helper), Phase C (use) | ✅ |
| Five env vars + canonical defaults exposed in `serve --help` | Phase E | ✅ |
| `event=rag_disabled reason=embedding_function_unavailable` on EF failure | Phase C step 1 (try/except around `build_openai_embedding_function`) | ✅ |
| Sidecar replayed via `register_primary_text` | Phase C step 1 (`_replay_primary_text_index`) | ✅ |
| `event=rag_disabled reason=...` on chromadb-missing or persist-dir-missing | Phase C step 1 | ✅ |
| `CoachHandover` widened; legacy `None` callers unchanged | Phase A | ✅ |
| Macbeth AO1+AO2 turn produces non-empty `primary_matches` | Phase G test 3 | ✅ |
| AO3-only turn: `retrieval_skipped_reason="ao3_only:training_first"`, zero retrieve calls | Phase G test 4 | ✅ |
| `get_last_retrieval_mode()` forwarded into structured log | Phase D step 1, AD-6 | ✅ |
| `architectural-reviewer` signoff on widening (A vs B) | Phase 2.5B | ✅ APPROVE WITH RECOMMENDATIONS (option A confirmed; AD-6 + AD-7 revised in this plan) |

---

## Plan version: v2
**Generated**: 2026-05-08
**Author**: Claude Opus 4.7 (1M)
**Mode**: design-first (per task frontmatter); user requested stop at Phase 2.8 checkpoint

### Revision history

- **v1** — Initial plan.
- **v2** — AD-6 revised (event name `orchestrator_turn_completed` per AC, with branch-specific `retrieval_mode` values to side-step the `get_last_retrieval_mode()` state-leakage trap on skip branches). AD-7 revised (sidecar fail-soft logs at WARNING, not INFO). Both per architectural-reviewer recommendations.
