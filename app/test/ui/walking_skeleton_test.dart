// Wave-5 widget tests (updated in wave-6 for constructor injection): the app
// boots to sign-in and navigation between the three screens works.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  Widget makeApp() {
    final identity = FakeIdentityProvider();
    return StudyTutorApp(
      identity: identity,
      sessionApi: FakeSessionApi(identity: identity),
      voiceApi: FakeVoiceApi(),
    );
  }

  testWidgets('app boots to the sign-in screen', (tester) async {
    await tester.pumpWidget(makeApp());

    expect(find.text('Study Tutor'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
  });

  testWidgets('sign-in → home → session → back to home', (tester) async {
    await tester.pumpWidget(makeApp());

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Hi, Lilymay'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Start new session'),
        findsOneWidget);
    // skipOffstage: false so this fails if sign-in is merely covered (plain
    // push) rather than replaced — offstage routes are skipped by default.
    expect(find.text('Sign in', skipOffstage: false), findsNothing,
        reason: 'sign-in is replaced, not stacked');

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('No messages yet'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Hi, Lilymay'), findsOneWidget);
  });

  testWidgets('sign-in shows displayName choices and can pick the second '
      'principal', (tester) async {
    await tester.pumpWidget(makeApp());

    // The fake exposes two principals → both are offered as choices.
    expect(find.widgetWithText(OutlinedButton, 'Lilymay'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Alex'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Alex'));
    await tester.pumpAndSettle();

    expect(find.text('Hi, Alex'), findsOneWidget,
        reason: 'picking a principal signs in as them, not the default');
  });
}
