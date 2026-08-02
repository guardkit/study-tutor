---
id: TASK-FLV1-001
title: Show the app version on the home screen
task_type: feature
feature_id: FEAT-FLV1
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
component: app
conformance:
  ac_paths: true
  rules:
  - id: R-FLV1-UI
    type: token_coverage
    paths:
    - app/lib/ui/home_screen.dart
    require_tokens:
    - "appVersion"
  - id: R-FLV1-TESTS
    type: assert_command
    command: "cd app && flutter test"
---

# TASK-FLV1-001: Show the app version on the home screen

## Objective

Display the app's own version on the home screen — a small, additive,
read-only UI element (the Flutter twin of FEAT-STV1's `/api/version`).
No network, no new dependencies, no platform channels.

## Acceptance Criteria

- **AC-001**: A constant `appVersion` lives in `app/lib/config/` (a new small
  file beside the existing config), carrying the version string from
  `app/pubspec.yaml`'s `version:` line.
- **AC-002**: The constant can never silently drift from pubspec: a test reads
  `app/pubspec.yaml` from disk and asserts `appVersion` matches its `version:`
  value — the pubspec is the single source of truth, the test is the pin.
- **AC-003**: The home screen (`app/lib/ui/home_screen.dart`) renders the
  version as unobtrusive secondary text (e.g. a small "v1.0.0+1" line),
  styled consistently with the screen's existing secondary text; it must not
  displace or reorder any existing element.
- **AC-004**: A widget test proves the home screen shows the version string
  (pumps the screen with its existing test scaffolding — read the
  neighbouring home screen tests and mirror their setup exactly).
- **AC-005**: `cd app && flutter analyze` stays clean and the FULL
  `cd app && flutter test` suite stays green (386 existing cases + the new
  ones). No existing test is modified.
- **AC-006**: NO other screen, port, adapter, or backend file is touched. If
  the builder believes any other surface must change, that is a
  STOP-and-report, not an edit.

## Implementation Notes

- `app/pubspec.yaml:19` → `version: 1.0.0+1` (today's value).
- The home screen is `app/lib/ui/home_screen.dart`; its tests live under
  `app/test/ui/` — mirror their pump/scaffold pattern.
- Working directory law: this is an `app`-component task — the verdict is
  `flutter test` at cwd `app/` per the repo's toolchain declaration.

## Test Commands (Coach Validation)

```bash
cd app && flutter test
```
