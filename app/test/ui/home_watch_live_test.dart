// live-mirror entry point (spec: BUILD (a)): Home surfaces a "Watch live"
// control on each active session, opening the read-only LiveSessionScreen.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/live_session_screen.dart';

void main() {
  late FakeIdentityProvider identity;
  late FakeSessionApi sessionApi;
  late FakeVoiceApi voiceApi;

  setUp(() async {
    identity = FakeIdentityProvider();
    await identity.signIn();
    sessionApi = FakeSessionApi(identity: identity);
    voiceApi = FakeVoiceApi();
  });

  Widget wrap() => MaterialApp(
        home: HomeScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
        ),
      );

  testWidgets('active session shows a Watch live control that opens the mirror',
      (tester) async {
    final started = await sessionApi.startSession(subject: 'english');
    await sessionApi.turn(started.sessionId, 'hello');

    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    // The active card carries both Resume and a Watch live affordance.
    expect(find.widgetWithText(FilledButton, 'Resume'), findsOneWidget);
    final watch = find.byTooltip('Watch live');
    expect(watch, findsOneWidget);

    await tester.tap(watch);
    await tester.pump(); // push
    await tester.pump(); // initial resume resolves

    expect(find.byType(LiveSessionScreen), findsOneWidget);
    expect(find.text('hello'), findsOneWidget, reason: 'mirror shows the turn');
    expect(find.text('LIVE'), findsOneWidget);

    // Leave the live screen so its poll timer is torn down cleanly.
    await tester.pageBack();
    await tester.pumpAndSettle();
  });

  testWidgets('no Watch live control when there are no active sessions',
      (tester) async {
    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    expect(find.byTooltip('Watch live'), findsNothing);
    expect(find.textContaining('No sessions yet'), findsOneWidget);
  });
}
