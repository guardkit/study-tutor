---
id: TASK-PO02F-002
title: Set explicit num_predict ceiling on Ollama requests
status: backlog
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
priority: high
task_type: bugfix
tags: [phase-0, ollama, llm-client, truncation]
complexity: 2
parent_task: TASK-PO02-007
feature_id: FEAT-PO-002
dependencies: []
estimated_minutes: 30
implementation_mode: direct
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Set explicit num_predict ceiling on Ollama requests

## Description

The TASK-PO02-007 smoke test observed a Macbeth response truncating mid-sentence:

> `"Body Paragraph 2: Analyse the deception and manipulation involved in her ambition (the "`

This is not a model defect — it's almost certainly hitting Ollama's default `num_predict` ceiling. `src/study_tutor/llm/client.py` currently sends:

```python
payload: dict[str, object] = {
    "model": model,
    "prompt": prompt,
    "stream": False,
}
```

…with **no explicit token cap**. Ollama's default for `num_predict` varies by model/config but is typically around 128 tokens — far too small for a GCSE essay scaffold.

## Acceptance Criteria

- [ ] **Confirm root cause.** Run a reproduction: the Macbeth prompt from the smoke log, with the current payload vs. with an explicit high `num_predict`. Observe whether the truncation disappears.
- [ ] **Add `num_predict` to payload** in `src/study_tutor/llm/client.py::LLMClient._generate_ollama`. Suggested value: **2048** (enough for a full GCSE essay scaffold; configurable via env for tuning).
- [ ] **Make it configurable.** New env var `OLLAMA_NUM_PREDICT` (integer), default 2048. Read at call time (SR-03 pattern — never at module import).
- [ ] **Document the new knob** in `.env.example` alongside the other Ollama settings.
- [ ] **Unit test.** Extend the existing LLM client tests to assert the payload includes `num_predict` and that the value comes from the env var when set. Do not add a network-touching test — the existing structure uses response stubs.
- [ ] **Manual re-run.** Repeat the Macbeth Lady-Macbeth-ambition prompt through the MCP stdio path; confirm the essay scaffold completes through "Body Paragraph 2" without truncation.

## Implementation Notes

- **Direct mode.** This is roughly 10 lines of code plus one test — don't over-engineer.
- Keep the default in the module constants alongside `DEFAULT_OLLAMA_BASE_URL` / `DEFAULT_OLLAMA_MODEL` (e.g. `DEFAULT_OLLAMA_NUM_PREDICT = 2048`).
- Do **not** also add `temperature`, `top_p`, `repeat_penalty`, etc. in the same pass (YAGNI). Add them when a specific need arises.
- Higher `num_predict` means longer worst-case latency; that's acceptable since the smoke test showed steady-state turns at ~11–13s and we have a 30s ceiling with headroom.

## Reference Files

- Smoke log: [.claude/reviews/TASK-PO02-007-smoke-log.md](../../../.claude/reviews/TASK-PO02-007-smoke-log.md) (see "Session 2 — Macbeth → Defects observed → 2. Truncation")
- Payload construction site: [src/study_tutor/llm/client.py:58-85](../../../src/study_tutor/llm/client.py)
- Ollama API reference for `num_predict`: https://github.com/ollama/ollama/blob/main/docs/api.md#generate-request-with-options
