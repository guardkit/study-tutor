---
id: TASK-VOX-006
title: "HTTP routes — flag-gated voice-turn/voice-audio, envelope mapping, serve-http wiring"
task_type: feature
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VOX-005]
consumer_context:
  - task: TASK-VOX-005
    consumes: VoiceTurnService + ChunkStore
    framework: "Starlette handlers over app.state"
    driver: "starlette"
    format_note: "voice_turn(...) -> VoiceTurnResult; ChunkStore.get(session_id, chunk_id) -> bytes | None (None ⇒ transport-level 404, no error_type)"
  - task: TASK-VOX-001
    consumes: VoiceConfig
    framework: "frozen dataclass"
    driver: "stdlib dataclasses"
    format_note: "enabled gates route mounting; STT_/TTS_ env names read once in serve-http"
---

## Description

Bind the frozen contract (binding §2/§2.1/§4 Rev 1) into the adapter:

- **Handlers** in `src/study_tutor/voice/routes.py`:
  `POST /api/sessions/{session_id}/voice-turn` (multipart via TASK-VOX-004;
  `stream` field reserved-and-ignored like `turn`, app.py:265) and
  `GET /api/sessions/{session_id}/voice-audio/{chunk_id}` (returns
  `audio/wav` bytes; store miss ⇒ **404 `{"error": "audio chunk expired or unknown"}`
  with no `error_type`** — binding §4.2 Rev 1). Both call
  `_resolve_student_id` first (app.py:88-110) and enforce session ownership
  exactly like the six existing verbs.
- **Error mapping** per-handler (there is no middleware): the six voice
  exceptions → 413/413/415/422/422/503 with `{"error", "error_type"}` (class
  name); the four session errors keep their existing mapping (`_map_error_to_response`,
  app.py:45-85); `ValueError`/missing-field → 400 no error_type.
- **Conditional mounting** in `create_app` (app.py:468-481 pattern): routes
  appended **only when** `voice_config.enabled` — flag absent/off ⇒ 404, and
  the six original routes are never affected. `create_app` gains an optional
  `voice_config`/`voice_service` parameter defaulting to disabled (all
  existing tests untouched).
- **Wiring** in `serve-http` (`cli/main.py:819-956`): `VoiceConfig.from_env()`
  → `AudioClient` → `ChunkStore` → `VoiceTurnService` (reusing the existing
  `reply_fn_factory`), stuffed on `app.state` like every other dependency.

Tests (`tests/unit/http/test_voice_routes.py`, TestClient + AsyncMock per
`test_app.py:32-74` conventions): status mapping for all six voice errors;
401 missing/invalid token; 403 other student's session; 404 unknown session;
410 ended session; flag off ⇒ 404 both routes + text routes unaffected;
`stream: true` accepted-and-ignored; chunk-miss 404 body shape; happy-path
response shape `{transcript, tutor_response, audio:[{seq, chunk_id, url}]}`.

## Acceptance Criteria

- [ ] All binding §2/§4 Rev 1 mappings verified by TestClient tests (list above)
- [ ] Flag off: voice routes 404, existing suite fully green with zero changes to existing tests
- [ ] `voice_audio` streams `audio/wav` with correct content-type; miss ⇒ 404 without `error_type`
- [ ] `serve-http` boots with voice enabled and disabled (subprocess boot smoke pattern, `test_serve_http.py:33-75`, skipped without DSN)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam test: verify the ChunkStore contract from TASK-VOX-005 at the route boundary."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("chunk_store_get")
def test_chunk_miss_is_transport_404(client_with_voice):
    """Contract: ChunkStore.get -> None maps to 404 with NO error_type
    (binding §4.2 Rev 1). Producer: TASK-VOX-005; consumer: voice_audio route."""
    r = client_with_voice.get("/api/sessions/s1/voice-audio/expired", headers=AUTH)
    assert r.status_code == 404
    assert "error_type" not in r.json()
```

## References

- Binding §2/§2.1/§4 Rev 1 (BINDING_SHA `e50897d1…`) · design §5.1/§5.5 · `http/app.py` seams cited above
