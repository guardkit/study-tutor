# ADR-ARCH-008 — MCP-only for agent access; single-user auth posture

## Status

Partially superseded by **ADR-ARCH-017** (2026-04-27).

The SR-07 classification table at lines 35–46 below — specifically the
`tutor_start_session` row and the "stable across phases for forward compatibility"
rationale block — is **superseded**. ADR-ARCH-017 reclassifies `tutor_start_session`
as sync in Phase 0, with a measurement-conditional Phase 1 reversion rule.

The remainder of this ADR — the single-transport choice (MCP stdio only), the
HTTP MCP deferral, the single-user auth posture, the Phase 0 session-scope
limitation (in-memory dict per child process) — **remains accepted and in force**.

**Date:** 2026-04-18 (original); 2026-04-27 (partial supersession)
**Phase:** Phase 0
**Related:** ADR-ARCH-014, ADR-ARCH-017, LES1 §1 (transport), CC-01, CC-02, CC-07

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
| `tutor_start_session` | ~~long-running~~ → **sync** (see ADR-ARCH-017) | < 1s; warm-up fire-and-forget |
| `tutor_turn` | sync | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |

> ⚠️ **Superseded by ADR-ARCH-017 (2026-04-27).** The original rationale below is preserved
> for historical record only; it does not represent the current decision. The classification
> table above is updated to reflect the current decision. See ADR-ARCH-017 for the new
> rationale and the Phase 1 measurement-conditional reversion rule.
>
> *(Original 2026-04-18 rationale, preserved verbatim:)*
> `tutor_start_session` is architected as long-running for Phase-1 forward
> compatibility (where it will read the student model from Graphiti). In Phase 0
> the implementation is a UUID mint + in-memory dict insert that returns in ≤1s.
> The classification is stable across phases so `/feature-spec` does not need to
> re-classify the MCP contract when Graphiti lands.

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

**Phase 0 session scope.** Session state lives in an in-memory dict inside the
single MCP stdio child process. Claude Desktop spawns a fresh child per
conversation, so:

- A new Claude Desktop conversation = a fresh process = an empty session dict.
- `tutor_session_status(session_id=...)` against a session created in a prior
  conversation will fail.
- **Demo-script constraint (16 May):** do not close and re-open the stdio
  transport mid-session.

This limitation is generalised by ASSUM-003 and is fine for Phase 0. Phase 1
Graphiti-backed sessions remove it.

## References

- LES1 §1 (transport) and row 22 (single-transport discipline) in
  `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- Phase 0 scope SR-07 classification table.
- DEC-01 (demo surface strategy).
