/// KeycloakIdentityProvider — real OIDC adapter behind the unchanged IdentityProvider port.
///
/// Implements the 3-member IdentityProvider port with:
/// - Silent-then-interactive sign-in flow (PKCE S256)
/// - Proactive background refresh
/// - Sign-out wins over in-flight refresh (generation-based)
/// - Unrecoverable refresh degrades gracefully
///
/// Design ref: KC-D7 / KC-D4
library;

import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter_appauth/flutter_appauth.dart';
import '../config/keycloak_config.dart';
import '../domain/principal.dart';
import '../ports/identity_provider.dart';
import 'secure_session_store.dart';

/// Sign-in cancelled by user (browser dismissed).
class SignInCancelled implements Exception {
  const SignInCancelled(this.message);
  final String message;

  @override
  String toString() => 'SignInCancelled: $message';
}

/// Sign-in failed (discovery/IdP/transport error).
class SignInFailed implements Exception {
  const SignInFailed(this.message, [this.cause]);
  final String message;
  final Object? cause;

  @override
  String toString() =>
      'SignInFailed: $message${cause != null ? ' (cause: $cause)' : ''}';
}

/// KeycloakIdentityProvider implementing the IdentityProvider port.
class KeycloakIdentityProvider implements IdentityProvider {
  KeycloakIdentityProvider(this._config, this._appAuth, this._store);

  final KeycloakConfig _config;
  final FlutterAppAuth _appAuth;
  final SecureSessionStore _store;

  Principal? _currentPrincipal;
  Future<Principal>? _signInInFlight;
  Timer? _refreshTimer;
  int _generation = 0;

  @override
  Principal? get currentPrincipal => _currentPrincipal;

  /// Expose config for composition seam tests (KC-D7).
  KeycloakConfig get config => _config;

  @override
  Future<Principal> signIn() {
    // Single-flight guard: return in-flight Future if one exists
    if (_signInInFlight != null) {
      return _signInInFlight!;
    }

    // whenComplete is folded into the returned future: a discarded derived
    // future would re-raise sign-in errors as uncaught zone errors even
    // though the caller catches them on the original.
    final future = _performSignIn().whenComplete(() {
      _signInInFlight = null;
    });
    _signInInFlight = future;

    return future;
  }

  Future<Principal> _performSignIn() async {
    // Silent-then-interactive (KC-D7): ALWAYS try the stored refresh token
    // before any browser. Access-token expiry is deliberately NOT checked —
    // an expired access token with a live refresh token is the normal
    // >5-minute-idle case the silent path exists for (KC-G3 idle-refresh).
    final storedSession = await _store.read();
    if (storedSession != null && storedSession.refreshToken.isNotEmpty) {
      try {
        final principal = await _silentRefresh(storedSession.refreshToken);
        return principal;
      } catch (e) {
        // Silent refresh failed, fall through to interactive
      }
    }

    // Interactive flow
    return await _interactiveSignIn();
  }

  Future<Principal> _silentRefresh(String refreshToken) async {
    final currentGeneration = _generation;
    try {
      final response = await _appAuth.token(
        TokenRequest(
          _config.clientId,
          _config.redirectUrl,
          refreshToken: refreshToken,
          issuer: _config.issuer,
          scopes: _config.scopes,
        ),
      );

      return await _handleTokenResponse(response, currentGeneration);
    } on FlutterAppAuthPlatformException catch (e) {
      throw SignInFailed('Silent refresh failed', e);
    }
  }

  Future<Principal> _interactiveSignIn() async {
    final currentGeneration = _generation;
    try {
      // No promptValues:['login']. Sign-out is local-only (ASSUM-004), so a
      // surviving Keycloak SSO session is reused silently here instead of being
      // forced through a re-auth prompt — which on mobile Chrome lands on a
      // stock-theme "re-authenticate" page whose Sign In button never enables
      // (KC-G3 finding). Accepted tradeoff (2026-07-20, personal-device model):
      // after a LOCAL sign-out the next sign-in resumes silently, without
      // credentials, until the 30-min IdP idle timeout. Revisit when the planned
      // custom login theme lands (re-enable prompt=login) or if shared-device use
      // grows (full RP-initiated logout on sign-out).
      final response = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          _config.clientId,
          _config.redirectUrl,
          issuer: _config.issuer,
          scopes: _config.scopes,
        ),
      );

      return await _handleTokenResponse(response, currentGeneration);
    } on FlutterAppAuthUserCancelledException {
      // flutter_appauth 8.x: user cancel is a SIBLING of the platform
      // exception (both extend PlatformException directly) — it must be
      // caught explicitly or a real cancel escapes the SignInCancelled fence.
      throw SignInCancelled('User cancelled sign-in');
    } on FlutterAppAuthPlatformException catch (e) {
      if (_isCancelError(e)) {
        // Belt-and-braces: some platform variants surface cancel as a plain
        // platform exception carrying a CANCEL code.
        throw SignInCancelled('User cancelled sign-in');
      } else {
        throw SignInFailed('Interactive sign-in failed: ${e.message}', e);
      }
    }
  }

  bool _isCancelError(FlutterAppAuthPlatformException e) {
    final code = e.code.toUpperCase();
    return code.contains('CANCEL') ||
        code.contains('USER_CANCEL') ||
        code == 'CANCELED';
  }

  Future<Principal> _handleTokenResponse(
    TokenResponse response,
    int expectedGeneration,
  ) async {
    final displayName = _extractDisplayName(response.idToken);
    final accessToken = response.accessToken;
    final refreshToken = response.refreshToken;
    final expiry = response.accessTokenExpirationDateTime;

    if (accessToken == null || accessToken.isEmpty) {
      throw SignInFailed('Access token is missing');
    }

    final principal = Principal(token: accessToken, displayName: displayName);

    // signOut-wins fence: persist AND publish only when no generation bump
    // happened during the async exchange — an unconditional write here would
    // resurrect the session signOut just cleared (family device). The write
    // itself awaits, so re-check afterwards and compensate if signOut landed
    // mid-write.
    if (_generation == expectedGeneration) {
      await _store.write(
        StoredSession(
          refreshToken: refreshToken ?? '',
          accessToken: accessToken,
          accessTokenExpiry:
              expiry ?? DateTime.now().add(const Duration(hours: 1)),
          displayName: displayName,
        ),
      );
      if (_generation == expectedGeneration) {
        _currentPrincipal = principal;
        _scheduleProactiveRefresh(refreshToken ?? '', expiry);
      } else {
        await _store.clear();
      }
    }

    return principal;
  }

  String _extractDisplayName(String? idToken) {
    if (idToken == null) return 'User';

    try {
      final parts = idToken.split('.');
      if (parts.length < 2) return 'User';

      final payload = parts[1];
      final normalized = base64.normalize(payload);
      final decoded = utf8.decode(base64.decode(normalized));
      final json = jsonDecode(decoded) as Map<String, dynamic>;

      return json['name'] as String? ??
          json['preferred_username'] as String? ??
          'User';
    } catch (e) {
      return 'User';
    }
  }

  /// Proactive-refresh lead cap and delay floor.
  ///
  /// A fixed 5-minute lead on a ~5-minute access token (Keycloak's default
  /// 300 s) computes a near-zero delay: the timer fires immediately, the
  /// refreshed token again has ~5 min of life, and it reschedules at ~0 —
  /// a refresh hot-loop (KC-G3 observed ~10/s). [_minRefreshDelay] floors the
  /// delay so a short-lived token can never busy-loop; [_refreshLeadCap] is the
  /// normal lead for longer-lived tokens.
  static const Duration _refreshLeadCap = Duration(minutes: 5);
  static const Duration _minRefreshDelay = Duration(seconds: 30);

  /// Delay before the next proactive refresh for a token expiring
  /// [timeUntilExpiry] from now. Leads expiry by up to [_refreshLeadCap], but
  /// never by more than half the token's remaining life, and never returns less
  /// than [_minRefreshDelay]. Pure and static so the scheduling policy is unit-
  /// testable without timers.
  static Duration computeRefreshDelay(Duration timeUntilExpiry) {
    final seconds = timeUntilExpiry.inSeconds;
    final leadSeconds = seconds <= 0 ? 0 : min(_refreshLeadCap.inSeconds, seconds ~/ 2);
    final delay = timeUntilExpiry - Duration(seconds: leadSeconds);
    return delay < _minRefreshDelay ? _minRefreshDelay : delay;
  }

  void _scheduleProactiveRefresh(String refreshToken, DateTime? expiry) {
    _refreshTimer?.cancel();

    if (expiry == null) return;

    final delay = computeRefreshDelay(expiry.difference(DateTime.now()));

    _refreshTimer = Timer(delay, () {
      _performBackgroundRefresh(refreshToken);
    });
  }

  Future<void> _performBackgroundRefresh(String refreshToken) async {
    final currentGeneration = _generation;

    TokenResponse? response;
    try {
      response = await _appAuth.token(
        TokenRequest(
          _config.clientId,
          _config.redirectUrl,
          refreshToken: refreshToken,
          issuer: _config.issuer,
          scopes: _config.scopes,
        ),
      );
    } catch (e) {
      // Unrecoverable refresh: clear principal and degrade to sign-in
      if (_generation == currentGeneration) {
        _currentPrincipal = null;
        await _store.clear();
      }
      return;
    }

    // Check generation again after async operation
    if (_generation != currentGeneration) {
      // Sign-out happened during refresh - discard the response
      return;
    }

    await _handleTokenResponse(response, currentGeneration);
  }

  @override
  Future<void> signOut() async {
    // Bump generation to win over any in-flight refresh
    _generation++;

    _refreshTimer?.cancel();
    _refreshTimer = null;
    _currentPrincipal = null;
    _signInInFlight = null;

    await _store.clear();
  }

  /// Test hook: force a refresh for testing purposes.
  Future<void> forceRefresh() async {
    final session = await _store.read();
    if (session != null) {
      await _performBackgroundRefresh(session.refreshToken);
    }
  }
}
