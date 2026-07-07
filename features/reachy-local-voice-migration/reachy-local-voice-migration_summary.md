# Feature Spec Summary: Reachy Local Voice Migration

**Feature ID**: FEAT-VOICE-004
**Stack**: python
**Generated**: 2026-07-07
**Scenarios**: 25 total (7 smoke, 0 regression)
**Assumptions**: 9 total (7 high / 2 medium / 0 low confidence)
**Review required**: No (all resolved/confirmed 2026-07-07; 2 medium items are gate-decided at R01/R-G6 with fallback policy pre-approved)

## Scope

Migrates the Reachy Mini's voice conversation off the HF-hosted Realtime cloud onto a
local speech-to-speech unit on the GB10, closing the standing D3 exception where a
minor's voice transited a third-party cloud. Tutoring turns go **direct to the
study-tutor** via a new `ask_tutor` HTTP tool (no Jarvis in the loop), giving the robot
identical session semantics to the phone so a phone-started session can be resumed on
the robot (D8 pickup). Also ports `query_student_model` off the frozen knowledge graph
onto the durable Postgres-backed read (recon D2), fixes the rejected tool-interface
shape (D1), and covers the deployment and profile-reconcile mechanics (D4, D7) and the
Pi app-version gate (D3).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 3 |
| Negative cases (@negative) | 7 |
| Edge cases (@edge-case) | 14 |
| Smoke (@smoke) | 7 |

_(Tags overlap — several scenarios carry both @edge-case and @negative.)_

## Deferred Items

None — all four proposal groups and all five expansion scenarios were accepted.

## Resolved

- **ASSUM-001** — the shared subject constant. **RESOLVED 2026-07-07: `english`.**
  Investigation found `english` correct everywhere (Scholar persona = AQA English Lang/Lit,
  `query_student_model` default, the fine-tune, the student model, fleet-gateway probe/tests);
  the app's `maths` was a stale v1 placeholder with no content behind it. Fix applied: app
  `defaultSubject` `'maths'`→`'english'`; fleet-gateway unchanged. Treated as a **default**,
  not a hard pin — `ask_tutor` exposes `subject` as a parameter, so multi-subject is
  supported without rework once the app gains a subject picker.

## Open Assumptions

None. ASSUM-007 (tutor-unavailable copy) and ASSUM-008 (slow-turn filler) were drafted in
Scholar's voice and recorded in TASK-VOX-R07 (tool offline string) and TASK-VOX-R08 (persona
copy) on 2026-07-07. ASSUM-003 (0.6B/1.7B checkpoint) and ASSUM-004 (two-robot topology) are
medium-confidence and decided empirically at R01 / R-G6, with the 1.7B fallback pre-approved.

## Recon deltas covered by this spec

| Delta | Where it lands |
|-------|----------------|
| D1 (rejected tool-interface shape) | Negative: "A tool that does not conform … is not offered" |
| D2 (Postgres-backed student read) | Key: "The student-model lookup reads from the durable student store" |
| D3 (Pi app-version re-point support) | Edge: "Migration is blocked when the robot's installed app cannot honour the re-point" |
| D4 (profile drift reconcile to Pi) | Edge: "The reconciled robot profile keeps the working tool set" |
| D6 (subject-pin tension) | ASSUM-001 + Boundary/Negative subject-match scenarios |
| D7 (clean re-clone, not git pull) | Edge: "Shipping the new tutor tool … preserves the robot's local configuration" |
| R-G3 (tool round-trip) | Key: "A student-model tool call round-trips through the local voice session" |
| R-G5 (residency) | Boundary: "Tutoring-turn responsiveness depends on the tutor model's residency" |
| R-G6 (two robots) | Edge: "Two robots hold tutoring conversations at the same time" |

## Integration with /feature-plan

    /feature-plan "Reachy Local Voice Migration" \
      --context features/reachy-local-voice-migration/reachy-local-voice-migration_summary.md

Per build-plan §0a, the FEAT-VOICE-004 spec/plan run in the Fable window; builds (R1–R4)
are Operator + Opus. This feature is independent of FEAT-VOICE-001–003 and of G-RAT/G-CON.
