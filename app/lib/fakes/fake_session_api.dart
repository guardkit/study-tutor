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
import '../domain/gamification.dart';
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

  /// §5: every verb taking a `session_id` asserts the session's
  /// `student_id` == caller's → SessionForbidden otherwise.
  void _requireOwner(Session session, String studentId) {
    if (session.studentId != studentId) {
      throw const SessionForbidden();
    }
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
      // subject does not match. The contract's singular wording leaves the
      // pick undefined when duplicate actives exist (logged in QUESTIONS.md);
      // align with listSessions' "resume where you left off" ordering: the
      // most recently active match wins.
      final matches = _store.sessions.values
          .where((s) =>
              s.studentId == studentId &&
              s.subject == subject &&
              s.status == SessionStatus.active)
          .toList()
        ..sort((a, b) => b.lastActivity.compareTo(a.lastActivity));
      final existing = matches.firstOrNull;
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
  }) async {
    final studentId = _requireStudentId();
    // §3: student_id is the partition key — callers only ever see their own
    // sessions. Most-recent-activity first ("resume where you left off").
    var sessions = _store.sessions.values
        .where((s) => s.studentId == studentId)
        .where((s) => status == null || s.status == status)
        .toList()
      ..sort((a, b) => b.lastActivity.compareTo(a.lastActivity));
    if (limit != null && sessions.length > limit) {
      sessions = sessions.sublist(0, limit);
    }
    return sessions
        .map((s) => SessionSummary(
              sessionId: s.id,
              subject: s.subject,
              topic: s.topic,
              status: s.status,
              startedAt: s.startedAt,
              lastActivity: s.lastActivity,
              turnCount: s.turnCount,
            ))
        .toList();
  }

  @override
  Future<ResumeSessionResult> resumeSession(String sessionId) async {
    final studentId = _requireStudentId();
    final session = _requireSession(sessionId);
    _requireOwner(session, studentId);
    // §5/§4: resume is an ACTIVE-session verb — `ended` is terminal, so resume
    // on an ended session → SessionEnded (matches the real backend + the port
    // doc "Active sessions only"). Session-History reads an ended transcript
    // through the additive `turns_since` verb instead, which reads ended too.
    _requireActive(session);
    return ResumeSessionResult(
      sessionId: session.id,
      status: session.status,
      turns: _transcript(session.id),
      studentId: studentId,
    );
  }

  @override
  Future<TurnsSinceResult> turnsSince(String sessionId, int since) async {
    final studentId = _requireStudentId();
    final session = _requireSession(sessionId);
    _requireOwner(session, studentId);
    // Binding §2.4: the additive delta read. Reads ENDED sessions too — do NOT
    // _requireActive here, so a poll survives the active→ended transition and
    // History can load an ended transcript. `next` is the RAW total row count;
    // `since >= total` yields an empty tail (never an error).
    final rows = _transcript(session.id);
    final total = rows.length;
    final start = since < total ? since : total;
    return TurnsSinceResult(
      sessionId: session.id,
      status: session.status,
      turns: List.unmodifiable(rows.sublist(start)),
      next: total,
    );
  }

  @override
  Future<TurnResult> turn(String sessionId, String userMessage) async {
    final studentId = _requireStudentId();
    final session = _requireSession(sessionId);
    _requireOwner(session, studentId);
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
    final studentId = _requireStudentId();
    // §9: session_status is the one verb that still answers on an ended
    // session — no _requireActive here (ownership still applies).
    final session = _requireSession(sessionId);
    _requireOwner(session, studentId);
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
    final studentId = _requireStudentId();
    final session = _requireSession(sessionId);
    _requireOwner(session, studentId);
    _requireActive(session);
    final ended = session.copyWith(
      status: SessionStatus.ended,
      lastActivity: _clock(),
    );
    _store.sessions[session.id] = ended;
    return EndSessionResult(
      sessionId: session.id,
      status: SessionStatus.ended,
      // §6.2: the fake models the nullable settlement block deterministically
      // over the store (fixed XP per session shape) so contract tests pin
      // exact values while live tests assert invariants.
      gamification: _settle(studentId, ended),
    );
  }

  /// Fixed XP per fake session shape (contract §5 Rev 2 `xp_awarded`): a
  /// deterministic engagement-band base keyed off turn count.
  static int _sessionXp(int turnCount) {
    if (turnCount == 0) return 0; // settled but sub-engagement
    if (turnCount < 3) return 60;
    return 120;
  }

  /// Synthesise the settlement block from the store state after [ended] is
  /// banked — pure and deterministic (contract §5 Rev 2 semantics):
  /// `total_xp = SUM(session.xp) + SUM(achievement.xp)`, level derived from the
  /// design §3.1 economy, First Steps (+50) unlocked on the student's first
  /// scoring session.
  SessionGamification _settle(String studentId, Session ended) {
    final endedForStudent = _store.sessions.values
        .where((s) =>
            s.studentId == studentId && s.status == SessionStatus.ended)
        .toList();

    final xpAwarded = _sessionXp(ended.turnCount);
    final sessionXpTotal = endedForStudent.fold<int>(
        0, (sum, s) => sum + _sessionXp(s.turnCount));

    // First Steps: banked once, on the first ended session that scores XP.
    final scoringEndedCount =
        endedForStudent.where((s) => _sessionXp(s.turnCount) > 0).length;
    final newlyFirstSteps = xpAwarded > 0 && scoringEndedCount == 1;
    final achievementsUnlocked = <UnlockedAchievement>[
      if (newlyFirstSteps)
        const UnlockedAchievement(id: 'first_steps', name: 'First Steps', xp: 50),
    ];
    final achievementXpAll = scoringEndedCount > 0 ? 50 : 0;

    final totalXp = sessionXpTotal + achievementXpAll;
    final priorXp =
        totalXp - xpAwarded - (newlyFirstSteps ? 50 : 0);
    final level = GamificationEconomy.levelForXp(totalXp);
    final priorLevel = GamificationEconomy.levelForXp(priorXp);

    return SessionGamification(
      xpAwarded: xpAwarded,
      totalXp: totalXp,
      levelNumber: level.number,
      levelName: level.name,
      levelUp: level.number > priorLevel.number,
      achievementsUnlocked: achievementsUnlocked,
      // A deterministic streak proxy: the count of the student's ended
      // sessions (the fake has no London calendar). Live asserts invariants.
      streakDays: endedForStudent.length,
      streakExtended: true,
    );
  }
}
