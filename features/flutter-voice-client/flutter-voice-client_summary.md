# Feature Spec Summary: Flutter tap-to-talk voice client (FEAT-VOICE-003)

**Stack**: dart (Flutter client under `app/`; the root repo auto-detects as python)
**Generated**: 2026-07-07T08:04:13+01:00
**Scenarios**: 22 total (4 smoke, 2 regression)
**Assumptions**: 11 total (8 high / 1 medium / 2 low confidence)
**Review required**: Yes (3 soft assumptions — copy strings + the Phase-0-gated recorder encoder)

## Scope

The observable behaviour of the study-tutor Flutter app's tap-to-talk voice feature:
recording a spoken question (with a client-side 60 s hard stop and 10 MB backstop),
transcript-first display, ordered playback of the answer's spoken parts, incremental
text render on the streaming (live-channel) path, the amber `VoiceUnavailable`
degradation experience, microphone-permission and connection-problem handling, and the
"green-but-broken" direction-pin fidelity of the outgoing recording. It also captures the
deliberate scope events this feature introduces — three new runtime dependencies and the
Android/iOS manifest permission additions.

This spec covers **only the client**. It deliberately does **not** duplicate FEAT-VOICE-001
(`voice-server-module` — server upload-validation rulebook and boundary pairs) or
FEAT-VOICE-002 (`streaming-voice` — server streaming path, WS frame ordering, chunk-by-URL
delivery, cross-student chunk-fetch security). Where the client surfaces a server decision
(e.g. an unsupported-format refusal), the scenario asserts the **client's surfacing and
recoverability**, not the server's rulebook.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 3 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 9 |
| Smoke (@smoke) | 4 |
| Regression (@regression) | 2 |

(Scenario total is 22; category rows overlap because some scenarios carry more than one tag,
e.g. `@edge-case @negative` and `@negative @smoke`. The `@negative` Scenario Outline expands
to 5 examples at run time.)

## Deferred Items

None — all four proposal groups and all four edge-case-expansion scenarios were accepted.

## Open Assumptions (low / medium confidence)

- **ASSUM-006 (medium)** — recorder encoder m4a/AAC-default, opus-fallback is **Phase-0-gated**
  on the m4a-against-live-STT test. The fidelity guarantee (format preserved exactly as
  captured) holds regardless of which encoder wins; only the captured format is unsettled.
- **ASSUM-010 (low)** — exact microphone-permission-denied copy is inferred, not design-specified.
- **ASSUM-011 (low)** — the plain-terms refusal-reason wording is inferred; the underlying
  error types are contract-firm, the user-facing copy is not.

Verify all three before the spec is treated as final copy.

## Testing note (for /feature-plan)

Per design §6.4, these scenarios are intended to run in **both** backends via the app's
dual-backend harness: hermetic (`FakeVoiceApi`/`FlakyVoiceApi` + MockClient direction pins)
and live (`app/test_live/` voice variants, `--concurrency=1`, quiet GPU). The direction-pin
scenario ("delivered to the tutor exactly as recorded") is the hermetic "green-but-broken"
defence ported from the LPA to the Dart seam. `@task:` tags are intentionally **absent** —
they are added by `/feature-plan` Step 11 once FEAT-VOICE-003 tasks exist.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Flutter tap-to-talk voice client" \
      --context features/flutter-voice-client/flutter-voice-client_summary.md
