# ADR-ARCH-007 — Graphiti split topology: FalkorDB on Synology + Gemini entity extraction + GB10 embedder

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-006 (GB10 freed for training), DEC-02, DEC-08

## Context

Graphiti has three component dependencies:

1. A graph-DB backend (FalkorDB is the recommended FalkorDB /
   Neo4j-compatible option; this project uses FalkorDB).
2. An LLM for entity extraction (Gemini 2.5 Pro here).
3. An embedding model (nomic-embed-text-v1.5 on GB10:8001).

DEC-07 mandates that GB10 is freed for training during Phase 1 —
meaning FalkorDB and the entity-extraction LLM cannot live on GB10.
DEC-02 records the topology decision taken on 16 April 2026.

The MacBook is the tutor's primary host; it reaches all three
component services over Tailscale.

## Decision

Graphiti runs as a three-host split topology:

| Component | Host | Reach from MacBook |
|---|---|---|
| **FalkorDB graph store** | Synology NAS (`whitestocks`) | Tailscale, port 6379 |
| **Entity-extraction LLM** | Google Gemini 2.5 Pro | Gemini API (public internet) |
| **Embedder** | GB10 (nomic-embed-text-v1.5 on :8001) | Tailscale |

The three Tailscale hops are documented; the Gemini hop is documented
as an explicit on-device-residency exception (see ADR-ARCH-015).

Config lives in `.guardkit/graphiti.yaml` (already present as of
2026-04-18):

```yaml
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
llm_provider: gemini
llm_model: gemini-2.5-pro
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
embedding_dimensions: 1024
```

Phase 0 includes a `guardkit graphiti status` check in the
clean-machine walkthrough; connection failure does not block Phase 0
(Graphiti write-back is Phase 1+).

## Alternatives considered

- **All-in-one on GB10.** Rejected. Conflicts with DEC-07 training
  schedule.
- **All-in-one on MacBook.** Rejected. FalkorDB sits better on a
  server-class machine (Synology NAS is always-on). Local MacBook
  Graphiti would go away when the laptop sleeps.
- **Entity-extraction via a local model (e.g. Qwen on GB10).**
  Rejected for Phase 1 MVP per DEC-08 — Gemini is paid-for, 1–3s
  latency, cheaper than standing up another local model and
  scheduling its GB10 slot.
- **Embedder on MacBook via Ollama.** Considered. Kept on GB10
  because the embedder is small enough not to block training, and
  FalkorDB + embedder colocation simplified nothing.

## Consequences

**Positive:**
- GB10 freed for sequential training workloads.
- FalkorDB on always-on Synology NAS is reliable.
- Gemini latency (1–3s) is absorbed by the async session-end
  write-back (ADR-ARCH-003) and is not on the hot path.

**Negative:**
- Three hosts = three failure modes. Mitigated by fail-soft
  degradation (ADR-ARCH-014).
- Gemini sees session summaries — explicit on-device-residency
  exception (ADR-ARCH-015). Session summaries must avoid full
  student names / school identifiers; monitored in Phase 1
  (ASSUM-013).
- Tailscale dependency becomes load-bearing. Proven in B8E4
  walkthrough; acceptable.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`
- `.guardkit/graphiti.yaml` (2026-04-18 snapshot)
- specialist-agent TASK-REV-B8E4 walkthrough evidence on Tailscale
  reliability.
