// Scope §3: SessionNotFoundError → the shared "can't open this session"
// surface, back to home. Induced through the fakes: the session id the home
// screen is about to resume no longer exists in the store.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/home_screen.dart';

void main() {
  testWidgets('resuming an unknown session id → shared error surface, back '
      'to home, no crash', (tester) async {
    final identity = FakeIdentityProvider();
    final store = InMemorySessionStore();
    final sessionApi = FakeSessionApi(identity: identity, store: store);
    final voiceApi = FakeVoiceApi();
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Resume'), findsOneWidget);

    // The id goes stale: the session vanishes from the store entirely.
    final id = store.sessions.keys.single;
    store.sessions.remove(id);
    store.turnsBySession.remove(id);

    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();

    expect(find.text("Can't open this session"), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(find.text('Hi, Lilymay'), findsOneWidget);
    expect(find.text(homeEmptyState), findsOneWidget,
        reason: 're-list after the error: the stale row is gone');
  });
}
