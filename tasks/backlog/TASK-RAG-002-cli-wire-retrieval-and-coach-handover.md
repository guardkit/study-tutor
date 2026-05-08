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
