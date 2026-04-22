# RAG Grounding for Quote Fidelity — Design Sketch

## For: `/feature-plan` FEAT-PO-006 (tentative)
## Date: 21 April 2026
## Status: Scoping output of TASK-PO02F-001 — design only, no code
## Predecessor: [TASK-PO02-007 smoke log](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) (Macbeth session fabricated `"unmaculate me from the deed"` vs canonical `"unsex me here"`)
## Context: The single highest-visibility failure mode for a GCSE literature tutor is fabricated primary-text quotations. Students quoting invented lines in an exam is a trust-breaking event. Prompt-patching the fine-tuned Gemma 4 will not fix this reliably; a retrieval/verification layer will. This doc commits the approach before we spend engineering time.

---

## Decision summary (one line)

**Post-hoc quote verification as MVP, embedded-context retrieval as Phase B.** A deterministic verifier that cannot be fabricated past is the only safety guarantee strong enough to put in front of an exam-preparing student; embeddings help the model cite *before* it has to hallucinate.

---

## 1. Corpus inventory

**Scope for MVP.** AQA English Literature spec 8702. Prioritise the two texts the live smoke already exercises (Macbeth, An Inspector Calls), then extend.

| Text | Author | Copyright | Source of record | Canonical addressing |
|---|---|---|---|---|
| Macbeth | Shakespeare | PD | [Folger Shakespeare Library](https://folger.edu/explore/shakespeares-works/macbeth/) TEI XML | Act.Scene.Line (Folger line numbering) |
| Romeo and Juliet | Shakespeare | PD | Folger TEI | Act.Scene.Line |
| A Christmas Carol | Dickens | PD | [Project Gutenberg #46](https://www.gutenberg.org/ebooks/46) | Stave / paragraph |
| Dr Jekyll & Mr Hyde | Stevenson | PD | Project Gutenberg #43 | Chapter / paragraph |
| Frankenstein (1818 or 1831) | Shelley | PD | Project Gutenberg (pick 1831 — more commonly set) | Volume / chapter / paragraph |
| AQA Power & Conflict poetry | Various | **Mixed** | Per-poem; Shelley/Blake/Wordsworth PD, Dharker/Duffy/Armitage in-copyright | Poem / line |
| **An Inspector Calls** | Priestley (d. 1984) | **In copyright until 2055** | Cannot ship. See §1a. | — |
| **Blood Brothers / DNA / History Boys** | Russell / Kelly / Bennett | **In copyright** | Cannot ship. | — |

### 1a. In-copyright texts — policy

Priestley died in 1984 → UK copyright expires 2055. Shipping the full text of *An Inspector Calls* is not an option. Three feasible postures:

1. **Analysis mode only** for in-copyright texts. Tutor may discuss themes, stagecraft, Priestley's socialist critique — but will **not produce verbatim stage directions or dialogue**. Quote verifier treats any quoted string for an in-copyright text as unverifiable → strip and substitute with a description ("the stage direction describes the lighting hardening when the Inspector enters").
2. **User-supplied text**, cached per-student. The Phase 1 Graphiti student model can hold a per-student `Text` episode containing a user-licensed copy. Not Phase 0 scope.
3. **License acquisition.** Out of scope for the hackathon build; note as a commercial path.

MVP = posture (1). Explicit in the role prompt: "For in-copyright texts, paraphrase; do not quote." The verifier enforces.

### 1b. Edition choice — why Folger over Gutenberg for Shakespeare

Gutenberg carries a serviceable Macbeth but line-numbering is inconsistent across editions. Folger publishes TEI XML with canonical modern line-numbering used by most GCSE teachers (AQA's own exemplars reference Folger-style numbering). Extra parsing work (~1 day) in exchange for citations the English teacher will not flag as "from the wrong edition".

---

## 2. Retrieval shape — chosen approach

### MVP (Phase A): Post-hoc quote verification

```
Player LLM → response text → quote-extractor → corpus-matcher → decision:
  ├─ exact match            → annotate with citation "(Macbeth 1.5.41)", return
  ├─ near-miss (≤3 edit dist) → substitute with exact string, annotate "(corrected)", log
  ├─ no match                → strip quote, replace with "[paraphrased]", log
  └─ in-copyright text       → strip quote, paraphrase, log
```

**Why this is the right MVP.**

- **Deterministic safety.** A fabricated quote cannot reach the student. The verifier is not a probabilistic suggestion to the LLM; it is a gate on the response bytes.
- **Small surface.** Regex / TEI-aware quote extractor + `rapidfuzz` against a flat-text corpus index. No new serving infra. Runs inline in the MCP handler or (preferably) in the Coach pass — already a quality-gate locus per FEAT-PH1-003.
- **Composes with fine-tuning.** Does not fight the base model's prompt; orthogonal safety net.
- **Model-independent.** Works the same whether we swap Gemma 4 for a future local or Bedrock model.

**Why not tool-call grounding (option a) as MVP.** Fine-tuned small-open-weight models are patchy at disciplined tool-calling; we measured >10s just for the LLM hop, adding another RTT to every quote-bearing turn pushes us over the 15s tool-description budget. And the model still has the option *not* to call — it cannot fabricate past the verifier, it can fabricate past a tool it never invoked.

**Why not embedded-context as MVP.** Helps the model but does not guarantee fidelity — it can read the correct line and still misquote. Good Phase B add-on, weak Phase A primary.

### Phase B: Embedded-context retrieval (opt-in boost)

Once the verifier is live and instrumented, add pre-turn retrieval:

```
tutor_turn(session_id, msg)
  → detect quote-intent ("specific quotes I could use") in user msg
  → if yes: top-K passage retrieval from corpus:{text_id} → prepend as <context> block to player prompt
  → player LLM generates
  → verifier (Phase A) still runs — retrieval reduces fabrication pressure but does not replace the gate
```

This is where embeddings earn their keep: Shakespeare-speech-level chunks retrieved by semantic similarity to the student's question ("Lady Macbeth's ambition in 1.5"), concatenated into the player prompt so the model sees the authoritative text before speaking.

### Phase C (future, probably Phase 2)

Tool-call grounding (`lookup_quote(text_id, search)`) when we have a tool-capable model in the player slot. Bedrock Claude or a Gemma 4 checkpoint explicitly trained on tool-use. Not MVP.

---

## 3. Embedding / indexing sketch

### Chunk granularity

| Text type | Chunk | Metadata |
|---|---|---|
| Shakespeare | **One speech** (speaker's uninterrupted block), max ~150 lines | `{text_id, act, scene, speaker, line_start, line_end}` |
| Prose (novels) | **One paragraph**, min 3 sentences, max ~400 words; adjacent-paragraph overlap for long sections | `{text_id, chapter, paragraph_index, start_offset}` |
| Poetry | **One poem** (small enough) | `{text_id, poem_title, poet, line_count}` |

Speech-level gives the model enough context to quote within flow (cross-line quotations work) and keeps chunks small enough to be useful for retrieval. Paragraph-level on prose matches the way students actually quote novels.

### Vector store — reuse, do not proliferate

**Store**: FalkorDB on Synology, same host as the Phase 1 Graphiti student model (DEC-02).
**Embedder**: `nomic-embed-text-v1.5` on GB10 port 8001, same instance that already serves student-model embeddings.
**Group IDs**:

- `corpus:gcse-english:macbeth`
- `corpus:gcse-english:christmas-carol`
- `corpus:gcse-english:frankenstein`
- …one per text.

Keeps corpus queries cleanly separable from student-state queries while staying inside the same infra. No second vector store, no second embedder.

### Flat-text index — needed alongside embeddings

The **verifier** (Phase A) does not use embeddings — it does exact/near-exact string matching. A flat text file per text plus SQLite FTS5 is enough:

```
corpora/
  macbeth/
    full.txt                 # Folger plain text
    lines.jsonl              # {"act":1,"scene":5,"line":41,"speaker":"LADY MACBETH","text":"Come, you spirits"}
    fts5.sqlite              # FTS5 over lines.text for fast substring + fuzzy lookup
```

The embedding index is only needed for Phase B retrieval assist. The verifier MVP ships without touching FalkorDB at all — useful decoupling: Phase A can land before Phase 1's Graphiti spike resolves.

### GB10 headroom

`nomic-embed-text-v1.5` is ~137M parameters, ~500 MB VRAM at FP16. GB10 currently hosts the Gemma 4 MoE (~25B params, Q4_K_M ≈ 14 GB) plus the embedder. Indexing the whole AQA PD corpus is a one-shot job measured in minutes, not a live-latency concern. No VRAM blocker.

---

## 4. Eval harness sketch

Ship **before** the implementation. If we cannot measure fabrication rate, we cannot claim to have fixed it.

### Golden quote set

`tests/quote_fidelity/golden_quotes.yaml` — seed with known-hard cases, starting from the TASK-PO02-007 smoke:

```yaml
- id: qf-macbeth-unsex
  text_id: macbeth
  prompt: "Give me a specific quote from Act 1 Scene 5 showing Lady Macbeth rejecting femininity."
  expected_exact: "Come, you spirits / That tend on mortal thoughts, unsex me here"
  canonical_citation: "Macbeth 1.5.41-42"
  known_fabrications:
    - "That tend on mortal coats… unmaculate me from the deed"   # observed 2026-04-21

- id: qf-macbeth-raven
  text_id: macbeth
  prompt: "Quote the raven line from Act 1 Scene 5."
  expected_exact: "The raven himself is hoarse / That croaks the fatal entrance of Duncan"
  canonical_citation: "Macbeth 1.5.38-40"

- id: qf-macbeth-dagger
  text_id: macbeth
  prompt: "Give me the opening of the dagger soliloquy."
  expected_exact: "Is this a dagger which I see before me"
  canonical_citation: "Macbeth 2.1.33"

- id: qf-macbeth-innocent-flower   # control — smoke saw this rendered correctly
  text_id: macbeth
  prompt: "How does Lady Macbeth describe the deception needed to kill Duncan?"
  expected_exact: "Look like the innocent flower, / But be the serpent under 't"
  canonical_citation: "Macbeth 1.5.66-67"

# Extend with: "Out, damned spot", "Tomorrow and tomorrow and tomorrow",
# Scrooge "bah humbug", Jekyll "man is not truly one, but truly two"...
```

### Harness

- Run each prompt through `tutor_turn` with a clean session.
- Extract quoted strings from the response (TEI-style quotation marks, block-quote patterns, and the `/` linebreak convention Shakespeare responses use).
- For each extracted quote: substring + fuzzy match (`rapidfuzz.partial_ratio >= 95`) against the corpus FTS5 index.
- Metrics:
  - **Fabrication rate** = quoted strings with no ≥95 fuzzy match / total quoted strings. **This is the target metric.**
  - **Citation coverage** = quoted strings accompanied by a citation (post-verifier).
  - **False-correction rate** = verifier rewrites where the original was actually correct in a different edition (sanity check).

### Regression gate

Phase A target: fabrication rate < 5 % on the golden set (from an observed ≥20 % baseline in the smoke). Phase B target: < 1 %.

Re-run harness on every Player-model change (fine-tune iteration, model swap) and every corpus ingest.

---

## 5. Hand-off to implementation

Promote this doc to `FEAT-PO-006: RAG grounding for quote fidelity` via `/feature-plan` once accepted. Expected breakdown:

| Subtask | Gist | Rough effort |
|---|---|---|
| FEAT-PO-006-T1 | Corpus ingest — Folger Macbeth + Gutenberg Christmas Carol → `corpora/` + FTS5 | 0.5 day |
| FEAT-PO-006-T2 | Quote extractor + verifier module (`src/study_tutor/grounding/verifier.py`) — pure, no I/O past FTS5 | 1 day |
| FEAT-PO-006-T3 | Eval harness + golden quote YAML → CI gate | 0.5 day |
| FEAT-PO-006-T4 | Wire verifier into `tutor_turn` response path (Coach pass or inline) | 0.5 day |
| FEAT-PO-006-T5 | In-copyright paraphrase-mode policy + test case | 0.5 day |
| FEAT-PO-006-T6 (Phase B) | Embedded-context retrieval assist | 1–2 days |

Sequencing constraint: **ship FEAT-PO-006 before multi-subject expansion (Maths, Biology).** Every subject added without grounding multiplies the hallucination surface. Solving for English once, then generalising the verifier pattern, is cheaper than retrofitting.

## Reference

- Failure sample: [TASK-PO02-007 smoke log §Session 2](../../../.claude/reviews/TASK-PO02-007-smoke-log.md)
- LLM client (injection point for verifier): [src/study_tutor/llm/client.py](../../../src/study_tutor/llm/client.py)
- Tutor role manifest (where retrieved context would be injected): [roles/tutor/role.yaml](../../../roles/tutor/role.yaml), [roles/tutor/prompts/player.md](../../../roles/tutor/prompts/player.md)
- Phase 1 context (RAG is "Layer 2"): [phase-1-scope.md](phase-1-scope.md)
- Infra decisions this reuses: [decisions-log-2026-04-17.md DEC-02](decisions-log-2026-04-17.md)
