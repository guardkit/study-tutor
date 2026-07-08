import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';
import 'package:study_tutor_app/fakes/fake_voice_api.dart';
import 'package:study_tutor_app/ports/voice_api.dart';

void main() {
  group('FakeVoiceApi', () {
    late FakeVoiceApi api;

    setUp(() {
      api = FakeVoiceApi();
    });

    test('voiceTurn returns canned transcript and audio', () async {
      final audio = Uint8List.fromList([1, 2, 3, 4]);
      final result = await api.voiceTurn(
        's-1',
        audio,
        contentType: 'audio/m4a',
      );

      expect(result.transcript, isNotEmpty);
      expect(result.answerParts, isNotEmpty);
      expect(result.answerParts.first, isA<TextAnswerPart>());
    });

    test('voiceTurnStream emits canned events', () async {
      final audio = Uint8List.fromList([1, 2, 3, 4]);
      final stream = api.voiceTurnStream(
        's-1',
        audio,
        contentType: 'audio/m4a',
      );

      final events = await stream.toList();
      expect(events, isNotEmpty);
      expect(events.any((e) => e is TranscriptEvent), isTrue);
      expect(events.any((e) => e is TextTokenEvent), isTrue);
      expect(events.last, isA<TurnCompleteEvent>());
    });

    test('fetchAudioChunk returns tiny silent WAV bytes', () async {
      final bytes = await api.fetchAudioChunk('s-1', 'chunk-1');
      expect(bytes, isNotEmpty);
      expect(bytes.length, lessThan(10000)); // tiny (~9KB for 0.1s WAV)
    });
  });

  group('FlakyVoiceApi', () {
    late FakeVoiceApi inner;
    late FlakyVoiceApi flaky;

    setUp(() {
      inner = FakeVoiceApi();
      flaky = FlakyVoiceApi(inner);
    });

    test('delegates when no failures injected', () async {
      final audio = Uint8List.fromList([1, 2, 3, 4]);
      final result = await flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a');
      expect(result.transcript, isNotEmpty);
    });

    test('injects TransportError when voiceTurn is failing', () async {
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<TransportError>()),
      );
    });

    test('injects VoiceUnavailable when configured', () async {
      flaky.errorToThrow = const VoiceUnavailable();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<VoiceUnavailable>()),
      );
    });

    test('injects UnsupportedAudioFormat', () async {
      flaky.errorToThrow = const UnsupportedAudioFormat();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<UnsupportedAudioFormat>()),
      );
    });

    test('injects EmptyRecording', () async {
      flaky.errorToThrow = const EmptyRecording();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<EmptyRecording>()),
      );
    });

    test('injects UnintelligibleQuery', () async {
      flaky.errorToThrow = const UnintelligibleQuery();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<UnintelligibleQuery>()),
      );
    });

    test('injects QueryTooLong', () async {
      flaky.errorToThrow = const QueryTooLong();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<QueryTooLong>()),
      );
    });

    test('injects RecordingTooLarge', () async {
      flaky.errorToThrow = const RecordingTooLarge();
      flaky.failing.add('voiceTurn');
      final audio = Uint8List.fromList([1, 2, 3, 4]);

      expect(
        () => flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a'),
        throwsA(isA<RecordingTooLarge>()),
      );
    });

    test('recovers after removing from failing set', () async {
      flaky.failing.add('voiceTurn');
      flaky.failing.remove('voiceTurn');

      final audio = Uint8List.fromList([1, 2, 3, 4]);
      final result = await flaky.voiceTurn('s-1', audio, contentType: 'audio/m4a');
      expect(result.transcript, isNotEmpty);
    });
  });

  group('VoiceRecorder', () {
    late VoiceRecorder recorder;

    setUp(() {
      recorder = VoiceRecorder();
    });

    test('has 60-second max duration by default', () {
      expect(recorder.maxDuration, equals(const Duration(seconds: 60)));
    });

    test('enforces 10MB backstop by default', () {
      expect(recorder.maxSizeBytes, equals(10 * 1024 * 1024));
    });

    test('uses aacLc encoder by default', () {
      expect(recorder.encoder, equals(AudioEncoder.aacLc));
    });

    test('allows custom max duration', () {
      final customRecorder = VoiceRecorder(
        maxDuration: const Duration(seconds: 30),
      );
      expect(customRecorder.maxDuration, equals(const Duration(seconds: 30)));
    });

    test('allows custom max size', () {
      final customRecorder = VoiceRecorder(
        maxSizeBytes: 5 * 1024 * 1024,
      );
      expect(customRecorder.maxSizeBytes, equals(5 * 1024 * 1024));
    });

    test('allows opus encoder as fallback', () {
      final opusRecorder = VoiceRecorder(encoder: AudioEncoder.opus);
      expect(opusRecorder.encoder, equals(AudioEncoder.opus));
    });

    test('encoder selection is injectable', () {
      // Verify that encoder can be changed without touching fidelity logic
      final customRecorder = VoiceRecorder(
        encoder: AudioEncoder.opus,
      );
      expect(customRecorder.encoder, equals(AudioEncoder.opus));
    });

    test('starts in non-recording state', () {
      expect(recorder.isRecording, isFalse);
    });
  });
}
