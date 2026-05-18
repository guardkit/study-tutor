# Study Tutor — Technical Write-Up

**Submission:** Gemma 4 Good Hackathon (Kaggle × Google DeepMind)
**Deadline:** 18 May 2026, 23:59 UTC
**Status:** 🔲 Stub — populated incrementally through Phases 0–2. Target feature-complete: 10 May 2026. Final polish: 17–18 May.

> This is a living document. Each section is a titled stub with a one-line note. Content is added as each phase lands so the final write-up is a synthesis, not a sprint.

---

## 1. Problem Statement

> *Lilymay, AI tutors, teenage engagement, privacy — why a 15-year-old won't open a revision tool on a Tuesday evening, and why a cloud-hosted AI tutor isn't an acceptable answer.*

## 2. Solution Overview

> *Three-layer architecture at a glance: fine-tuned Gemma 4 26B-A4B (MoE) on-device (behaviour), RAG over licensed sources (knowledge), gamification layer (engagement).*

## 3. Pipeline Methodology

> *How the training data was produced — agentic dataset factory, Player–Coach adversarial generation, Unsloth fine-tuning harness. Why this yields better training data than hand-curation.*

## 4. Fine-Tuning Specifics

> *Base model `unsloth/gemma-4-26B-A4B-it` — Gemma 4 26B-A4B (MoE, 27B params). LoRA rank 16, Unsloth + TRL SFT, 1 epoch, effective batch 4, max-seq 2048, bf16, single GB10. ShareGPT format, 75/25 `<think>` ratio. Published: HF `RichWoollcott/studytutor-gcse-26b-moe` (merged 16-bit) + `RichWoollcott/gcse-tutor-gemma4-26b-moe-GGUF` (Q4_K_M). Confirm example count and final loss from train.log. Training data provenance and filtering.*

## 5. Architecture

> *Phase 1 Ollama-on-GB10 runtime + Phase 2 Graphiti student model + DeepAgents Player–Coach loop + gamification state engine. Where each layer lives and how they compose.*

## 6. Gamification Design

> *Single-user engagement mechanics — personal growth over competition. XP economy, level progression, achievements, streaks, daily challenges, Boss Battle exam mode. See `docs/gamification/design.md` for the full spec.*

## 7. On-Device Deployment

> *GB10 under the desk → Ollama → GGUF Q4_K_M. Zero cloud calls in the default path. Privacy story: no student data leaves the home network.*

## 8. Bedrock Migration Path

> *AWS Bedrock Custom Model Import as the scale-to-zero fallback for demo week and multi-user scenarios. Cost profile (~$1.50–$3.00 per 5-min session), cold-start behaviour, when to route traffic where.*

## 9. Multi-Subject Expansion

> *Domain-agnostic pipeline — adding a subject is a `domains/{subject}/GOAL.md` plus a `sources/` directory, not a code change. Architecture demonstration, not Phase 0 implementation.*

## 10. Copyright and Provenance

> *Bring-your-own-sources public repo pattern. What the repo ships vs. what users acquire themselves. Training-data provenance chain. See `copyright-training-data-analysis.md`.*

## 11. Evaluation

We evaluated the fine-tuned tutor honestly — including against the model it
was built from. The full method and evidence are in
[`docs/runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md`](../runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md)
and [`RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md`](../runbooks/RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md);
this section reports it straight, including where the fine-tune falls short.

### 11.1 Method

A fixed 16-prompt golden set of GCSE-English tutoring situations (8 behaviour
categories, each with pre-declared `expected_behaviours` and `red_flags`) plus
3 scripted multi-turn sessions. The fine-tuned tutor (`gemma4-tutor`) was
compared head-to-head against its **own base model**, `unsloth/gemma-4-26B-A4B-it`,
under strict parity: identical system prompt, identical greedy decoding, the
same `llama-server` runtime and chat template — the only variable is the
fine-tuned weights. Three instruments were used: blind pairwise judging
(single- and multi-turn), and a length-neutral criterion-referenced re-score.

### 11.2 What the fine-tune does well

- **Socratic stance is confirmed, not assumed.** On the length-neutral
  criterion score the fine-tune equals or beats the base on every pure-Socratic
  item (quotation analysis, paragraph feedback). Multi-turn, it out-scores the
  base on Socratic stance (5.0 vs 4.0). It reliably guides rather than
  hands over answers.
- **It surfaces its pedagogical reasoning.** The fine-tune emits a structured
  `<think>` block (AO mapping, grade-appropriate strategy) on ~63% of prompts;
  the base never does. In Open WebUI this renders as a collapsible panel.
- **Zero template-token leaks**, and it runs **fully on-device**.

### 11.3 Where it falls short (honest findings)

Against a strong instruction-tuned base given the *same* tutoring system
prompt, the current fine-tune checkpoint does **not** score higher overall —
criterion-referenced, the base met 88.5% of expected behaviours vs the
fine-tune's 62.5%. The gap is **not** a verbosity artefact (the length-neutral
instrument confirms it); it concentrates in three specific, fixable areas:

1. **Factual reliability** — isolated slips on set-text metadata (the
   1945 writing date of *An Inspector Calls*; a poem title; a character name).
2. **Deflection** — when a student asks a direct question ("what does AO2
   *mean*?"), it sometimes returns questions instead of first explaining.
3. **Role discipline / closure** — one out-of-role drift; some answers end
   without a concrete next step.

These are logged in [`known-issues.md`](../runbooks/known-issues.md) as inputs
to a future re-train.

### 11.4 Limitations

The judge was a single model-driven evaluator over a 16+3 item set — a
*directional* result, not a statistically powered one. Blind pairwise judging
also has a documented bias toward longer answers; the criterion-referenced
re-score was added specifically to control for it. Most importantly, **no
synthetic eval here measures sustained engagement** — whether a real teenager
keeps opening the tutor week after week. That is the metric this project most
cares about, and the evidence for it is the real revision sessions run with a
Year-10 student through Open WebUI and the Reachy Mini companion (§5, §12) —
not a benchmark score. We deliberately did not run leaderboard-style
benchmarks: they are the wrong frame for a single-student tutor.

### 11.5 Honest conclusion

Fine-tuning gave us a tutor with a reliable Socratic style and visible
pedagogical reasoning, running entirely on-device. It has not yet been shown
to out-perform a well-prompted base model on a quality rubric, and it carries
specific accuracy weaknesses we are transparent about. The contribution we
stand behind is the **reproducible pipeline and the honest evaluation harness**
itself — both shipped in this repo — as much as any single checkpoint.

## 12. Roadmap

> *Reachy Mini embodied interface, mobile surface, multi-subject expansion, Graphiti-backed long-term student model, Boss Battle exam mode.*

## 13. Acknowledgements

> *Pollen Robotics (Reachy), Unsloth (fine-tuning framework), Ollama (runtime), Anthropic (Claude — build harness), Google DeepMind (Gemma 4 base model), and the GCSE English teachers whose open pedagogy informed the Assessment Objective framing.*
