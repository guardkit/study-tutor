// Sign-out affordance widget test — covers AC-001 through AC-006 per TASK-KCA3-005.
//
// Validates that the HomeScreen exposes a sign-out action (app-bar overflow menu),
// tapping it calls identity.signOut() then routeToSignIn(...), clearing the
// navigation stack and landing on SignInScreen with currentPrincipal null.
// Uses FakeIdentityProvider — no Keycloak adapter dependency.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/home_screen.dart';
import 'package:study_tutor_app/ui/sign_in_screen.dart';

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

  Widget makeApp() {
    return MaterialApp(
      home: HomeScreen(
        identity: identity,
        sessionApi: sessionApi,
        voiceApi: voiceApi,
      ),
    );
  }

  group('Sign-out affordance', () {
    testWidgets('AC-001: HomeScreen exposes sign-out action in app bar', (
      tester,
    ) async {
      await tester.pumpWidget(makeApp());
      await tester.pumpAndSettle();

      // The overflow menu button should be present
      final overflowButton = find.byType(PopupMenuButton<String>);
      expect(overflowButton, findsOneWidget, reason: 'app bar should have overflow menu');

      // Tap to open the menu
      await tester.tap(overflowButton);
      await tester.pumpAndSettle();

      // Sign out menu item should be present
      expect(find.text('Sign out'), findsOneWidget, reason: 'overflow menu should contain Sign out action');
    });

    testWidgets('AC-002, AC-003: Tapping sign-out calls identity.signOut() and routes to SignInScreen', (
      tester,
    ) async {
      await tester.pumpWidget(makeApp());
      await tester.pumpAndSettle();

      // Verify signed in initially
      expect(identity.currentPrincipal, isNotNull, reason: 'should be signed in initially');
      expect(identity.currentPrincipal?.displayName, equals('Lilymay'));

      // Open overflow menu
      final overflowButton = find.byType(PopupMenuButton<String>);
      await tester.tap(overflowButton);
      await tester.pumpAndSettle();

      // Tap sign out
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();

      // AC-003: currentPrincipal should be null after sign-out
      expect(identity.currentPrincipal, isNull, reason: 'identity.signOut() should clear currentPrincipal');

      // AC-002: Should have navigated to SignInScreen
      expect(find.byType(SignInScreen), findsOneWidget, reason: 'should route to SignInScreen after sign-out');

      // Verify HomeScreen is no longer in the widget tree (navigation stack cleared)
      expect(find.byType(HomeScreen), findsNothing, reason: 'navigation stack should be cleared');
    });

    testWidgets('AC-004: Sign-out is driven through IdentityProvider port (uses FakeIdentityProvider)', (
      tester,
    ) async {
      await tester.pumpWidget(makeApp());
      await tester.pumpAndSettle();

      // This test inherently validates AC-004 by using FakeIdentityProvider
      // The fact that we can test sign-out without a Keycloak adapter proves
      // the port abstraction works correctly

      final overflowButton = find.byType(PopupMenuButton<String>);
      await tester.tap(overflowButton);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();

      // Verify the port method was effective
      expect(identity.currentPrincipal, isNull, reason: 'FakeIdentityProvider.signOut() should have been called');
      expect(find.byType(SignInScreen), findsOneWidget);
    });

    testWidgets('Sign-out clears navigation stack and returns to sign-in screen (@key-example @smoke)', (
      tester,
    ) async {
      await tester.pumpWidget(makeApp());
      await tester.pumpAndSettle();

      // Open overflow menu
      final overflowButton = find.byType(PopupMenuButton<String>);
      await tester.tap(overflowButton);
      await tester.pumpAndSettle();

      // Tap sign out
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();

      // BDD scenario: "Signing out clears the session and returns to the sign-in screen"
      expect(identity.currentPrincipal, isNull, reason: 'session should be cleared');
      expect(find.byType(SignInScreen), findsOneWidget, reason: 'should return to sign-in screen');
      expect(find.byType(HomeScreen), findsNothing, reason: 'back stack should be cleared');

      // Verify we can't navigate back to HomeScreen (stack truly cleared)
      final navigator = tester.state<NavigatorState>(find.byType(Navigator));
      expect(navigator.canPop(), isFalse, reason: 'navigation stack should be fully cleared');
    });
  });
}
