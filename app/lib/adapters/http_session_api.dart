/// HttpSessionApi — the real transport adapter behind the `SessionApi` port.
///
/// Binding: API-session-http-binding.md, consumed at the BINDING_SHA pinned
/// in the phase-2 build plan header — six verbs under
/// `Authorization: Bearer <token>` (§3), JSON shapes per contract §5, wire
/// enum values = the domain enum names. The binding doc is frozen: if the
/// wire disagrees with it, that is a backend/binding bug to raise, never
/// something to adapt to silently here.
///
/// p2-wave-3 scope: the six happy paths. The §9 envelope → typed-exception
/// mapping and per-request deadlines land in p2-wave-4; until then every
/// non-2xx response surfaces as [TransportError] (already non-crashing at
/// every call site since p2-wave-1).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/identity_provider.dart';
import '../ports/session_api.dart';

class HttpSessionApi implements SessionApi {
  HttpSessionApi({
    required String baseUrl,
    required this._identity,
    http.Client? client,
  })  : _base = baseUrl.endsWith('/')
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl,
        _client = client ?? http.Client();

  final String _base;
  final IdentityProvider _identity;
  final http.Client _client;

  Uri _uri(String path, [Map<String, String> query = const {}]) {
    final uri = Uri.parse('$_base$path');
    return query.isEmpty ? uri : uri.replace(queryParameters: query);
  }

  /// Binding §3: the token is honored from the credential header ONLY. When
  /// signed out no header is sent — the server answers 401 (mapped in
  /// p2-wave-4), never a client-side guess.
  Map<String, String> _headers({required bool hasJsonBody}) {
    final token = _identity.currentPrincipal?.token;
    return {
      if (hasJsonBody) 'content-type': 'application/json',
      if (token != null) 'authorization': 'Bearer $token',
    };
  }

  /// Decode a 2xx JSON body ([utf8] over the raw bytes — charset headers are
  /// not trusted to be present). Any non-2xx is a TransportError until
  /// p2-wave-4 lands the §9 envelope mapping.
  dynamic _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw TransportError('unexpected HTTP ${response.statusCode}');
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
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
  }) async {
    final response = await _client.post(
      _uri('/api/sessions/start'),
      headers: _headers(hasJsonBody: true),
      body: jsonEncode({
        'subject': ?subject,
        'topic': ?topic,
        'resume_if_active': resumeIfActive,
      }),
    );
    final json = _decode(response) as Map<String, dynamic>;
    final turns = json['turns'] as List<dynamic>?;
    return StartSessionResult(
      sessionId: json['session_id'] as String,
      studentId: json['student_id'] as String,
      resumed: json['resumed'] as bool,
      turns: turns == null ? null : _turns(turns),
    );
  }

  @override
  Future<List<SessionSummary>> listSessions({
    SessionStatus? status,
    int? limit,
  }) async {
    final response = await _client.get(
      _uri('/api/sessions', {
        if (status != null) 'status': status.name,
        if (limit != null) 'limit': '$limit',
      }),
      headers: _headers(hasJsonBody: false),
    );
    final json = _decode(response) as List<dynamic>;
    return json.map((row) {
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
  }

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) async {
    final response = await _client.get(
      _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/resume'),
      headers: _headers(hasJsonBody: false),
    );
    final json = _decode(response) as Map<String, dynamic>;
    return ResumeSessionResult(
      sessionId: json['session_id'] as String,
      status: SessionStatus.values.byName(json['status'] as String),
      turns: _turns(json['turns'] as List<dynamic>),
      studentId: json['student_id'] as String,
    );
  }

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) async {
    final response = await _client.post(
      _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/turn'),
      headers: _headers(hasJsonBody: true),
      // `stream` is omitted: HTTP `turn` is the whole-response variant
      // (binding §6; streaming is WS-only and lands with voice).
      body: jsonEncode({'user_message': userMessage}),
    );
    final json = _decode(response) as Map<String, dynamic>;
    return TurnResult(tutorResponse: json['tutor_response'] as String);
  }

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) async {
    final response = await _client.get(
      _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/status'),
      headers: _headers(hasJsonBody: false),
    );
    final json = _decode(response) as Map<String, dynamic>;
    return SessionStatusResult(
      sessionId: json['session_id'] as String,
      studentId: json['student_id'] as String,
      status: SessionStatus.values.byName(json['status'] as String),
      turnCount: json['turn_count'] as int,
      startedAt: DateTime.parse(json['started_at'] as String),
      lastActivity: DateTime.parse(json['last_activity'] as String),
      resumable: json['resumable'] as bool,
    );
  }

  @override
  Future<EndSessionResult> endSession(String sessionId) async {
    final response = await _client.post(
      // Binding §2: path param only — no request body.
      _uri('/api/sessions/${Uri.encodeComponent(sessionId)}/end'),
      headers: _headers(hasJsonBody: false),
    );
    final json = _decode(response) as Map<String, dynamic>;
    return EndSessionResult(
      sessionId: json['session_id'] as String,
      status: SessionStatus.values.byName(json['status'] as String),
    );
  }
}
