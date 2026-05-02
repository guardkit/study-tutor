---
id: TASK-REV-GR1A
title: "Plan: Graphiti Runtime Integration Repair"
task_type: review
status: review_complete
priority: high
created: 2026-05-02T00:00:00+00:00
updated: 2026-05-02T00:00:00+00:00
complexity: 5
tags:
  - feature-plan
  - graphiti
  - llm-wiring
  - embedder
  - llama-swap
  - local-only
  - no-cloud-api
  - phase-1-falsification-repair
  - dark-factory
parent_task: TASK-PH2-GR-001
related:
  - TASK-PH2-GR-001
  - TASK-PH2-GR-002
context_files:
  - features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md
  - tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
clarification:
  context_a:
    timestamp: 2026-05-02T00:00:00Z
    mode: defaults
    decisions:
      review_depth: D                  # All layers equally — full architectural pass across all five waves
      conflict_resolution: A           # Blast-radius minimisation — Loader path; defer schema unification to TASK-PH2-GR-002
      specific_concerns: F             # No specific concerns beyond the ACs
      output_format: B                 # AC-compliance + targeted risk flags from the risk register
      smoke_test_scope: A              # In-scope — review verifies smoke test catches graphiti-core 0.30 constructor-surface drift
  context_b:
    timestamp: 2026-05-02T00:00:00Z
    mode: mixed                        # User overrode some defaults
    decisions:
      approach: R                      # Ratify Loader path
      execution: D                     # Detect automatically — user wants /feature-build (autobuild)
      testing: D                       # Default per-subtask complexity
      constraints: N                   # None beyond Wave 4 LLM-bound floor (acknowledged)
      workspace_naming: A              # Auto-generated (autobuild-friendly)
subtasks:
  - TASK-GR-LOAD
  - TASK-GR-WIRE
  - TASK-GR-SMOK
  - TASK-GR-SEED
  - TASK-GR-DEMO
feature_id: FEAT-FD32
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  score: 78
  findings_count: 8
  recommendations_count: 5
  decision: pending_user_choice
  report_path: .claude/reviews/TASK-REV-GR1A-review-report.md
  completed_at: 2026-05-02T00:00:00Z
---

# Plan: Graphiti Runtime Integration Repair

## Description

Decision-mode review task for `/feature-plan "Graphiti Runtime Integration Repair"`. Drives the orchestration that produces the structured feature YAML (FEAT-XXXX), the wave-organised subtask breakdown for [TASK-PH2-GR-001](./TASK-PH2-GR-001-graphiti-runtime-integration-repair.md), and the BDD scenario→task linking for the existing `features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature` file.

The implementation context is fully established in the parent task — this review task exists to (a) validate the proposed wave breakdown against the 8 acceptance criteria, (b) produce the parallel-execution graph for `/feature-build`, and (c) capture the audit trail for the planning decisions.

## Context

### Parent task (where the work is defined)

**TASK-PH2-GR-001** — Graphiti runtime integration repair — wire local LLM + embedder via llama-swap (no cloud APIs). 8 ACs, complexity 5, blocks FEAT-PH2-001, parent_validation: phase-1-validation.md.

### Hard constraints (non-negotiable)

- **DECISION-DF-001**: No cloud LLM/embedding APIs on the critical path. `llm_provider in ("openai", "gemini")` and `embedding_provider == "openai"` MUST raise `ValueError` at config-load time.
- **All inference via llama-swap on `:9000`** (Tailscale: `http://promaxgb10-41b1:9000/v1`). MacBook ollama is the documented fallback.
- **Use the GuardKit-canonical pattern** from `guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client` / `_build_embedder` — `OpenAIGenericClient` + `OpenAIEmbedder`, `api_key="local-key"` placeholder.
- **Cross-encoder NOT defaulted to OpenAI silently** — init-time WARN log required (per AC-003); any runtime cross-encoder call is a critical error.
- **Loader path** for the `.guardkit/graphiti.yaml` integration (per Q2 default). Schema unification deferred to TASK-PH2-GR-002.

### BDD coupling

- Feature file `features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature` exists with 24 scenarios.
- Every scenario already tagged `@task:TASK-PH2-GR-001` (per the summary file).
- Step 11 (BDD linking) will detect zero retag work needed — the feature is already wired for the R2 task-level oracle to fire during `/task-work TASK-PH2-GR-001` Phase 4.

## Acceptance Criteria (for the planning artefact)

- [ ] Decision review surfaces the 8 ACs from TASK-PH2-GR-001 and the 5-risk register, mapped to wave assignments.
- [ ] Implementation hint's 5-wave shape (loader+guard, build_llm+build_embedder+cross_encoder_guard, smoke test, seed+gate flip, MCP demo) validated against AC coverage. Every AC must be assigned to a wave.
- [ ] Structured feature YAML (`.guardkit/features/FEAT-XXXX.yaml`) generated with wave-based parallel groups, complexity scores, and `file_path` resolution against actual files on disk (`--discover`).
- [ ] Subtask markdown files generated under `tasks/backlog/graphiti-runtime-integration-repair/` (subfolder, not parent backlog/) with `task_type: feature` (not `scaffolding` — these touch business logic), `parent_review: TASK-REV-GR1A`, `feature_id: FEAT-XXXX`, and lint-compliance acceptance criterion present on every implementation/refactor wave.
- [ ] Mermaid diagrams in IMPLEMENTATION-GUIDE.md: data flow (always), integration contract (complexity 5 → optional, but include given DECISION-DF-001 enforcement complexity), task dependency graph (≥3 tasks → required).
- [ ] §4 Integration Contracts section generated for the cross-task data dependencies: (a) loader output → wiring input (config object), (b) wired client → smoke test (real client), (c) wired client → seed script (real client), (d) wired client → MCP demo (real client).
- [ ] Step 11 BDD-linker run on `features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature`: expected outcome is `status=skipped, reason=all_tagged` (idempotency path — every scenario already carries `@task:TASK-PH2-GR-001`). If any scenario lacks the tag, linker proposes mapping at threshold ≥0.6.
- [ ] Pre-flight validation (`guardkit feature validate FEAT-XXXX`) passes: no intra-wave deps, valid `task_type`, all task files exist.

## Test Requirements

This is a planning task — no production tests required. The "tests" for the planning artefact are:

- The generated feature YAML parses through `FeatureLoader.validate_feature()` without errors.
- The generated subtask files all carry `task_type` (CoachValidator profile selection works).
- The generated IMPLEMENTATION-GUIDE.md renders Mermaid diagrams correctly in GitHub markdown preview.

## Implementation Notes

### Why this is a review task, not direct task creation

The parent task (TASK-PH2-GR-001) is already richly specified — 8 ACs, hard constraints, risk register, even an "Implementation hint" with 5 named waves. The standard `/task-create` flow would just stamp another task. `/feature-plan` adds value by:

1. Parameterising the wave breakdown into machine-readable parallel groups for `/feature-build`.
2. Producing the §4 Integration Contracts that catch cross-task seam bugs (the same class of bug that hid the Phase 1 falsification — graphiti-core's silent default to OpenAI when no `llm_client` was passed).
3. Generating the IMPLEMENTATION-GUIDE.md data-flow diagram, which makes the "config → wired client → live evidence" chain auditable at a glance.

### Why the wave breakdown matters here specifically

Wave 1 (loader + DECISION-DF-001 guard) is a hard prerequisite for Waves 2–5: it's the only gate that prevents accidental cloud-API regression during the rest of the repair. Treating it as a parallel sibling of Wave 2 would risk a half-wired client running cloud requests during dev iterations. Sequential dependency is mandatory.

Waves 3 (smoke test) and 4 (seed) can be implemented serially (smoke test gates seed quality), but the seed run itself is LLM-bound (~30 min wall-clock on MacBook ollama; Phase 1 latency-spike measured 78s/`add_episode` median). Worth front-loading.

Wave 5 (MCP demo) is the human-in-the-loop verification step — it cannot be parallelised because it depends on a live FalkorDB seed from Wave 4 plus a Claude Desktop session.

### Known unblockers already in flight

Three patches landed during the close-out gate run on 2026-05-02 (commits `a210472`, `78d3498`, `732672c`):

- `queries.py:_read_student_partition` — read API now correctly uses `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids`.
- `async_write.py:_add_episode_kwargs` — graphiti-core 0.29's real `add_episode` signature wired.
- Group-id format normalised: `student-`, `subject-`, `fleet-` (from `student:`, `subject:`, `fleet:`) per graphiti-core 0.29's `GroupIdValidationError`.

These are prerequisites; this plan assumes they are merged on `main`.

## Cross-references

- `tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md` — the parent task this plan decomposes.
- `features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md` — feature spec (24 scenarios, DECISION-DF-001 surface, Phase 1 gate coupling).
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical client pattern to mirror.
- `.guardkit/graphiti.yaml` — config source-of-truth.
- `docs/research/ideas/phase-1-validation.md` — the gate that this work flips from Falsified to Held.
