/// Session domain models.
///
/// Contract: API-session-cross-device.md §4 (lifecycle), §5 (shapes),
/// §6 (persistence semantics) — pinned at CONTRACT_SHA. Field names are the
/// Dart-cased forms of the contract's snake_case wire names.
library;

/// §4: states are `active` | `ended`; `ended` is terminal.
enum SessionStatus { active, ended }

/// §5/§6: who spoke a turn. Wire values are the enum names.
enum TurnRole { user, tutor }

/// One transcript entry — §5 `resume_session` output: `{role, content, ts}`.
/// Transcript order is insertion order (§6 append-only), never re-sorted.
class TurnEntry {
  const TurnEntry({required this.role, required this.content, required this.ts});

  final TurnRole role;
  final String content;
  final DateTime ts;

  @override
  bool operator ==(Object other) =>
      other is TurnEntry &&
      other.role == role &&
      other.content == content &&
      other.ts == ts;

  @override
  int get hashCode => Object.hash(role, content, ts);

  @override
  String toString() => 'TurnEntry(${role.name}, $content, $ts)';
}

/// A session record — §6 `session` row shape (minus backend-only JSONB).
class Session {
  const Session({
    required this.id,
    required this.studentId,
    this.subject,
    this.topic,
    required this.status,
    required this.startedAt,
    required this.lastActivity,
    required this.turnCount,
  });

  final String id;
  final String studentId;
  final String? subject;
  final String? topic;
  final SessionStatus status;
  final DateTime startedAt;
  final DateTime lastActivity;

  /// §4: monotonic `session_version` analogue — never decreases.
  final int turnCount;

  Session copyWith({
    SessionStatus? status,
    DateTime? lastActivity,
    int? turnCount,
  }) =>
      Session(
        id: id,
        studentId: studentId,
        subject: subject,
        topic: topic,
        status: status ?? this.status,
        startedAt: startedAt,
        lastActivity: lastActivity ?? this.lastActivity,
        turnCount: turnCount ?? this.turnCount,
      );

  @override
  bool operator ==(Object other) =>
      other is Session &&
      other.id == id &&
      other.studentId == studentId &&
      other.subject == subject &&
      other.topic == topic &&
      other.status == status &&
      other.startedAt == startedAt &&
      other.lastActivity == lastActivity &&
      other.turnCount == turnCount;

  @override
  int get hashCode => Object.hash(
      id, studentId, subject, topic, status, startedAt, lastActivity, turnCount);

  @override
  String toString() => 'Session($id, ${status.name}, turns: $turnCount)';
}

/// §5 `list_sessions` row:
/// `{session_id, subject, topic, status, started_at, last_activity, turn_count}`.
class SessionSummary {
  const SessionSummary({
    required this.sessionId,
    this.subject,
    this.topic,
    required this.status,
    required this.startedAt,
    required this.lastActivity,
    required this.turnCount,
  });

  final String sessionId;
  final String? subject;
  final String? topic;
  final SessionStatus status;
  final DateTime startedAt;
  final DateTime lastActivity;
  final int turnCount;

  @override
  bool operator ==(Object other) =>
      other is SessionSummary &&
      other.sessionId == sessionId &&
      other.subject == subject &&
      other.topic == topic &&
      other.status == status &&
      other.startedAt == startedAt &&
      other.lastActivity == lastActivity &&
      other.turnCount == turnCount;

  @override
  int get hashCode => Object.hash(
      sessionId, subject, topic, status, startedAt, lastActivity, turnCount);

  @override
  String toString() => 'SessionSummary($sessionId, ${status.name})';
}
