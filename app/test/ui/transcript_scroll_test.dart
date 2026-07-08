// Fix-wave regression tests: the transcript must keep the newest message on
// screen. ListView.builder culls items outside the viewport, so "the latest
// bubble is findable / the oldest is not" is exactly "the list is scrolled
// to the bottom".
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/session.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/session_screen.dart';

void main() {
  final t0 = DateTime.utc(2026, 7, 4);

  List<TurnEntry> longTranscript(int pairs) => [
        for (var i = 0; i < pairs; i++) ...[
          TurnEntry(role: TurnRole.user, content: 'user-msg-$i', ts: t0),
          TurnEntry(role: TurnRole.tutor, content: 'tutor-msg-$i', ts: t0),
        ],
      ];

  Widget wrap(Widget child) => MaterialApp(home: child);

  testWidgets('resume opens at the latest exchange, not the oldest message',
      (tester) async {
    final identity = FakeIdentityProvider();
    final api = FakeSessionApi(identity: identity);
    final voiceApi = FakeVoiceApi();

    await tester.pumpWidget(wrap(SessionScreen(
      identity: identity,
      sessionApi: api,
      voiceApi: voiceApi,
      sessionId: 's-1',
      initialTurns: longTranscript(15),
    )));
    await tester.pumpAndSettle();

    expect(find.text('tutor-msg-14'), findsOneWidget,
        reason: 'the newest bubble is on screen');
    expect(find.text('user-msg-0'), findsNothing,
        reason: 'the oldest message is above the fold (culled by the list)');
  });

  testWidgets('sending in a long transcript keeps the new reply visible',
      (tester) async {
    final identity = FakeIdentityProvider();
    final api = FakeSessionApi(identity: identity);
    final voiceApi = FakeVoiceApi();
    await identity.signIn();
    final started = await api.startSession(subject: 'maths');
    for (var i = 0; i < 10; i++) {
      await api.turn(started.sessionId, 'seed-$i');
    }
    final resumed = await api.resumeSession(started.sessionId);

    await tester.pumpWidget(wrap(SessionScreen(
      identity: identity,
      sessionApi: api,
      voiceApi: voiceApi,
      sessionId: started.sessionId,
      initialTurns: resumed.turns,
    )));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'one more');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('one more'), findsOneWidget,
        reason: 'the just-sent message is on screen, not below the fold');
    // Turn index 10 → cannedReplies[10 % 4] == cannedReplies[2].
    expect(find.text(FakeSessionApi.cannedReplies[2]), findsOneWidget,
        reason: 'the tutor reply to the new message is on screen');
    expect(find.text('seed-0'), findsNothing,
        reason: 'old messages scrolled away above');
  });
}
