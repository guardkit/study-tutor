/// FakeVoiceApi + FlakyVoiceApi decorator + FakeVoiceRecorder mock.
///
/// Hermetic test infrastructure for voice features (FEAT-VOICE-003):
/// - FakeVoiceApi: canned transcript + tiny silent-WAV responses
/// - FlakyVoiceApi: failure injection (mirrors FlakySessionApi pattern)
/// - FakeVoiceRecorder: deterministic recorder mock (the real VoiceRecorder
///   moved to `lib/adapters/voice_recorder.dart` in S-A2 §5.1)
///
/// `VoiceRecorder`/`AudioEncoder` are re-exported from the adapter so existing
/// call sites and tests keep their `fakes/fake_voice_api.dart` import.
library;

import 'dart:typed_data';

import '../adapters/voice_recorder.dart';
import '../domain/errors.dart';
import '../ports/voice_api.dart';

export '../adapters/voice_recorder.dart' show AudioEncoder, VoiceRecorder;

/// Canned transcript responses cycled by call index.
const _cannedTranscripts = [
  'What is the quadratic formula?',
  'How do I solve for x?',
  'Can you explain photosynthesis?',
  'What is the capital of France?',
];

/// Canned answer text responses.
const _cannedAnswers = [
  "Let's break that down together — what do you already know?",
  'Good thinking. Walk me through your reasoning step by step.',
  'Nearly there — check the last step once more.',
  'Exactly right! Want to try a slightly harder one?',
];

/// Generate a minimal silent WAV file (44 bytes header + minimal PCM data).
/// Returns bytes for a valid 16-bit PCM WAV at 44.1kHz, 1 channel, ~100ms duration.
Uint8List _tinysilentWav() {
  // Minimal WAV: RIFF header (12) + fmt chunk (24) + data chunk (8 + samples)
  // 44100 Hz * 0.1s * 2 bytes/sample = 8820 bytes of silence
  final sampleCount = 4410; // 0.1 seconds at 44.1kHz
  final dataSize = sampleCount * 2; // 16-bit = 2 bytes per sample
  final fileSize = 36 + dataSize;

  final bytes = BytesBuilder();

  // RIFF header
  bytes.add('RIFF'.codeUnits);
  bytes.add(_int32Bytes(fileSize));
  bytes.add('WAVE'.codeUnits);

  // fmt chunk
  bytes.add('fmt '.codeUnits);
  bytes.add(_int32Bytes(16)); // chunk size
  bytes.add(_int16Bytes(1)); // audio format (PCM)
  bytes.add(_int16Bytes(1)); // num channels
  bytes.add(_int32Bytes(44100)); // sample rate
  bytes.add(_int32Bytes(88200)); // byte rate (44100 * 2 * 1)
  bytes.add(_int16Bytes(2)); // block align
  bytes.add(_int16Bytes(16)); // bits per sample

  // data chunk
  bytes.add('data'.codeUnits);
  bytes.add(_int32Bytes(dataSize));
  bytes.add(Uint8List(dataSize)); // silent samples (all zeros)

  return bytes.toBytes();
}

Uint8List _int32Bytes(int value) {
  return Uint8List(4)
    ..[0] = value & 0xFF
    ..[1] = (value >> 8) & 0xFF
    ..[2] = (value >> 16) & 0xFF
    ..[3] = (value >> 24) & 0xFF;
}

Uint8List _int16Bytes(int value) {
  return Uint8List(2)
    ..[0] = value & 0xFF
    ..[1] = (value >> 8) & 0xFF;
}

/// In-memory fake VoiceApi implementation with deterministic canned responses.
///
/// Returns canned transcript + answer text (no real STT/LLM/TTS), cycling
/// through predefined responses by call count. Audio chunks are tiny silent
/// WAV files (~9KB each). Suitable for hermetic widget tests and BDD scenarios.
class FakeVoiceApi implements VoiceApi {
  int _callCount = 0;

  @override
  Future<VoiceTurnResult> voiceTurn(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async {
    final idx = _callCount++ % _cannedTranscripts.length;
    return VoiceTurnResult(
      transcript: _cannedTranscripts[idx],
      answerParts: [
        TextAnswerPart(seq: 0, text: _cannedAnswers[idx]),
        AudioAnswerPart(seq: 1, chunkId: 'chunk-$idx'),
      ],
    );
  }

  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) async* {
    final idx = _callCount++ % _cannedTranscripts.length;

    // Emit transcript (final)
    yield TranscriptEvent(
      transcript: _cannedTranscripts[idx],
      isFinal: true,
    );

    // Emit answer text as tokens (split into words)
    final words = _cannedAnswers[idx].split(' ');
    for (final word in words) {
      yield TextTokenEvent(token: '$word ');
      await Future.delayed(const Duration(milliseconds: 10));
    }

    // Emit audio part
    yield AudioPartEvent(seq: words.length, chunkId: 'chunk-$idx');

    // Signal completion
    yield const TurnCompleteEvent();
  }

  @override
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId) async {
    return _tinysilentWav();
  }
}

/// Decorator that injects voice errors into VoiceApi calls.
///
/// Mirrors the FlakySessionApi pattern: maintains a [failing] set of verb names
/// and an optional [errorToThrow]. When a verb is in [failing], throws the
/// configured error instead of delegating. Mutate [failing] mid-test to simulate
/// transient network failures, backend unavailability, or validation errors.
///
/// Example:
/// ```dart
/// final flaky = FlakyVoiceApi(FakeVoiceApi());
/// flaky.failing.add('voiceTurn');
/// flaky.errorToThrow = const VoiceUnavailable();
/// // Now voiceTurn throws VoiceUnavailable
/// ```
class FlakyVoiceApi implements VoiceApi {
  FlakyVoiceApi(this._inner);

  final VoiceApi _inner;

  /// Set of verb names that should fail. Add/remove to control failure injection.
  final Set<String> failing = {};

  /// The error to throw when a verb is in [failing]. Defaults to TransportError.
  SessionApiException errorToThrow = const TransportError();

  Future<T> _call<T>(String verb, Future<T> Function() body) async {
    if (failing.contains(verb)) {
      throw errorToThrow;
    }
    return body();
  }

  Stream<T> _callStream<T>(String verb, Stream<T> Function() body) async* {
    if (failing.contains(verb)) {
      throw errorToThrow;
    }
    yield* body();
  }

  @override
  Future<VoiceTurnResult> voiceTurn(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) =>
      _call(
        'voiceTurn',
        () => _inner.voiceTurn(sessionId, audio, contentType: contentType),
      );

  @override
  Stream<VoiceTurnEvent> voiceTurnStream(
    String sessionId,
    Uint8List audio, {
    required String contentType,
  }) =>
      _callStream(
        'voiceTurnStream',
        () => _inner.voiceTurnStream(sessionId, audio, contentType: contentType),
      );

  @override
  Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId) =>
      _call(
        'fetchAudioChunk',
        () => _inner.fetchAudioChunk(sessionId, chunkId),
      );
}

/// Deterministic [VoiceRecorder] mock for hermetic tests — the fake that stays
/// behind now that the real recorder lives in `lib/adapters/voice_recorder.dart`
/// (S-A2 §5.1). `stop()` returns fixed canned bytes; no microphone, no files.
///
/// Implements the [VoiceRecorder] interface so it drops into any call site that
/// accepts one (the session screen constructor).
class FakeVoiceRecorder implements VoiceRecorder {
  FakeVoiceRecorder({
    this.encoder = AudioEncoder.aacLc,
    Duration? maxDuration,
    int? maxSizeBytes,
    Uint8List? cannedBytes,
    this.throwOnStart,
  })  : maxDuration = maxDuration ?? const Duration(seconds: 60),
        maxSizeBytes = maxSizeBytes ?? (10 * 1024 * 1024),
        _cannedBytes = cannedBytes ?? Uint8List.fromList(List<int>.filled(64, 7));

  @override
  final AudioEncoder encoder;
  @override
  final Duration maxDuration;
  @override
  final int maxSizeBytes;

  final Uint8List _cannedBytes;

  /// When set, [start] throws it — models a permission denial.
  final Object? throwOnStart;

  bool _isRecording = false;
  VoiceAutoStop? _onMaxDuration;

  @override
  bool get isRecording => _isRecording;

  @override
  Future<void> start({VoiceAutoStop? onMaxDuration}) async {
    if (throwOnStart != null) throw throwOnStart!;
    _onMaxDuration = onMaxDuration;
    _isRecording = true;
  }

  /// Test hook: simulate the 60-second hard-stop firing with the canned bytes.
  void fireAutoStop() {
    if (!_isRecording) return;
    _isRecording = false;
    _onMaxDuration?.call(_cannedBytes, null);
  }

  @override
  Future<Uint8List?> stop() async {
    if (!_isRecording) return null;
    _isRecording = false;
    return _cannedBytes;
  }

  @override
  void cancel() => _isRecording = false;

  @override
  void dispose() => _isRecording = false;
}
