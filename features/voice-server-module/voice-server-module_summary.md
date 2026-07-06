# Feature Spec Summary: Voice turn — spoken questions answered with spoken replies (FEAT-VOICE-001)

**Stack**: python (Starlette HTTP adapter)
**Generated**: 2026-07-06
**Scenarios**: 27 total (3 smoke, 2 regression)
**Assumptions**: 6 total (3 high / 2 medium / 1 low confidence — all human-confirmed)
**Review required**: No (ASSUM-005, the only low-confidence item, was owner-confirmed 2026-07-06)

## Scope

The server voice module for the study-tutor HTTP adapter: a non-streaming
`voice_turn` (multipart upload → STT → the identical turn pipeline → TTS →
chunk-by-URL reply audio) plus `voice_audio` fetch, mounted behind
`STUDY_TUTOR_VOICE_ENABLED`, speaking the tutor's closed error envelope
(six voice `error_type`s, contract §9 Rev 1). Covers upload validation
(size/duration/format, order-sensitive), session semantics parity (ownership,
lifecycle, per-turn durability, cross-device resume), ephemeral-audio
invariants (no audio at rest; in-memory parsing), degradation
(voice-down → text unaffected, no third-party egress; TTS-only failure →
text answer with empty audio per ASSUM-005), and security/concurrency edges
(spoken prompt injection, path-shaped filenames, simultaneous turns,
hanging speech services, true-size-over-declared-size enforcement).

Out of scope here (later features): WS streaming + sentence-chunked TTS
(FEAT-VOICE-002 with TASK-STREAM-001), the Flutter client (FEAT-VOICE-003),
Reachy (FEAT-VOICE-004).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 4 |
| Boundary conditions (@boundary) | 7 |
| Negative cases (@negative) | 12 (incl. overlaps with boundary/edge) |
| Edge cases (@edge-case) | 10 |

(Tag overlaps mean columns sum past 27.)

## Deferred Items

None — all four groups accepted as proposed; all six expansion scenarios included.

## Open Assumptions (low confidence)

None outstanding. ASSUM-005 (TTS half-failure → text answer with empty
audio, turn recorded once) is `confidence=low` but **owner-confirmed
2026-07-06**; it is a behavioural decision not present in the frozen
contract text — carry it into the FEAT-VOICE-002 streaming design
unchanged (an `audio_ref`-less done frame is the streaming analogue).

## Non-Gherkin obligations (for /feature-plan)

These are implementation-level pins the scenarios deliberately do not
encode (domain language), but the plan must carry:

- **Wire-seam tests** at `httpx.MockTransport`: multipart field `file`,
  filename, content-type with codec params intact, `model` field — the
  LPA "green but broken" defence (design §5.1, blueprint §7).
- **In-memory multipart parsing** (never `request.form()` — Starlette
  spools >1 MB parts to disk temp files) with `python-multipart` as a
  direct `pyproject.toml` pin (design §5.1).
- Upload validation **order**: size → empty → base-MIME → best-effort
  duration, with an order-pinning test (the LPA left the order untested).
- Error mapping per binding §4.1 Rev 1 (413/413/415/422/422/503) in the
  `{"error","error_type"}` envelope; flag-off ⇒ routes absent (404).
- Route registration via the conditional-route pattern in `create_app`
  (`http/app.py`), config via frozen dataclass `from_env` (`http/auth.py`
  precedent); deps on `app.state`.

## Integration with /feature-plan

    /feature-plan "FEAT-VOICE-001 server voice module" \
      --context features/voice-server-module/voice-server-module_summary.md
