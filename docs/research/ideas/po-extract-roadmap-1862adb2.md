# Product Owner Extraction — Roadmap

**Session ID:** `1862adb2`
**Mode:** `po_extract`
**Project:** study-tutor
**Source path:** `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/research/ideas/`
**Coverage score:** 0.9
**Generated:** 17 April 2026

---

## Scope Framing (as supplied)

Hackathon delivery by 18 May 2026 — gamified GCSE tutor for Lilymay (Year 10, AQA English Language and Literature) using DeepAgents harness, fine-tuned Gemma 4 31B, Graphiti student model, ChromaDB RAG, with gamification engine. Direct-to-student product (not teacher-facilitated), multi-subject architecture starting with English.

---

## Source Documents

| Filename | Contribution |
|---|---|
| `GCSE_English_AI_Tutor_Proposal.md` | Core product scope, target subject area, tutoring goals, adaptive support, exam preparation focus, and overall learner-facing value proposition. |
| `GCSE_Gamification_Research.md` | Motivation rationale and evidence for gamified engagement, learner rewards, progress visibility, and completion recognition. |
| `copyright-training-data-analysis.md` | Copyright and training-data boundary constraining how the tutor should handle protected texts and learner requests involving source material. |
| `deepagents-patterns-review.md` | Evidence for session-oriented conversational patterns supporting a multi-turn tutoring experience. Architecture-specific mechanisms were not promoted as product features. |
| `gemma4-hackathon-submission-plan.md` | Delivery and submission planning context. Collateral and packaging items intentionally excluded from the product feature roadmap in response to coach feedback. |

---

## Priority Rationale

The roadmap prioritises the core tutoring experience first because the product proposal centres on an AI tutor for GCSE English learning. Motivation features follow once sessions and feedback exist, because rewards and progress need tutoring activity to attach to. Safeguard features are included as cross-cutting boundaries because the documentation highlights copyright-aware operation, but architecture, CLI, runtime orchestration, and hackathon submission packaging have been removed from the product feature roadmap or treated as implementation concerns rather than learner-facing capabilities.

---

## EPIC-001 — GCSE English Tutoring Experience

**Bounded context:** Learner Tutoring

This epic covers the learner-facing tutoring journey for GCSE English Language and Literature. It focuses on the observable behaviour of the tutor during conversation, explanation, feedback, and session progression.

### FEAT-PO-001 — Conversational GCSE English Tutor

The product provides an AI tutor that talks with learners in a natural, supportive conversation rather than acting like a static revision page. It helps learners with GCSE English Language and Literature by answering questions, explaining ideas clearly, and keeping the exchange focused on study support.

- **Depends on:** —
- **Constraints:** Must address GCSE English Language and Literature support. Must operate as a conversational tutor rather than a passive content library.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-002 — Adaptive Explanation and Personalised Guidance

The tutor adapts its explanations to the learner's current needs instead of giving the same response to every pupil. It offers personalised guidance during the conversation so that support can be adjusted to understanding level, uncertainty, and the specific English topic being discussed.

- **Depends on:** FEAT-PO-001
- **Constraints:** Personalisation must remain within GCSE English tutoring scope. Guidance should adapt during conversation.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-003 — Exam Preparation Support

The tutor helps learners prepare for GCSE English examinations, not just explore topics casually. It supports revision and exam-focused study by guiding learners through the kinds of knowledge and practice needed for English Language and Literature success.

- **Depends on:** FEAT-PO-001
- **Constraints:** Must remain focused on GCSE exam preparation. Must support both English Language and Literature.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-004 — Quotations and Evidence Guidance

The tutor helps learners work with quotations and textual evidence as part of GCSE English study. When a learner is analysing a text or building an exam response, the tutor should guide them in using relevant quotations and connecting those quotations to their interpretation.

- **Depends on:** FEAT-PO-001, FEAT-PO-003
- **Constraints:** Must support quotation use within GCSE English tutoring. Feedback should stay tied to textual analysis and exam response building.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-005 — Constructive Feedback on English Work

The tutor gives feedback that helps the learner improve rather than only judging whether an answer is right or wrong. In GCSE English terms, this means responding to the learner's ideas with constructive guidance on interpretation, written response quality, and how to strengthen an answer.

- **Depends on:** FEAT-PO-001, FEAT-PO-002
- **Constraints:** Feedback must be constructive and improvement-oriented. Feedback should remain grounded in GCSE English tasks.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-006 — Session-Based Study Support

The tutoring experience is organised as a study session rather than a single isolated answer. During a session, the tutor supports the learner through an ongoing exchange so that questions, explanations, and follow-up guidance can build on what has already been discussed.

- **Depends on:** FEAT-PO-001
- **Constraints:** Must support multi-turn tutoring sessions. Session flow should preserve continuity across learner turns.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`, `deepagents-patterns-review.md`

---

## EPIC-002 — Learner Motivation and Progression

**Bounded context:** Gamification

This epic covers learner motivation features drawn from the gamification research and proposal material. It focuses on visible progression, rewards, and study encouragement that can help learners stay engaged with GCSE English revision.

### FEAT-PO-007 — Gamified Learning Journey

The product uses gamification to make GCSE English revision more engaging for learners. The learning journey should feel rewarding and motivating, so that learners are encouraged to return and continue practising rather than treating revision as a one-off interaction.

- **Depends on:** FEAT-PO-006
- **Constraints:** Gamification must support learning motivation rather than distract from revision. Must fit GCSE English study use.
- **Source documents:** `GCSE_English_AI_Tutor_Proposal.md`, `GCSE_Gamification_Research.md`

### FEAT-PO-008 — Reward and Achievement Feedback

The tutor gives learners visible signs of achievement as they make progress through study. These rewards should reinforce effort and completion so that learners receive positive encouragement tied to their tutoring activity.

- **Depends on:** FEAT-PO-007
- **Constraints:** Rewards should reinforce learning activity. Achievement signals should be understandable to GCSE learners.
- **Source documents:** `GCSE_Gamification_Research.md`, `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-009 — Progress Tracking for Revision

The product shows learners that they are making progress in their GCSE English revision over time. This progress view should connect tutoring activity to a sense of advancement, helping learners understand that completed study and continued practice are moving them forward.

- **Depends on:** FEAT-PO-006, FEAT-PO-007
- **Constraints:** Progress indicators must relate to revision activity. Progress should be understandable without requiring teacher interpretation.
- **Source documents:** `GCSE_Gamification_Research.md`, `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-010 — Session Completion Recognition

When a learner finishes a study session, the product recognises that completion in a visible way. This completion feedback should encourage the learner to continue revising and should connect the end of a session to the wider sense of achievement and progression.

- **Depends on:** FEAT-PO-006, FEAT-PO-008, FEAT-PO-009
- **Constraints:** Completion recognition must be tied to study sessions. Must reinforce motivation without replacing academic feedback.
- **Source documents:** `GCSE_Gamification_Research.md`, `GCSE_English_AI_Tutor_Proposal.md`

---

## EPIC-003 — Safe and Copyright-Aware Tutoring

**Bounded context:** Content Safeguards

This epic covers learner-visible safeguards and content boundaries evidenced in the documentation. It focuses on how the tutor handles copyrighted material and keeps support within acceptable tutoring use.

### FEAT-PO-011 — Copyright-Aware Handling of Learning Content

The tutor must handle learning content in a way that respects copyright constraints described in the source analysis. When supporting GCSE English study, it should avoid turning the product into a channel for reproducing protected material in ways that fall outside the documented safety boundary.

- **Depends on:** FEAT-PO-001
- **Constraints:** Must respect copyright-related limits described in the documentation. Content support must remain appropriate for tutoring use.
- **Source documents:** `copyright-training-data-analysis.md`, `GCSE_English_AI_Tutor_Proposal.md`

### FEAT-PO-012 — Bounded Text Support for GCSE English

When learners ask for help with texts, the tutor should provide support in a bounded tutoring form rather than unrestricted reproduction of source material. In practice, it should help with understanding, analysis, and use of evidence while keeping responses within the documented copyright-aware limits.

- **Depends on:** FEAT-PO-004, FEAT-PO-011
- **Constraints:** Must support analysis and understanding without unrestricted text reproduction. Must align with copyright-aware handling described in the documents.
- **Source documents:** `copyright-training-data-analysis.md`, `GCSE_English_AI_Tutor_Proposal.md`

---

## Constraints and Dependencies

- Only learner-observable product capabilities are included in the roadmap; hackathon collateral and delivery packaging are intentionally excluded from product features.
- Features must remain grounded in the available documents and use only cited filenames from the provided list.
- Gamification features depend on tutoring sessions and learner progress signals rather than on submission or demo artefacts.
- Copyright-aware behaviour constrains how the tutor supports quotations, texts, and evidence use.

---

## Open Questions

1. The proposal and research support gamification, but the exact reward mechanics are not fully specified in the documentation; the implementation may need to choose between points, badges, streaks, or other visible achievement signals.
2. The documentation supports adaptive and constructive tutoring, but it does not fully define how learner progress should be measured across English Language and Literature topics.
3. The copyright analysis establishes caution around protected material, but the exact operational boundary for quotation length and reproduction handling will need a policy decision before detailed specification.

---

## Assumptions

### ASM-001 — Domain (confidence: high)

**Statement:** The primary product described by the documentation is a learner-facing GCSE English tutoring experience rather than a tooling or infrastructure product.

**Source:** `GCSE_English_AI_Tutor_Proposal.md`

**Impact if wrong:** The epic structure and prioritisation would need to shift away from learner tutoring toward another product centre.

### ASM-002 — Scope (confidence: high)

**Statement:** Hackathon submission planning documents describe delivery collateral and milestones, not enduring learner-facing product features.

**Source:** `gemma4-hackathon-submission-plan.md`

**Impact if wrong:** Some excluded items would need to be restored as roadmap features, changing the current separation between product scope and delivery scope.

### ASM-003 — Compliance (confidence: medium)

**Statement:** The copyright analysis is intended to constrain the tutor's observable behaviour when handling texts and quotations.

**Source:** `copyright-training-data-analysis.md`

**Impact if wrong:** The safeguard epic would need to be rewritten as internal policy guidance rather than feature behaviour.

---

## Dependency Graph Summary

```
FEAT-PO-001 (Conversational Tutor)
├── FEAT-PO-002 (Adaptive Explanation)
│   └── FEAT-PO-005 (Constructive Feedback)
├── FEAT-PO-003 (Exam Prep)
│   └── FEAT-PO-004 (Quotations Guidance)
│       └── FEAT-PO-012 (Bounded Text Support)
├── FEAT-PO-006 (Session-Based Study)
│   └── FEAT-PO-007 (Gamified Journey)
│       ├── FEAT-PO-008 (Rewards)
│       └── FEAT-PO-009 (Progress Tracking)
│           └── FEAT-PO-010 (Completion Recognition)
└── FEAT-PO-011 (Copyright-Aware Handling)
    └── FEAT-PO-012 (Bounded Text Support)
```

---

## Notes on This Run

This extraction was produced after an earlier `po_idea` run (`86d6f116`) drifted significantly — inventing a teacher-facilitator product model, deferring gamification, and citing synthetic source documents. Moving to `po_extract` against the real documents folder grounded the output: coverage score rose from `null` to 0.9, the learner-facing framing was restored, gamification became a first-class epic, and copyright handling was surfaced from the existing research rather than inferred.

The delivery scope — hackathon submission packaging, Lilymay as specific test user, 18 May deadline, fine-tuned Gemma 4 31B, Graphiti, ChromaDB, DeepAgents harness, Ollama — was intentionally excluded by the agent as "implementation and delivery concerns rather than learner-facing capabilities" (see priority rationale). A separate delivery plan mapping these features to calendar days against 18 May remains an open piece of work.
