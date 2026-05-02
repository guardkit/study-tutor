---
id: TASK-PH2-GR-002
title: Extract shared Graphiti core library across study-tutor, guardkit, specialist-agent
task_type: refactor
phase: post-hackathon-or-phase-3
implementation_mode: design-first
complexity: 8
estimated_minutes: 1200
status: backlog
priority: medium
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
dependencies:
- TASK-PH2-GR-001
related:
- guardkit:guardkit/knowledge/graphiti_client.py
- specialist-agent:src/specialist_agent/tools/graphiti_client.py
- guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md
tags:
- graphiti
- shared-library
- cross-repo
- debt-reduction
- discussion-starter
- post-hackathon
---

# Extract shared Graphiti core library

## Status: discussion-starter

This task is **scoped from study-tutor but should be promoted to a guardkit-level task** before execution. It's recorded here so the duplication debt is visible from the study-tutor backlog (since study-tutor will be the third consumer once `TASK-PH2-GR-001` lands), but the actual extraction work should live alongside the canonical implementation in guardkit.

**Defer to post-hackathon (after 18 May 2026 submission)** unless one of the trigger conditions below fires.

## Why this exists

There are now **three independent Graphiti client implementations** across the appmilla fleet, all converging on the same `OpenAIGenericClient` + `OpenAIEmbedder` pattern against llama-swap on GB10:

| Repo | File | Lines | Purpose |
|---|---|---|---|
| `guardkit` | `guardkit/knowledge/graphiti_client.py` | ~2496 | Canonical: full LLM/embedder/dimension-preflight/falkordb-workaround/group-prefixing/seeding/init |
| `specialist-agent` | `src/specialist_agent/tools/graphiti_client.py` | ~460 | Search-side: lazy init, graceful degradation, circuit breaker, safe query methods |
| `study-tutor` | `src/study_tutor/knowledge/graphiti_client.py` | (small) | Phase-1: lifecycle wrapper + healthcheck only; no LLM/embedder wiring (about to be repaired by `TASK-PH2-GR-001`) |

Plus there's a fleet-wide config schema (`.guardkit/graphiti.yaml`) shared across **at least 13 repos** per [`guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md`](../../../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md) — the schema is fully harmonised but each repo loads it differently (or not at all). The endpoint migration that document calls out (vLLM ports 8000/8001 → llama-swap port 9000) was applied to guardkit during v3 deployment but **still pending across the other 13 repos** as of 2026-04-29 — suggesting a shared library could have made that migration a single PR rather than fourteen.

## Proposed scope

A new package — working name `appmilla-graphiti-core` — extracted from the canonical guardkit implementation, with a dependency-inverted public API:

```
appmilla_graphiti_core/
├── __init__.py
├── config/
│   ├── schema.py            # GraphitiConfig dataclass (the .guardkit/graphiti.yaml shape)
│   └── loader.py            # load_from_yaml + env-var overrides
├── client/
│   ├── client.py            # GraphitiClient lifecycle wrapper (initialize / close / healthcheck)
│   ├── llm_factory.py       # _build_llm_client (vllm / ollama / gemini-on-explicit-opt-in)
│   └── embedder_factory.py  # _build_embedder (vllm / ollama)
├── partition/
│   ├── reader.py            # read_partition(driver, group_ids, limit) → (nodes, edges)
│   ├── writer.py            # GraphitiWriteHelper (fire-and-forget add_episode wrapper)
│   └── group_id.py          # GroupIdValidator + namespace prefix constants
├── falkordb_workaround.py   # PR #1170 monkey-patch (single-group_id search bug)
├── preflight.py             # embedding dimension pre-flight check
└── safety/
    ├── decision_df_001.py   # DECISION-DF-001 guard: raise on cloud providers when local-only required
    └── circuit_breaker.py   # specialist-agent's safe-query pattern
```

Three target consumers:

- **guardkit** — replaces `guardkit/knowledge/graphiti_client.py` (the canonical source) with `from appmilla_graphiti_core import GraphitiClient`. The bulk of the existing module's logic lives in the shared lib; the thin remainder is guardkit-specific seeding helpers.
- **study-tutor** — replaces `src/study_tutor/knowledge/graphiti_client.py` and `src/study_tutor/knowledge/async_write.py` (or at least the LLM/embedder construction half) with the shared lib. Keeps the study-tutor-specific `EpisodeBase` / `SessionCompletedEpisode` / `MisconceptionObservedEpisode` types in-repo (they're domain entities, not infra).
- **specialist-agent** — replaces `src/specialist_agent/tools/graphiti_client.py` with the shared lib's `client.py` + `safety/circuit_breaker.py`. The search-side `search_nodes_safe` / `search_facts_safe` methods become library methods.

Plus a long tail (10+ repos per the endpoint-migration task) that don't yet have a Python Graphiti client but consume `.guardkit/graphiti.yaml` indirectly via guardkit's tooling — those become library consumers if/when they ever need direct programmatic Graphiti access.

## Why post-hackathon, not now

- **Submission deadline is Monday 18 May.** The hackathon submission is the load-bearing milestone. Refactoring three repos onto a new shared library is exactly the kind of "while we're here" work that consumes the wrong calendar week.
- **Premature consolidation risk.** The three implementations converge on the same pattern but each has local context (study-tutor's CC-13 single-call-site invariant; specialist-agent's circuit breaker; guardkit's seeding helpers). Forcing them into a shared shape before all three are settled would lock in the wrong abstraction. `TASK-PH2-GR-001` settles study-tutor; that's the third converging point — *then* the shared shape is visible.
- **Test surface multiplies.** Each repo has its own test suite for its Graphiti integration (study-tutor: `tests/unit/knowledge/test_*.py`; guardkit: `tests/knowledge/test_graphiti_*.py`; specialist-agent: `tests/.../test_graphiti_*.py`). A shared lib means a shared test harness — designing that well is its own ~half-day task on top of the extraction.

## Trigger conditions to reopen earlier

Promote to in-progress (and likely to a guardkit-level task) if any of:

- **A second cross-repo Graphiti API drift surfaces** like the one this Phase 1 close-out exercise just exposed. If wiring up another repo to the same llama-swap endpoint requires re-deriving the same `_build_llm_client` / `_build_embedder` pattern from scratch, the case for shared code stops being theoretical.
- **graphiti-core 0.30 ships with a breaking API change.** Pinning each repo's compat code separately gets expensive; centralising means one PR fixes the fleet.
- **A new repo (jarvis, forge, or one of the named-but-not-yet-built fleet members) needs a runtime Graphiti integration before submission.** Building it from scratch when guardkit and study-tutor and specialist-agent already have one each would be a fourth instance of the same code.
- **The `.guardkit/graphiti.yaml` endpoint-migration task ([`guardkit:docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md`](../../../guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md)) gets reopened to apply the next round of fleet-wide config changes** (e.g. when llama-swap moves off `:9000` or when a new model alias replaces `qwen-graphiti`). The shared-lib path makes that a one-PR change instead of a 13-PR sweep.

## Acceptance criteria (sketch — reshape during `/feature-spec`)

1. **AC-001** — Package published as `appmilla-graphiti-core` (location TBD: pip-installable from a private repo, monorepo subpackage, or a single-source git submodule — the choice depends on the broader appmilla packaging story).
2. **AC-002** — guardkit, study-tutor, and specialist-agent all import the shared client; their individual `graphiti_client.py` modules become thin shims (or are deleted entirely if no repo-specific logic remains).
3. **AC-003** — All three consumers' existing test suites stay green. Shared-lib tests cover: config loader, LLM/embedder factories, DECISION-DF-001 guard, partition read/write, group-id validation, falkordb_workaround, embedding dimension preflight, circuit breaker.
4. **AC-004** — A single-document migration runbook (in guardkit's `docs/research/`) explains how to onboard a new fleet repo to the shared lib in <30 min.
5. **AC-005** — Cross-repo divergence note captured: which group-id namespaces each consumer uses (study-tutor: `student-`/`subject-`/`fleet-appmilla`; guardkit: `product_knowledge`/`command_workflows`/`architecture_decisions`; specialist-agent: TBD). The lib doesn't enforce a single namespace — it provides validators and the consumer chooses the prefixes.

## Out of scope

- **Changing graphiti-core's own surface.** This task wraps graphiti-core; it doesn't fork it.
- **Changing the FalkorDB topology** (Synology NAS via Tailscale). That's a fleet-infrastructure decision, separate task if revisited.
- **Migrating the cross-repo `.guardkit/graphiti.yaml` files to a new shared schema.** They're already on the same schema. The lib just standardises the *loader* that consumes them.

## Cross-references

- `tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md` — the immediate-unblocker task this is the long-term follow-up to.
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical implementation; the source of truth for the extraction.
- `specialist-agent/src/specialist_agent/tools/graphiti_client.py` — companion search-side implementation; contributes the `_safe` pattern + circuit-breaker.
- `guardkit/docs/research/dgx-spark/TASK-graphiti-yaml-endpoint-migration.md` — the fleet-wide config-migration evidence: 13 repos with the same schema, same migration done piecemeal. The strongest argument for centralisation.
- `guardkit/docs/research/dgx-spark/README.md` — the all-llama.cpp deployment story this lib targets.
