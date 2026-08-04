// Runs around EVERY file in test_live/ (flutter_test's per-directory hook):
// registers an end-of-file cleanup so no run leaves stray suite sessions
// behind — the 2026-08-03 finding where leftover subject:'maths' test
// sessions surfaced on the real Home as convincing "Continue: …" cards.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'suite_identity.dart';

const _rawApiBaseUrl = String.fromEnvironment('API_BASE_URL');

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  tearDownAll(() async {
    final base = _rawApiBaseUrl.endsWith('/')
        ? _rawApiBaseUrl.substring(0, _rawApiBaseUrl.length - 1)
        : _rawApiBaseUrl;
    await cleanupSuiteSessions(base);
  });
  await testMain();
}
