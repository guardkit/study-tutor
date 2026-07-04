/// FakeSessionApi — a reference implementation of the contract's behavioural
/// statements (scope §2.3), not a stub.
///
/// Contract: API-session-cross-device.md §3–§6, §9 (pinned at CONTRACT_SHA).
/// Caller identity is resolved per call from the identity fake's token
/// introspection (§3) — the UI never passes `student_id`. Tutor replies are
/// canned and deterministic, keyed off turn index (scope §2.3): determinism
/// is what makes the contract tests exact.
library;

import '../domain/errors.dart';
import '../domain/session.dart';
import '../ports/session_api.dart';
import 'fake_identity_provider.dart';

/// The fake backend's store, separate from the client object so a second
/// FakeSessionApi instance over the *same* store models a second device —
/// the §4 per-turn-durability analogue (scope §4 test 3).
class InMemorySessionStore {
  final Map<String, Session> sessions = {};
  final Map<String, List<TurnEntry>> turnsBySession = {};
  int _nextId = 0;

  String nextSessionId() => 's-${++_nextId}';
}

class FakeSessionApi implements SessionApi {
  FakeSessionApi({
    required this._identity,
    InMemorySessionStore? store,
    DateTime Function()? clock,
  })  : _store = store ?? InMemorySessionStore(),
        _clock = clock ?? DateTime.now;

  final FakeIdentityProvider _identity;
  final InMemorySessionStore _store;
  final DateTime Function() _clock;

  /// Deterministic canned tutor replies, cycled by turn index.
  static const cannedReplies = [
    "Let's break that down together — what do you already know?",
    'Good thinking. Walk me through your reasoning step by step.',
    'Nearly there — check the last step once more.',
    'Exactly right! Want to try a slightly harder one?',
  ];

  /// §3: derive the caller's `student_id` from the current token via the
  /// fake auth-server introspection; §9: no valid token → Unauthenticated.
  String _requireStudentId() {
    final studentId =
        _identity.studentIdForToken(_identity.currentPrincipal?.token);
    if (studentId == null) {
      throw const Unauthenticated();
    }
    return studentId;
  }

  /// §9: unknown `session_id` → SessionNotFoundError.
  Session _requireSession(String sessionId) {
    final session = _store.sessions[sessionId];
    if (session == null) {
      throw const SessionNotFoundError();
    }
    return session;
  }

  /// §4: `ended` is terminal — any verb except `session_status` on an ended
  /// session → SessionEnded.
  void _requireActive(Session session) {
    if (session.status == SessionStatus.ended) {
      throw const SessionEnded();
    }
  }

  List<TurnEntry> _transcript(String sessionId) =>
      List.unmodifiable(_store.turnsBySession[sessionId] ?? const []);

  @override
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  }) async {
    final studentId = _requireStudentId();

    if (resumeIfActive) {
      // §5: keyed on (student, subject) — an active session for a different
      // subject does not match.
      final existing = _store.sessions.values
          .where((s) =>
              s.studentId == studentId &&
              s.subject == subject &&
              s.status == SessionStatus.active)
          .firstOrNull;
      if (existing != null) {
        return StartSessionResult(
          sessionId: existing.id,
          studentId: studentId,
          resumed: true,
          turns: _transcript(existing.id),
        );
      }
    }

    final now = _clock();
    final id = _store.nextSessionId();
    _store.sessions[id] = Session(
      id: id,
      studentId: studentId,
      subject: subject,
      topic: topic,
      status: SessionStatus.active,
      startedAt: now,
      lastActivity: now,
      turnCount: 0,
    );
    _store.turnsBySession[id] = [];
    return StartSessionResult(
      sessionId: id,
      studentId: studentId,
      resumed: false,
    );
  }

  @override
  Future<List<SessionSummary>> listSessions({
    SessionStatus? status,
    int? limit,
  }) {
    throw UnimplementedError('listSessions lands in wave-4 (contract test 9)');
  }

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) async {
    final studentId = _requireStudentId();
    final session = _requireSession(sessionId);
    _requireActive(session);
    return ResumeSessionResult(
      sessionId: session.id,
      status: session.status,
      turns: _transcript(session.id),
      studentId: studentId,
    );
  }

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) async {
    _requireStudentId();
    final session = _requireSession(sessionId);
    _requireActive(session);

    final now = _clock();
    final reply = cannedReplies[session.turnCount % cannedReplies.length];

    // §4/§6: the (user, tutor) pair is committed to the store as the turn
    // completes — per-turn durable, append-only.
    _store.turnsBySession[session.id]!
      ..add(TurnEntry(role: TurnRole.user, content: userMessage, ts: now))
      ..add(TurnEntry(role: TurnRole.tutor, content: reply, ts: now));
    _store.sessions[session.id] = session.copyWith(
      turnCount: session.turnCount + 1,
      lastActivity: now,
    );

    return TurnResult(tutorResponse: reply);
  }

  @override
  Future<SessionStatusResult> sessionStatus(String sessionId) async {
    _requireStudentId();
    // §9: session_status is the one verb that still answers on an ended
    // session — no _requireActive here.
    final session = _requireSession(sessionId);
    return SessionStatusResult(
      sessionId: session.id,
      studentId: session.studentId,
      status: session.status,
      turnCount: session.turnCount,
      startedAt: session.startedAt,
      lastActivity: session.lastActivity,
      resumable: session.status == SessionStatus.active,
    );
  }

  @override
  Future<EndSessionResult> endSession(String sessionId) async {
    _requireStudentId();
    final session = _requireSession(sessionId);
    _requireActive(session);
    _store.sessions[session.id] = session.copyWith(
      status: SessionStatus.ended,
      lastActivity: _clock(),
    );
    return EndSessionResult(
      sessionId: session.id,
      status: SessionStatus.ended,
    );
  }
}
