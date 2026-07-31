// Session-History screen (spec §3): lists the student's ENDED sessions and,
// on tap, opens their transcript read-only (no input bar). Driven entirely
// through the fakes.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/history_screen.dart';
import 'package:study_tutor_app/ui/transcript_view.dart';

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

  /// Start a session on [subject], run [turns] turns, then end it.
  Future<String> endedSession(String subject, {int turns = 1}) async {
    final started = await sessionApi.startSession(subject: subject);
    for (var i = 0; i < turns; i++) {
      await sessionApi.turn(started.sessionId, 'q$i');
    }
    await sessionApi.endSession(started.sessionId);
    return started.sessionId;
  }

  Widget wrap() => MaterialApp(
        home: HistoryScreen(
          identity: identity,
          sessionApi: sessionApi,
          voiceApi: voiceApi,
        ),
      );

  testWidgets('lists ended sessions with title-cased subject + turn count', (
    tester,
  ) async {
    await endedSession('biology', turns: 2);

    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    expect(find.text('Biology'), findsOneWidget,
        reason: 'subject is title-cased');
    expect(find.text('2 turns'), findsOneWidget);
  });

  testWidgets('does not list active sessions — ended only', (tester) async {
    await endedSession('biology');
    // An active session for a different subject must not appear.
    await sessionApi.startSession(subject: 'chemistry');

    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    expect(find.text('Biology'), findsOneWidget);
    expect(find.text('Chemistry'), findsNothing);
  });

  testWidgets('empty state when there are no ended sessions', (tester) async {
    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    expect(find.textContaining('No finished sessions yet'), findsOneWidget);
  });

  testWidgets('tapping an ended session opens its transcript read-only', (
    tester,
  ) async {
    await endedSession('biology', turns: 2);

    await tester.pumpWidget(wrap());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Biology'));
    await tester.pumpAndSettle();

    // The read-only transcript is shown: the turns, in order, via TranscriptView.
    expect(find.byType(TranscriptView), findsOneWidget);
    expect(find.text('q0'), findsOneWidget);
    expect(find.text('q1'), findsOneWidget);
    // Deterministic tutor replies from the fake.
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[1]), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('q0')).dy,
      lessThan(tester.getTopLeft(find.text('q1')).dy),
      reason: 'transcript order is turn order',
    );

    // Read-only: no input bar to send another message.
    expect(find.byType(TextField), findsNothing);
    expect(find.byIcon(Icons.send), findsNothing);
  });
}
