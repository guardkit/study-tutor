# ADR-ARCH-022 — Corpus retrieval: add a lexical/exact-match path; defer agentic retrieval-as-tool

## Status

Proposed

**Date:** 2026-07-02
**Phase:** Phase 1 (Knowledge & Curriculum) — revisited during mobile/voice (Act 2) planning
**Supersedes:** none
**Related:** [ADR-ARCH-002](ADR-ARCH-002-three-layer-architecture.md) (three-layer; RAG is Layer 2), [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) (Coach `AsyncSubAgent`), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-user/local posture), [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (on-device residency), [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) (sync read path), [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (async write-back; 78.98s `add_episode`), ADR-FLEET-003 (agent capability exposure — MCP for agents, HTTP/WS for app clients), FEAT-PH1-004 (Primary-Text RAG + quote verifier), [rag-grounding-design.md](../../research/ideas/rag-grounding-design.md), [openwebui-rag-empirical-findings-2026-04-23.md](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md). **Adjacent:** [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the Student-Model layer moves off Graphiti/FalkorDB to a study-tutor-owned Postgres (JSONB) store (out of scope here; the corpus store is independent).

## Context

**Trigger.** ChromaDB has publicly repositioned from "vector database for RAG" to **"search infrastructure for AI"** (their CEO: *"We never use the term RAG"*), foregrounding hybrid / full-text / regex search, "context engineering," and their **Context Rot** research (across 18 frontier models, reliability degrades non-uniformly as input length grows, *even on trivial tasks*). This prompted a review: is classic single-shot top-K RAG still the right shape for study-tutor's primary-text grounding, or should the project adopt "agentic search"?

**What study-tutor already implements** (so this is not a greenfield question — most of the "agentic" thesis is already in the codebase):

- **Selective, pre-Player retrieval decision.** The four-branch `decide_retrieval` / `should_retrieve` tree ([retrieval.py](../../../src/study_tutor/knowledge/retrieval.py)) — AO3-only bypass; no-primary → AnalysisMode; mixed-AO3 tag; primary-present retrieve — plus a 5s embedder-availability override. This *is* conditional/adaptive retrieval; the system does not retrieve blindly on every turn.
- **Curated context, not context-stuffing.** Source-typed chunks (`primary_text` / `secondary_study_guide` / `secondary_critical`), **primary-first** ordering, a BGE cross-encoder rerank (`BAAI/bge-reranker-v2-m3`), and defence-in-depth AQA exclusion at both ingest and retrieval.
- **A deterministic post-hoc quote verifier** ([quote_verifier.py](../../../src/study_tutor/knowledge/quote_verifier.py)) — extracted quotes are exact-substring + bounded edit-distance (≤3) matched against corpus chunks read back from ChromaDB, then stripped / paraphrased / corrected / cited by act·scene. **This is the load-bearing fabrication-safety gate.** Vector retrieval is a fabrication-*pressure* reducer, not the guarantee.

**Corpus store.** The text corpus lives in **ChromaDB** (local `PersistentClient`), injected via `set_collection_provider`. It is **independent of the Graphiti/FalkorDB Student-Model layer currently being removed** — removing FalkorDB does not touch the corpus.

**Scope note — Graphiti → fleet-memory.** Student state (per-topic confidence, XP, achievements) is being migrated off Graphiti/FalkorDB. Motivation: graphiti-core's `add_episode` measured **78.98s median** ([ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md)) because of its internal **entity-extraction LLM fan-out**, a real GB10 memory/throughput drag. That migration is resolved by [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — a study-tutor-owned **Postgres (JSONB)** store, **not** fleet-memory. This ADR governs the document-retrieval layer only and treats the Student-Model backend as an independent store.

**Latency reality** (correcting an earlier loose "~15s voice budget"). There is **no measured 15s figure**. The measured cost is **> 10s for the local LLM hop alone** on the fine-tuned Gemma 4 MoE, and the codified budget is **`tutor_turn` p95 < 10s** ([ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md)). The "15s" in `rag-grounding-design.md` is a *tool-description budget* ceiling for adding tool-call grounding, not a voice round-trip. On the planned voice path, STT (Parakeet) and TTS (Kokoro) wrap that LLM hop; **local generation dominates the turn**, and a second in-loop LLM hop roughly **doubles** it.

**Model reality.** The Player is a fine-tuned **Gemma 4 MoE (4B active)**, documented "patchy at disciplined tool-calling." Verified external research (Chroma Context Rot; agentic-RAG surveys): sub-7B models are harmed by retrieved context by its **mere presence**, and exhibit a tool **over-calling** bias that does **not** improve with scale.

**Empirical precedent.** [OpenWebUI Finding 1](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — RAG against a *partial* corpus (study-guide only) **degraded** the fine-tune by suppressing its own correct verbatim Shakespeare. A self-directed retrieval loop free to over-call would amplify exactly this.

## Decision

Three commitments for the **corpus-retrieval layer**.

### D1 — Add a lexical / exact-match retrieval path alongside vector similarity — **DO**

- Add a **lexical branch** to the retrieval layer matching exact / near-exact strings, complementing dense vector similarity. GCSE literature answers hinge on **verbatim quotation** ("find the line containing *unsex me here*") — precisely where dense embeddings are weakest and where fabrication pressure (and its exam-day cost) is highest. This is the one genuine gap Chroma's "beyond RAG" critique exposes for this system, and it directly counters Context Rot by fetching precise tokens.
- **Implementation: reuse the existing ChromaDB collection** via Chroma's native full-text + `$regex` / `$contains` query surface over the chunk `document` field. **No new store.** The exact-match semantics already in [quote_verifier.py](../../../src/study_tutor/knowledge/quote_verifier.py) are the reference for match behaviour.
- **Merge** lexical + vector candidates before the existing BGE rerank (candidate union / hybrid-merge), keeping the reranker as the final ordering step and `_primary_first` partitioning unchanged.
- **Keep it local.** Do **not** adopt Chroma Cloud's managed RRF hybrid Search API to obtain this — it is Cloud-only and adds network latency + corpus egress for a capability approximable locally.
- **Gate:** measure against the golden-quote eval harness (fabrication rate target < 5% Phase A / < 1% Phase B). The lexical path must not raise the verifier's false-correction rate (the "study-guide paraphrase corrected into a misattributed quote" risk — [OpenWebUI Open Question 3](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)).

### D2 — Do not expose retrieval as a Player-callable tool (agentic retrieval-as-tool) — **DEFER**

- Retrieval stays a **pre-Player, orchestrator-decided, injected-context** step (the `decide_retrieval` tree), **not** a tool the Player invokes mid-generation. This closes [OpenWebUI Open Question 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) with a *no-for-now*.
- **Reasons (stacked):**
  1. **Small-model tool-calling weakness** + the over-call bias → fabricated-query and over-retrieval failure modes on a 4B-active Player.
  2. **Latency** — a second in-loop LLM hop roughly doubles an already > 10s turn and breaches the `tutor_turn` p95 < 10s budget; worse on the voice path.
  3. **Empirical degradation precedent** (Finding 1) — self-directed over-retrieval would amplify the observed suppression of the fine-tune's own correct text.
  4. **Consistency with the Graphiti-removal lesson** — LLM-in-the-hot-loop on the GB10 already proved too costly on the *write* path (78.98s `add_episode`); do not re-introduce it on the *read* path.
- **Safe halfway step (allowed, not required):** a **second retrieval pass may be triggered by the async Coach** ([ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md)) on low-confidence turns. The Coach is already off the caller-facing latency path (fire-and-forget, [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md)), so this buys iteration without a tool in the weak caller's hands or on the turn budget.
- **Revisit trigger:** reopen when **(a)** the Player slot moves to a reliably tool-calling model, **and** **(b)** multi-subject expansion introduces corpora where multi-hop retrieval genuinely beats prefix injection.

### D3 — Reaffirm ChromaDB local-persistent as the corpus store; skip Cloud, Cloud-hybrid-RRF, and collection forking — **SKIP**

- The corpus is a handful of public-domain set texts — **orders of magnitude** below Chroma's single-node ceiling (~5–10M vectors). Cloud buys nothing on scale and costs latency + egress + an external dependency, against the GB10 local-first posture ([ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) / [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)).
- **Collection forking is Cloud-only** and solves a problem study-tutor does not have — per-student state lives in the Student-Model layer (study-tutor-owned Postgres per [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)), not the text corpus. Revisit only if per-student *in-copyright* text caching is ingested **and** the system is already on Cloud for other reasons.

**Scope boundary.** This ADR governs **document/corpus retrieval only**. The Student-Model backend (now study-tutor-owned Postgres per [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)) is a separate decision; nothing here depends on it, because the corpus store (ChromaDB) and the memory store are independent surfaces.

## Alternatives considered

- **Adopt "agentic RAG" wholesale (Player drives multi-tool search).** Rejected now — the four stacked reasons in D2. Anthropic's own default applies: prefer the simplest architecture; optimising single LLM calls with retrieval is usually enough.
- **Replace vector RAG with lexical-only.** Rejected. Dense retrieval still wins for conceptual/thematic queries ("Lady Macbeth's ambition in 1.5") where the student's wording won't lexically match the text. Lexical **complements**, not replaces.
- **Do nothing / keep vector-only.** Rejected. Leaves the one genuine gap (exact-quote retrieval) unaddressed, in the exact domain where fabrication is most damaging.
- **Build a separate SQLite FTS5 index for lexical** (per the original [rag-grounding-design §3](../../research/ideas/rag-grounding-design.md) sketch). Rejected. Chroma now provides native full-text/regex over the *same* collection; a second store is avoidable complexity. The FTS5 sketch predates Chroma's full-text support and was never built.
- **Migrate corpus to Chroma Cloud for managed hybrid RRF.** Rejected — D3.
- **Block retrieval work until the fleet-memory migration lands.** Rejected. The corpus and memory layers are independent; coupling them is a false dependency.

## Consequences

**Positive:**
- Closes the one real gap in the "beyond RAG" critique for this system (exact-quote retrieval) at near-zero infra cost by reusing the existing Chroma collection + verifier match semantics.
- Keeps the fabrication-safety guarantee **deterministic** (verifier) rather than delegating it to a probabilistic agentic-eval loop.
- Protects the `tutor_turn` p95 < 10s budget and the voice path by refusing an in-loop second LLM hop.
- Records a defensible "we evaluated agentic search and deferred it, with explicit triggers" position — useful for the Act 2 / Act 4 production-differentiation narrative.
- Decouples the retrieval decision from the Graphiti → fleet-memory migration; neither blocks the other.

**Negative:**
- Hybrid lexical + vector adds a candidate source and a merge step to the retrieval path; modest added complexity in the retrieval module and its tests.
- Multi-hop / comparative queries remain served by a single injected-context pass and may retrieve less completely than an iterative agent would. Accepted for now; the Coach-triggered second pass is the escape hatch.
- Open Question 4 is closed "no for now"; a future reader may want it reopened. The revisit triggers are explicit to make that cheap.

## Downstream artefacts flagged stale

- [docs/planning/feature-roadmap.md](../../planning/feature-roadmap.md) — FEAT-PH1-004 "dynamic retrieval" should name the lexical branch; record D2/D3 outcomes.
- [docs/research/ideas/rag-grounding-design.md](../../research/ideas/rag-grounding-design.md) §3 — the "reuse FalkorDB for vectors" store choice **and** the "SQLite FTS5" lexical sketch are both superseded (corpus is on ChromaDB; lexical via Chroma native full-text).
- [docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — Open Question 4 resolved by D2 (defer, with triggers).
- [docs/gamification/design.md](../../gamification/design.md) §6 / §11 and any doc asserting "confidence/state maintained in Graphiti" — reframe to the **Student-Model layer** (study-tutor-owned Postgres per [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)), not Graphiti specifically.
- [docs/handoffs/study-tutor-mobile-voice-conversation-starter.md](../../handoffs/study-tutor-mobile-voice-conversation-starter.md) — voice-turn latency framing should cite the measured **> 10s LLM hop** + **p95 < 10s** budget rather than an unqualified "15s".

## C4 diagram re-review status

System topology is **unchanged**: same containers and external systems. D1 adds a query mode to the existing ChromaDB-backed retrieval relationship (label text: "similarity search" → "hybrid lexical + similarity search"); it introduces no new container, store, or external dependency. The mandatory C4 re-review gate is **not** triggered; affected description strings in `container.md` are refreshed in-place if/when this ADR is accepted.

## References

- ChromaDB positioning + **Context Rot** research — `trychroma.com`, `research.trychroma.com/context-rot` (retrieved 2026-07-02; the "search infrastructure for AI" tagline and the CEO "we never use the term RAG" framing are verbatim as of that date).
- [ADR-ARCH-002](ADR-ARCH-002-three-layer-architecture.md), [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md), [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md), [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md), [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md).
- ADR-FLEET-003 — agent capability exposure boundary (MCP vs HTTP/WS).
- FEAT-PH1-004 — Primary-Text RAG + quote verifier.
- [src/study_tutor/knowledge/retrieval.py](../../../src/study_tutor/knowledge/retrieval.py) — `decide_retrieval` / `retrieve` / reranker.
- [src/study_tutor/knowledge/quote_verifier.py](../../../src/study_tutor/knowledge/quote_verifier.py) — deterministic quote gate.
- [rag-grounding-design.md](../../research/ideas/rag-grounding-design.md) — Phase A/B retrieval design (the ">10s LLM hop" and "15s tool-description budget" phrasing this ADR corrects).
- [openwebui-rag-empirical-findings-2026-04-23.md](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — Finding 1 (partial-corpus degradation), Open Question 4 (retrieval-as-tool).
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — 78.98s `add_episode` (the LLM-in-loop write cost motivating Graphiti removal; the write-path analogue of D2's read-path argument).
</content>
</invoke>
