# Conversation starter — HTTP App Access adapter (GB10 build)

**Date:** 2026-07-04. **Owner:** Rich. **Build host:** GB10 (`promaxgb10-41b1`), per decision [phase-2 scope §6.1](../research/ideas/flutter-app-phase2-scope.md).
**Vehicle:** guardkit `/feature-spec` → `/feature-plan` → autobuild, same as FEAT-SMP-001/002/003.
**Contract pin:** [API-session-cross-device.md](../design/contracts/API-session-cross-device.md) at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`. Contract changes are owned by `/design-refine` only — this build MUST NOT edit contract docs.
**Demand side:** [flutter-app-phase2-scope.md](../research/ideas/flutter-app-phase2-scope.md) §2 — the Flutter client's needs; the app waves are being built **in parallel on the Mac** against this feature's binding table.
**Feature ID:** FEAT-APP-001 (new series — `FEAT-PH2-*` is already taken by the gamification/dashboard roadmap).
**Sequencing (decided 2026-07-05):** this feature builds **FIRST**, before FEAT-SMP-004 (Graphiti write-path teardown — [its handoff](study-tutor-w3-sessions-merged-smp004-teardown-conversation-starter.md)). Both features edit `cli/main.py` and `pyproject.toml`, so they must run sequentially — and the Mac-side app waves are blocked on this feature's binding table + a live `:8100`, while the teardown blocks nobody. Accepted consequence: the HTTP deployment image carries `graphiti-core[falkordb]` until SMP-004 lands. SMP-004's boot gate then extends to `serve-http` (recorded in that handoff).

---

## 1. What to build

The **HTTP transport FEAT-SMP-003 explicitly deferred** (its spec summary §Out-of-scope: "the HTTP/WS transport + `turn_stream`"): a thin HTTP adapter exposing the six contract §5 verbs over **port 8100** (decision §6.2 — 9100/9200 stay reserved for voice), as a *second consumer* of the already-wired `SessionService` (`src/study_tutor/session/service.py`, wired + proven over MCP since `ea7c135`).

Deliverables the spec must cover:

1. **Six JSON endpoints** mirroring contract §5 (`start_session`, `list_sessions`, `resume_session`, `turn`, `session_status`, `end_session`). Plain request/response — **no WS, no streaming**: `turn_stream` stays `NotImplementedError` (voice is phase 3, decision §6.4).
2. **The HTTP binding table** — verb → method + path + status-code-per-`error_type` (§9 flat envelope, errors from `session/errors.py` mapped 1:1), **plus a "dev endpoints" section recording the dev token values and the reset route** (so the Mac side codes against the doc, never guesses). Publish it as a doc (suggest `docs/design/contracts/API-session-http-binding.md`) **in the first task and treat it as frozen once pushed** — the Mac-side app build consumes it at a pinned SHA; silent changes strand the client.
3. **Interim auth = static token→student table** (contract §3 with config instead of Keycloak): prod config one entry (Lilymay); dev config two entries + reject-unknown-tokens, which is what lets the app's ownership (`SessionForbidden`) and auth (`Unauthenticated`) contract tests run live. Config, not an auth system — D9 (Keycloak later) untouched. **The dev values are fixed, not yours to invent** (they must equal the app's existing fake-IdP constants): `<bearer-lilymay>` → `lilymay`, `<bearer-alex>` → `alex` (`app/lib/fakes/fake_identity_provider.dart:16,19` — read-only reference; never edit `app/**`). Record both in the binding doc's dev section.
4. **Dev-only reset** (e.g. `POST /__dev__/reset`, env-flag-gated, absent from prod config): truncates **`session` + `session_turn` rows only — not learner-state tables** (XP/streak/confidence stay), so the app's live contract suite is test-isolated against the durable store. Record the actual route in the binding doc's dev section — **including the caveat that reset is global server state, so the live suite must run `--concurrency=1`** (surfaced by the Mac-side p2-wave-2 review, 2026-07-04).
5. **Serve entrypoint + deployment slot:** a `serve-http` CLI subcommand beside `serve`/`serve-nats`; **a new compose file under `deploy/http/`** (the existing root `docker-compose.study-tutor.yml` is outside this build's blast radius and hard-requires `NATS_PASSWORD` — ADR-ARCH-023's independent-deployability posture means the HTTP service must not inherit that coupling).
6. **Web stack decision inside the spec:** starlette/uvicorn are already transitive via `mcp`; fastapi would be net-new. Either way, pin whatever is served on as a **direct** dependency in pyproject.
7. **Student-row seed (REVIEW-REQUIRED assumption in the spec — the gap found in the 2026-07-05 alignment review):** `session.student_id` is `NOT NULL REFERENCES student(student_id)` ([schema_reference.sql:47](../../src/study_tutor/knowledge/store/schema_reference.sql)) and `create_session` ([postgres.py:672](../../src/study_tutor/knowledge/store/postgres.py)) plain-INSERTs with no auto-create — `start_session` for an unseeded student is an `IntegrityError`, not a contract error. The live suite runs as BOTH dev tokens, so the deployment DB needs `student` rows for `lilymay` AND `alex`; the only existing seed tool (`scripts/seed_student_model.py`) seeds the **graph**, not Postgres. This feature ships a minimal **idempotent Postgres seed for the token-table student rows** (identity rows only — baseline `topic_confidence` data stays with FEAT-SMP-004's ASSUM-010 disposition). Also decide + record in the binding doc what an authenticated-but-unseeded student gets from `start_session` (must map to a §9 envelope, not a 500).

## 2. Constraints and retro lessons (encode in the plan, don't soften)

- **Blast radius:** `src/**`, `deploy/**`, `docs/design/contracts/API-session-http-binding.md`, feature/task files. **Never `app/**`** (Mac-side, in-flight) and never the pinned contract.
- **MCP surface untouched** — agent-hosts keep their four tools exactly as-is (contract §10).
- From the "Coach-green but not mergeable" retro family (**in the guardkit repo**, latest pushed `99bf79d5` 2026-07-04 — call-site drift; siblings: undefined BDD step, self-defeating boundary tests; lessons restated here in full so this doc stands alone):
  - any signature change → **sweep all call sites** (the SMP-003 cutover changed `MCPAdapter.__init__` + its test but not the two `cli/main.py` call sites; serve crashed on boot);
  - injected-dependency unit tests are **not** production-wiring coverage — test the wired path;
  - the boot smoke must **assert READY** (bound port answering a health/first request), not "no crash within N seconds" (SIGTERM(-15) was accepted as success and masked the last one).
- `resume_if_active` semantics are already implemented (`ORDER BY last_activity DESC LIMIT 1`, `postgres.py:706`) and pinned by the app's contract test — the HTTP layer must not reorder them.

## 3. Definition of done

- Six endpoints live on GB10 `:8100` (dev config: two tokens + reset enabled; `student` rows for both tokens seeded in the deployment DB); READY boot smoke green; suite green; per-wave guardkit gates as usual.
- Tailscale ACL entry lets the Mac/emulator host reach `:8100`.
- **Integration proof is Mac-side and attended:** the live contract suite in **this repo's `app/test_live/`** (created by the Mac-side p2-wave — it may not exist yet when you finish; that's expected) runs green against this deployment, then the cross-device walk (scope §3.6). Coordinate with Rich before calling the feature complete — the app suite is the acceptance test.

## 4. Kickoff (drafted 2026-07-05 — same workflow as FEAT-SMP-001/002/003)

```
/feature-spec "HTTP App Access adapter (FEAT-APP-001) — six contract §5 verbs (start_session, list_sessions, resume_session, turn, session_status, end_session) as plain JSON endpoints on :8100, a SECOND consumer of the already-wired SessionService (MCP surface untouched, contract §10); no WS/streaming — turn_stream stays NotImplementedError (voice is phase 3). Publish the HTTP binding table as docs/design/contracts/API-session-http-binding.md in the FIRST task and freeze it once pushed (verb → method+path, status-code per error_type from session/errors.py mapped 1:1 onto the §9 flat envelope, PLUS a dev-endpoints section recording the fixed dev tokens <bearer-lilymay>→lilymay / <bearer-alex>→alex and the reset route — the Mac-side app codes against this doc at a pinned SHA). Interim auth = static token→student config table (prod: lilymay only; dev: both tokens + reject-unknown → Unauthenticated). Dev-only env-flag-gated POST /__dev__/reset truncating session + session_turn rows ONLY (learner-state tables untouched), absent from prod config. Minimal idempotent Postgres seed for the token-table student rows — session.student_id FKs student (schema_reference.sql:47), create_session (postgres.py:672) does NOT auto-create, so start_session for an unseeded student IntegrityErrors; identity rows only, baseline topic_confidence stays with FEAT-SMP-004; REVIEW-REQUIRED — also define the §9 error an authenticated-but-unseeded student gets (never a 500). serve-http CLI subcommand beside serve/serve-nats + a NEW compose under deploy/http/ (must not inherit the root compose's NATS_PASSWORD coupling). Web-stack decision inside the spec (starlette/uvicorn already transitive via mcp vs net-new fastapi) with whatever is served on pinned as a DIRECT dependency in pyproject. Boot smoke must assert READY — bound port answers a health/first request — not no-crash-within-N-seconds. resume_if_active semantics (ORDER BY last_activity DESC LIMIT 1, store/postgres.py:706) must not be reordered. Blast radius: src/**, deploy/**, the new binding doc, feature/task files — NEVER app/** (Mac-side, in-flight) and never the pinned contract (CONTRACT_SHA 22791af)." \
  --context docs/design/contracts/API-session-cross-device.md \
  --context docs/research/ideas/flutter-app-phase2-scope.md \
  --context docs/handoffs/study-tutor-http-adapter-conversation-starter.md \
  --context src/study_tutor/session/service.py \
  --context src/study_tutor/session/errors.py \
  --context src/study_tutor/knowledge/store/postgres.py \
  --context src/study_tutor/cli/main.py \
  --context pyproject.toml
```

Then `/feature-plan "HTTP App Access Adapter" --context features/<slug>/<slug>_summary.md --feature-id FEAT-APP-001 --no-questions`, serialize the waves, then `GUARDKIT_HARNESS=sdk guardkit autobuild feature FEAT-APP-001 --fresh`.

**Operational discipline — same as the SMP-004 handoff §5** (read `docs/retros/` + `guardkit/docs/retros/` first): serialize `orchestration.parallel_groups` to one-task-per-wave; export an **ephemeral** `STUDY_TUTOR_PG_DSN` (throwaway postgres:16 on a non-5434 port, `alembic upgrade head`; NEVER the NAS); independent verification on the merged `main` tree with `.env` present — full `pytest tests/` + the READY boot smoke for **both** `serve` and `serve-http`; selective squash-merge (code+test paths only); ignore the 3 pre-existing NATS-smoke failures.

*References: phase-2 scope (demand side + decisions), FEAT-SMP-003 spec summary (`features/durable-cross-device-sessions/`), `SessionService` docstring open-decisions (§#1 identity, resolved here by the token table), RUNBOOK-study-tutor-gb10-docker-deployment.md (compose context), app/QUESTIONS.md (contract-ambiguity log).*
