# ADR-ARCH-032 — Subject-scoped RAG: per-subject collections, subject-keyed wiring, closure-level coverage check

## Status

**Proposed — built on Rich's Lane 2 step 2 spec word (2026-08-02, in-session:
"yes please proceed"); ratifies with the lane's merge word.**

**Date:** 2026-08-02 (Lane 2 step 2 of the plan of record)
**Related:** ADR-TUTOR-MULTI-SUBJECT (the mechanism this plumbs);
[ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) (whose
per-account-collection tenancy this composes with);
DECISION-RAG-001 (guardkit — the unified chromadb pattern this extends);
`docs/design/contracts/SUBJECT_DEFAULT.md` (the `english` default);
the Lane 2 1a receipt
([RESULTS-lane2-rag-image-1a-2026-08-01.md](../../runbooks/RESULTS-lane2-rag-image-1a-2026-08-01.md)).

## Context

RAG went live 2026-08-02 as a single-collection English layer
(`gcse-english-v1`, one module-level collection provider, one flat
primary-text registry, retrieval blind to `session.subject`). The plan's
Lane 2 step 2 names the build: per-subject collections *or* a subject
metadata field (one design decision), a subject-keyed primary-text
registry, `session.subject` threaded into the coach-handover closure,
per-subject ingest roots, and a **mandatory per-subject corpus-coverage
check** (the partial-corpus degradation finding: weak retrieval is worse
than no retrieval).

## Decision

### D1 — Per-subject collections (not a metadata field)

One ChromaDB collection per subject, in the single persistent store:

- **Naming:** `gcse-<subject>-v1`. The existing `gcse-english-v1` already
  fits the scheme — English's collection is grandfathered untouched (no
  re-ingest, no re-embed). The `-v1` version suffix stays load-bearing
  per DECISION-RAG-001. (Dulcie's KS3 level dimension, when it lands,
  extends the scheme in its own decision — not pre-built here.)
- **Why not a subject metadata field:** hard isolation beats filter
  discipline — a `where`-clause slip must not leak Macbeth into a French
  session; per-subject re-ingest/re-embed stays independent (the 1a
  receipt's 768→1024 migration would have been per-subject, not
  all-or-nothing); deletion per subject is collection-drop; and the shape
  composes directly with ADR-ARCH-031's per-account collections (the
  pilot's tenancy becomes account×subject collections, same seam).

### D2 — Subject-keyed wiring, discovery at boot

`build_rag_providers` discovers collections matching the scheme via
`list_collections()`, wires one provider per subject, and replays one
primary-text sidecar per subject:

- Sidecars: `.primary_text_index.<subject>`; the legacy unsuffixed
  `.primary_text_index` is read as **english's** (the baked store keeps
  working unmodified).
- `CHROMA_COLLECTION` (env) keeps its meaning as the default subject's
  collection name override — back-compat with DECISION-RAG-001 §3.1.
- Boot logs one `event=rag_subject_coverage subject=… chunks=…
  primary_texts=…` line per discovered subject — the operator-visible
  half of the coverage check.

The retrieval module's seams become subject-keyed with `english` as the
default argument everywhere (`set_collection_provider(provider,
subject=…)`, `register_primary_text(name, subject=…)`,
`has_primary_text(name, subject=…)`, `retrieve(…, subject=…)`, plus
`has_corpus(subject)`) — every existing caller and test is unchanged by
default.

### D3 — The coverage check lives in the coach-handover closure

The closure (cli/main.py) now reads `session.subject`, and **before** the
four-branch decision: a session whose subject has **no wired collection**
skips retrieval with the new structured reason
`no_corpus_for_subject` — the verifier still runs against empty chunks
(same envelope as every other skip). **Never a cross-subject fallback**:
a French session with no French corpus gets honest analysis-mode, not
English chunks. `should_retrieve`'s pure four-branch contract is
unchanged (it gains only the subject passthrough to the registry lookup).

### D4 — Two Lane 1 seam fixes pulled forward (load-bearing here)

Subject-keyed retrieval is incoherent while front doors disagree on what
`subject` contains, so two fixes land in this lane, explicitly annexed
from Lane 1 step 2:

1. **The MCP quirk:** the adapter wrote `subject=student_id`
   (`'lilymay'`) — under D3 that would silently kill retrieval for MCP
   sessions (unknown subject → skip). It now sends the shared default
   `english`. Consequence, accepted: MCP sessions key on
   `(student, 'english')` — the SAME resume key as the app and robot,
   which **closes the parallel-session divergence between front doors**
   (a named plan contradiction). Any in-flight MCP session at deploy
   time strands (none exist; MCP is the demoted legacy door).
2. **Server normalisation:** `start_session` with an omitted/empty
   subject persisted `''`; the service now normalises to the shared
   default at the boundary, so `(student, subject)` keying and D3's
   check always see a real subject. The backend constant
   `SUBJECT_DEFAULT = "english"` lives in `session/service.py`; the
   knowledge layer keeps its own equal default (layering: knowledge
   must not import session), and the SUBJECT_DEFAULT seam test pins
   all of them to the contract doc's one value.

Still Lane 1's (NOT built here): the app subject picker, student-model
subject filtering, the subject dimension on `topic_confidence`/chests.

### D5 — Per-subject ingest roots

`scripts/ingest_corpus.py` gains `--subject <slug>`: derives the sources
root (`domains/gcse-<subject>/sources/`), the collection
(`gcse-<subject>-v1`), and the sidecar name
(`.primary_text_index.<subject>`; english keeps the legacy name).
Explicit `--corpus-root`/`--collection` still override. The AQA refusal
gate is structural (loader-level) and therefore inherited by every
subject's ingest unchanged — the honesty constraint the plan names.

## Consequences

- Scanning a new subject's guides becomes: docling → md into
  `domains/gcse-<subject>/sources/…` → `ingest_corpus.py --subject <slug>`
  → rebuild/redeploy. No code change per subject.
- Until a subject's corpus lands, its sessions run honest analysis-mode
  (`no_corpus_for_subject` in the logs — greppable, and the boot coverage
  lines show what IS wired).
- English behaviour is bit-identical (default arguments + grandfathered
  collection + legacy sidecar fallback) — verified by the unchanged
  hermetic suite plus the live smoke re-run at deploy.
- The selective-retrieval posture (ADR-FLEET-002) and the four-branch
  decision tree are untouched; citation anchors remain deferred (Lane 2
  step 3 owns fix-or-defer, per the 1a receipt).
