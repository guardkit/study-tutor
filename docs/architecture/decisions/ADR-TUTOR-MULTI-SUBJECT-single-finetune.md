# ADR: Single Fine-Tune, Multi-Subject Architecture

**Date:** 2026-05-05
**Status:** Accepted — **amended 2026-08-01**: the RAG-source references to mark schemes /
past papers / examiner reports below are struck; AQA assessment material is excluded
absolutely per mission law 4. See [Amendment 2026-08-01](#amendment-2026-08-01--aqa-assessment-material-excluded-from-all-rag-sources-mission-law-4)
at the end of this document. The core decision (one fine-tune + per-subject prompts +
per-subject corpora) is unchanged.
**Decision maker:** Rich
**Context:** Multi-subject expansion of the GCSE study tutor

---

## Decision

One fine-tuned model (`gemma4-tutor` — Gemma 4 26B A4B MoE fine-tuned on English tutoring data) serves all GCSE subjects. Subject differentiation is achieved through per-subject system prompts and per-subject ChromaDB RAG collections. No per-subject or per-cluster fine-tuning is required.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  gemma4-tutor                    │
│          (one fine-tune, all subjects)           │
│     Behaviour: Socratic questioning, scaffolding,│
│     resisting "just tell me", patience           │
└────────────┬──────────────────┬──────────────────┘
             │                  │
    System Prompt (per-subject) │  RAG (per-subject ChromaDB)
             │                  │
  ┌──────────┴─────┐   ┌───────┴──────────────────┐
  │ AQA spec refs  │   │ CGP guides, mark schemes, │
  │ Subject context│   │ examiner reports, past     │
  │ Grade targets  │   │ papers — per subject       │
  └────────────────┘   └──────────────────────────┘
```

> ⚠ **Struck by the 2026-08-01 amendment:** the RAG box in the diagram above lists
> "mark schemes, examiner reports, past papers — per subject" as sources. That is AQA
> assessment material and is **excluded absolutely** (mission law 4); it predates the
> hardened law and must not be built from. See the amendment section at the end.

**Serving:** llama-swap on GB10 (:9000), single model alias `gemma4-tutor`.

**Access:** Open WebUI subject presets (dropdown selector) — each preset maps to the same model with a different system prompt.

**RAG:** One ChromaDB collection per subject, seeded via Docling from CGP guides and ~~AQA materials~~ *(amended 2026-08-01: AQA **specification** documents only — factual curriculum structure; AQA assessment material is refused at ingest and retrieval)*. 768-dim embeddings (nomic-embed-text-v1.5).

## Why this works

The fine-tuning taught generic tutoring behaviour — how to tutor — not subject knowledge. The system prompt activates subject context. The RAG provides curriculum content. These three layers are independently updatable:

| Layer | What it provides | How it's updated |
|---|---|---|
| Fine-tune | Tutoring behaviour (Socratic questioning, scaffolding, patience, mark scheme alignment) | Retrain with new behaviour examples |
| System prompt | Subject context (AQA spec, assessment objectives, grade descriptors) | Edit text file, restart preset |
| RAG | Curriculum knowledge (quotes, formulas, historical facts, vocabulary) | Re-ingest source documents into ChromaDB |

This is the Daniel Bourke principle in practice: **fine-tuning teaches behaviour, not facts.**

## Evidence

Validated 2026-05-05 via 17 structured test prompts across 7 subjects, all using the English-trained `gemma4-tutor` with subject-specific system prompts via Open WebUI.

**Subjects tested:** Maths, French, Spanish, History, Biology, Chemistry (plus English as the baseline).

**Pass rate:** 17/17. No failures. Two minor observations (History H3 and Spanish S2 produced slightly longer responses with mild list formatting) — both still fundamentally Socratic.

**Key evidence points:**

- **Maths (highest risk):** Model scaffolded a trapezium area problem by asking "what would happen if you flipped a trapezium and joined it?" rather than stating the formula. Guided percentage/voucher order-of-operations by asking the student to try both approaches.

- **Biology misconception handling:** Student said "plants get food from soil." Model responded with "what do you remember about what a plant actually needs to make its food?" — classic Socratic misconception correction, not a lecture.

- **Resistance to "just tell me":** Student asked "can you just tell me the order?" (mitosis stages). Model replied "before I give you the order, let me ask you something first" and scaffolded via the PMAT mnemonic hint.

- **Bilingual scaffolding (French):** For a translation request, model asked "which French verb for 'to want'? It starts with a 'v' and has six letters..." rather than providing the answer.

Full test prompts: `docs/research/ideas/multi-subject-validation-prompts.md`
Full results transcript: `docs/research/multi-subject-validation-results.md`

## Rejected alternatives

### Per-subject fine-tuning
One fine-tune per subject (8 models). Rejected because the validation proves the English fine-tune generalises. Would require 8× the training data preparation with no demonstrated benefit. llama-swap could handle the switching, but it's unnecessary complexity.

### Cluster fine-tuning
Three fine-tunes grouped by pedagogical similarity (Humanities, STEM, Languages). Considered as a middle ground. Rejected after the Maths and French tests passed — if the most pedagogically distant subjects from English (procedural maths, bilingual French) work with system prompt alone, clustering adds no value.

### Single model, no RAG
Relying on the model's training knowledge for all subjects. Rejected because curriculum-specific knowledge (exact AQA mark scheme criteria, specific CGP guide content, grade boundary descriptors) needs to be retrievable and updatable independently of the model.

## What this means for the expansion plan

1. **No new fine-tuning work.** The existing `gemma4-tutor` serves all subjects.

2. **Per-subject system prompts already exist.** Open WebUI presets for Maths, French, Spanish, History, Biology, Chemistry are live and validated.

3. **Per-subject RAG is the remaining work.** Each subject needs a ChromaDB collection seeded from CGP guides via Docling. This is the agentic-dataset-factory ingestion pipeline (`domains/{subject}/sources/` → Docling → ChromaDB).

4. **Maths may need additional behaviour examples later.** The validation passed, but Maths tutoring has the widest pedagogical gap from English. If real student sessions reveal the model struggles with specific maths interaction patterns (e.g. scaffolding algebraic manipulation step-by-step), targeted behaviour examples can be added to the fine-tuning dataset without requiring a separate model.

## Open WebUI subject presets (current state)

| Preset | System prompt | RAG collection | Status |
|---|---|---|---|
| GCSE English Tutor | `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` | Not yet | ✅ Live, validated by Lilymay |
| GCSE Maths Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |
| GCSE French Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |
| GCSE Spanish Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |
| GCSE History Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |
| GCSE Biology Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |
| GCSE Chemistry Tutor | Open WebUI preset | Not yet | ✅ Validated (this ADR) |

## Cross-references

- System prompt (English): `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt` (GB10)
- Open WebUI RUNBOOK: `docs/research/ideas/RUNBOOK-open-webui-tutor-access.md`
- Fine-tuning principle: Daniel Bourke (Queensland AI Meetup, March 2026)
- ADR-FLEET-002: Selective retrieval over always-on RAG
- Dataset factory domain config: `agentic-dataset-factory/domains/`

---

## Amendment 2026-08-01 — AQA assessment material excluded from all RAG sources (mission law 4)

*Added as part of the Lane 4 contradiction burn-down
([ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) D5). The original text
above is deliberately left legible (annotated, not rewritten) — ADR hygiene.*

This ADR predates the hardened law 4 of the ratified mission
(`docs/study-tutor-mission-statement-2026-08-01.md`, 2026-08-01): **AQA assessment
material — past papers, mark schemes, examiner reports, specimen papers — is excluded
absolutely: never trained on, never ingested, never retrieved.** AQA's policy prohibits AI
use of its material, and the guard is also pedagogical (mark schemes short-circuit
Socratic behaviour).

**What is struck in the original text:**

1. The architecture diagram's RAG box: "CGP guides, **mark schemes, examiner reports,
   past papers** — per subject" — the bolded items are struck.
2. The "RAG:" serving line's "seeded via Docling from CGP guides and AQA materials" —
   "AQA materials" is narrowed to AQA **specification** documents only (factual paper
   structure and AO definitions — the same distinction drawn in
   `docs/research/ideas/copyright-training-data-analysis.md` §6).
3. The "Single model, no RAG" rejected-alternative's rationale ("exact AQA mark scheme
   criteria… needs to be retrievable") — the *rejection* stands, but retrievable
   curriculum knowledge means study-guide and primary-text content plus specification
   facts, never mark-scheme wording.

**What per-subject collections are actually seeded from** (Rich's 2026-08-01 corpus
ruling, plan Lane 1 step 3): the family's school-bought printed study guides
(scan → docling, standard/VLM modes), public-domain primary texts (Standard Ebooks), and
AQA specification facts. Every subject has a law-4-compliant corpus path on this basis.

**Enforcement receipts:** ingest refusal `AQA_REFUSAL_PATTERN`
(`src/study_tutor/knowledge/corpus.py`) + retrieval defence-in-depth
`AQA_FILENAME_PATTERN` (`src/study_tutor/knowledge/retrieval.py`) — both inherited into
every per-subject (and, come the pilot, per-account) pipeline per ADR-ARCH-031 D3.4.

The core decision of this ADR — one fine-tune, per-subject system prompts, per-subject
corpora — is unchanged by this amendment.
