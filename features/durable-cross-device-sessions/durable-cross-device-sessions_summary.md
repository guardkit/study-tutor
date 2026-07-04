# Feature Spec Summary: Durable Cross-Device Sessions (FEAT-SMP-003)

**Stack**: python
**Generated**: 2026-07-04T11:37:04Z
**Scenarios**: 22 total (1 Scenario Outline); 4 @smoke, 1 @regression
**Assumptions**: 12 total (5 high / 4 medium / 3 low confidence)
**Review required**: Yes (ASSUM-003, ASSUM-008, ASSUM-010)

## Scope

Makes study sessions durable, student-keyed, and resumable across devices, and moves
session-end learner-state persistence off Graphiti onto Postgres. Implements the 6
`PostgresStudentStore` session methods over the merged W1 `session`/`session_turn`
schema; wires the already-built `SessionService` (ownership/status guards + the six
verbs) into both MCP adapter sites via a shared `build_session_service()` helper;
server-resolves a single-user identity (config, default `lilymay`) kept separate from
the planner slug; swaps the 4 MCP tools onto `SessionService` with the MCP + NATS
surface byte-for-byte unchanged; and ports the pure `Phase1MinimalDeltaPolicy` over W2
store reads to produce the session-end `ConfidenceUpdate[]` for the durable,
idempotent `record_session_completion`, preserving the live `session.completed` event.

**Out of scope**: the HTTP/WS transport + `turn_stream` (mobile `/goal` build); a real
XP/gamification engine; wiring the Coach verdict into misconceptions; the full Graphiti
teardown incl. deleting `session.tutor_session` (FEAT-SMP-004 — the adapter just stops
using it).

## Scenario Counts by Category

| Group | Count |
|-------|-------|
| A — Key examples | 6 |
| B — Boundary conditions | 5 |
| C — Negative / guards | 5 |
| D — Edge cases / migration semantics | 6 |
| **Total** | **22** |

(Cross-cutting tags: @lifecycle, @resume, @session-end, @guard, @security, @durability,
@cross-device, @surface, @regression, @idempotency.)

## Key design decisions (from the scope decision + spec review)

1. **Durable lifecycle + session-end onto Postgres** (the chosen scope). Sessions become
   durable/resumable over the live MCP path; session-end writes learner state to Postgres
   (ADR-ARCH-023 D2), replacing the Graphiti F3 flush + `record_topic_confidence_update`.
2. **Identity split (ASSUM-001).** A config single-user id (default `lilymay`), server-resolved
   and used as the ownership key — *separate* from the planner slug so the guard is neither
   tautological nor a break when Keycloak arrives.
3. **Confidence delta ported, not reinvented (ASSUM-008, low).** The pure `Phase1MinimalDeltaPolicy`
   runs over W2 `get_topic_confidences`; with misconceptions empty (ASSUM-007) only the +1
   engagement bonus is live. XP = 0 placeholder (ASSUM-006).
4. **Surface frozen (ASSUM-005).** The 4 MCP tools, descriptions, error envelopes, and NATS aliases
   are byte-for-byte unchanged — a hard regression gate.
5. **`session.completed` payload preserved (ASSUM-010, low).** The live emitted dict is the
   regression target; the events-schema.yaml divergence is a flagged follow-up.

## Open Assumptions (low confidence — human/Coach review required)

- **ASSUM-003** — resume-if-active via a single transaction (no partial-unique-index migration).
- **ASSUM-008** — the ported confidence-delta policy semantics (Phase-1 expedient; FEAT-PH2-001 replaces).
- **ASSUM-010** — preserve the live `session.completed` payload vs reconcile with events-schema.yaml.

## Execution risks for /feature-plan and autobuild

- **The 4-tool surface is the sharpest regression gate.** `tests/unit/mcp/test_adapter.py` +
  `tests/unit/adapters/test_command_router.py` assert tool names, the `"Marks session ended."`
  description, the `{session_id, status:"ended"}` end shape, and the `tutor_start_session→start_session`
  alias. The swap onto `SessionService` must keep these green — verify the WHOLE suite (per the W1
  self-defeating-boundary-tests retro), not just per-task.
- **Wire BOTH `main.py` sites.** `serve` AND `_build_nats_runtime`; the NATS path currently has no
  student-store wiring at all, so `build_session_service()` (and, for it to be non-empty, the
  conditional `build_student_store()`) must be added there too.
- **Serialize the waves.** Store methods + adapter swap + session-end port all touch overlapping
  modules (`postgres.py`, `adapter.py`, `main.py`); per the parallel-wave worktree-pollution retro,
  encode one-task-per-wave in the feature YAML `orchestration.parallel_groups`.
- **Export an ephemeral `STUDY_TUTOR_PG_DSN`** (throwaway `postgres:16`, never the NAS) before
  autobuild so the Coach's DB-backed session tests run for real.

## Integration with /feature-plan

    /feature-plan "Durable Cross-Device Sessions" \
      --context features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
