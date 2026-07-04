# Flutter App — Phase 2 Scope: real transport slice

**Status:** Draft — for Rich's review; §6 lists the decisions only he can make. Adversarially verified (3 lenses, 19 findings applied) 2026-07-04.
**Date:** 2026-07-04. **Owner:** Rich.
**Contract pin:** unchanged — [API-session-cross-device.md](../../design/contracts/API-session-cross-device.md) at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`. Phase 2 *consumes* the contract on both sides of the seam; contract changes stay owned by `/design-refine` (contract §10). Handoff D1–D9 are closed and untouched.
**Predecessor:** [flutter-app-scope.md](flutter-app-scope.md) (v1 — fake-backend slice, shipped 2026-07-04, 80 tests).
**Residency:** [ADR-ARCH-015](../../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md) carries into the phase where it first has teeth: still **no telemetry/analytics/crash reporting**, and the app's `API_BASE_URL` only ever points at household/Tailscale infrastructure — no third-party endpoint appears in any flavour.
**Related:** [migration build plan §5a](student-model-postgres-migration-scope-and-build-plan.md) (FEAT-SMP-003), `src/study_tutor/session/service.py` (the scaffold this lands on), [mobile+voice handoff](../../handoffs/study-tutor-mobile-voice-conversation-starter.md) (covers sequencing steps **3–4**; see §6.5 for the deliberate step-1 deferral).

---

## 1. What phase 2 is

One sentence: **swap the fake for the real backend over HTTP, and prove they agree by running the same contract suite against both.**

Two coordinated builds, one on each side of the seam:

1. **Backend — FEAT-SMP-003** (not specced here): durable student-keyed sessions in the existing Postgres tables + the HTTP App Access adapter over `SessionService`. It has its own owner-process — guardkit `/feature-spec` → `/feature-plan` → autobuild per the migration plan — and this doc only states the *demand side* (§2). Ground truth as of `3cff683`: `session`/`session_turn` tables exist (W1 schema); the six PG session methods (`postgres.py:671–707`) raise `NotImplementedError`; `SessionService` is unwired scaffolding (its docstring lists 6 open decisions, one — the §9 error-set ratification — already resolved by G-CON, leaving the plan's 5 build decisions); **no web framework is a direct dependency** (starlette/uvicorn are present transitively via `mcp`, so SMP-003 could serve HTTP without a net-new framework — its call).
2. **App — the HTTP adapter slice** (this scope, §3): `HttpSessionApi` behind the *existing* `SessionApi` port, wire-error mapping onto the *existing* typed exceptions, a composition-root switch, and the contract suite runnable against both adapters.

v1's moat is the point of this phase: the contract tests were written against the port, so "fake and backend agree" becomes a test run, not an argument.

## 2. Demand side: what the app needs from FEAT-SMP-003

The SMP-003 spec owns its design; the app slice needs this surface to exist:

1. **HTTP JSON endpoints for the six verbs** (contract §5 names and shapes; plain request/response — **no WS/streaming in this phase**, contract §7 lands with voice).
2. **A ratified HTTP binding table** — verb → method + path + status-code-per-`error_type` (§9 envelope). The contract is deliberately transport-neutral, so this small table is where the wire is pinned; it belongs in the SMP-003 `/feature-spec`, and **app deliverable §3.1 is blocked on it** — otherwise the app invents routes that silently diverge.
3. **Interim auth = the fake IdP's model, server-side** (contract §3 derivation with a static table instead of Keycloak): the adapter resolves `student_id` from a **configured token→student table**. Prod config keeps the single-user posture (one entry, Lilymay). **Dev config carries two entries + reject-unknown-tokens on**, which is what lets the ownership (`SessionForbidden`) and auth (`Unauthenticated`) contract tests run live. This is config, not multi-student auth — no Keycloak, no provisioning (D9 untouched).
4. **A dev-only state reset** (e.g. `POST /__dev__/reset`, enabled by env flag, absent in prod config): truncates session/session_turn state so live contract tests are isolated. The live suite asserts absolute state (`hasLength(1)`, `isEmpty`); without per-test reset against the durable store it fails from the second test onward.
5. **Per-turn durability + ordered resume** (contract §4/§6) — what makes the cross-device demo real.
6. **Error envelope** (contract §9) — flat JSON with `error_type` from the closed set.

Two items that look demand-side but are **decisions for Rich, not the SMP-003 plan** (§6): the GB10 port + Tailscale ACL, and the `resume_if_active` duplicate-pick ambiguity (a *contract* question owned by `/design-refine`).

## 3. App-side deliverables

1. **`HttpSessionApi implements SessionApi`** — six verbs per the ratified binding table (§2.2), JSON ↔ existing domain models, `Authorization: Bearer <token>` from the `IdentityProvider` port. **One proposed dependency: `package:http`** (Dart-team, boring — §6.3). Nothing else: no dio, no codegen, no state-management change. **Timeouts are part of the adapter:** per-request deadline aligned to the contract budgets (~15s `turn` for the p95<10s budget, ~5s read verbs); a timeout maps to `TransportError`.
2. **Wire-error mapping + `TransportError`:** non-2xx → parse envelope → the existing typed exceptions. Network failure / timeout / malformed body → `TransportError`, a **client-local** member of the sealed hierarchy (documented as not part of the §9 wire set). It gets the fourth UI treatment in `error_handling.dart`: non-crashing "connection problem — try again" surface that **preserves the unsent input**, verified by a widget test using a throwing `SessionApi` stub. (v1 rule: every reachable error has a defined, tested UI behaviour.)
3. **Composition-root switch:** `--dart-define=API_BASE_URL=…` — empty (default) wires `FakeSessionApi` exactly as v1; set, `main.dart` wires `HttpSessionApi`. Identity stays `FakeIdentityProvider` in both flavours (port untouched); its constant token is entry #1 in the dev token table (§2.3) — recorded in the binding table so the backend doesn't learn it from app source. No settings UI.
4. **Contract suite over both adapters via a `ContractBackend` harness abstraction** (not just a client factory — the suite drives identity switching, token invalidation, a second client, and a deterministic clock): `fake` implementation = today's harness; `live` implementation = clients bound to the dev token table (principal-switch = different token; invalidate = garbage token), `reset()` = §2.4 endpoint, and **relative-ordering timing assertions** (no tick-clock exactness against server timestamps). One mechanism, no test tags: the live suite lives under `test_live/` (outside the default `flutter test` tree, so the hermetic gate can never accidentally hit a server) and requires `API_BASE_URL`; generous per-test timeouts (real `turn` calls at p95<10s each).
5. **Android dev networking:** the debug manifest already carries `INTERNET`; add the cleartext posture for the dev flavour (network-security-config scoped to the backend host, or https — follows §6.2's port/host decision) and document the emulator base-URL rule (`10.0.2.2` vs Tailscale hostname) in the build plan. Debug builds only — matches the apk-debug gate.
6. **Cross-device proof (attended, the phase-2 morning-gate):** scripted steps — emulator signed in as Lilymay → start + two turns → `curl` as the same student: `list_sessions` shows the session with `turn_count: 2`, `turn` adds a third exchange, `resume_session` returns all turns in order → on the emulator: navigate home → Resume → the transcript shows **all six messages including the curl-injected pair, in order** → End on the emulator → `curl session_status` shows `ended`, `resumable: false`. Pass = every step observed; no second emulator (curl suffices).

## 4. Sequencing & gates

- **Backend first, app overlapped:** §3.2–§3.5 can be built and hermetically tested before the server exists; §3.1 waits for the binding table (§2.2); the live run and §3.6 wait for FEAT-SMP-003 deployed.
- **App green gate unchanged:** `flutter analyze` clean + `flutter test` green (hermetic — `test_live/` excluded by location) + `flutter build apk --debug`; one commit per wave; blast radius `app/**` (+ this doc family).
- **Phase-2 done =** live contract suite green (all nine areas, using §2.3/§2.4) + §3.6 walk clean + the 80 existing hermetic tests untouched-green.

## 5. Explicitly OUT of phase 2

WS streaming `turn` / voice / STT-TTS (contract §7); Keycloak & real multi-student auth (D9 — the static token table is config, not an auth system); token refresh; offline queue / on-device persistence; `session_version` concurrent-resume UX (contract §11 OQ2) — the §3.6 proof observes remote turns via explicit re-resume, not live refresh; session TTL (§11 OQ4); iOS/web claims; Reachy; any MCP-surface change.

## 6. Decisions Rich owns (blocking, in rough order)

1. **FEAT-SMP-003 ownership** — GB10 autobuild vs this Mac session; nothing in-repo records an owner and the SMP status metadata is stale (trust `git log`).
2. **GB10 port + Tailscale ACL for the HTTP surface** — nothing reserved; 8080 (Open WebUI), 9000 (llama-swap), 9100/9200 (voice) are taken/earmarked. Also fixes http-vs-https for the dev flavour (§3.5).
3. **Approve `package:http`** — the single proposed addition to v1's closed dependency list.
4. **`resume_if_active` duplicate-pick** — a contract-level ambiguity (contract §5 wording is singular; duplicates are permitted). Owned by `/design-refine`, not the SMP-003 spec: either ratify "most-recently-active wins" (what the app's fake + a pinned contract test do today) or add a uniqueness rule. Logged in [app/QUESTIONS.md](../../../app/QUESTIONS.md).
5. **Sequencing deviation sign-off** — the handoff ordered voice endpoints first (step 1, rationale: also unblocks Reachy); this phase does steps 2–4 first and defers voice. Sequencing wasn't a D-numbered closed decision, but the reorder should be deliberate, not implicit.

---

*Next artifacts once §6.1–§6.4 are decided: (a) FEAT-SMP-003 `/feature-spec` (backend — owns the binding table §2.2 and its own plan), (b) `flutter-app-phase2-build-plan.md` (app waves, v1 discipline).*
