---
complexity: 6
dependencies: []
feature_id: FEAT-AUTH-002
id: TASK-KCA2-002
implementation_mode: task-work
parent_review: TASK-REV-KCA2
status: design_approved
task_type: refactor
title: TokenResolver protocol + TableTokenResolver refactor — resolve_student_from_token
  delegates step 2
wave: 1
---

## Description

Introduce the resolver seam in [auth.py](../../../src/study_tutor/http/auth.py)
per **KC-D6**, preserving the outer auth contract byte-for-byte. Producer of the
**§4 `TOKEN_RESOLVER`** contract (consumed by TASK-KCA2-004).

**Deliverables (all in `src/study_tutor/http/auth.py`):**

1. **`TokenResolver` protocol** — `async def resolve(self, token: str) -> str`,
   raising `Unauthenticated` on any un-resolvable token. This is "step 2" (the
   derivation source) extracted behind an interface.
2. **`TableTokenResolver`** — a frozen dataclass wrapping `token_to_student`;
   `resolve` does the existing dict lookup and raises `Unauthenticated("Unknown
   token")` on a miss. **Behaviour identical to today's inline lookup.**
3. **`HTTPAuthConfig` gains `resolver: TokenResolver`** (Option 1 from the review):
   `from_env` constructs a `TableTokenResolver` from the parsed table so existing
   callers are unchanged. `resolve_student_from_token(header, config, store)`
   keeps its **signature** and its (1) Bearer extraction and (3) unseeded-student
   guard verbatim — only the inline table lookup becomes
   `student_id = await config.resolver.resolve(token)`.

The [app.py](../../../src/study_tutor/http/app.py) `_resolve_student_id` and
[ws.py](../../../src/study_tutor/http/ws.py) upgrade path call the same function,
so **WS inherits the resolver for free** (binding §2.1) — do not touch those files.

**Permanent invariant of the WHOLE feature (safe to assert, never filled later):**
`auth.py` imports **no** `jwt` / `keycloak` / `jose` symbol — the AC-005 tripwire
stays green here. The Keycloak imports arrive in a *different* module
(`auth_keycloak.py`, TASK-KCA2-003), never in this file. Do **not** import
`auth_keycloak` from `auth.py` (that would drag the string `keycloak` into the
file the tripwire greps).

## Acceptance Criteria

- [ ] `TokenResolver` protocol and `TableTokenResolver` exist in `auth.py`; `HTTPAuthConfig` carries a `resolver` built by `from_env`
- [ ] `resolve_student_from_token` keeps its signature and delegates only step 2 to `config.resolver.resolve(token)`; Bearer extraction and the unseeded-student guard are unchanged
- [ ] The existing `tests/unit/http/test_auth.py` suite (incl. missing-header, non-Bearer, unknown-token, unseeded-guard) passes unchanged — table mode is **byte-for-byte** identical
- [ ] `auth.py` contains no `jwt`/`keycloak`/`jose` import (AC-005 tripwire stays green)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "In table mode a configured token identifies its student" (@smoke)
- "The Bearer extraction contract is identical in both modes" (table branch)
- "A non-Bearer Authorization header is rejected in both modes" (table branch)

## References

- design [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) (TokenResolver seam) · seam [auth.py](../../../src/study_tutor/http/auth.py) + AC-005 tripwire [test_auth.py](../../../tests/unit/http/test_auth.py) · [binding §2.1 WS auth](../../../docs/design/contracts/) · IMPLEMENTATION-GUIDE §4 (`TOKEN_RESOLVER`) · security-touching (auth boundary) ⇒ FULL_REQUIRED human checkpoint
</content>
</invoke>