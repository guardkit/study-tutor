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

import '../domain/gamification.dart';
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

/// Binding §2.4 (additive addendum) `turns_since` output:
/// `{session_id, status, turns, next}`.
///
/// The additive delta read: [turns] are the ordered transcript ROWS at index
/// `>= since` (0-based ROW offset into the same rows `resume_session` returns —
/// NOT the `//2` pair count), and [next] is the RAW total row count to feed the
/// next poll's `since`. Reads active AND ended sessions (`allow_ended`), so it
/// NEVER throws SessionEnded — a poll survives the active→ended transition.
class TurnsSinceResult {
  const TurnsSinceResult({
    required this.sessionId,
    required this.status,
    required this.turns,
    required this.next,
  });

  final String sessionId;
  final SessionStatus status;

  /// The tail of the ordered transcript at row index `>= since` (§6 order,
  /// never re-sorted). Empty when `since >= next`.
  final List<TurnEntry> turns;

  /// The RAW total row count — the `since` value for the next poll.
  final int next;
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

/// §5 `end_session` output: `{session_id, status: "ended", gamification?}`.
///
/// Revision 2 (S-A3): the response gains the OPTIONAL, nullable [gamification]
/// settlement block (contract §5 Rev 2). Additive — nothing else on this type
/// changes. `null` ⇒ the engine has not settled the session yet; a client MUST
/// treat that as "settlement not reflected", never as an error, and never
/// fabricate a celebration.
class EndSessionResult {
  const EndSessionResult({
    required this.sessionId,
    required this.status,
    this.gamification,
  });

  final String sessionId;
  final SessionStatus status;

  /// The nullable settlement block — present only once the engine settles.
  final SessionGamification? gamification;
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

  /// Binding §2.4 (additive addendum) `turns_since` — the delta read: the
  /// ordered transcript rows at 0-based ROW index `>= since` plus the raw
  /// total row count in [TurnsSinceResult.next]. Reads active AND ended
  /// sessions, so it NEVER throws SessionEnded — a poll survives the
  /// active→ended transition. Additive: NOT one of the §5 six verbs.
  Future<TurnsSinceResult> turnsSince(String sessionId, int since);

  /// §5 `turn` — appends the `(user, tutor)` pair durably, bumps turn_count.
  Future<TurnResult> turn(String sessionId, String userMessage);

  /// §5 `session_status` — the one verb that still answers on an ended
  /// session (§9).
  Future<SessionStatusResult> sessionStatus(String sessionId);

  /// §5 `end_session` — `ended` is terminal (§4).
  Future<EndSessionResult> endSession(String sessionId);
}
