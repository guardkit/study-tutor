# Review Report — TASK-REV-PRV4

**Feature:** Primary-Text RAG and Source-Typed Quote Verifier (FEAT-PH1-004)
**Mode:** decision · **Depth:** standard
**Generated:** 2026-04-30

---

## 1. Context-A directives applied

- **Focus:** all aspects (architecture + safety + algorithm + integration)
- **Trade-off priority:** quality / safety
- **Concerns highlighted:** Coach handover contract; agentic-dataset-factory
  (ADF) chunker reuse posture; fuzzy-correction false positives
  (Open Question 3 from openwebui-rag-empirical-findings-2026-04-23.md)

All 15 ASSUMs in the assumptions manifest are marked `human_response: confirmed`,
so this review extends them with **mechanism-level resolutions**, not
substantive policy changes.

---

## 2. Technical options analysis

### Option A — Three-module split with citation-aware chunker variant *(Recommended)*

- `corpus.py` — `SourceType` enum + `CorpusChunk` Pydantic model +
  loader that walks the four-folder tree and infers source-type from
  parent directory.
- `retrieval.py` — `should_retrieve()` decision function +
  `retrieve()` source-filtered search (Chroma + bge-reranker, with
  graceful degradation).
- `quote_verifier.py` — `extract_quotes()` + `verify_quote()` +
  `rewrite_response()` returning the four match types as a tagged
  union of dataclasses.
- **Citation-aware chunker variant** adapted from
  `agentic-dataset-factory/ingestion/chunker.py`. ADF's
  `RecursiveCharacterTextSplitter` is fixed-size with `Chunk(text,
  metadata)` — close to what we need, but we extend the metadata
  dict with `source_type`, `text_name`, and `citation_anchor` (act/
  scene/line for plays; chapter/paragraph for novels). Adapt rather
  than import to avoid taking on ADF's domain-config coupling.

**Complexity:** Medium (5/10) · **Effort:** 5–7 hours sequential,
~3–4h elapsed with wave-2 parallelism

**Pros:**
- Three modules align cleanly with the three behavioural surfaces
  in the BDD spec (corpus loader / retrieval-decision / verifier).
- Each module is a single-responsibility seam — testable in
  isolation; matches the 23-Apr empirical R1/R2/R3 mental model.
- Chunker adaptation keeps citation-anchor logic close to where
  it's consumed (verifier), instead of forcing it through ADF's
  generic `Chunk.metadata` dict.
- Clean handover into TASK-DTL-002: `verifier_metadata` is a
  Pydantic model with deterministic fields (`primary_matches`,
  `secondary_rewrites`, `fuzzy_corrections`, `stripped`,
  `long_passage_shortenings`, `cross_text_mismatches`).

**Cons:**
- More upfront module work than a single-file "verifier.py" approach.
- Citation-anchor parsing for novels (chapter/paragraph) is fuzzier
  than plays (act/scene/line) — needs an explicit per-text
  `citation_strategy` selection at ingest time.

### Option B — Single `knowledge.py` module with submodule classes

- One module, three classes (`Corpus`, `Retriever`, `QuoteVerifier`).
- Single import surface for the Coach to consume.

**Complexity:** Low–Medium (4/10) · **Effort:** 4–5 hours

**Pros:**
- Smaller surface area; faster to land before Friday 2 May target.
- Easier to refactor into separate modules later if needed.

**Cons:**
- Single-responsibility violation; large file becomes hard to test.
- Corpus loader and verifier have very different concerns
  (filesystem vs string matching) — co-locating them obscures the
  natural seam line.
- BDD spec organises scenarios into three slices; module structure
  diverging from the spec creates cognitive load on test-to-task
  mapping.

### Option C — Reuse ADF chunker and ChromaDB ingestion as-is

- Import the agentic-dataset-factory ingestion pipeline as a library
  dependency; only write a thin wrapper for source-type inference
  and the verifier.

**Complexity:** Medium (5/10 — high integration risk) ·
**Effort:** 3–4 hours if integration is clean, 8–10h if not

**Pros:**
- Maximum DRY — no duplicate ingestion code.
- ADF's pattern is already proven on the same corpus (Mr Bruff
  PDFs).

**Cons:**
- ADF is in a separate repo — cross-repo coupling adds a build
  dependency that the Phase 1 timeline can't absorb if integration
  is bumpy.
- ADF doesn't carry citation-anchor metadata; would still need a
  post-processing step to derive `citation_anchor` from chunk
  positions.
- ADF expects a domain-config Pydantic stub (`SourceDocument`) that
  doesn't match our four-folder source-typed shape — adapter logic
  required either way.

---

## 3. Recommended approach

### ✅ Option A — Three-module split with citation-aware chunker variant

**Rationale:**

1. **Quality/safety priority** (Context-A trade-off) — three
   isolated modules with three independent test surfaces give the
   strongest defence-in-depth against the load-bearing safety
   invariants (secondary-not-as-primary; cross-text-not-misattributed;
   long-passage-shortened).
2. **Module structure mirrors BDD slice structure** — Slice 1
   (corpus loader, 8 scenarios), Slice 2 (retrieval-decision +
   filtered retrieval, 11 scenarios), Slice 3 (verifier, 16
   scenarios). The bdd-linker step (Step 11) becomes mechanical.
3. **Coach handover (TASK-DTL-002 seam) is a single Pydantic
   contract** — `VerifierMetadata` is consumed by `score_rubric`'s
   `quote_fidelity` criterion. Stable, versionable, testable.
4. **Open Question 3 closes naturally** — fuzzy correction is
   restricted to **primary-text** matches only. If a study-guide
   paraphrase happens to be ≤3 edits from a Shakespeare line,
   primary-wins precedence in `verify_quote()` ensures the primary
   match is taken; the secondary chunk is never even consulted for
   correction. (See @edge-case @primary-wins scenario.)
5. **ADF chunker is adapted, not imported** — copies the proven
   `RecursiveCharacterTextSplitter` + `Chunk(text, metadata)` shape
   into `corpus.py`, extends metadata with source-typed fields.
   Avoids cross-repo build dependency for a 30-line splitter.

### Recommended resolutions for low-confidence assumptions

| ASSUM | Topic | Resolved as |
|-------|-------|-------------|
| **008** | AQA refusal mechanism | Filename-pattern matching at the loader (regex over `past[_-]paper`, `mark[_-]scheme`, `examiner[_-]report`), with the deny-list as a defence-in-depth layer; refusal log line references the publisher's prohibition. |
| **009** | In-copyright deny-list | Explicit `INCOPYRIGHT_TITLES` constant in `corpus.py`: `{"inspector_calls", "blood_brothers", "dna", "lord_of_the_flies", "anita_and_me", "animal_farm"}`. Loader matches case-insensitively against filename stems and folder names. Refusal log line advises the per-student Phase 2 path. |
| **010** | Secondary attribution phrase | Single configurable `SECONDARY_ATTRIBUTION_TEMPLATES` constant: `("as one critic observes", "as one study guide notes", "as one commentator suggests")`. Verifier picks deterministically by hash of the matched phrase to keep tests stable. |
| **011** | Long-passage shortening | Verbatim quotes >30 words are reduced to a short embedded quote of ≤12 words by selecting the densest analytical span (longest contiguous substring sharing the matched chunk's start or end). |
| **013** | Embedder unavailability | 5-second per-call timeout on the embedding service; on timeout, `should_retrieve()` returns `(False, "analysis_mode:embedder_timeout")` and the turn proceeds without retrieval. Unit test injects a sleep-stub embedder. |

### Recommended resolutions for medium-confidence assumptions

| ASSUM | Topic | Resolved as |
|-------|-------|-------------|
| **005** | Citation-anchor shape | Plays use `act/scene/line` (e.g. `"5.1.35"`); novels use `chapter/paragraph` (e.g. `"III.7"`). `CitationAnchor` is a Pydantic discriminated union keyed by `kind: Literal["play","novel"]`. |
| **006** | Skip-reason strings | Literal strings: `"analysis_mode:no_primary_text"`, `"ao3_only:training_first"`, `"analysis_mode:embedder_timeout"`. Constants exposed at `retrieval` module level so tests can assert against the names without string drift. |
| **007** | AO3 mixed-mode behaviour | AO3-only → bypass; AO3+(AO1/AO2) → retrieve for non-AO3 evidence and the turn metadata records `mode: "mixed"`. Decision tree is a pure function over `set[str]` of focus AOs. |
| **012** | Whitespace/punctuation normalisation | `_normalise(text)` collapses internal whitespace, strips surrounding punctuation, equates curly/straight quote variants, lowercases. Applied symmetrically to the quoted span and every candidate corpus chunk before matching. |
| **015** | Cross-text mismatch | Spans matching a different primary text than the session's text → paraphrase rewrite with softened certainty + `cross_text_mismatch` event. Never annotated with the wrong text's citation. |

---

## 4. Architecture and integration

### Coach handover contract (settled)

The verifier rewrites the response **in place** and emits a
structured `VerifierMetadata` Pydantic model alongside it. The Coach
(TASK-DTL-002) consumes both:

```python
@dataclass(frozen=True)
class VerifierMetadata:
    primary_matches: list[PrimaryMatch]            # annotated with citation
    secondary_rewrites: list[SecondaryRewrite]     # phrase + attribution
    fuzzy_corrections: list[FuzzyCorrection]       # corrected + edit distance
    stripped: list[NoMatchStrip]                   # original phrase + reason
    long_passage_shortenings: list[Shortening]    # original + reduced
    cross_text_mismatches: list[CrossTextEvent]   # span + wrong-text id
    retrieval_skipped_reason: str | None          # surfaces analysis-mode
```

`score_rubric` derives the `quote_fidelity` criterion from this
metadata using a deterministic mapping (e.g. each
`SecondaryRewrite` → −0.1, each `NoMatchStrip` → −0.2, capped at
0.0). When `retrieval_skipped_reason` is set, the criterion is
suppressed (pass-through 1.0) per @edge-case @quote-fidelity
@retrieval scenario.

This shape is consumed in **TASK-DTL-002** acceptance criterion
"Quote-verifier annotation flows" and the seam test at
`tests/integration/test_tutoring_loop.py`.

### ADF chunker reuse

Adapt-rather-than-import. Copy the shape of
`agentic-dataset-factory/ingestion/chunker.py:30` into
`src/study_tutor/knowledge/corpus.py:chunk_text`, but extend the
metadata dict with source-typed fields:

```python
metadata = {
    "source_file": path,
    "source_type": source_type,    # NEW
    "text_name": text_name,        # NEW
    "citation_anchor": anchor,     # NEW (CitationAnchor model)
    "chunk_index": index,
}
```

The decision **not** to add `agentic-dataset-factory` as a build
dependency keeps Phase 1 self-contained and avoids cross-repo
coupling on a 30-line splitter.

### Open Question 3 resolution (false-positive fuzzy correction)

The risk: when both primary-text and secondary chunks are in the
corpus, the verifier could "correct" a legitimate study-guide
paraphrase into a misattributed Shakespeare quote.

**Resolution:** the verifier applies match types in strict
precedence order:

1. **Primary verbatim** (annotate with citation)
2. **Cross-text mismatch** (rewrite as paraphrase — never annotate)
3. **Secondary verbatim** (rewrite with critic-style attribution)
4. **Fuzzy primary** (≤3 edits from a primary-text chunk only)
5. **No match** (strip + paraphrase)

Fuzzy correction is restricted to primary-text source. Secondary
matches at the verbatim layer take precedence over fuzzy primary
matches, so a study-guide paraphrase that's ≤3 edits from a
Shakespeare line is rewritten as paraphrase, not "corrected" into a
misattributed quote. Tested by an explicit Group D edge-case.

---

## 5. Risks and trade-offs

| Risk | Mitigation |
|------|-----------|
| Citation-anchor parsing for novels less well-defined than plays | Per-text `citation_strategy` constant; default fallback to chapter-only when paragraph cannot be inferred. |
| ChromaDB ingestion path not yet wired in this repo | Build plan §Morning Track B already names this — add as dependency in TASK-PRV-001 (corpus loader). |
| Demo-readiness clock — Friday 2 May target | Wave-2 parallelism (corpus + verifier independent of retrieval) + 7 small subtasks averaging ~30–60 min each. |
| Reranker download (~568 MB) on first run | Documented as a one-time setup; tests use a fake reranker stub. |
| Cross-repo divergence with `appmilla-fleet` group-id convention | Out of scope (FEAT-PH1-001 owns Graphiti group-id semantics). |

---

## 6. Subtask sequencing (obvious risks only)

Recommended slicing into **7 subtasks** across **3 waves**:

- **Wave 1 (foundation):** TASK-PRV-001 (citation anchor & source
  type models); runs alone — produces the Pydantic shapes everything
  else consumes.
- **Wave 2 (parallel-safe):** TASK-PRV-002 (corpus loader),
  TASK-PRV-003 (retrieval-decision function); these touch
  independent modules and can run in parallel.
- **Wave 3 (parallel-safe):** TASK-PRV-004 (source-filtered retrieval
  with reranker degradation), TASK-PRV-005 (quote verifier — extract +
  match + rewrite); both depend on Wave 2 outputs but on different
  modules.
- **Wave 4 (integration):** TASK-PRV-006 (Coach handover seam — wires
  `verify_quotes()` + `VerifierMetadata` into TASK-DTL-002's
  `score_rubric`), TASK-PRV-007 (integration smoke + tests).

Full slicing is emitted by `/feature-plan` [I]mplement.

---

## 7. Decision recommendation

**Recommended:** **[I]mplement** with Option A.

The five low-confidence and four medium-confidence assumptions all
have concrete mechanism-level resolutions. The Coach handover
contract is settled. Open Question 3 closes via primary-wins
precedence + fuzzy-restricted-to-primary. The Phase 1 critical-path
calendar (Friday 2 May target) accommodates 7 small subtasks
averaging 30–60 minutes each, with wave-2 parallelism.

If the [I]mplement choice is **not** taken, the fallback documented
in phase-1-build-plan G1 — "ship a 5-criterion Coach for the demo
and defer the verifier to Phase 2 with the rubric weight
redistributed" — remains available, but is materially weaker for
the hackathon's pedagogical-quality story (the source-typed verifier
is the load-bearing differentiator).
