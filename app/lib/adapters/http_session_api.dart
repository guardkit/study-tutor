/// HttpSessionApi — the real transport adapter behind the `SessionApi` port.
///
/// Binding: API-session-http-binding.md (Revision 2), consumed at
/// `BINDING_SHA=53f2fc51a35aa051c3dd899563a5cdbb7b620061` (the S-R2
/// ratification commit — supersedes the phase-2 pin `6eb7b88`, per the binding
/// doc's Revision-2 re-pin note) — six verbs under
/// `Authorization: Bearer <token>` (§3), JSON shapes per contract §5, wire
/// enum values = the domain enum names. Revision 2 adds `end_session`'s
/// nullable `gamification` settlement block (§5 Rev 2). The binding doc is
/// frozen: if the wire disagrees with it, that is a backend/binding bug to
/// raise, never something to adapt to silently here.
///
/// Error posture (p2-wave-4, binding §4): a non-2xx carrying the §9 envelope
/// (`{error, error_type}`) maps 1:1 onto the typed exceptions —
/// `error_type` is the closed set's discriminator. Everything the wire can
/// do wrong OUTSIDE that envelope — network failure, deadline exceeded,
/// 400/500 (no `error_type`, binding §4.2), undecodable or wrong-shape
/// bodies — is [TransportError], the client-local member.
library;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/errors.dart';
import '../domain/gamification.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';

class HttpSessionApi implements SessionApi {
  HttpSessionApi({
    required String baseUrl,
    required this._identity,
    http.Client? client,
    this._turnDeadline = turnBudget,
    this._readDeadline = readBudget,
  })  : _base = baseUrl.endsWith('/')
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl,
        _client = client ?? http.Client();

  /// Per-request deadlines aligned to the contract budgets (plan p2-wave-4):
  /// `turn` has a p95 < 10s budget (§5) → 15s; every other verb is a
  /// fast read / ms-scale write (§6) → 5s. Constructor overrides exist for
  /// tests only: hermetic tests shrink them; the live contract suite raises
  /// `turn` above the contract's 30s hard ceiling (SR-07), which the
  /// product posture deliberately undercuts.
  ///
  /// A deadline abandons the request client-side but cannot cancel it: a
  /// timed-out `turn` may still commit on the server, so a retry can append
  /// a duplicate turn. Contract §4 tolerates this (append-only,
  /// last-writer-wins; turn_count lets a client detect the advance).
  static const turnBudget = Duration(seconds: 15);
  static const readBudget = Duration(seconds: 5);

  final String _base;
  final IdentityProvider _identity;
  final http.Client _client;
  final Duration _turnDeadline;
  final Duration _readDeadline;

  /// Release the underlying connection pool. The composed app holds one
  /// adapter for its whole lifetime and never needs this; tests and
  /// short-lived tools might.
  void close() => _client.close();

  Uri _uri(String path, [Map<String, String> query = const {}]) {
    final uri = Uri.parse('$_base$path');
    return query.isEmpty ? uri : uri.replace(queryParameters: query);
  }

  /// Binding §3: the token is honored from the credential header ONLY. When
  /// signed out no header is sent — the server answers 401 → Unauthenticated,
  /// never a client-side guess.
  Map<String, String> _headers({required bool hasJsonBody}) {
    final token = _identity.currentPrincipal?.token;
    return {
      if (hasJsonBody) 'content-type': 'application/json',
      if (token != null) 'authorization': 'Bearer $token',
    };
  }

  /// One wire exchange: deadline → network → §9 envelope → shape mapping.
  /// [map] runs inside the malformed-body guard: a 2xx whose body does not
  /// decode or does not fit the contract §5 shape is a [TransportError].
  Future<T> _send<T>(
    Duration deadline,
    Future<http.Response> Function() request,
    T Function(dynamic json) map,
  ) async {
    http.Response response;
    try {
      response = await request().timeout(deadline);
    } on TimeoutException {
      throw const TransportError('request deadline exceeded');
    } on http.ClientException catch (e) {
      // package:http wraps socket/connection failures in ClientException on
      // every platform client.
      throw TransportError('network failure: ${e.message}');
    }
    _throwWireError(response);
    try {
      return map(jsonDecode(utf8.decode(response.bodyBytes)));
    } on FormatException {
      throw const TransportError('malformed response body');
    } on TypeError {
      throw const TransportError('response body does not fit the §5 shape');
    } on ArgumentError {
      // Enum.values.byName on an out-of-enum wire value (e.g. a status this
      // app version does not know) — same posture as any other wrong shape.
      throw const TransportError('response body does not fit the §5 shape');
    }
  }

  /// Binding §4.1: non-2xx with a §9 envelope → the typed exception for its
  /// `error_type` (the closed set's discriminator; the status code is the
  /// transport dressing). Binding §4.2: 400/500 carry no `error_type` — they
  /// are transport-level, outside the closed set → [TransportError].
  void _throwWireError(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) return;

    Object? decoded;
    try {
      decoded = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      decoded = null;
    }
    final envelope = decoded is Map<String, dynamic> ? decoded : null;
    // Type-checked, never cast: a non-conforming body (nested error objects
    // from a proxy, say) must degrade, not throw a raw TypeError past the
    // sealed hierarchy.
    final error = envelope?['error'];
    final envelopeMessage = error is String ? error : null;
    final message = envelopeMessage ?? 'HTTP ${response.statusCode}';

    switch (envelope?['error_type']) {
      case 'SessionNotFoundError':
        throw SessionNotFoundError(message);
      case 'SessionEnded':
        throw SessionEnded(message);
      case 'SessionForbidden':
        throw SessionForbidden(message);
      case 'Unauthenticated':
        throw Unauthenticated(message);
    }
    throw TransportError(envelopeMessage == null
        ? 'HTTP ${response.statusCode}'
        : 'HTTP ${response.statusCode}: $envelopeMessage');
  }

  TurnEntry _turnEntry(Map<String, dynamic> json) => TurnEntry(
        role: TurnRole.values.byName(json['role'] as String),
        content: json['content'] as String,
        ts: DateTime.parse(json['ts'] as String),
      );

  List<TurnEntry> _turns(List<dynamic> json) =>
      json.map((t) => _turnEntry(t as Map<String, dynamic>)).toList();

  @override
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  }) =>
      _send(_readDeadline, () {
        return _client.post(
          _uri('/api/sessions/start'),
          headers: _headers(hasJsonBody: true),
          body: jsonEncode({
            'subject': ?subject,
            'topic': ?topic,
            'resume_if_active': resumeIfActive,
          }),
        );
      }, (json) {
        final m = json as Map<String, dynamic>;
        final turns = m['turns'] as List<dynamic>?;
        return StartSessionResult(
          sessionId: m['session_id'] as String,
          studentId: m['student_id'] as String,
          resumed: m['resumed'] as bool,
          turns: turns == null ? null : _turns(turns),
        );
      });

  @override
  Future<List<SessionSummary>> listSessions({
    SessionStatus? status,
    int? limit,
  }) =>
      _send(_readDeadline, () {
        return _client.get(
          _uri('/api/sessions', {
            if (status != null) 'status': status.name,
            if (limit != null) 'limit': '$limit',
          }),
          headers: _headers(hasJsonBody: false),
        );
      }, (json) {
        return (json as List<dynamic>).map((row) {
          final r = row as Map<String, dynamic>;
          return SessionSummary(
            sessionId: r['session_id'] as String,
            subject: r['subject'] as String?,
            topic: r['topic'] as String?,
            status: SessionStatus.values.byName(r['status'] as String),
            startedAt: DateTime.parse(r['started_at'] as String),
            lastActivity: DateTime.parse(r['last_activity'] as String),
            turnCount: r['turn_count'] as int,
          );
        }).toList();
      });

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) =>
      _send(_readDeadline, () {
        return _client.get(
          _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/resume'),
          headers: _headers(hasJsonBody: false),
        );
      }, (json) {
        final m = json as Map<String, dynamic>;
        return ResumeSessionResult(
          sessionId: m['session_id'] as String,
          status: SessionStatus.values.byName(m['status'] as String),
          turns: _turns(m['turns'] as List<dynamic>),
          studentId: m['student_id'] as String,
        );
      });

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) =>
      _send(_turnDeadline, () {
        return _client.post(
          _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/turn'),
          headers: _headers(hasJsonBody: true),
          // `stream` is omitted: HTTP `turn` is the whole-response variant
          // (binding §6; streaming is WS-only and lands with voice).
          body: jsonEncode({'user_message': userMessage}),
        );
      }, (json) {
        final m = json as Map<String, dynamic>;
        return TurnResult(tutorResponse: m['tutor_response'] as String);
      });

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) =>
      _send(_readDeadline, () {
        return _client.get(
          _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/status'),
          headers: _headers(hasJsonBody: false),
        );
      }, (json) {
        final m = json as Map<String, dynamic>;
        return SessionStatusResult(
          sessionId: m['session_id'] as String,
          studentId: m['student_id'] as String,
          status: SessionStatus.values.byName(m['status'] as String),
          turnCount: m['turn_count'] as int,
          startedAt: DateTime.parse(m['started_at'] as String),
          lastActivity: DateTime.parse(m['last_activity'] as String),
          resumable: m['resumable'] as bool,
        );
      });

  @override
  Future<EndSessionResult> endSession(String sessionId) =>
      _send(_readDeadline, () {
        return _client.post(
          // Binding §2: path param only — no request body.
          _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/end'),
          headers: _headers(hasJsonBody: false),
        );
      }, (json) {
        final m = json as Map<String, dynamic>;
        // Rev 2 (contract §5): the nullable `gamification` settlement block.
        // Absent/null ⇒ not yet settled — parse only when present, never invent.
        final gamification = m['gamification'] as Map<String, dynamic>?;
        return EndSessionResult(
          sessionId: m['session_id'] as String,
          status: SessionStatus.values.byName(m['status'] as String),
          gamification: gamification == null
              ? null
              : SessionGamification.fromJson(gamification),
        );
      });
}
