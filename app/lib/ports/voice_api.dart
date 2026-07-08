/// The `VoiceApi` port — sibling to SessionApi, handles voice turns.
///
/// Design: FEAT-VOICE-003 §6.2 (pinned at orientation doc ef8375f).
/// Voice input flows through this port (audio → transcript + TTS response),
/// leaving the frozen `SessionApi` text contract untouched. The port offers
/// both request/response ([voiceTurn]) and streaming ([voiceTurnStream])
/// variants — the real adapter implements whichever the wire binding supports.
///
/// All verbs may throw the six voice errors (see domain/errors.dart) plus the
/// existing closed set (§9: SessionNotFoundError, SessionEnded, etc.), which
/// apply to session-scoped verbs the same way text turns do.
library;

import 'dart:typed_data';

/// Non-streaming `voice_turn` output: `{transcript, answer_parts}`.
/// The full response arrives once, synchronously — no incremental delivery.
class VoiceTurnResult {
  const VoiceTurnResult({
    required this.transcript,
    required this.answerParts,
  });

  /// The recognized user utterance (STT output).
  final String transcript;

  /// Ordered answer parts: text + audio chunk references (seq determines order).
  final List<AnswerPart> answerParts;

  @override
  bool operator ==(Object other) =>
      other is VoiceTurnResult &&
      other.transcript == transcript &&
      _listEquals(other.answerParts, answerParts);

  @override
  int get hashCode => Object.hash(transcript, Object.hashAll(answerParts));

  @override
  String toString() =>
      'VoiceTurnResult(transcript: $transcript, parts: ${answerParts.length})';
}

/// One answer part — either text or an audio chunk reference. The `seq` field
/// defines rendering order across both types (incrementing from 0).
sealed class AnswerPart {
  const AnswerPart({required this.seq});

  /// Sequence number — determines rendering order across text and audio parts.
  final int seq;
}

/// Text answer part — rendered inline or spoken via TTS.
final class TextAnswerPart extends AnswerPart {
  const TextAnswerPart({required super.seq, required this.text});

  final String text;

  @override
  bool operator ==(Object other) =>
      other is TextAnswerPart && other.seq == seq && other.text == text;

  @override
  int get hashCode => Object.hash(seq, text);

  @override
  String toString() => 'TextAnswerPart(seq: $seq, text: $text)';
}

/// Audio answer part — reference to a chunk fetched via [VoiceApi.fetchAudioChunk].
final class AudioAnswerPart extends AnswerPart {
  const AudioAnswerPart({required super.seq, required this.chunkId});

  /// Opaque backend chunk ID — passed to `fetchAudioChunk` to retrieve bytes.
  final String chunkId;

  @override
  bool operator ==(Object other) =>
      other is AudioAnswerPart && other.seq == seq && other.chunkId == chunkId;

  @override
  int get hashCode => Object.hash(seq, chunkId);

  @override
  String toString() => 'AudioAnswerPart(seq: $seq, chunk: $chunkId)';
}

/// Streaming `voice_turn` event — emitted incrementally during response
/// generation. The stream yields: transcript-frame → text-tokens → audio-parts.
sealed class VoiceTurnEvent {
  const VoiceTurnEvent();
}

/// Transcript frame: the recognized user utterance (may arrive incrementally
/// or once finalized, depending on the STT backend).
final class TranscriptEvent extends VoiceTurnEvent {
  const TranscriptEvent({required this.transcript, required this.isFinal});

  final String transcript;

  /// True when the STT is finalized; false for intermediate hypotheses.
  final bool isFinal;

  @override
  bool operator ==(Object other) =>
      other is TranscriptEvent &&
      other.transcript == transcript &&
      other.isFinal == isFinal;

  @override
  int get hashCode => Object.hash(transcript, isFinal);

  @override
  String toString() =>
      'TranscriptEvent(transcript: $transcript, final: $isFinal)';
}

/// Incremental text token — a fragment of the answer text, emitted as the LLM
/// generates tokens. The UI concatenates these to show real-time response.
final class TextTokenEvent extends VoiceTurnEvent {
  const TextTokenEvent({required this.token});

  final String token;

  @override
  bool operator ==(Object other) =>
      other is TextTokenEvent && other.token == token;

  @override
  int get hashCode => token.hashCode;

  @override
  String toString() => 'TextTokenEvent(token: $token)';
}

/// Audio part event — signals that an audio chunk is available. The `seq`
/// determines playback order; the `chunkId` is fetched via `fetchAudioChunk`.
final class AudioPartEvent extends VoiceTurnEvent {
  const AudioPartEvent({required this.seq, required this.chunkId});

  final int seq;
  final String chunkId;

  @override
  bool operator ==(Object other) =>
      other is AudioPartEvent &&
      other.seq == seq &&
      other.chunkId == chunkId;

  @override
  int get hashCode => Object.hash(seq, chunkId);

  @override
  String toString() => 'AudioPartEvent(seq: $seq, chunk: $chunkId)';
}

/// Turn complete event — signals that no more events will arrive (no more text
/// tokens, no more audio parts). The UI can finalize rendering and re-enable
/// the microphone.
final class TurnCompleteEvent extends VoiceTurnEvent {
  const TurnCompleteEvent();

  @override
  bool operator ==(Object other) => other is TurnCompleteEvent;

  @override
  int get hashCode => 0;

  @override
  String toString() => 'TurnCompleteEvent()';
}

abstract interface class VoiceApi {
  /// Request/response voice turn — upload audio, receive the full answer once.
  /// Throws the six voice errors (UnsupportedAudioFormat, EmptyRecording, etc.)
  /// plus the existing §9 errors (SessionNotFoundError, SessionEnded, etc.).
  Future<VoiceTurnResult> voiceTurn(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  });

  /// Streaming voice turn — upload audio, receive incremental events
  /// (transcript → text tokens → audio parts → complete). The stream closes
  /// after [TurnCompleteEvent]; errors are thrown into the stream.
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  });

  /// Fetch a pre-generated audio chunk by its opaque ID (returned in
  /// [AudioAnswerPart] or [AudioPartEvent]). The bytes are the raw audio
  /// payload in the format negotiated with the backend (typically Opus/OGG).
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId);
}

/// Helper to compare lists for equality (Dart lacks a built-in deep equals).
bool _listEquals<T>(List<T> a, List<T> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}
