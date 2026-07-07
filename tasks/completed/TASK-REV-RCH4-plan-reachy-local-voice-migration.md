---
id: TASK-REV-RCH4
title: "Plan: Reachy Local Voice Migration"
task_type: review
status: completed
priority: high
created: 2026-07-07
feature_ref: FEAT-VOICE-004
clarification:
  context_a:
    timestamp: 2026-07-07
    decisions:
      focus: all
      tradeoff: quality
context_files:
  - features/reachy-local-voice-migration/reachy-local-voice-migration_summary.md
  - features/reachy-local-voice-migration/reachy-local-voice-migration.feature
  - docs/design/voice-tutor-and-reachy-design.md
  - docs/research/ideas/reachy-local-backend-recon-deltas-2026-07-06.md
---

# Plan: Reachy Local Voice Migration (FEAT-VOICE-004)

Decision-mode review for the Reachy local-voice migration. Consumes the 25-scenario
BDD spec and the recon deltas. See analysis and decision checkpoint in the session log.

Key constraint discovered during review: the code artefacts (ask_tutor tool,
query_student_model port, Scholar profile) live in the **sibling `fleet-gateway`
repo**, not in study-tutor — so study-tutor's AutoBuild cannot build them. This plan is
the authoritative sequencing + spec home; execution is Operator + Opus per build-plan §0a.
