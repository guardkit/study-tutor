# Implementation Guide — FEAT-SMP-003: Durable Cross-Device Sessions

**Feature:** `FEAT-SMP-003` · **Spec:** [durable-cross-device-sessions.feature](../../../features/durable-cross-device-sessions/durable-cross-device-sessions.feature) (22 scenarios) · **Contract:** [API-session-cross-device.md](../../../docs/design/contracts/API-session-cross-device.md) (Accepted, G-CON) · **Builds on:** W1 (write path), W2 (reads)

## Scope

Makes study sessions durable, student-keyed, and resumable across devices, and moves session-end learner-state
persistence off Graphiti onto Postgres. The 6 `PostgresStudentStore` session methods + wiring the (already-built)
`SessionService` into both MCP adapter sites + a config single-user identity + swapping the 4 MCP tools onto
`SessionService` (surface byte-for-byte unchanged) + the session-end completion port (Phase1MinimalDeltaPolicy
over W2 reads → durable `record_session_completion`, preserving `session.completed`).

**Out of scope:** the HTTP/WS transport + `turn_stream` (mobile `/goal`); a real XP/gamification engine; wiring
the Coach verdict into misconceptions; deleting `session.tutor_session` + the graph write plumbing (FEAT-SMP-004).

## §1: Data Flow — Read/Write Paths (before → after)

```mermaid
flowchart LR
    subgraph Tools["4 MCP tools (surface FROZEN)"]
        T1["tutor_start_session"]
        T2["tutor_turn"]
        T3["tutor_session_status"]
        T4["tutor_session_end"]
    end
    subgraph Svc["SessionService (built; wired by SMP3-04)"]
        SS["start/turn/status/end + guards"]
    end
    subgraph Store["PostgresStudentStore session methods (SMP3-01..03)"]
        M1["create_session / get_session"]
        M2["list_sessions / get_turns"]
        M3["append_turn / end_session"]
    end
    subgraph PG["Postgres"]
        P1[("session")]
        P2[("session_turn")]
        P3[("topic_confidence")]
    end
    subgraph End["Session-end onto Postgres (SMP3-05/06)"]
        C1["build_session_completion<br/>(Phase1MinimalDeltaPolicy over W2 reads)"]
        C2["record_session_completion (W1, idempotent)"]
        EV["session.completed event (payload preserved)"]
    end

    T1 --> SS
    T2 --> SS
    T3 --> SS
    T4 --> SS
    SS --> M1
    SS --> M2
    SS --> M3
    M1 --> P1
    M2 --> P1
    M2 --> P2
    M3 --> P1
    M3 --> P2
    T4 -->|turn_count>0| C1
    C1 -->|reads| P3
    C1 --> C2
    C2 --> P3
    T4 --> EV

    W1["OLD: in-memory SessionStore"]:::old
    W2["OLD: perform_session_end + Graphiti F3/F2"]:::old
    T2 -.->|"REMOVED (SMP3-06)"| W1
    T4 -.->|"REMOVED (SMP3-06)"| W2
    classDef old fill:#fdd,stroke:#c00,stroke-dasharray:4
    style C1 fill:#cfc,stroke:#090
    style SS fill:#ffd,stroke:#c90
```

**Disconnection note (resolved):** every tool now flows through `SessionService` → durable Postgres; the two
red dotted paths (the in-memory `SessionStore` and the Graphiti session-end write) are **removed by SMP3-06** —
the module files stay until FEAT-SMP-004, but nothing calls them. No write path is left without a read.

## §2: Integration Contract — session-end sequence (the cutover)

```mermaid
sequenceDiagram
    participant A as MCPAdapter.tutor_session_end
    participant S as SessionService.end_session
    participant B as build_session_completion (SMP3-05)
    participant St as PostgresStudentStore
    participant E as EventBus

    A->>A: turn_count == 0 ?  (I-T6 zero-turn → completion=None)
    alt turn_count > 0
        A->>B: build_session_completion(store, student_id, topic, turns, misc={})
        B->>St: get_topic_confidences(student_id)   [W2 read]
        B-->>A: SessionCompletion(confidence_updates, xp=0, misc=[])
    end
    A->>E: emit session.completed (preserved payload, BEFORE the write — DDR-003)
    A->>S: end_session(student_id, session_id, completion)
    S->>St: end_session(session_id)  (active→ended)
    opt completion is not None
        S->>St: record_session_completion(...)  (W1, idempotent on session_id)
    end
    S-->>A: EndSessionResult(session_id)
    A-->>A: return {"session_id", "status":"ended"}   (UNCHANGED shape)
    Note over A,E: The 4 tool names/args/descriptions + NATS aliases are byte-for-byte unchanged (ASSUM-005).
```

## §3: Task Dependency Graph (serialized — one task per wave)

```mermaid
graph TD
    T1["SMP3-01<br/>create+get_session<br/>(feature, cx5)"] --> T2["SMP3-02<br/>list+get_turns<br/>(feature, cx4)"]
    T2 --> T3["SMP3-03<br/>append_turn+end_session<br/>(feature, cx5)"]
    T3 --> T4["SMP3-04<br/>identity + service wiring<br/>(feature, cx4)"]
    T4 --> T5["SMP3-05<br/>completion producer<br/>(feature, cx5)"]
    T5 --> T6["SMP3-06<br/>MCP adapter cutover<br/>(feature, cx6)"]
    T6 --> T7["SMP3-07<br/>BDD + fake + integration + surface<br/>(testing, cx6)"]
```

_Strictly serial — store methods, adapter, and main.py all overlap; per the [parallel-wave worktree-pollution retro](../../../docs/retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md). The **completion producer (05) precedes the cutover (06)** so 06 is one atomic swap — no intermediate "end writes no learner state" a later task must un-break (the [self-defeating-tests retro](../../../docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md))._

## §4: Integration Contracts

### Contract: STUDY_TUTOR_PG_DSN
- **Producer:** W0 deploy (`.env`); read by `build_student_store()` / `build_session_service()` (SMP3-04).
- **Consumer(s):** SMP3-04 (boot wiring, both `main.py` sites), transitively the 6 store methods, SMP3-07 (ephemeral PG).
- **Format:** `postgresql+asyncpg://…` (store coerces `postgresql://`); boot guard uses `os.environ.get(...)`.
- **Validation:** SMP3-04 test asserts `build_session_service()` called iff the DSN is set at both sites.

### Contract: SessionService (session.provider → MCP adapter)
- **Producer:** `build_session_service()` (SMP3-04) → `set_session_service(SessionService())`.
- **Consumer:** `MCPAdapter` (SMP3-06) via `get_session_service()` (or an injected fake-backed service in tests).
- **Format:** the built `SessionService` resolves the wired `StudentStore`; an unwired service at boot is fail-fast (provider.py).
- **Validation:** SMP3-06 surface regression (`test_adapter.py`) with an injected `SessionService(store=FakeStudentStore())`.

### Contract: reply_fn (adapter tutor loop → SessionService.turn)
- **Producer:** the adapter wraps today's inline orchestrator/Phase-0 loop as `reply_fn: ReplyFn` (SMP3-06).
- **Consumer:** `SessionService.turn(..., reply_fn=...)` — the service owns the two durable `append_turn` calls.
- **Format:** `reply_fn(user_message) -> TutorReply(response, metadata)`; metadata re-projected into the unchanged response dict.
- **Validation:** SMP3-06/07 assert `tutor_turn` returns the unchanged Phase-0 / orchestrator shapes and persists two turns.

## Assumptions carried into tasks (3 low-confidence, still open)

| Assumption | Decision | Task |
|---|---|---|
| ASSUM-003 | resume-if-active via one transaction (no partial-unique-index migration) | SMP3-01 |
| ASSUM-008 | confidence delta = ported Phase1MinimalDeltaPolicy over store reads (engagement bonus only, misc empty) | SMP3-05 |
| ASSUM-010 | preserve the live `session.completed` payload (events-schema.yaml reconciliation deferred) | SMP3-06 |

## Test strategy

- **Store (SQL) behaviour** → ephemeral-PG integration (throwaway `postgres:16`, non-5434 port); NAS scope-guard test.
- **Service/guard behaviour** → `FakeStudentStore` (its 6 session methods already exist).
- **Surface regression (sharpest gate)** → `tests/unit/mcp/test_adapter.py` + `tests/unit/adapters/test_command_router.py`
  must stay green after the cutover — the 4 tools, descriptions, error envelopes, and NATS aliases are frozen (ASSUM-005).
- **Composition guard** → SMP3-06/07 run the WHOLE `pytest tests/`, and SMP3-07 runs `pytest features/…`
  explicitly (an undefined BDD step is a FAILURE — guardkit retro 2026-07-04, not `pending`).

## AutoBuild operational checklist (READ before `guardkit autobuild`)

1. Waves are already serialized (one task per wave) in `.guardkit/features/FEAT-SMP-003.yaml`.
2. `export STUDY_TUTOR_PG_DSN=<ephemeral PG>` (throwaway `postgres:16`, non-5434 port) before launching.
3. After it finishes, independently run `pytest tests/` AND `pytest features/durable-cross-device-sessions`
   (Coach per-task green ≠ composition green; the surface regression + BDD steps are the risk).
4. Squash-merge only the code/test paths (`src/…/store/postgres.py`, `src/…/session/*`, `src/…/mcp/adapter.py`,
   `src/…/cli/main.py`, `src/…/knowledge/*` for the moved policy, `features/…`, `tests/**`) — not `.guardkit/`/`tasks/` churn.

## Next after W3

FEAT-SMP-004 — delete the graph write plumbing + `session.tutor_session` + `queries.py` write path; retire the CC-13 machinery.
