# test_live — the contract suite against the real adapter

> **⚠ DESTRUCTIVE + POLLUTING on a shared store (2026-08-03 finding).**
> This suite signs in as the REAL primary student (`token-lilymay`) and its
> `reset()` calls `POST /__dev__/reset`, which **truncates the ENTIRE
> session+turn store for all students** (learner-state XP/streak/confidence
> survive). It also leaves stray test sessions behind (the shared bodies
> start `subject: 'maths'` sessions) that then surface on the app's Home as
> real-looking cards. Until the dedicated-suite-student + per-student-reset
> exit lands (known-issues, Test-suite artifacts), treat every run as an
> operator-attended act that DELETES session history — never run it against
> a store anyone cares about without saying so first.

The same 35 test bodies as `test/contract/` (imported from there, not
copied), run through `LiveContractBackend` against a deployed GB10 HTTP
adapter. This directory is **outside the default `flutter test` tree** — the
hermetic gate never runs it, and its code lands green without a server.

## Requirements

- The GB10 adapter deployed in **dev config** on `:8100` (binding doc at
  BINDING_SHA `53f2fc5` — the S-R2 Revision-2 ratification commit, superseding
  the phase-2 pin `6eb7b88`): dev token table
  (`token-lilymay` / `token-alex`) and the `POST /__dev__/reset` route
  enabled. **Never point this suite at a prod config** — every test starts
  by truncating session state.
- Network path from this machine to the adapter (Tailscale).

## Run command

```bash
cd app
flutter test test_live --concurrency=1 \
  --dart-define=API_BASE_URL=http://<gb10-host>:8100
```

`--concurrency=1` is **required**, not advisory: `reset()` truncates GLOBAL
server state (binding §5.2), so the default parallel suite files would
clobber each other's fixtures mid-test.

Budget real time: ~35 tests, many making real `turn` calls. Measured on the
dev deployment (2026-07-05, post Coach fix): first turn in a session
~12-22s, turns with history ~36-48s — still above the contract's p95 < 10s
budget and 30s ceiling (SR-07), an open QUESTIONS.md item. The live adapter
therefore runs `turn` with a 90s harness deadline and every suite file
carries a 10-minute per-test timeout. Warm the tutor set first (one curl
turn) so the first test doesn't eat the model cold-load. `reset()` fails
fast (10s) with a pointed message when the host is unreachable (Tailscale
ACL / route) rather than hanging setUp.

## What differs from the hermetic run

Only the backend implementation (`live_contract_backend.dart`):

- clients bound to the dev token table; principal switch = the other token;
  invalidate = a garbage token actually sent on the wire
- `reset()` = the binding doc's dev reset route (per-test isolation)
- tutor replies: non-empty string (the exact canned-string pins are the
  fake's — an LLM is not canned)
- clock expectation: at-or-after (relative ordering; no tick-clock exactness)

If a live run fails, triage per the build plan §pre-registered success bar:
app-bug vs adapter-bug vs binding-doc gap — the binding doc is the arbiter,
and contract disagreements go to `/design-refine`, never patched locally.
