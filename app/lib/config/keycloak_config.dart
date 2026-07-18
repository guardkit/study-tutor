/// OIDC client configuration for Keycloak authentication.
///
/// Carries the configuration surface consumed by the KeycloakIdentityProvider
/// adapter (TASK-KCA3-003). Implements the §4 OIDC_CLIENT_CONFIG contract.
///
/// Compile-time configuration (--dart-define flags):
/// - KEYCLOAK_ISSUER: OIDC discovery base URL (empty = hermetic-fake flavour)
/// - KEYCLOAK_CLIENT_ID: public client identifier (default: 'study-tutor-app')
///
/// Frozen constants (ASSUM-003 - byte-identical across Keycloak, Android, iOS):
/// - redirectUrl: 'com.appmilla.studytutor:/oauth2redirect'
/// - scopes: ['openid', 'offline_access']
class KeycloakConfig {
  /// OIDC discovery base URL.
  ///
  /// Examples:
  /// - Production: https://keycloak.example.com/realms/study-tutor
  /// - Empty string: hermetic-fake flavour (no Keycloak)
  final String issuer;

  /// OIDC public client identifier.
  ///
  /// Default: 'study-tutor-app' (matches Keycloak realm-as-code in FEAT-AUTH-001)
  final String clientId;

  /// OAuth2 redirect URI - frozen constant per ASSUM-003.
  ///
  /// MUST be byte-identical in:
  /// - Keycloak study-tutor-app client Valid Redirect URIs
  /// - Android manifest appAuthRedirectScheme
  /// - iOS Info.plist CFBundleURLSchemes
  ///
  /// Value: 'com.appmilla.studytutor:/oauth2redirect'
  final String redirectUrl;

  /// OIDC scopes - frozen constant.
  ///
  /// - openid: required for OIDC
  /// - offline_access: required for refresh tokens
  final List<String> scopes;

  /// Constructs a KeycloakConfig.
  ///
  /// [issuer] is required; empty string indicates hermetic-fake flavour.
  /// [clientId] defaults to 'study-tutor-app'.
  /// [redirectUrl] and [scopes] are frozen constants (cannot be overridden).
  const KeycloakConfig({
    required this.issuer,
    this.clientId = 'study-tutor-app',
  })  : redirectUrl = 'com.appmilla.studytutor:/oauth2redirect',
        scopes = const ['openid', 'offline_access'];

  /// Constructs a KeycloakConfig from compile-time environment variables.
  ///
  /// Reads:
  /// - KEYCLOAK_ISSUER (default: empty string = hermetic-fake)
  /// - KEYCLOAK_CLIENT_ID (default: 'study-tutor-app')
  ///
  /// Example:
  /// ```dart
  /// final config = KeycloakConfig.fromEnvironment(Platform.environment);
  /// ```
  ///
  /// Or for testing:
  /// ```dart
  /// final config = KeycloakConfig.fromEnvironment({
  ///   'KEYCLOAK_ISSUER': 'https://keycloak.example.com/realms/study-tutor',
  /// });
  /// ```
  factory KeycloakConfig.fromEnvironment(Map<String, String> environment) {
    return KeycloakConfig(
      issuer: environment['KEYCLOAK_ISSUER'] ?? '',
      clientId: environment['KEYCLOAK_CLIENT_ID'] ?? 'study-tutor-app',
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is KeycloakConfig &&
          runtimeType == other.runtimeType &&
          issuer == other.issuer &&
          clientId == other.clientId &&
          redirectUrl == other.redirectUrl &&
          _listEquals(scopes, other.scopes);

  @override
  int get hashCode =>
      issuer.hashCode ^
      clientId.hashCode ^
      redirectUrl.hashCode ^
      _listHashCode(scopes);

  @override
  String toString() {
    return 'KeycloakConfig('
        'issuer: $issuer, '
        'clientId: $clientId, '
        'redirectUrl: $redirectUrl, '
        'scopes: $scopes)';
  }

  /// Helper for list equality comparison.
  bool _listEquals(List<String> a, List<String> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  /// Helper for list hash code.
  int _listHashCode(List<String> list) {
    int hash = 0;
    for (final item in list) {
      hash ^= item.hashCode;
    }
    return hash;
  }
}
