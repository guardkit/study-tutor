---
id: TASK-PO02F-001
title: Scope RAG grounding for quote fidelity
status: completed
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
completed: 2026-04-21T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-PO02F-001/
deliverable: docs/research/ideas/rag-grounding-design.md
organized_files:
  - TASK-PO02F-001.md
priority: high
task_type: research
tags: [phase-1, rag, grounding, quote-fidelity, english-literature]
complexity: 5
parent_task: TASK-PO02-007
feature_id: TBD
dependencies: []
estimated_minutes: 90
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Scope RAG grounding for quote fidelity

## Description

The TASK-PO02-007 smoke test revealed the single most visible failure mode for a GCSE literature tutor: **fabricated or corrupted primary-text quotations**. During a Macbeth session, the fine-tuned Gemma 4 produced:

> `"Come, you spirits / That tend on mortal coats… unmaculate me from the deed"`

…when the actual Shakespeare is:

> `"Come, you spirits / That tend on mortal thoughts, unsex me here"`

A correctly-rendered quote (`"Look like the innocent flower / But be the serpent under 't"`) appeared in the same response, so the model is close but unreliable. **Students quoting a fabricated line in an exam is a catastrophic tutor failure** — trust erodes instantly.

The right place to fix this is not more fine-tuning. It's a **retrieval layer** that grounds every quote-bearing response against the primary text. This task is a **scoping task only** — produce the design, not the implementation.

## Acceptance Criteria

- [x] **Corpus inventory.** Decide the authoritative text source per GCSE set-text (Macbeth, An Inspector Calls, plus any others on the exam board syllabus). Record edition/source (Project Gutenberg? OUP? Royal Shakespeare Company?). Whatever we choose becomes the corpus of record — license and canonical line-numbering both matter.
- [x] **Retrieval shape decision.** Document which approach we're taking and why:
  - (a) Tool-call grounding — expose a `lookup_quote(text_id, search)` tool the model must call before quoting; cite exact line numbers in the response.
  - (b) Embedded-context grounding — RAG-fetch likely passages at turn time and concatenate into the player prompt.
  - (c) Post-hoc verification — generate the response freely, then run a verifier pass that flags/corrects quotes against the corpus.
  - (d) Something hybrid.
- [x] **Embedding/indexing sketch.** If we go with retrieval, name the chunk granularity (scene? speech? line-with-context?) and the vector store (likely the same one we'll use for pedagogy memory — don't proliferate stores).
- [x] **Eval harness sketch.** How do we regression-test quote fidelity? Minimum proposal: a set of known-hard quotes (e.g. `"unsex me here"`, `"The raven himself is hoarse"`, the dagger soliloquy) with expected exact strings. Ship this before the implementation lands so we can measure the delta.
- [x] **Output.** A one-page design doc at `docs/research/ideas/rag-grounding-design.md` that hand-offs cleanly to a subsequent implementation task.

## Implementation Notes

- **This is a scoping task, not an implementation task.** Do not begin building the retrieval layer in this task — the point is to commit the approach before we invest engineering time.
- The feature is likely big enough to warrant its own FEAT ID (tentatively **FEAT-PO-006: RAG grounding**). Promote the design doc into a feature plan once it's approved.
- Prioritize sequencing this **before multi-subject expansion**. Every subject we add (Maths, Biology) without grounding compounds the hallucination surface area. Solving it once for English and generalizing is cheaper than solving it per-subject.
- Check whether GB10 has enough VRAM headroom to co-host a local embedding model or whether we go with a smaller CPU-side embedder; this feeds into the retrieval shape decision.

## Reference Files

- Smoke log that surfaced this: [.claude/reviews/TASK-PO02-007-smoke-log.md](../../../.claude/reviews/TASK-PO02-007-smoke-log.md)
- Current LLM client (no grounding): [src/study_tutor/llm/client.py](../../../src/study_tutor/llm/client.py)
- Role manifest + player prompt (where retrieved context would be injected): [roles/tutor/role.yaml](../../../roles/tutor/role.yaml), [roles/tutor/prompts/player.md](../../../roles/tutor/prompts/player.md)
