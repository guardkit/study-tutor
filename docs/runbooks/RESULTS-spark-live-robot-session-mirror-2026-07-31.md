# Results — backend support for the live robot-session mirror (spark lane)

**Date:** 2026-07-31 · **Handoff:** [HANDOFF-spark-live-robot-session-mirror.md](HANDOFF-spark-live-robot-session-mirror.md) · **Method:** orchestrated-build-playbook (run `wf_40c1458e-204`, 4 agents, zero fix passes)
**State:** both stages built, coach-verified, coordinator-reviewed. **Committed locally only — nothing pushed.** The merge word is Rich's.

---

## The two rulings (owner gate pre-granted 2026-07-31)

1. **Stage 1 (the `turns-since` delta read) ruled IN.** The handoff recommends it; the plan-of-record's Study-Tutor track names the live app↔backend integration as the lane's consumer. **Seat (amendment 5):** the phone's live-mirror poll calls `turns?since=` in place of `status`+`resume`.
2. **Stage 2 (real-time push) ruled IN, mechanism = SSE** — the choice the handoff left to the design pass. Grounds, verified in code: the existing `/ws` route is mounted **only** behind `STUDY_TUTOR_VOICE_ENABLED` and carries the frozen contract-§7 streamed-**write** frame vocabulary; the mirror is a one-way read-only viewer that must work with voice off. SSE is an additive read route, the same no-re-pin class as Stage 1.

## What shipped (2 local commits on `main`, baseline `0471a8f`)

| Commit | Stage | Content |
|---|---|---|
| `96816ff` | S1 | `GET /api/sessions/{id}/turns?since={n}` → `{session_id, status, turns:[{role,content,ts}], next}`. Service read with `allow_ended=True` (poll survives the active→ended transition; 410 impossible). Binding addendum §2.4. 25 tests. |
| `a62eac3` | S2 | `GET /api/sessions/{id}/turns/stream` — SSE (`turn_appended` carrying the §2.4 envelope verbatim, terminal `session_ended`, `: keepalive` comments). In-process `TurnNotifier` pinged by the service after each persisted row and after `end_session`'s finalize; stream also re-reads every 3 s tick, so cross-process writes surface anyway; degrades to pure ticking when unwired. One notifier instance shared by service and app (wiring + `serve-http`). Binding addendum §2.5. 34 tests. |

Both routes are always mounted, bearer-authed, ownership from the token only, additive — **no `CONTRACT_SHA`/`BINDING_SHA` re-pin** (the `GET /api/student-model` posture).

## Coordinator review (playbook rule 4 — all driven by the coordinator's own hands)

- **Suite re-run:** 1634 passed, 31 skipped, **1 pre-existing failure only** (see below). 59 new tests over the 1575 baseline.
- **Full diff read** (`git diff 0471a8f..HEAD`, +2005/−3): the only deleted lines anywhere are 2 wiring lines replaced in `session/wiring.py` and 1 import line in `cli/main.py`. `http/app.py` and `session/service.py` have **zero deletions** → the six frozen verbs, the voice routes, and every status code are byte-unchanged. Store port untouched. Ephemeral/no-audio-at-rest unaffected (text rows only).
- **Broker isolation grep** lane-wide: no `nats://`, no `4222`, no NATS import, no CLI use — only docstring prose saying "no broker".
- **End-to-end smoke** (coordinator-authored, in-process): missing token → plain JSON 401 (no stream); `since=-1` → 400 without `error_type`; poll route returns the correct delta; the stream delivered catch-up → notified delta → terminal `session_ended`, rows byte-identical to `resume`'s shape.
- **Local only:** `origin/main` = `0471a8f`; nothing pushed.

## Advisory findings (coach, agreed by the coordinator — none blocking)

- **Notifier missed-signal window:** a `notify()` landing between a stream's read and its next park waits out the ≤3 s tick (the `_SessionSignal.version` field is currently unused; a version-compare in `wait_for_change` would close the window). Latency-only, bounded, and the tick is the binding-§2.5-specified fallback.
- **Store read is O(whole transcript) per poll** — only the wire payload is O(new rows), by design (store port fence). Revisit only if per-poll DB cost ever matters.
- **Per-viewer tick load:** even with the notifier, each open stream re-reads every 3 s — the notifier buys latency, not DB load. Fine at one-viewer scale.

## Left for Rich (the merge word)

1. Push `96816ff` + `a62eac3` (+ this record) when satisfied; then tell the app lane the Stage-1/Stage-2 endpoints are live so the phone can swap its poll to `turns?since=` and optionally the stream.
2. Plan-of-record Track F cell update lives in `ai-transition` — cross-repo, not edited by this lane.
3. **Pre-existing, named (not this lane's):** the hermetic suite's one standing failure is `test_no_whitestocks_connection_in_tests` — the NAS scope guard trips on the string "whitestocks" in `tests/unit/http/test_auth_keycloak.py`, left by the earlier auth lane. Candidate for known-issues.md or a one-line fix in that lane's scope.
