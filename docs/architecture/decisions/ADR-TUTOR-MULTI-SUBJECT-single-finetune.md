# ADR: Single Fine-Tune, Multi-Subject Architecture

**Date:** 2026-05-05
**Status:** Accepted
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

**Serving:** llama-swap on GB10 (:9000), single model alias `gemma4-tutor`.

**Access:** Open WebUI subject presets (dropdown selector) — each preset maps to the same model with a different system prompt.

**RAG:** One ChromaDB collection per subject, seeded via Docling from CGP guides and AQA materials. 768-dim embeddings (nomic-embed-text-v1.5).

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
