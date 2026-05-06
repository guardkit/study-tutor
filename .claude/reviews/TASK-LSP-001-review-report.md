# Review Report: TASK-LSP-001

**Task**: Route Player provider through llama-swap (OpenAI-compat) instead of Ollama `/api/generate`
**Mode**: decision (architectural)
**Depth**: standard
**Date**: 2026-05-06
**Reviewer**: /task-review

---

## Revision History

- **2026-05-06 (v1)**: Initial recommendations: D1=C (`local-player`), D2=B (alias),
  with `.env` / `.env.example` / `mcp-wrapper.sh` updates as part of TASK-LSP-002.
- **2026-05-06 (v2 — this revision, [R]evise round)**: Operator constraint —
  "we already have TASK-LCN-001 for env vars; either fold all of this into
  this review or leave the env variables alone." Revised to **leave env
  variables alone**. The Python-only change is sufficient to unblock the
  Player because D2-B aliases `provider="local"` (the value already on disk
  in `.env`) through `/v1/chat/completions`. This made D1=C's `local-player`
  a parallel name nothing actually configures, so D1 flips to **B (mutate
  `local` body)** for a single-name end state. F2 (stale `.env` comments)
  is moved out of TASK-LSP-002 scope and is now naturally owned by whoever
  next touches `.env` — which is TASK-LCN-001's territory. **No env files
  are modified by TASK-LSP-002.**

---

## Executive Summary

The Player path in [src/study_tutor/llm/client.py:107-113](src/study_tutor/llm/client.py#L107-L113) hits Ollama's native `/api/generate`, which the deployed llama-swap host on the GB10 does not expose — so every `tutor_turn` call 404s. The Coach path already uses `_generate_openai_compat` against `/v1/chat/completions` and works. The fix is mechanically small. After the revision round, the chosen decisions deliberately sidestep TASK-LCN-001's env-var rename so the two tasks do not overlap.

**Recommended decisions (revised)**:

| | Decision | Choice | One-line rationale |
|---|---|---|---|
| D1 | Player provider name | **B — mutate `local` body** | Single-name end state. No `.env` change needed because the deployed value is already `AGENT_MODELS__REASONING_MODEL=local`. No parallel `local-player` name nothing configures. |
| D2 | Back-compat for `provider="local"` | **B — route through `_generate_openai_compat`** | Same change as D1-B — they collapse into one decision. The `local` branch's body is replaced with a delegation to the existing OpenAI-compat helper; `_generate_ollama` is deleted. |
| D3 | Sequencing vs TASK-LCN-001 | **A — this task first** | Player is 404'ing now; rename is cosmetic. Unblock first. |
| D4 | `OLLAMA_BASE_URL` shared fallback | **A — keep, with docstring note** | Single-host setup is the documented Phase-1 reality; tightening can ride with TASK-LCN-001. |
| D5 | Test additions | **Wire-shape migration only** | Existing wire-shape assertions in `test_provider_resolution.py` migrate from Ollama-native to OpenAI-compat shape; no new test files. The "new provider name" test (#1) and "error enum" test (#2) drop because no new provider name is introduced. The D3-positive invariant test (#4) and SR-03 forbidden-tuple update (#5) also drop for the same reason. |

**D3 invariant check**: `local` ≠ `local-coach` (string-equal comparison at [factory.py:385](src/study_tutor/tutoring/coach/factory.py#L385)) → invariant satisfied. The check is identical to today's deployed state, so there is no regression risk on this axis.

**Files touched by TASK-LSP-002 under this revision**:

- [src/study_tutor/llm/client.py](src/study_tutor/llm/client.py)
- [tests/unit/llm/test_provider_resolution.py](tests/unit/llm/test_provider_resolution.py)

**Files NOT touched** (out of scope, owned elsewhere):

- `.env`, `.env.example` — owned by TASK-LCN-001 (rename) and the operator
- `scripts/mcp-wrapper.sh` — default `local` keeps working unchanged
- All `AGENT_MODELS__*` values — keep current settings

**Score**: 86/100 (up from 82/100 in v1) — tighter scope, zero overlap with TASK-LCN-001, smaller diff, fewer test additions, same runtime fix.

---

## Findings

### F1 — `_generate_ollama` targets an endpoint the deployment does not expose

[client.py:178](src/study_tutor/llm/client.py#L178) POSTs to `{base_url}/api/generate`. With `.env` set to `OLLAMA_BASE_URL=http://promaxgb10-41b1:9000` (llama-swap), this returns 404 for every Player call. The Coach path on [client.py:131-136](src/study_tutor/llm/client.py#L131-L136) already routes through `_generate_openai_compat` and works against the same host. The asymmetry is the bug.

### F2 — `.env` comment block is stale and reinforces the bug

[.env](/.env) line ~12 says:

> "Player provider: Mac Ollama (gcse-tutor fine-tune)"

…immediately above `OLLAMA_BASE_URL=http://promaxgb10-41b1:9000`. The host is llama-swap, not Mac Ollama. The Coach block (~line 17) calls llama-swap's endpoint "Ollama-compatible /api/generate" — that is wrong; per the operator's verified `curl /v1/models`, llama-swap exposes only `/v1/chat/completions`. These comments don't break code, but they encode the same misconception this task is fixing.

**Recommendation (revised)**: ~~include a one-line `.env` comment fix in
the follow-up task's diff~~. Per [R]evise feedback, all `.env` editing
is owned by TASK-LCN-001 to avoid task overlap. The comment fix is
cheap to roll into TASK-LCN-001 (which already rewrites this region of
`.env` and `.env.example`) and is **out of TASK-LSP-002's scope**.

### F3 — Naming choice interacts with TASK-LCN-001 in a load-bearing way

TASK-LCN-001 ([file](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md)) renames `OLLAMA_*` → `LOCAL_*` and `_generate_ollama` → `_generate_local`. The provider name discriminator (`AGENT_MODELS__REASONING_MODEL=local`) is **not** renamed by that task — `local` is "the right abstraction" per its rationale. Consequences for D1:

- Option A (`llama-swap`): TASK-LCN-001 renames `OLLAMA_*` → `LOCAL_*`. The provider name `llama-swap` then disagrees with both the env-var prefix (`LOCAL_*`) and the method name (`_generate_local`). Naming churn — bad.
- Option B (mutate `local` body): keeps a single name forever. But TASK-LCN-001 keeps `local` as the primary provider name, so picking B and then having TASK-LCN-001 also keep `local` produces the cleanest end state. Only cost: today the wire shape under `provider="local"` changes.
- Option C (`local-player`): introduces a parallel name to `local-coach`. TASK-LCN-001 doesn't touch provider name strings, so C survives that rename intact. Pattern-symmetric with the already-shipped Coach.
- Option D (`openai-compat`): conflates provider role with wire protocol. Future hosts speaking the same wire protocol would have no name to take.

C is the recommended default in the task file. **B is also defensible** and is the genuinely simpler end state — see the alternative below in D1.

### F4 — D2 + D1 interact: `provider="local"` cannot keep its current wire shape if `.env` already points at llama-swap

The current state on disk:

- `AGENT_MODELS__REASONING_MODEL=local` ([.env](/.env))
- `OLLAMA_BASE_URL=http://promaxgb10-41b1:9000` ([.env](/.env))
- `LLMClient(provider="local")` → `_generate_ollama` → 404

So the present-day "back-compat" for `provider="local"` is *broken back-compat*. The Mac-Ollama interpretation of "preserve `/api/generate` for `local`" only protects callers who set `OLLAMA_BASE_URL` to a real Ollama host. This is fine for unit tests using mocked `httpx.post` (the only callers that currently care about the wire shape are [tests/unit/llm/test_provider_resolution.py:60-104](tests/unit/llm/test_provider_resolution.py#L60-L104)), but it is **not** fine for the deployed configuration.

D2-B (alias `local` → openai-compat) reflects this reality and avoids leaving a wire path that 404s in the deployment. It does require updating those unit tests' wire-shape assertions.

### F5 — `_generate_openai_compat` falls back to `OLLAMA_BASE_URL` even when the role-specific URL exists

[client.py:209-213](src/study_tutor/llm/client.py#L209-L213):

```python
base_url = (
    os.environ.get(base_url_env)
    or os.environ.get("OLLAMA_BASE_URL")
    or DEFAULT_OLLAMA_BASE_URL
)
```

With this task complete, **both** Player and Coach helpers will hit this fallback chain. Today both providers want the same host, so the fallback is harmless. As soon as the Coach moves off the GB10 (Phase-2 calibration, or anyone setting `OLLAMA_COACH_BASE_URL` to an Anthropic-direct shim), an unset Player base URL silently inherits the Coach's host. That is the kind of failure mode operators chase for hours.

**This is a real smell, but it is also exactly what TASK-LCN-001 needs to touch**, since the fallback's env-var name (`OLLAMA_BASE_URL`) is itself being renamed. Tightening the fallback now means TASK-LCN-001 retouches the same lines a week later. **D4-A (keep) with a docstring note** is the right scope split.

### F6 — D3 invariant (ASSUM-LCA-009) is exact-string

The validation is a literal `==` comparison: [factory.py:385](src/study_tutor/tutoring/coach/factory.py#L385).

Any chosen Player provider name that is not the exact string `"local-coach"` satisfies it. All four D1 options are safe by name. The boot-time check raises `CoachConfigurationError` if violated, so a regression would surface immediately.

### F7 — SR-03 forbidden-token test (`test_adapter_handlers_do_not_reference_provider_string_literals`) *(N/A under revised D1=B)*

[test_provider_resolution.py:179-209](tests/unit/llm/test_provider_resolution.py#L179-L209) regexes for `["']{token}["']` over a list `('local', 'bedrock', 'openai', 'anthropic', 'gemini')`. Under v1's D1=C (`local-player`), this test would have needed an extra entry to preserve SR-03's contract under the new name.

Under **revised D1=B**, no new provider name is introduced — the contract continues to hold against the existing `local` token, and **no test change is required on this axis**. Finding kept in the report only as a note for any future revision that re-introduces a parallel provider name.

---

## Decisions (with rationale)

### D1 — Provider name → **B (mutate `local` body)** *(revised)*

Recommended because:

- **Zero env overlap with TASK-LCN-001.** The deployed value
  `AGENT_MODELS__REASONING_MODEL=local` keeps working unchanged. No
  `.env`, `.env.example`, or `mcp-wrapper.sh` edits in TASK-LSP-002.
- Single-name end state. One provider name (`local`) routed through
  one helper (`_generate_openai_compat`). No parallel `local-player`
  name that nothing actually configures.
- Aligned with TASK-LCN-001's stated semantic for `local`: "Mac
  Ollama, llama-swap, vLLM, any Ollama-compatible HTTP server" —
  i.e. `local` is already defined as protocol-agnostic at the
  rename task's documentation level. This decision just makes the
  code match that definition today.
- Smallest possible diff. One branch's body changes; one helper
  (`_generate_ollama`) is deleted.

**Defensible alternative — C (`local-player`) with env-free implementation**:
keep introducing `local-player` as a code-level branch parallel to
`local-coach`, but do **not** change `AGENT_MODELS__REASONING_MODEL` in
`.env`. The deployed `local` value continues to work via the alias.
The cost is a parallel name that is symmetric with `local-coach` but
that nothing currently configures — a slightly dead branch waiting to
be adopted. The benefit is the operator-readable `local-player` /
`local-coach` symmetry. If the operator wants the symmetry, this is
fine; the no-overlap rule is still satisfied because no env file is
edited under either choice. **Defaulting to B because the operator's
[R]evise feedback explicitly favoured tight scope and minimal
overlap, and B is the smaller, cleaner expression of that.**

**Why this is no longer C in v1's recommendation**: in v1, C's
attractiveness rested on `.env` adopting `local-player` so the
symmetric naming actually meant something at runtime. Once env edits
are off the table, C becomes "introduce a new branch nothing
configures and ride on the alias to `local`" — which is structurally
identical to B except with one more dead-ish name in the codebase.

### D2 — Back-compat for `provider="local"` → **B (route through `_generate_openai_compat`)** *(unchanged)*

Under D1=B, this is the same decision: the `local` branch's body
becomes a call to `_generate_openai_compat`. `_generate_ollama` is
deleted. The unit tests at
[test_provider_resolution.py:60-104](tests/unit/llm/test_provider_resolution.py#L60-L104)
need updating: assertions on `/api/generate` URL shape and
`body["prompt"]` shape become `/v1/chat/completions` URL and
`body["messages"]` shape. This is **not weakening** — it is reflecting
the contract correctly. The number of assertions stays the same.

Mac Ollama hosts also support `/v1/chat/completions`, so anyone
running real Ollama on `localhost:11434` keeps working without
re-configuration.

This is consistent with the operator's verbatim "no use of ollama for
this at all".

### D3 — Sequencing vs TASK-LCN-001 → **A (this task first)**

Recommended because:

- The Player is 404'ing in the deployed configuration **right now**. TASK-LCN-001 is a cosmetic rename with no runtime impact.
- This task creates the new provider branch using `OLLAMA_*` env vars (the names that exist on disk today). TASK-LCN-001 then renames those names alongside the Coach's in lockstep — exactly the rename it was already going to do.
- TASK-LCN-001's acceptance criteria do not require this task's outcome, so they remain satisfiable in either order.

### D4 — `OLLAMA_BASE_URL` shared fallback → **A (keep, with docstring note)**

Recommended because:

- The fallback is the documented Phase-1 single-host setup. Removing it now would break the Coach setup that just shipped under FEAT-6CC5.
- TASK-LCN-001 has to touch these exact lines to rename the env var. Tightening now means re-touching the same lines next.
- The sharp edge from F5 is real but bounded: it bites only when the Player and Coach hosts diverge, which is a Phase-2 event.

**Add a one-line docstring caveat** to `_generate_openai_compat` noting that two providers now share the fallback and that a Phase-2 cleanup is owned by TASK-LCN-001.

### D5 — Test additions → **Wire-shape migration only** *(revised)*

Under D1=B (mutate `local`), the original test list collapses:

- ~~New provider name routes to `/v1/chat/completions`.~~ — drops; no
  new provider name introduced.
- ~~Unsupported-provider error enumerates the new provider name.~~ —
  drops; the error enumeration is unchanged
  (`'local'`, `'local-coach'`, `'bedrock'`).
- **Wire-shape migration** of the existing tests at
  [test_provider_resolution.py:60-156](tests/unit/llm/test_provider_resolution.py#L60-L156):
  - `test_local_provider_posts_to_ollama_with_system_prompt` →
    rename or rewrite assertions: URL `/api/generate` →
    `/v1/chat/completions`; body `{prompt, system, options.num_predict}`
    → `{messages: [{role: system, ...}, {role: user, ...}], max_tokens}`.
  - `test_local_provider_omits_system_when_none` → asserts no
    system-role message is present in `messages`.
  - `test_local_provider_uses_env_num_predict_at_call_time` and
    `test_local_provider_falls_back_to_default_on_bad_num_predict`
    → assertions move from `body["options"]["num_predict"]` to
    `body["max_tokens"]`.
  - `test_local_provider_wraps_http_errors` → `match="Ollama request"`
    → `match="OpenAI-compat request"`.
- ~~D3-positive test for `local-player` / `local-coach` pairing.~~ —
  drops; the existing FEAT-6CC5 tests already cover `local` vs
  `local-coach`, which is the configuration that survives this task.
- ~~Add `'local-player'` to the SR-03 forbidden-tokens tuple.~~ —
  drops; no `local-player` literal is introduced.

No new test files are added. Assertion count stays the same; only the
wire shape and error string move. This is a true mechanical rewrite,
not a coverage change.

### D3 invariant check (ASSUM-LCA-009)

- Mechanism: exact-string `==` at [factory.py:385](src/study_tutor/tutoring/coach/factory.py#L385).
- Chosen Player name: `local` (unchanged from today).
- Coach name (already in `.env`): `local-coach`.
- `"local" == "local-coach"` → `False`. **Invariant holds.**
- Configuration is identical to today's deployed state on this axis,
  so there is no regression risk. Boot smoke check in
  `MCPAdapter.__init__` calls `validate_coach_config` and continues
  to pass.

---

## Recommendations (for follow-up implementation task) *(revised)*

**TASK-LSP-002 — Python-only Player wire-shape fix. No env changes.**

1. **Create TASK-LSP-002** in `tasks/backlog/` with prefix `LSP`.
   Reference TASK-LSP-001 in `related:`.
2. In [client.py:107-144](src/study_tutor/llm/client.py#L107-L144),
   replace the `local` branch's body with a call to
   `_generate_openai_compat(prompt, system, model_env="OLLAMA_MODEL", base_url_env="OLLAMA_BASE_URL")`.
3. Delete the `_generate_ollama` method
   ([client.py:146-189](src/study_tutor/llm/client.py#L146-L189)).
   Also delete the now-unused module-level constant
   `DEFAULT_OLLAMA_NUM_PREDICT` references inside `_generate_ollama`'s
   body (the constant itself is still used by `_generate_openai_compat`
   via `_resolve_num_predict`, so leave the top-level definition in
   place for TASK-LCN-001 to rename).
4. Update the unsupported-provider error message at
   [client.py:141-144](src/study_tutor/llm/client.py#L141-L144) only
   if the wording changes (the enumeration list does not change —
   still `'local', 'local-coach', 'bedrock'`).
5. Migrate the wire-shape assertions in
   [tests/unit/llm/test_provider_resolution.py:60-156](tests/unit/llm/test_provider_resolution.py#L60-L156)
   per D5 (revised) — same number of tests, OpenAI-compat shape, and
   error-string update from `"Ollama request"` to `"OpenAI-compat request"`.
6. Add a one-line docstring caveat to `_generate_openai_compat` per
   D4: "Both `local` and `local-coach` reach this helper after
   TASK-LSP-002; the `OLLAMA_BASE_URL` fallback at line 211 is
   therefore shared across providers — see TASK-LCN-001 for the
   eventual tightening." Pure documentation; no behaviour change.
7. Smoke gate: `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
   must remain green.
8. Full unit suite: `pytest tests/unit/llm/ -x` must pass.
9. Manual verification: Claude Desktop boot → `tutor_turn` happy path
   against `http://promaxgb10-41b1:9000`. **No `.env` edit required
   between v1 and v2.**

**Explicitly out of scope for TASK-LSP-002 (under [R]evise)**:

- Any change to `.env` — including `AGENT_MODELS__REASONING_MODEL`
  value, `OLLAMA_*` names/values, and comments. Owned by TASK-LCN-001
  and the operator.
- Any change to `.env.example`. Owned by TASK-LCN-001.
- Any change to `scripts/mcp-wrapper.sh`. The `local` default keeps
  working unchanged.
- The F2 stale-comment fix in `.env`. Naturally caught by TASK-LCN-001
  when it rewrites those comments around the renamed vars; left for
  that task to handle.
- Removing the `OLLAMA_BASE_URL` shared fallback in
  `_generate_openai_compat`. Owned by TASK-LCN-001 (D4 docstring note
  flags the issue).

---

## Context Used

No knowledge graph context was loaded (Graphiti unavailable in this session). Review is grounded in:

- [src/study_tutor/llm/client.py](src/study_tutor/llm/client.py) — full read
- [src/study_tutor/tutoring/coach/factory.py:380-391](src/study_tutor/tutoring/coach/factory.py#L380-L391) — D3 invariant mechanism
- [tests/unit/llm/test_provider_resolution.py](tests/unit/llm/test_provider_resolution.py) — existing test surface
- [tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md](tasks/backlog/TASK-LCN-001-rename-ollama-env-vars-to-provider-namespaced.md) — sequencing context
- [scripts/mcp-wrapper.sh](scripts/mcp-wrapper.sh) — boot path
- [.env](/.env) and [.env.example](/.env.example) — current configured state

---

## Decision Checkpoint

**Operator decision recorded: [I]mplement** (2026-05-06).

Follow-up implementation task created:
[tasks/backlog/TASK-LSP-002-route-local-player-through-openai-compat.md](tasks/backlog/TASK-LSP-002-route-local-player-through-openai-compat.md)

The v2 decisions (D1=B, D2=B, D3=A, D4=A, D5=wire-shape-migration) are
inlined into TASK-LSP-002's frontmatter (`review_decisions:`) and
acceptance criteria. TASK-LSP-001 stays in `tasks/in_review/` as the
audit trail and is closed out by `/task-complete TASK-LSP-001` once
TASK-LSP-002 is verified merged.

Suggested next command:
```
/task-work TASK-LSP-002
```
