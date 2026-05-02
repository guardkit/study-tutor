---
id: TASK-PH2-GR-001
title: Graphiti runtime integration repair — wire Gemini LLM + GB10 embedder + cross-encoder
task_type: feature
parent_validation: phase-1-validation.md
phase: 2
implementation_mode: design-first
complexity: 6
estimated_minutes: 240
status: backlog
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
dependencies: []
blocks:
- FEAT-PH2-001
tags:
- graphiti
- llm-wiring
- embedder
- phase-1-falsification-repair
- runtime-integration
- ahead-of-FEAT-PH2-001
---

# Graphiti runtime integration repair

## Why this exists

Phase 1 close-out gate (`docs/research/ideas/phase-1-validation.md`) falsified Phase 1 success criteria G2, G3, G4, G5, G6, and G13. Root cause: `src/study_tutor/knowledge/graphiti_client.py:get_client(config)` constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, and no `cross_encoder`**, so graphiti-core 0.29 defaults all three to OpenAI clients keyed off `OPENAI_API_KEY` (which in this project is the placeholder `not_needed`). Every `add_episode` call (which graphiti-core implements as an LLM-driven entity-extraction round-trip) 401s against OpenAI before reaching FalkorDB. The Phase 1 autobuild stayed green because every graphiti test mocks the integration; nothing in `tests/` ever booted a real `Graphiti` instance.

This task is the Phase 2 leading task — must land **before** FEAT-PH2-001 spec + plan because gamification reads `get_student_state` and writes `GamificationState` through the same broken client path.

## Acceptance criteria

1. **AC-001 — Gemini LLM client wired.** `get_client(config)` constructs a Gemini-backed `LLMClient` keyed off `GOOGLE_API_KEY` and `config.llm_model` (default `"gemini-2.5-pro"`) and passes it to `Graphiti(...)`. Whatever `graphiti-core[<extra>]` install gives us the Gemini client class is added to the Phase 1 setup checklist in `phase-1-build-plan.md` (and to a new `[knowledge-graph]` extra in `pyproject.toml` so future `uv pip install` / `pip install -e .[knowledge-graph]` runs are reproducible).
2. **AC-002 — Custom-URL embedder wired.** `get_client` constructs an embedder pointing at `config.embedder_url` (default `"http://promaxgb10-41b1:8001/v1"` — the GB10 vLLM service) and passes it to `Graphiti(...)`. If the embedder client class needs an extra, it's bundled into the same `[knowledge-graph]` extra as AC-001.
3. **AC-003 — Cross-encoder wired (or explicitly disabled).** Decide between (a) wiring a Gemini-backed cross-encoder, (b) wiring a no-op stub that bypasses reranking, or (c) leaving the OpenAI default and documenting that retrieval reranking is degraded. Ship one of these and document the choice inline. The decision must not silently cost OpenAI tokens at runtime — that's the failure mode we just dug ourselves out of.
4. **AC-004 — Smoke test exercising live graphiti-core.** New `tests/smoke/test_graphiti_live_smoke.py` (or equivalent location) that boots a `Graphiti` instance against a stubbed driver and exercises one round-trip: `add_episode(...)` → `EntityNode.get_by_group_ids(...)` → assertion that the episode is reachable. The test must fail loudly if `LLMClient`/`Embedder`/`CrossEncoder` defaults regress to OpenAI in future. The CC-13 regex audit (single `add_episode(` call site in `src/`) continues to pass.
5. **AC-005 — `python scripts/seed_student_model.py` lands Lilymay's baseline against the live Synology FalkorDB.** All 25 entity writes succeed. `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity with the expected attributes. `get_student_state(client, "lilymay")` returns a non-empty `StudentState` (year_group=11, target_grade="8", non-empty subjects, non-empty topic_confidences). Re-running the seed is idempotent (`event=seeding_skipped`).
6. **AC-006 — End-to-end demo session via MCP runs at least once.** `tutor_start_session` → 5–7× `tutor_turn` → `tutor_session_end` from Claude Desktop, with at least one Coach revision observed and a `session_completed` episode written to Graphiti and visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. This unblocks Phase 1 G3 + G4 + G5 + G6 + G13. Capture turn p50/p95 latency in `phase-1-validation.md` (revisit trigger flagged in `phase-2-build-plan.md §"What is TBD"`).
7. **AC-007 — `phase-1-validation.md` updated.** The five falsified items (G2, G3, G4, G5, G6, G13) flip from "Falsified" to "Held" with the live evidence inline. Phase 1 is then structurally complete on its own terms.

## Out of scope

- **Coach calibration pass** (separate Phase 2 nice-to-have per `phase-2-build-plan.md §"Should be green; can absorb on Saturday morning"`). The repair task only needs the runtime to work; it doesn't need the Coach to be optimally tuned.
- **Multi-student support.** Single-student (Lilymay) is the Phase 1+2 invariant.
- **Index migration.** If FalkorDB has stale indices from earlier seed attempts that produce `Connection closed by server` warnings during `build_indices_and_constraints`, those warnings are background-task noise that don't block the main flow. Investigate only if the warnings escalate into actual write failures after the LLM/embedder fixes land.
- **Adding gamification fields to `tutor_session_end`** — that's FEAT-PH2-001 item 4 and stays in FEAT-PH2-001's own subtask list.

## Already-fixed-in-flight (commit before starting this task)

These three patches landed during the close-out gate run on 2026-05-02 and are awaiting commit. They're prerequisites for this task — both because they're on the same call path and because they're standalone API-correctness wins regardless of the LLM-wiring outcome.

- **Read API**: `queries.py:_read_student_partition` seam now calls `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` on the driver, with a duck-typed shortcut for legacy `search_nodes`/`search_memory_facts` test mocks. `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` swallowed (bootstrap case).
- **Write API**: `async_write.py:_add_episode_kwargs` builds graphiti-core 0.29's real signature: `source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]` (singular). Flush-id audit string still rides into structured logs unchanged.
- **Group-id format**: `student:` → `student-`, `subject:` → `subject-`, `fleet:appmilla` → `fleet-appmilla` (graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`). Constants in `student_model.py` updated; module docstring updated; cross-repo divergence note preserved; tests updated in `test_student_model.py`, `test_graphiti_client.py`, `test_session_end.py`, `test_async_write.py`.

Tests at 695/696 (the one failure is a pre-existing dev-machine `mypy`-on-system-Python env issue from FEAT-PH1-002, not introduced by this work).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini rate limits hit during 25-entity seed | Medium | Medium | Seed serially with a small inter-write delay; the script already drains via `helper.drain()` so a slow path is acceptable. Per the 2026-04-27 latency spike, `add_episode` median is 78s — 25 sequential writes is ~30 min. Acceptable for a one-off seed. |
| Embedder URL unreachable at smoke-test time | Medium | Low | The smoke test (AC-004) uses a stubbed driver, not the live FalkorDB; embedder reachability only matters at AC-005 / AC-006 time. If GB10 is down, defer AC-005/006 by the GB10 outage duration; fall back to a local embedder for the demo if outage persists past Saturday afternoon. |
| Cross-encoder choice (AC-003) blocks on a graphiti-core API decision | Low | Low | Default to (b) — a no-op cross-encoder stub — if the wired option doesn't surface cleanly. Reranking quality is not load-bearing for the Phase 2 demo. |
| Stale indices on FalkorDB from earlier broken seed attempts | Medium | Low | The `Connection closed by server` warning during `build_indices_and_constraints` looked like a transient FalkorDB-side issue, not a hard blocker. If it returns post-fix, drop the `study_tutor` database and re-create. |

## Implementation hint (non-binding — re-derive during `/feature-plan`)

Likely subtask shape (3–4 waves, ~5 subtasks):

- **Wave 1 — `pyproject.toml` `[knowledge-graph]` extra + setup-checklist update.** Declare the Gemini + embedder extras. ~15 min.
- **Wave 2 — `get_client` LLM/embedder/cross-encoder construction.** New helper functions + integration into `get_client`. ~60 min.
- **Wave 3 — Live smoke test + CC-13 regex audit verification.** ~45 min.
- **Wave 4 — Re-run seed, capture verification evidence (`mcp__graphiti__search_nodes` output), update `phase-1-validation.md`.** ~30 min plus the seed's own ~30 min LLM-bound runtime.
- **Wave 5 — End-to-end demo session via MCP, capture turn p50/p95.** ~30–45 min.

Total: ~half a day (4 hours) plus the seed's LLM-bound runtime.

## Cross-references

- `docs/research/ideas/phase-1-validation.md` — the gate that falsified G2/G3/G4/G5/G6/G13 and triggered this task.
- `docs/research/ideas/phase-1-scope.md §FEAT-PH1-001` "Group IDs" — original colon-form spec; superseded by the dash-form note in `student_model.py`.
- `docs/research/ideas/phase-2-build-plan.md §"Day 1"` — must be amended to insert this task between the validation gate and FEAT-PH2-001 spec + plan.
- `docs/research/ideas/graphiti-latency-spike-results.md` — `add_episode` median 78s; informs the seed-runtime estimate.
- `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` — the mocks that let the integration drift through Phase 1; AC-004's smoke test is the regression-prevention complement.
