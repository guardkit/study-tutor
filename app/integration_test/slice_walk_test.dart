// The attended-walk surrogate, run on a REAL device/simulator (first run: the
// iOS walk, Rich's word 2026-08-02). Drives the slice checkpoints through the
// REAL composition root — `main()` in its default hermetic flavour (fake
// backend, fake identity; no dart-defines) — mirroring the Android DoD walk:
// sign in → Home (with the Lane 1 step 2 subject picker) → start → two text
// turns → away → resume (transcript intact) → end (celebration sheet →
// dismissed to Home, session off the list). Voice stays out of this walk by
// design: real mic capture needs the system permission dialog and TTS
// audibility needs human ears — both remain an attended human walk.
//
// No pumpAndSettle here: under the live on-device binding the engine keeps
// scheduling frames (and Home animates), so open-ended settles time out at
// their 10-minute ceiling. Every wait is a bounded poll for the thing the
// walk actually needs to see next.
//
// Run: cd app && flutter test integration_test -d <device-id>
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/main.dart' as app;

/// Pump real frames until [finder] matches, or fail after [timeout].
Future<void> pumpUntil(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 30),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isNotEmpty) return;
  }
  throw TestFailure('timed out after $timeout waiting for $finder');
}

/// Pump real frames until [finder] matches nothing — used to let an outgoing
/// route finish its pop transition before the walk acts on what's beneath it
/// (acting mid-transition leaves two screens in the tree and taps ambiguous).
Future<void> pumpUntilGone(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 30),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isEmpty) return;
  }
  throw TestFailure('timed out after $timeout waiting for $finder to leave');
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets(
      'slice walk: sign-in → picker → start → two turns → away → resume → end',
      (tester) async {
    app.main();

    // Sign-in screen.
    await pumpUntil(tester, find.text('Study Tutor'));
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));

    // Home: greeting, and the subject picker visible at one subject.
    await pumpUntil(tester, find.text('Hi, Lilymay'));
    expect(find.text('Subject'), findsOneWidget);
    expect(find.byType(SegmentedButton<String>), findsOneWidget);
    expect(find.text('English'), findsOneWidget);

    // Start a session — opens titled by the selected subject.
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await pumpUntil(tester, find.widgetWithText(AppBar, 'English'));
    await pumpUntil(tester, find.textContaining('Ask your first question'));

    // Two text turns against the fake backend's canned replies.
    await tester.enterText(find.byType(TextField), 'first question');
    await tester.tap(find.byIcon(Icons.send));
    await pumpUntil(tester, find.text(FakeSessionApi.cannedReplies[0]));
    expect(find.text('first question'), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'second question');
    await tester.tap(find.byIcon(Icons.send));
    await pumpUntil(tester, find.text(FakeSessionApi.cannedReplies[1]));
    expect(find.text('second question'), findsOneWidget);

    // Away: Home re-lists the active session with its turn count. Wait out
    // the pop transition fully before touching Home.
    await tester.pageBack();
    await pumpUntilGone(tester, find.text('End session'));
    await pumpUntil(tester, find.widgetWithText(Card, 'English'));
    await pumpUntil(tester, find.text('2 turns'));

    // Resume: the ordered transcript is intact.
    await tester.tap(find.widgetWithText(FilledButton, 'Resume'));
    await pumpUntil(tester, find.text('End session'));
    await pumpUntil(tester, find.text('first question'));
    await pumpUntil(tester, find.text('second question'));

    // End: the fake's settlement block raises the celebration sheet (XP
    // count-up, confetti — the bounded poll rides the animations out).
    await tester.tap(find.text('End session'));
    await pumpUntil(tester, find.text('Nice work'),
        timeout: const Duration(seconds: 45));
    // A tap during the sheet's slide-up misses (the render position is still
    // in transit) — keep tapping until the sheet actually dismisses.
    final dismissDeadline = DateTime.now().add(const Duration(seconds: 30));
    while (find.text('Nice work').evaluate().isNotEmpty) {
      if (DateTime.now().isAfter(dismissDeadline)) {
        throw TestFailure('celebration sheet never dismissed');
      }
      await tester.pump(const Duration(seconds: 1));
      await tester.tap(find.text('Nice work'), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 500));
    }

    // Dismiss pops to Home; the ended session is off the resume list.
    await pumpUntilGone(tester, find.text('End session'));
    await pumpUntil(tester, find.text('Hi, Lilymay'));
    await pumpUntil(tester, find.textContaining('No sessions yet'));
  });
}
