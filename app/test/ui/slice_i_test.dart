// Wave-6 widget tests: the screens are wired to the ports — sign-in drives
// IdentityProvider, "Start new session" drives startSession, send drives
// turn and the transcript grows (build plan wave-6).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;

  Widget makeApp() {
    identity = FakeIdentityProvider();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
    return StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi);
  }

  Future<void> signIn(WidgetTester tester) async {
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
  }

  testWidgets('sign-in drives IdentityProvider.signIn and lands on home',
      (tester) async {
    await tester.pumpWidget(makeApp());
    expect(identity.currentPrincipal, isNull);

    await signIn(tester);

    expect(identity.currentPrincipal, FakeIdentityProvider.lilymay,
        reason: 'the button must actually call the port');
    expect(find.text('Hi, Lilymay'), findsOneWidget);
  });

  testWidgets('"Start new session" drives startSession and opens the '
      'session screen', (tester) async {
    await tester.pumpWidget(makeApp());
    await signIn(tester);

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('English'), findsOneWidget);
    expect(find.textContaining('Ask your first question'), findsOneWidget);
    expect(await sessionApi.listSessions(), hasLength(1),
        reason: 'a session must exist in the fake store');
  });

  testWidgets('one turn round-trip renders the user message and the canned '
      'tutor reply', (tester) async {
    await tester.pumpWidget(makeApp());
    await signIn(tester);
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'what is a fraction?');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('what is a fraction?'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    expect(find.textContaining('Ask your first question'), findsNothing);

    // Transcript grows: a second exchange appends, nothing is replaced.
    await tester.enterText(find.byType(TextField), 'a part of a whole?');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('what is a fraction?'), findsOneWidget);
    expect(find.text('a part of a whole?'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[1]), findsOneWidget);
  });
}
