/// Hermetic tests for KeycloakIdentityProvider — no browser, no network, no platform channel.
///
/// Covers: silent refresh, interactive flow, cancel/failure distinction, single-flight,
/// proactive refresh, sign-out race, unrecoverable refresh, launch scenarios.
///
/// Includes seam tests for STORED_SESSION and SIGNIN_OUTCOME contracts.
library;

import 'package:fake_async/fake_async.dart';
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

    test('expired access token still refreshes silently (no browser)',
        () async {
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

      expect(appauth.tokenRefreshCalls, 1,
          reason: 'an expired access token with a live refresh token is the '
              'normal >5-min-idle case — silent refresh, not a browser '
              '(KC-G3 idle-refresh gate)');
      expect(appauth.interactiveCalls, 0);
    });

    test('stored session without a refresh token goes interactive', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: '',
          accessToken: 'a0',
          expiry: DateTime.now().add(const Duration(minutes: 30)),
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      expect(appauth.tokenRefreshCalls, 0);
      expect(appauth.interactiveCalls, 1);
    });

    test('interactive sign-in does NOT force a re-auth prompt (KC-G3 decision)',
        () async {
      // Dropping promptValues:['login'] lets a surviving SSO session resume
      // silently instead of hitting the stock-theme re-auth page that disables
      // Sign In on mobile Chrome (2026-07-20; personal-device tradeoff).
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore();
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn();

      expect(appauth.interactiveCalls, 1);
      expect(appauth.lastInteractivePromptValues, isNull,
          reason: 'must not force prompt=login — avoids the broken re-auth page');
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

  group('computeRefreshDelay (KC-G3 hot-loop fix)', () {
    test('a ~5-min access token schedules a floored delay, not ~zero', () {
      final delay = KeycloakIdentityProvider.computeRefreshDelay(
          const Duration(minutes: 5));
      expect(delay, greaterThanOrEqualTo(const Duration(seconds: 30)),
          reason: 'the 300s token that drove the ~10/s hot-loop must now '
              'schedule well above zero');
      expect(delay, lessThan(const Duration(minutes: 5)),
          reason: 'still refreshes before expiry');
    });

    test('never returns less than the 30s floor (tiny/expired tokens)', () {
      for (final s in [0, 5, 40, 60, 300]) {
        expect(
            KeycloakIdentityProvider.computeRefreshDelay(Duration(seconds: s)),
            greaterThanOrEqualTo(const Duration(seconds: 30)),
            reason: 'floor guards the busy-loop for lifetime=${s}s');
      }
      expect(
          KeycloakIdentityProvider.computeRefreshDelay(
              const Duration(seconds: -10)),
          greaterThanOrEqualTo(const Duration(seconds: 30)),
          reason: 'an already-expired token must not busy-loop either');
    });

    test('a normal-length token keeps the ~5-min-before-expiry lead', () {
      expect(
          KeycloakIdentityProvider.computeRefreshDelay(const Duration(hours: 1)),
          const Duration(minutes: 55));
    });
  });

  group('proactive refresh', () {
    test('does not hot-loop on a short-lived (~5-min) token', () async {
      final appauth = FakeAppAuth()
        // Mirrors Keycloak's real 300s access-token lifetime — the config that
        // produced the ~10/s refresh flood before the floor was added.
        ..tokenLifetime = const Duration(minutes: 5);
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: DateTime.now().add(const Duration(minutes: 30)),
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      await idp.signIn(); // silent refresh #1 schedules the proactive timer
      expect(appauth.tokenRefreshCalls, 1);

      await Future.delayed(const Duration(milliseconds: 900));

      // Pre-fix this window saw dozens of refreshes (delay ~0). The floored
      // delay (~150s for a 300s token) must fire NONE within 900 ms.
      expect(appauth.tokenRefreshCalls, 1,
          reason: 'floored proactive delay must not busy-loop (KC-G3 fix)');
      expect(idp.currentPrincipal, isNotNull);
    });

    test('proactive timer still fires a refresh before expiry', () {
      // fake_async drives virtual time so we can advance past the floored delay
      // (~150s for a 300s token) without a real wall-clock wait.
      fakeAsync((async) {
        final appauth = FakeAppAuth()..tokenLifetime = const Duration(minutes: 5);
        final store = FakeSecureSessionStore()
          ..seed(
            refreshToken: 'r0',
            accessToken: 'a0',
            expiry: DateTime.now().add(const Duration(minutes: 30)),
            displayName: 'Test User',
          );
        final idp = KeycloakIdentityProvider(config, appauth, store);

        idp.signIn(); // silent refresh #1 schedules the proactive timer
        async.flushMicrotasks();
        expect(appauth.tokenRefreshCalls, 1);

        // Advance past one floored delay; the proactive timer must fire refresh #2.
        async.elapse(const Duration(seconds: 160));
        expect(appauth.tokenRefreshCalls, greaterThanOrEqualTo(2),
            reason: 'the proactive timer must still fire before expiry');
        expect(idp.currentPrincipal, isNotNull);

        idp.signOut(); // cancel the pending timer so fakeAsync drains cleanly
        async.flushMicrotasks();
      });
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

    test('unreadable stored session treated as signed out', () async {
      final appauth = FakeAppAuth();
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: DateTime.now().add(const Duration(minutes: 30)),
          displayName: 'Test User',
        )
        ..corruptData = true;
      final idp = KeycloakIdentityProvider(config, appauth, store);

      expect(idp.currentPrincipal, isNull);

      // Fail-closed: the unreadable store must behave as signed-out — signIn
      // goes interactive, never a phantom silent refresh from corrupt data.
      await idp.signIn();
      expect(appauth.tokenRefreshCalls, 0);
      expect(appauth.interactiveCalls, 1);
    });

    test('signOut during in-flight sign-in keeps the store cleared', () async {
      final appauth = FakeAppAuth()..delayTokenRefresh = true;
      final store = FakeSecureSessionStore()
        ..seed(
          refreshToken: 'r0',
          accessToken: 'a0',
          expiry: DateTime.now().add(const Duration(minutes: 30)),
          displayName: 'Test User',
        );
      final idp = KeycloakIdentityProvider(config, appauth, store);

      final inFlight = idp.signIn();
      await Future.delayed(const Duration(milliseconds: 10));
      await idp.signOut();
      try {
        await inFlight;
      } catch (_) {}

      expect(await store.read(), isNull,
          reason: 'signOut wins: the losing exchange must not resurrect '
              'the cleared session (family device)');
      expect(idp.currentPrincipal, isNull);
    });
  });
}

// Fake FlutterAppAuth for hermetic testing
class FakeAppAuth implements FlutterAppAuth {
  int interactiveCalls = 0;
  int tokenRefreshCalls = 0;

  /// promptValues on the most recent interactive authorize — lets tests assert
  /// the flow does NOT force a re-auth prompt (KC-G3 decision, 2026-07-20).
  List<String>? lastInteractivePromptValues;
  bool failNextTokenRefresh = false;
  bool failAllTokenRefreshes = false;
  bool delayTokenRefresh = false;

  /// Lifetime of tokens minted by [token] — shorten to just past the 5-minute
  /// proactive threshold to make the proactive-refresh timer fire in-test.
  Duration tokenLifetime = const Duration(hours: 1);

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
    lastInteractivePromptValues = request.promptValues;

    if (_throwsCancel) {
      // The REAL SDK type for user cancel (flutter_appauth 8.x): a SIBLING of
      // FlutterAppAuthPlatformException — the fake must throw what production
      // throws or the cancel fence test guards nothing.
      throw FlutterAppAuthUserCancelledException(
        code: 'USER_CANCELED',
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

    final expiry = DateTime.now().add(tokenLifetime);
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
