// Scope §3: SessionForbidden → the shared "can't open this session" surface,
// back to home. Induced through the fakes: the session the home screen is
// about to resume becomes one owned by the second principal (the store row
// is swapped to Alex's ownership under the same id).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  testWidgets('resuming a session owned by the second principal → shared '
      'error surface, back to home, no crash', (tester) async {
    final identity = FakeIdentityProvider();
    final store = InMemorySessionStore();
    final sessionApi = FakeSessionApi(identity: identity, store: store);
    final voiceApi = FakeVoiceApi();
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi));

    // Lilymay starts a session and goes back home, which lists it.
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Resume'), findsOneWidget);

    // Seed the ownership violation: the same session id now belongs to Alex.
    final id = store.sessions.keys.single;
    final original = store.sessions[id]!;
    store.sessions[id] = Session(
      id: original.id,
      studentId: 'alex',
      subject: original.subject,
      topic: original.topic,
      status: original.status,
      startedAt: original.startedAt,
      lastActivity: original.lastActivity,
      turnCount: original.turnCount,
    );

    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();

    expect(find.text("Can't open this session"), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(find.text('Home'), findsOneWidget);
    expect(find.text('No active sessions'), findsOneWidget,
        reason: 're-list after the error: the foreign row is gone');
  });
}
