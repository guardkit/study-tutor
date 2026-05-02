# Review Report: TASK-REV-GR1A — Plan: Graphiti Runtime Integration Repair

## Executive Summary

Decision-mode review. The parent task **TASK-PH2-GR-001** is exhaustively specified (8 ACs, 5-risk register, 5-wave implementation hint) and the diagnosis is verified against the current `src/study_tutor/knowledge/graphiti_client.py` — `get_client()` at [graphiti_client.py:305](../../src/study_tutor/knowledge/graphiti_client.py#L305) constructs `Graphiti(graph_driver=driver)` with no `llm_client`, no `embedder`, no `cross_encoder`. graphiti-core 0.29 silently defaults all three to OpenAI clients keyed off `OPENAI_API_KEY`, which 401s on every `add_episode`. The Phase 1 falsification cluster (G2/G3/G4/G5/G6/G13) is mechanically explained by this single missing-kwargs bug.

**Recommendation: [I]mplement** with the 5-wave breakdown from the parent task's "Implementation hint" section. The waves map cleanly to the 8 ACs, the dependency chain is strictly sequential between waves (Wave N+1 cannot run before Wave N), and one in-wave parallel opportunity exists between AC-001 and AC-002 inside Wave 2. The Loader path (per Q2 default) is the right call for blast-radius reasons — schema unification stays in TASK-PH2-GR-002.

**Architecture score: 78/100** (deductions: cross-encoder guard policy needs tightening per AC-003 risk flag; smoke test gating in CI is unspecified; integration contract between loader and wired client needs a §4 entry to prevent the same kwarg-drift bug recurring in graphiti-core 0.30).

## Review Details

- **Mode**: decision
- **Depth**: standard
- **Reviewer**: software-architect (synthesis) + architectural-reviewer (AC mapping)
- **Clarification context (from /feature-plan Context A)**:
  - review_depth: D (All layers equally — full architectural pass)
  - conflict_resolution: A (Loader path; defer schema unification)
  - specific_concerns: F (None beyond ACs)
  - output_format: B (AC-compliance + targeted risk flags)
  - smoke_test_scope: A (In-scope — verify drift detection)

## Findings

### F1 — The current bug is precisely the missing-kwargs case

`graphiti_client.py:305` constructs `Graphiti(graph_driver=driver)` with no LLM/embedder/cross_encoder. graphiti-core 0.29 then defaults to OpenAI clients reading `OPENAI_API_KEY` (placeholder `not_needed` in this env). Every `add_episode` returns 401. Phase 1 tests didn't catch it because `tests/unit/knowledge/test_async_write.py:FakeClient` mocks the integration entirely — no test ever booted a real `Graphiti` instance. **Confirmed by direct file read.**

### F2 — `GraphitiConnectionConfig` schema is wrong for the local-only world

Defaults at [graphiti_client.py:81-83](../../src/study_tutor/knowledge/graphiti_client.py#L81-L83): `llm_provider: str = "gemini"`, `llm_model: str = "gemini-2.5-pro"`. These defaults are themselves a DECISION-DF-001 violation — even if the YAML loader does the right thing, anyone constructing `GraphitiConnectionConfig()` directly in tests or scripts gets a Gemini-pointing config. **The Wave 1 loader must override these defaults at construction time, AND a future cleanup should change the dataclass defaults to `vllm` / `qwen-graphiti` / `local-key`.** (The latter is a ≤1-line change but is technically out-of-scope for this repair task per the YAGNI principle stated in `.claude/rules/code-style.md`. Flag for a follow-up.)

### F3 — `embedder_url` field exists but is unused

The current dataclass has an `embedder_url` field (line 83) but nothing reads it — `get_client()` never constructs an embedder. The Wave 2 work makes this field load-bearing. The new loader (Wave 1) needs to map the YAML's `embedding_base_url` to this field, OR the dataclass adds new fields (`embedding_provider`, `embedding_base_url`, `embedding_model`, `embedding_dimensions`) per AC-004. **Recommend adding new fields**, not reusing `embedder_url`, because the existing field has different semantics in test fixtures.

### F4 — Cross-encoder guard policy needs to be stricter than AC-003 currently states

AC-003 asks for an init-time WARN log if cross_encoder is left as graphiti-core's default. WARN logs are easy to miss in production; if a future search code path calls the cross-encoder, it would silently hit OpenAI and burn budget before anyone noticed. **Recommend hardening AC-003**: instead of a WARN log, wrap the cross-encoder slot with a sentinel object that raises `RuntimeError("cross_encoder not wired; reranker calls disabled per DECISION-DF-001")` on any attribute access. graphiti-core's search paths in study-tutor (`EntityNode.get_by_group_ids`/`EntityEdge.get_by_group_ids`) bypass the reranker, so the sentinel is never touched on the happy path; if anyone wires up a search code path that needs reranking, the sentinel raises a loud error at first call instead of a silent £30 Gemini bill.

### F5 — The smoke test (AC-005) needs a clear CI policy

The smoke test design as written boots a real `Graphiti` instance against either (a) a stubbed driver or (b) a live FalkorDB if `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1`. **Open question per Q5 (smoke_test_scope=A)**: GitHub Actions cannot reach `promaxgb10-41b1:9000` (Tailscale only). The test must therefore either:
- (a) Skip cleanly in CI when the env var is unset (decorator: `@pytest.mark.skipif(...)` keyed off the env var), with a separate stubbed-driver test that runs unconditionally and asserts kwarg shape, OR
- (b) Mock the LLM/embedder transport and assert that `Graphiti.__init__` was called WITH the wired clients (constructor-shape assertion, not behaviour assertion).

**Recommend (a) + (b) together**: the constructor-shape assertion catches a future graphiti-core 0.30 kwarg rename (closes the regression scenario from the .feature file), and the live test is the smoke gate that catches transport-level breakage.

### F6 — §4 Integration Contracts are needed

Cross-task data dependencies exist:
- TASK-001 (loader) produces a `GraphitiConnectionConfig` instance → consumed by TASK-002 (wired client)
- TASK-002 (wired client) produces a real `Graphiti` instance → consumed by TASK-003 (smoke test), TASK-004 (seed), TASK-005 (MCP demo)
- TASK-004 (seed) produces FalkorDB rows in `student-lilymay` group_id → consumed by TASK-005 (MCP demo's `tutor_start_session`)

Each is a candidate for the silent-default class of bug. The IMPLEMENTATION-GUIDE.md must list these contracts explicitly.

### F7 — The `@regression` BDD scenario is well-aimed

Scenario: "A graphiti library upgrade that drifts the constructor surface is caught." This is exactly the right regression-prevention scenario — graphiti-core's history shows constructor-surface drift between 0.28 → 0.29 (the bug fixed in commit `a210472` was a casualty of one such drift). The smoke test (per F5(b) above) must include a constructor-shape assertion: `Graphiti.__init__` was called with a non-None `llm_client` AND a non-None `embedder`. This catches the case where graphiti-core 0.30 renames `llm_client` to `llm` and the wiring silently regresses.

### F8 — Wave 4 seed runtime is LLM-bound, not concurrency-bound

Per the parent task's risk register: "Phase-1 latency-spike measured 78s/write (LLM-bound), so 25 sequential writes ≈ 30 min." This means Wave 4 cannot be sped up by raising `chunk_extraction_concurrency` — the bottleneck is the model's tokens/sec on a single `add_episode`, not the fan-out. **Plan accordingly**: Wave 4 has a hard wall-clock floor of ~30 min plus `tutor_session_*` round-trips. Don't promise a faster turnaround.

## AC → Wave Coverage Matrix

| AC | Wave | Scope | Coverage |
|---|---|---|---|
| AC-001 (LLM client wired) | 2 | `_build_llm_client` mirror of guardkit pattern | ✅ Direct |
| AC-002 (embedder wired) | 2 | `_build_embedder` mirror | ✅ Direct |
| AC-003 (cross-encoder guard) | 2 | Sentinel object (per F4) | ⚠️ Tighten — sentinel, not WARN |
| AC-004 (config from YAML) | 1 | `from_yaml` classmethod + DECISION-DF-001 reject | ✅ Direct |
| AC-005 (live smoke test) | 3 | Stubbed-driver test (always) + live test (env-gated) | ⚠️ Add CI policy |
| AC-006 (Lilymay seed) | 4 | `python scripts/seed_student_model.py` against FalkorDB | ✅ Direct |
| AC-007 (MCP demo session) | 5 | Claude Desktop tutor_start → 5–7× tutor_turn → tutor_session_end | ✅ Direct |
| AC-008 (phase-1-validation update) | 4 (or 5) | Flip G2/G3/G4/G5/G6/G13 from Falsified to Held | ✅ Direct |

**No AC is uncovered.** Three need targeted risk-flag refinement (AC-003, AC-005, AC-008's evidence standard).

## Recommended Approach

### Wave breakdown (5 waves, 5 subtasks)

```
Wave 1: TASK-LOAD  — `from_yaml` loader + DECISION-DF-001 guard          (~30 min)  complexity 4
                     ↓ produces GraphitiConnectionConfig
Wave 2: TASK-WIRE  — `_build_llm_client` + `_build_embedder` + sentinel  (~60 min)  complexity 5
                     ↓ produces wired Graphiti
Wave 3: TASK-SMOKE — Constructor-shape test (always) + live test (gated) (~45 min)  complexity 4
                     ↓ verifies wiring
Wave 4: TASK-SEED  — Re-seed Lilymay + flip phase-1-validation gate     (~30+30 min) complexity 4
                     ↓ produces live FalkorDB rows
Wave 5: TASK-DEMO  — End-to-end MCP demo session via Claude Desktop      (~30-45 min) complexity 3
                     ↓ closes G3/G4/G5/G6/G13
```

**Total complexity: 20** (aggregated). Aligns with parent task's complexity 5 (per-task average).

**Sequential dependencies are non-negotiable**:
- Wave 2 cannot run before Wave 1 (needs the loader's config).
- Wave 3 cannot run before Wave 2 (needs the wired client to test).
- Wave 4 cannot run before Wave 3 (don't seed against an unverified client — that's how Phase 1 got into this mess).
- Wave 5 cannot run before Wave 4 (MCP demo needs Lilymay's baseline in FalkorDB).

**One in-wave parallel opportunity**: AC-001 and AC-002 inside Wave 2 are independent — they're sibling helper functions. Could be split if useful, but the savings are marginal (both are small) and splitting doubles the integration-test surface. **Recommend keeping them as one task.**

### §4 Integration Contracts

Four contracts to document in IMPLEMENTATION-GUIDE.md:

1. **GraphitiConnectionConfig schema** (Wave 1 → Wave 2)
   - Producer: TASK-LOAD's `load_graphiti_config_from_yaml()`
   - Consumer: TASK-WIRE's `get_client()`
   - Format: must have non-None `llm_provider in ("vllm","ollama")`, `llm_base_url`, `llm_model`, `embedding_provider in ("vllm","ollama")`, `embedding_base_url`, `embedding_model`. Cloud providers MUST raise at load time.
   - Validation: TASK-WIRE's smoke test asserts `config.llm_provider != "openai" and != "gemini"`.

2. **Wired Graphiti client** (Wave 2 → Waves 3/4/5)
   - Producer: TASK-WIRE's `get_client()`
   - Consumer: TASK-SMOKE, TASK-SEED, TASK-DEMO
   - Format: real `Graphiti` instance with `llm_client is not None`, `embedder is not None`, `cross_encoder` is the sentinel object (F4).
   - Validation: TASK-SMOKE constructor-shape test asserts these non-None / sentinel invariants.

3. **Lilymay seed** (Wave 4 → Wave 5)
   - Producer: TASK-SEED's `seed_student_model.py` run
   - Consumer: TASK-DEMO's `tutor_start_session`
   - Format: 25 entity writes succeed; `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity; `get_student_state(client, "lilymay")` returns non-empty `StudentState`.
   - Validation: TASK-DEMO loads Lilymay state at session-start; failure → cannot tutor.

4. **MCP session episode** (Wave 5 self-contained, but must close Phase 1 gate)
   - Producer: TASK-DEMO's `tutor_session_end`
   - Consumer: phase-1-validation.md (G3/G4/G5/G6/G13)
   - Format: `session_completed` episode written to Graphiti, visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. Capture turn p50/p95.
   - Validation: Phase 1 gate flip recorded with live evidence inline.

### Mermaid diagrams (will be in IMPLEMENTATION-GUIDE.md)

- **Data Flow**: write paths (`get_client` → `add_episode` → FalkorDB) and read paths (`EntityNode.get_by_group_ids` → query consumers). All paths connected (no NOT WIRED dotted edges expected post-repair).
- **Integration Contracts**: sequence diagram showing Loader → Wired Client → Smoke / Seed / Demo, with the cross_encoder sentinel called out as a Note.
- **Task Dependency Graph**: linear chain Wave1 → Wave2 → Wave3 → Wave4 → Wave5 (no parallel-safe siblings to colour green).

## Risk Register Carry-Through (per Q4 = output_format B)

The 5 risks from the parent task all stay relevant. Re-stated with wave assignments:

| Risk | Wave | Mitigation status |
|---|---|---|
| MacBook ollama offline at seed time | 4 | YAML toggle to GB10 (single-line). Acceptable. |
| GB10 rate-limits at 25 concurrent writes | 4 | `chunk_extraction_concurrency: 4` already in YAML; Phase-1 78s/write means LLM-bound, not concurrency-bound (F8). |
| GB10 down during repair | 4 | MacBook fallback active. Repair slips with GB10 outage; Phase 2 day-by-day already plans for this. |
| `OpenAIGenericClient` API drift in graphiti-core minor bumps | 2, 3 | Pin `>=0.29,<0.30` in pyproject.toml (Wave 2). Smoke test constructor-shape assertion (Wave 3) catches drift on next bump. **F7 confirms this is well-aimed.** |
| Stale FalkorDB indices | 4 | If `Connection closed by server` reappears post-fix, drop graph via `redis-cli -h whitestocks -p 6379 GRAPH.DELETE study_tutor` and re-seed. |

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|---|---|---|---|---|
| Loader path (defer schema unify to TASK-PH2-GR-002) | 78/100 | 4h + ~30min seed | Low | ✅ **Recommended** |
| Schema-replace path (unify GraphitiConnectionConfig directly) | 65/100 | 8h+ | Medium | ❌ Defer — bigger blast radius, no Phase-2 benefit |
| Direct-wire to Gemini (rescinded earlier draft) | N/A | N/A | Critical | ❌ DECISION-DF-001 violation |
| No-op (keep Phase 1 falsified) | 0/100 | 0h | Critical | ❌ Blocks FEAT-PH2-001 |

## Recommendations Summary (in implementation order)

1. **Wave 1**: Add `load_graphiti_config_from_yaml(path: Path) -> GraphitiConnectionConfig` and reject `llm_provider in ("openai","gemini")` / `embedding_provider == "openai"` at load time with structured log lines. (AC-004, partially AC-001/AC-002.)
2. **Wave 2**: Mirror guardkit's `_build_llm_client` + `_build_embedder` patterns inside `get_client()`. Add a sentinel object for `cross_encoder` (F4 hardening of AC-003). (AC-001, AC-002, AC-003.)
3. **Wave 3**: Add `tests/smoke/test_graphiti_live_smoke.py` with two layers — unconditional constructor-shape assertion (catches graphiti-core 0.30 drift, F7) + env-gated live FalkorDB round-trip (catches transport breakage). CC-13 regex audit re-runs. (AC-005.)
4. **Wave 4**: Run `python scripts/seed_student_model.py` against live FalkorDB. Capture evidence inline in `phase-1-validation.md`, flipping G2/G3/G4/G5/G6/G13 from "Falsified" to "Held". (AC-006, partial AC-008.)
5. **Wave 5**: End-to-end MCP demo via Claude Desktop. Capture turn p50/p95. Confirm `session_completed` episode written. Final phase-1-validation.md flip (or move from Wave 4 if cleaner). (AC-007, completes AC-008.)

## Decision Checkpoint

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete for: Plan: Graphiti Runtime Integration Repair

Architecture score: 78/100
Findings: 8
Recommendations: 5 (one per wave)

Recommended approach: Loader path (Q2 default), 5-wave breakdown,
                      tightened cross-encoder guard (sentinel not WARN),
                      smoke test as constructor-shape + env-gated live round-trip.

Options:
  [A]ccept    - Save findings; create implementation tasks manually later
  [R]evise    - Request deeper analysis on a specific finding
  [I]mplement - Generate the 5-wave subtask structure + structured feature YAML
                + Mermaid diagrams + §4 Integration Contracts in
                IMPLEMENTATION-GUIDE.md (RECOMMENDED)
  [C]ancel    - Discard plan
```
