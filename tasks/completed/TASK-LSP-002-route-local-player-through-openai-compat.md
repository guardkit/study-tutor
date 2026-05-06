---
id: TASK-LSP-002
title: Route Player provider through llama-swap (OpenAI-compat) — collapse `local` branch onto `_generate_openai_compat`
task_type: implementation
status: completed
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T15:45:00+00:00
completed: 2026-05-06T15:45:00+00:00
previous_state: in_review
complexity: 3
parent_review: TASK-LSP-001
related:
  - TASK-LSP-001
  - TASK-LCN-001
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-004
tags:
  - implementation
  - llm-config
  - provider-routing
  - llama-swap
  - bug-fix
  - feat_lca
context_files:
  - src/study_tutor/llm/client.py
  - tests/unit/llm/test_provider_resolution.py
  - tests/unit/mcp/test_adapter.py
  - tests/integration/test_mcp_lca_smoke.py
test_results:
  status: passed
  llm_unit: 15/15 passed
  feat_lca_smoke: 3 passed, 1 skipped (fixture-conditional)
  adapter_and_smoke: 20 passed, 1 skipped
  manual_verification: confirmed (Claude Desktop tutor_start_session + tutor_turn against http://promaxgb10-41b1:9000)
review_decisions:
  source: TASK-LSP-001 (v2)
  D1: B (mutate `local` body — single-name end state, no env edits)
  D2: B (route `local` through `_generate_openai_compat`; delete `_generate_ollama`)
  D3: A (this task first; TASK-LCN-001 second)
  D4: A (keep `OLLAMA_BASE_URL` shared fallback; add docstring caveat)
  D5: wire-shape migration of existing tests; no new test files
---

# Route Player provider through llama-swap (OpenAI-compat) — collapse `local` branch onto `_generate_openai_compat`

## Description

The Player path in
[src/study_tutor/llm/client.py:107-113](src/study_tutor/llm/client.py#L107-L113)
calls `_generate_ollama()` against `/api/generate` (Ollama's native
endpoint). The deployed inference stack has moved entirely to
**llama-swap on the GB10** (`promaxgb10-41b1:9000`, reachable over
Tailscale). llama-swap exposes only the OpenAI-compatible surface
(`/v1/chat/completions`); it does **not** serve `/api/generate`.
Result: every Player call from `tutor_turn` returns 404.

The Coach path already works because `local-coach` routes through
[`_generate_openai_compat()`](src/study_tutor/llm/client.py#L191-L246)
at `/v1/chat/completions`. This task gives the Player the same
treatment.

**Per the v2 review decisions on TASK-LSP-001 ([R]evise round)**, this
task is **Python-only**. No `.env`, `.env.example`, or
`scripts/mcp-wrapper.sh` edits — those are owned by TASK-LCN-001
(env-var rename) to avoid task overlap. The deployed value
`AGENT_MODELS__REASONING_MODEL=local` continues to work because the
`local` branch body is mutated to delegate to `_generate_openai_compat`.
The provider-name discriminator stays as `local`; only the wire
protocol that branch speaks changes.

## Why this approach (D1=B, mutate `local` body)

The v1 review recommended introducing a parallel `local-player`
provider name (D1=C) symmetric with the existing `local-coach`. The
operator's [R]evise feedback was: do not edit env vars in two tasks.
With env edits off the table, `local-player` would be a code-level
name nothing actually configures — it would ride on the alias to
`local` indefinitely.

D1=B (mutate `local`) is therefore cleaner under the no-overlap rule:

- Single provider name (`local`), single helper
  (`_generate_openai_compat`).
- Smallest possible diff. One branch's body changes; one helper
  (`_generate_ollama`) is deleted.
- TASK-LCN-001 already documents `local` as protocol-agnostic ("Mac
  Ollama, llama-swap, vLLM, any Ollama-compatible HTTP server"); this
  task makes the code match that definition.
- Mac Ollama hosts also expose `/v1/chat/completions`, so any
  single-host operator running real Ollama keeps working without
  re-configuration.

## Concrete changes

### `src/study_tutor/llm/client.py`

1. In
   [client.py:107-113](src/study_tutor/llm/client.py#L107-L113),
   replace the `local` branch's body with a delegation:
   ```python
   if self.provider == "local":
       return self._generate_openai_compat(
           prompt,
           system,
           model_env="OLLAMA_MODEL",
           base_url_env="OLLAMA_BASE_URL",
       )
   ```
2. Delete the `_generate_ollama` method
   ([client.py:146-189](src/study_tutor/llm/client.py#L146-L189)) and
   its lazy `httpx` import inside that method body. Leave the
   module-level constant `DEFAULT_OLLAMA_BASE_URL` and
   `DEFAULT_OLLAMA_MODEL` in place — they are still used by
   `_generate_openai_compat` and will be renamed by TASK-LCN-001
   alongside the env vars.
3. Add a one-line docstring caveat to `_generate_openai_compat` per
   D4 (single sentence, after the existing docstring):
   > Note: after TASK-LSP-002 both `local` and `local-coach`
   > providers reach this helper, so the `OLLAMA_BASE_URL` fallback at
   > line 211 is shared across providers. TASK-LCN-001 owns the
   > eventual tightening alongside the `OLLAMA_*` → `LOCAL_*` rename.
4. Leave the unsupported-provider error message at
   [client.py:141-144](src/study_tutor/llm/client.py#L141-L144)
   unchanged. The enumerated names (`'local', 'local-coach',
   'bedrock'`) are still correct.

### `tests/unit/llm/test_provider_resolution.py` — wire-shape migration

Migrate existing assertions so they reflect the new wire shape under
`provider="local"`. **No new test files; assertion count stays the
same.**

- [`test_local_provider_posts_to_ollama_with_system_prompt`](tests/unit/llm/test_provider_resolution.py#L60):
  - URL `/api/generate` → `/v1/chat/completions`.
  - Body assertions:
    - `body["model"] == "gcse-tutor-test"` (unchanged).
    - `body["prompt"]` / `body["system"]` → assert the messages list:
      `body["messages"] == [{"role": "system", "content": "You are a tutor."},
      {"role": "user", "content": "Explain the dagger speech."}]`.
    - `body["stream"] is False` (unchanged).
    - `body["options"]["num_predict"] == 2048` →
      `body["max_tokens"] == 2048`.
  - Rename test to `test_local_provider_posts_openai_compat_with_system_prompt`
    or similar (keep grep-discoverable).
- [`test_local_provider_omits_system_when_none`](tests/unit/llm/test_provider_resolution.py#L91):
  assert no message with `role == "system"` is in `body["messages"]`
  (i.e. the messages list contains only the user message). Rename
  optional.
- [`test_local_provider_uses_env_num_predict_at_call_time`](tests/unit/llm/test_provider_resolution.py#L107):
  `body["options"]["num_predict"] == 512` →
  `body["max_tokens"] == 512`.
- [`test_local_provider_falls_back_to_default_on_bad_num_predict`](tests/unit/llm/test_provider_resolution.py#L128):
  same migration — `body["options"]["num_predict"] == 2048` →
  `body["max_tokens"] == 2048`.
- [`test_local_provider_wraps_http_errors`](tests/unit/llm/test_provider_resolution.py#L147):
  `match="Ollama request"` → `match="OpenAI-compat request"`.

### Tests that stay unchanged

- `test_agent_models_reasoning_model_format` — provider-resolution
  contract; no wire-shape coupling.
- `test_bedrock_provider_raises_not_implemented` — Bedrock branch
  untouched.
- `test_unsupported_provider_raises_llm_provider_error` —
  enumeration unchanged.
- `test_no_module_level_client_instantiation` — SR-03 source check.
- `test_adapter_handlers_do_not_reference_provider_string_literals` —
  no new provider-name literal is added, so the forbidden-tokens
  tuple does not need updating.

## Acceptance Criteria

- [ ] `_generate_ollama` is deleted from
      [src/study_tutor/llm/client.py](src/study_tutor/llm/client.py).
- [ ] The `local` branch body in `LLMClient.generate` calls
      `_generate_openai_compat` with `model_env="OLLAMA_MODEL"`,
      `base_url_env="OLLAMA_BASE_URL"`.
- [ ] `_generate_openai_compat` has a one-line docstring note about
      the shared `OLLAMA_BASE_URL` fallback (D4).
- [ ] `tests/unit/llm/test_provider_resolution.py` wire-shape
      assertions migrated per the list above; assertion count
      unchanged.
- [ ] `pytest tests/unit/llm/ -x` passes.
- [ ] `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
      passes (FEAT-6CC5 smoke gate).
- [ ] **Manual verification**: stop Claude Desktop, restart it, run
      `tutor_start_session` and `tutor_turn`; both must succeed
      end-to-end against `http://promaxgb10-41b1:9000`. **No `.env`
      edit required.**
- [ ] All modified files pass project lint/format checks with zero
      errors.

## Out of Scope (per TASK-LSP-001 v2 review — owned by TASK-LCN-001)

- Any edit to `.env` — including `AGENT_MODELS__REASONING_MODEL`
  value, `OLLAMA_*` names/values, and the F2 stale-comment fix
  ("Player ... Mac Ollama" / "Ollama-compatible /api/generate"
  comments above the `OLLAMA_*` blocks).
- Any edit to `.env.example`.
- Any edit to `scripts/mcp-wrapper.sh` — the existing `local` default
  in line 25 keeps working unchanged.
- Renaming the module-level `DEFAULT_OLLAMA_*` constants. TASK-LCN-001
  renames these to `DEFAULT_LOCAL_*` alongside the env-var rename.
- Removing the `OLLAMA_BASE_URL` shared fallback in
  `_generate_openai_compat`. D4-A keeps it; the docstring caveat
  flags the issue for TASK-LCN-001 to tighten.
- Introducing a parallel `local-player` provider name. D1=B chose the
  single-name end state; if a future operator wants the symmetric
  `local-player` / `local-coach` naming, that is a separate
  consideration (and would have to be coordinated with TASK-LCN-001's
  env-var pattern).

## Test Requirements

- Test parity with the existing `test_provider_resolution.py`
  coverage — only wire shape and one error string move; no test is
  deleted or weakened.
- No new test files. The "new provider name" / "error enumeration" /
  "D3 positive" / "SR-03 forbidden tuple" tests proposed in the v1
  review do **not** apply under D1=B because no new provider name is
  introduced (see TASK-LSP-001 v2 D5 for the dropped list).

## Implementation Notes

### Why `_generate_openai_compat`'s `model_env` argument is `OLLAMA_MODEL` (not a renamed value)

This task uses the env-var names that exist on disk **today**
(`OLLAMA_MODEL`, `OLLAMA_BASE_URL`). TASK-LCN-001 will rename those
to `LOCAL_MODEL` / `LOCAL_BASE_URL` in lockstep with the Coach's vars
in a separate commit. Sequencing is intentional (per D3-A): unblock
the runtime first, rename second.

### Why `_generate_ollama` is deleted (not kept as dead code)

Per the operator's verbatim "no use of ollama for this at all" — and
per D2-B in the review — there is no caller that benefits from the
Ollama-native code path remaining in the codebase. The `provider="local"`
surface is preserved by aliasing to `_generate_openai_compat`; the
old method's body has no remaining users. Deleting it removes the
"this provider talks Ollama-native" misconception from the file.

### D3 invariant (ASSUM-LCA-009)

- Player provider name: `local` (unchanged).
- Coach provider name: `local-coach` (already in `.env`).
- `"local" == "local-coach"` → `False`. Invariant holds at boot per
  `validate_coach_config` in
  [src/study_tutor/tutoring/coach/factory.py:385](src/study_tutor/tutoring/coach/factory.py#L385).
- This is identical to the deployed configuration on this axis, so
  no regression risk on D3.

## Test Execution Log

### 2026-05-06 — /task-work TASK-LSP-002 (intensity=minimal, complexity=3, parent_review=TASK-LSP-001)

**Implementation diff** (Python-only, per D1=B / D2-B / D4-A):

- `src/study_tutor/llm/client.py`
  - `LLMClient.generate` `local` branch body: `_generate_ollama(...)` →
    `_generate_openai_compat(prompt, system, model_env="OLLAMA_MODEL",
    base_url_env="OLLAMA_BASE_URL")`.
  - Deleted `_generate_ollama` method (was lines 146–189 pre-edit) including
    its lazy `httpx` import. Module-level `DEFAULT_OLLAMA_*` constants kept
    (still used by `_generate_openai_compat`; TASK-LCN-001 will rename them
    alongside the env-var rename).
  - Added a four-line docstring caveat to `_generate_openai_compat` (D4)
    flagging that after TASK-LSP-002 both `local` and `local-coach` reach
    this helper, so the `OLLAMA_BASE_URL` shared fallback is now
    cross-provider; tightening is owned by TASK-LCN-001.
  - Unsupported-provider error message at the bottom of `generate` left
    untouched — enumeration `'local', 'local-coach', 'bedrock'` is still
    correct.

- `tests/unit/llm/test_provider_resolution.py` (wire-shape migration; assertion
  count unchanged):
  - `test_local_provider_posts_to_ollama_with_system_prompt` →
    `test_local_provider_posts_openai_compat_with_system_prompt`. URL
    assertion `/api/generate` → `/v1/chat/completions`. Body assertions
    moved from `prompt`/`system`/`options.num_predict` to a literal
    `messages` list assertion (`[{system}, {user}]`) plus
    `body["max_tokens"] == 2048`. Mock JSON shape changed from
    `{"response": "..."}` to OpenAI-compat
    `{"choices": [{"message": {"content": "..."}}]}`.
  - `test_local_provider_omits_system_when_none`: assert no message with
    `role == "system"` is in `body["messages"]` and the list contains only
    the user message. Mock JSON updated to OpenAI-compat shape.
  - `test_local_provider_uses_env_num_predict_at_call_time`:
    `body["options"]["num_predict"] == 512` → `body["max_tokens"] == 512`.
    Mock JSON updated to OpenAI-compat shape.
  - `test_local_provider_falls_back_to_default_on_bad_num_predict`:
    `body["options"]["num_predict"] == 2048` → `body["max_tokens"] == 2048`.
    Mock JSON updated to OpenAI-compat shape.
  - `test_local_provider_wraps_http_errors`: `match="Ollama request"` →
    `match="OpenAI-compat request"`.

- Tests untouched (per the task's explicit list): `test_agent_models_reasoning_model_format`,
  `test_bedrock_provider_raises_not_implemented`,
  `test_unsupported_provider_raises_llm_provider_error`,
  `test_no_module_level_client_instantiation`,
  `test_adapter_handlers_do_not_reference_provider_string_literals`.

**Test runs:**

- `pytest tests/unit/llm/ -x` → **15 passed in 0.11s** ✓ (AC item 5).
- `pytest -m "feat_lca and smoke" tests/unit tests/integration -x` →
  **3 passed, 1 skipped, 840 deselected in 1.14s** ✓ (AC item 6 — FEAT-6CC5
  smoke gate; the skip is a fixture-conditional case in
  `test_mcp_lca_smoke.py`, not a regression introduced by this task).
- Cross-check: `pytest tests/unit/mcp/test_adapter.py
  tests/integration/test_mcp_lca_smoke.py -x` → **20 passed, 1 skipped**
  ✓ — confirms the SR-03 forbidden-tokens regex
  (`test_adapter_handlers_do_not_reference_provider_string_literals`) still
  passes (no new provider literal added).
- `grep -rn "_generate_ollama" src/ tests/` → **no matches** ✓ (AC item 1).

**ACs met deterministically:**

- [x] AC1 — `_generate_ollama` deleted from `client.py` (grep above).
- [x] AC2 — `local` branch calls `_generate_openai_compat` with
  `model_env="OLLAMA_MODEL"`, `base_url_env="OLLAMA_BASE_URL"`.
- [x] AC3 — `_generate_openai_compat` docstring carries the D4 caveat.
- [x] AC4 — wire-shape migrations applied per the task list; assertion count
  per migrated test unchanged.
- [x] AC5 — `pytest tests/unit/llm/ -x` passes.
- [x] AC6 — `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
  passes.
- [x] AC8 — project has no `[tool.ruff]` / `[tool.black]` / `[tool.mypy]`
  configuration in `pyproject.toml`, so "passes lint/format checks with
  zero errors" is vacuously satisfied; the file imports cleanly under
  `pytest`'s collection step (Python 3.14.2).

**Pending operator action (AC7):**

- [ ] Manual verification — stop Claude Desktop, restart it, run
  `tutor_start_session` and `tutor_turn` against
  `http://promaxgb10-41b1:9000`. **No `.env` edit required**: the deployed
  `AGENT_MODELS__REASONING_MODEL=local` continues to work because the
  `local` branch body is now an OpenAI-compat call (D1=B). This task is
  in IN_REVIEW pending that confirmation.

**Out-of-scope items confirmed untouched** (owned by TASK-LCN-001):
`.env`, `.env.example`, `scripts/mcp-wrapper.sh`, `DEFAULT_OLLAMA_*` constant
names, the `OLLAMA_BASE_URL` shared fallback, and any `local-player`
provider name introduction.
