// Scope §3: SessionEnded → session screen shows the ended state, input
// disabled. Induced through the fakes: another client over the same store
// (a "second device") ends the session, then the UI attempts a turn.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  testWidgets('turn on a session ended elsewhere → ended state, input '
      'disabled, no crash', (tester) async {
    final identity = FakeIdentityProvider();
    final store = InMemorySessionStore();
    final sessionApi = FakeSessionApi(identity: identity, store: store);
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'first question');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    // End the session behind the UI's back — same student, other device.
    final otherDevice = FakeSessionApi(identity: identity, store: store);
    await otherDevice.endSession(store.sessions.keys.single);

    await tester.enterText(find.byType(TextField), 'still there?');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('Session ended'), findsOneWidget);
    expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
    expect(
      tester
          .widget<IconButton>(find.widgetWithIcon(IconButton, Icons.send))
          .onPressed,
      isNull,
    );
    expect(find.text('End session'), findsNothing,
        reason: 'no End affordance on an already-ended session');
    // (find.text alone would also match the un-sent text still sitting in
    // the disabled input field — scope the finder to the transcript list.)
    expect(
      find.descendant(
          of: find.byType(ListView), matching: find.text('still there?')),
      findsNothing,
      reason: 'the rejected message must not be appended to the transcript',
    );
    expect(find.text('first question'), findsOneWidget,
        reason: 'the earlier transcript stays readable');
  });
}
