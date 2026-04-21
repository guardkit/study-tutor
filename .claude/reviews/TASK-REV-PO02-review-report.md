---
task_id: TASK-REV-PO02
feature_id: FEAT-PO-002
title: "Plan: FEAT-PO-002 — Fine-tuned English tutoring runtime over local deployment"
review_mode: decision
review_depth: standard
reviewer: orchestrator
created: 2026-04-19T00:00:00Z
clarification_context:
  depth: confirm_plus_spot_checks
  tradeoff: balanced
  focus_areas: [parity_surfaces, mcp_transport_tool_contract, task_decomposition]
---

# Review Report: TASK-REV-PO02 — FEAT-PO-002 Planning

## Executive Summary

FEAT-PO-002 delivers the Phase 0 critical-path runtime: Python package scaffold, MCP transport with four tutor tools, Ollama-backed LLM client with Bedrock stub, in-memory session state, and unit-test coverage of the two parity surfaces that are genuinely code-level (SR-01 stdio, SR-03 provider resolution). The existing hour-by-hour build plan in [phase-0-build-plan.md](../../docs/research/ideas/phase-0-build-plan.md) is coherent, internally consistent, and built on lessons already paid for in the specialist-agent weekend.

**Per Context A clarification (B / C / 1,3,5): this review confirms the plan with three targeted spot-checks and produces a 7-subtask GuardKit breakdown. No technical options are reopened.**

- Findings: 3 substantive (one per focus area) + 5 decision-point resolutions
- Approach score: 82/100 (plan is sound; the -18 reflects residual integration risk at the MCP/LLM seam and one ambiguous-ownership file)
- Recommendation: **[I]mplement** — generate the 7-subtask breakdown and proceed with reviewer-in-loop `/task-work` execution

---

## Focus Area 1 — Parity surfaces (SR-01 → SR-07)

The plan correctly identifies that parity surfaces are **structural**, not features in their own right, and bakes them into the implementation steps rather than as a separate phase. This is the correct posture. The only two surfaces that need executable code are **SR-01 (stdio discipline)** and **SR-03 (provider resolution at factory)** — both get dedicated unit tests ([phase-0-build-plan.md:453-454](../../docs/research/ideas/phase-0-build-plan.md#L453-L454)). The remaining four are verifications:

- **SR-02** (CWD absolute path) — ensured by the bash wrapper in `scripts/mcp-wrapper.sh`, verified by clean-machine walkthrough
- **SR-04** (`[providers]` extras completeness) — verified by `pip show` per declared provider
- **SR-05** (Dockerfile parity) — pass-through in Phase 0 (no Dockerfile), re-activated in Phase 1
- **SR-06** (`.env` hygiene) — verified by grep for placeholder patterns
- **SR-07** (tool description ≡ behaviour) — read-verification of MCP tool descriptions vs handler behaviour

**Risk flag (balanced stance):** The plan puts parity verification on Sunday morning after end-to-end Saturday work. This matches the specialist-agent pattern and is correct, but it means SR-01 and SR-03 violations only surface 12+ hours after the code is written. **Mitigation:** the `tests/unit/mcp/test_stdio_discipline.py` and `tests/unit/llm/test_provider_resolution.py` tests should be written **Saturday evening at first-commit time**, not Sunday morning. Shifts verification earlier without adding work. Recommend this adjustment be captured in the Sunday-morning subtask's acceptance criteria.

**Spot-check verdict:** Pattern transfer from specialist-agent is low-risk. Both SR-01 and SR-03 bugs in LES1 (TASK-MDF-MCPB, TASK-MDF-PMEV) were *fixed* in specialist-agent; we're copying the fixed pattern, not the buggy one.

## Focus Area 3 — MCP transport + tool contract

The plan specifies four MCP tools and their classifications explicitly ([phase-0-scope.md:167-171](../../docs/research/ideas/phase-0-scope.md#L167-L171)):

| Tool | Class | Description contract | SR-07 validation |
|------|-------|---------------------|------------------|
| `tutor_start_session` | long-running | "returns session_id immediately" | Must return in ≤1s |
| `tutor_turn` | sync | "< 30s target" | Must complete synchronously |
| `tutor_session_status` | sync | "polls session state" | Must be pure read |
| `tutor_session_end` | sync | "triggers async Graphiti write in Phase 1" | Phase 0: no-op; the description must NOT say "async" until Phase 1 |

**Spot-check finding:** The `tutor_session_end` description is currently planned as "triggers async Graphiti write in Phase 1" — this is an SR-07 violation for Phase 0, because in Phase 0 the handler does nothing async (there's no Graphiti yet). **Recommendation:** description must be "marks session ended" in Phase 0, with a code-level `TODO(phase-1): add async Graphiti write` comment. Description and behaviour must match *in this phase*, not a future phase.

**Fire-and-forget pattern transfer:** The plan references copying `specialist-agent/src/specialist_agent/mcp/adapter.py::_start_po_session()` / `_run_po_session()` ([phase-0-build-plan.md:154](../../docs/research/ideas/phase-0-build-plan.md#L154)). This is the proven pattern. Risk is low; the mapping is direct (`start_session` → `start_po_session`, `_run_tutor_session` → `_run_po_session`).

**`tutor_turn` synchronous contract, Ollama round-trip:** The scope says `< 30s target`. Ollama calls on GB10 over Tailscale for a 31B Q4_K_M model: first-token latency ~2-5s, full response for a typical tutor turn ~8-15s. Comfortable headroom, but **first-call warm-up can exceed 30s** if the model isn't already loaded. Mitigation: `tutor_start_session` should trigger a no-op `generate` call to warm the model — this is a one-line addition that turns a flaky 30s timeout edge case into a reliable 10-15s first turn. Capture as acceptance criterion on the MCP adapter subtask.

## Focus Area 5 — Task decomposition granularity

The build plan's natural breakpoints are: morning (FEAT-PO-001 docs), afternoon (scaffold + LLM client + session), evening (MCP skeleton + end-to-end), Sunday morning (parity hardening). These map cleanly to GuardKit task boundaries, but with one caveat: **the Saturday afternoon block is too coarse** — it bundles scaffold (trivial), LLM client (moderate), and session state (trivial) into one undifferentiated chunk. That's fine for a solo weekend but weak for reviewer-in-loop checkpointing.

**Proposed decomposition: 7 subtasks, 3 waves.** Wave 1 is two parallel-safe foundation tasks. Wave 2 is three tasks with a linear dep chain (client → session → adapter). Wave 3 is parity hardening + integration smoke test. Breakdown below in §Proposed Task Breakdown.

**Rejected alternative: one task per parity surface.** Would produce 7+ tasks for verification steps that are mostly grep/pip-show/read-the-description. Over-granular; bundles correctly into Wave 3.

**Rejected alternative: one task for the whole MCP adapter + CLI + wrapper.** Would be a 400-LOC task mixing tool registration, handler logic, CLI argparse, and bash. The three concerns have different reviewer questions ("are the four tools right?" vs "is stdio clean?" vs "does the wrapper use absolute paths?"). Keeping them together obscures review.

---

## Decision-Point Resolutions

| ID | Decision | Resolution | Rationale |
|----|----------|-----------|-----------|
| **D1** | `roles/tutor/role.yaml` — FEAT-PO-001 or FEAT-PO-002? | **FEAT-PO-002** owns the file structure; FEAT-PO-001 owns the `prompts/player.md` content. | The role manifest is infrastructure the MCP server needs to start; the player prompt content is domain substance. Splitting by concern — not by artefact — preserves feature boundaries. |
| **D2** | Unit tests — per-surface or consolidated? | Two code tests (SR-01 stdio, SR-03 provider) as planned. SR-04/05/06/07 folded into a single **verification checklist subtask**, not separate tests. | Matches what's testable in code (SR-01/03) vs what's a one-time shell-level check (SR-04–07). Over-testing config-level invariants adds ceremony without adding rigour. |
| **D3** | Bedrock code in `llm/client.py` from day one? | **Stub only in FEAT-PO-002** (raises `NotImplementedError`). Real impl in FEAT-PO-004. | The plan already says this ([phase-0-build-plan.md:144](../../docs/research/ideas/phase-0-build-plan.md#L144)). The stub establishes the interface FEAT-PO-004 fills. |
| **D4** | `scripts/mcp-wrapper.sh` — FEAT-PO-002 or FEAT-PO-003? | **FEAT-PO-002**. | The wrapper is runtime glue required to start the MCP server. FEAT-PO-003 is documentation and repo packaging; it should *reference* the wrapper, not own it. |
| **D5** | Execution mode — `/task-work` (reviewer-in-loop) or `/feature-build` (autonomous)? | **`/task-work`** reviewer-in-loop. | Plan explicitly recommends this for FEAT-PO-002 ([phase-0-build-plan.md:419](../../docs/research/ideas/phase-0-build-plan.md#L419)): "critical path, parity surfaces". Autonomous build is reserved for doc-heavy features. |

---

## Proposed Task Breakdown

### Wave 1 — Foundation (Saturday afternoon, parallel-safe)

| ID | Title | task_type | Complexity | Est. | Deps |
|----|-------|-----------|-----------|------|------|
| TASK-PO02-001 | Python package scaffold (pyproject.toml, src/ tree, AGENTS.md, .env.example, .gitignore, .mcp.json) | scaffolding | 3 | 60 min | — |
| TASK-PO02-002 | Role manifest + player prompt shell (roles/tutor/role.yaml, roles/tutor/prompts/player.md placeholder) | declarative | 2 | 30 min | — |

### Wave 2 — Runtime implementation (Saturday evening, linear chain)

| ID | Title | task_type | Complexity | Est. | Deps |
|----|-------|-----------|-----------|------|------|
| TASK-PO02-003 | LLM client with provider resolution — Ollama path + Bedrock stub + `_default_player_model()` | feature | 4 | 75 min | TASK-PO02-001 |
| TASK-PO02-004 | In-memory tutor session state (`src/study_tutor/session/tutor_session.py`) | feature | 3 | 45 min | TASK-PO02-001 |
| TASK-PO02-005 | MCP adapter + CLI + bash wrapper (4 tools, stdio serve, `scripts/mcp-wrapper.sh`, Claude Desktop config snippet) | feature | 6 | 120 min | TASK-PO02-002, TASK-PO02-003, TASK-PO02-004 |

### Wave 3 — Parity hardening + integration (Sunday morning, parallel-safe)

| ID | Title | task_type | Complexity | Est. | Deps |
|----|-------|-----------|-----------|------|------|
| TASK-PO02-006 | Parity surface verification + unit tests (test_stdio_discipline.py, test_provider_resolution.py, SR-02/04/06/07 checklist) | testing | 4 | 75 min | TASK-PO02-005 |
| TASK-PO02-007 | Claude Desktop integration + first-call smoke test (live `tutor_turn` against fine-tuned Gemma 4 via Ollama) | integration | 3 | 45 min | TASK-PO02-005 |

**Total: 7 subtasks, ~7½ hours of focused work, matching the plan's 9-hour Saturday (allows for 1½ hours of context-switching and debugging).**

**Parallel groups (waves):**
- Wave 1: `[TASK-PO02-001, TASK-PO02-002]`
- Wave 2: `[TASK-PO02-003, TASK-PO02-004]` then `[TASK-PO02-005]`
- Wave 3: `[TASK-PO02-006, TASK-PO02-007]`

---

## §4 Integration Contracts

Four cross-task data dependencies exist. Each must be specified so consumer tasks can implement against a fixed interface.

### Contract: AGENT_MODELS__REASONING_MODEL
- **Producer task:** TASK-PO02-001 (writes placeholder in `.env.example`)
- **Consumer task:** TASK-PO02-003 (reads via `os.environ` in `_default_player_model()`)
- **Artifact type:** environment variable
- **Format constraint:** string ∈ `{"local", "bedrock", "openai", "anthropic", "gemini"}`. Phase 0 valid values: `"local"` (Ollama on GB10, default) or `"bedrock"` (raises `NotImplementedError` until FEAT-PO-004).
- **Validation method:** `tests/unit/llm/test_provider_resolution.py` covers the env-var → factory flow end-to-end (SR-03).

### Contract: Role manifest path
- **Producer task:** TASK-PO02-002 (writes `roles/tutor/role.yaml` at a known relative path)
- **Consumer task:** TASK-PO02-005 (MCP adapter + CLI resolve role from `roles/<role>/role.yaml` at repo root; role name comes from `serve --role tutor`)
- **Artifact type:** filesystem path
- **Format constraint:** path resolves from an **absolute repo root** set by the bash wrapper per SR-02. Relative resolution from CWD is not acceptable.
- **Validation method:** clean-machine walkthrough loads `role tutor` from a fresh clone; SR-02 check verifies absolute-path wrapper.

### Contract: Tutor session interface
- **Producer task:** TASK-PO02-004 (defines `TutorSession` with `session_id`, `turns: list`, `get/append_turn()` methods)
- **Consumer task:** TASK-PO02-005 (MCP adapter's `_run_tutor_session()` and `tutor_turn` handler)
- **Artifact type:** Python class / in-memory interface
- **Format constraint:** Phase-0 in-memory only. Must NOT block Phase 1 Graphiti integration — session data model should be a plain dataclass (easily serialisable) not a stateful engine.
- **Validation method:** Code review at Coach validation; specifically verify no persistent-state assumptions leak into the interface.

### Contract: LLM client interface
- **Producer task:** TASK-PO02-003 (`LLMClient.generate(prompt, system, ...) -> str`)
- **Consumer task:** TASK-PO02-005 (called from MCP handler per turn)
- **Artifact type:** Python class / method
- **Format constraint:** Synchronous call, string-in / string-out. Response streaming is out-of-scope for Phase 0 (MCP `tutor_turn` is sync per SR-07).
- **Validation method:** Unit test in `test_provider_resolution.py` uses a stubbed client; TASK-PO02-007 smoke test exercises the real path.

---

## Risk Register (Balanced)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `tutor_start_session` timeout due to Ollama cold-start on first call | Medium | Low | Warm-up no-op `generate()` in `start_session` handler (1-line addition in TASK-PO02-005) |
| SR-07 violation in `tutor_session_end` description (says "async Graphiti" but handler is no-op in Phase 0) | High | Medium | TASK-PO02-005 acceptance: descriptions match Phase-0 behaviour; Phase-1 update captured as `TODO(phase-1)` |
| Role manifest schema diverges from specialist-agent, breaking future Coach integration in Phase 1 | Low | Medium | TASK-PO02-002 copies `specialist-agent/roles/product-owner/role.yaml` verbatim as starting shape |
| Parity surface verification on Sunday catches an SR-01 violation from Saturday | Medium | Low | Write parity unit tests at first commit (Saturday evening), not Sunday — shift-left verification |
| Session state design leaks assumptions that block Graphiti in Phase 1 | Low | Medium | Keep `TutorSession` as a plain dataclass, no engine logic in Phase 0 (captured in Contract #3) |

---

## Recommendation

**[I]mplement** with the 7-subtask breakdown above.

Rationale: The build plan is authoritative and the clarified review stance (confirm + spot-checks, balanced) supports implementation now rather than further analysis. The three findings (early parity tests, SR-07 session_end wording, Ollama cold-start warm-up) are **inline acceptance-criteria additions**, not reasons to revise the plan structure. The five decision-point resolutions remove ambiguity cleanly.

Execution mode: **`/task-work TASK-PO02-XXX`** reviewer-in-loop, per plan's explicit recommendation for critical-path code. No `/feature-build` autonomous run for FEAT-PO-002.

---

## Decision Checkpoint

The review is complete. Awaiting human decision.

- **[A]ccept** — archive report, keep the 7-task breakdown for later
- **[R]evise** — re-run with different focus (e.g. shift to Phase 1 forward-compatibility, or re-open technical options)
- **[I]mplement** — generate subtask files + IMPLEMENTATION-GUIDE.md + `.guardkit/features/FEAT-PO-002.yaml`
- **[C]ancel** — discard review
