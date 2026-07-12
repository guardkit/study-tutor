/// HttpStudentModelApi — the real transport behind the `StudentModelApi` port.
///
/// Binding: API-session-http-binding.md §2.2 / §2.2.1, consumed at BINDING_SHA
/// `53f2fc51a35aa051c3dd899563a5cdbb7b620061` — `GET /api/student-model` under
/// `Authorization: Bearer <token>` (§3), `subject` the one required query
/// param. The binding doc is frozen: if the wire disagrees with it, that is a
/// backend/binding bug to raise, never something to adapt to silently here.
///
/// Error posture (binding §2.2 / §4): a 401 (missing/invalid token or unseeded
/// student, ASSUM-001) maps to [Unauthenticated]; a 400 (missing `subject`) is
/// a transport-level rejection with no `error_type` → [TransportError]; every
/// other non-2xx, network failure, deadline, or malformed/wrong-shape body is
/// likewise [TransportError], the client-local member.
library;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/errors.dart';
import '../domain/gamification.dart';
import '../ports/identity_provider.dart';
import '../ports/student_model_api.dart';

class HttpStudentModelApi implements StudentModelApi {
  HttpStudentModelApi({
    required String baseUrl,
    required this._identity,
    http.Client? client,
    this.readDeadline = _defaultReadDeadline,
  })  : _base = baseUrl.endsWith('/')
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl,
        _client = client ?? http.Client();

  /// A fast read (§6 semantics) — 5s, matching HttpSessionApi's read budget.
  static const _defaultReadDeadline = Duration(seconds: 5);

  final IdentityProvider _identity;
  final String _base;
  final http.Client _client;
  final Duration readDeadline;

  void close() => _client.close();

  /// Binding §3: the token is honored from the credential header ONLY. Signed
  /// out ⇒ no header ⇒ the server answers 401 → [Unauthenticated].
  Map<String, String> _headers() {
    final token = _identity.currentPrincipal?.token;
    return {if (token != null) 'authorization': 'Bearer $token'};
  }

  @override
  Future<StudentModel> fetch({required String subject}) async {
    final uri = Uri.parse('$_base/api/student-model')
        .replace(queryParameters: {'subject': subject});

    http.Response response;
    try {
      response = await _client.get(uri, headers: _headers()).timeout(readDeadline);
    } on TimeoutException {
      throw const TransportError('request deadline exceeded');
    } on http.ClientException catch (e) {
      throw TransportError('network failure: ${e.message}');
    }

    _throwWireError(response);

    try {
      final json = jsonDecode(utf8.decode(response.bodyBytes));
      return StudentModel.fromJson(json as Map<String, dynamic>);
    } on FormatException {
      throw const TransportError('malformed response body');
    } on TypeError {
      throw const TransportError('response body does not fit the §2.2 shape');
    }
  }

  /// Binding §2.2 / §4: 401 → [Unauthenticated] (the one closed-set error this
  /// read can raise); every other non-2xx is a transport-level rejection
  /// (§4.2) → [TransportError].
  void _throwWireError(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) return;

    Object? decoded;
    try {
      decoded = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      decoded = null;
    }
    final envelope = decoded is Map<String, dynamic> ? decoded : null;
    final error = envelope?['error'];
    final message = error is String ? error : 'HTTP ${response.statusCode}';

    if (response.statusCode == 401) {
      throw Unauthenticated(message);
    }
    throw TransportError('HTTP ${response.statusCode}: $message');
  }
}
