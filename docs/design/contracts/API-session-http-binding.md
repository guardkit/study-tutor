# API Contract — HTTP Binding for Cross-Device Session Persistence

**⚠️ FROZEN CONTRACT — changes after push require coordination with the app side.**

**Transport binding for:** [API-session-cross-device.md](API-session-cross-device.md) at `CONTRACT_SHA=<S-R2 ratification commit — Revision 2; pin on push, see Revision 2 note>` (contract **Revision 2** — gamification settlement; supersedes the Rev 1 pin `574615e916bfacafd014b2a0027b47cdf20d8f4a`)  
**Status:** Active — **Revision 2 (2026-07-12)**: `end_session`'s response gains the **nullable `gamification` block** (§2 binding table + contract §5 Rev 2) — the first re-pin of `CONTRACT_SHA` since the freeze. New `BINDING_SHA` = the S-R2 ratification commit (recorded on push, per the Rev-1 external-recording precedent). **Nullable ⇒ additive-safe:** clients pinned at the prior `BINDING_SHA=6eb7b88c…` / `CONTRACT_SHA=574615e…` keep working (the block is absent until settlement). **Revision 1 (2026-07-05)**: voice routes + WS binding added (`/design-refine` G-CON, [voice build plan §5a](../../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md)); those routes and status codes are unchanged by Rev 2.  
**Phase:** FEAT-APP-001 (HTTP/WS adapter for mobile+voice) → FEAT-VOICE-001…003 (voice phase) → Phase-R Lane B (gamification settlement)  
**Generated:** 2026-07-05 · **Revision 1:** 2026-07-05 · **Revision 2:** 2026-07-12

**Revision 2 note (2026-07-12, Phase-R S-R2) — `CONTRACT_SHA`/`BINDING_SHA` re-pin discipline:** contract [Revision 2](API-session-cross-device.md) is the first shape change to an *original* verb, so per §7 the binding must re-pin `CONTRACT_SHA` (to the commit that lands cross-device Revision 2) and record a new `BINDING_SHA` (this binding revision's commit). The S-R2 docs stage lands **both** the contract Revision 2 and this binding re-pin in **one commit**, so `CONTRACT_SHA` and `BINDING_SHA` **both resolve to that single S-R2 ratification commit**. A commit cannot cite its own hash, so — exactly as the Rev-1 `BINDING_SHA` was recorded externally (voice scope & build plan §0) — the concrete 40-char SHA is **pinned on push**: Rich records `git rev-parse HEAD` of the pushed S-R2 commit into both fields and the app-config pin. The app side bumps its `BINDING_SHA` to that value. Until then the placeholder above stands for "the S-R2 ratification commit". This re-pin is scoped to `end_session`; the six-verb-freeze (§7) otherwise holds.

**Addendum 2026-07-09 (FEAT-VOICE-004 R05):** additive read verb `GET /api/student-model` bound in §2.2. Additive only — the six session verbs, the voice Rev 1 routes, and their status codes are unchanged; the frozen voice `CONTRACT_SHA`/`BINDING_SHA` are **not** disturbed. This is a student-model read, not a session verb, so the transport-neutral session contract SHA is unaffected.

**Addendum 2026-07-31 (live robot-session mirror, Stage 1):** additive read verb `GET /api/sessions/{session_id}/turns?since={n}` bound in §2.4. Additive only — the six session verbs, the voice Rev 1 routes, and their status codes are unchanged, so there is **no `CONTRACT_SHA`/`BINDING_SHA` re-pin** (same posture as the `GET /api/student-model` addendum below). It is a delta *read* over the transcript `resume_session` already returns, not a session verb, so the transport-neutral session contract SHA is unaffected.

**Addendum 2026-07-12 (Phase-R S-R2):** additive **enrichment** of `GET /api/student-model` (§2.2) and additive **start_session response fields** (§2.1) — both additive, so **no `CONTRACT_SHA`/`BINDING_SHA` re-pin for these two** (only the `end_session` gamification block, being an original-verb shape change, drives the Revision 2 re-pin above). Every pre-existing field keeps its exact name and semantics; `data_available` unchanged.

---

## 1. Purpose

This document binds the transport-neutral [API-session-cross-device.md](API-session-cross-device.md) contract to the HTTP wire format. It defines the HTTP method, path, request/response JSON shapes, and status codes for each of the six session verbs. This binding is **frozen once pushed**: the Flutter app build consumes it at a pinned SHA (`BINDING_SHA`), making every route, method, and status code a hard commitment.

The contract (at the Revision 2 `CONTRACT_SHA` pinned in the header — superseding the Rev 1 pin `574615e916bfacafd014b2a0027b47cdf20d8f4a`) defines the transport-neutral semantics; this document provides the HTTP-specific details.

---

## 2. HTTP Binding Table

All endpoints use JSON request/response bodies. The server listens on **port 8100**.

| Verb | HTTP Method | Path | Request Shape (reference to contract §5) | Response Shape (reference to contract §5) |
|---|---|---|---|---|
| `start_session` | POST | `/api/sessions/start` | `{ subject?, topic?, resume_if_active? }` (contract §5) | `{ session_id, student_id, resumed: bool, turns?, topic?, opening_prompt?, focus_aos? }` (contract §5; the last three **additive** per §2.3, S-R2) |
| `list_sessions` | GET | `/api/sessions` | Query params: `status?`, `limit?` (contract §5) | `[{ session_id, subject, topic, status, started_at, last_activity, turn_count }]` (contract §5) |
| `resume_session` | GET | `/api/sessions/{session_id}/resume` | Path param: `session_id` (contract §5) | `{ session_id, status, turns:[{role,content,ts}], student_id }` (contract §5) |
| `turn` | POST | `/api/sessions/{session_id}/turn` | `{ user_message, stream? }` (contract §5); path param: `session_id` | `{ tutor_response }` (contract §5) or token stream (WS only, contract §7) |
| `session_status` | GET | `/api/sessions/{session_id}/status` | Path param: `session_id` (contract §5) | `{ session_id, student_id, status, turn_count, started_at, last_activity, resumable }` (contract §5) |
| `end_session` | POST | `/api/sessions/{session_id}/end` | Path param: `session_id` (contract §5) | `{ session_id, status:"ended", gamification? }` (contract §5 **Rev 2** — `gamification` is the nullable settlement block; absent until the engine settles the session) |
| `voice_turn` *(Rev 1)* | POST | `/api/sessions/{session_id}/voice-turn` | **`multipart/form-data`**, file field **`audio`** (filename + full content-type incl. codec params forwarded); `stream` reserved-and-ignored on HTTP (whole-response variant, like `turn`) | `{ transcript, tutor_response, audio: [{seq, chunk_id, url}] }` (contract §5 Rev 1) |
| `voice_audio` *(Rev 1)* | GET | `/api/sessions/{session_id}/voice-audio/{chunk_id}` | Path params: `session_id`, `chunk_id` | **`audio/wav`** bytes (binary response) |
| `student_model` *(read, R05)* | GET | `/api/student-model` | Query params: `subject` (required), `student_name?` (hint, ignored) | `{ student_name, streak_days, level_name, recent_xp, near_achievements:[], topic_confidence:{topic:conf}, data_available }` (§2.2) |
| `turns_since` *(read, 2026-07-31)* | GET | `/api/sessions/{session_id}/turns` | Path param: `session_id`; query param: `since?` (int row offset, default `0`) | `{ session_id, status, turns:[{role,content,ts}], next:int }` (§2.4) |

**Note:** Request and response JSON shapes are defined in contract §5. This binding table maps verbs to HTTP methods and paths; the payload semantics are unchanged from the contract.

**Rev 1 notes:**
- `voice_turn`'s multipart request and `voice_audio`'s binary response are the two deliberate exceptions to "all endpoints use JSON bodies".
- **Rollout flag:** the voice routes are mounted only when `STUDY_TUTOR_VOICE_ENABLED` is set (the same conditional-route pattern as §5's dev endpoints) — with the flag absent they return 404. The six original routes are never flag-gated.

### 2.1 WebSocket Binding (Rev 1)

**Endpoint:** `GET /api/sessions/{session_id}/ws` (WebSocket upgrade)

- Carries the streamed `turn` (client frame `{type:"turn", user_message, stream:true}`) and the streamed `voice_turn` (header frame + one binary message) — frame vocabulary and ordering per **contract §7 (Rev 1)**.
- **Auth:** the same `Authorization: Bearer <token>` header, presented on the upgrade request; `student_id` derivation and the session-ownership check run at upgrade time (403/401 close the socket with the error frame first where the handshake allows).
- **Errors:** domain errors surface as `{type:"error", error, error_type}` frames (the §4.1 envelope in frame form), after which the server closes the socket for terminal errors.
- The non-streaming HTTP `turn` and `voice_turn` remain available regardless — clients that don't stream never open the WS (contract §7).

### 2.2 Student-Model Read Binding (additive — FEAT-VOICE-004 R05)

**Endpoint:** `GET /api/student-model` (always mounted; bearer-authed like the six session verbs).

Serves the Reachy robot's `query_student_model` tool (sibling `fleet-gateway`, FEAT-VOICE-004 R05) — the durable learner record previously read from the now-frozen Graphiti graph (recon D2). **Additive read verb:** it does not alter the six session verbs, the voice Rev 1 routes, or their status codes, and it does **not** disturb the frozen voice `CONTRACT_SHA`/`BINDING_SHA`.

- **Query params:** `subject` (required — absent → 400), `student_name` (optional hint, **ignored**; identity is derived server-side from the token, never client-asserted).
- **Auth:** the same `Authorization: Bearer <token>` → `_resolve_student_id`. Unseeded/invalid token → `Unauthenticated` (401), never 500 (§3, ASSUM-001).
- **Response (200):**
  ```json
  {
    "student_name": "lilymay",
    "streak_days": 5,
    "level_name": "Learner",
    "recent_xp": 240,
    "near_achievements": [],
    "topic_confidence": {"macbeth": 0.7, "poetry": 0.55},
    "data_available": true
  }
  ```
- **Empty record:** a seeded student with no banked XP and no topic confidence returns 200 with `data_available: false` (never 500 for "nothing logged"). Consumers **gate on `data_available`**.
- **Projection scope (minimal real slice):** `streak_days` / `level_name` / `recent_xp` are derived at read time from the student's `ended` sessions (`study_tutor.gamification` — an honest subset of gamification design §2.1 / §3.1 / §4.1). `near_achievements` is always `[]` until the Phase-2 gamification state engine (**FEAT-PO-007**; gamification design §12, ADR-ARCH-013) ships the §5 achievement catalog + near-miss tracking. `level_name` values are the design §3.1 tiers (Beginner…Grandmaster), not the stale graph-era labels.
- **Consumer pin:** fleet-gateway pins the path via `common.tutor_client.STUDENT_MODEL_PATH` and maps any non-2xx (incl. a pre-ship 404) to a graceful "unavailable".

#### 2.2.1 Enrichment (additive — Phase-R S-R2, 2026-07-12)

Once the Phase-R gamification engine ([ADR-ARCH-030](../../architecture/decisions/ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md)) settles sessions and `get_gamification_state` reads banked facts, `GET /api/student-model` gains the following fields. **Additive only** — every field in the R05 response above keeps its **exact name and semantics**, `data_available` is unchanged, and the read stays a student-model read (no `CONTRACT_SHA`/`BINDING_SHA` re-pin, per the header S-R2 addendum). Fleet-gateway passes the dict opaquely and gates on `data_available`, so the enrichment is safe for the live Reachy consumer.

New fields:

- `total_xp` (int) — `SUM(session.xp_awarded) + SUM(achievement.xp_awarded)` (ADR-ARCH-030 D2).
- `level_number` (int, 1–15) — the level for `total_xp` (design §3.1 thresholds).
- `xp_into_level` (int) — XP accumulated **within** the current level.
- `xp_to_next_level` (int) — XP remaining to the next threshold (0 at Level 15, terminal).
- `longest_streak` (int) — longest consecutive-London-day streak ever (design §4.1; London calendar per design §13.1 D6).
- `recent_achievements` (array, **last 5** by unlock time, newest first) — `[{id, name, unlocked_at, xp_awarded}]`.
- `near_achievements` — **shape change** from the R05 hardwired `[]` to **top-3 objects** `[{id, name, description, progress, target, hint}]`, where `progress`/`target` are integers on the same scale (e.g. `{progress: 4, target: 5}` for Morning Star) and `hint` is a static per-achievement "what gets you there" string with progress interpolated. Empty array while nothing is close.
- `next_unlock` — `{level, feature}`: the next level-gated feature (design §3.2 unlock gates), e.g. `{level: 6, feature: "Exam-style practice questions"}`.

Enriched response (200), additive over the R05 shape:

```json
{
  "student_name": "lilymay",
  "streak_days": 6,
  "level_name": "Learner",
  "recent_xp": 240,
  "topic_confidence": {"macbeth": 0.7, "poetry": 0.55},
  "data_available": true,

  "total_xp": 640,
  "level_number": 5,
  "xp_into_level": 40,
  "xp_to_next_level": 460,
  "longest_streak": 8,
  "recent_achievements": [
    {"id": "three_day_run", "name": "Three Day Run", "unlocked_at": "2026-07-11T18:20:00+01:00", "xp_awarded": 100}
  ],
  "near_achievements": [
    {"id": "morning_star", "name": "Morning Star", "description": "5 sessions started before 09:00", "progress": 4, "target": 5, "hint": "One more early-morning session (4/5)."}
  ],
  "next_unlock": {"level": 6, "feature": "Exam-style practice questions"}
}
```

> **Courtesy note to the fleet-gateway team (Phase-R S-R2 — no code change required here; Rich delivers this).** `near_achievements` changes from the R05 hardwired `[]` to an array of **objects** `[{id, name, description, progress, target, hint}]`. fleet-gateway passes the student-model dict opaquely and gates only on `data_available`, so nothing breaks. But the Scholar narration prompt now has real material: it may want to read `progress`/`target` (e.g. *"two sessions away from Poetry Pioneer"* — design §9.1) and the ready-made `hint` string, rather than treating `near_achievements` as always-empty. `recent_achievements` (last 5, with `unlocked_at`) similarly feeds the "celebration"/"what she just earned" narration. This is an **additive** enrichment: no field is renamed or removed. Rich hands this note to the fleet-gateway lane; **no edits are made outside the study-tutor repo by this stage.**

---

### 2.3 `start_session` Response Enrichment (additive — Phase-R S-R2)

When planning moves into `SessionService.start_session` (spec §2.1, [ADR-ARCH-030](../../architecture/decisions/ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md) D7 hook), the `POST /api/sessions/start` response gains three **additive** fields. **No `CONTRACT_SHA`/`BINDING_SHA` re-pin** (additive addendum, not an original-verb shape change): the existing `{session_id, student_id, resumed, turns?}` fields keep their exact names and semantics; pinned clients that ignore unknown fields are unaffected.

- `topic` (string|null) — the planned topic for the session (the session's persisted `topic`).
- `opening_prompt` (string|null) — the planner's opening prompt for the first turn. **Not persisted** on the session row (spec §2.1); returned in the start response only.
- `focus_aos` (array of AO strings, e.g. `["AO2","AO3"]`) — the assessment objectives the plan focuses on (from the persisted plan facts). Empty array when the planner produced none / degraded to baseline.

The MCP `tutor_start_session` keeps its existing `plan_summary` shape, now sourced from the same service-side plan (spec §2.1); this HTTP enrichment is the transport-neutral plan surfaced on the HTTP verb.

---

### 2.4 Turns-Since Delta Read Binding (additive — live robot-session mirror Stage 1, 2026-07-31)

**Endpoint:** `GET /api/sessions/{session_id}/turns` (always mounted, never flag-gated; bearer-authed like the six session verbs).

Serves the phone's **read-only live mirror** of the tutoring session the Reachy Mini robot is driving (handoff `docs/runbooks/HANDOFF-spark-live-robot-session-mirror.md` Stage 1). The phone polls this in place of `status` + `resume`, so an update costs O(new rows) rather than O(whole conversation).

**Additive read verb:** it does **not** alter the six session verbs, the voice Rev 1 routes, or their status codes, and it does **not** disturb the frozen `CONTRACT_SHA`/`BINDING_SHA` (no re-pin — same posture as §2.2's `GET /api/student-model`). It is a delta read over the transcript `resume_session` already returns; the transport-neutral session contract is unchanged. Ephemeral/no-audio-at-rest (§6 Rev 1) is unaffected — these are text turns only.

- **Path param:** `session_id`.
- **Query param:** `since` (optional, default `0`) — a plain **0-based row offset** into the same ordered rows `resume_session` returns, **not** a timestamp and **not** the `turn_count // 2` pairs number that `list_sessions`/`session_status` project. Non-integer or negative → 400 (§4.2, no `error_type`).
- **Auth/ownership:** the same `Authorization: Bearer <token>` → `_resolve_student_id`; the session's `student_id` must equal the caller's, else `SessionForbidden` (403). Identity is never client-asserted.
- **Response (200):**
  ```json
  {
    "session_id": "sess-123",
    "status": "active",
    "turns": [
      {"role": "user", "content": "What drives Macbeth?", "ts": "2026-07-31T10:15:00+00:00"},
      {"role": "tutor", "content": "Let's look at Act 1...", "ts": "2026-07-31T10:15:04+00:00"}
    ],
    "next": 8
  }
  ```
  - `turns` — only the rows at index ≥ `since`. The row shape is **byte-identical** to `resume_session`'s (`{role, content, ts}`, `ts` an ISO-8601 `datetime.isoformat()`), so the app's existing transcript parser is reused unchanged.
  - `next` — the **raw total row count** of the session's transcript (again, never the `// 2` pairs number). The client passes it back as `since` on the next poll.
- **Beyond the end:** `since >= next` returns `turns: []` with `next` = the total, **200 — not an error**.
- **Ended sessions:** unlike `resume_session`, this read works for **active *and* ended** sessions (service-side `allow_ended=True`, the same carve-out `session_status` uses), so the poll survives the active→ended transition. **`SessionEnded` (410) is therefore impossible on this route.**
- **Errors:** `SessionNotFoundError` → 404, `SessionForbidden` → 403, `Unauthenticated` → 401 (§4.1 envelope); malformed `since` → 400 with `{"error": "Validation failed: …"}` and no `error_type` (§4.2).

---

## 3. Authentication

**Header:** `Authorization: Bearer <token>`

- The token is honored from the credential header **ONLY**.
- The server resolves `student_id` from the validated token (contract §3 derivation; never client-asserted).
- **Interim single-user mode:** While Keycloak is not yet fronting the API, the adapter resolves a single configured `student_id` (Lilymay). The binding does not change when auth turns on; only the derivation source does.

**ASSUM-001 (unseeded student):** An authenticated-but-unseeded student (valid token but no StudentStore record) is refused as `Unauthenticated` (HTTP 401), **never a 500**. The StudentStore seed is a prerequisite for session access.

---

## 4. Error Status Codes

The contract defines a closed set of four domain errors (contract §9, `src/study_tutor/session/errors.py`). Each maps to exactly one HTTP status code within the flat `{"error", "error_type"}` envelope (contract §9, API-tutoring §4).

### 4.1 Closed-Set Domain Errors

| `error_type` | HTTP Status | Trigger |
|---|---|---|
| `SessionNotFoundError` | 404 Not Found | `session_id` unknown |
| `SessionEnded` | 410 Gone | Verb on an `ended` session (except `session_status`) |
| `SessionForbidden` | 403 Forbidden | Session's `student_id` ≠ caller's `student_id` |
| `Unauthenticated` | 401 Unauthorized | Missing/invalid Keycloak token or unseeded student (ASSUM-001) |
| `RecordingTooLarge` *(Rev 1, voice)* | 413 Payload Too Large | `voice_turn` upload exceeds the 10 MB byte cap |
| `QueryTooLong` *(Rev 1, voice)* | 413 Payload Too Large | Recording exceeds the 60 s cap (server best-effort) |
| `UnsupportedAudioFormat` *(Rev 1, voice)* | 415 Unsupported Media Type | Upload MIME base-type not in the supported set |
| `EmptyRecording` *(Rev 1, voice)* | 422 Unprocessable Entity | Zero-byte upload |
| `UnintelligibleQuery` *(Rev 1, voice)* | 422 Unprocessable Entity | STT produced an empty/whitespace transcript |
| `VoiceUnavailable` *(Rev 1, voice)* | 503 Service Unavailable | STT/TTS unreachable — text `turn` unaffected (degradation copy, no cloud failover) |

**Response body** (all types, unchanged envelope):
```json
{
  "error": "Human-readable message",
  "error_type": "<one of the types above>"
}
```

The six Rev 1 voice types occur only on the voice verbs/WS frames (contract §9 Rev 1); the original four remain the complete set for the six original verbs.

### 4.2 Transport-Level Errors (Outside Closed Set)

These are HTTP-layer postures, not domain errors from `session/errors.py`.

| Condition | HTTP Status | Response Shape |
|---|---|---|
| Malformed JSON / missing required field | 400 Bad Request | `{ "error": "Validation failed: <details>" }` (no `error_type` — not a domain error) |
| Unexpected server error | 500 Internal Server Error | `{ "error": "Internal server error" }` (no `error_type`) |
| Unknown/expired `voice_audio` `chunk_id` *(Rev 1)* | 404 Not Found | `{ "error": "audio chunk expired or unknown" }` (no `error_type` — chunk refs are ephemeral by design, TTL ≤120 s; the client skips the chunk and continues playback) |

**Note:** Validation errors (400) do **not** carry an `error_type` because they are not part of the closed contract set defined in `session/errors.py`. They are transport-level rejections that occur before the service layer is reached.

---

## 5. Dev Endpoints

These endpoints are **environment-flag-gated** and absent from production.

### 5.1 Dev Token Table

The fake auth server's token-to-student mapping (mirrors `app/lib/fakes/fake_identity_provider.dart` lines 22-25, **read-only reference**):

| Token | `student_id` |
|---|---|
| `token-lilymay` | `lilymay` |
| `token-alex` | `alex` |

**CRITICAL:** These values MUST equal the app's fake IdP constants at `app/lib/fakes/fake_identity_provider.dart:16,19`. **Never edit `app/**`** — this is a read-only reference.

### 5.2 Reset Route

**Endpoint:** `POST /__dev__/reset`

- **Purpose:** Truncates `session` + `session_turn` rows only (no StudentStore state).
- **Scope:** Global server state — affects all students.
- **Consequence:** The live acceptance suite **must run with `--concurrency=1`** to avoid test isolation failures.
- **Presence:** Dev/test environments only; env-flag-gated (absent from prod).

### 5.3 Health Route

**Endpoint:** `GET /healthz`

- **Purpose:** Liveness check.
- **Response:** `200 OK` when the server is responsive.
- **Port:** **8100** (same as the API).

---

## 6. Notes

- **Streaming semantics (voice, Rev 1):** Contract §7 (Rev 1) now defines the complete WS frame vocabulary — `voice_turn` header + binary upload inbound; `transcript` / `token` / `audio_ref` / `done` / `error` outbound — bound at §2.1. HTTP `turn` and HTTP `voice_turn` return whole responses; streaming is WS-only. The question formerly deferred here (handoff OQ2) is resolved: server-side STT/TTS inside `voice_turn` (ADR-ARCH-024 r1).
- **Ephemeral audio (Rev 1):** inbound `voice_turn` audio is transcribed and discarded — parsed in memory, never written to disk, DB, or logs; synthesized chunks live in an in-memory TTL-bounded store only. No audio at rest anywhere (ADR-ARCH-024 D3 + blueprint §5; verified by the voice live smoke's DB/disk sweep).
- **Persistence timing:** Contract §6 defines per-turn synchronous Postgres writes and `end_session` learner-state commits. The HTTP binding does not change these semantics.
- **Ownership checks:** Every verb taking a `session_id` asserts the session's `student_id == caller student_id`, else `SessionForbidden` (403). This is a service-layer rule, not an HTTP-specific detail, but it propagates to every HTTP endpoint that accepts `session_id`.

---

## 7. Freeze Discipline

**This document is frozen once pushed.** The Flutter app consumes it at a pinned SHA (`BINDING_SHA`). Changes to routes, methods, or status codes require:

1. Coordination with the app side (bump `BINDING_SHA` in app config).
2. A migration plan if live app instances are in the wild.
3. `/design-refine` if the change touches the contract (contract §10).

**Before editing:** confirm the change is truly required and communicate with the mobile team.

---

*Authored 2026-07-05 for FEAT-APP-001 (TASK-APP1-01); bound contract `22791afbcdb3b71abbe6bd2f1b8e18218988942f`. **Revision 1** 2026-07-05 (G-CON, voice — `/design-refine`): binds contract Revision 1 at `574615e916bfacafd014b2a0027b47cdf20d8f4a`; this revision's commit is the new `BINDING_SHA`, recorded in the [voice scope & build plan §0](../../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md). The prior `BINDING_SHA=6eb7b88c…` remains valid for phase-2 clients (additive change).*
