---
id: TASK-PO02F-003
title: Fix stale DEFAULT_OLLAMA_MODEL fallback in client.py
status: backlog
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
priority: low
task_type: bugfix
tags: [phase-0, llm-client, hygiene, micro]
complexity: 1
parent_task: TASK-PO02-007
feature_id: FEAT-PO-002
dependencies: []
estimated_minutes: 10
implementation_mode: direct
micro: true
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Fix stale DEFAULT_OLLAMA_MODEL fallback in client.py

## Description

The plan doc assumed the fine-tuned model would be tagged `gcse-tutor-gemma4-31b:Q4_K_M`; the actual tag served on the MacBook Pro is `gcse-tutor-gemma4-moe:latest` (25.2B MoE, Q4_K_M). This mismatch landed in a module-level constant that is only consulted as a fallback when `OLLAMA_MODEL` is unset:

```python
# src/study_tutor/llm/client.py:19
DEFAULT_OLLAMA_MODEL = "gcse-tutor-gemma4-31b:Q4_K_M"
```

Runtime is **fine** — `.env` overrides this — but a silent fallback to a nonexistent model would surface as a confusing 404 from Ollama rather than a clear config error.

## Acceptance Criteria

- [ ] Update `DEFAULT_OLLAMA_MODEL` in `src/study_tutor/llm/client.py:19` to `"gcse-tutor-gemma4-moe:latest"` (or to whatever the team decides is the canonical default — confirm with the plan doc owner first).
- [ ] Update `DEFAULT_OLLAMA_BASE_URL` on `client.py:18` from `"http://gb10.tailnet:11434"` to `"http://localhost:11434"`. The tailnet host was speculative in the plan doc; the real Phase 0 host is localhost. Same reasoning — fallback should hit a plausible default, not a ghost.
- [ ] Grep for other occurrences of the old strings in the repo (`gcse-tutor-gemma4-31b`, `gb10.tailnet`) and update docs / task files / plan references as appropriate. Do not rewrite historical smoke logs or completed task files — those are time-stamped artefacts.
- [ ] No test changes needed unless existing tests happen to assert on the literal defaults.

## Implementation Notes

- **Micro task.** Single constant change plus a grep sweep — should take under 10 minutes.
- If the team prefers to remove the defaults altogether and make `OLLAMA_MODEL` / `OLLAMA_BASE_URL` **required** (fail loudly on missing config rather than falling back to a possibly-wrong default), that's an equally good outcome — raise it with the plan owner during the fix.

## Reference Files

- [src/study_tutor/llm/client.py:18-19](../../../src/study_tutor/llm/client.py)
- Smoke log note: [.claude/reviews/TASK-PO02-007-smoke-log.md](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) (see "Follow-ups" #4)
