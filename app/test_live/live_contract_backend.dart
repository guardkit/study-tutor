// p2-wave-6: the live ContractBackend — the same harness abstraction the
// hermetic suite runs on (test/contract/contract_backend.dart), implemented
// over a deployed GB10 HTTP adapter in dev config. The suite bodies are
// imported unchanged from test/contract/; only this backend differs.
//
// Requires --dart-define=API_BASE_URL and MUST run with --concurrency=1
// (reset() truncates GLOBAL server state — binding §5.2). See README.md
// here for the run command. Never point this at a prod config.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:study_tutor_app/adapters/http_session_api.dart';
import 'package:study_tutor_app/domain/principal.dart';
import 'package:study_tutor_app/fakes/fake_identity_provider.dart';
import 'package:study_tutor_app/ports/identity_provider.dart';
import 'package:study_tutor_app/ports/session_api.dart';

import '../test/contract/contract_backend.dart';

const _rawApiBaseUrl = String.fromEnvironment('API_BASE_URL');

/// Normalized exactly as HttpSessionApi normalizes it, so the reset route
/// and the six verbs always agree on the request-target (a trailing slash
/// in the define must not 404 only the reset).
final _apiBaseUrl = _rawApiBaseUrl.endsWith('/')
    ? _rawApiBaseUrl.substring(0, _rawApiBaseUrl.length - 1)
    : _rawApiBaseUrl;

/// The contract authorizes turns up to a 30s hard ceiling (API-tutoring
/// SR-07; the p95 < 10s line is a budget, not a bound). A conformance
/// harness must survive contract-conforming tail latency, so the live
/// adapter gets a deadline above the ceiling — unlike the app, where 15s
/// is the product posture.
const _liveTurnDeadline = Duration(seconds: 35);

/// The one raw HTTP call this backend makes itself. Without it, a
/// blackholed host (the Tailscale-ACL-not-yet-open state wave-7 names)
/// would hang every setUp into the 5-minute test timeout instead of
/// failing fast and pointedly.
const _resetDeadline = Duration(seconds: 10);

/// Identity over the binding doc's dev token table (§5.1). The principals
/// reuse the fake IdP's constants — the binding doc is committed to those
/// exact values, so there is one source of truth in the app. Invalidation
/// swaps the token the adapter will SEND for garbage: the client still
/// holds a principal (the stale-token shape), and the server — the validity
/// authority — rejects the next call with 401.
class _DevTableIdentity implements IdentityProvider {
  Principal? _current;

  @override
  Principal? get currentPrincipal => _current;

  @override
  Future<Principal> signIn() async =>
      _current = FakeIdentityProvider.lilymay;

  Future<Principal> signInSecondStudent() async =>
      _current = FakeIdentityProvider.secondStudent;

  void invalidateCurrentToken() {
    final current = _current;
    if (current != null) {
      _current = Principal(
        token: 'garbage-${current.token}',
        displayName: current.displayName,
      );
    }
  }

  @override
  Future<void> signOut() async {
    _current = null;
  }
}

class LiveContractBackend implements ContractBackend {
  LiveContractBackend() {
    if (_apiBaseUrl.isEmpty) {
      throw StateError(
          'test_live requires --dart-define=API_BASE_URL=http://<gb10>:8100 '
          '(see test_live/README.md); it is deliberately unset in the '
          'hermetic gate, which never runs this suite.');
    }
    _api = HttpSessionApi(
      baseUrl: _apiBaseUrl,
      identity: _identity,
      turnDeadline: _liveTurnDeadline,
    );
  }

  final _identity = _DevTableIdentity();
  late final HttpSessionApi _api;

  @override
  SessionApi get api => _api;

  /// Dev table entry #1 (binding §5.1).
  @override
  String get defaultStudentId => 'lilymay';

  /// The reset route published in the binding doc (§5.2) — never a guess.
  /// Truncates session + session_turn rows server-wide, which is exactly why
  /// the run command pins --concurrency=1.
  @override
  Future<void> reset() async {
    final http.Response response;
    try {
      response = await http
          .post(Uri.parse('$_apiBaseUrl/__dev__/reset'))
          .timeout(_resetDeadline);
    } on TimeoutException {
      throw StateError(
          'dev reset got no answer from $_apiBaseUrl within '
          '${_resetDeadline.inSeconds}s — is the adapter reachable from '
          'this machine (Tailscale ACL / host route)?');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw StateError(
          'dev reset failed: HTTP ${response.statusCode} — is the adapter '
          'deployed in dev config (reset route is env-flag-gated)?');
    }
    await _identity.signOut();
  }

  @override
  Future<void> signIn() async => _identity.signIn();

  @override
  Future<void> signInSecondStudent() async =>
      _identity.signInSecondStudent();

  @override
  void invalidateCurrentToken() => _identity.invalidateCurrentToken();

  @override
  bool get hasLocalPrincipal => _identity.currentPrincipal != null;

  /// A second client object over the same server and current principal —
  /// live, this is genuinely a second HTTP client (second device).
  @override
  SessionApi secondClient() => HttpSessionApi(
        baseUrl: _apiBaseUrl,
        identity: _identity,
        turnDeadline: _liveTurnDeadline,
      );

  /// A live tutor is an LLM: replies are real, not canned — the strongest
  /// promise is a non-empty string (the exact-string pins stay on the fake).
  @override
  Matcher expectedTutorReply(int turnIndex) =>
      allOf(isA<String>(), isNotEmpty);

  /// Relative ordering only (scope §3.4): a real server clock guarantees
  /// non-decrease, not the fake tick-clock's strict advancement — at-or-after
  /// is the honest live expectation.
  @override
  Matcher advancedFrom(DateTime earlier) => predicate<DateTime>(
      (t) => !t.isBefore(earlier), 'a DateTime at or after $earlier');
}
