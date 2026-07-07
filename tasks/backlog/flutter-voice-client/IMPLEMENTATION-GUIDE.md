# Implementation Guide: Flutter tap-to-talk voice client (FEAT-VOICE-003)

**Parent review:** TASK-REV-V3C1 · **Approach:** Option 1 (port + fidelity first → MVP HTTP → streaming)
**Trade-off priority:** Quality/reliability · **Testing:** Standard (quality gates + dual-backend/direction-pins)

Client-only feature. Does **not** duplicate FEAT-VOICE-001 (server rulebook) or FEAT-VOICE-002
(server streaming). Where the client surfaces a server decision, it asserts the client's
**surfacing and recoverability**, not the server's rulebook.

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths (client → tutor)"]
        W1["SessionScreen mic press\n(record → 60s/10MB stop)"]
        W2["HttpVoiceApi.voiceTurn()\nMVP multipart upload"]
        W3["HttpVoiceApi.voiceTurnStream()\nWS upload (live)"]
    end

    subgraph Storage["Seam / Transport"]
        S1[("multipart 'audio'\n(codec params intact)")]
        S2[("WS frames\n(seq-ordered)")]
    end

    subgraph Reads["Read Paths (tutor → client UI)"]
        R1["Transcript-first render\n(SessionScreen)"]
        R2["just_audio ordered\nplayback queue (seq)"]
        R3["fetchAudioChunk()\n(authenticated per part)"]
        R4["Amber VoiceUnavailable\ndegradation notice"]
    end

    W1 -->|"press to send"| W2
    W1 -->|"live channel"| W3
    W2 -->|"POST"| S1
    W3 -->|"WS send"| S2

    S1 -->|"VoiceTurnResult"| R1
    S2 -->|"VoiceTurnEvent (transcript frame)"| R1
    S2 -->|"VoiceTurnEvent (audio part by seq)"| R2
    S2 -->|"chunk-by-URL"| R3
    S1 -->|"VoiceUnavailable error_type"| R4
    S2 -.->|"VoiceUnavailable error_type"| R4

    style R1 fill:#cfc,stroke:#090
    style R2 fill:#cfc,stroke:#090
    style R3 fill:#cfc,stroke:#090
    style R4 fill:#ffe,stroke:#c90
```

_What to look for: every write path (record → upload, MVP + WS) has a wired read path (transcript,
playback, chunk fetch, degradation). No disconnected read._

**Disconnection Alert:** None within the feature. The streaming read paths (R2/R3) depend on
**FEAT-VOICE-002** server delivery — a deliberate **cross-feature** seam (server owns WS frame
ordering + chunk-by-URL), not an in-feature disconnected read. TASK-VC-006 asserts the client side;
the live end-to-end proof lives in TASK-VC-007 against the GB10 tutor.

---

## Integration Contracts (sequence)

```mermaid
sequenceDiagram
    participant U as User
    participant SS as SessionScreen
    participant Rec as Recorder (record)
    participant API as HttpVoiceApi
    participant T as Tutor (FEAT-VOICE-001/002)
    participant JA as just_audio

    U->>SS: press mic → speak → press to send
    SS->>Rec: start / stop (60s hard stop, 10MB backstop)
    Rec-->>SS: audio bytes + captured contentType
    SS->>API: voiceTurn(sessionId, bytes, contentType)
    Note over API,T: Direction-pin: field 'audio', filename ext,\nContent-Type codec params INTACT, bearer, on-session
    API->>T: multipart POST (green-but-broken defence here)
    T-->>API: transcript + answer parts (or error_type)
    API-->>SS: VoiceTurnResult (transcript FIRST)
    SS-->>U: transcript rendered like a typed turn
    SS->>JA: enqueue answer parts by seq
    JA-->>U: ordered spoken answer
    Note over SS,U: VoiceUnavailable → amber notice, mic disabled for session
```

_What to look for: the transcript is passed onward to the UI (rendered first) and the answer bytes
reach just_audio — no "fetch then discard". The fidelity contract is asserted at the API→Tutor arrow._

---

## Task Dependencies

```mermaid
graph TD
    T1["TASK-VC-001\ndeps + manifests"]
    T2["TASK-VC-002\nVoiceApi port + DTOs"]
    T3["TASK-VC-003\nHttpVoiceApi + fidelity pins"]
    T4["TASK-VC-004\nfakes + recorder (60s/10MB)"]
    T5["TASK-VC-005\nSessionScreen UX + degradation"]
    T6["TASK-VC-006\nstreaming + ordered playback"]
    T7["TASK-VC-007\ndual-backend + live tests"]

    T2 --> T3
    T1 --> T4
    T2 --> T4
    T3 --> T5
    T4 --> T5
    T5 --> T6
    T3 --> T7
    T5 --> T7
    T6 --> T7

    style T1 fill:#cfc,stroke:#090
    style T2 fill:#cfc,stroke:#090
    style T3 fill:#cfc,stroke:#090
    style T4 fill:#cfc,stroke:#090
```

_Tasks with green background can run in parallel within their wave._

### Execution waves (auto-detected)

- **Wave 1** (parallel): TASK-VC-001, TASK-VC-002 — no cross-dependency, disjoint files.
- **Wave 2** (parallel): TASK-VC-003, TASK-VC-004 — both build on the port; disjoint files (adapter vs fakes/recorder).
- **Wave 3**: TASK-VC-005 — needs the HTTP turn + recorder/fakes.
- **Wave 4**: TASK-VC-006 — layers streaming on the MVP UX host.
- **Wave 5**: TASK-VC-007 — exercises the full surface, hermetic + live.

---

## §4: Integration Contracts

### Contract: VoiceApi (internal interface)
- **Producer task:** TASK-VC-002
- **Consumer task(s):** TASK-VC-003, TASK-VC-004, TASK-VC-006, TASK-VC-005 (via injection)
- **Artifact type:** Dart `abstract interface class` + DTOs (`VoiceTurnResult`, `VoiceTurnEvent`) + sealed error types
- **Format constraint:** DTO field names and the six sealed `error_type` members are stable; adapters
  implement the interface exactly; `VoiceUnavailable` is the degradation-driving member.
- **Validation method:** Coach verifies all consumers compile against `voice_api.dart` and a `switch`
  over the sealed errors is exhaustive.

### Contract: VOICE_UPLOAD_MULTIPART (the fidelity seam — "green but broken")
- **Producer task:** TASK-VC-003 (builds the outgoing multipart in `HttpVoiceApi.voiceTurn`)
- **Consumer task(s):** TASK-VC-007 (live-seam validation); external consumer = tutor server (FEAT-VOICE-001)
- **Artifact type:** HTTP multipart request via `package:http` MultipartRequest
- **Format constraint:** multipart field name **`audio`**; filename extension matching the **captured
  codec**; `Content-Type` **preserving codec params exactly as recorded** (never silently re-encoded or
  stripped); `Authorization: Bearer …` present; request path bound to the caller's `sessionId`.
- **Validation method:** hermetic MockClient direction-pins in TASK-VC-003 assert every field above;
  TASK-VC-007 ports the same assertions to the live GB10 seam. This is the single highest-value test
  asset — a recording that uploads "green" but arrives mis-authed / wrong-session / re-encoded is the
  exact failure this contract exists to catch.

---

## Open items carried into the build

- **ASSUM-006 (encoder, Phase-0 gated):** m4a/AAC default vs opus fallback is settled by the Phase-0
  m4a-against-live-STT test **inside TASK-VC-004**; keep the encoder injectable. The fidelity guarantee
  holds regardless of winner.
- **ASSUM-010 / ASSUM-011 (copy, low-confidence):** mic-permission + refusal-reason wording is inferred.
  Behaviour is firm and hermetically testable against whatever strings are chosen — remains
  autobuild-suitable; confirm final copy with design before release.

---

## Next steps

1. Review this guide + the data-flow diagram (the primary review artefact).
2. `/feature-build FEAT-VOICE-003` for autonomous wave execution, **or** start Wave 1 manually:
   `/task-work TASK-VC-001` and `/task-work TASK-VC-002`.
