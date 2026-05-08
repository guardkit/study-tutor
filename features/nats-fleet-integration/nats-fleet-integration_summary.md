# Feature Spec Summary: study-tutor NATS Fleet Integration

**Stack**: python
**Generated**: 2026-05-08
**Scenarios**: 31 total (7 smoke, 7 regression) — duplicate-delivery scenario deferred 2026-05-08
**Assumptions**: 7 total (5 high / 1 medium / 1 deferred)
**Review required**: No (ASSUM-007 resolved via deferral; see decision log)

## Scope

This specification defines the behaviour of the study-tutor agent as a participant in the NATS fleet — boot lifecycle, command round-trip semantics, regression guards for the four documented bugs from the 2026-05-08 jarvis runbook (PubAck race, on_command mapping, OPENAI_BASE_URL /v1, wire-tap pattern), and operational realities (split-brain, concurrent same-session turns, oversized results, missing infra). Covers all three implementation phases: Phase 1 (minimum viable adapter + live registration + heartbeat, demo-critical 2026-05-11), Phase 2 (readiness gating + KV-watch hardening), Phase 3 (Docker/GB10 deployment).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 5 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 5 |
| Edge cases (@edge-case) | 16 |
| Smoke (@smoke, subset) | 7 |
| Regression (@regression, subset) | 7 |

## Phase distribution (via @phase-N tags)

| Phase | Scenarios | Notes |
|---|---|---|
| Phase 1 | ~22 | Demo-critical, deadline 2026-05-11. Includes lifecycle + 4 round-trips + 3 bug regression guards + concurrency + reconnect |
| Phase 2 | ~5 | Readiness gating, idempotency, split-brain, runbook documentation of stale-registry symptom |
| Phase 3 | ~7 | Docker/GB10 deployment, oversized result, LLM unreachable, missing KV bucket, wire-tap regression |

(Some scenarios carry multiple @phase tags where they apply across phases.)

## Bug regression guards (one scenario per bug)

| Tag | Bug from runbook | Scenario |
|---|---|---|
| @bug-1 @regression | PubAck race on JetStream COMMAND subject | "A reply to a request-style dispatch lands on the caller's inbox, not only on the result topic" |
| @bug-2 @regression | command_router.on_command does not consult tool_to_command | "A tool-name dispatch resolves to the canonical command through the tool_to_command map" (Outline × 4) |
| @bug-3 @regression | OPENAI_BASE_URL missing /v1 suffix | "A misconfigured LLM base URL surfaces a clear configuration error during a tutor turn" |
| @bug-4 @regression | Wire-tap pattern agents.command.<id>.> returns 0 envelopes | "A wire-tap on the documented command subject pattern captures a real dispatch" |
| @bug-5 @regression | InMemoryManifestRegistry rejects intents=[] | "A manifest with zero intent capabilities is rejected at registration" + just-inside boundary scenario |

## Cross-references

- **Canonical input**: `docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md`
- **Source bug catalogue**: `jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md` (lines 60-138)
- **Architecture decision**: `docs/talks/openwebui-nats-pipe-architecture.md`
- **Superseded scope doc**: `features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md` (kept for cross-reference; do not duplicate when generating the build plan)
- **Reference implementation**: `specialist-agent/src/specialist_agent/adapters/nats_adapter.py` (NATSAdapter), `command_router.py` (CommandRouter), `manifest.py` (factory)

## Decisions encoded (2026-05-08)

These three project decisions are baked into the spec:

1. **Phase 1 includes live registration + heartbeat.** The "live discovery" scenario in Group A asserts jarvis discovers the tutor without any stub-yaml fallback. No @stub-yaml scenarios exist.
2. **Session durability uses hybrid Graphiti, not JetStream KV.** The "container restart loses sessions" scenario is tagged @known-limitation @phase-3 and explicitly references "pre-FU-001 limitation" — fixed by the Graphiti durability follow-up, not by KV.
3. **Stale-agent reaper deferred to jarvis post-demo.** The "killed tutor leaves stale registry entry" scenario asserts the runbook documents manual cleanup; no automatic reaper behaviour is specified for study-tutor.

## Deferred Items

None — all four primary groups and all four edge-case categories were accepted in curation.

## Open Assumptions (low confidence)

None. ASSUM-007 was resolved on 2026-05-08 via deferral (Option C): tutor behaviour under duplicate delivery is undefined; jarvis MUST NOT duplicate-dispatch. The duplicate-delivery scenario was removed from the spec. If duplicate delivery is ever observed in a real runbook, revisit via TASK-NATS-FU-005.

## Integration with /feature-plan

This summary should be passed to `/feature-plan` as a context file:

    /feature-plan "study-tutor NATS Fleet Integration" \
        --context features/nats-fleet-integration/nats-fleet-integration_summary.md \
        --context docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md

`/feature-plan` Step 11 (BDD link) will associate `@task:<TASK-ID>` tags with these scenarios automatically based on the recommended task breakdown in the review document. Pre-tagging by hand is unnecessary.
