/// The `SessionApi` port — contract §5's six verbs, 1:1, transport-neutral.
///
/// Contract: API-session-cross-device.md §5 (pinned at CONTRACT_SHA).
/// v1 has one adapter (FakeSessionApi); the real HTTP/WS adapter later
/// implements this same interface. `turn` is the plain request/response
/// variant (§7 HTTP) — no streaming in v1.
///
/// All verbs may throw the §9 closed error set (see domain/errors.dart):
/// callers are identified by their token (§3), never by passing `student_id`.
library;

import '../domain/session.dart';

/// §5 `start_session` output: `{session_id, student_id, resumed, turns?}`.
class StartSessionResult {
  const StartSessionResult({
    required this.sessionId,
    required this.studentId,
    required this.resumed,
    this.turns,
  });

  final String sessionId;
  final String studentId;

  /// True iff `resume_if_active` matched an existing active session for
  /// `(student, subject)` instead of creating a new one.
  final bool resumed;

  /// Present when [resumed] — the existing ordered transcript.
  final List<TurnEntry>? turns;
}

/// §5 `resume_session` output: `{session_id, status, turns, student_id}`.
class ResumeSessionResult {
  const ResumeSessionResult({
    required this.sessionId,
    required this.status,
    required this.turns,
    required this.studentId,
  });

  final String sessionId;
  final SessionStatus status;

  /// Ordered transcript (§6: `session_turn` rows in turn order).
  final List<TurnEntry> turns;
  final String studentId;
}

/// §5 `turn` output (HTTP variant): `{tutor_response}`.
class TurnResult {
  const TurnResult({required this.tutorResponse});

  final String tutorResponse;
}

/// §5 `session_status` output: `{session_id, student_id, status, turn_count,
/// started_at, last_activity, resumable}`.
class SessionStatusResult {
  const SessionStatusResult({
    required this.sessionId,
    required this.studentId,
    required this.status,
    required this.turnCount,
    required this.startedAt,
    required this.lastActivity,
    required this.resumable,
  });

  final String sessionId;
  final String studentId;
  final SessionStatus status;
  final int turnCount;
  final DateTime startedAt;
  final DateTime lastActivity;

  /// §4: true iff status is `active`.
  final bool resumable;
}

/// §5 `end_session` output: `{session_id, status: "ended"}`.
class EndSessionResult {
  const EndSessionResult({required this.sessionId, required this.status});

  final String sessionId;
  final SessionStatus status;
}

abstract interface class SessionApi {
  /// §5 `start_session`. With [resumeIfActive], returns the existing active
  /// session for `(student, subject)` (`resumed: true`, with turns) instead
  /// of creating a new one.
  Future<StartSessionResult> startSession({
    String? subject,
    String? topic,
    bool resumeIfActive = false,
  });

  /// §5 `list_sessions`, optionally filtered by [status], capped at [limit].
  Future<List<SessionSummary>> listSessions({SessionStatus? status, int? limit});

  /// §5 `resume_session` — loads the ordered transcript. Active sessions only
  /// (§4: ended is terminal → SessionEnded).
  Future<ResumeSessionResult> resumeSession(String sessionId);

  /// §5 `turn` — appends the `(user, tutor)` pair durably, bumps turn_count.
  Future<TurnResult> turn(String sessionId, String userMessage);

  /// §5 `session_status` — the one verb that still answers on an ended
  /// session (§9).
  Future<SessionStatusResult> sessionStatus(String sessionId);

  /// §5 `end_session` — `ended` is terminal (§4).
  Future<EndSessionResult> endSession(String sessionId);
}
