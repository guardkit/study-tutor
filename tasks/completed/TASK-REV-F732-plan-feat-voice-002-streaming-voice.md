---
id: TASK-REV-F732
title: "Plan: FEAT-VOICE-002 streaming voice"
status: completed
task_type: review
review_mode: decision
review_depth: standard
created: 2026-07-06T21:05:00Z
updated: 2026-07-06T21:45:00Z
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  options_count: 3
  recommendations_count: 8
  decision: implement
  feature_id: FEAT-VOICE-002
  feature_file: .guardkit/features/FEAT-VOICE-002.yaml
  recommended_option: tiered-dependency (Option 1)
  report_path: .claude/reviews/TASK-REV-F732-review-report.md
  completed_at: 2026-07-06T21:45:00Z
priority: high
tags: [voice, streaming, websocket, planning, feat-voice-002]
complexity: 8
context_files:
  - features/streaming-voice/streaming-voice_summary.md
  - features/streaming-voice/streaming-voice.feature
  - features/streaming-voice/streaming-voice_assumptions.yaml
  - docs/design/voice-tutor-and-reachy-design.md
  - docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md
  - tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md
clarification:
  context_a:
    timestamp: 2026-07-06T21:00:00Z
    mode: defaults
    gating: ai_gated_no_value_detected
    decisions:
      focus: all
      tradeoff: quality
      concerns:
        - chunk-straddling quote verification against accumulated text (ADR-ARCH-027 named obligation)
        - six low-confidence-but-confirmed assumptions (ASSUM-003/005/007/008/009/010) get closest implementation-vs-spec scrutiny
        - no-duplication boundary with FEAT-VOICE-001 (refusal parity via shared rulebook, not reimplementation)
        - BINDING_SHA discipline — contract/binding Rev 1 frozen; implement, don't re-freeze
---

# Task: Plan: FEAT-VOICE-002 streaming voice

## Description

Decision review for planning FEAT-VOICE-002 — streaming tutoring turns (live
text and voice) on the session channel. The BDD spec exists
(`features/streaming-voice/streaming-voice.feature`, 31 scenarios, all 10
assumptions owner-confirmed 2026-07-06). The design and contract are frozen
and ratified: voice design §5, ADR-ARCH-026 (Accepted), ADR-ARCH-027,
contract §7 Rev 1 + binding Rev 1 (`CONTRACT_SHA=574615e9…`,
`BINDING_SHA=e50897d1…`). This review analyses implementation approaches and
produces the task breakdown; it does not re-open ratified decisions.

Subsumes the server scopes of TASK-STREAM-001 (Scope 1 streaming Player
generation, Scope 2 WS transport — already frozen at G-CON, Scope 4
acceptance); the Flutter client (Scope 3) is FEAT-VOICE-003.

## Review Scope

- Technical options for implementing the frozen §7 frame flow
  (`transcript` → `token`* → `audio_ref`* → `done`, `error` envelope)
- Task decomposition, dependencies, parallel waves, AutoBuild suitability
  (operator_handoff detection for runtime-observation ACs)
- Risk analysis: the four Context A concerns above
- Effort/complexity estimation per task

## Acceptance Criteria

- [ ] Technical options analysis with recommended approach
- [ ] Task breakdown honouring the spec's Non-Gherkin obligations (frozen pins)
- [ ] Decision checkpoint presented (A/R/I/C)

## Test Execution Log

(review task — no tests)
