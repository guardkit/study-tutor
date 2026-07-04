/// Typed errors mirroring the contract's closed error set.
///
/// Contract: API-session-cross-device.md §9 (pinned at CONTRACT_SHA).
/// Each exception carries the contract's exact `error_type` string in
/// [SessionApiException.errorType] so the future real-transport adapter can
/// map the wire envelope 1:1. The set is closed — `sealed` enforces that no
/// error type exists outside this file.
library;

sealed class SessionApiException implements Exception {
  const SessionApiException(this.message);

  final String message;

  /// The contract §9 `error_type` string, verbatim.
  String get errorType;

  @override
  String toString() => '$errorType: $message';
}

/// §9: `session_id` unknown.
final class SessionNotFoundError extends SessionApiException {
  const SessionNotFoundError([super.message = 'session_id unknown']);

  @override
  String get errorType => 'SessionNotFoundError';
}

/// §9: verb on an `ended` session (except `session_status`).
final class SessionEnded extends SessionApiException {
  const SessionEnded([super.message = 'session is ended']);

  @override
  String get errorType => 'SessionEnded';
}

/// §9: session's `student_id` ≠ caller's.
final class SessionForbidden extends SessionApiException {
  const SessionForbidden([super.message = 'session not owned by caller']);

  @override
  String get errorType => 'SessionForbidden';
}

/// §9: missing/invalid token.
final class Unauthenticated extends SessionApiException {
  const Unauthenticated([super.message = 'missing or invalid token']);

  @override
  String get errorType => 'Unauthenticated';
}
