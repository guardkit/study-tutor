# Results — backend support for the live robot-session mirror (spark lane)

**Date:** 2026-07-31 · **Handoff:** [HANDOFF-spark-live-robot-session-mirror.md](HANDOFF-spark-live-robot-session-mirror.md) · **Method:** orchestrated-build-playbook (runs `wf_40c1458e-204` S1+S2, 4 agents · `wf_3813003b-37f` S0, 2 agents — zero fix passes across all three stages)
**State:** all three stages (S0 added by the 2026-07-31 handoff amendment, built after S1/S2) coach-verified and coordinator-reviewed. Merge word given 2026-07-31; push blocked only on this machine's missing GitHub credentials (the `spark-fcf6` SSH key needs registering) — everything is committed locally and queued.

---

## The rulings (owner gate pre-granted 2026-07-31)

1. **Stage 1 (the `turns-since` delta read) ruled IN.** The handoff recommends it; the plan-of-record's Study-Tutor track names the live app↔backend integration as the lane's consumer. **Seat (amendment 5):** the phone's live-mirror poll calls `turns?since=` in place of `status`+`resume`.
2. **Stage 2 (real-time push) ruled IN, mechanism = SSE** — the choice the handoff left to the design pass. Grounds, verified in code: the existing `/ws` route is mounted **only** behind `STUDY_TUTOR_VOICE_ENABLED` and carries the frozen contract-§7 streamed-**write** frame vocabulary; the mirror is a one-way read-only viewer that must work with voice off. SSE is an additive read route, the same no-re-pin class as Stage 1.
3. **Stage 0 contract ruling** (the call the amended handoff delegated): widening `resume` to read ended sessions is an **additive-safe widening, no `CONTRACT_SHA`/`BINDING_SHA` re-pin**. Grounds (recorded verbatim in both contract docs' dated addenda): response shape unchanged; *previously-errored → now-returns* cannot break a pinned client's success path; the sole pinned consumer (`app/`) requested it and its shared contract test `s4_lifecycle_test.dart` already expects it. **Rich may still re-pin on push** — the S0 coach's §7-freeze note flags that 410→200 for one state *is* a status-code change on an original verb, so the discretion is real, not rubber-stamped.

## What shipped (baseline `0471a8f` for S1/S2; post-merge `2ae4d9e` for S0)

| Commit | Stage | Content |
|---|---|---|
| `96816ff` | S1 | `GET /api/sessions/{id}/turns?since={n}` → `{session_id, status, turns:[{role,content,ts}], next}`. Service read with `allow_ended=True` (poll survives the active→ended transition; 410 impossible). Binding addendum §2.4. 25 tests. |
| `a62eac3` | S2 | `GET /api/sessions/{id}/turns/stream` — SSE (`turn_appended` carrying the §2.4 envelope verbatim, terminal `session_ended`, `: keepalive` comments). In-process `TurnNotifier` pinged by the service after each persisted row and after `end_session`'s finalize; stream also re-reads every 3 s tick, so cross-process writes surface anyway; degrades to pure ticking when unwired. One notifier instance shared by service and app (wiring + `serve-http`). Binding addendum §2.5. 34 tests. |
| `833f6de` | S0 | `resume` reads **ended** sessions (the History screen's transcript read; built after S1/S2 because the handoff amendment adding it arrived with the app-lane merge). One behavior change: `resume_session` flips to `allow_ended=True`; handler and `ResumeResult` shape untouched. Terminality pinned: `turn`/`turn_stream`/`end_session`/`voice_turn` keep `allow_ended=False` → 410, with new regression tests. Backend now matches the app's shared contract test exactly. Dated addenda in the binding **and** the cross-device contract carrying ruling 3. 9 net-new tests (suite 1634 → 1643). |

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

## Stage 0 review (2026-07-31, after the merge word — coordinator-driven like the rest)

- Suite re-run by the coordinator's hand: **1643 passed**, 31 skipped, only the known pre-existing failure.
- S0 diff read: the sole behavior change is the `allow_ended=True` flip at the service; `app.py` gained docstring lines only (zero deletions); 410 mapping retained and pinned by a new test.
- Coordinator smoke through the real service + routes: resume of an ended session → 200 with the ordered transcript and `status: "ended"`; `turn` and `end` on the same session → 410 `SessionEnded`.
- Coach notes accepted and surfaced (none blocking): the binding §4.1 trigger cell carries a dated **in-place** annotation (its cross-device twin was handled by addendum instead — method inconsistency only, semantics correct); the §7 freeze-discipline point above feeds ruling 3's re-pin discretion; a stale §2.4 phrase ("unlike `resume_session`…") is corrected by the addendum text rather than rewritten.
- Also verified at S0: the one extra failure seen when running the durable-cross-device feature file **standalone** (`test_redelivering_the_same_completed_session…`) reproduces identically at the pre-S0 baseline — a pre-existing fixture-ordering artifact, green in full-suite order, not this lane's.

## Left for Rich (merge word given 2026-07-31; push pending credentials)

1. **Unblock the push:** register the spark machine's `spark-fcf6` SSH key (`~/.ssh/id_ed25519.pub`) with GitHub — this box has no `gh`, token, or registered key. Queued to push: study-tutor `main` (S1, S2, S0, the app-lane merge, this record) and the `ai-transition` plan-of-record update.
2. On push, exercise ruling 3's discretion: accept the no-re-pin addenda as-is, or re-pin `CONTRACT_SHA`/`BINDING_SHA` for the resume widening (the S-R2 "pin on push" pattern).
3. Tell the app lane the Stage-0/1/2 endpoints are live: History's `resume`-on-ended now works against the real backend (realigning the opt-in live contract suite), and the mirror can swap its poll to `turns?since=` with the SSE stream optional.
4. **Pre-existing, named (not this lane's):** the hermetic suite's one standing failure is `test_no_whitestocks_connection_in_tests` — the NAS scope guard trips on the string "whitestocks" in `tests/unit/http/test_auth_keycloak.py`, left by the earlier auth lane. Candidate for known-issues.md or a one-line fix in that lane's scope. Likewise the standalone-order fixture artifact in the durable-cross-device feature tests (above).
