---
id: TASK-VOX-007
title: "pytest-bdd step definitions — wire the 27-scenario voice feature file hermetically"
task_type: testing
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 5
implementation_mode: task-work
complexity: 5
dependencies: [TASK-VOX-006]
---

## Description

Implement step definitions in
`features/voice-server-module/test_voice_server_module.py` (house convention:
step-def module lives beside the `.feature`, cf.
`features/http-app-access-adapter/test_http_app_access_adapter.py`) covering
the scenarios in `voice-server-module.feature` — hermetic throughout:
TestClient over `create_app` with a fake reply-fn (canned tutor answers),
`MockAudioTransport` for STT/TTS (set_transcript / simulate-down toggles),
and the TASK-VOX-003 synthetic builders for boundary payloads.

Scenario→fixture notes:
- "resume from another device" — second TestClient over the same app/store.
- "no request should leave for any third-party service" — assert the mock
  transport captured zero calls to non-configured hosts (it is the only
  egress; the fake reply-fn is in-process).
- "No recording audio is ever kept" — inspect the session store rows +
  patched `tempfile.SpooledTemporaryFile` guard + capturing log handler.
- "path-shaped filename" / "spoken re-instruction" — filename passes through
  to the STT multipart only; canned reply-fn shows the transcript reached the
  turn path as plain user input.
- Simultaneous turns — `anyio`/task-group double submission against one app.

Every scenario keeps its `@task:` tag from the Step-11 linker run; this task
turns `scenarios_pending` into `scenarios_passed` for the tags pointing at
TASK-VOX-001..006 and itself.

## Acceptance Criteria

- [ ] `uv run pytest features/voice-server-module -q` green (all wired scenarios pass; none skipped without a recorded reason)
- [ ] No live network: the suite passes with no GB10 reachable (hermetic guarantee)
- [ ] Full repo suite (`uv run pytest tests -q`) still green
- [ ] All modified files pass project-configured lint/format checks with zero errors

## References

- `features/voice-server-module/voice-server-module.feature` (+ `_assumptions.yaml`) · TASK-VOX-002's MockAudioTransport · house step-def precedent in `features/*/test_*.py`
