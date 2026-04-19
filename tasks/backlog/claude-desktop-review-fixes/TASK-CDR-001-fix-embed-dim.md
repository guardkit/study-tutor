---
id: TASK-CDR-001
title: Fix embedding_dimensions 1024 → 768 in ADR-007 + graphiti.yaml
status: backlog
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 1
implementation_mode: task-work
created: 2026-04-19
priority: high
tags: [graphiti, config, embedding, phase-0, phase-1-seeding-blocker]
complexity: 2
blocks: [system-design]
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix embedding_dimensions 1024 → 768 in ADR-007 + graphiti.yaml

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
finding **F1** — hard bug. Both the architecture decision record and the live
Graphiti config declare `embedding_dimensions: 1024`, but `nomic-embed-text-v1.5`
is natively a 768-dimension model. No Matryoshka truncation is configured
anywhere. If FalkorDB's index is provisioned at 1024 and the embedder returns
768, Phase 1 seeding fails at the first write.

## Scope of Changes

**Files:**
- `docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md` — line 52
- `.guardkit/graphiti.yaml` — line 14

**Edits:**
1. Change `embedding_dimensions: 1024` → `embedding_dimensions: 768` in both files.
2. Add a one-line clarification in ADR-007 (near the config block) confirming
   nomic-embed-text-v1.5's native 768-dimension output, so future readers don't
   wonder where the number came from.

## Acceptance Criteria

- [ ] `.guardkit/graphiti.yaml` contains `embedding_dimensions: 768`.
- [ ] `ADR-ARCH-007-graphiti-split-topology.md` contains `embedding_dimensions: 768`
      in its embedded YAML snippet.
- [ ] ADR-007 includes a short note that 768 is the model's native output (and a
      reminder that introducing Matryoshka truncation requires updating both
      files together).
- [ ] `grep -n "embedding_dimensions" .guardkit/graphiti.yaml docs/architecture/decisions/ADR-ARCH-007-*.md`
      returns only `768` results.

## Test Requirements

Verifiable invariant: grep must not find `1024` as the value of
`embedding_dimensions` anywhere in the repo.

```bash
! grep -rn "embedding_dimensions:[[:space:]]*1024" . \
    --include='*.yaml' --include='*.md'
```

The command must return no matches (exit 1 is success).

## Implementation Notes

- This must land before any Phase 1 Graphiti seeding work starts.
- The change is not reversible-safe by itself — if the FalkorDB index has
  already been provisioned at 1024, it must be recreated at 768 before the
  next seed. At time of writing no Phase 1 seeding has run, so a clean-state
  edit is sufficient.

## Provenance

- Parent review finding: F1
- Reviewer evidence: external knowledge of `nomic-embed-text-v1.5` dimensionality;
  cross-check against the agentic-dataset-factory ChromaDB wiring.
- Triage: ACCEPT (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
