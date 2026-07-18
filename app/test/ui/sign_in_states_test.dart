/// Widget tests for SignInScreen state machine (TASK-KCA3-004).
///
/// Drives a fake IdentityProvider that produces cancel/failure/success outcomes
/// to verify loading, cancel, failure, and success states render correctly.
/// No browser, no network.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/adapters/keycloak_identity_provider.dart';
import 'package:study_tutor_app/ports/identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/fakes/fake_session_api.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ui/sign_in_screen.dart';
import 'package:study_tutor_app/ui/home_screen.dart';

/// Fake identity provider for testing different sign-in outcomes.
class FakeIdentityForTesting implements IdentityProvider {
  FakeIdentityForTesting({
    this.shouldCancel = false,
    this.shouldFail = false,
    this.failureMessage = 'Sign-in failed',
  });

  final bool shouldCancel;
  final bool shouldFail;
  final String failureMessage;

  Principal? _current;
  int signInCallCount = 0;

  @override
  Principal? get currentPrincipal => _current;

  @override
  Future<Principal> signIn() async {
    signInCallCount++;
    // Simulate async operation
    await Future<void>.delayed(const Duration(milliseconds: 10));

    if (shouldCancel) {
      throw const SignInCancelled('User cancelled sign-in');
    }
    if (shouldFail) {
      throw SignInFailed(failureMessage);
    }

    _current = const Principal(token: 'test-token', displayName: 'Test User');
    return _current!;
  }

  @override
  Future<void> signOut() async {
    _current = null;
  }

  /// Factory: creates a provider that cancels sign-in.
  factory FakeIdentityForTesting.cancels() {
    return FakeIdentityForTesting(shouldCancel: true);
  }

  /// Factory: creates a provider that fails with discovery error.
  factory FakeIdentityForTesting.failsDiscovery() {
    return FakeIdentityForTesting(
      shouldFail: true,
      failureMessage: 'Discovery document unavailable',
    );
  }

  /// Factory: creates a provider that succeeds.
  factory FakeIdentityForTesting.succeeds() {
    return FakeIdentityForTesting();
  }
}


void main() {
  group('SignInScreen state machine', () {
    testWidgets('shows loading indicator while signIn is in-flight',
        (tester) async {
      final identity = FakeIdentityForTesting.succeeds();
      final fakeIdentity = FakeIdentityProvider();
      await fakeIdentity.signIn(); // Sign in so sessionApi can authenticate
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Initial state: sign-in button present, no loading indicator
      expect(find.text('Sign in'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);

      // Tap sign-in
      await tester.tap(find.text('Sign in'));
      await tester.pump(); // Start async operation

      // During in-flight: loading indicator present, button disabled
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Complete the async operation
      await tester.pumpAndSettle();

      // After success: navigated to HomeScreen
      expect(find.byType(HomeScreen), findsOneWidget);
    });

    testWidgets('shows cancel message when SignInCancelled is thrown',
        (tester) async {
      final identity = FakeIdentityForTesting.cancels();
      final fakeIdentity = FakeIdentityProvider();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Tap sign-in
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      // Should show cancel message, NOT try-again
      expect(find.textContaining('cancelled'), findsOneWidget);
      expect(find.text('Try again'), findsNothing);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('shows failure state with Try again on SignInFailed',
        (tester) async {
      final identity = FakeIdentityForTesting(shouldFail: true);
      final fakeIdentity = FakeIdentityProvider();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Tap sign-in
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      // Should show failure state with Try again button
      expect(find.text('Try again'), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('discovery-unavailable renders failure state, not cancel',
        (tester) async {
      final identity = FakeIdentityForTesting.failsDiscovery();
      final fakeIdentity = FakeIdentityProvider();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Tap sign-in
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      // Discovery failure is FAILURE (Try again), NOT cancel
      expect(find.text('Try again'), findsOneWidget);
      expect(find.textContaining('cancelled'), findsNothing);
    });

    testWidgets('Try again button retries sign-in', (tester) async {
      final identity = FakeIdentityForTesting(shouldFail: true);
      final fakeIdentity = FakeIdentityProvider();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Initial sign-in fails
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(identity.signInCallCount, 1);

      // Tap Try again
      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      // signIn should be called again
      expect(identity.signInCallCount, 2);
    });

    testWidgets('double-tap during loading invokes signIn only once',
        (tester) async {
      final identity = FakeIdentityForTesting.succeeds();
      final fakeIdentity = FakeIdentityProvider();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      // Tap sign-in twice rapidly
      await tester.tap(find.text('Sign in'));
      await tester.pump(); // Don't settle, keep in-flight
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      // signIn should be called only once
      expect(identity.signInCallCount, 1);
    });

    testWidgets('on success navigates to HomeScreen', (tester) async {
      final identity = FakeIdentityForTesting.succeeds();
      final fakeIdentity = FakeIdentityProvider();
      await fakeIdentity.signIn(); // Sign in so sessionApi can authenticate
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: identity,
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );

      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();

      // Should navigate to HomeScreen
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(SignInScreen), findsNothing);
    });
  });

  // Seam test from task specification (adapted to real constructor shape)
  group('SIGNIN_OUTCOME seam test', () {
    testWidgets('cancel and failure render distinct states', (tester) async {
      final fakeIdentity = FakeIdentityProvider();

      // Test cancel state
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: FakeIdentityForTesting.cancels(),
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(find.textContaining('cancelled'), findsOneWidget);
      expect(find.text('Try again'), findsNothing);

      // Test failure state
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            identity: FakeIdentityForTesting.failsDiscovery(),
            sessionApi: FakeSessionApi(identity: fakeIdentity),
            voiceApi: FakeVoiceApi(),
          ),
        ),
      );
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(find.text('Try again'), findsOneWidget);
      expect(find.textContaining('cancelled'), findsNothing);
    });
  });
}
