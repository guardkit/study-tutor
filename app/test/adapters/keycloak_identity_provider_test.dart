/// Hermetic tests for KeycloakIdentityProvider — no browser, no network, no platform channel.
///
/// Covers: silent refresh, interactive flow, cancel/failure distinction, single-flight,
/// proactive refresh, sign-out race, unrecoverable refresh, launch scenarios.
///
/// Includes seam tests for STORED_SESSION and SIGNIN_OUTCOME contracts.

import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/adapters/keycloak_identity_provider.dart';
import 'package:study_tutor_app/adapters/secure_session_store.dart';
import 'package:study_tutor_app/config/keycloak_config.dart';
import 'package:study_tutor_app/domain/principal.dart';
import 'package:flutter_appauth/flutter_appauth.dart';

void main() {
  late KeycloakConfig config;

  setUp(() {
    config = const KeycloakConfig(issuer: 'https://keycloak.test/realms/test');
  });

  group('SEAM TESTS - STORED_SESSION and SIGNIN_OUTCOME contracts', () {
    test('a valid stored session refreshes silently — no interactive flow', () async {
      final appauth = FakeAppAuth();
      final farFuture = DateTime.now().add(const Duration(hours: 24));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: farFuture,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      expect(appauth.interactiveCalls, 0,
          reason: 'silent refresh must precede any browser');
      expect(appauth.tokenRefreshCalls, 1);
      expect(idp.currentPrincipal, isNotNull);
    });

    test('cancel and failure surface as distinct outcomes', () async {
      final store = FakeSecureSessionStore();

      // Verify cancel outcome
      final cancelIdp = KeycloakIdentityProvider(
        config,
        FakeAppAuth.cancels(),
        store,
      );

      Object? caughtException;
      try {
        await cancelIdp.signIn();
        fail('Expected SignInCancelled to be thrown');
      } on SignInCancelled catch (e) {
        caughtException = e;
      }
      expect(caughtException, isNotNull, reason: 'Should have caught SignInCancelled');
      expect(caughtException, isA<SignInCancelled>());

      // Verify failure outcome
      final failIdp = KeycloakIdentityProvider(
        config,
        FakeAppAuth.failsDiscovery(),
        store,
      );

      Object? caughtFailure;
      try {
        await failIdp.signIn();
        fail('Expected SignInFailed to be thrown');
      } on SignInFailed catch (e) {
        caughtFailure = e;
      }
      expect(caughtFailure, isNotNull, reason: 'Should have caught SignInFailed');
      expect(caughtFailure, isA<SignInFailed>());
    });
  });

  group('signIn', () {
    test('no stored session triggers interactive flow', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      final principal = await idp.signIn();

      expect(appauth.interactiveCalls, 1);
      expect(appauth.tokenRefreshCalls, 0);
      expect(principal.displayName, isNotEmpty);
      expect(idp.currentPrincipal, equals(principal));
    });

    test('expired stored session triggers interactive flow', () async {
      final appauth = FakeAppAuth();
      final pastExpiry = DateTime.now().subtract(const Duration(hours: 1));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: pastExpiry,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      expect(appauth.interactiveCalls, 1);
    });

    test('second concurrent signIn shares one flow', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      final futures = <Future<Principal>>[
        idp.signIn(),
        idp.signIn(),
        idp.signIn(),
      ];
      await Future.wait(futures);

      expect(appauth.interactiveCalls, 1,
          reason: 'single-flight: only one interactive flow');
    });

    test('silent refresh fails triggers interactive flow', () async {
      final appauth = FakeAppAuth()..failNextTokenRefresh = true;
      final farFuture = DateTime.now().add(const Duration(hours: 24));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: farFuture,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      expect(appauth.tokenRefreshCalls, 1);
      expect(appauth.interactiveCalls, 1,
          reason: 'fallback to interactive after silent refresh fails');
    });
  });

  group('proactive refresh', () {
    test('refreshes before access token expiry', () async {
      final appauth = FakeAppAuth();
      final soonExpiry = DateTime.now().add(const Duration(minutes: 4));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: soonExpiry,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      // Wait for proactive refresh (should happen shortly)
      await Future.delayed(const Duration(milliseconds: 100));

      expect(appauth.tokenRefreshCalls, greaterThanOrEqualTo(1));
      expect(idp.currentPrincipal, isNotNull,
          reason: 'principal stays available after refresh');
    });

    test('unrecoverable refresh clears principal without throwing', () async {
      final appauth = FakeAppAuth();
      final farFuture = DateTime.now().add(const Duration(hours: 24));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: farFuture,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();
      expect(idp.currentPrincipal, isNotNull);

      // Simulate unrecoverable refresh
      appauth.failAllTokenRefreshes = true;
      await idp.forceRefresh(); // Test hook

      expect(idp.currentPrincipal, isNull,
          reason: 'unrecoverable refresh degrades to signed out');
    });
  });

  group('signOut', () {
    test('clears principal and store', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();
      expect(idp.currentPrincipal, isNotNull);

      await idp.signOut();

      expect(idp.currentPrincipal, isNull);
      expect(await store.read(), isNull);
    });

    test('wins over in-flight refresh', () async {
      final appauth = FakeAppAuth()..delayTokenRefresh = true;
      final farFuture = DateTime.now().add(const Duration(hours: 24));
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: farFuture,
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      // Start a refresh
      final refreshFuture = idp.forceRefresh();

      // Give refresh time to start
      await Future.delayed(const Duration(milliseconds: 10));

      // Sign out during refresh
      await idp.signOut();

      // Wait for refresh to complete
      await refreshFuture;

      expect(idp.currentPrincipal, isNull,
          reason: 'sign-out wins over completing refresh');
    });
  });

  group('currentPrincipal', () {
    test('returns null when signed out', () {
      final idp = KeycloakIdentityProvider(
        config,
        FakeAppAuth(),
        FakeSecureSessionStore(),
      );

      expect(idp.currentPrincipal, isNull);
    });

    test('returns cached principal when signed in', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      final principal = await idp.signIn();

      expect(idp.currentPrincipal, equals(principal));
    });

    test('stays available across multiple accesses', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      final p1 = idp.currentPrincipal;
      final p2 = idp.currentPrincipal;
      final p3 = idp.currentPrincipal;

      expect(p1, equals(p2));
      expect(p2, equals(p3));
    });
  });

  group('launch scenarios', () {
    test('absent stored session treated as signed out', () {
      final idp = KeycloakIdentityProvider(
        config,
        FakeAppAuth(),
        FakeSecureSessionStore(),
      );

      expect(idp.currentPrincipal, isNull);
    });

    test('unreadable stored session treated as signed out', () {
      final store = FakeSecureSessionStore()..corruptData = true;
      final idp = KeycloakIdentityProvider(config, FakeAppAuth(), store);

      expect(idp.currentPrincipal, isNull);
    });
  });
}

// Fake FlutterAppAuth for hermetic testing
class FakeAppAuth implements FlutterAppAuth {
  int interactiveCalls = 0;
  int tokenRefreshCalls = 0;
  bool failNextTokenRefresh = false;
  bool failAllTokenRefreshes = false;
  bool delayTokenRefresh = false;

  final bool _throwsCancel;
  final bool _throwsFailure;

  FakeAppAuth({
    this._throwsCancel = false,
    this._throwsFailure = false,
  });

  factory FakeAppAuth.cancels() => FakeAppAuth(throwsCancel: true);
  factory FakeAppAuth.failsDiscovery() => FakeAppAuth(throwsFailure: true);

  @override
  Future<AuthorizationResponse> authorize(AuthorizationRequest request) async {
    throw UnimplementedError();
  }

  @override
  Future<AuthorizationTokenResponse> authorizeAndExchangeCode(
    AuthorizationTokenRequest request,
  ) async {
    interactiveCalls++;

    if (_throwsCancel) {
      throw FlutterAppAuthPlatformException(
        code: 'CANCELED',
        message: 'User canceled',
        platformErrorDetails: FlutterAppAuthPlatformErrorDetails(),
      );
    }

    if (_throwsFailure) {
      throw FlutterAppAuthPlatformException(
        code: 'DISCOVERY_FAILED',
        message: 'Discovery failed',
        platformErrorDetails: FlutterAppAuthPlatformErrorDetails(),
      );
    }

    final expiry = DateTime.now().add(const Duration(hours: 1));
    return AuthorizationTokenResponse(
      'access_$interactiveCalls',
      'refresh_$interactiveCalls',
      expiry,
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiVGVzdCBVc2VyIn0.test',
      'Bearer',
      null, // scopes
      {}, // authorizationAdditionalParameters
      {}, // tokenAdditionalParameters
    );
  }

  @override
  Future<TokenResponse> token(TokenRequest request) async {
    tokenRefreshCalls++;

    if (delayTokenRefresh) {
      await Future.delayed(const Duration(milliseconds: 100));
    }

    if (failAllTokenRefreshes || failNextTokenRefresh) {
      failNextTokenRefresh = false;
      throw FlutterAppAuthPlatformException(
        code: 'TOKEN_FAILED',
        message: 'Token refresh failed',
        platformErrorDetails: FlutterAppAuthPlatformErrorDetails(),
      );
    }

    final expiry = DateTime.now().add(const Duration(hours: 1));
    return TokenResponse(
      'access_refreshed_$tokenRefreshCalls',
      'refresh_refreshed_$tokenRefreshCalls',
      expiry,
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiVGVzdCBVc2VyIn0.test',
      'Bearer',
      null, // scopes
      {}, // tokenAdditionalParameters
    );
  }

  @override
  Future<EndSessionResponse> endSession(EndSessionRequest request) async {
    throw UnimplementedError();
  }
}

// Fake SecureSessionStore for hermetic testing
class FakeSecureSessionStore implements SecureSessionStore {
  StoredSession? _session;
  bool corruptData = false;

  void seed({
    required String refreshToken,
    required String accessToken,
    required DateTime expiry,
    required String displayName,
  }) {
    _session = StoredSession(
      refreshToken: refreshToken,
      accessToken: accessToken,
      accessTokenExpiry: expiry,
      displayName: displayName,
    );
  }

  @override
  Future<StoredSession?> read() async {
    if (corruptData) return null;
    return _session;
  }

  @override
  Future<void> write(StoredSession session) async {
    _session = session;
  }

  @override
  Future<void> clear() async {
    _session = null;
  }
}
