// The happy-path slice widget test (scope §4 close): pump the real app with
// the fakes injected and drive the whole slice through actual widgets —
// sign in → start → two turns → navigate away → resume from home
// (transcript intact) → end (input disabled). This is the test that makes
// `flutter test` fail if the screens are never wired to the port.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/app.dart';
import 'package:study_tutor_app/ui/home_screen.dart';

void main() {
  testWidgets('full slice: sign in → start → turns → away → resume → end',
      (tester) async {
    final identity = FakeIdentityProvider();
    final sessionApi = FakeSessionApi(identity: identity);
    final voiceApi = FakeVoiceApi();
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi, voiceApi: voiceApi));

    // Sign in.
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Hi, Lilymay'), findsOneWidget);

    // Start a session.
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Ask your first question'), findsOneWidget);

    // Two turns — transcript grows.
    await tester.enterText(find.byType(TextField), 'first question');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'second question');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();
    expect(find.text('first question'), findsOneWidget);
    expect(find.text('second question'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[1]), findsOneWidget);

    // Navigate away — home re-lists and shows the resume affordance.
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget,
        reason: 'session lists under the default subject, title-cased (ASSUM-001)');
    expect(find.text('2 turns'), findsOneWidget,
        reason: 'turn_count survives leaving the session');
    expect(find.widgetWithText(FilledButton, 'Start new session'),
        findsOneWidget, reason: 'starting fresh stays possible');

    // Resume — the transcript reloads from the store, intact and in order.
    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();
    expect(find.text('first question'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[0]), findsOneWidget);
    expect(find.text('second question'), findsOneWidget);
    expect(find.text(FakeSessionApi.cannedReplies[1]), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('first question')).dy,
      lessThan(tester.getTopLeft(find.text('second question')).dy),
      reason: 'transcript order is turn order',
    );

    // The resumed session is live: a third turn continues the same thread.
    await tester.enterText(find.byType(TextField), 'third question');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();
    expect(find.text(FakeSessionApi.cannedReplies[2]), findsOneWidget,
        reason: 'reply index continues from the stored turn_count');

    // End — the settlement block fires the celebration sheet (§6.2), then the
    // dismiss pops back to Home.
    await tester.tap(find.text('End session'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('celebration-sheet')), findsOneWidget,
        reason: 'a non-null gamification block celebrates on end');
    expect(find.text('Nice work'), findsOneWidget);

    // Dismiss → pop to Home; the ended session is gone from the resume list.
    await tester.tap(find.text('Nice work'));
    // The Home flame idle-pulses once the streak is alive today, so a single
    // perpetual animation is on screen — settle with bounded pumps, not
    // pumpAndSettle.
    await tester.pump(); // start the pop transition
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('Resume'), findsNothing);
    expect(find.text(homeEmptyState), findsOneWidget);
  });
}
