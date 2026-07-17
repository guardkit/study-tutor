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

  @override
  Future<Principal> signIn() {
    // Single-flight guard: return in-flight Future if one exists
    if (_signInInFlight != null) {
      return _signInInFlight!;
    }

    final future = _performSignIn();
    _signInInFlight = future;

    future.whenComplete(() {
      _signInInFlight = null;
    });

    return future;
  }

  Future<Principal> _performSignIn() async {
    // Attempt silent refresh first
    final storedSession = await _store.read();
    if (storedSession != null && !_isExpired(storedSession.accessTokenExpiry)) {
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

  bool _isExpired(DateTime expiry) {
    return DateTime.now().isAfter(expiry);
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
      final response = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          _config.clientId,
          _config.redirectUrl,
          issuer: _config.issuer,
          scopes: _config.scopes,
          promptValues: ['login'],
        ),
      );

      return await _handleTokenResponse(response, currentGeneration);
    } on FlutterAppAuthPlatformException catch (e) {
      if (_isCancelError(e)) {
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

    // Persist to secure store
    await _store.write(
      StoredSession(
        refreshToken: refreshToken ?? '',
        accessToken: accessToken,
        accessTokenExpiry:
            expiry ?? DateTime.now().add(const Duration(hours: 1)),
        displayName: displayName,
      ),
    );

    // Only update principal if generation hasn't changed (sign-out wins)
    if (_generation == expectedGeneration) {
      _currentPrincipal = principal;
      _scheduleProactiveRefresh(refreshToken ?? '', expiry);
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

  void _scheduleProactiveRefresh(String refreshToken, DateTime? expiry) {
    _refreshTimer?.cancel();

    if (expiry == null) return;

    final now = DateTime.now();
    final timeUntilExpiry = expiry.difference(now);

    // Refresh 5 minutes before expiry (or immediately if <5 min remaining)
    final refreshIn = timeUntilExpiry - const Duration(minutes: 5);
    final delay = refreshIn.isNegative ? Duration.zero : refreshIn;

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
