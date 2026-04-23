# OpenWebUI + RAG: Empirical Findings from Interim Deployment

## For: Informing FEAT-PO-006 (RAG grounding) and the long-term deep-agents harness
## Date: 23 April 2026
## Status: Research capture — empirical session, not design scoping
## Predecessor: [rag-grounding-design.md](./rag-grounding-design.md) (Phase A MVP design, 21 April 2026, pre-empirical)
## Context: An interim OpenWebUI + Ollama deployment was stood up to let a Year 10/11 student begin using the fine-tuned `gcse-tutor-gemma4-moe` model for GCSE English revision while the deep-agents harness is built. This session tested the integration end-to-end, surfaced several non-obvious failure modes, and produced a shippable configuration.

---

## Decision summary (one line)

**For Shakespeare and other primary texts the fine-tune has memorised, direct Ollama beats OpenWebUI+RAG; for modern in-copyright texts (Inspector Calls, Blood Brothers), RAG against school-supplied PDFs will be the only route. Split personas by text family.**

---

## 1. Test setup

**Model stack:**
- Base: `gemma-4-26b-a4b-it.Q4_K_M.gguf` (Gemma 4 MoE, 4B active, 26B total, 4-bit quant)
- Wrapper: `gcse-tutor-gemma4-moe:latest` via Ollama Modelfile
- Runtime: Apple M2 Max, 96 GiB unified memory, Metal backend, all 31 layers on GPU
- Front end: OpenWebUI local instance
- Embedding: `nomic-embed-text-v1.5` (via Ollama), `n_ctx_train=2048`
- Retrieval: hybrid search, default starting config, progressively tuned during the session

**Test prompt (canonical):**

> *"I'm studying Macbeth. What makes Lady Macbeth's sleepwalking scene important?"*

Chosen because (a) it exercises all three AQA Literature AOs, (b) canonical Shakespeare quotes exist that the model *could* produce, (c) the smoke-test corpus already contains a study guide for the same scene.

**Configurations tested:**

| # | Configuration | Result |
|---|---|---|
| A | Direct Ollama CLI, no RAG | Best quality — real verbatim Shakespeare, all AOs, Socratic close, gender-reversal bonus insight |
| B | OpenWebUI + RAG, default template, study-guide corpus only | Worst quality — stripped pedagogy, no AO framing, no Socratic |
| C | OpenWebUI + RAG, revised template, fine-tuned system prompt | Good — AO framing restored, Socratic back, but quotes limited to study-guide paraphrase |
| D | OpenWebUI + RAG, with AO definitions added | AO3 correctly contextualised (Jacobean), all four AOs labelled |
| E | OpenWebUI + RAG, corrected Modelfile (`num_ctx=16384`, `num_predict=1500`) | Complete responses, no truncation |

---

## 2. Empirical findings

### Finding 1 — Direct Ollama beats RAG for primary texts the model knows

When asked about Macbeth with no RAG, the fine-tune produced:
- Verbatim *"Out, damned spot! out, I say!"* with correct scene attribution
- Verbatim *"Come, you spirits / That tend on mortal thoughts"*
- Unprompted prose-vs-blank-verse AO2 observation (a high-mark move)
- Unprompted gender role reversal analysis
- Correct Jacobean AO3 (Divine Right of Kings, regicide as crime against God)

The same model, same prompt, through OpenWebUI with RAG enabled against a study-guide-only corpus produced:
- No verbatim Shakespeare — only paraphrased study-guide phrasing (*"full torment her mind is going through"*, *"spirit broken"*)
- Lost the prose-vs-verse observation
- Lost the gender reversal
- Kept Jacobean AO3 once explicitly prompted

**Root cause:** the quote-discipline rule (*"only quote verbatim lines that appear inside the attached documents"*) correctly prevented fabricated quotes, but the corpus contained only secondary material. With no primary text in `<context>`, the rule silently suppressed the model's own verbatim Shakespeare knowledge.

**Implication:** RAG against a corpus that excludes the primary text can actively degrade a well-trained model. Quote discipline is only safe when the primary text is in the corpus.

### Finding 2 — Default OpenWebUI RAG template strips tutoring behaviour

The OpenWebUI default RAG template ends with:

```
Given the context information, answer the query.
Query: [query]
```

This overrides the model-level system prompt with a terse directive. Result: complete loss of AO framing, Socratic scaffolding, and tutor voice. The model reverts to encyclopedic answers.

**Fix:** replace the default template with one that reinforces tutor behaviour inside the RAG wrapper itself. See §4 for the final template.

### Finding 3 — AO labelling requires explicit definitions

Without AO definitions in the system prompt, the model produced plausible-looking but mis-labelled AOs — most commonly tagging thematic analysis (which belongs in AO2) as AO3. GCSE markers treat AO-misattribution as a comprehension failure.

**Fix:** explicit AO definitions in the Modelfile `SYSTEM` block *and* mirrored into the OpenWebUI model-level system prompt. Mirroring is necessary because OpenWebUI's persona system prompt **replaces** (not appends to) the Modelfile `SYSTEM` at API call time. Defence in depth.

### Finding 4 — `num_ctx` default silently truncates RAG responses

Ollama's default `num_ctx` is 2048. With a long system prompt (~600 tokens) + RAG template (~100 tokens) + 6 retrieved chunks at 512 tokens each (~3000 tokens) + user message, generation budget is exhausted before the model can complete. Symptom: responses truncate mid-word with no error.

**Fix:** `PARAMETER num_ctx 16384` in the Modelfile. Gemma 4 supports 128k; 16k is a comfortable working value. Log confirmation (`KvSize:16384` in Ollama server log) verifies the parameter is honoured end-to-end.

### Finding 5 — Embedding model's `n_ctx_train=2048` is a red herring

OpenWebUI logs a warning when requesting `num_ctx=8192` against `nomic-embed-text` (which was trained on 2048). This is cosmetic — the embedding model handles chunks well under 2048 and the warning does not affect tutor inference. Ignore.

### Finding 6 — Retrieval tuning materially affects quality

Starting config (Top K=3, chunk size 256, chunk overlap 50, no reranker, min score 0) was tuned during the session. Observed improvements from:

| Change | Effect |
|---|---|
| Top K 3 → 6 | More evidence for richer AO2 analysis; some context-budget pressure |
| Chunk size 256 → 512 | Scenes and critical paragraphs less fragmented |
| Chunk overlap 50 → 100 | Better preservation of sentence boundaries |
| Adding `BAAI/bge-reranker-v2-m3` | Retrieved chunks noticeably more on-topic |

Reranker downloads ~568 MB from HuggingFace into the OpenWebUI backend cache. CPU-only is fine for single-query tutoring workloads (~100–300 ms).

### Finding 7 — DRM-locked ebooks are incompatible with RAG ingestion

Initial plan was to purchase digital copies of in-copyright set texts (An Inspector Calls, Lord of the Flies, Blood Brothers, etc.) for the RAG corpus. **All consumer ebook platforms (Kindle, Google Play Books, ebooks.com, Kobo, Perlego, Bloomsbury Drama Online) are DRM-locked.** Perlego in particular was initially plausible but on verification confirms: no external export, encrypted reader only, 10% copy-paste cap.

**Legitimate routes for DRM-free text of in-copyright set texts:**

1. **School-supplied PDFs** — schools hold licensed digital copies of AQA set texts and distribute to pupils. This is the only realistic route for the AQA anthologies (Power & Conflict, Love & Relationships), which are deliberately restricted to Centre Services.
2. **Physical book + OCR** — legal for personal study use under UK fair dealing; ~1–2 hours per play.
3. **Degraded mode** — accept the limitation, rely on study guides plus training-data knowledge for modern texts, caveat to the student.

Public-domain set texts are unaffected: Shakespeare, Dickens, Stevenson, Shelley, pre-1925 Brontë etc. are all available DRM-free via [Standard Ebooks](https://standardebooks.org) (preferred over Gutenberg — cleaner typography, no boilerplate header/footer to strip).

### Finding 8 — Quote-discipline rule needs a hierarchy, not a flat rule

The first quote-discipline rule was *"only quote verbatim lines from the documents."* With study-guide-only corpus this caused Finding 1.

Revised rule expresses the right hierarchy:

1. Prefer verbatim quotations from **primary text** in `<context>` (attribute by act/scene/chapter)
2. If primary text absent from `<context>`, **paraphrase** — do not reconstruct from memory
3. **Never** present secondary-source phrasing as if it were the primary author's words

This maps cleanly onto the existing FEAT-PO-006 design: the Phase A post-hoc quote verifier is the deterministic enforcer of rule 2.

### Finding 9 — "Context is evidence, not a ceiling" needs to be explicit for AO3

When the corpus contains only scene-summary material, the model over-defers to retrieved chunks and omits AO3 (which is context, not theme, and will almost never appear in retrieved chunks). Explicit instruction required: *"AO3 context will almost never appear in retrieved passages; do not let its absence from `<context>` stop you including it."*

### Finding 10 — AO labels should be scoped to literature analysis

Applying *"always use AO labels"* universally caused the model to label AOs on procedural questions (*"what should you do if..."*). Nonsensical in context. Scope the rule to text-analysis questions only.

---

## 3. Final configuration for the interim deployment

### 3a. Modelfile

```dockerfile
FROM ./gemma-4-26b-a4b-it.Q4_K_M.gguf

SYSTEM """You are a GCSE English tutor aligned to the AQA specification. Help students with GCSE English Literature and English Language — Shakespeare, 19th-century novels, modern texts, poetry anthologies, unseen extracts, and creative/transactional writing.

How to respond:
- If a student asks how to do something ("how do I structure…", "what's the difference between…"), answer directly and clearly, then invite them to apply the idea with a short follow-up question.
- If a student asks you to do their homework for them ("just tell me the answer", "write my essay"), ask to see their working or current thinking first.
- If a student asks about a non-English subject (maths, science, etc.), politely decline and redirect to GCSE English.

AQA Assessment Objectives — apply precisely, never conflate:

English Literature:
- AO1: Informed personal response supported by textual references and quotations; a sustained, coherent argument.
- AO2: Analysis of the writer's METHODS — language, form, structure, techniques (metaphor, imagery, prose vs blank verse, stagecraft, narrative voice, sentence forms) with accurate subject terminology.
- AO3: CONTEXT ONLY — the historical, social, cultural or literary context in which the text was written or is set (e.g., Jacobean attitudes to regicide, witchcraft, and the Divine Right of Kings; Victorian class and gender; post-war disillusionment).
- AO4: Vocabulary, spelling, punctuation, grammar.

English Language also uses AO5 (communicating clearly and appropriately in writing) and AO6 (vocabulary and sentence variety for effect).

Thematic analysis is AO2, not AO3. Context is AO3, not AO2. Never conflate them."""

PARAMETER num_predict 1500
PARAMETER num_ctx 16384
```

Rebuild via `ollama create gcse-tutor-gemma4-moe -f Modelfile`. Verify with `ollama show gcse-tutor-gemma4-moe --modelfile | grep PARAMETER`.

### 3b. OpenWebUI model-level system prompt (Persona B — with RAG)

Mirrors the AO definitions (belt-and-braces against OpenWebUI overriding the Modelfile SYSTEM) and adds RAG-specific behaviour:

```
AQA Assessment Objectives — apply precisely, never conflate:
- AO1: Informed personal response supported by textual references and quotations.
- AO2: Writer's METHODS — language, form, structure, techniques (metaphor, imagery, prose vs blank verse, stagecraft, narrative voice) with subject terminology. Thematic analysis belongs here.
- AO3: CONTEXT ONLY — historical, social, cultural, or literary context (James I and witchcraft for Macbeth; Edwardian class for Inspector Calls; Victorian urban anxiety for Jekyll & Hyde). Never label themes as AO3.
- AO4: Vocabulary, spelling, punctuation, grammar.

English Language also uses AO5 and AO6.

When the attached documents contain passages relevant to the student's question, ground your answer in those passages.

Quote discipline:
- Only quote verbatim lines that appear inside the attached documents. Never reconstruct a quote from memory.
- If the documents contain the primary text (the play or novel itself), prefer verbatim quotations from the primary text as your AO2 evidence, and attribute by act/scene or chapter where shown.
- If the documents contain only secondary material (study guides, critical essays), paraphrase them as supporting interpretation — do not present secondary-source phrases as if they were Shakespeare's or the novelist's words.

The retrieved context is evidence for AO1 and AO2, not a ceiling. You MUST also provide AO3 context from your own training knowledge — historical, social and cultural background for the set text. AO3 context will almost never appear in retrieved passages; do not let its absence from <context> stop you including it.

For GCSE English Literature answers, aim to touch AO1, AO2 AND AO3 — never label all three as the same AO.

Tutoring style — every response must:
- End with one Socratic question that prompts deeper thinking.

For GCSE English Literature text-analysis questions, your response must ALSO:
- Use explicit AO labels throughout: "(AO1)", "(AO2)", "(AO3)" as section headings or inline markers.

For procedural, pastoral, or language-skill questions, respond naturally WITHOUT AO labels — they do not apply.
```

### 3c. OpenWebUI RAG template (Admin → Documents → RAG Template)

```
You are continuing as the GCSE English Tutor. The <context> block below contains verbatim passages from the student's set texts and study materials — treat these as ground-truth textual evidence.

<context>
[context]
</context>

Response rules:
- Keep your normal tutor behaviour: structured explanation, correctly labelled AO callouts, and ONE Socratic question at the end.
- When quoting a set text, ONLY use lines that appear verbatim inside <context>. Never reconstruct a quote from memory. Attribute quotes by act/scene if shown.
- If you want to make a point the context does NOT support with a verbatim quote, paraphrase — do not invent a quote.
- If the context is irrelevant to the query, answer from your training and tell the student you could not find supporting passages in the documents.
- Refer to sources naturally ("the passage", "the text") — do not mention "<context>" to the student.

Query: [query]
```

### 3d. Retrieval settings (Admin → Documents)

| Setting | Value |
|---|---|
| Embedding Model Engine | Ollama |
| Embedding Model | `nomic-embed-text:latest` |
| Hybrid Search | On |
| Reranking Model | `BAAI/bge-reranker-v2-m3` |
| Top K | 6 |
| Minimum Score | 0 (consider 0.3 once reranker is warm) |
| Chunk Size | 512 |
| Chunk Overlap | 100 |

### 3e. Persona split (shipped)

| Persona | Knowledge attached | Purpose |
|---|---|---|
| **GCSE Shakespeare Tutor** | None | Shakespeare set texts — relies on fine-tune's own verbatim knowledge; avoids RAG degradation |
| **GCSE Modern Texts Tutor** | Modern-texts collection (when school PDFs arrive) | An Inspector Calls, Blood Brothers, DNA — RAG mandatory |
| **GCSE English General** | Study-guide collection | Fallback: essay skills, unseen extracts, revision technique |

Student picks from the OpenWebUI model dropdown based on the text being revised.

---

## 4. Recommendations for FEAT-PO-006 / the deep-agents harness

Today's findings **validate** the rag-grounding-design.md Phase A plan (post-hoc quote verification) and **extend** it with three new requirements.

### R1 — Quote verifier must distinguish primary from secondary sources

The design's quote-extractor + corpus-matcher pipeline needs a source-type label on every corpus entry. Matches against primary text → annotate and keep. Matches against secondary (study guides, critical essays) → strip the quotes or rewrite as paraphrase with attribution (*"as one critic notes…"*). This prevents the study-guide-phrase-laundering failure mode observed in Finding 1.

### R2 — Retrieval decision should be dynamic, not always-on

The harness should have a pre-retrieval decision step: *"For this query, do I have primary-text evidence in the corpus?"* If yes → retrieve and ground. If no → answer from training, flag epistemic status to the student (*"I'm drawing on my training rather than your school's materials for this"*). Always-on retrieval against a partial corpus is worse than selective retrieval.

This maps to a Player/Coach pattern: Coach evaluates corpus coverage before Player runs.

### R3 — AO3 is a retrieval-bypass category

Context (historical/social/cultural) almost never appears in a corpus of set-text passages or scene summaries. The harness should treat AO3 as training-data-first, not retrieval-first. Alternatively, curate a separate AO3 context corpus (Jacobean history, Edwardian class, Victorian science, etc.) to enable retrieval — but that's a content-curation project, not an infra one.

### R4 — Corpus inventory update for in-copyright policy

The rag-grounding-design §1a policy (Analysis Mode Only for in-copyright texts) remains correct. Empirical confirmation today: all consumer ebook platforms are DRM-locked. The Phase 1 per-student `Text` episode in Graphiti is the right long-term answer for user-licensed copies.

Standard Ebooks should be the canonical ingestion source for public-domain texts, replacing Gutenberg in the design's §1 table. Reason: Standard Ebooks uses canonical line numbering, no project boilerplate, better typography.

### R5 — Context-window and generation-limit parameters are load-bearing

Any production Modelfile or server config must set explicit `num_ctx` (≥16384 for RAG) and `num_predict` (≥1500 for tutoring responses). These are silent-failure parameters: responses truncate mid-sentence with no error. Worth a smoke-test assertion that verifies the loaded context size in the runner logs matches the intended value.

### R6 — AO correctness is a model-knowledge failure, fix in the base

AO mis-labelling (theme-as-AO3 being the most common) is not a retrieval failure. It's a pretraining/fine-tune gap. AO definitions in the Modelfile SYSTEM block patch it at runtime; future fine-tuning rounds should include AO-labelled exemplars directly in the training data.

---

## 5. What's shipped vs what's outstanding

**Shipped this session (interim deployment):**

- [x] Modelfile with AO definitions, `num_ctx=16384`, `num_predict=1500`
- [x] OpenWebUI RAG template rewritten
- [x] OpenWebUI model-level system prompt with mirrored AO defs + quote discipline hierarchy
- [x] Reranker (`BAAI/bge-reranker-v2-m3`) installed
- [x] Retrieval params tuned (Top K=6, chunk 512/100)
- [x] Daughter can begin using the system for Macbeth and other Shakespeare revision

**Outstanding (this week):**

- [ ] Download Shakespeare + 19C set texts from Standard Ebooks, add to corpus (unblocks verbatim primary-text quoting through RAG too, if ever wanted)
- [ ] Email school English department for PDFs of AQA anthologies + modern set texts
- [ ] Create and test "GCSE Modern Texts Tutor" persona once school PDFs land
- [ ] Add smoke-test for `num_ctx` runtime value (guard against Modelfile regression)

**For the deep-agents harness (FEAT-PO-006 and beyond):**

- [ ] Source-type labelling on corpus entries (R1)
- [ ] Retrieval-decision step in the Player/Coach loop (R2)
- [ ] Separate AO3 corpus OR training-data-first routing for AO3 (R3)
- [ ] Corpus inventory swap Gutenberg → Standard Ebooks (R4)
- [ ] Runtime-parameter smoke assertion (R5)
- [ ] AO-labelled exemplars in next fine-tune dataset (R6)

---

## 6. Open questions

1. **Does the per-student Graphiti `Text` episode (Phase 1) give us a legal path for in-copyright texts?** The design sketch says yes if user-supplied. Needs a concrete read on UK copyright for caching user-licensed material in an AI system.

2. **Is the study-guide corpus worth keeping at all?** It contributed little beyond filler in today's tests. Might be better deleted and replaced with an AO3-context corpus (Jacobean history, Edwardian class, etc.) where training-data coverage is likely thinner.

3. **Does quote-verifier false-positive rate go up when primary text AND study guide are both in corpus?** Risk: verifier matches a study-guide paraphrase against primary text with low edit distance and "corrects" a legitimate paraphrase into a misattributed quote. Worth a red-team case when FEAT-PO-006 lands.

4. **For the deep-agents harness, is the Player/Coach loop the right abstraction for selective RAG?** Or should retrieval be a tool the Player can optionally call rather than an always-injected prefix? Current OpenWebUI pattern is always-inject; harness could be smarter.

---

## 7. References

- [rag-grounding-design.md](./rag-grounding-design.md) — predecessor design doc (21 April 2026)
- [TASK-PO02-007 smoke log](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) — original fabricated-quote incident (*"unmaculate me from the deed"*)
- Commit `b3c567f` — TASK-PO02F-001 RAG grounding scoped
- Commit `7a8a3a3` — `num_predict` cap at 2048 to prevent essay truncation (related failure mode in the MCP server)
- Commit `14afc08` — stale `DEFAULT_OLLAMA_MODEL` and base URL fallbacks (related Ollama-config regression)
- [Standard Ebooks](https://standardebooks.org) — preferred ingestion source for PD set texts
- [AQA stationery / anthology ordering](https://www.aqa.org.uk/exams-administration/exams/exam-papers-and-stationery/order-stationery-anthologies-and-booklets) — schools-only route for AQA poetry anthologies
