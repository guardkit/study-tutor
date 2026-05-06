---
id: TASK-LSP-001
title: Review — route Player provider through llama-swap (OpenAI-compat) instead of Ollama /api/generate
task_type: review
status: review_complete
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T00:00:00+00:00
complexity: 4
decision_required: true
review_mode: decision
review_depth: standard
tags:
  - review
  - architecture-review
  - decision-point
  - llm-config
  - provider-routing
  - llama-swap
related:
  - TASK-LCN-001
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-004
context_files:
  - src/study_tutor/llm/client.py
  - src/study_tutor/cli/main.py
  - tests/unit/llm/test_provider_resolution.py
  - tests/unit/tutoring/adapters/test_llm_player_adapter.py
  - tests/unit/mcp/test_stdio_discipline.py
  - tests/unit/mcp/test_adapter.py
  - tests/integration/test_mcp_lca_smoke.py
  - .env
  - .env.example
  - scripts/mcp-wrapper.sh
test_results:
  status: pending
review_results:
  mode: decision
  depth: standard
  score: 86
  findings_count: 7
  recommendations_count: 9
  revisions: 2
  decision: implement
  followup_task: TASK-LSP-002
  report_path: .claude/reviews/TASK-LSP-001-review-report.md
  completed_at: 2026-05-06T00:00:00+00:00
  revision_notes: >-
    v2 ([R]evise): operator constraint — TASK-LCN-001 owns env-var work;
    no overlap. Revised D1 from C (local-player) to B (mutate local body).
    TASK-LSP-002 is now Python-only; no edits to .env, .env.example, or
    scripts/mcp-wrapper.sh. Test additions collapsed to wire-shape
    migration of the existing test_provider_resolution.py assertions.
---

# Review — route Player provider through llama-swap (OpenAI-compat) instead of Ollama /api/generate

## Description

The Player path in [src/study_tutor/llm/client.py:107-113](src/study_tutor/llm/client.py#L107-L113)
calls `_generate_ollama()` against `/api/generate` (Ollama's native endpoint).
That worked when the Player ran against Mac Ollama on `localhost:11434`.

The deployed inference stack has now moved entirely to **llama-swap on the GB10**
(`promaxgb10-41b1:9000`, reachable over Tailscale). llama-swap exposes only the
OpenAI-compatible surface (`/v1/chat/completions`); it does **not** serve
`/api/generate`. Result: every Player call from `tutor_turn` returns 404.

The Coach path already works because `local-coach` routes through
[`_generate_openai_compat()`](src/study_tutor/llm/client.py#L191-L246) at
`/v1/chat/completions`. The fix is to give the Player an analogous wiring.

The operator has stated (problem statement, verbatim):

> "All models are hosted via lama-swap on the GB10 over tailscale; there should
> be no use of ollama for this at all."

This is a **review task** because the proposed implementation has several
naming and scope choices that interact with an already-queued refactor
([TASK-LCN-001](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md))
and with the D3 two-provider invariant (ASSUM-LCA-009). We need to make
those decisions explicitly before opening an implementation task.

## Problem Statement (verbatim from operator)

```
Location: study-tutor repo, src/study_tutor/llm/client.py

What happened: The local provider in LLMClient.generate() calls
_generate_ollama() which hits /api/generate (Ollama's native endpoint).
This was fine when the Player ran against Mac Ollama on localhost:11434.
Now that all inference has moved to llama-swap on GB10
(promaxgb10-41b1:9000), the Player gets a 404 because llama-swap only
exposes /v1/chat/completions (OpenAI-compat), not /api/generate.

The Coach (local-coach provider) already works — it uses
_generate_openai_compat() which hits /v1/chat/completions.

Constraint: llama-swap does NOT expose /api/generate. Only
/v1/chat/completions is available.

Verified working:
  curl http://promaxgb10-41b1:9000/v1/models
  → gemma4-tutor, qwen36-workhorse, nomic-embed, qwen-graphiti,
    architect-agent

Env context (.env):
  OLLAMA_BASE_URL=http://promaxgb10-41b1:9000
  OLLAMA_MODEL=gemma4-tutor
  OLLAMA_COACH_BASE_URL=http://promaxgb10-41b1:9000
  OLLAMA_COACH_MODEL=qwen36-workhorse
```

The operator's proposed sketch:

1. `src/study_tutor/llm/client.py` — add a new provider string
   (e.g. `llama-swap`) that routes through `_generate_openai_compat()`
   using the Player's env vars (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`).
   The D3 invariant requires the provider name to differ from
   `local-coach`. Update the unsupported-provider error to mention it.
2. `.env` — switch `AGENT_MODELS__REASONING_MODEL` from `local` to the
   new provider name.
3. `scripts/mcp-wrapper.sh` — update the fallback default to match.
4. `.env.example` — document the new provider option.
5. Tests — keep existing `LLMClient(provider="local")` tests passing
   (backward compat); add a test for the new provider path.

## Why this is a review task (not /task-work)

The fix is small in lines of code, but it sits across three open
architectural questions. Implementing the operator's sketch directly
risks locking in a decision we will then immediately want to revisit.
The questions:

1. **Provider name choice.** `llama-swap` is technology-leaking in
   exactly the way [TASK-LCN-001](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md)
   identifies as a smell (the env-var rename motivation). If the new
   provider is named `llama-swap`, we will rename it again in TASK-LCN-001.
2. **Backward compat scope.** The operator says "no use of ollama for
   this at all". Strict reading: the `local`/`_generate_ollama` branch
   should be deleted. Sketch reading: keep it for back-compat. These
   are not the same task.
3. **Sequencing vs TASK-LCN-001.** TASK-LCN-001 already proposes
   `LOCAL_*` env vars and `_generate_local` method naming. If we
   sequence wrong, we ship a broken Player into a rename and either
   double-touch the file or leave a confusing intermediate state.
4. **D3 two-provider invariant.** The invariant needs the provider
   *names* to differ between Player and Coach. Player and Coach
   currently both point at the same physical llama-swap host. The
   invariant has been upheld by name, not by host. We need to make
   sure the new naming preserves that contract.
5. **Hidden coupling: `_generate_openai_compat`'s base-URL fallback.**
   That helper currently falls back to `OLLAMA_BASE_URL` when its
   role-specific env is unset. Two providers reading from a shared
   `OLLAMA_BASE_URL` is fine today (one host) but is exactly the
   single-host accident that future debugging will misdiagnose.

## Decisions required (review output)

The review must produce a decision on each of the following, with
rationale captured in this file's "Decisions" section:

### D1 — Provider name for the Player path

Pick one and record why:

| Option | Provider name | Trade-off |
|---|---|---|
| A | `llama-swap` | Operator's suggestion. Technology-leaking. Will be renamed by TASK-LCN-001. |
| B | `local` (mutate body) | Change `_generate_ollama` body to call `_generate_openai_compat` semantics. Single name. Breaks any test that asserts Ollama-native wire shape. Conflicts with strict reading of operator's "no Ollama at all". |
| C | `local-player` | Symmetric with `local-coach`. Role-naming, not technology-naming. Forward-compatible with TASK-LCN-001. |
| D | `openai-compat` | API-contract-named (matches the existing `_generate_openai_compat` helper). Provider-name == wire-protocol. Risk: when a real OpenAI provider lands, the name collides. |

**Recommended default: C (`local-player`).** It is symmetric with the
already-working `local-coach`, is technology-neutral (so TASK-LCN-001
will not need to rename it again), and unambiguously satisfies D3
(`local-player` ≠ `local-coach`). Confirm or override.

### D2 — Backward-compat for `provider="local"` / `_generate_ollama`

Pick one:

| Option | Behaviour | Trade-off |
|---|---|---|
| A | Keep `local` branch and `_generate_ollama` as-is | Operator's sketch. Lowest blast radius. Leaves dead code that next operator will assume works. |
| B | Keep `local` branch but route it through `_generate_openai_compat` (alias) | Single code path. Surface compat for any caller still passing `provider="local"`. Slightly surprising semantics (a "local" provider that doesn't talk Ollama-native). |
| C | Delete `local` branch and `_generate_ollama` | Strictest reading of "no use of ollama at all". Loud failure for any stale caller. Requires updating any test that constructs `LLMClient(provider="local")`. |

**Recommended default: B.** Keeps the back-compat surface the
operator's sketch asks for, but does not retain a code path that
hits an endpoint that no longer exists in the deployment. Makes
TASK-LCN-001's later cleanup smaller. Confirm or override.

### D3 — Sequencing vs TASK-LCN-001 (env-var rename)

Pick one:

| Option | Order | Trade-off |
|---|---|---|
| A | This task first, TASK-LCN-001 second | Unblocks the Player today. TASK-LCN-001 then renames both providers' env vars in lockstep. |
| B | TASK-LCN-001 first, this task second | Renames first, then wires the new provider against `LOCAL_*` env vars. Cleaner final state but Player stays broken until both land. |
| C | Merge into one combined task | One commit. Larger blast radius, harder to revert. |

**Recommended default: A.** The Player is currently 404'ing in
production-of-one (operator's local Claude Desktop). Unblock first,
rename second. The new provider in this task uses `OLLAMA_BASE_URL` /
`OLLAMA_MODEL` (the names that exist in `.env` today); TASK-LCN-001
then renames those names alongside the Coach's. Confirm or override.

### D4 — `OLLAMA_BASE_URL` fallback inside `_generate_openai_compat`

The helper falls back from its role-specific base-URL env to
`OLLAMA_BASE_URL` ([client.py:209-213](src/study_tutor/llm/client.py#L209-L213)).
After this task, both Player and Coach will use this helper, so two
providers read from the same fallback. Pick one:

| Option | Behaviour | Trade-off |
|---|---|---|
| A | Keep the fallback | Single-host setups continue to work without setting both base-URL envs. |
| B | Remove the fallback for the Player path | Forces explicit configuration. Silently-misconfigured Player can no longer accidentally inherit Coach's URL. |

**Recommended default: A** with a docstring note. The single-host
fallback is the documented Phase-1 setup. Removing it can wait for
TASK-LCN-001 (which already touches this surface). Confirm or override.

### D5 — Test additions

The implementation task must add at least:

- [ ] One unit test that constructs `LLMClient(provider=<chosen name>)`
      and asserts the request goes to `/v1/chat/completions` (not
      `/api/generate`).
- [ ] One unit test that the unsupported-provider error message
      includes the new provider name in its enumeration.
- [ ] One regression test that `LLMClient(provider="local")` still
      behaves per D2's chosen option (kept-Ollama-native, kept-as-alias,
      or removed-with-clear-error).

Existing call sites to keep green (verified via grep):

- [src/study_tutor/cli/main.py](src/study_tutor/cli/main.py)
- [tests/unit/llm/test_provider_resolution.py](tests/unit/llm/test_provider_resolution.py)
- [tests/unit/tutoring/adapters/test_llm_player_adapter.py](tests/unit/tutoring/adapters/test_llm_player_adapter.py)
- [tests/unit/mcp/test_stdio_discipline.py](tests/unit/mcp/test_stdio_discipline.py)
- [tests/unit/mcp/test_adapter.py](tests/unit/mcp/test_adapter.py)
- [tests/integration/test_mcp_lca_smoke.py](tests/integration/test_mcp_lca_smoke.py)

## Out of scope for this review

- Renaming `OLLAMA_*` env vars → `LOCAL_*`. Owned by [TASK-LCN-001](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md).
- Removing the `bedrock` branch.
- Generalising `LLMClient` to a registry-driven provider abstraction.
- Coach calibration / Phase-2 Coach work.
- Touching Graphiti's LLM extractor wiring.

## Acceptance Criteria (for the review itself)

- [ ] D1 (provider name) decided and rationale captured in the
      "Decisions" section below
- [ ] D2 (back-compat for `local` / `_generate_ollama`) decided and
      rationale captured
- [ ] D3 (sequencing vs TASK-LCN-001) decided and rationale captured
- [ ] D4 (single-host base-URL fallback) decided and rationale captured
- [ ] D5 test list confirmed (or amended) and recorded
- [ ] D3 two-provider invariant (ASSUM-LCA-009) explicitly checked
      against the chosen provider name; record the check result
- [ ] One follow-up implementation task is created in
      `tasks/backlog/` with prefix `LSP` (e.g. `TASK-LSP-002`),
      referencing this review's decisions in its frontmatter
      `related:` field
- [ ] If D3 is "merge with TASK-LCN-001", note that on TASK-LCN-001's
      file too so the rename task knows it has absorbed this work

## Review Method

1. Read the problem statement above and confirm the constraint
   (`/api/generate` not exposed by llama-swap) by re-reading the
   `curl http://localhost:9000/v1/models` evidence in the operator's
   message.
2. Re-read [src/study_tutor/llm/client.py](src/study_tutor/llm/client.py)
   end-to-end — both branches and both helpers — to make sure the
   review answers are grounded in the current code, not the sketch.
3. Re-read [TASK-LCN-001](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md)
   to confirm the sequencing decision in D3 doesn't contradict its
   acceptance criteria.
4. For each of D1–D5, walk through the listed options against the
   current state, pick one (or propose a sixth), and record the
   rationale and any open follow-up below.
5. Open the follow-up implementation task with the chosen decisions
   inlined into its acceptance criteria.

## Decisions

_Recorded by `/task-review` 2026-05-06.
Full rationale, revision history, and supporting findings in
[.claude/reviews/TASK-LSP-001-review-report.md](.claude/reviews/TASK-LSP-001-review-report.md).
Status: **pending operator checkpoint** ([A]ccept / [R]evise / [I]mplement / [C]ancel).
Currently on revision **v2** (post-[R]evise: env-vars stay out of TASK-LSP-002
to avoid overlap with TASK-LCN-001)._

### D1 — Provider name → **B (mutate `local` body)** *(revised v2)*

**v1 chose C (`local-player`); operator's [R]evise feedback flipped this to B
to avoid `.env` overlap with TASK-LCN-001.** The deployed value
`AGENT_MODELS__REASONING_MODEL=local` keeps working unchanged; the
Python change alone is sufficient to unblock the Player. Single-name
end state, no parallel `local-player` name that nothing actually
configures, smallest possible diff. Aligned with TASK-LCN-001's
own definition of `local` as protocol-agnostic ("Mac Ollama,
llama-swap, vLLM, any Ollama-compatible HTTP server"). Defensible
alternative — C (`local-player`) implemented env-free via the alias —
is preserved only as a future option if the operator wants the
operator-readable symmetry with `local-coach`; the v2 default is B.

### D2 — Backward compat → **B (route `local` through `_generate_openai_compat`)** *(unchanged in spirit, collapses with D1=B)*

Under D1=B this is the same decision: the `local` branch's body becomes
a call to `_generate_openai_compat`, and `_generate_ollama` is deleted.
Mac Ollama hosts also expose `/v1/chat/completions`, so any operator
running real Ollama keeps working without re-configuration. The wire-shape
assertions in
[tests/unit/llm/test_provider_resolution.py:60-156](tests/unit/llm/test_provider_resolution.py#L60-L156)
must be updated to the OpenAI-compat shape (`messages` / `max_tokens`
instead of `prompt` / `options.num_predict`); count of assertions does
not change. This is consistent with the operator's verbatim "no use of
ollama for this at all".

### D3 — Sequencing → **A (this task first, TASK-LCN-001 second)**

The Player is 404'ing in production-of-one **now**; TASK-LCN-001 is a
cosmetic rename. Unblock first, rename second. This task creates the
new provider branch using the `OLLAMA_*` env-var names that exist on
disk today; TASK-LCN-001 then renames those names alongside the
Coach's in lockstep, exactly the rename it was already going to do.
TASK-LCN-001's acceptance criteria are satisfiable in either order.

### D4 — Base-URL fallback → **A (keep, with docstring caveat)**

The shared-fallback smell (both Player and Coach reading
`OLLAMA_BASE_URL` when their role-specific URL is unset, see
[client.py:209-213](src/study_tutor/llm/client.py#L209-L213)) is real
but bounded — it bites only when the two providers' hosts diverge,
which is a Phase-2 event. Tightening it now would force TASK-LCN-001
to re-touch the same lines for the env-var rename. Add a one-line
docstring note to `_generate_openai_compat` flagging the shared
fallback; full tightening rides with TASK-LCN-001.

### D5 — Test additions → **Wire-shape migration only** *(revised v2)*

Under D1=B the original five-test list collapses to a mechanical
wire-shape rewrite of the existing assertions. No new test files; no
new provider-name surface to assert against. Same number of
assertions; only the wire shape and one error string move.

- [x] Migrate
      [`test_local_provider_posts_to_ollama_with_system_prompt`](tests/unit/llm/test_provider_resolution.py#L60):
      URL `/api/generate` → `/v1/chat/completions`; body
      `{prompt, system, options.num_predict}` →
      `{messages: [...], max_tokens}`.
- [x] Migrate
      [`test_local_provider_omits_system_when_none`](tests/unit/llm/test_provider_resolution.py#L91):
      assert no system-role message in `messages`.
- [x] Migrate
      [`test_local_provider_uses_env_num_predict_at_call_time`](tests/unit/llm/test_provider_resolution.py#L107)
      and
      [`test_local_provider_falls_back_to_default_on_bad_num_predict`](tests/unit/llm/test_provider_resolution.py#L128):
      assertions move from `body["options"]["num_predict"]` to
      `body["max_tokens"]`.
- [x] Migrate
      [`test_local_provider_wraps_http_errors`](tests/unit/llm/test_provider_resolution.py#L147):
      `match="Ollama request"` → `match="OpenAI-compat request"`.

**Dropped from v1 because there is no new provider name under D1=B**:

- ~~Unit test for `LLMClient(provider="local-player")` →
  `/v1/chat/completions`~~
- ~~Error-enumeration test for `local-player`~~
- ~~Positive D3 test for `local-player` × `local-coach` pairing
  (the existing FEAT-6CC5 tests already cover `local` × `local-coach`,
  which is the configuration that survives this task)~~
- ~~SR-03 forbidden-tokens tuple update (no `local-player` literal
  is introduced)~~

### D3 invariant check (ASSUM-LCA-009) — **passes** *(revised v2)*

- Mechanism: literal `==` at [factory.py:385](src/study_tutor/tutoring/coach/factory.py#L385).
- Player name: **`local`** (unchanged from today under revised D1=B).
- Coach name (already in `.env`): `local-coach`.
- `"local" == "local-coach"` → `False`. Invariant holds.
- Configuration is identical to the deployed state on this axis, so
  there is no regression risk. Boot smoke check in
  `MCPAdapter.__init__` calls `validate_coach_config` and continues
  to pass.

## Notes for the follow-up implementation task *(revised v2)*

When opening TASK-LSP-002, copy these into its acceptance criteria so
they cannot be missed:

- The `tutor_turn` happy path against the live llama-swap on the
  GB10 (`http://promaxgb10-41b1:9000`) must succeed end-to-end from
  Claude Desktop after the change. **No `.env` edit required** — the
  deployed `AGENT_MODELS__REASONING_MODEL=local` keeps working.
- `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
  must still pass (the FEAT-6CC5 smoke gate).
- `pytest tests/unit/llm/ -x` must pass after the wire-shape
  migration in `test_provider_resolution.py`.
- The unsupported-provider error message in `LLMClient.generate`
  enumerates `'local', 'local-coach', 'bedrock'` (unchanged from
  today; no new provider name added).
- `_generate_ollama` is deleted; the `local` branch's body calls
  `_generate_openai_compat` with `model_env="OLLAMA_MODEL"`,
  `base_url_env="OLLAMA_BASE_URL"`.

**Out of scope for TASK-LSP-002 (owned by TASK-LCN-001 to avoid
overlap, per operator's [R]evise feedback)**:

- Any edit to `.env` — including `AGENT_MODELS__REASONING_MODEL`
  value, `OLLAMA_*` names/values, and the F2 stale-comment fix.
- Any edit to `.env.example`.
- Any edit to `scripts/mcp-wrapper.sh` — the existing `local`
  default keeps working unchanged.
- Removing the `OLLAMA_BASE_URL` shared fallback in
  `_generate_openai_compat` (D4-A keeps it; a docstring note flags
  the issue for TASK-LCN-001).

## Test Execution Log

[Automatically populated by /task-review or /task-work]
