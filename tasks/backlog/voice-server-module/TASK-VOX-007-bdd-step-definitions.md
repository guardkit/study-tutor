---
id: TASK-VOX-007
title: "pytest-bdd step definitions \u2014 wire the 27-scenario voice feature file\
  \ hermetically"
task_type: testing
parent_review: TASK-REV-852B
feature_id: FEAT-VOICE-001
wave: 5
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-VOX-006
status: in_review
autobuild_state:
  current_turn: 5
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-VOICE-001
  base_branch: main
  started_at: '2026-07-08T13:36:12.666253'
  last_updated: '2026-07-08T14:18:20.464337'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Security vulnerability: test_another_student_cannot_fetch_my_reply_audio
      fails with ''assert 200 == 403''. The endpoint returns 200 OK when it should
      deny access with 403 Forbidden, allowing cross-student audio fetching.: Fix
      the authorization check in the audio fetch endpoint to validate that the requesting
      student matches the audio owner. Add proper student_id validation before returning
      audio chunks.

      - Missing mp3 format support: test_recordings_in_supported_formats_are_accepted_regardless_of_codec_annotations[mp3]
      fails with ''assert 415 == 200''. Mp3 recordings are rejected when they should
      be accepted.: Add mp3 to the list of supported audio formats in the voice endpoint.
      Ensure the content-type validation accepts audio/mpeg and audio/mp3 MIME types.

      - ChunkStore expiry implementation bug: test_a_reply_audio_reference_fetched_promptly_succeeds_but_an_expired_one_is_gone
      fails with ''AttributeError: ChunkStore object has no attribute _chunks''.:
      Fix the ChunkStore implementation. The test code appears to access a private
      _chunks attribute that doesn''t exist. Either add the _chunks attribute to ChunkStore
      or refactor the expiry test to use the public API.

      ... and 1 more issues'
    timestamp: '2026-07-08T13:36:12.666253'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file .guardkit/bdd/TASK-VOX-007_authoring_junit.xml.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- AC-003 requires running `uv run pytest tests\
      \ -q` to verify the full repo test suite. Runtime parity check ran `tests/unit`\
      \ (1216 passed), which provides strong circumstantial evidence, but the exact\
      \ command scope was not verified. The Player only modified BDD test files under\
      \ features/, making it unlikely to break other tests, but explicit verification\
      \ is required.: Run: uv run pytest tests -q\n- AC-004 requires lint/format verification\
      \ of modified files. No evidence of lint/format checks in the evidence bundle.\
      \ Modified file: features/voice-server-module/test_voice_server_module.py: Run\
      \ project-configured lint/format checks (e.g., ruff check, black --check, mypy)\
      \ on features/voice-server-module/test_voice_server_module.py\n... and 1 more\
      \ issues"
    timestamp: '2026-07-08T13:51:57.346725'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file .guardkit/bdd/TASK-VOX-007_authoring_junit.xml.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Independent test verification absent: Phase\
      \ 4 (test-orchestrator) timed out after 60s. Evidence bundle shows tests_run:\
      \ null and independent_tests: null. Cannot verify AC-001 (BDD suite green) without\
      \ independent test execution.: Orchestrator must successfully complete Phase\
      \ 4 test execution to provide independent verification of the BDD suite. The\
      \ substrate timeout is not a Player issue, but prevents approval until resolved.\n\
      - Evidence gathering aborted (partial_gate_abort) before producing independent\
      \ verification signals for hermetic testing, full repo suite, or lint/format\
      \ checks. All ACs rely on verification that is absent from the evidence bundle.:\
      \ Orchestrator must complete evidence gathering to provide independent verification.\
      \ Per GATHERING-STATUS GUARD and ZERO-CARDINALITY TEST GUARD, absence of verification\
      \ is not success.\n... and 1 more issues"
    timestamp: '2026-07-08T14:01:58.486752'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file .guardkit/bdd/TASK-VOX-007_authoring_junit.xml.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file features/voice-server-module/test_voice_server_module.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- No independent test verification occurred\
      \ this turn. The test-orchestrator specialist timed out (SDKTimeoutError: Agent\
      \ invocation exceeded 60s timeout), and evidence_bundle.tests.tests_run = null.\
      \ Per absence-of-failure guard #2, zero-cardinality test execution is ABSENT\
      \ SIGNAL - cannot verify AC-001.: The orchestrator must successfully run `uv\
      \ run pytest features/voice-server-module -q` and capture deterministic evidence.\
      \ The timeout suggests infrastructure issues - investigate test runtime or increase\
      \ timeout threshold.\n... and 4 more issues"
    timestamp: '2026-07-08T14:07:42.291729'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 5
    decision: approve
    feedback: null
    timestamp: '2026-07-08T14:11:12.199200'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
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
