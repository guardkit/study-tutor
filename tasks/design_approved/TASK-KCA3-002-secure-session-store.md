---
complexity: 5
dependencies:
- TASK-KCA3-001
feature_id: FEAT-AUTH-003
id: TASK-KCA3-002
implementation_mode: task-work
parent_review: TASK-REV-KCA3
status: design_approved
task_type: feature
title: SecureSessionStore — flutter_secure_storage-backed token-response persistence
  (read/write/clear, unreadable ⇒ absent)
wave: 2
---

## Description

The persistence seam that keeps the family device signed in across restarts. A
`SecureSessionStore` in `app/lib/adapters/secure_session_store.dart` wraps
`flutter_secure_storage` (added in TASK-KCA3-001) and holds exactly the fields the
adapter needs to silently refresh: the **refresh token** (`offline_access`), the
access token, and the access-token expiry. Design ref **KC-D7** (offline token so
the family device stays signed in; KC-D4 offline idle default 30 days).

Producer of the **§4 `STORED_SESSION`** contract (consumed by TASK-KCA3-003).

**Deliverables:**

1. **`SecureSessionStore`** with a small, storage-shaped API:
   - `Future<StoredSession?> read()` — deserialize the persisted blob; returns
     `null` when nothing is stored **and** when the blob is unreadable/corrupt or
     the platform read throws (fail-closed to signed-out, never propagate).
   - `Future<void> write(StoredSession session)` — serialize + persist under a
     single key.
   - `Future<void> clear()` — delete the key.
2. **`StoredSession`** — a plain value object (`refreshToken`, `accessToken`,
   `accessTokenExpiry`, `displayName`) with JSON (de)serialization. No
   `flutter_appauth` type leaks across this seam — the adapter maps the appauth
   `TokenResponse` ↔ `StoredSession`, so the store stays library-agnostic and
   unit-testable without a browser.
3. Persist via `flutter_secure_storage` (platform Keystore / Keychain), **never**
   `SharedPreferences`/plaintext — a minor's session on a shared device must live
   in the platform secure store (@security).

**Hermetic tests (`app/test/adapters/secure_session_store_test.dart`) — no
platform channel:** inject a fake/in-memory `FlutterSecureStorage` (constructor
injection) and cover: round-trip write→read; `read()` on empty ⇒ `null`;
`read()` on a corrupt/undeserializable blob ⇒ `null` (no throw); `read()` when the
backing store throws ⇒ `null`; `clear()` removes the key.

## Acceptance Criteria

- [ ] `SecureSessionStore.write`/`read` round-trips a `StoredSession` (refresh token, access token, expiry, displayName) through `flutter_secure_storage`
- [ ] `read()` returns `null` for an absent key **and** for an unreadable/corrupt blob **and** when the backing store throws — it never propagates an exception (serves "An unreadable stored session is treated as signed out")
- [ ] The session is persisted in the platform secure store (`flutter_secure_storage`), not plaintext `SharedPreferences` (serves "The signed-in session is held in the platform secure store")
- [ ] `clear()` removes the persisted session
- [ ] No `flutter_appauth` type crosses the store API (the adapter owns the `TokenResponse` ↔ `StoredSession` mapping)
- [ ] Tests inject a fake secure storage — no platform channel, no real Keystore/Keychain
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "The signed-in session is held in the platform secure store" (@edge-case @security)
- "An unreadable stored session is treated as signed out" (@edge-case @negative)
- Persistence side of "The device stays signed in across an app restart without a browser prompt" (@key-example @smoke)

## References

- design [KC-D7 / KC-D4](../../../docs/design/keycloak-auth-user-management-design.md) (offline token; offline idle 30 days) · IMPLEMENTATION-GUIDE §4 (`STORED_SESSION`)