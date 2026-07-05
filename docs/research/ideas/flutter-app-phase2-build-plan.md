# Flutter App — Phase 2 Build Plan (real transport slice)

**Status: ✅ COMPLETE — all 7 waves green, pre-registered success bar met (2026-07-05).** Waves 1–6 built 2026-07-04/05 (one gate-green commit each, adversarially reviewed pre-commit; ledger in `app/PROGRESS.md`); wave 7 closed 2026-07-05: live contract suite **35/35** against the deployed GB10 adapter (twice — sync- and async-Coach builds; same 35 assertions as the hermetic fake run, 125/125) and the **§3.6 cross-device walk clean, every checkpoint observed** (emulator ↔ curl). Full acceptance record: [RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md](../../runbooks/RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md). Three backend bugs found and fixed via the suite along the way (`timestamp`→`ts`, row-counted `turn_count`, Coach latency chain) — the binding doc held as arbiter throughout; the app never adapted to off-contract wire behaviour. Follow-ons live elsewhere: streaming = TASK-STREAM-001 (voice phase, ADR-ARCH-026 phase 2); open app-side observations in `app/QUESTIONS.md`.
*(Plan was: Ready — decisions §6.1–§6.4 all made ([scope](flutter-app-phase2-scope.md) §6, 2026-07-04); adversarially verified, 2 lenses, 14 findings applied.)*
**Date:** 2026-07-04 (authored) → 2026-07-05 (completed). **Owner:** Rich.
**CONTRACT_SHA:** `22791afbcdb3b71abbe6bd2f1b8e18218988942f` (unchanged from v1).
**BINDING_SHA:** `6eb7b88c4c8ae412fb36327a4f56286c6b539a7a` *(pinned by p2-wave-3, 2026-07-05)* — `docs/design/contracts/API-session-http-binding.md`, produced by the GB10 adapter build ([kickoff](../../handoffs/study-tutor-http-adapter-conversation-starter.md) §1.2). It carries the six-verb wire table **and the dev section: token values + reset route** — verified on pin: dev tokens equal the app's fake-IdP constants (`token-lilymay`/`token-alex`), reset `POST /__dev__/reset` (global → live suite at `--concurrency=1`), `GET /healthz`, port 8100, CONTRACT_SHA matches. If the published doc ever differs from the app's constants, that is a **binding-doc bug — raise it, never adapt the app silently**.
**Scope:** [flutter-app-phase2-scope.md](flutter-app-phase2-scope.md) §3 — this plan only sequences it.
**Gate (unchanged from v1):** `cd app && flutter analyze` clean + `flutter test` green (hermetic — `test_live/` excluded by location, and no hermetic test may ever open a socket) + `flutter build apk --debug`; one commit per wave (`p2-wave-N: <name> [green]`); tick + log in `app/PROGRESS.md` inside the wave commit.
**Blast radius:** `app/**` + `docs/research/ideas/flutter-*` for waves 1–6. **Wave 7 is attended** and additionally writes its RESULTS file to `docs/runbooks/` (the v1 precedent: RESULTS files are attended-review artifacts, not wave artifacts).

---

## Waves (~1–2 h each)

### p2-wave-1: TransportError + fourth UI treatment
`domain/errors.dart` gains `TransportError` — a **client-local** member of the sealed hierarchy, documented as outside the §9 wire set (update the "closed set" doc comments in `errors.dart` and `error_handling.dart`). Fourth treatment: non-crashing "connection problem — try again" surface that preserves unsent input; guards added at every port call site alongside the existing handlers. Widget tests induce it with a throwing `SessionApi` stub (no network, hermetic).
**Done when:** treatment tested from session send, session end, home refresh/start/resume paths; green gate. *Needs: nothing.*

### p2-wave-2: ContractBackend harness refactor
Extract `test/contract/` onto a `ContractBackend` abstraction — creates clients bound to a principal, principal-switch, token-invalidate, `secondClient()`, clock expectations, `reset()` — with the **fake implementation** reproducing today's harness exactly. Timing assertions move to relative ordering (no tick-clock exactness). The abstraction is for the contract suite only — do not migrate unit/ui/errors/slice tests onto it.
**Done when:** all contract tests (currently 35) run through `ContractBackend` unmodified in substance, and the full suite (currently 80) is green; green gate. *Needs: nothing.*

### p2-wave-3: HttpSessionApi — six verbs + JSON mapping (BLOCKED on BINDING)
Add `package:http` (the one approved dep — scope §6.3). `HttpSessionApi implements SessionApi`: six verbs per the binding table, JSON ↔ existing domain models, bearer token from the identity port. Happy-path unit tests against canned JSON fixtures **derived from the binding table**. Update this plan's `BINDING_SHA` header line as part of the wave commit (doc edit, inside blast radius).
**Done when:** all six verbs round-trip their fixtures; BINDING_SHA pinned in header + commit message; green gate. *Needs: p2-wave-1 (TransportError exists for the transport-failure path even if wiring lands next wave); binding doc on origin.*

### p2-wave-4: wire errors + timeouts
Non-2xx → parse §9 envelope → the existing typed exceptions, per the binding table's status-code column; network failure / timeout / malformed body → `TransportError`. Per-request deadlines aligned to contract budgets (~15s `turn`, ~5s reads). Unit tests: full §9 set, malformed body, timeout → `TransportError`.
**Done when:** every `error_type` in the binding table maps to its typed exception in a test; green gate. *Needs: p2-wave-1, p2-wave-3.*

### p2-wave-5: composition switch + Android dev networking
`--dart-define=API_BASE_URL=…`: empty → `FakeSessionApi` (v1 behaviour, hermetic gate untouched); set → `HttpSessionApi`. Identity stays `FakeIdentityProvider` in both flavours (its constants are the binding doc's dev tokens — see header). Android: debug-flavour cleartext posture scoped to the backend host (`network-security-config`), emulator base-URL rule documented in-repo (`10.0.2.2` vs Tailscale hostname → GB10 `:8100`). Widget test: define unset wires the fake (composition assertion).
**Done when:** both flavours build; hermetic suite green; green gate. *Needs: p2-wave-3, p2-wave-4.*

### p2-wave-6: live ContractBackend (`test_live/`)
Live implementation of the harness abstraction: clients per dev-table token (principal-switch = other token; invalidate = garbage token), `reset()` → **the reset route published in the binding doc** (never hard-code a guess), generous per-test timeouts (real `turn` p95 < 10s). Lives under `app/test_live/` — outside the default `flutter test` tree, requires `API_BASE_URL`. Code lands green without a server (the gate never runs it); a `README` in `test_live/` gives the run command.
**Done when:** compiles + hermetic gate green; run command documented. *Needs: p2-wave-2, p2-wave-4.*

### p2-wave-7: attended integration — live suite + cross-device proof
Against the deployed GB10 adapter (`:8100`, dev config): run `test_live/` (all nine contract areas, dev tokens + reset — budget real time: ~35 tests with real `turn` calls); then the scripted cross-device walk (scope §3.6: emulator start + 2 turns → curl as same student lists/advances/resumes → emulator re-resume shows all six messages in order → end → curl sees `ended`/`resumable: false`). Record a RESULTS entry in `docs/runbooks/` (attended exception — see Blast radius).
**Done when:** live suite green + walk clean; RESULTS filed. *Needs: p2-wave-5, p2-wave-6, GB10 adapter deployed + Tailscale ACL.*

## Dependency map

A wave may start only when every wave in its "needs" column is committed green:

| wave | needs | blocked by external? |
|---|---|---|
| P2-W1 | — | no |
| P2-W2 | — | no |
| P2-W3 | W1 | **yes: binding doc on origin** |
| P2-W4 | W1, W3 | no |
| P2-W5 | W3, W4 | no |
| P2-W6 | W2, W4 | no |
| P2-W7 | W5, W6 | **yes: adapter deployed on GB10 :8100 + ACL** |

W1 and W2 are startable immediately, in either order. If the binding doc hasn't landed when both are green, stop cleanly — do not invent routes, tokens, or status codes (the scope's silent-divergence warning).

## Pre-registered success bar

Phase-2 done = scope §4: live contract suite green against the real adapter **and** the fake (same assertions) + §3.6 walk clean + the full hermetic suite green with the pre-phase tests unmodified in substance (W2's harness refactor is the sanctioned exception). Any live-run failure is triaged as app-bug vs adapter-bug vs binding-doc gap — the binding doc is the arbiter, and disagreements with the *contract* go to `/design-refine`, never patched locally.

**MET 2026-07-05:** hermetic 125/125 (pre-phase tests unmodified in substance) + live 35/35 (`test_live`, `--concurrency=1`, dev tokens + reset) + §3.6 walk clean (all six messages cross-device in order; ended/`resumable: false`). Five live-suite attempts were needed end-to-end; every failure along the way triaged per this rule to the adapter/deployment side and fixed there — see the attempts ledger in the [RESULTS file](../../runbooks/RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md).
