# Conversation starter — HTTP App Access adapter (GB10 build)

**Date:** 2026-07-04. **Owner:** Rich. **Build host:** GB10 (`promaxgb10-41b1`), per decision [phase-2 scope §6.1](../research/ideas/flutter-app-phase2-scope.md).
**Vehicle:** guardkit `/feature-spec` → `/feature-plan` → autobuild, same as FEAT-SMP-001/002/003.
**Contract pin:** [API-session-cross-device.md](../design/contracts/API-session-cross-device.md) at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`. Contract changes are owned by `/design-refine` only — this build MUST NOT edit contract docs.
**Demand side:** [flutter-app-phase2-scope.md](../research/ideas/flutter-app-phase2-scope.md) §2 — the Flutter client's needs; the app waves are being built **in parallel on the Mac** against this feature's binding table.

---

## 1. What to build

The **HTTP transport FEAT-SMP-003 explicitly deferred** (its spec summary §Out-of-scope: "the HTTP/WS transport + `turn_stream`"): a thin HTTP adapter exposing the six contract §5 verbs over **port 8100** (decision §6.2 — 9100/9200 stay reserved for voice), as a *second consumer* of the already-wired `SessionService` (`src/study_tutor/session/service.py`, wired + proven over MCP since `ea7c135`).

Deliverables the spec must cover:

1. **Six JSON endpoints** mirroring contract §5 (`start_session`, `list_sessions`, `resume_session`, `turn`, `session_status`, `end_session`). Plain request/response — **no WS, no streaming**: `turn_stream` stays `NotImplementedError` (voice is phase 3, decision §6.4).
2. **The HTTP binding table** — verb → method + path + status-code-per-`error_type` (§9 flat envelope, errors from `session/errors.py` mapped 1:1), **plus a "dev endpoints" section recording the dev token values and the reset route** (so the Mac side codes against the doc, never guesses). Publish it as a doc (suggest `docs/design/contracts/API-session-http-binding.md`) **in the first task and treat it as frozen once pushed** — the Mac-side app build consumes it at a pinned SHA; silent changes strand the client.
3. **Interim auth = static token→student table** (contract §3 with config instead of Keycloak): prod config one entry (Lilymay); dev config two entries + reject-unknown-tokens, which is what lets the app's ownership (`SessionForbidden`) and auth (`Unauthenticated`) contract tests run live. Config, not an auth system — D9 (Keycloak later) untouched. **The dev values are fixed, not yours to invent** (they must equal the app's existing fake-IdP constants): `token-lilymay` → `lilymay`, `token-alex` → `alex` (`app/lib/fakes/fake_identity_provider.dart:16,19` — read-only reference; never edit `app/**`). Record both in the binding doc's dev section.
4. **Dev-only reset** (e.g. `POST /__dev__/reset`, env-flag-gated, absent from prod config): truncates **`session` + `session_turn` rows only — not learner-state tables** (XP/streak/confidence stay), so the app's live contract suite is test-isolated against the durable store. Record the actual route in the binding doc's dev section.
5. **Serve entrypoint + deployment slot:** a `serve-http` CLI subcommand beside `serve`/`serve-nats`; **a new compose file under `deploy/http/`** (the existing root `docker-compose.study-tutor.yml` is outside this build's blast radius and hard-requires `NATS_PASSWORD` — ADR-ARCH-023's independent-deployability posture means the HTTP service must not inherit that coupling).
6. **Web stack decision inside the spec:** starlette/uvicorn are already transitive via `mcp`; fastapi would be net-new. Either way, pin whatever is served on as a **direct** dependency in pyproject.

## 2. Constraints and retro lessons (encode in the plan, don't soften)

- **Blast radius:** `src/**`, `deploy/**`, `docs/design/contracts/API-session-http-binding.md`, feature/task files. **Never `app/**`** (Mac-side, in-flight) and never the pinned contract.
- **MCP surface untouched** — agent-hosts keep their four tools exactly as-is (contract §10).
- From the "Coach-green but not mergeable" retro family (**in the guardkit repo**, latest pushed `99bf79d5` 2026-07-04 — call-site drift; siblings: undefined BDD step, self-defeating boundary tests; lessons restated here in full so this doc stands alone):
  - any signature change → **sweep all call sites** (the SMP-003 cutover changed `MCPAdapter.__init__` + its test but not the two `cli/main.py` call sites; serve crashed on boot);
  - injected-dependency unit tests are **not** production-wiring coverage — test the wired path;
  - the boot smoke must **assert READY** (bound port answering a health/first request), not "no crash within N seconds" (SIGTERM(-15) was accepted as success and masked the last one).
- `resume_if_active` semantics are already implemented (`ORDER BY last_activity DESC LIMIT 1`, `postgres.py:706`) and pinned by the app's contract test — the HTTP layer must not reorder them.

## 3. Definition of done

- Six endpoints live on GB10 `:8100` (dev config: two tokens + reset enabled); READY boot smoke green; suite green; per-wave guardkit gates as usual.
- Tailscale ACL entry lets the Mac/emulator host reach `:8100`.
- **Integration proof is Mac-side and attended:** the live contract suite in **this repo's `app/test_live/`** (created by the Mac-side p2-wave — it may not exist yet when you finish; that's expected) runs green against this deployment, then the cross-device walk (scope §3.6). Coordinate with Rich before calling the feature complete — the app suite is the acceptance test.

*References: phase-2 scope (demand side + decisions), FEAT-SMP-003 spec summary (`features/durable-cross-device-sessions/`), `SessionService` docstring open-decisions (§#1 identity, resolved here by the token table), RUNBOOK-study-tutor-gb10-docker-deployment.md (compose context), app/QUESTIONS.md (contract-ambiguity log).*
