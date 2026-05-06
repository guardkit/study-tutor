---
id: TASK-PTS-001
title: Strip <think> tokens from Player adapter responses
task_type: feature
status: completed
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T00:00:00+00:00
completed: 2026-05-06T00:00:00+00:00
previous_state: in_review
state_transition_reason: "All quality gates passed + manual MCP verification (5 turns, zero <think> leakage)"
completed_location: tasks/completed/TASK-PTS-001/
complexity: 2
related:
  - TASK-LSP-002
  - TASK-LCA-001
  - TASK-LCA-002
tags:
  - bug-fix
  - player-adapter
  - llm-output-sanitisation
  - thinking-tokens
  - gemma4-tutor
  - feat_lca
context_files:
  - src/study_tutor/tutoring/adapters/llm_player_adapter.py
  - src/study_tutor/llm/client.py
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-06T00:00:00+00:00
  adapter_suite: "40 passed"
  feat_lca_smoke: "3 passed, 1 skipped (unrelated)"
  new_strip_tests: "4 passed"
---

# Strip `<think>` tokens from Player adapter responses

## Description

The fine-tuned Gemma 4 26B-A4B MoE model (`gemma4-tutor`, served via
llama-swap on `promaxgb10-41b1:9000`) emits `<think>...</think>`
reasoning blocks as a preamble to its actual tutoring response. These
thinking tokens are leaking through to the student-facing
`tutor_response` field returned by `tutor_turn`.

In a live MCP session on **2026-05-06** (session `c78a49a0`), turns 1,
4, and 5 all contained visible `<think>` blocks with internal reasoning
like:

> `<think>\nThe student is asking about Lady Macbeth's ambition in
> Macbeth. This relates to AO1... At Grade 7, they should be able
> to...</think>\n\n<actual tutoring content>`

before the actual Socratic tutoring content. Students must never see
the model's internal reasoning channel.

## Root Cause

[`LLMPlayerAdapter.respond()`](src/study_tutor/tutoring/adapters/llm_player_adapter.py#L81-L104)
in
[src/study_tutor/tutoring/adapters/llm_player_adapter.py](src/study_tutor/tutoring/adapters/llm_player_adapter.py)
passes the raw LLM output through without stripping thinking tokens.
The
[`_generate_openai_compat()`](src/study_tutor/llm/client.py)
path returns `message.get("content", "")` verbatim — there is no
post-processing layer between the raw LLM output and the response
returned to the orchestrator.

## Required Fix

Add a stripping step that removes `<think>...</think>` blocks
(including multiline content) from the Player's response before it
reaches the orchestrator. The stripping must handle:

1. **Well-formed pairs**: `<think>...</think>` blocks (single- or
   multi-line content between the tags).
2. **Unclosed prefix**: `<think>` at the start of output with no
   closing tag — the model occasionally omits `</think>`. In that case,
   strip everything from the opening tag up to the first blank line (or
   to end-of-string if no blank line exists, treating the whole output
   as reasoning and returning empty string is wrong; prefer blank-line
   delimiter as the heuristic since the model emits `\n\n` between the
   reasoning preamble and the response).
3. **Trailing whitespace**: any leading whitespace/newlines left after
   stripping must be trimmed.

The stripping must live in **`LLMPlayerAdapter.respond()`** **and**
**`LLMPlayerAdapter.revise()`** so it applies regardless of which
orchestrator path is taken (first-attempt vs. revise loop).

**Do NOT strip in `LLMClient` itself** — other consumers (notably the
Coach adapter via `local-coach`) may need access to the raw output for
their own parsing or diagnostics. Sanitisation is a Player-adapter
concern, not a transport-layer concern.

## Concrete changes

### `src/study_tutor/tutoring/adapters/llm_player_adapter.py`

1. Add a module-private helper `_strip_think_tokens(raw: str) -> str`
   that:
   - Removes all `<think>...</think>` blocks (case-insensitive,
     `re.DOTALL` so `.` matches newlines).
   - If the result still starts with `<think>` (unclosed tag),
     drop everything from that opening tag up to the first `\n\n`
     boundary; if no blank line exists, fall through to "strip up to
     and including the opening tag only" (preserving content but
     removing the dangling marker — better to leak no reasoning than
     leak the whole turn).
   - `lstrip()` the result to remove leading whitespace/newlines left
     by the strip.
2. Wrap the awaited return in `respond()` with `_strip_think_tokens(...)`:
   ```python
   raw = await asyncio.to_thread(client.generate, learner_message, self._player_prompt)
   return _strip_think_tokens(raw)
   ```
3. Apply the same wrap in `revise()` around its `asyncio.to_thread(...)`
   return.
4. The helper lives at module scope (not as a `@staticmethod` on the
   class) so the unit tests can import and test it directly without
   instantiating `LLMPlayerAdapter` (which requires a `RoleConfig` and
   a player-prompt file on disk).

### `tests/unit/tutoring/adapters/test_llm_player_adapter_strip.py` (new file)

New test file at `tests/unit/tutoring/adapters/test_llm_player_adapter_strip.py`
covering `_strip_think_tokens` directly:

- `test_strip_well_formed_think_block_removes_block_and_trims_leading_whitespace`
  - Input: `"<think>\nReasoning here.\n</think>\n\nActual response."`
  - Expected: `"Actual response."`
- `test_strip_well_formed_think_block_with_multiple_blocks`
  - Input: two `<think>...</think>` blocks separated by content; both
    are removed.
- `test_strip_unclosed_think_prefix_uses_blank_line_delimiter`
  - Input: `"<think>\nReasoning with no close tag.\n\nActual response."`
  - Expected: `"Actual response."`
- `test_strip_passthrough_when_no_think_tags`
  - Input: `"Plain tutoring response with no reasoning preamble."`
  - Expected: input returned unchanged (no spurious whitespace edits
    beyond what `lstrip()` would do on a clean string).

(The above four cases satisfy the task brief: `(a)` well-formed,
`(b)` unclosed at start, `(c)` whitespace cleanup, plus the passthrough
case.)

## Acceptance Criteria

- [ ] Module-private helper `_strip_think_tokens` added to
      [src/study_tutor/tutoring/adapters/llm_player_adapter.py](src/study_tutor/tutoring/adapters/llm_player_adapter.py).
- [ ] `LLMPlayerAdapter.respond()` wraps its returned LLM output through
      `_strip_think_tokens(...)` before returning.
- [ ] `LLMPlayerAdapter.revise()` wraps its returned LLM output through
      `_strip_think_tokens(...)` before returning.
- [ ] No edit to `src/study_tutor/llm/client.py` — sanitisation lives
      strictly in the Player adapter (Coach path must remain unaffected).
- [ ] New test file `tests/unit/tutoring/adapters/test_llm_player_adapter_strip.py`
      exists with the four cases above; all pass.
- [ ] `pytest tests/unit/tutoring/adapters/ -x` passes.
- [ ] `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
      passes (FEAT-6CC5 smoke gate — no regression in existing Player
      adapter behaviour).
- [ ] **Manual verification**: restart Claude Desktop, run
      `tutor_start_session` then `tutor_turn` against
      `http://promaxgb10-41b1:9000` with the Macbeth scenario; the
      `tutor_response` field on the returned envelope must contain no
      `<think>` text and no internal-reasoning preamble across at least
      5 consecutive turns.

## Reproduction Evidence (session `c78a49a0`, 2026-05-06)

- **Turn 1**: `<think>\nThe student is asking about Lady Macbeth's
  ambition in Macbeth. This relates to AO1...`
- **Turn 4**: similar `<think>` preamble.
- **Turn 5**: `<think>\nThe student is analyzing Lady Macbeth's
  invocation of the spirits...\n</think>\n\nThat's a really strong
  insight!...`

Cases 1 and 4 are the "unclosed tag" pathology (`</think>` truncated by
the model); case 5 is the well-formed pair. The implementation must
handle both.

## Out of Scope

- Any change to `LLMClient` or its OpenAI-compat helper.
- Any change to the Coach adapter or Coach prompt — Coach output is not
  routed through this stripping helper.
- Any prompt-engineering attempt to suppress `<think>` emission at the
  model side. The model is fine-tuned to emit reasoning; we sanitise on
  the consumer side rather than try to retrain the prompt.
- Stripping other reasoning-style tags (`<reasoning>`, `<scratchpad>`,
  etc.) — only `<think>` is observed in production output today.
  Adding speculative tag handling is YAGNI.

## Implementation Notes

- The helper is intentionally module-private (`_strip_think_tokens`)
  rather than class-attached: it is a pure string transform with no
  adapter state, and direct importability simplifies the unit tests.
- Use `re.DOTALL` on the `<think>...</think>` regex so multiline
  reasoning is captured. `re.IGNORECASE` is cheap insurance against
  the model emitting `<Think>` or `<THINK>` (not observed but trivially
  defended).
- The unclosed-tag heuristic (strip-to-blank-line) is the Hippocratic
  choice: if no `\n\n` exists in the output, we are in pathological
  territory and should prefer to drop the dangling `<think>` marker
  alone rather than blank the entire turn — leaking the marker without
  reasoning is less harmful than returning an empty `tutor_response`.

## Test Execution Log

### Automated (2026-05-06)

- `pytest tests/unit/tutoring/adapters/test_llm_player_adapter_strip.py -v`
  → **4/4 passed** (the four cases specified in this brief).
- `pytest tests/unit/tutoring/adapters/ -x`
  → **40/40 passed** (no regression in existing Player or Coach adapter tests).
- `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
  → **3 passed, 1 skipped** (FEAT-6CC5 smoke gate — skip is unrelated).

### Manual MCP verification (2026-05-06, user-confirmed)

5 consecutive Macbeth turns against `http://promaxgb10-41b1:9000`:

| Turn | `<think>` present? | Duration (s) | Decision |
|------|--------------------|--------------|----------|
| 1    | ✅ No              | 35.3         | fallback |
| 2    | ✅ No              | 9.5          | accept   |
| 3    | ✅ No              | 12.1         | fallback |
| 4    | ✅ No              | 11.5         | accept   |
| 5    | ✅ No              | 13.3         | fallback |

Zero `<think>` token leakage across all five turns.

### Out-of-scope observation (separate task)

Turn 1 of the verification session showed Coach meta-commentary
(`"I've reviewed your response and identified that... Here's a revised
version..."`) leaking into `tutor_response` on the **fallback** path.
This is unrelated to `<think>` stripping — it points at the revise/
fallback path concatenating Coach evaluation text into the Player's
turn output. Worth a follow-up diagnostic task on the Coach→Player
revise loop; not in scope for TASK-PTS-001.
