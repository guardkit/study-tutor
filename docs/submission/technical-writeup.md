# StudyTutor — A Privacy-First GCSE Tutor on Local Hardware

**Submission:** The Gemma 4 Good Hackathon (Kaggle × Google DeepMind)
**Category:** Future of Education
**Author:** Rich Woollcott, Bristol, UK
**Deadline:** 18 May 2026, 23:59 UTC

---

## Summary

StudyTutor is a fine-tuned Gemma 4 26B MoE model that tutors a Year 10 student for her GCSE exams. It runs entirely on an NVIDIA DGX Spark (GB10) in the family home — no cloud, no subscription, no data leaving the house. The training data was generated autonomously by a Player-Coach adversarial pipeline, and the model is served through Open WebUI so the student accesses it like any chat interface. This isn't a prototype — it's in daily use by a real student preparing for real exams.

---

## 1. The Problem

GCSE English is high-stakes — it's a gateway qualification in the UK that affects college and career options. Private tutoring costs £25–50/hour and is inaccessible to many families. Existing AI tutoring tools are cloud-based, raising privacy concerns for minors, and use generic models that don't understand the specific exam board's assessment objectives, mark scheme language, or the particular texts a student is studying.

What's needed is a tutor that understands the AQA specification (not just "English literature"), uses Socratic questioning rather than giving answers, runs locally so a child's educational data never leaves the home, costs nothing per session after setup, and is available 24/7 during revision periods.

---

## 2. Our Solution

StudyTutor is built on a four-layer architecture where each layer is independently upgradeable.

**Layer 1 — Fine-tuned model (behaviour).** The Gemma 4 26B A4B MoE model is fine-tuned using LoRA via Unsloth to learn how a good GCSE tutor responds — Socratic questioning, scaffolded explanations, assessment-objective-aligned feedback, encouragement calibrated to student level. Critically, it refuses to simply give answers when asked. The fine-tuning teaches behaviour, not facts.

**Layer 2 — RAG knowledge store.** Curriculum content lives in a ChromaDB vector store — 581 embedded chunks across three GCSE set texts (Macbeth, An Inspector Calls, and the AQA Power & Conflict poetry anthology), plus Mr Bruff study guides, AQA mark schemes, and examiner reports. A per-turn decision selectively retrieves primary-text passages to ground the tutor's answer, and a post-hoc verifier checks every quotation against the source text, correcting or stripping anything not verbatim. When the student moves to a new text or topic, the knowledge layer updates without retraining the model.

**Layer 3 — Player-Coach orchestration.** Each tutoring turn runs through a Player-Coach loop at inference time. The Player (fine-tuned Gemma 4) generates a response; the Coach validates it against quality criteria before it reaches the student. This provides a runtime quality gate beyond what fine-tuning alone achieves. The detailed harness mechanics — protocols, the bounded revision loop, the prose-injection invariant, and fallback policy — are documented in [implementation_notes.md § Player–Coach harness](implementation_notes.md#playercoach-harness--how-it-actually-runs).

**Layer 4 — Graphiti memory.** A temporal knowledge graph in FalkorDB persists the student's profile and per-topic confidence scores. At session start, a deterministic planner reads the student model and selects the session's focus — the weakest topic outside a 48-hour cooldown window. At session end, outcomes write back and shift confidence scores. Topic selection measurably adapts across sessions — verified live across four sessions with topic confidence progressing 55% → 56% → 57% → 58%.

---

## 3. How We Used Gemma 4

- **Model:** Gemma 4 26B A4B MoE (Apache 2.0), base: `unsloth/gemma-4-26b-a4b-it`
- **Fine-tuning:** Unsloth + TRL SFTTrainer, LoRA, on DGX Spark GB10 (128GB unified memory)
- **Training data format:** ShareGPT JSONL with `<think>` reasoning blocks (75% reasoning / 25% direct ratio enforced — fewer reasoning examples degrades post-fine-tune reasoning capability)
- **Inference:** llama-swap on GB10 port 9000, with nomic-embed-text-v1.5 (768-dim) for embeddings
- **Access layer:** Open WebUI (single Docker container, `--network host`), accessed over Tailscale
- **Why Gemma 4:** The MoE architecture (26B total, 4B active) gives strong reasoning within the GB10's memory budget. Apache 2.0 licensing enables unrestricted local deployment.

---

## 4. Training Data Generation

The Agentic Dataset Factory is a standalone, domain-agnostic pipeline. Adding a new subject requires only a new `domains/` directory containing a GOAL.md (behavioural specification) and source documents — no code changes.

**Stage 0 — Ingest:** Docling processes source PDFs into chunks, indexed into ChromaDB. Both standard mode (digital PDFs) and VLM mode (scanned paperbacks via a home office scanner) are validated and working on the GB10.

**Stage 1 — Generate:** A Player-Coach adversarial loop runs overnight on the GB10. The Player agent retrieves curriculum chunks and generates tutoring dialogue examples. The Coach agent evaluates each example against GOAL.md criteria (AO coverage, Socratic quality, grade calibration, factual accuracy). Rejected examples are revised and resubmitted, up to 5 cycles. Accepted examples are routed to either the behaviour layer (train.jsonl for fine-tuning) or the knowledge layer (rag_index/ for ChromaDB seeding).

The pipeline produced validated training data without human intervention.

---

## 5. Multi-Subject Support

The fine-tuned model demonstrates tutoring capability across multiple subjects. Sessions have been run for GCSE English Literature (Macbeth, An Inspector Calls, Power & Conflict poetry), GCSE History (post-war Britain), and exploratory sessions in GCSE Maths (linear equations). The same architecture and fine-tuning approach extends to any subject — the domain-agnostic pipeline means adding a subject is a configuration change, not an engineering change.

---

## 6. Embodied Interface — Reachy Mini

A Pollen Robotics Reachy Mini ("Scholar") provides an embodied physical tutor interface. The student can interact with the same underlying model through voice conversation with the robot, which sits on the desk during study sessions. Physical presence increases engagement — particularly important for a teenager who might not voluntarily open a chat interface.

---

## 7. Hardware & Deployment

| Component | Hardware | Role |
|-----------|----------|------|
| DGX Spark GB10 | 128GB unified memory, Blackwell GPU | Inference, fine-tuning, agent execution |
| MacBook Pro M2 Max | 64GB | Planning, orchestration |
| Synology DS918+ NAS | 32TB | FalkorDB/Graphiti backend |

The system runs entirely on home hardware connected via Tailscale mesh networking. No cloud services on the critical path. Cost per tutoring session: £0.00.

---

## 8. What We Learned (Honest Failures)

**Always-on RAG degrades fine-tuned models.** When the model retrieves on every turn, it second-guesses its fine-tuned behaviour. Selective retrieval — only when the harness determines curriculum grounding is needed — produces better results. Documented in ADR-FLEET-002.

**The generation pipeline model matters.** A Coach model that's too capable produces over-generous scores. One that's too weak produces false rejections. Calibrating the Coach to the domain is non-trivial.

**75% reasoning examples are required.** Training with fewer `<think>` blocks degraded the model's ability to reason through complex literary analysis.

**Memory selects the topic but doesn't yet shape the lesson.** The Graphiti student model drives adaptive topic selection (verified, working). However, the per-topic confidence and misconception data computed by the planner does not yet flow into the fine-tuned model's prompt — a contained improvement that would upgrade "memory selects the topic" to "memory shapes the lesson."

**A fine-tuned tutor doesn't automatically beat a well-prompted base model — and we shipped the evaluation that says so.** We ran a blind, parity-controlled comparison of the fine-tune against its own base model (`unsloth/gemma-4-26b-a4b-it`) — identical system prompt, decoding and runtime, only the weights differ. On a length-neutral criterion score the base met 88.5% of expected tutoring behaviours to the fine-tune's 62.5%, and it caught genuine factual slips in the fine-tune (a set-text date, a poem title) now logged for a re-train. The full harness and results are in the repo (`docs/runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md`); we kept them in even though the result wasn't flattering.

**Static evals can't see what this tutor is for.** A rubric scores isolated text responses, so it rewards a long, comprehensive answer over a concise Socratic turn — but the concise turn is exactly what sustains a spoken conversation with the Reachy robot and what compounds across a multi-turn revision session. The eval is structurally blind to engagement and to teaching trajectory, the two things StudyTutor is built around; it also confirmed the fine-tune is genuinely the more Socratic model and the one that surfaces its pedagogical `<think>` reasoning. The honest position: the fine-tune's value shows in sustained real use, and measuring it properly needs longitudinal engagement data, not a one-shot benchmark.

---

## 9. Impact & Vision

**Immediate:** A real Year 10 student in Bristol using this daily for GCSE revision. The tutor understands AQA assessment objectives, knows the set texts, and guides discovery rather than giving answers.

**Scalable:** The same pipeline can produce tutors for any subject. Any family with local hardware can replicate the setup. The Agentic Dataset Factory is open-source.

**Privacy:** No student data leaves the home network. No subscription. No usage tracking. No data monetisation. A child's learning journey — including mistakes, misconceptions, and weak areas — stays private.

---

## 10. Reproducibility

1. Clone the study-tutor and agentic-dataset-factory repos
2. Acquire GCSE source materials (Mr Bruff guides ~£25, AQA past papers free)
3. Run Docling ingestion pipeline
4. Run Player-Coach generation loop (overnight, ~8 hours)
5. Fine-tune Gemma 4 26B using provided training script
6. Deploy via Open WebUI

Total material cost: ~£25 for study guides. Hardware: DGX Spark GB10.

---

## 11. Links

- **Model:** [huggingface.co/RichWoollcott/gcse-tutor-gemma4-26b-moe](https://huggingface.co/RichWoollcott/gcse-tutor-gemma4-26b-moe)
- **Code:** [GitHub — study-tutor](#) *(link TBC)*
- **Code:** [GitHub — agentic-dataset-factory](#) *(link TBC)*

---

## 12. Acknowledgements

Google DeepMind (Gemma 4 base model), Unsloth (fine-tuning framework), Pollen Robotics (Reachy Mini), Anthropic (Claude — build harness and planning), NVIDIA (DGX Spark platform), and the GCSE English teachers whose open pedagogy informed the Assessment Objective framing.
