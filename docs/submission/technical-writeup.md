# Study Tutor — Technical Write-Up

**Submission:** Gemma 4 Good Hackathon (Kaggle × Google DeepMind)
**Deadline:** 18 May 2026, 23:59 UTC
**Status:** 🔲 Stub — populated incrementally through Phases 0–2. Target feature-complete: 10 May 2026. Final polish: 17–18 May.

> This is a living document. Each section is a titled stub with a one-line note. Content is added as each phase lands so the final write-up is a synthesis, not a sprint.

---

## 1. Problem Statement

> *Lilymay, AI tutors, teenage engagement, privacy — why a 15-year-old won't open a revision tool on a Tuesday evening, and why a cloud-hosted AI tutor isn't an acceptable answer.*

## 2. Solution Overview

> *Three-layer architecture at a glance: fine-tuned Gemma 4 31B on-device (behaviour), RAG over licensed sources (knowledge), gamification layer (engagement).*

## 3. Pipeline Methodology

> *How the training data was produced — agentic dataset factory, Player–Coach adversarial generation, Unsloth fine-tuning harness. Why this yields better training data than hand-curation.*

## 4. Fine-Tuning Specifics

> *Gemma 4 31B Dense base, LoRA adapter, ShareGPT format, 75/25 `<think>` ratio, ~1,736 examples, ~2h 5min on GB10, final loss 0.7015. Training data provenance and filtering.*

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

> *What we measured (quote fidelity, AO coverage, coach-criteria pass rate, session completion) and what we deliberately did not (leaderboard-style benchmarks — wrong frame for a single-student tutor).*

## 12. Roadmap

> *Reachy Mini embodied interface, mobile surface, multi-subject expansion, Graphiti-backed long-term student model, Boss Battle exam mode.*

## 13. Acknowledgements

> *Pollen Robotics (Reachy), Unsloth (fine-tuning framework), Ollama (runtime), Anthropic (Claude — build harness), Google DeepMind (Gemma 4 base model), and the GCSE English teachers whose open pedagogy informed the Assessment Objective framing.*
