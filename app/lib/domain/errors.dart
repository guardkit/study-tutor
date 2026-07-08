/// Typed errors mirroring the contract's closed error set.
///
/// Contract: API-session-cross-device.md §9 (pinned at CONTRACT_SHA).
/// Each exception carries the contract's exact `error_type` string in
/// [SessionApiException.errorType] so the real-transport adapter can map the
/// wire envelope 1:1. The set is closed — `sealed` enforces that no error
/// type exists outside this file: the four §9 wire errors plus exactly one
/// **client-local** member, [TransportError], which never appears in a wire
/// envelope (phase-2 scope §3.2).
library;

sealed class SessionApiException implements Exception {
  const SessionApiException(this.message);

  final String message;

  /// The wire `error_type` string, verbatim per contract §9 — except on the
  /// client-local [TransportError], where it is a label that never appears
  /// in a wire envelope.
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

/// Client-local (phase-2 scope §3.2): the transport failed before a §9
/// envelope arrived — network unreachable, timeout, or a malformed response
/// body. NOT part of the §9 wire set: no backend ever sends it; the HTTP
/// adapter synthesises it, so [errorType] is a client-side label rather than
/// a contract string. UI treatment: the non-crashing "connection problem —
/// try again" surface, which preserves unsent input.
final class TransportError extends SessionApiException {
  const TransportError([super.message = 'could not reach the backend']);

  @override
  String get errorType => 'TransportError';
}

/// Voice-specific errors (FEAT-VOICE-003 §6.2): six error types for the
/// VoiceApi port, extending the same sealed hierarchy. Like the §9 errors
/// above, each carries its contract `error_type` string so the voice adapter
/// can map wire envelopes 1:1.

/// Audio format not supported (codec, sample rate, or container).
final class UnsupportedAudioFormat extends SessionApiException {
  const UnsupportedAudioFormat(
      [super.message = 'audio format not supported']);

  @override
  String get errorType => 'UnsupportedAudioFormat';
}

/// Recording contains no audio content or is too short to process.
final class EmptyRecording extends SessionApiException {
  const EmptyRecording([super.message = 'recording is empty or too short']);

  @override
  String get errorType => 'EmptyRecording';
}

/// Audio is clear but the query is unintelligible (no transcribable speech).
final class UnintelligibleQuery extends SessionApiException {
  const UnintelligibleQuery(
      [super.message = 'could not understand the query']);

  @override
  String get errorType => 'UnintelligibleQuery';
}

/// Transcribed query exceeds the maximum allowed length.
final class QueryTooLong extends SessionApiException {
  const QueryTooLong([super.message = 'query exceeds maximum length']);

  @override
  String get errorType => 'QueryTooLong';
}

/// Recording size exceeds the maximum allowed payload.
final class RecordingTooLarge extends SessionApiException {
  const RecordingTooLarge([super.message = 'recording exceeds size limit']);

  @override
  String get errorType => 'RecordingTooLarge';
}

/// Voice backend unavailable — drives the amber degradation copy that prompts
/// the user to fall back to text input.
final class VoiceUnavailable extends SessionApiException {
  const VoiceUnavailable(
      [super.message = 'voice service temporarily unavailable']);

  @override
  String get errorType => 'VoiceUnavailable';
}
