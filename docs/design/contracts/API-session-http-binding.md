# API Contract — HTTP Binding for Cross-Device Session Persistence

**⚠️ FROZEN CONTRACT — changes after push require coordination with the app side.**

**Transport binding for:** [API-session-cross-device.md](API-session-cross-device.md) at `CONTRACT_SHA=574615e916bfacafd014b2a0027b47cdf20d8f4a` (contract Revision 1 — voice)  
**Status:** Active — **Revision 1 (2026-07-05)**: voice routes + WS binding added (`/design-refine` G-CON, [voice build plan §5a](../../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md)). Additive only: the six original verbs, their routes, and status codes are unchanged — clients pinned at `BINDING_SHA=6eb7b88c…` keep working.  
**Phase:** FEAT-APP-001 (HTTP/WS adapter for mobile+voice) → FEAT-VOICE-001…003 (voice phase)  
**Generated:** 2026-07-05 · **Revision 1:** 2026-07-05

---

## 1. Purpose

This document binds the transport-neutral [API-session-cross-device.md](API-session-cross-device.md) contract to the HTTP wire format. It defines the HTTP method, path, request/response JSON shapes, and status codes for each of the six session verbs. This binding is **frozen once pushed**: the Flutter app build consumes it at a pinned SHA (`BINDING_SHA`), making every route, method, and status code a hard commitment.

The contract (at `CONTRACT_SHA=574615e916bfacafd014b2a0027b47cdf20d8f4a`, Revision 1) defines the transport-neutral semantics; this document provides the HTTP-specific details.

---

## 2. HTTP Binding Table

All endpoints use JSON request/response bodies. The server listens on **port 8100**.

| Verb | HTTP Method | Path | Request Shape (reference to contract §5) | Response Shape (reference to contract §5) |
|---|---|---|---|---|
| `start_session` | POST | `/api/sessions/start` | `{ subject?, topic?, resume_if_active? }` (contract §5) | `{ session_id, student_id, resumed: bool, turns? }` (contract §5) |
| `list_sessions` | GET | `/api/sessions` | Query params: `status?`, `limit?` (contract §5) | `[{ session_id, subject, topic, status, started_at, last_activity, turn_count }]` (contract §5) |
| `resume_session` | GET | `/api/sessions/{session_id}/resume` | Path param: `session_id` (contract §5) | `{ session_id, status, turns:[{role,content,ts}], student_id }` (contract §5) |
| `turn` | POST | `/api/sessions/{session_id}/turn` | `{ user_message, stream? }` (contract §5); path param: `session_id` | `{ tutor_response }` (contract §5) or token stream (WS only, contract §7) |
| `session_status` | GET | `/api/sessions/{session_id}/status` | Path param: `session_id` (contract §5) | `{ session_id, student_id, status, turn_count, started_at, last_activity, resumable }` (contract §5) |
| `end_session` | POST | `/api/sessions/{session_id}/end` | Path param: `session_id` (contract §5) | `{ session_id, status:"ended" }` (contract §5) |
| `voice_turn` *(Rev 1)* | POST | `/api/sessions/{session_id}/voice-turn` | **`multipart/form-data`**, file field **`audio`** (filename + full content-type incl. codec params forwarded); `stream` reserved-and-ignored on HTTP (whole-response variant, like `turn`) | `{ transcript, tutor_response, audio: [{seq, chunk_id, url}] }` (contract §5 Rev 1) |
| `voice_audio` *(Rev 1)* | GET | `/api/sessions/{session_id}/voice-audio/{chunk_id}` | Path params: `session_id`, `chunk_id` | **`audio/wav`** bytes (binary response) |

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
