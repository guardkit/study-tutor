# ADR-ARCH-008 — MCP-only for agent access; single-user auth posture

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-014, LES1 §1 (transport), CC-01, CC-02, CC-07

## Context

Study Tutor needs to expose functionality to:

- AI agents (Claude Desktop today; future Ship's Computer fleet via
  Jarvis).
- Humans via Open WebUI (Lilymay).
- Developers via CLI (README walkthrough, hackathon judges).

`specialist-agent` ships dual transports (MCP + NATS) because its
orchestration role requires fleet messaging. Study Tutor has no
equivalent need — it serves a single student, exposes a single role
(tutor), and has no fleet-broadcast semantics.

Per LES1 row 3/4/5, NATS-specific rows are marked "—" for study-tutor.
LES1 row 22 explicitly notes: *"Single-transport agents still
stream-split test stdout (easiest place to drift)"* — so MCP
discipline remains load-bearing even in a single-transport world.

## Decision

Phase 0 ships a **single transport — MCP stdio**. Four tools
classified per CC-07 / SR-07:

| Tool | Class | Bound |
|---|---|---|
| `tutor_start_session` | long-running (returns `session_id` in ≤1s; poll via `tutor_session_status`) | n/a (fire-and-forget) |
| `tutor_turn` | sync | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |

HTTP MCP transport is deferred to Phase 1+ (only if a real use case
emerges — e.g. a containerised Bedrock wrapper).

Authentication posture: **single-user process-level trust**.

- MCP stdio = child-process trust boundary.
- Open WebUI = LAN / Tailscale trust.
- CLI = filesystem-permission trust.
- No JWT, OAuth2, API keys at the tool level, multi-tenant user
  management, or RBAC.

Outbound provider API keys live in `.env` (gitignored, `.env.example`
for reference per CC-06 / SR-06).

## Alternatives considered

- **MCP + NATS (following specialist-agent's pattern).** Rejected.
  Study Tutor has no fleet-broadcast need. NATS adds operational
  complexity (stream/KV provisioning per LES1 §7) without value.
- **HTTP API as primary surface.** Rejected for Phase 0. Adds auth
  layer complexity; no consumer requires it.
- **Add GraphQL or gRPC.** Rejected. No requirements.
- **Multi-tenant auth.** Rejected. Single-student system;
  multi-student would be a Phase 3+ post-hackathon rethink.

## Consequences

**Positive:**
- LES1 row 22 (stream-split test for single-transport agents) is
  the gating discipline; easier to enforce than multi-transport.
- No NATS operational burden (stream provisioning, subject design,
  password rotation).
- 4-tool surface is minimal and testable.

**Negative:**
- Future fleet integration (Jarvis) will require adding a NATS
  transport. Design-compatible (the tutor role and AgentManifest
  pattern are fleet-ready) but will be a Phase 3+ migration.
- Open WebUI is not MCP-aware — humans see only Layer 1 (fine-tuned
  behaviour) via Open WebUI. The architectural reveal (three-layer,
  Coach, Graphiti) is accessible only via the MCP surface. Accepted;
  demo script uses both surfaces.

## References

- LES1 §1 (transport) and row 22 (single-transport discipline) in
  `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- Phase 0 scope SR-07 classification table.
- DEC-01 (demo surface strategy).
