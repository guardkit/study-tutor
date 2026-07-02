# API Contract — Cross-Device Session Persistence

**Bounded context:** Tutoring + App Access (HTTP/WS adapter)
**Phase:** FEAT-SMP-003 (this cluster) → mobile+voice slice
**Status:** **Proposed** — feeds the [FEAT-SMP-003 `/feature-spec`](../../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) and the mobile [`/goal`](../../handoffs/study-tutor-mobile-voice-conversation-starter.md); ratify via `/design-refine` before build (it changes accepted contracts — see §10).
**Generated:** 2026-07-02.
**Related:** [ADR-ARCH-023](../../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) (Postgres StudentStore — sessions persist here), ADR-FLEET-003 (MCP for agent-hosts, HTTP/WS for app clients), [ADR-ARCH-008](../../architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md) (**partially superseded** for app clients — §10), [API-tutoring.md](API-tutoring.md) (the MCP verbs this mirrors), [mobile+voice handoff](../../handoffs/study-tutor-mobile-voice-conversation-starter.md) (D6–D9), [events-schema.yaml](../events-schema.yaml).

---

## 1. Purpose — what changes, and why

Today ([API-tutoring.md](API-tutoring.md)) a session is **in-memory, not student-keyed, "end-once, append-only, no resume"** (§8), reachable only over **MCP stdio, no auth** (§2). The real-user request — *"pick up study sessions from my phone and/or the Reachy robot"* — requires three changes, and only three:

1. **Durable, student-keyed sessions** — persisted in the Postgres StudentStore ([ADR-ARCH-023](../../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)), keyed to a `student_id`, survive process restarts and device switches.
2. **Resumable** — a session stays re-attachable while `active`; a second device loads the transcript and continues the same thread. (Relaxes "end-once, append-only".)
3. **A second transport** — an **HTTP/WS** surface for app clients (phone/web) alongside the existing **MCP** surface for agent-hosts, per **ADR-FLEET-003**. Both surfaces operate on the *same* student-keyed session store.

Everything else (the tutor loop, the Coach, the events, the AO rubric) is unchanged. This contract is the seam.

## 2. Consumers & surfaces

| Consumer | Surface | Transport | Auth |
|---|---|---|---|
| Flutter phone / web client | App Access adapter | **HTTP + WebSocket** | Keycloak (D9) |
| Reachy robot client | App Access adapter | HTTP/WS (or MCP) | Keycloak / device |
| AI agent-hosts (Claude Desktop, Jarvis) | MCP | stdio | local/Tailscale |

**Both surfaces are thin adapters over one `SessionService`**; the persistence, identity, and lifecycle rules below are transport-agnostic. The verbs mirror the MCP tools 1:1 so there is a single mental model (ADR-FLEET-003).

## 3. Identity & auth

- **`student_id` is the partition key** for every session, turn, and StudentStore row. A session belongs to exactly one student; a student may have many sessions.
- **Derivation:** on the HTTP/WS surface, `student_id` is derived from the **Keycloak subject** (`sub` claim) via a `sub → student_id` mapping (D9). The client never asserts `student_id` directly — it comes from the validated token.
- **Interim single-user mode:** while Keycloak is not yet fronting the API, the adapter resolves a single configured `student_id` (Lilymay) — the current no-auth posture ([API-tutoring.md §2](API-tutoring.md), ADR-ARCH-014) stays valid as a degenerate case. The contract does not change when auth turns on; only the derivation source does.
- **Cross-device pickup rule:** both the phone and the robot authenticate as the **same** Keycloak subject → same `student_id` → they see and resume the same sessions. This is the whole mechanism (handoff D8).

## 4. Session lifecycle & states

```
                 start_session
                      │
                      ▼
   (resume ◀──────  active  ──────▶ end_session ──▶ ended
     any device      │  ▲                              (terminal)
     while active)   └──┘ turn (per-turn durable append)
```

- **States:** `active` | `ended`. `ended` is terminal (no re-open). **`active` is resumable** from any device authenticated as the owning student.
- **Per-turn durability:** each `(user, tutor)` pair is committed to Postgres **as the turn completes**, not only at session end — this is what makes mid-session device switching lossless.
- **Concurrency (single-user reality):** last-writer-wins on turns; the contract does **not** attempt real-time multi-device co-editing. A `session_version` (monotonic turn count) lets a client detect it resumed a session another device advanced, and re-fetch. (Open question §11.)

## 5. Verbs (mirror the MCP surface + resume)

Shapes are transport-neutral; HTTP = request/response JSON, WS = the same messages as frames (plus streaming on `turn`, §7).

| Verb | Input | Output | Notes vs [API-tutoring.md](API-tutoring.md) |
|---|---|---|---|
| `start_session` | `{ subject?, topic?, resume_if_active? }` (student from auth) | `{ session_id, student_id, resumed: bool, turns? }` | Gains `student_id` (from auth) + `resumed`. If `resume_if_active` and an active session for `(student, subject)` exists, returns it with its `turns` instead of creating a new one. |
| `list_sessions` | `{ status?, limit? }` | `[{ session_id, subject, topic, status, started_at, last_activity, turn_count }]` | **New.** Lets a device show "resume where you left off". |
| `resume_session` | `{ session_id }` | `{ session_id, status, turns:[{role,content,ts}], student_id }` | **New.** Loads the transcript for a device that didn't start the session. 403 if not owned by the caller's `student_id`. |
| `turn` | `{ session_id, user_message, stream? }` | `{ tutor_response }` or a token stream (§7) | Same shape; now **persists the pair per-turn**. p95 < 10s budget unchanged. |
| `session_status` | `{ session_id }` | `{ session_id, student_id, status, turn_count, started_at, last_activity, resumable }` | Adds `student_id`, `last_activity`, `resumable`. |
| `end_session` | `{ session_id }` | `{ session_id, status:"ended" }` | Same. Triggers the synchronous StudentStore write (XP/streak/confidence/achievement — FEAT-SMP-001) and the `session.completed` event. |

**Ownership check:** every verb taking a `session_id` asserts the session's `student_id == caller student_id`, else `error_type: "SessionForbidden"`.

## 6. Persistence semantics (maps to the StudentStore schema — FEAT-SMP-001)

- A **`session`** row: `session_id (PK)`, `student_id (FK)`, `subject`, `topic`, `status`, `started_at`, `last_activity`, `turn_count`, plus JSONB `aos_scaffolded` / summary.
- A **`session_turn`** row per turn: `session_id (FK)`, `turn_index`, `role`, `content`, `ts` (+ optional `ao_scaffolded`). Append-only within a session.
- **Write timing:** `turn` commits the turn rows synchronously (ms-scale — [ADR-ARCH-023](../../architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) D2); `end_session` commits the learner-state deltas in one transaction. No fire-and-forget, no Graphiti.
- **Resume read:** `resume_session` / `start_session(resume_if_active)` returns the ordered `session_turn` rows so the new device renders the thread. Read-path budget < 2s (inherits the [API-tutoring.md](API-tutoring.md) status budget).

## 7. Streaming semantics (voice)

- The **voice path** (handoff D6: phone → WS → STT → `turn` → TTS → back) needs **token streaming** to stay inside the turn budget with speech on both ends.
- **WS `turn`** with `stream: true` emits `{type:"token", text}` frames then a terminal `{type:"done", turn_index}`. TTS consumes tokens as they arrive.
- **HTTP `turn`** (simple web/text) returns the whole `{ tutor_response }` — no streaming required.
- Whether STT/TTS ride the *same* conversation WS or separate endpoints is the GB10-voice-endpoint decision (handoff OQ2) — out of scope here; this contract only fixes that `turn` **has** a streaming variant on WS.

## 8. Events (Shared Kernel B) — unchanged vocabulary

`session.started {session_id, student_id, subject, topic, started_at}` · `session.turn_completed {session_id, turn_index, role, ao_scaffolded?}` · `session.completed {session_id, duration_seconds, topic, aos_touched, quality_score, ended_at}` — identical to [API-tutoring.md §5](API-tutoring.md); `session.started` already carries `student_id`. Emit remains on state transition ([DDR-003](../decisions/DDR-003-session-completed-emits-on-state-transition.md)), now decoupled from a *fast* Postgres write rather than a slow Graphiti one. Optional additive `session.resumed {session_id, student_id, device?}` — defer unless a consumer needs it.

## 9. Error envelope

Flat dict per [API-tutoring.md §4](API-tutoring.md). Closed set extended by:

| `error_type` | Trigger |
|---|---|
| `SessionNotFoundError` | `session_id` unknown |
| `SessionEnded` | verb on an `ended` session (except `session_status`) |
| `SessionForbidden` | **new** — session's `student_id` ≠ caller's |
| `Unauthenticated` | **new** (HTTP/WS) — missing/invalid Keycloak token |

## 10. Contract changes requiring `/design-refine`

This doc is **Proposed** precisely because it touches accepted contracts:

1. **Relaxes "end-once, append-only, no resume"** ([API-tutoring.md §8](API-tutoring.md)) — adds `resume_session` / `list_sessions` and re-attachment while `active`. (§8 explicitly said `tutor_pause/resume` were "not requested" — they are now.)
2. **Adds an HTTP/WS surface** — [ADR-ARCH-008](../../architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md) is MCP-only; **ADR-FLEET-003 supersedes it for app clients**. Record the partial supersession in `/design-refine`.
3. **Adds `student_id`, auth (`Unauthenticated`/`SessionForbidden`), and per-turn durability** — schema + error-set growth.

None of these change the MCP surface's existing behaviour; they *extend* it. Agent-hosts keep the four MCP tools exactly as-is.

## 11. Open questions

1. **`sub → student_id` mapping** (handoff OQ4/D9) — where it lives (Keycloak attribute vs a `student` table lookup) and how a new student is provisioned.
2. **Concurrent resume** — is last-writer-wins + `session_version` enough, or does the robot↔phone hand-off need an explicit "active device" lease? (Single-user makes this low-stakes; revisit if two devices are ever truly simultaneous.)
3. **Voice transport shape** (handoff OQ2) — single Realtime-style WS vs separate STT/TTS; decided when the GB10 voice endpoints are built.
4. **Session TTL / auto-end** — does an `active` session that's untouched for N hours auto-`end` (triggering the StudentStore write) or stay resumable indefinitely? Affects streak/XP attribution timing.

---

*Proposed 2026-07-02. Consumed by FEAT-SMP-003 (`/feature-spec`) and the mobile `/goal` opener. Ratify via `/design-refine` (§10) before build.*
