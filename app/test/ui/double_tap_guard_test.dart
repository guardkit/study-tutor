// Fix-wave regression test: a double-tap on Home's Start/Resume must not
// start two sessions or push two screens. The two taps land in the same
// frame (no pump between them), so the button has not yet rebuilt as
// disabled — only the synchronous `_busy` guard can stop the second one.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

void main() {
  testWidgets('double-tap on Start new session creates exactly one session',
      (tester) async {
    final identity = FakeIdentityProvider();
    final store = InMemorySessionStore();
    final sessionApi = FakeSessionApi(identity: identity, store: store);
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();

    final start = find.widgetWithText(FilledButton, 'Start new session');
    await tester.tap(start);
    await tester.tap(start, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(store.sessions.length, 1,
        reason: 'the second tap must be swallowed by the in-flight guard');
    expect(find.byType(SessionScreen, skipOffstage: false), findsOneWidget,
        reason: 'exactly one session screen pushed');
  });

  testWidgets('double-tap on Resume opens exactly one session screen',
      (tester) async {
    final identity = FakeIdentityProvider();
    final store = InMemorySessionStore();
    final sessionApi = FakeSessionApi(identity: identity, store: store);

    // Seed an active session so Home shows a Resume card.
    await identity.signIn();
    final seeded = await sessionApi.startSession(subject: 'maths');
    await sessionApi.turn(seeded.sessionId, 'hello');

    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi));
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();

    final resume = find.widgetWithText(FilledButton, 'Resume');
    await tester.tap(resume);
    await tester.tap(resume, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(find.byType(SessionScreen, skipOffstage: false), findsOneWidget);
    expect(store.sessions.length, 1);
  });
}
