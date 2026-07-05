# Feature Spec Summary: HTTP App Access Adapter (FEAT-APP-001)

**Stack**: python
**Generated**: 2026-07-05T07:02:01Z
**Scenarios**: 34 total (5 smoke, 4 regression; two are 4–6-row outlines)
**Assumptions**: 11 total (2 high / 5 medium / 4 low confidence)
**Review required**: Yes — 4 low-confidence assumptions, all operator-confirmed at defaults; ASSUM-001 (unseeded-student → `Unauthenticated`) is the one the Coach must verify against the binding doc

## Scope

The six contract §5 verbs (`start_session`, `list_sessions`, `resume_session`, `turn`,
`session_status`, `end_session`) exposed as plain JSON endpoints on port 8100, as a
second consumer of the proven `SessionService` — the MCP surface stays byte-for-byte
untouched (contract §10). The build publishes the HTTP binding table
(`docs/design/contracts/API-session-http-binding.md`) **in its first task** and freezes
it once pushed: the Mac-side Flutter build consumes it at a pinned SHA, and its dev
section records the fixed dev tokens (`token-lilymay`→`lilymay`, `token-alex`→`alex`),
the reset route, and the reset-is-global caveat (live suite runs `--concurrency=1`).
Interim auth is a static token→student config table (prod: Lilymay only; dev: two
tokens + reject-unknown). A dev-only, env-flag-gated reset truncates `session` +
`session_turn` rows only. An idempotent student-identity seed closes the FK gap found
in the 2026-07-05 alignment review (`session.student_id` references `student`;
`create_session` does not auto-create). Deployment lands as a `serve-http` CLI
subcommand plus a new compose under `deploy/http/` (no `NATS_PASSWORD` coupling), with
a boot smoke that asserts READY (bound port answering), not no-crash-within-N-seconds.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 7 |
| Negative cases (@negative) | 9 |
| Edge cases (@edge-case) | 11 |

(One scenario is double-tagged `@negative @edge-case`; counts are per-tag.)

## Constraints the plan must not soften

- **Blast radius:** `src/**`, `deploy/**`, the new binding doc, feature/task files —
  NEVER `app/**` (Mac-side, in-flight) and never the pinned contract
  (`CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`).
- **Sequencing:** builds BEFORE FEAT-SMP-004 (both edit `cli/main.py` + `pyproject.toml`).
- **`resume_if_active` pick order** (`ORDER BY last_activity DESC LIMIT 1`,
  `store/postgres.py:706`) is pinned by the app's contract test — must not be reordered.
- Retro lessons (call-site drift `99bf79d5` family): signature change → sweep ALL call
  sites; injected-dependency unit tests are not production-wiring coverage; boot smoke
  asserts READY.
- The concurrency scenario ("Simultaneous resume-if-active starts converge") is
  hermetic-tier only — too racy for the Mac's live suite.

## Deferred Items

None — all four groups accepted; 6 expansion scenarios (security/concurrency/
integrity) accepted in full.

## Open Assumptions (low confidence)

- ASSUM-001 — unseeded-student requests refused as `Unauthenticated` (the
  REVIEW-REQUIRED item from the handoff; keeps the §9 closed set intact)
- ASSUM-004 — health route `GET /healthz`
- ASSUM-007 — config via `STUDY_TUTOR_HTTP_TOKENS` / `STUDY_TUTOR_HTTP_DEV_RESET` env vars
- ASSUM-008 — seed as a `study-tutor seed-students` CLI subcommand

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "HTTP App Access Adapter" \
      --context features/http-app-access-adapter/http-app-access-adapter_summary.md \
      --feature-id FEAT-APP-001 --no-questions
