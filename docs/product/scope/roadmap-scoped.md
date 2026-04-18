# ideas -- Product Roadmap

## Mode

scope

## Epics

### EPIC-001: Learner Tutoring Experience

**Bounded Context:** Tutoring Session BC

This epic delivers the learner-facing tutoring flow for GCSE English revision and guided practice. It focuses on a coherent end-to-end tutoring session rather than isolated interface fragments, so the selected scope can produce a usable educational experience within the current constraint.

**Features:**
  - FEAT-PO-001: GCSE English guided tutoring session
  - FEAT-PO-002: Targeted formative feedback during tutor exchanges

### EPIC-002: Learner Motivation and Progress Signals

**Bounded Context:** Gamification BC

This epic introduces lightweight motivational mechanics that reinforce study behaviour during GCSE English revision. The selected features are limited to the research-backed loop that can be delivered coherently within the present scope, avoiding a broad rewards platform.

**Features:**
  - FEAT-PO-003: Session-based rewards and progress feedback
  - FEAT-PO-004: Streaks and learner re-engagement cues

## Priority Rationale

The selected scope preserves the existing dependency structure and concentrates delivery on one coherent learner journey: a GCSE English tutoring session with immediate educational feedback, then a lightweight motivational layer that reinforces repeated study. Guided tutoring and formative feedback were kept first because they are the core value described in the GCSE English tutor proposal, while gamification features were retained only where they are directly supported by the research document and can sit on top of the tutoring flow without expanding into a broader platform.

## Constraints and Dependencies

- The revised selection retains the current dependency structure rather than introducing new prerequisite chains.
- FEAT-PO-002 depends on FEAT-PO-001 because formative feedback requires an active tutoring session and shared learner response context.
- FEAT-PO-003 depends on FEAT-PO-001 because rewards are attached to meaningful tutoring activity inside the learner session.
- FEAT-PO-004 depends on FEAT-PO-003 because streaks and re-engagement cues build on the existence of session-level progress and reward tracking.
- All feature grounding has been rebuilt from the provided product documents, removing references to conversation-starter-roadmap.md.

## Open Questions

- The gamification research supports motivational mechanics, but the exact balance between visible rewards and low-pressure study encouragement may need calibration during feature specification.
- The tutor proposal establishes the educational direction, but assessment granularity and subject coverage breadth may need tighter limits if implementation capacity is smaller than assumed.

## Feature Spec Inputs

### FEAT-PO-001: GCSE English guided tutoring session

**Bounded Context:** Tutoring Session BC

**Description:**
The system starts a GCSE English tutoring session that guides a learner through a focused topic or task using age-appropriate explanations, scaffolded questioning, and iterative feedback. The tutor should maintain session context, adapt prompts to learner responses, and keep the interaction aligned to GCSE English learning goals rather than generic conversation.

**Source Documents:** GCSE_English_AI_Tutor_Proposal.md, deepagents-patterns-review.md

**Constraints:**
  - Must stay grounded in GCSE English tutoring outcomes described in the proposal
  - Must use the existing orchestration pattern rather than introducing a new interaction model

**Suggested Context Files:** GCSE_English_AI_Tutor_Proposal.md, deepagents-patterns-review.md

### FEAT-PO-002: Targeted formative feedback during tutor exchanges

**Bounded Context:** Tutoring Session BC

**Description:**
The tutor evaluates learner answers during a session and responds with concrete formative feedback that identifies strengths, misunderstandings, and next-step improvements in GCSE English terms. Feedback should be actionable inside the same exchange, so the learner can revise or extend an answer without leaving the tutoring flow.

**Source Documents:** GCSE_English_AI_Tutor_Proposal.md, deepagents-patterns-review.md

**Constraints:**
  - Must operate as part of the guided tutoring loop
  - Must prioritise in-session feedback over full assessment workflows

**Suggested Context Files:** GCSE_English_AI_Tutor_Proposal.md, deepagents-patterns-review.md

**Depends On:** FEAT-PO-001

### FEAT-PO-003: Session-based rewards and progress feedback

**Bounded Context:** Gamification BC

**Description:**
The product awards visible progress signals for meaningful learner activity such as completing tutor sessions, answering prompts, or returning for revision practice, in line with the gamification research outcomes. Rewards should reinforce persistence and progression in GCSE English study while remaining tightly coupled to educational actions rather than superficial engagement.

**Source Documents:** GCSE_Gamification_Research.md, GCSE_English_AI_Tutor_Proposal.md

**Constraints:**
  - Must implement only research-supported motivational mechanics that fit the MVP
  - Must attach rewards to learning behaviours inside the tutor experience

**Suggested Context Files:** GCSE_Gamification_Research.md, GCSE_English_AI_Tutor_Proposal.md

**Depends On:** FEAT-PO-001

### FEAT-PO-004: Streaks and learner re-engagement cues

**Bounded Context:** Gamification BC

**Description:**
The product tracks consecutive study participation and presents re-engagement cues that encourage learners to return to GCSE English practice without breaking the tutoring flow. Streak visibility and reminders should be designed to sustain regular revision habits identified in the gamification research, while avoiding pressure mechanics that distract from learning.

**Source Documents:** GCSE_Gamification_Research.md, GCSE_English_AI_Tutor_Proposal.md, gemma4-hackathon-submission-plan.md

**Constraints:**
  - Must remain lightweight enough for the scoped delivery window
  - Must support a demoable learner motivation loop without requiring a full notifications platform

**Suggested Context Files:** GCSE_Gamification_Research.md, GCSE_English_AI_Tutor_Proposal.md, gemma4-hackathon-submission-plan.md

**Depends On:** FEAT-PO-003

## Source Documents

| Document | Contribution |
| --- | --- |
| GCSE_English_AI_Tutor_Proposal.md | Provided the primary product grounding for the learner tutoring experience, including the educational purpose, learner interaction model, and need for in-session feedback aligned to GCSE English outcomes. |
| GCSE_Gamification_Research.md | Provided direct grounding for the motivational mechanics in scope, especially progress signals, streaks, and research-backed engagement approaches tied to learner study behaviour. |
| deepagents-patterns-review.md | Informed implementation assumptions about orchestration and interaction patterns, but only when paired with the product-specific tutor proposal so the scope remains grounded in the educational product. |
| gemma4-hackathon-submission-plan.md | Helped constrain the motivational feature set to a lightweight, demoable slice suitable for scoped delivery, while being paired with the product proposal and gamification research. |

## Assumptions

| # | Category | Assumption | Confidence | Impact if Wrong |
| --- | --- | --- | --- | --- |
| ASM-001 | constraints | The requested revision is to re-ground and refine the existing scoped feature set rather than to change the previously accepted delivery constraint or dependency ordering. | high | If the delivery constraint itself changed, the selected feature set could be too large or too small for the intended plan. |
| ASM-002 | scope | The existing dependency structure referenced in the feedback is FEAT-PO-001 as the base tutoring capability, with feedback and gamification features layered on top of it. | medium | If prior dependencies differed materially, some retained prerequisite links may need adjustment before implementation planning. |
| ASM-003 | technology | deepagents-patterns-review.md and gemma4-hackathon-submission-plan.md are supporting documents for delivery and orchestration, not standalone product-grounding sources, so every feature that cites them should also cite a product-specific GCSE document. | high | If those documents were intended as primary product documents, the grounding rules applied in this revision would be stricter than necessary. |
| ASM-004 | team | A lightweight gamification slice consisting of progress signals and streak-style re-engagement is feasible within the same scoped increment as the tutoring session, whereas a broader rewards economy or notification system would exceed the intended scope. | medium | If the team has more capacity than assumed, the roadmap may be conservative; if less, the gamification scope may still need to be reduced further. |
