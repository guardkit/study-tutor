// FEAT-VOICE-003 unit tests: the six voice error types extend the same sealed
// SessionApiException hierarchy, carrying their contract `error_type` strings.
// These errors complement the §9 wire set with voice-specific failure modes.
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';

void main() {
  group('voice error_type strings, verbatim', () {
    test('UnsupportedAudioFormat', () {
      expect(const UnsupportedAudioFormat().errorType, 'UnsupportedAudioFormat');
    });

    test('EmptyRecording', () {
      expect(const EmptyRecording().errorType, 'EmptyRecording');
    });

    test('UnintelligibleQuery', () {
      expect(const UnintelligibleQuery().errorType, 'UnintelligibleQuery');
    });

    test('QueryTooLong', () {
      expect(const QueryTooLong().errorType, 'QueryTooLong');
    });

    test('RecordingTooLarge', () {
      expect(const RecordingTooLarge().errorType, 'RecordingTooLarge');
    });

    test('VoiceUnavailable', () {
      expect(const VoiceUnavailable().errorType, 'VoiceUnavailable');
    });
  });

  group('voice error mechanics', () {
    test('all six are catchable as SessionApiException', () {
      const errors = <SessionApiException>[
        UnsupportedAudioFormat(),
        EmptyRecording(),
        UnintelligibleQuery(),
        QueryTooLong(),
        RecordingTooLarge(),
        VoiceUnavailable(),
      ];
      for (final e in errors) {
        expect(e, isA<Exception>());
        expect(e, isA<SessionApiException>());
      }
    });

    test('toString carries errorType for debug logs', () {
      expect(
          const VoiceUnavailable().toString(), startsWith('VoiceUnavailable'));
    });

    test('message is carried through', () {
      expect(const QueryTooLong('exceeded limit').message, 'exceeded limit');
    });

    test('default messages are present', () {
      expect(const UnsupportedAudioFormat().message, isNotEmpty);
      expect(const EmptyRecording().message, isNotEmpty);
      expect(const UnintelligibleQuery().message, isNotEmpty);
      expect(const QueryTooLong().message, isNotEmpty);
      expect(const RecordingTooLarge().message, isNotEmpty);
      expect(const VoiceUnavailable().message, isNotEmpty);
    });
  });

  group('sealed exhaustiveness — compile-time enforcement', () {
    test('switch over SessionApiException covers all members including voice',
        () {
      // This test exists to trigger a compile error if a new error type is
      // added but not handled. The switch is exhaustive over the sealed type.
      const errors = <SessionApiException>[
        // §9 wire errors
        SessionNotFoundError(),
        SessionEnded(),
        SessionForbidden(),
        Unauthenticated(),
        // Client-local
        TransportError(),
        // Voice errors (FEAT-VOICE-003)
        UnsupportedAudioFormat(),
        EmptyRecording(),
        UnintelligibleQuery(),
        QueryTooLong(),
        RecordingTooLarge(),
        VoiceUnavailable(),
      ];

      for (final e in errors) {
        final handled = switch (e) {
          SessionNotFoundError() => 'session_not_found',
          SessionEnded() => 'session_ended',
          SessionForbidden() => 'session_forbidden',
          Unauthenticated() => 'unauthenticated',
          TransportError() => 'transport',
          UnsupportedAudioFormat() => 'audio_format',
          EmptyRecording() => 'empty_recording',
          UnintelligibleQuery() => 'unintelligible',
          QueryTooLong() => 'query_too_long',
          RecordingTooLarge() => 'recording_too_large',
          VoiceUnavailable() => 'voice_unavailable',
        };
        expect(handled, isNotEmpty);
      }
    });

    test('voice errors are distinguishable by type in catch blocks', () {
      // Invariant: each error type is unique and catchable independently,
      // so adapters can map wire envelopes 1:1 and UI can show tailored copy.
      const error = UnsupportedAudioFormat('test');

      expect(error, isA<UnsupportedAudioFormat>());
      expect(error, isNot(isA<EmptyRecording>()));
      expect(error, isNot(isA<VoiceUnavailable>()));
    });
  });
}
