# Feature: Graphiti Runtime Integration Repair (FEAT-FD32)

**Status**: Planned (5 waves, sequential)
**Parent task**: [TASK-PH2-GR-001](../TASK-PH2-GR-001-graphiti-runtime-integration-repair.md)
**Review task**: [TASK-REV-GR1A](../../in_review/TASK-REV-GR1A-plan-graphiti-runtime-integration-repair.md)
**Spec & scenarios**: [features/graphiti-runtime-integration-repair/](../../../features/graphiti-runtime-integration-repair/) (24 BDD scenarios)
**Implementation guide**: [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)

## Problem

[`get_client()`](../../../src/study_tutor/knowledge/graphiti_client.py#L262-L341) constructs `Graphiti(graph_driver=driver)` with no `llm_client`, no `embedder`, no `cross_encoder`. graphiti-core 0.29 silently defaults all three to OpenAI clients keyed off `OPENAI_API_KEY` (set to placeholder `not_needed`), so every `add_episode` returns 401. Phase 1 tests didn't catch this because every graphiti test mocks the integration; nothing in `tests/` ever booted a real `Graphiti` instance.

This is the root cause of Phase 1's falsified gate items: G2, G3, G4, G5, G6, G13.

## Solution

Mirror the GuardKit-canonical wiring pattern from `guardkit/guardkit/knowledge/graphiti_client.py`:
- `_build_llm_client(config)` → `OpenAIGenericClient` pointing at local llama-swap on `:9000`.
- `_build_embedder(config)` → `OpenAIEmbedder` pointing at the same local endpoint.
- `_build_cross_encoder_sentinel()` → opaque object that raises on access (DECISION-DF-001 enforcement).

Load configuration from `.guardkit/graphiti.yaml` via a new `load_graphiti_config_from_yaml()` helper that rejects cloud providers at config-load time.

Verify with a two-layer smoke test (constructor-shape always-on + env-gated live FalkorDB round-trip), re-seed Lilymay against live FalkorDB, and conduct an end-to-end MCP demo session through Claude Desktop to flip the Phase 1 gate items.

## Subtasks (5 waves, strictly sequential)

| Wave | Task | Goal | Complexity | Estimate |
|---|---|---|---|---|
| 1 | [TASK-GR-LOAD](./TASK-GR-LOAD-yaml-loader-and-decision-df-001-guard.md) | YAML loader + DECISION-DF-001 guard | 4 | ~30m |
| 2 | [TASK-GR-WIRE](./TASK-GR-WIRE-build-llm-client-and-embedder-with-cross-encoder-sentinel.md) | `_build_llm_client` + `_build_embedder` + cross-encoder sentinel | 5 | ~60m |
| 3 | [TASK-GR-SMOK](./TASK-GR-SMOK-graphiti-runtime-smoke-test.md) | Constructor-shape test (always) + env-gated live FalkorDB round-trip | 4 | ~45m |
| 4 | [TASK-GR-SEED](./TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md) | Re-seed Lilymay + flip G2/G3 to Held | 4 | ~30m + ~30m seed runtime |
| 5 | [TASK-GR-DEMO](./TASK-GR-DEMO-end-to-end-mcp-tutor-session.md) | MCP demo through Claude Desktop + flip G4/G5/G6/G13 to Held | 3 | ~45m |

**Aggregate complexity**: 20. **Total wall-clock**: ~3.5 to 4 hours of working time, plus the LLM-bound seed runtime.

## Hard constraints

- **DECISION-DF-001**: No cloud LLM/embedding APIs on the critical path. Triggered by a £30 Gemini overspend in 3 days; cloud providers off-limits even as fallbacks unless explicitly approved per-task.
- **All inference via llama-swap on `:9000`** (Tailscale: `http://promaxgb10-41b1:9000/v1`). MacBook ollama is the documented fallback.
- **GuardKit-canonical wiring pattern** — mirror `_build_llm_client` / `_build_embedder` from the GuardKit client; do not invent.
- **Cross-encoder NOT defaulted to OpenAI silently** — sentinel object that raises on first attribute access.
- **Loader path** for `.guardkit/graphiti.yaml` integration. Schema unification deferred to TASK-PH2-GR-002.

## Architecture review summary

- **Score**: 78/100 (review report at [.claude/reviews/TASK-REV-GR1A-review-report.md](../../../.claude/reviews/TASK-REV-GR1A-review-report.md))
- **Hardenings beyond parent ACs**:
  - F4: Cross-encoder uses sentinel object, not just a WARN log (silent £30/week budget leak prevention).
  - F5: Smoke test split into always-on constructor-shape + env-gated live round-trip (CI-friendly without losing transport-level coverage).
  - F7: Constructor-shape test asserts exact kwarg names — catches graphiti-core 0.30 drift before it ships.

## How to execute

### Sequential (recommended for first run)

```bash
# Wave 1
/task-work TASK-GR-LOAD
/task-complete TASK-GR-LOAD

# Wave 2 (depends on Wave 1's loader + extended config schema)
/task-work TASK-GR-WIRE
/task-complete TASK-GR-WIRE

# Wave 3 (depends on Wave 2's wired client)
/task-work TASK-GR-SMOK
/task-complete TASK-GR-SMOK

# Sanity check before seeding
STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 pytest tests/smoke/test_graphiti_live_smoke.py -v

# Wave 4 (long-running due to LLM-bound seed)
/task-work TASK-GR-SEED
/task-complete TASK-GR-SEED

# Wave 5 (open Claude Desktop, conduct the live session)
/task-work TASK-GR-DEMO
/task-complete TASK-GR-DEMO

# Wrap-up
/task-complete TASK-PH2-GR-001       # parent feature
/task-complete TASK-REV-GR1A         # review task
```

### Autobuild (per Q2 = D detect-automatically)

```bash
/feature-build FEAT-FD32
```

`/feature-build` reads `.guardkit/features/FEAT-FD32.yaml`, sees five waves of one task each, and runs them serially. Wave 5 (TASK-GR-DEMO) requires human-in-the-loop — autobuild will pause for the live session per AC-DEMO-01.

## Phase 1 closure mapping

This feature flips the entire Phase 1 falsification cluster:

| Gate | Wave that closes it | Evidence type |
|---|---|---|
| G2 | Wave 4 (Seed) | Seed log + `mcp__graphiti__search_nodes` JSON |
| G3 | Wave 4 (Seed) + Wave 5 (Demo confirmation) | `get_student_state` JSON |
| G4 | Wave 5 (Demo) | MCP session log excerpt |
| G5 | Wave 5 (Demo) | Coach revision excerpt |
| G6 | Wave 5 (Demo) | `mcp__graphiti__get_episodes` JSON |
| G13 | Wave 5 (Demo) | Session log + p50/p95 latency |

Phase 1 becomes structurally complete on its own terms. FEAT-PH2-001 (gamification) is unblocked.
