---
id: TASK-PH2-GR-001
title: Graphiti runtime integration repair — wire local LLM + embedder via llama-swap (no cloud APIs)
task_type: feature
parent_validation: phase-1-validation.md
phase: 2
implementation_mode: design-first
complexity: 5
estimated_minutes: 240
status: completed
completed: 2026-05-07T00:00:00+00:00
completed_location: tasks/completed/TASK-PH2-GR-001/
completion_reason: "Closed by TASK-GR-DEMO AC-DEMO-06 on 2026-05-07. All five wave subtasks (TASK-GR-LOAD, TASK-GR-WIRE, TASK-GR-SMOK, TASK-GR-SEED, TASK-GR-DEMO) shipped. Live demo on 2026-05-07 confirmed end-to-end Graphiti runtime integration via the new wired client; G3/G4/G5/G6/G13 flipped to Held in phase-1-validation.md."
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-07T00:00:00+00:00
previous_state: backlog
dependencies: []
blocks:
- FEAT-PH2-001
related:
- TASK-PH2-GR-002
- guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md
review_task: TASK-REV-GR1A
feature_id: FEAT-FD32
subtasks:
- TASK-GR-LOAD   # Wave 1 — YAML loader + DECISION-DF-001 guard
- TASK-GR-WIRE   # Wave 2 — _build_llm_client + _build_embedder + cross-encoder sentinel
- TASK-GR-SMOK   # Wave 3 — Smoke test (constructor-shape + env-gated live)
- TASK-GR-SEED   # Wave 4 — Re-seed Lilymay + flip G2/G3
- TASK-GR-DEMO   # Wave 5 — End-to-end MCP demo + flip G4/G5/G6/G13
tags:
- graphiti
- llm-wiring
- embedder
- llama-swap
- local-only
- no-cloud-api
- dark-factory
- phase-1-falsification-repair
- runtime-integration
- ahead-of-FEAT-PH2-001
---

# Graphiti runtime integration repair

## Why this exists

Phase 1 close-out gate (`docs/research/ideas/phase-1-validation.md`) falsified G2/G3/G4/G5/G6/G13. Root cause: [`src/study_tutor/knowledge/graphiti_client.py:get_client(config)`](../../src/study_tutor/knowledge/graphiti_client.py) constructs `Graphiti(graph_driver=driver)` with **no `llm_client`, no `embedder`, no `cross_encoder`**, so graphiti-core 0.29 defaults all three to OpenAI clients keyed off `OPENAI_API_KEY` (`not_needed` placeholder) and 401s on every `add_episode`. The Phase 1 autobuild stayed green because every graphiti test mocks the integration; nothing in `tests/` ever booted a real `Graphiti` instance.

This task is the Phase 2 leading task — must land **before** FEAT-PH2-001 spec + plan because gamification reads `get_student_state` and writes `GamificationState` through the same client path.

## Hard constraints

### No cloud LLM/embedding APIs on the critical path (DECISION-DF-001)

Per [`guardkit/docs/research/dgx-spark/README.md`](../../../guardkit/docs/research/dgx-spark/README.md): _"DECISION-DF-001: No cloud API on dark factory critical path (triggered by £30 Gemini spend in 3 days)."_ All Graphiti LLM and embedding traffic must hit the local GB10 fleet, not OpenAI/Gemini/Anthropic. The earlier draft of this task mentioned wiring `GeminiClient` as the LLM — **rescinded**. Cloud providers are off-limits even as fallbacks unless explicitly approved per-task.

### All inference goes through llama-swap on `:9000`

The DGX Spark stack was migrated 2026-04-29 from vLLM (ports 8000/8001) to all-llama.cpp via llama-swap on a single port `:9000`. Reference: [`guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md`](../../../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md). Models accessed via llama-swap aliases:

| Alias | Model | Role |
|---|---|---|
| `qwen-graphiti` | Qwen2.5-14B-Instruct FP8 | Graphiti entity extraction (the LLM `add_episode` calls) |
| `nomic-embed` | nomic-embed-text-v1.5 (768 dims) | Embeddings for Graphiti + ChromaDB |

Endpoint: `http://promaxgb10-41b1:9000/v1` (Tailscale hostname). Single OpenAI-compatible interface for both LLM and embedder.

### Use the GuardKit-canonical wiring pattern

GuardKit has the solved 2496-line client at [`guardkit/guardkit/knowledge/graphiti_client.py`](../../../guardkit/guardkit/knowledge/graphiti_client.py). The two key methods to mirror:

- `_build_llm_client()` — for `vllm`/`ollama` providers, returns
  ```python
  OpenAIGenericClient(
      config=LLMConfig(
          base_url=config.llm_base_url,
          model=config.llm_model,
          api_key="local-key",  # placeholder; local inference ignores it
      ),
      max_tokens=config.llm_max_tokens,
  )
  ```
- `_build_embedder()` — for `vllm`/`ollama` providers, returns
  ```python
  OpenAIEmbedder(
      config=OpenAIEmbedderConfig(
          base_url=config.embedding_base_url,
          embedding_model=config.embedding_model,
          api_key="local-key",
          embedding_dim=config.embedding_dimensions,  # only when explicit
      ),
  )
  ```

Both `OpenAIGenericClient` and `OpenAIEmbedder` ship with the base `graphiti-core` install (already installed in the study-tutor venv after the close-out repair sweep — no new pip extras needed for local-only operation).

`cross_encoder` is left as graphiti-core's default. `add_episode` does not invoke it (it only matters for search reranking); searches in study-tutor go through `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` which bypass reranking too. If reranking is ever needed downstream, raise a follow-up task — do **not** wire OpenAI's default reranker.

### Read config from `.guardkit/graphiti.yaml`

study-tutor already has [`/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/graphiti.yaml`](../../.guardkit/graphiti.yaml) with the GuardKit-canonical schema (same shape across guardkit, study-tutor, specialist-agent, jarvis, forge, etc.). Current values:

```yaml
project_id: study_tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3
chunk_extraction_concurrency: 4
# Active: MacBook Pro M2 Max (Ollama, Q4_K_M) — GB10 busy with dataset factory
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1
embedding_model: nomic-embed
group_ids: [product_knowledge, command_workflows, architecture_decisions]
```

The current `llm_provider: ollama` (MacBook fallback) is fine for an immediate seed run. Once GB10 is free, the commented-out `llm_provider: vllm` block at the top should be re-enabled (single-line config swap; no code change). **Do not** uncomment the Gemini fallback that exists in `guardkit/.guardkit/graphiti.yaml` — that's GuardKit's choice for its own knowledge graph, not ours, and conflicts with DECISION-DF-001 for study-tutor's runtime.

The Phase-1 `GraphitiConnectionConfig` Pydantic model in [`graphiti_client.py:62-90`](../../src/study_tutor/knowledge/graphiti_client.py#L62-L90) has a different schema (uses `falkor_host`, `embedder_url`, no `llm_provider` switch). Two ways to bridge:

1. **Loader path** — add a `GraphitiConfig.from_yaml(".guardkit/graphiti.yaml")` classmethod that reads the canonical YAML and projects into the runtime model. Keeps the runtime model isolated; YAML is the source of truth.
2. **Schema-replace path** — replace `GraphitiConnectionConfig` with the GuardKit-canonical 13-field config dataclass directly. Cleaner long-term but bigger blast radius (migrates the field names referenced throughout `get_client`, `seed_student_model.py`, tests).

Recommended: **Loader path** for this repair task (smallest blast radius, unblocks Lilymay seed today). Schema unification deferred to TASK-PH2-GR-002 (shared Graphiti core lib).

## Acceptance criteria

1. **AC-001 — Local LLM client wired via `OpenAIGenericClient`.** `get_client()` constructs an `OpenAIGenericClient` for `llm_provider in ("vllm", "ollama")` using the canonical pattern from `guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client`. `api_key="local-key"` (placeholder). `OPENAI_API_KEY` is **never** read by this code path. Per DECISION-DF-001, `llm_provider == "openai"` and `llm_provider == "gemini"` are not supported in the study-tutor runtime — raise `ValueError("cloud LLM providers disabled per DECISION-DF-001")` with a structured log line at config-load time if either is configured.
2. **AC-002 — Local embedder wired via `OpenAIEmbedder`.** `get_client()` constructs an `OpenAIEmbedder` for `embedding_provider in ("vllm", "ollama")` using the canonical pattern from `guardkit/guardkit/knowledge/graphiti_client.py:_build_embedder`. Same `api_key="local-key"`. Same DECISION-DF-001 enforcement on `embedding_provider == "openai"`.
3. **AC-003 — Cross-encoder left as graphiti-core default.** Documented inline that `add_episode` does not invoke the reranker; if a future search path needs reranking, a follow-up task wires a local cross-encoder. **Do not** ship the cross-encoder defaulted to OpenAI silently — add an init-time guard that logs `WARN: cross_encoder defaulted to graphiti-core internal; reranker calls would hit OpenAI` and treat any cross-encoder use at runtime as a critical error.
4. **AC-004 — Config loaded from `.guardkit/graphiti.yaml`.** New helper `load_graphiti_config_from_yaml(path: Path = Path(".guardkit/graphiti.yaml")) -> GraphitiConnectionConfig` projects the YAML into the runtime model. Fields used: `falkordb_host`, `falkordb_port`, `timeout`, `llm_provider`, `llm_base_url`, `llm_model`, `llm_max_tokens`, `embedding_provider`, `embedding_base_url`, `embedding_model`, `embedding_dimensions` (when present), `chunk_extraction_concurrency`. Env-var overrides honoured for the standard set (`FALKORDB_HOST`, `FALKORDB_PORT`, `GRAPHITI_ENABLED`, etc.) per the YAML's documented contract. The seed script and `tutor_session_*` MCP handlers both load via this helper rather than hand-constructing `GraphitiConnectionConfig`.
5. **AC-005 — Live-graphiti smoke test.** New `tests/smoke/test_graphiti_live_smoke.py` (or equivalent) boots a real `Graphiti` instance with the wired LLM + embedder against either (a) a stubbed driver, or (b) a live FalkorDB if `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1` is set. Round-trips one `add_episode(group_id="student-test", ...)` → `EntityNode.get_by_group_ids(...)` → asserts the episode is reachable. The test fails loudly if either client construction skips the local-endpoint config (defaults regress to OpenAI). The CC-13 regex audit (single `add_episode(` call site in `src/`) continues to pass.
6. **AC-006 — `python scripts/seed_student_model.py` lands Lilymay's baseline against live Synology FalkorDB.** All 25 entity writes succeed. `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity with the expected attributes. `get_student_state(client, "lilymay")` returns a non-empty `StudentState` (year_group=11, target_grade="8", non-empty subjects, non-empty topic_confidences). Re-running is idempotent (`event=seeding_skipped`).
7. **AC-007 — End-to-end demo session via MCP runs at least once.** `tutor_start_session` → 5–7× `tutor_turn` → `tutor_session_end` from Claude Desktop, with at least one Coach revision observed and a `session_completed` episode written to Graphiti and visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. This unblocks Phase 1 G3/G4/G5/G6/G13. Capture turn p50/p95 latency in `phase-1-validation.md`.
8. **AC-008 — `phase-1-validation.md` updated.** The five falsified items (G2, G3, G4, G5, G6, G13) flip from "Falsified" to "Held" with the live evidence inline. Phase 1 is then structurally complete on its own terms.

## Out of scope

- **Coach calibration pass.** Separate Phase 2 nice-to-have. The repair only needs the runtime to work; it doesn't need the Coach to be optimally tuned.
- **Multi-student support.** Single-student (Lilymay) is the Phase 1+2 invariant.
- **Index migration.** If FalkorDB has stale indices from earlier seed attempts, the `Connection closed by server` warnings during `build_indices_and_constraints` are background-task noise. Investigate only if they escalate into actual write failures after the LLM/embedder fixes land.
- **Adding gamification fields to `tutor_session_end`.** That's FEAT-PH2-001 item 4 and stays in FEAT-PH2-001's own subtask list.
- **Extracting the shared Graphiti core library.** That's `TASK-PH2-GR-002` (separate task — see `tasks/backlog/TASK-PH2-GR-002-extract-shared-graphiti-core-lib.md`). This repair task ships the in-repo wiring; the extraction task is the longer-term debt-reduction follow-up.
- **Cloud LLM/embedder fallbacks.** Not allowed per DECISION-DF-001.

## Already-fixed-in-flight (committed 2026-05-02 — `a210472`, `78d3498`, `732672c`)

These three patches landed during the close-out gate run on 2026-05-02. They're prerequisites for this task — both because they're on the same call path and because they're standalone API-correctness wins regardless of the LLM-wiring outcome.

- **Read API**: `queries.py:_read_student_partition` seam now calls `EntityNode.get_by_group_ids` / `EntityEdge.get_by_group_ids` on the driver, with a duck-typed shortcut for legacy `search_nodes`/`search_memory_facts` test mocks. `GroupsNodesNotFoundError` / `GroupsEdgesNotFoundError` swallowed (bootstrap case).
- **Write API**: `async_write.py:_add_episode_kwargs` builds graphiti-core 0.29's real signature: `source=EpisodeType.json`, `source_description=f"flush:{flush_id}:{name}"`, `reference_time=now()`, `group_id=group_ids[0]` (singular). Flush-id audit string still rides into structured logs unchanged.
- **Group-id format**: `student:` → `student-`, `subject:` → `subject-`, `fleet:appmilla` → `fleet-appmilla` (graphiti-core 0.29's `GroupIdValidationError` rejects characters outside `[A-Za-z0-9_-]`). Constants in `student_model.py` updated; module docstring updated; cross-repo divergence note preserved; tests updated.

Tests at 695/696 (the one failure is a pre-existing dev-machine `mypy`-on-system-Python env issue from FEAT-PH1-002, not introduced here).

**Note on the cross-repo group-id namespace.** The `.guardkit/graphiti.yaml` uses `group_ids: [product_knowledge, command_workflows, architecture_decisions]` — those are the **GuardKit tooling's** group IDs (for its own knowledge graph about the project). The study-tutor **runtime** uses different group ids (`student-lilymay`, `subject-aqa-8702-eng-lit`, `fleet-appmilla`) for its own knowledge graph about the learner. Both sets of writes hit the same FalkorDB; partition isolation is via group_id. This is by design and not a conflict — the AC-004 loader only consumes the connection + LLM/embedder fields from the YAML, not the `group_ids` list (which is GuardKit's surface, not the tutor's).

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| MacBook ollama (current YAML active) is offline at seed time | Low | Low | Toggle YAML to `llm_provider: vllm` pointing at GB10:9000; the swap is a single-line edit. The `qwen-graphiti` alias is always-loaded on llama-swap (zero swap latency). |
| GB10 llama-swap rate-limits at 25 concurrent writes | Medium | Medium | `chunk_extraction_concurrency: 4` already in YAML caps fan-out; per [`guardkit:TASK-OPS-9F2A`](../../../guardkit/docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md) this eliminated 429s in production. The seeder already uses `helper.drain()` to serialise; Phase-1 latency-spike measured 78s/write (LLM-bound), so 25 sequential writes ≈ 30 min. Acceptable for a one-off seed. |
| GB10 down for an extended period | Low | High (blocks repair) | YAML fallback to MacBook ollama (currently active). If both unreachable, repair task itself slips by the GB10 outage; Phase 2 day-by-day already accounts for this in its slip-to-Sunday contingency. |
| `OpenAIGenericClient` API surface drifts in graphiti-core minor version bumps | Low | Medium | Pin graphiti-core in `pyproject.toml` to `>=0.29,<0.30`. Smoke test (AC-005) catches regression on next bump. |
| Stale FalkorDB indices from earlier broken seeds | Medium | Low | If `Connection closed by server` returns post-fix, drop the `study_tutor` database via `redis-cli -h whitestocks -p 6379 GRAPH.DELETE study_tutor` and re-seed. |

## Implementation hint (non-binding — re-derive during `/feature-plan`)

Likely subtask shape (3–4 waves, ~5 subtasks):

- **Wave 1 — `GraphitiConnectionConfig.from_yaml` loader + DECISION-DF-001 guard.** Adds the loader; rejects cloud providers at config-load. ~30 min.
- **Wave 2 — `_build_llm_client` + `_build_embedder` mirrors of guardkit's pattern.** Inserted into `get_client()` before `Graphiti(...)` construction. Cross-encoder guard (AC-003). ~60 min.
- **Wave 3 — Live smoke test + CC-13 regex audit verification.** ~45 min.
- **Wave 4 — Re-run seed, capture verification evidence, update `phase-1-validation.md`.** ~30 min plus the seed's ~30 min LLM-bound runtime.
- **Wave 5 — End-to-end MCP demo session, capture turn p50/p95.** ~30–45 min.

Total: ~half a day (4 hours) plus the seed's LLM-bound runtime.

## Cross-references

- `docs/research/ideas/phase-1-validation.md` — the gate that falsified G2/G3/G4/G5/G6/G13 and triggered this task.
- `docs/research/ideas/phase-2-build-plan.md §"Day 1"` — Saturday 2 May morning step 3 (where this task slots in).
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical client; mirror its `_build_llm_client` + `_build_embedder` patterns.
- `guardkit/docs/research/dgx-spark/README.md` — the all-llama.cpp + llama-swap deployment overview; DECISION-DF-001 source.
- `guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md` — production deployment validation (65 GB VRAM, 41.32 tok/s workhorse, all four models coexisting).
- `guardkit/docs/research/dgx-spark/VALIDATION-OPS-7CB1-9F2A-results.md` — `chunk_extraction_concurrency: 4` provenance (eliminates 429 throttling).
- `guardkit/docs/research/dgx-spark/llama-swap-config.yaml` — model-alias registry (`qwen-graphiti`, `nomic-embed`).
- `guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md` — the cross-repo migration task that listed study-tutor as priority-High (still pending; this task supersedes it for study-tutor).
- `specialist-agent/src/specialist_agent/tools/graphiti_client.py` — companion client (search-side use case; ~460 lines; same `OpenAIGenericClient`/`OpenAIEmbedder` pattern).
- `study-tutor/.guardkit/graphiti.yaml` — the source-of-truth config this task wires `get_client` to load from.
- `docs/research/ideas/graphiti-latency-spike-results.md` — `add_episode` median 78s; informs the seed-runtime estimate.
- `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` — the mocks that let the integration drift through Phase 1; AC-005's smoke test is the regression-prevention complement.
- `TASK-PH2-GR-002` (sibling task) — long-term: extract guardkit's `graphiti_client.py` + `falkordb_workaround.py` + embedder preflight into a shared `appmilla-graphiti-core` package consumed by guardkit, study-tutor, specialist-agent, and the rest of the fleet. This repair task is intentionally scoped narrower so it can ship today; the extraction task captures the duplication debt for prioritisation later.
