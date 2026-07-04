// Scope §3: Unauthenticated → route to the sign-in screen. Induced through
// the fakes: invalidate the token mid-session, then use the UI.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/ui/app.dart';

void main() {
  testWidgets('invalidated token on start → routed back to sign-in, no crash',
      (tester) async {
    final identity = FakeIdentityProvider();
    final sessionApi = FakeSessionApi(identity: identity);
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Home'), findsOneWidget);

    // The switch: the app still holds a principal, the backend rejects it.
    identity.invalidateCurrentToken();

    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    expect(find.text('Study Tutor'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
    // skipOffstage: false so this fails if Home is merely covered by a
    // pushed sign-in route instead of removed from the stack (a plain push
    // keeps it offstage in the tree, which the default finder skips).
    expect(find.text('Home', skipOffstage: false), findsNothing,
        reason: 'the stack is cleared — no back route into the app');

    // Recovery: re-signing in yields a valid credential again — the
    // Unauthenticated → sign-in → retry loop must not dead-end.
    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Home'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();
    expect(find.text('Session'), findsOneWidget,
        reason: 'after re-auth the app is usable, not looping to sign-in');
  });

  testWidgets('invalidated token on a turn → routed back to sign-in',
      (tester) async {
    final identity = FakeIdentityProvider();
    final sessionApi = FakeSessionApi(identity: identity);
    await tester.pumpWidget(
        StudyTutorApp(identity: identity, sessionApi: sessionApi));

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Start new session'));
    await tester.pumpAndSettle();

    identity.invalidateCurrentToken();

    await tester.enterText(find.byType(TextField), 'hello?');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);
    expect(find.text('Session', skipOffstage: false), findsNothing,
        reason: 'stack cleared — the session route is gone, not covered');
  });
}
