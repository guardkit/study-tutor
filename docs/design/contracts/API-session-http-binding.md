# API Contract — HTTP Binding for Cross-Device Session Persistence

**⚠️ FROZEN CONTRACT — changes after push require coordination with the app side.**

**Transport binding for:** [API-session-cross-device.md](API-session-cross-device.md) at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`  
**Status:** Active  
**Phase:** FEAT-APP-001 (HTTP/WS adapter for mobile+voice)  
**Generated:** 2026-07-05

---

## 1. Purpose

This document binds the transport-neutral [API-session-cross-device.md](API-session-cross-device.md) contract to the HTTP wire format. It defines the HTTP method, path, request/response JSON shapes, and status codes for each of the six session verbs. This binding is **frozen once pushed**: the Flutter app build consumes it at a pinned SHA (`BINDING_SHA`), making every route, method, and status code a hard commitment.

The contract (at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`) defines the transport-neutral semantics; this document provides the HTTP-specific details.

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

**Note:** Request and response JSON shapes are defined in contract §5. This binding table maps verbs to HTTP methods and paths; the payload semantics are unchanged from the contract.

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

**Response body** (all four):
```json
{
  "error": "Human-readable message",
  "error_type": "<one of the four types above>"
}
```

### 4.2 Transport-Level Errors (Outside Closed Set)

These are HTTP-layer postures, not domain errors from `session/errors.py`.

| Condition | HTTP Status | Response Shape |
|---|---|---|
| Malformed JSON / missing required field | 400 Bad Request | `{ "error": "Validation failed: <details>" }` (no `error_type` — not a domain error) |
| Unexpected server error | 500 Internal Server Error | `{ "error": "Internal server error" }` (no `error_type`) |

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

- **Streaming semantics (voice):** Contract §7 defines token streaming for WebSocket `turn` with `stream: true`. HTTP `turn` returns the whole `{ tutor_response }` — no streaming. WebSocket streaming details are deferred to the voice transport implementation (handoff OQ2).
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

*Authored 2026-07-05 for FEAT-APP-001 (TASK-APP1-01). Binds contract `22791afbcdb3b71abbe6bd2f1b8e18218988942f`.*
