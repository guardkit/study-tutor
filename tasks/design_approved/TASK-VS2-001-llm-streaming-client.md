---
complexity: 5
dependencies: []
feature_id: FEAT-VOICE-002
id: TASK-VS2-001
implementation_mode: task-work
parent_review: TASK-REV-F732
status: design_approved
task_type: feature
title: LLM streaming client — LLMClient.generate_stream + LLMPlayerAdapter.respond_stream
  (SSE token iterator)
wave: 1
---

## Description

TASK-STREAM-001 Scope 1, both seams (spec summary "Non-Gherkin obligations").

**`LLMClient.generate_stream(prompt, system=None) -> AsyncIterator[str]`**
(`src/study_tutor/llm/client.py`): stream tokens from the same
`/v1/chat/completions` endpoint `generate()` uses, via
`httpx.AsyncClient(...).stream(...)` with `"stream": True`; parse
OpenAI-compatible SSE `data: {...}` lines (`choices[0].delta.content`),
terminate on `data: [DONE]`. **Purely additive** — `generate()` (which
hardcodes `"stream": False` at `client.py:185`) is untouched; the upstream
llama-swap/OpenAI endpoint already supports SSE.

**`LLMPlayerAdapter.respond_stream(session_state, learner_message) ->
AsyncIterator[str]`** (`tutoring/adapters/llm_player_adapter.py`): natively
async — **no** `asyncio.to_thread` bridge (that bridge at lines ~162/192
exists only because `generate()` is sync). Prompt assembly identical to
`respond()`.

**ASSUM-009 (owner-confirmed):** the stall bound is the existing LLM request
timeout — configured as an httpx **read timeout** on the stream (via
`httpx.Timeout`), not a single total-request deadline, so a
slow-but-progressing stream is never killed while a silent stall is.

## Acceptance Criteria

- [ ] `LLMClient.generate_stream` is `async def` returning `AsyncIterator[str]`; a seam test with a mock httpx transport feeding canned SSE lines asserts tokens yield in source order and the iterator terminates cleanly on `[DONE]`
- [ ] Timeout is read-timeout semantics: test asserts a stream yielding tokens continuously past the window is NOT killed, while one silent for the read-timeout window raises (ASSUM-009)
- [ ] `LLMPlayerAdapter.respond_stream` yields the same token sequence its `generate_stream` source produces, with prompt assembly matching `respond()` (assert equal call args on a shared fake)
- [ ] Existing `LLMClient.generate` tests pass with zero modifications (regression guard); `generate()` body unchanged
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "A typed question's answer streams while it is still being composed" (@smoke)
- "A tutor model that stalls without producing anything ends in a visible failure"

## Seam Tests

```python
"""Seam test: verify GENERATE_STREAM contract for TASK-VS2-003."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("GENERATE_STREAM")
async def test_generate_stream_token_order_and_done():
    """Contract: AsyncIterator[str] yielding delta tokens in SSE source order,
    terminating on `data: [DONE]`. Producer: TASK-VS2-001 (this task);
    consumer: TASK-VS2-003 run_turn_stream.
    """
    client = make_client_with_mock_transport(sse_lines=[
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        "data: [DONE]",
    ])
    tokens = [t async for t in client.generate_stream("q")]
    assert tokens == ["Hel", "lo"]
```

## References

- Spec summary "Non-Gherkin obligations" (`LLMClient.generate_stream`) · TASK-STREAM-001 Scope 1 · ASSUM-009 · `llm/client.py:106-205` · `tutoring/adapters/llm_player_adapter.py:162,192` · review report .claude/reviews/TASK-REV-F732-review-report.md