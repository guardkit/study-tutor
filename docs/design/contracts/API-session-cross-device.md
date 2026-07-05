# API Contract — Cross-Device Session Persistence

**Bounded context:** Tutoring + App Access (HTTP/WS adapter)
**Phase:** FEAT-SMP-003 (this cluster) → mobile+voice slice
**Status:** **Accepted** — ratified 2026-07-03 via `/design-refine` (G-CON gate — [migration build plan §5a](../../research/ideas/student-model-postgres-migration-scope-and-build-plan.md)). Feeds the [FEAT-SMP-003 `/feature-spec`](../../research/ideas/student-model-postgres-migration-scope-and-build-plan.md) and the mobile [`/goal`](../../handoffs/study-tutor-mobile-voice-conversation-starter.md). §10's three accepted-contract changes are recorded: [ADR-ARCH-008](../../architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md) partially superseded for app clients (ADR-FLEET-003); [API-tutoring.md §8](API-tutoring.md) "end-once/append-only" relaxed; API-tutoring §4 closed error set extended (`SessionForbidden` / `Unauthenticated`).
**Revision 1 (2026-07-05)** — voice extension, ratified via `/design-refine` (G-CON gate — [voice build plan §5a](../../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md), [voice design §8](../voice-tutor-and-reachy-design.md)): §5 gains `voice_turn`/`voice_audio`, §7 gains the voice frame vocabulary, §9 gains six voice error types, §11 OQ3 resolved. **Additive only** — the six existing verbs, their shapes, and the four original error types are unchanged (§10 change 4).
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
| `voice_turn` | `{ session_id, audio (binary upload: bytes + content_type + filename), stream? }` (student from auth) | `{ transcript, tutor_response, audio: [{seq, chunk_id, url}] }`, or streamed frames (§7) | **New (Rev 1).** Voice variant of `turn`: the server transcribes the clip (shared GB10 STT), runs the *identical* turn pipeline, and synthesizes the reply (TTS) as ordered wav chunks referenced by `audio[]`. The transcript persists as a typed user turn — per-turn durability, ownership, and lifecycle rules unchanged. Caps: 60 s (client-enforced primary, server best-effort) / 10 MB. Inbound audio is ephemeral: transcribed and discarded, never at rest ([ADR-ARCH-024](../../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) D3 + blueprint §5). |
| `voice_audio` | `{ session_id, chunk_id }` | binary `audio/wav` | **New (Rev 1).** Fetches one synthesized reply chunk by reference. Chunks are held in memory only, TTL-bounded (≤120 s) — an expired/unknown `chunk_id` is a transport-level 404 (binding §4.2), and the client skips that chunk (best-effort playback). |

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
- **Voice frame vocabulary (Rev 1)** — extends, never replaces, the frames above (`token`/`done` are byte-for-byte unchanged; non-voice streamed turns never see the new frames):
  - Client → server, voice turn over the WS: `{type:"voice_turn", content_type, size_bytes}` header frame, followed by **one binary frame** carrying the recorded clip (≤10 MB).
  - Server → client, in order: `{type:"transcript", text}` first (the STT confirmation, persisted as the typed user turn) → `{type:"token", text}` × N → `{type:"audio_ref", seq, chunk_id, url}` per synthesized sentence chunk (fetched via `voice_audio`, played in `seq` order) → terminal `{type:"done", turn_index}`.
  - Errors on the WS surface as `{type:"error", error, error_type}` frames carrying the §9 envelope.
  - Token release is gated by chunk-boundary quote verification ([ADR-ARCH-027](../../architecture/decisions/ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md)): a sentence chunk's tokens are emitted only after that chunk passes verification.
- **Resolved (Rev 1)** — the question this section previously deferred to handoff OQ2 (single Realtime-style WS vs separate STT/TTS endpoints) is closed by [ADR-ARCH-024](../../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) r1: STT/TTS are **server-side** calls to the shared GB10 audio endpoints made inside `voice_turn`; the conversation WS carries only the frames above. `/v1/realtime` is Reachy's in-process shape, not part of this contract.

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
| `RecordingTooLarge` | **Rev 1 (voice)** — `voice_turn` upload exceeds the 10 MB byte cap |
| `QueryTooLong` | **Rev 1 (voice)** — recording exceeds the 60 s cap (server best-effort probe; the client-side stop is primary enforcement) |
| `UnsupportedAudioFormat` | **Rev 1 (voice)** — upload MIME base-type not in the supported set (matching is on base type; codec parameters ignored) |
| `EmptyRecording` | **Rev 1 (voice)** — zero-byte upload |
| `UnintelligibleQuery` | **Rev 1 (voice)** — STT produced an empty/whitespace transcript |
| `VoiceUnavailable` | **Rev 1 (voice)** — STT/TTS unreachable; the text `turn` path is unaffected (degradation is a feature with copy — no cloud failover exists, [ADR-ARCH-024](../../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) D3) |

Voice `error_type` values are exception class names, matching the original four. They occur only on the Rev 1 voice verbs/frames — the four original types remain the complete set for the six original verbs.

## 10. Contract changes requiring `/design-refine`

This doc was **Proposed** precisely because it touches accepted contracts; all three changes below were recorded on ratification (2026-07-03, `/design-refine` G-CON):

1. **Relaxes "end-once, append-only, no resume"** ([API-tutoring.md §8](API-tutoring.md)) — adds `resume_session` / `list_sessions` and re-attachment while `active`. (§8 explicitly said `tutor_pause/resume` were "not requested" — they are now.)
2. **Adds an HTTP/WS surface** — [ADR-ARCH-008](../../architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md) is MCP-only; **ADR-FLEET-003 supersedes it for app clients**. Partial supersession recorded in ADR-ARCH-008 §Status (2026-07-03).
3. **Adds `student_id`, auth (`Unauthenticated`/`SessionForbidden`), and per-turn durability** — schema + error-set growth.

None of these change the MCP surface's existing behaviour; they *extend* it. Agent-hosts keep the four MCP tools exactly as-is.

4. **Revision 1 (2026-07-05, `/design-refine` G-CON — voice):** adds `voice_turn`/`voice_audio` (§5), the voice WS frame vocabulary (§7), and six voice error types (§9). **Additive only** — the six existing verbs, their wire shapes, the four original error types, and the MCP surface are byte-for-byte unchanged; existing clients pinned to the pre-Rev-1 SHAs keep working. Decisions consumed, not made, here: [ADR-ARCH-024](../../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) r1 (transport, pins, D3), [ADR-ARCH-026](../../architecture/decisions/ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md) (async Coach precondition), [ADR-ARCH-027](../../architecture/decisions/ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md) (chunk-boundary verification).

## 11. Open questions

1. **`sub → student_id` mapping** (handoff OQ4/D9) — where it lives (Keycloak attribute vs a `student` table lookup) and how a new student is provisioned.
2. **Concurrent resume** — is last-writer-wins + `session_version` enough, or does the robot↔phone hand-off need an explicit "active device" lease? (Single-user makes this low-stakes; revisit if two devices are ever truly simultaneous.)
3. ~~**Voice transport shape** (handoff OQ2) — single Realtime-style WS vs separate STT/TTS; decided when the GB10 voice endpoints are built.~~ **Resolved 2026-07-05** (Rev 1 §7; ADR-ARCH-024 r1): server-side STT/TTS inside `voice_turn` + the tutor's own WS. `/v1/realtime` is Reachy's shape only.
4. **Session TTL / auto-end** — does an `active` session that's untouched for N hours auto-`end` (triggering the StudentStore write) or stay resumable indefinitely? Affects streak/XP attribution timing.

---

*Proposed 2026-07-02; **Accepted 2026-07-03** via `/design-refine` (§10 changes recorded). **Revision 1 (voice) 2026-07-05** via `/design-refine` (§10 change 4; G-CON, voice build plan §5a). Consumed by FEAT-SMP-003 (`/feature-spec`), the mobile `/goal` opener, and FEAT-VOICE-001…004.*
