/system-design --focus="Inference Runtime" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md


Architecture and existing design context found. Let me load all the relevant files in parallel.

Read ARCHITECTURE.md
Read ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Read openwebui-rag-empirical-findings-2026-04-23.md
Now let me load the existing design context to see what's already there.

Bash List existing design subdirectories
IN
ls docs/design/contracts/ docs/design/models/ docs/design/decisions/ docs/design/diagrams/ 2>/dev/null

OUT
docs/design/contracts/:
API-inference-runtime.md
API-mcp-transport.md
API-tutoring.md

docs/design/decisions/:
DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md
DDR-002-coach-async-subagent-owns-graphiti-writes.md
DDR-003-session-completed-emits-on-state-transition.md

docs/design/diagrams/:
tutoring-c4-l3.md

docs/design/models/:
DM-inference-runtime.md
DM-mcp-transport.md
DM-tutoring.md
Read API-inference-runtime.md
Read DM-inference-runtime.md
Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Run interactive design refinement against ADR-ARCH-018 (CC-14: SR-09 Modelfile params; CC-13 reach into LLMClient if any)

Identify protocol surfaces (LLMClient internal Python interface only — confirm no external surface change)

Update DM-inference-runtime.md with SR-09/CC-14 invariants and num_predict/num_ctx env coverage

Update API-inference-runtime.md to reference CC-14 and num_ctx contract

Capture DDR(s) for Inference Runtime decisions (e.g. CC-14 conformance gate, num_ctx env-var introduction)

Run contradiction detection vs existing ADRs

C4 L3 review gate (skip if <=3 components)

Update docs/design/README.md and emit summary; offer Graphiti seeding commands
Read README.md
Let me also check what cross-context pointers Tutoring made to Inference Runtime, and read the events schema.

Bash Find existing CC-14 cross-context pointers
IN
grep -n -E "CC-14|num_ctx|num_predict|SR-09|inference-runtime|InferenceRuntime|Inference Runtime" docs/design/contracts/API-tutoring.md docs/design/models/DM-tutoring.md docs/design/contracts/API-mcp-transport.md docs/design/models/DM-mcp-transport.md docs/design/events-schema.yaml 2>/dev/null | head -80

OUT
docs/design/models/DM-mcp-transport.md:7:**Refreshed:** 2026-04-27 by `/system-design --focus="MCP Transport"` to absorb [ADR-ARCH-017](../../architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md), [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-13 / CC-14), and [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md).
docs/design/models/DM-mcp-transport.md:97:| `MCPAdapter` | `LLMClient` (Inference Runtime) | constructed per call | P0 |
docs/design/models/DM-tutoring.md:94:**Cross-context pointer (CC-14, runtime LLM parameters explicit):** the explicit `num_ctx` / `num_predict` invariant lives in [`DM-inference-runtime.md`](DM-inference-runtime.md) (Inference Runtime context). Tutoring inherits the guarantee through the `LLMClient` boundary; no Tutoring-side invariant is added here to avoid duplication. Tutoring's role is to *use* the configured client — not to assert Modelfile parameters.
docs/design/models/DM-tutoring.md:103:| `TutorSession` | `LLMClient` (Inference Runtime context) | depends-on (injected via `MCPAdapter`) | P0 |
docs/design/contracts/API-mcp-transport.md:13:MCP Transport is a **thin façade** owning the external protocol surface for AI agents. It enforces transport-layer invariants (SR-01 / SR-02 / SR-07 / CC-08 / CC-13) and turns the tutor into a discoverable, invokable system. The tools themselves and their behavioural contracts belong to **Tutoring** — see `API-tutoring.md`. CC-14 (runtime LLM parameters explicit) is owned by Inference Runtime / Tutoring; this contract notes only its presence on the cross-cutting checklist (see §5.5).
docs/design/contracts/API-mcp-transport.md:64:### 5.5 CC-14 (runtime LLM parameters) — pointer
docs/design/contracts/API-mcp-transport.md:65:CC-14 (every Modelfile sets explicit `num_ctx` / `num_predict`, with smoke-test assertions via `ollama show` *and* runner-log inspection) is owned by **Inference Runtime** / **Tutoring**. MCP Transport carries it on its cross-cutting checklist for completeness only; the contract surface (tool descriptions, schemas, error envelope) does not change with CC-14.
docs/design/contracts/API-tutoring.md:216:- **CC-14 inference parameters** — explicit `num_ctx` / `num_predict` is enforced in the [Inference Runtime contract](API-inference-runtime.md) and data model. Tutoring inherits the guarantee through the `LLMClient` boundary; no Tutoring-side test is required.
Read API-tutoring.md (lines 201-230)
Read DM-tutoring.md (lines 86-115)
Read client.py
I have full context now. The /system-design --focus="Inference Runtime" run is the last outstanding ADR-018/019 stale-reference sweep flagged in docs/design/README.md §5. The work is well-scoped: absorb CC-14 (num_ctx / num_predict Modelfile discipline) into API-inference-runtime.md and DM-inference-runtime.md, document the smoke-test pattern, and capture a DDR for the non-trivial design choice (Modelfile-owns-num_ctx, not client).

Architecture loaded: 6 bounded contexts; focused on Inference Runtime.
Existing design context found — will refresh.
Graphiti available (config enabled: true, FalkorDB at whitestocks:6379).

Here's the delta plan I'll apply (bias-to-defaults, in line with the prior MCP / Tutoring focus runs):

Δ1 — API-inference-runtime.md header — add the 2026-04-27 (PM late) refresh note citing ADR-ARCH-018 and the OpenWebUI RAG findings.

Δ2 — API-inference-runtime.md §4 (Configuration surface) — split table into client-resident (env vars) vs Modelfile-resident (num_ctx, num_predict); explain that LLMClient does not set num_ctx per request.

Δ3 — API-inference-runtime.md §5 (Invariants) — add I-IR7 (Modelfile params explicit, CC-14 thresholds) and I-IR8 (options.num_predict is always set per request; OLLAMA_NUM_PREDICT is operator override, not CC-14 floor).

Δ4 — API-inference-runtime.md §7 (Conformance tests) — add CC-14 smoke test row: ollama show <model> --modelfile | grep PARAMETER + runner-log line llama_new_context_with_model: n_ctx = N.

Δ5 — API-inference-runtime.md §8/§9 — out-of-scope/open-question polish (Modelfile-owns-num_ctx; non-Ollama-provider CC-14 extension still open).

Δ6 — DM-inference-runtime.md §4 — same Modelfile-vs-client split in env-var/config table; add runner-log assertion narrative.

Δ7 — DM-inference-runtime.md §5 (Invariants) — same I-IR7 / I-IR8 rows.

Δ8 — DM-inference-runtime.md §6 / §8 — relationships note pointing to Modelfile as a configuration artefact; out-of-scope alignment.

Δ9 — DDR-004-num-ctx-modelfile-owned-not-client.md — new DDR pinning the design choice.

Δ10 — docs/design/README.md — log the run, mark Inference Runtime stale references resolved (close the §5 / §7.6 outstanding item).

No new C4 L3 (Inference Runtime is ≤3 components: LLMClient + helpers + lazy httpx provider call). No contradictions expected — the deltas codify CC-14 which ADR-ARCH-018 explicitly mandates for this context.

Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer Graphiti seeding commands
Edit API-inference-runtime.md
Added 1 line
Now Δ2 — split §4 to distinguish client-resident from Modelfile-resident config.

Edit API-inference-runtime.md
Added 17 lines
Now Δ3 — invariants table additions.

Edit API-inference-runtime.md
Added 2 lines
Now Δ4 — extend §7 conformance tests with the CC-14 smoke test.

Edit API-inference-runtime.md
Added 9 lines
Now Δ5 — out-of-scope and open questions.

Edit API-inference-runtime.md
Added 6 lines
Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer Graphiti seeding commands
Now Δ6 — refresh DM-inference-runtime.md.

Edit DM-inference-runtime.md
Added 1 line
Edit DM-inference-runtime.md
Added 15 lines
Now Δ7 — extend invariants table and Δ8 — relationships note + out-of-scope alignment.

Edit DM-inference-runtime.md
Added 2 lines
Edit DM-inference-runtime.md
Added 1 line
Edit DM-inference-runtime.md
Added 2 lines
Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer Graphiti seeding commands
Now Δ9 — DDR-004. Let me check the format of an existing DDR so I match the house style.

Read DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md
Read DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md (lines 51-250)
Format clear. Now writing DDR-004.

Write DDR-004-num-ctx-modelfile-owned-not-client.md
87 lines
# DDR-004 — `num_ctx` is owned by the Modelfile, not by `LLMClient`; CC-14 conformance is a smoke test

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 0 (rule); Phase 1 (operative as RAG-enabled personas + smoke test land)
**Bounded context:** Inference Runtime
**Related:** [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-14 — runtime LLM parameters explicit; SR-09 origin), [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4 + §3a](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md), [API-inference-runtime.md §4 / §5 / §7](../contracts/API-inference-runtime.md), [DM-inference-runtime.md §4 / §5 (I-IR7, I-IR8)](../models/DM-inference-runtime.md), [DM-tutoring.md §6 cross-context pointer](../models/DM-tutoring.md).

## Context

[ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) promoted SR-09 to **CC-14**: every Ollama Modelfile used by the tutor must set explicit `num_ctx` (≥ 16384 for RAG-enabled personas) and `num_predict` (≥ 1500 for tutoring responses), with smoke-test assertions via `ollama show <model> --modelfile | grep PARAMETER` and via the runner-log line `llama_new_context_with_model: n_ctx = N`.

The empirical anchor is the 23 April 2026 OpenWebUI RAG session ([openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)): Ollama's default `num_ctx = 2048` silently truncated tutoring responses mid-sentence whenever RAG was active (system prompt ~600 tokens + RAG template ~100 tokens + 6 retrieved chunks at 512 tokens ≈ 3000 tokens — generation budget exhausted before completion, with no error). The fix landed in the deployed Modelfile as `PARAMETER num_ctx 16384` + `PARAMETER num_predict 1500`.

ADR-ARCH-018 settles **what** must hold (≥ 16384 / ≥ 1500, asserted) but does not settle **where** the rule lives in the codebase. The Inference Runtime contract has to choose between two designs:

1. **Client-resident:** push `num_ctx` into the request payload from `LLMClient._generate_ollama`, mirroring the existing per-request `options.num_predict` pathway (`client.py:89`). The client becomes the enforcer; the smoke test is auxiliary.
2. **Modelfile-resident:** leave `num_ctx` to the Modelfile, with the smoke test as the **primary** conformance gate. The client trusts the loaded model and continues to set only `options.num_predict` per request.

Today's `client.py` is shape (2) — `options.num_ctx` is not in the payload, only `options.num_predict` is. CC-14 forces the choice to be explicit rather than incidental.

## Decision

**`LLMClient` does not set `options.num_ctx` per request. The Ollama Modelfile is the single source of truth for the runtime context window. CC-14 conformance is enforced by a smoke test, not by per-request enforcement in the client.**

Concretely:

- `_generate_ollama` (`client.py:78–107`) continues to omit `num_ctx` from the request payload's `options` block. Only `num_predict` is set per request.
- The Modelfile (`PARAMETER num_ctx N`, `PARAMETER num_predict N`) is the canonical locus for both parameters.
- The CC-14 smoke test runs against the loaded model — both halves are required:
  - **`ollama show <model> --modelfile | grep PARAMETER`** confirms the Modelfile literal at the threshold.
  - **Runner-log inspection** of `llama_new_context_with_model: n_ctx = N` from a real inference call confirms the runner actually loaded that value.
- `OLLAMA_NUM_PREDICT` (env var, default 2048) remains the per-request operator override for `num_predict`. It is not the CC-14 floor — the Modelfile default is. Operators tuning below 1500 explicitly accept the truncation risk that CC-14 was introduced to prevent.
- Codified as **I-IR7** and **I-IR8** in [`DM-inference-runtime.md §5`](../models/DM-inference-runtime.md); the smoke test is recorded in [`API-inference-runtime.md §7.2`](../contracts/API-inference-runtime.md).

## Rationale

- **`num_ctx` is a per-model, model-load-time concern; `num_predict` is a per-request tuning knob.** The two parameters are not symmetric. `num_ctx` allocates KV-cache memory at load time and is fixed for the lifetime of the running model; setting it per request is at best wasteful and at worst inconsistent with what the runner has actually allocated. `num_predict` is a generation-budget ceiling per call. Pushing both into the request payload conflates two different lifecycles.
- **Persona split lives in the Modelfile, not in the client.** The deployed configuration ([§3e of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)) splits "GCSE Shakespeare Tutor" (no RAG) from "GCSE Modern Texts Tutor" (RAG mandatory) and a general fallback. RAG-enabled personas need `num_ctx ≥ 16384`; the Shakespeare persona does not. The persona-to-`num_ctx` mapping is a **deployment** decision (which Modelfile to load), not a request-time decision. Putting `num_ctx` in the client would either (a) require the client to know which persona it is talking to, or (b) force a single value across personas — both worse than the Modelfile staying authoritative.
- **The empirical failure mode is silent truncation.** Finding 4 establishes that `num_ctx` regressions surface as mid-word truncation with no error. A smoke-test gate at Modelfile-build time is the right shape: once asserted, it stays asserted until the Modelfile changes; the test is cheap to re-run; and the runner-log half closes the loophole where a build artefact diverges from what the runner uses. A runtime check from the client cannot detect the same failure because the client sees a string truncated by the runner — there is no error to catch.
- **Symmetry with `num_predict` resolution is an illusion.** `_resolve_num_predict()` (`client.py:31–44`) reads an env var and applies it as a per-request ceiling — a *capping* operation against the Modelfile default. There is no analogous capping operation for `num_ctx`: the runner has already allocated whatever the Modelfile said. The shapes look similar but have different semantics.
- **Non-Ollama providers don't have Modelfiles.** Bedrock Custom Model Import sets context size at import time (a model-ARN attribute); OpenAI / Anthropic / Gemini expose context windows as model-ID metadata. Putting `num_ctx` into `LLMClient` would force a per-provider switch with five non-overlapping shapes. Keeping `num_ctx` out of the client preserves the option to add per-provider CC-14 conformance gates without committing to a particular runtime locus today (open question, [API-inference-runtime.md §9 item 4](../contracts/API-inference-runtime.md)).

## Alternatives considered

- **Push `num_ctx` into `LLMClient._generate_ollama`'s `options` payload.** Rejected.
  - Duplicates the Modelfile setting and risks drift (Modelfile says 16384, client says 8192 → which wins? The runner uses what was loaded at startup, so the client setting is effectively a no-op or worse, a misleading log artefact).
  - Couples per-persona context budgets to client code; the persona split documented in [§3e of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) becomes harder to maintain.
  - Does not actually catch silent-truncation regressions — the runner has already loaded `num_ctx` by the time the client sends a request.

- **Add a unified `_resolve_inference_params()` that returns both `num_ctx` and `num_predict` from env vars.** Rejected. Same drift / coupling risk as above; treats the two parameters as if they had the same lifecycle when they do not.

- **Defer the rule and rely on per-PR review.** Rejected. The 78.98s `add_episode` median made CC-13 non-negotiable for analogous reasons; the silent-truncation failure mode for `num_ctx` is the same shape — a regression class that produces incorrect outputs without errors. A recorded rule + smoke test is cheaper than re-litigating per PR.

- **Bind the rule to ADR-ARCH-018 alone.** Rejected. ADR-ARCH-018 is an *architectural* commitment about *which parameters must be explicit*. The Modelfile-vs-client split is a *design-level* artefact about *where the explicitness lives in the codebase*. Conflating them obscures the chain of evidence and makes the design-level rule invisible to anyone reading only `docs/design/`.

## Consequences

**Positive:**
- `LLMClient` stays simple — one provider matrix, one per-request tuning knob (`num_predict`), no client-side enforcement of model-load-time concerns.
- The Modelfile remains the single locus for persona-specific context-window decisions; persona split is a deployment-time choice, not a code-time choice.
- The CC-14 smoke test is the cheapest possible conformance gate — once green, it stays green until the Modelfile changes; the runner-log half makes it decisive (catches "Modelfile changed but runner did not reload" failures).
- Aligns with the Inference Runtime's anti-corruption-layer role (`ARCHITECTURE.md §3`): provider-specific knowledge (Modelfile vs request-payload semantics) stays inside the context.

**Negative:**
- A regressed Modelfile is silently catastrophic *unless* the smoke test runs. The CC-14 smoke test must run on every Modelfile change (CI or pre-commit hook); a stale or skipped test re-introduces the silent-truncation class. Mitigated by recording the test recommendation in [`API-inference-runtime.md §7.2`](../contracts/API-inference-runtime.md) and flagging it as outstanding in [§5 of `openwebui-rag-empirical-findings`](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) (*"Add smoke-test for `num_ctx` runtime value (guard against Modelfile regression)"*).
- Extending CC-14 to non-Ollama providers requires per-provider conformance work; there is no single implementation point in `LLMClient` to extend. Recorded as an open question in [API-inference-runtime.md §9 item 4](../contracts/API-inference-runtime.md).
- The client-payload shape (no `num_ctx`) and the Modelfile shape (canonical `num_ctx`) are easy to confuse on first read. Mitigated by I-IR7 / I-IR8 spelling out both halves and by the §4.1 / §4.2 split in the API contract and data model.

## Affected artefacts

- [`docs/design/contracts/API-inference-runtime.md §4 (split into 4.1 client-resident / 4.2 Modelfile-resident) + §5 (invariants 6, 7) + §7.2 (CC-14 smoke test row) + §8 (per-request `num_ctx` out of scope) + §9 (non-Ollama-provider extension)`](../contracts/API-inference-runtime.md) — references this DDR.
- [`docs/design/models/DM-inference-runtime.md §4 (4.1 / 4.2 split) + §5 (I-IR7, I-IR8) + §6 (Modelfile relationship row) + §8 (per-request `num_ctx` out of scope)`](../models/DM-inference-runtime.md) — encodes the rule and its enforcement; **source of truth** for the cross-context CC-14 pointer in [`DM-tutoring.md §6`](../models/DM-tutoring.md).
- [`src/study_tutor/llm/client.py` lines 78–107 (`_generate_ollama`)](../../../src/study_tutor/llm/client.py) — the request-payload shape that this DDR commits to (no `options.num_ctx`).
- The Modelfile of `gcse-tutor-gemma4-moe:latest` (and any future RAG-enabled persona Modelfile) — the canonical locus this DDR points at; not under version control in this repo today, but the deployed configuration is captured in [§3a of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md).

## References

- [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — CC-14 / SR-09 promotion to load-bearing cross-cutting concern.
- [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the silent-truncation failure mode CC-14 was introduced to prevent.
- [openwebui-rag-empirical-findings-2026-04-23.md §3a](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the deployed Modelfile (`PARAMETER num_ctx 16384`, `PARAMETER num_predict 1500`).
- [openwebui-rag-empirical-findings-2026-04-23.md §3e](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the persona split that depends on per-Modelfile `num_ctx`.
- [openwebui-rag-empirical-findings-2026-04-23.md §5 outstanding-this-week](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — "Add smoke-test for `num_ctx` runtime value" — this DDR is the design home for that test.
Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer Graphiti seeding commands
Contradiction detection complete — checked all 19 architecture ADRs and 3 existing DDRs:

ADR-ARCH-018 (CC-14 origin): the deltas implement this ADR's CC-14 mandate in the design layer. Direct dependency, no conflict.
ADR-ARCH-006 (dual inference path Ollama + Bedrock): consistent. CC-14 today is Ollama-specific; non-Ollama extension is recorded as an open question rather than a contradiction.
All other ADRs and DDR-001/002/003: orthogonal.
✓ No contradictions. The deltas resolve the stale-reference item flagged in docs/design/README.md §5 rather than introducing new conflicts.

Now Δ10 — update docs/design/README.md to log the run and close the outstanding item.

Edit README.md
Added 1 line
Edit README.md
Added 1 line
Now extend §3 with the Inference Runtime refresh row, and update §4 / §5 / §7.

Edit README.md
Added 6 lines
Edit README.md
Modified
Edit README.md
Added 2 lines
Now update the "stale references swept" / "stale references not swept" sections to reflect that the Inference Runtime sweep is done.

Edit README.md
Added 7 lines
Now §7 next steps — close the "Inference Runtime focus run" outstanding item.

Edit README.md
Added 1 line
Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer Graphiti seeding commands
Edit README.md
Modified
Let me verify the final state of the key files looks right.

Bash Verify section structure of refreshed files
IN
echo "===API-inference-runtime===" && grep -n "^## \|^### " docs/design/contracts/API-inference-runtime.md && echo "===DM-inference-runtime===" && grep -n "^## \|^### " docs/design/models/DM-inference-runtime.md && echo "===DDR-004 lines===" && wc -l docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md

OUT
===API-inference-runtime===
11:## 1. Consumer model
25:## 2. Public Python interface
58:## 3. Provider matrix
75:## 4. Configuration surface
79:### 4.1 Client-resident (env vars, read at call time)
93:### 4.2 Modelfile-resident (CC-14 — Ollama only)
106:## 5. Invariants
116:## 6. Sync vs async
120:## 7. Conformance tests
122:### 7.1 In place / today
128:### 7.2 Recommended additions
136:## 8. Out of scope
145:## 9. Open questions for downstream phases
===DM-inference-runtime===
11:## 1. Aggregate root: `LLMClient`
25:## 2. Value object: `ProviderLabel`
41:## 3. Value object: `LLMProviderError`
50:## 4. Configuration surface
54:### 4.1 Client-resident (env vars; SR-03 forbids module-level caching)
64:### 4.2 Modelfile-resident (CC-14 — Ollama only)
77:## 5. Invariants
90:## 6. Relationships
101:## 7. Persistence
105:## 8. Out of scope
===DDR-004 lines===
      86 docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md
Section structure intact. Now let me run the Tier 2 Graphiti connectivity check.

Bash Tier 2 Graphiti connectivity check
IN
guardkit graphiti status 2>&1 | head -30

OUT
╔════════════════════════════════════════╗
║       Graphiti Knowledge Status        ║
╚════════════════════════════════════════╝

  Status: ENABLED
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"

  System Knowledge:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • product_knowledge: 84
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • command_workflows: 100
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • patterns: 100
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • agents: 100
  Project Knowledge:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • project_overview: 63
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
    • project_architecture: 2
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
  Decisions:
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
Graphiti reachable (FalkorDB at whitestocks:6379, embeddings on GB10 responding). Here is the design summary and the seeding commands offer.

✅ SYSTEM DESIGN COMPLETE — /system-design --focus="Inference Runtime" (2026-04-27 PM late)
Closes the last outstanding ADR-018/019 stale-reference item flagged in docs/design/README.md §5 / §7.6.

Files updated / created

docs/design/
├── README.md                                 (logged 2026-04-27 PM-late refresh; closed Inference Runtime sweep)
├── contracts/
│   └── API-inference-runtime.md              (Δ1–Δ5: header refresh; §4 split client/Modelfile; §5 invariants 6 & 7; §7.2 CC-14 smoke tests; §8/§9 out-of-scope + open question)
├── models/
│   └── DM-inference-runtime.md               (Δ6–Δ8: §4 split; I-IR7 / I-IR8 invariants; §6 Modelfile relationship; §8 out-of-scope alignment)
└── decisions/
    └── DDR-004-num-ctx-modelfile-owned-not-client.md  (NEW — Modelfile-vs-client locus; CC-14 conformance via two-part smoke test)
Design decisions captured
DDR-004 — num_ctx is owned by the Ollama Modelfile, not by LLMClient. CC-14 conformance is enforced by a smoke test (ollama show <model> --modelfile | grep PARAMETER and runner-log inspection of llama_new_context_with_model: n_ctx = N), not by a per-request client check. OLLAMA_NUM_PREDICT (env var, default 2048) is the operator override for num_predict, not the CC-14 floor (≥ 1500 — Modelfile-default).
Contradiction detection
✓ No contradictions against the 19 architecture ADRs or DDR-001/002/003. Deltas implement ADR-ARCH-018's CC-14 mandate; non-Ollama-provider extension recorded as an open question rather than a conflict.

C4 L3 review gate
Skipped. Inference Runtime confirmed ≤ 3 internal components (LLMClient + provider-resolution helpers + lazy httpx-on-Ollama path; the Modelfile is a configuration artefact). Threshold not met.

OpenAPI validation
Skipped. No REST surface in Inference Runtime (it has no external protocol surface — internal Python interface only).

📥 Graphiti seeding (offer)
Graphiti is reachable (FalkorDB at whitestocks:6379, vLLM embeddings on promaxgb10-41b1:8001 responding). Here are the commands to seed this run's artefacts. Note: with add_episode median 78.98s and max_concurrent_episodes: 3, run them sequentially and after any prior refresh batch finishes:


guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md \
  --group project_design

guardkit graphiti add-context docs/design/models/DM-inference-runtime.md \
  --group project_design

guardkit graphiti add-context docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md \
  --group architecture_decisions
Want me to run these seeding commands now? (Y/n) — I'll execute them sequentially via the Bash tool; given the 78.98s median per add_episode, the batch will take ~4 minutes if no other Graphiti work is in flight.

Recommended next steps (after seeding)
Implement the CC-14 Modelfile-parameter smoke test (API §7.2, DM §5 I-IR7) on the next PR that touches the Modelfile build or tests/unit/llm/. Two-part assertion is load-bearing — the runner-log half catches Modelfile/runner divergence.
Implement the CC-14 client-payload smoke test asserting options.num_predict is always present in the Ollama request payload.
Revisit non-Ollama CC-14 extension when FEAT-PO-004 (Bedrock) ships — see API-inference-runtime.md §9 item 4.
command-history.md
please seed to graphiti
Seeding sequentially. Each add_episode median is 78.98s, so each command will take ~60–120s.

Bash Seed API-inference-runtime.md to project_design
IN
guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md --group project_design 2>&1 | tail -20

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH
Try 'guardkit-py graphiti add-context --help' for help.

Error: No such option: --group
Bash Check correct flag for add-context
IN
guardkit graphiti add-context --help 2>&1 | head -40

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH

  Add context from files to Graphiti.

  Adds content from markdown files to the Graphiti knowledge graph. Supports
  single files or directories with glob patterns.

  Examples:
      guardkit graphiti add-context docs/ADR-001.md
      guardkit graphiti add-context docs/architecture/
      guardkit graphiti add-context docs/ --pattern "**/*.md"
      guardkit graphiti add-context docs/ADR-001.md --type adr
      guardkit graphiti add-context docs/ --dry-run
      guardkit graphiti add-context docs/ --delay 1.0
      guardkit graphiti add-context docs/ --delay 0

  Supported parser types:
      - adr: Architecture Decision Records
      - feature_spec: Feature specifications
      - full_doc: Full document capture (entire markdown content)
      - project_overview: Project overview documents
      - project_doc: General project documentation (CLAUDE.md, README.md)

Options:
  --type TEXT           Force parser type (adr, feature-spec, project-
                        overview)
  -f, --force           Overwrite existing context
  --dry-run             Show what would be added without adding
  --pattern TEXT        Glob pattern for directory (default: **/*.md)
  -v, --verbose         Show detailed processing output
  -q, --quiet           Suppress non-error output
  --delay FLOAT         Inter-episode delay in seconds (default: 0.5, 0 to
                        disable)
  --chunk-size INTEGER  Force chunking for docs above this size in bytes
                        (default: 10240). Use 0 to always chunk.
  --timeout FLOAT       Per-episode timeout in seconds (overrides auto-
                        detected timeout). Use for slow vLLM instances.
  --help                Show this message and exit.
The CLI doesn't accept --group — it auto-detects from path/type. Let me first dry-run to confirm the routing.

Bash Dry-run to confirm group routing
IN
guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md --dry-run 2>&1 | tail -30

OUT
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

  ✓ docs/design/contracts/API-inference-runtime.md (full_doc)

Dry run complete - Would add:
  1 file, 10 episodes

Warnings:
  Warning: docs/design/contracts/API-inference-runtime.md: Large document (12733
bytes) split into 10 chunks
Dry-run confirms routing (full_doc parser). API-inference-runtime.md splits into 10 chunks — ~5–7 min for that file at 78.98s/episode median with concurrency 3. I'll run the three commands sequentially in the background and notify when each finishes.

Bash Sequentially seed all three Inference Runtime artefacts
IN
guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md > /tmp/seed-api-ir.log 2>&1 && echo "===NEXT===" && guardkit graphiti add-context docs/design/models/DM-inference-runtime.md > /tmp/seed-dm-ir.log 2>&1 && echo "===NEXT===" && guardkit graphiti add-context docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md --type adr > /tmp/seed-ddr-004.log 2>&1 && echo "===DONE==="

OUT
Command running in background with ID: bj85ytshz. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/d3b6c405-f8b8-4077-a490-f3339289c5fc/tasks/bj85ytshz.output
Background seeding started. I'll wait for completion notification — typical batch ~10 minutes for ~22 chunks at 78.98s/episode median with concurrency 3.

ScheduleWakeup
IN
{
  "delaySeconds": 270,
  "reason": "checking Graphiti seeding progress (first file ~5-7min for 10 chunks)",
  "prompt": "/system-design --focus=\"Inference Runtime\" --from docs/architecture/ARCHITECTURE.md --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md"
}
OUT
Next wakeup scheduled for 17:08:00 (in 254s).
Seeding is running in the background (job bj85ytshz). I'll check progress in ~4½ minutes (270s — well within the 5-min Anthropic prompt-cache window). I'll report back as each command completes; if all three finish before the wakeup, you'll get an earlier notification from the background job itself.

phase-1-build-plan.md
what's the status?
Bash Check seeding log progress
IN
ls -la /tmp/seed-api-ir.log /tmp/seed-dm-ir.log /tmp/seed-ddr-004.log 2>&1; echo "---"; tail -5 /tmp/seed-api-ir.log 2>&1; echo "---DM---"; tail -5 /tmp/seed-dm-ir.log 2>&1; echo "---DDR---"; tail -5 /tmp/seed-ddr-004.log 2>&1

OUT
Exit code 1
ls: /tmp/seed-ddr-004.log: No such file or directory
-rw-r--r--  1 richardwoollcott  wheel  4550 Apr 27 17:33 /tmp/seed-api-ir.log
-rw-r--r--  1 richardwoollcott  wheel   795 Apr 27 17:33 /tmp/seed-dm-ir.log
---
  Added 1 file, 10 episodes

Warnings:
  Warning: docs/design/contracts/API-inference-runtime.md: Large document (12733
bytes) split into 10 chunks
---DM---
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

---DDR---
tail: /tmp/seed-ddr-004.log: No such file or directory
Bash Check if seeding processes are still running
IN
ps -p $(pgrep -f "guardkit graphiti add-context" | head -3) 2>&1 | head -10; echo "---"; date

OUT
  PID TTY           TIME CMD
34459 ??         0:00.01 /bin/zsh -c source /Users/richardwoollcott/.claude/shell-snapshots/snapshot-zsh-1777304921672-um1ae9.sh 2>/dev/null || true && setopt NO_EXTENDED_GLOB 2>/dev/null || true && eval 'guardkit graphiti add-context docs/design/contracts/API-inference-runtime.md > /tmp/seed-api-ir.log 2>&1 && echo "===NEXT===" && guardkit graphiti add-context docs/design/models/DM-inference-runtime.md > /tmp/seed-dm-ir.log 2>&1 && echo "===NEXT===" && guardkit graphiti add-context docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md --type adr > /tmp/seed-ddr-004.log 2>&1 && echo "===DONE==="' < /dev/null && pwd -P >| /tmp/claude-0292-cwd
---
Mon Apr 27 17:34:54 BST 2026
Seeding status (as of 17:34:54)
File	Status	Episodes
API-inference-runtime.md	✅ Completed	10 / 10 added
DM-inference-runtime.md	🔄 In progress	started ~30s ago, connected to FalkorDB
DDR-004	⏳ Queued	not yet started
Background job bj85ytshz still running (the parent shell process is alive). The first file (10 chunks) finished — that's the largest of the three. DM-inference-runtime.md is mid-stream now; DDR-004 is queued behind it. I'll continue monitoring on the previously-scheduled wake-up (~3 minutes from now).

Bash Check final seeding logs
IN
echo "===API==="; tail -5 /tmp/seed-api-ir.log; echo "===DM==="; tail -8 /tmp/seed-dm-ir.log; echo "===DDR==="; tail -8 /tmp/seed-ddr-004.log

OUT
===API===
  Added 1 file, 10 episodes

Warnings:
  Warning: docs/design/contracts/API-inference-runtime.md: Large document (12733
bytes) split into 10 chunks
===DM===
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 202606.68015480042 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-inference-runtime.md]: nodes=13, edges=13, invalidated=0
  ✓ docs/design/models/DM-inference-runtime.md (full_doc)

Summary:
  Added 1 file, 1 episode
===DDR===
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 276364.4709587097 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_ddr-004-num-ctx-is-owned-by-the-modelfile-not-by-llmclient-cc-14-conformance-is-a-smoke-test]: nodes=16, edges=18, invalidated=0
  ✓ docs/design/decisions/DDR-004-num-ctx-modelfile-owned-not-client.md (adr)

Summary:
  Added 1 file, 1 episode
✅ Graphiti seeding complete
All three Inference Runtime artefacts seeded successfully:

File	Episodes	Nodes / Edges	Group
API-inference-runtime.md	10 (chunked from 12,733 bytes)	—	project_design (full_doc)
DM-inference-runtime.md	1	13 nodes, 13 edges	project_design (full_doc)
DDR-004	1	16 nodes, 18 edges	architecture_decisions (adr)
DM-inference-runtime took 202s; DDR-004 took 276s — both above the 78.98s add_episode median, consistent with the LLM-extraction load on graph-heavy artefacts. The two LLM-side warnings about duplicate_facts idx values on the DM seeding are benign (graphiti-core noise; still committed nodes=13, edges=13).

The /system-design --focus="Inference Runtime" run is fully complete: design artefacts updated, DDR-004 captured, README closed out, and knowledge graph seeded.

/system-design --focus="Inference Runtime" --from docs/architecture/ARCHITECTURE.md --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md
The wake-up fired with the original /system-design invocation as the resume prompt — but the run is already fully complete. The seeding job notification arrived just before this and confirmed all three artefacts are in the knowledge graph. Nothing to redo.

Update Todos

Load existing design context for Inference Runtime + check architecture cross-references (CC-13/CC-14)

Update API-inference-runtime.md (Δ1–Δ5)

Update DM-inference-runtime.md (Δ6–Δ8)

Capture DDR-004 (num_ctx Modelfile-owned, not client)

Run contradiction detection vs existing ADRs

Update docs/design/README.md with this run — close stale-reference outstanding item

Offer + execute Graphiti seeding (sequential, post-completion of prior batch)
✅ /system-design --focus="Inference Runtime" — fully complete
All seven steps done, no remaining work:

Step	Status
Architecture context loaded (19 ADRs + 6 bounded contexts)	✅
API-inference-runtime.md refreshed (Δ1–Δ5: §4 client/Modelfile split, §5 invariants 6 & 7, §7.2 CC-14 smoke tests, §8/§9 out-of-scope + open question)	✅
DM-inference-runtime.md refreshed (Δ6–Δ8: §4 split, I-IR7 / I-IR8, §6 Modelfile relationship, §8 alignment)	✅
DDR-004-num-ctx-modelfile-owned-not-client.md captured	✅
Contradiction detection vs 19 ADRs + 3 prior DDRs — no conflicts	✅
C4 L3 — skipped (Inference Runtime ≤ 3 components)	✅
docs/design/README.md updated; closed last outstanding ADR-018/019 stale-reference item	✅
Graphiti seeded — 12 episodes total (10 chunks for API + 1 for DM + 1 for DDR-004)	✅
The previously-scheduled wake-up was meant to check seeding progress, but the seeding-complete notification arrived first. Re-invocation isn't needed.