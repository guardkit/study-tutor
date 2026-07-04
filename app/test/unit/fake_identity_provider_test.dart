// Wave-2 unit tests: sign-in yields a principal; both principals and token
// invalidation are usable from tests (scope §2.2; contract §3 derivation).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/identity_provider.dart';

void main() {
  group('sign-in / sign-out', () {
    test('signIn yields the default principal (Lilymay) and sets current', () async {
      final idp = FakeIdentityProvider();
      expect(idp.currentPrincipal, isNull);

      final principal = await idp.signIn();

      expect(principal, FakeIdentityProvider.lilymay);
      expect(idp.currentPrincipal, FakeIdentityProvider.lilymay);
    });

    test('signOut clears the current principal', () async {
      final idp = FakeIdentityProvider();
      await idp.signIn();
      await idp.signOut();
      expect(idp.currentPrincipal, isNull);
    });

    test('fake satisfies the IdentityProvider port', () {
      expect(FakeIdentityProvider(), isA<IdentityProvider>());
    });
  });

  group('second principal (ownership tests need it)', () {
    test('signInAs switches to the second student', () async {
      final idp = FakeIdentityProvider();
      final principal = await idp.signInAs(FakeIdentityProvider.secondStudent);
      expect(principal, FakeIdentityProvider.secondStudent);
      expect(idp.currentPrincipal, FakeIdentityProvider.secondStudent);
    });

    test('the two principals map to distinct student ids', () {
      final idp = FakeIdentityProvider();
      final a = idp.studentIdForToken(FakeIdentityProvider.lilymay.token);
      final b = idp.studentIdForToken(FakeIdentityProvider.secondStudent.token);
      expect(a, isNotNull);
      expect(b, isNotNull);
      expect(a, isNot(b));
    });
  });

  group('token → student_id derivation (§3)', () {
    test('valid token derives a student id', () {
      final idp = FakeIdentityProvider();
      expect(idp.studentIdForToken('token-lilymay'), 'lilymay');
    });

    test('unknown token derives nothing', () {
      final idp = FakeIdentityProvider();
      expect(idp.studentIdForToken('token-nobody'), isNull);
    });

    test('null token (signed out) derives nothing', () {
      final idp = FakeIdentityProvider();
      expect(idp.studentIdForToken(idp.currentPrincipal?.token), isNull);
    });
  });

  group('invalidate-token switch', () {
    test('invalidated token becomes undetectable as a student, '
        'while the client-side principal stays set (stale token)', () async {
      final idp = FakeIdentityProvider();
      final principal = await idp.signIn();
      expect(idp.studentIdForToken(principal.token), 'lilymay');

      idp.invalidateCurrentToken();

      expect(idp.studentIdForToken(principal.token), isNull,
          reason: 'backend introspection must reject the token');
      expect(idp.currentPrincipal, principal,
          reason: 'the app still thinks it is signed in — that is the point');
    });

    test('invalidation only hits the invalidated token, not the other student',
        () async {
      final idp = FakeIdentityProvider();
      await idp.signIn();
      idp.invalidateCurrentToken();
      expect(
        idp.studentIdForToken(FakeIdentityProvider.secondStudent.token),
        'alex',
      );
    });

    test('invalidating while signed out is a no-op', () {
      final idp = FakeIdentityProvider();
      idp.invalidateCurrentToken();
      expect(idp.studentIdForToken('token-lilymay'), 'lilymay');
    });
  });
}
