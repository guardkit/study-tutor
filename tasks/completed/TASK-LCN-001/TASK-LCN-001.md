---
id: TASK-LCN-001
title: Rename OLLAMA_* env vars to provider-namespaced LOCAL_* names
task_type: refactor
status: completed
priority: normal
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T12:30:00+00:00
completed: 2026-05-06T12:30:00+00:00
completed_location: tasks/completed/TASK-LCN-001/
complexity: 3
tags:
  - tech-debt
  - llm-config
  - refactor
  - naming
related:
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-004
context_files:
  - src/study_tutor/llm/client.py
  - tests/unit/llm/test_provider_resolution.py
  - .env
  - .env.example
  - scripts/mcp-wrapper.sh
  - scripts/graphiti_latency_spike.py
test_results:
  status: passed
  llm_unit: "15/15 passed (tests/unit/llm/)"
  feat_lca_smoke: "3 passed, 1 skipped (-m 'feat_lca and smoke')"
  full_unit_regression: "831/833 passed; 2 pre-existing failures unrelated to scope (test_graphiti_client_wiring.py::test_cross_encoder_sentinel_raises_on_arbitrary_method_name and test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule both fail identically on bare main with the rename stashed)"
---

# Rename OLLAMA_* env vars to provider-namespaced LOCAL_* names

## Description

The LLM config layer leaks an implementation-technology assumption that no
longer matches reality. Every env var, helper function, and constant in
`src/study_tutor/llm/client.py` is prefixed `OLLAMA_*` even though the
deployed stack now routes through **llama-swap** on the GB10 (Player gemma4
fine-tune is hosted on Mac Ollama, but the Coach `qwen36-workhorse`,
Graphiti's LLM extractor, and embeddings are all on llama-swap; vLLM has
been retired). The names misrepresent what the config actually selects, and
the misrepresentation will get worse as more roles get added.

The provider names in `AGENT_MODELS__*` (`local`, `local-coach`) are the
right abstraction. Per-provider config should mirror those names so each
provider owns its own config namespace. This task renames the
implementation-leaking `OLLAMA_*` vars to `LOCAL_*` / `LOCAL_COACH_*` so the
config layer aligns with the provider name pattern and doesn't lie about
the underlying inference technology.

This is a contained, mechanical refactor with good existing test coverage
in `tests/unit/llm/test_provider_resolution.py`. Low risk; the runtime
behaviour does not change.

## Why now (and why not earlier)

- The rename was deferred during FEAT-6CC5 (LLM Player and Coach Adapters)
  to avoid touching the Player path mid-feature.
- TASK-LCA-004 added `OLLAMA_COACH_*` vars under the same misleading
  prefix to maintain naming consistency with the existing `OLLAMA_*` vars
  rather than do a piecemeal rename.
- The post-FEAT-6CC5 wiring of Coach against the GB10 llama-swap exposed
  the naming as actively misleading: `OLLAMA_COACH_BASE_URL=http://promaxgb10-41b1:9000`
  is pointing at llama-swap, not Ollama. Future maintainers reading the
  env will be misled about what's running there.

## Out of scope

- Removing the `bedrock` provider branch from `LLMClient.generate`.
  Operator decision is to defer Bedrock indefinitely (llama-swap is
  serving fine), but pruning the branch is a separate decision; keep this
  task focused on the rename.
- Generalising `LLMClient` to a registry-driven provider abstraction.
  That's a bigger refactor; this task only renames existing surfaces.
- Updating `scripts/graphiti_latency_spike.py` comments that reference
  vLLM. Graphiti is now also on llama-swap, so those comments are stale —
  but the latency-spike script is observability, not runtime, and a
  separate cleanup task should handle it.
- Touching the Coach API contract (`/v1/chat/completions` vs
  `/api/generate`). The two methods stay distinct because they speak
  different wire formats — only their *names* and the env vars they read
  are in scope here.

## Concrete renames

### Env vars

| Old | New |
|---|---|
| `OLLAMA_BASE_URL` | `LOCAL_BASE_URL` |
| `OLLAMA_MODEL` | `LOCAL_MODEL` |
| `OLLAMA_NUM_PREDICT` | `LOCAL_NUM_PREDICT` |
| `OLLAMA_TIMEOUT_SECONDS` | `LOCAL_TIMEOUT_SECONDS` |
| `OLLAMA_COACH_BASE_URL` | `LOCAL_COACH_BASE_URL` |
| `OLLAMA_COACH_MODEL` | `LOCAL_COACH_MODEL` |

### Module-level constants in `src/study_tutor/llm/client.py`

| Old | New |
|---|---|
| `DEFAULT_OLLAMA_BASE_URL` | `DEFAULT_LOCAL_BASE_URL` |
| `DEFAULT_OLLAMA_MODEL` | `DEFAULT_LOCAL_MODEL` |
| `DEFAULT_OLLAMA_TIMEOUT_SECONDS` | `DEFAULT_LOCAL_TIMEOUT_SECONDS` |
| `DEFAULT_OLLAMA_NUM_PREDICT` | `DEFAULT_LOCAL_NUM_PREDICT` |

### Method names in `LLMClient`

| Old | New |
|---|---|
| `_generate_ollama(...)` | `_generate_local(...)` |
| `_generate_openai_compat(...)` | (unchanged — name is API-contract-accurate, not technology-leaking) |

### Internal references

- Inline fallback chain in both `_generate_local` and
  `_generate_openai_compat` reads `OLLAMA_BASE_URL` as a single-host
  fallback when the role-specific env var is unset. After rename this
  becomes `LOCAL_BASE_URL`.
- Error messages in both methods reference "Ollama" / "OpenAI-compat";
  update the Ollama-native one to "local LLM" or similar to stay neutral
  about the underlying server (llama-swap vs actual Ollama).

### Files in scope

- `src/study_tutor/llm/client.py` — primary site
- `tests/unit/llm/test_provider_resolution.py` — test parity (the existing
  test references `OLLAMA_*` names; rename in lockstep)
- `.env` — operator-side rename (so the rename doesn't break the running
  config)
- `.env.example` — documentation
- `scripts/mcp-wrapper.sh` — already doesn't reference `OLLAMA_*` by name
  but verify

## Acceptance Criteria

- [ ] All occurrences of the env-var names listed in "Concrete renames →
      Env vars" above are renamed exactly once across the project, with
      no `OLLAMA_*` leftovers in `src/`, `tests/`, `.env`, or `.env.example`
      (verify via `grep -rEn "OLLAMA_[A-Z_]+" src tests .env*` returning
      zero matches)
- [ ] All module-level constants in `src/study_tutor/llm/client.py` are
      renamed to the `DEFAULT_LOCAL_*` form
- [ ] `_generate_ollama` is renamed to `_generate_local`; the
      `local` provider branch in `LLMClient.generate` calls the renamed
      method
- [ ] `_generate_openai_compat` keeps its name (it's API-contract-named,
      not technology-named — leave alone)
- [ ] `tests/unit/llm/test_provider_resolution.py` is updated in lockstep
      and passes; no test is deleted or weakened — only the names change
- [ ] `pytest -m "feat_lca and smoke" tests/unit tests/integration -x`
      passes (the FEAT-6CC5 smoke gate; regression guard against silently
      breaking the Coach wiring)
- [ ] `pytest tests/unit/llm/ -x` passes
- [ ] The error message in `_generate_local` no longer says "Ollama
      request to ..." (use a neutral phrase like "local LLM request to ...")
      since the endpoint may be llama-swap, real Ollama, or any
      Ollama-compatible host
- [ ] `.env` (operator-side) is updated in the same commit as the source
      change so a fresh `MCPAdapter` boot succeeds without further env
      edits — the operator should not have to do a separate update step
- [ ] `.env.example` documents the new names with the same comments
      (D3 invariant, snapshot-at-boot, GB10-llama-swap reference for
      Coach) but using the renamed vars
- [ ] All modified files pass project-configured lint/format checks with
      zero errors
- [ ] Manual verification: stop Claude Desktop, run the MCP server
      directly via `scripts/mcp-wrapper.sh`, confirm boot smoke check
      passes; restart Claude Desktop and confirm `tutor_start_session`
      and `tutor_turn` both succeed (i.e. the rename didn't silently
      drop a referenced env var)

## Test Requirements

- Unit-test parity with the existing `test_provider_resolution.py`
  coverage; only the env-var names change in assertions
- No new test files needed (this is a mechanical rename) — but if the
  existing tests use string literals like `"OLLAMA_MODEL"` for
  `monkeypatch.setenv` calls, those need to be updated; that's covered
  by the parity AC above

## Implementation Notes

### Why this naming pattern

`AGENT_MODELS__REASONING_MODEL=local` is the provider-name discriminator.
Per-provider config matching the pattern `<PROVIDER>_*` (uppercased,
hyphens to underscores) gives:

```
AGENT_MODELS__REASONING_MODEL=local        →  LOCAL_BASE_URL, LOCAL_MODEL, ...
AGENT_MODELS__COACH_MODEL=local-coach      →  LOCAL_COACH_BASE_URL, LOCAL_COACH_MODEL, ...
```

This scales: when a real third provider is wired (e.g. an Anthropic-direct
provider as a richer Coach in Phase-2), it lands as
`AGENT_MODELS__COACH_MODEL=anthropic` with `ANTHROPIC_API_KEY`,
`ANTHROPIC_MODEL` etc. — each provider owns its own config namespace.

### What `local` actually means after the rename

`local` is the provider-name discriminator. The literal endpoint behind
it can be Mac Ollama, llama-swap on the GB10, a future vLLM instance,
or any Ollama-compatible HTTP server — the code path doesn't care, and
the renamed vars don't lie about that fact.

### Rename mechanics

This is a one-shot find/replace across a small set of files. Recommended
order to keep tests green throughout:

1. Update `src/study_tutor/llm/client.py` (constants, env-var lookups,
   method name, error messages)
2. Update `tests/unit/llm/test_provider_resolution.py` to match
3. Run `pytest tests/unit/llm/` — should be green
4. Update `.env.example`
5. Update `.env`
6. Run `pytest -m "feat_lca and smoke" tests/unit tests/integration -x` —
   should still be green
7. Manual MCP-server boot verification per the AC above

### Coordination with FEAT-PO-004 (Bedrock)

If FEAT-PO-004 (Bedrock provider) lands before this rename, that work
should NOT add `BEDROCK_*` env vars in the same module because that
crystallises the per-provider-namespace pattern; if FEAT-PO-004 lands
after this rename, it should follow the pattern naturally. Either order
is fine. If neither has happened yet (current state at task creation),
no coordination is needed.

## Test Execution Log

**Run date**: 2026-05-06 (via `/task-work TASK-LCN-001`)

**Quality gates**:
- ✅ Compilation: `from study_tutor.llm import client` imports cleanly with renamed
  symbols `DEFAULT_LOCAL_BASE_URL`, `DEFAULT_LOCAL_MODEL`,
  `DEFAULT_LOCAL_TIMEOUT_SECONDS`, `DEFAULT_LOCAL_NUM_PREDICT` exported.
- ✅ `pytest tests/unit/llm/ -x` — **15 passed in 0.06s** (5 in `test_client.py`,
  10 in `test_provider_resolution.py`).
- ✅ `pytest -m "feat_lca and smoke" tests/unit tests/integration -x` —
  **3 passed, 1 skipped** (FEAT-6CC5 regression guard against silently
  breaking the Coach wiring).
- ✅ Zero `OLLAMA_*` leftovers:
  `grep -rEn "OLLAMA_[A-Z_]+" src tests .env .env.example` returns no matches.
- ✅ End-to-end env smoke: `dotenv.load_dotenv('.env')` →
  `LOCAL_BASE_URL`, `LOCAL_MODEL`, `LOCAL_COACH_BASE_URL`,
  `LOCAL_COACH_MODEL` all resolve to expected values; no legacy
  `OLLAMA_*` keys present in the loaded environment.
- ✅ Full-unit regression: `pytest tests/unit` passes 831/833. The two
  failures (`test_graphiti_client_wiring.py::test_cross_encoder_sentinel_raises_on_arbitrary_method_name`
  and `test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule`)
  are **pre-existing on `main`** — verified by stashing the rename and
  running each in isolation; both fail identically without the rename.
  Out of scope for TASK-LCN-001.

**Notes on AC interpretation** (some ACs were written before TASK-LSP-002
landed and are now partially superseded):
- The AC **"`_generate_ollama` is renamed to `_generate_local`"** is moot.
  TASK-LSP-002 (commit `3d9680e`) collapsed both `local` and `local-coach`
  paths into a single `_generate_openai_compat` helper; there is no
  `_generate_ollama` method to rename. The `_generate_openai_compat` name
  is kept per the matching AC ("API-contract-named, not technology-named —
  leave alone"). The intent of this AC — eliminating Ollama-specific
  naming from the `local` provider path — is satisfied by renaming the
  env-var lookups (`OLLAMA_*` → `LOCAL_*`) and the module-level constants
  (`DEFAULT_OLLAMA_*` → `DEFAULT_LOCAL_*`).
- The AC **"error message in `_generate_local` no longer says 'Ollama
  request to ...'"** is moot for the same reason. The current error
  message in `_generate_openai_compat` is `"OpenAI-compat request to {base_url} failed"`
  — already API-contract-named, not technology-leaking. No change needed.

**Manual verification (operator-side, deferred to user)**:
- The AC asks for an MCP-server boot smoke check via
  `scripts/mcp-wrapper.sh` followed by `tutor_start_session` /
  `tutor_turn`. That is an operator-side action requiring a Claude
  Desktop restart and is outside what `/task-work` runs in-session. The
  `.env` rename is in lockstep with the source change, and the
  end-to-end env smoke above confirms the renamed vars resolve, so a
  fresh `MCPAdapter` boot should succeed. Recommend the operator perform
  this manual step before merging.

**Files modified**:
- `src/study_tutor/llm/client.py` — module-level constants, env-var
  lookups, comments referencing the renamed surfaces.
- `tests/unit/llm/test_provider_resolution.py` — env-var literals in
  `monkeypatch.setenv` / `patch.dict` calls and matching docstrings/
  assertion messages.
- `.env` — operator-side rename (in lockstep so MCP server boot doesn't
  break).
- `.env.example` — renamed vars, plus added `LOCAL_COACH_BASE_URL` /
  `LOCAL_COACH_MODEL` block with the D3 / snapshot-at-boot / GB10
  llama-swap comments per the AC's "documents the new names with the
  same comments" requirement (the existing `.env.example` lacked the
  Coach section that's been in `.env` since TASK-LCA-004).
- `scripts/mcp-wrapper.sh` — verified clean: doesn't reference
  `OLLAMA_*` directly (sources `.env`, so the rename is picked up
  automatically).

**State transition**: in_progress → in_review (all quality gates passed).
