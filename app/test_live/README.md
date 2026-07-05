# test_live — the contract suite against the real adapter

The same 35 test bodies as `test/contract/` (imported from there, not
copied), run through `LiveContractBackend` against a deployed GB10 HTTP
adapter. This directory is **outside the default `flutter test` tree** — the
hermetic gate never runs it, and its code lands green without a server.

## Requirements

- The GB10 adapter deployed in **dev config** on `:8100` (binding doc at the
  BINDING_SHA pinned in the phase-2 build plan header): dev token table
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

Budget real time: ~35 tests, many making real `turn` calls. The contract
budgets `turn` at p95 < 10s (30s hard ceiling, SR-07), but the first dev
deployment measures ~43s warm / ~66s cold (logged in `../QUESTIONS.md` as an
adapter-side conformance gap) — so the live adapter runs `turn` with a 120s
harness deadline and every suite file carries a 10-minute per-test timeout.
Expect a full run to take tens of minutes until the latency gap is closed.
Warm the model first (one curl turn) or the first test eats the cold-load.
`reset()` fails fast (10s) with a pointed message when the host is
unreachable (Tailscale ACL / route) rather than hanging setUp.

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
