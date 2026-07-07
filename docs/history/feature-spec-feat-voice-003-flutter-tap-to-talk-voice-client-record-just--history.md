# /feature-spec — feat-voice-003-flutter-tap-to-talk-voice-client-record-just- — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec feat-voice-003-flutter-tap-to-talk-voice-client-record-just- — 2026-07-07T06:08:23Z

### Prompt

```
/feature-spec "FEAT-VOICE-003 Flutter tap-to-talk voice client: record/just_audio/web_socket_channel deps (deliberate zero-deps DoD scope event); INTERNET+RECORD_AUDIO main-manifest + NSMicrophoneUsageDescription; VoiceApi port with Http/Fake/Flaky adapters mirroring SessionApi seams; tap-to-talk with client-side 60s hard stop; transcript-first display; ordered wav chunk playback; VoiceUnavailable amber degradation copy; hermetic direction-pin tests + app/test_live voice variants" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context app/README.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md
```

### Assistant response

I'll execute the `/feature-spec` command following the six-phase Propose-Review methodology. Let me start with **Phase 1: Context Gathering** (silent, no interaction).

Stack signals: root has `pyproject.toml` (Python backend) but this feature targets the **Flutter app** (`app/pubspec.yaml`). Let me read the two large context docs and scan the app seams the feature must mirror.

Rich context. Now let me examine the existing voice feature spec (to avoid overlap with FEAT-VOICE-002), the `SessionApi` seams to mirror, and the build-plan's client scope.
