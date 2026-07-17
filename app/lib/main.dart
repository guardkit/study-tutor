import 'package:flutter/material.dart';
import 'package:flutter_appauth/flutter_appauth.dart';

import 'adapters/http_session_api.dart';
import 'adapters/http_student_model_api.dart';
import 'adapters/http_voice_api.dart';
import 'adapters/keycloak_identity_provider.dart';
import 'adapters/secure_session_store.dart';
import 'config/keycloak_config.dart';
import 'fakes/fake_identity_provider.dart';
import 'fakes/fake_session_api.dart';
import 'fakes/fake_student_model_api.dart';
import 'fakes/fake_voice_api.dart';
import 'ports/identity_provider.dart';
import 'ports/session_api.dart';
import 'ports/student_model_api.dart';
import 'ports/voice_api.dart';
import 'ui/app.dart';

// Composition root: adapters are constructed HERE and only here (scope §2).

/// Compile-time flavour switch (phase-2 scope §3.3): empty — the default,
/// and what every hermetic test run sees — composes the v1 fake backend;
/// set (`--dart-define=API_BASE_URL=http://<host>:8100`), the real HTTP
/// adapter. No settings UI, no runtime switching.
const apiBaseUrl = String.fromEnvironment('API_BASE_URL');

/// KC-D7 flavour key: empty issuer (default) → hermetic-fake flavour with
/// concrete FakeIdentityProvider; set issuer → keycloak flavour with
/// KeycloakIdentityProvider. Replaces API_BASE_URL as the flavour switch.
const keycloakIssuer = String.fromEnvironment('KEYCLOAK_ISSUER');
const keycloakClientId =
    String.fromEnvironment('KEYCLOAK_CLIENT_ID', defaultValue: 'study-tutor-app');

/// KC-D7: compose the identity adapter by flavour. Empty issuer (default) →
/// concrete FakeIdentityProvider for the hermetic flavour; set issuer →
/// KeycloakIdentityProvider with OIDC config. Separated from [main] so tests
/// can assert the flavour selection.
IdentityProvider composeIdentity({String? keycloakIssuer}) {
  final issuer = keycloakIssuer ?? const String.fromEnvironment('KEYCLOAK_ISSUER');
  if (issuer.isEmpty) {
    // Hermetic-fake flavour: concrete FakeIdentityProvider for studentIdForToken
    return FakeIdentityProvider();
  } else {
    // Keycloak flavour: real OIDC adapter
    final config = KeycloakConfig(
      issuer: issuer,
      clientId: keycloakClientId,
    );
    return KeycloakIdentityProvider(
      config,
      FlutterAppAuth(),
      SecureSessionStore(),
    );
  }
}

/// The composition rules, de-typed to accept the [IdentityProvider] port
/// (KC-D7). The hermetic flavour composes fakes; the set-baseUrl flavour
/// composes HTTP adapters. FakeSessionApi still needs the concrete
/// FakeIdentityProvider for its studentIdForToken introspection hook, so
/// the fake flavour must pass the concrete type where the port expects it.
SessionApi composeSessionApi(String baseUrl, IdentityProvider identity) {
  if (baseUrl.isEmpty) {
    // Hermetic flavour: fake backend needs concrete FakeIdentityProvider
    return FakeSessionApi(identity: identity as FakeIdentityProvider);
  } else {
    // HTTP flavour: adapter accepts the port
    return HttpSessionApi(baseUrl: baseUrl, identity: identity);
  }
}

VoiceApi composeVoiceApi(String baseUrl, IdentityProvider identity) =>
    baseUrl.isEmpty
        ? FakeVoiceApi()
        : HttpVoiceApi(baseUrl: baseUrl, identity: identity);

/// The `StudentModelApi` composition (S-A3), mirroring [composeSessionApi]:
/// the fake read on the default flavour, the HTTP adapter when a base URL is
/// set. Now accepts the [IdentityProvider] port (KC-D7).
StudentModelApi composeStudentModelApi(
    String baseUrl, IdentityProvider identity) {
  if (baseUrl.isEmpty) {
    // Hermetic flavour: fake needs concrete FakeIdentityProvider
    return FakeStudentModelApi(identity: identity as FakeIdentityProvider);
  } else {
    // HTTP flavour: adapter accepts the port
    return HttpStudentModelApi(baseUrl: baseUrl, identity: identity);
  }
}

/// KC-D7 flavour-coherence guard: the keycloak flavour needs the real
/// backend. KEYCLOAK_ISSUER set with API_BASE_URL empty would hand the real
/// adapter to the fake composers (`identity as FakeIdentityProvider`) and
/// crash obscurely at boot — fail fast with an actionable message instead.
void assertFlavourCoherence({required String issuer, required String baseUrl}) {
  if (issuer.isNotEmpty && baseUrl.isEmpty) {
    throw StateError(
      'KEYCLOAK_ISSUER is set but API_BASE_URL is empty: the keycloak '
      'flavour requires the real backend. Pass --dart-define=API_BASE_URL=… '
      'or unset KEYCLOAK_ISSUER for the hermetic-fake flavour.',
    );
  }
}

void main() {
  // KC-D7: flavour selection keys on KEYCLOAK_ISSUER (empty → fake, set → real)
  assertFlavourCoherence(issuer: keycloakIssuer, baseUrl: apiBaseUrl);
  final identity = composeIdentity();
  runApp(StudyTutorApp(
    identity: identity,
    sessionApi: composeSessionApi(apiBaseUrl, identity),
    voiceApi: composeVoiceApi(apiBaseUrl, identity),
    studentModelApi: composeStudentModelApi(apiBaseUrl, identity),
  ));
}
