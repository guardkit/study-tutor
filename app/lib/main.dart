import 'package:flutter/material.dart';

import 'adapters/http_session_api.dart';
import 'fakes/fake_identity_provider.dart';
import 'fakes/fake_session_api.dart';
import 'ports/session_api.dart';
import 'ui/app.dart';

// Composition root: adapters are constructed HERE and only here (scope §2).

/// Compile-time flavour switch (phase-2 scope §3.3): empty — the default,
/// and what every hermetic test run sees — composes the v1 fake backend;
/// set (`--dart-define=API_BASE_URL=http://<host>:8100`), the real HTTP
/// adapter. No settings UI, no runtime switching.
const apiBaseUrl = String.fromEnvironment('API_BASE_URL');

/// The one composition rule, separated from [main] so a widget test can
/// assert it. Identity stays [FakeIdentityProvider] in BOTH flavours (port
/// untouched this phase); its constant token is the binding doc's dev-table
/// entry #1, which is what the real adapter sends as the bearer token.
SessionApi composeSessionApi(String baseUrl, FakeIdentityProvider identity) =>
    baseUrl.isEmpty
        ? FakeSessionApi(identity: identity)
        : HttpSessionApi(baseUrl: baseUrl, identity: identity);

void main() {
  final identity = FakeIdentityProvider();
  runApp(StudyTutorApp(
    identity: identity,
    sessionApi: composeSessionApi(apiBaseUrl, identity),
  ));
}
