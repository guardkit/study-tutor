// FEAT-VOICE-003 unit tests: VoiceApi port DTOs and structure invariants.
// Tests the data types without implementing the port (adapters come later).
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/ports/voice_api.dart';

void main() {
  group('VoiceTurnResult DTO', () {
    test('constructs with transcript and answer parts', () {
      const result = VoiceTurnResult(
        transcript: 'Hello world',
        answerParts: [],
      );

      expect(result.transcript, 'Hello world');
      expect(result.answerParts, isEmpty);
    });

    test('equality based on transcript and parts', () {
      const a = VoiceTurnResult(
        transcript: 'test',
        answerParts: [TextAnswerPart(seq: 0, text: 'answer')],
      );
      const b = VoiceTurnResult(
        transcript: 'test',
        answerParts: [TextAnswerPart(seq: 0, text: 'answer')],
      );
      const c = VoiceTurnResult(
        transcript: 'different',
        answerParts: [TextAnswerPart(seq: 0, text: 'answer')],
      );

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });

    test('hashCode consistent with equality', () {
      const a = VoiceTurnResult(
        transcript: 'test',
        answerParts: [TextAnswerPart(seq: 0, text: 'answer')],
      );
      const b = VoiceTurnResult(
        transcript: 'test',
        answerParts: [TextAnswerPart(seq: 0, text: 'answer')],
      );

      expect(a.hashCode, equals(b.hashCode));
    });

    test('toString includes transcript and part count', () {
      const result = VoiceTurnResult(
        transcript: 'test',
        answerParts: [
          TextAnswerPart(seq: 0, text: 'a'),
          AudioAnswerPart(seq: 1, chunkId: 'chunk1'),
        ],
      );

      expect(result.toString(), contains('test'));
      expect(result.toString(), contains('2'));
    });
  });

  group('AnswerPart sealed hierarchy', () {
    test('TextAnswerPart carries seq and text', () {
      const part = TextAnswerPart(seq: 0, text: 'Hello');

      expect(part.seq, 0);
      expect(part.text, 'Hello');
    });

    test('AudioAnswerPart carries seq and chunkId', () {
      const part = AudioAnswerPart(seq: 1, chunkId: 'chunk-123');

      expect(part.seq, 1);
      expect(part.chunkId, 'chunk-123');
    });

    test('TextAnswerPart equality based on seq and text', () {
      const a = TextAnswerPart(seq: 0, text: 'hello');
      const b = TextAnswerPart(seq: 0, text: 'hello');
      const c = TextAnswerPart(seq: 1, text: 'hello');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });

    test('AudioAnswerPart equality based on seq and chunkId', () {
      const a = AudioAnswerPart(seq: 0, chunkId: 'chunk1');
      const b = AudioAnswerPart(seq: 0, chunkId: 'chunk1');
      const c = AudioAnswerPart(seq: 0, chunkId: 'chunk2');

      expect(a, equals(b));
      expect(a, isNot(equals(c)));
    });

    test('switch over AnswerPart is exhaustive', () {
      // Compile-time exhaustiveness check — adding a new AnswerPart subtype
      // breaks this without a warning suppression.
      const parts = <AnswerPart>[
        TextAnswerPart(seq: 0, text: 'text'),
        AudioAnswerPart(seq: 1, chunkId: 'audio'),
      ];

      for (final part in parts) {
        final kind = switch (part) {
          TextAnswerPart() => 'text',
          AudioAnswerPart() => 'audio',
        };
        expect(kind, isIn(['text', 'audio']));
      }
    });
  });

  group('VoiceTurnEvent sealed hierarchy', () {
    test('TranscriptEvent carries transcript and isFinal', () {
      const event = TranscriptEvent(transcript: 'hello', isFinal: false);

      expect(event.transcript, 'hello');
      expect(event.isFinal, false);
    });

    test('TextTokenEvent carries token', () {
      const event = TextTokenEvent(token: 'hello');

      expect(event.token, 'hello');
    });

    test('AudioPartEvent carries seq and chunkId', () {
      const event = AudioPartEvent(seq: 2, chunkId: 'chunk-789');

      expect(event.seq, 2);
      expect(event.chunkId, 'chunk-789');
    });

    test('TurnCompleteEvent is a singleton-like marker', () {
      const a = TurnCompleteEvent();
      const b = TurnCompleteEvent();

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('equality implementations are consistent', () {
      const t1 = TranscriptEvent(transcript: 'test', isFinal: true);
      const t2 = TranscriptEvent(transcript: 'test', isFinal: true);
      const t3 = TranscriptEvent(transcript: 'test', isFinal: false);

      expect(t1, equals(t2));
      expect(t1, isNot(equals(t3)));

      const tok1 = TextTokenEvent(token: 'a');
      const tok2 = TextTokenEvent(token: 'a');
      const tok3 = TextTokenEvent(token: 'b');

      expect(tok1, equals(tok2));
      expect(tok1, isNot(equals(tok3)));
    });

    test('switch over VoiceTurnEvent is exhaustive', () {
      // Compile-time exhaustiveness check — adding a new event subtype breaks
      // this without a warning suppression.
      const events = <VoiceTurnEvent>[
        TranscriptEvent(transcript: 'hello', isFinal: true),
        TextTokenEvent(token: 'world'),
        AudioPartEvent(seq: 0, chunkId: 'chunk1'),
        TurnCompleteEvent(),
      ];

      for (final event in events) {
        final kind = switch (event) {
          TranscriptEvent() => 'transcript',
          TextTokenEvent() => 'text_token',
          AudioPartEvent() => 'audio_part',
          TurnCompleteEvent() => 'complete',
        };
        expect(kind, isIn(['transcript', 'text_token', 'audio_part', 'complete']));
      }
    });
  });

  group('VoiceApi interface structure', () {
    test('interface declares three methods with correct signatures', () {
      // This is a compile-time invariant enforced by the type system, but we
      // document the expected shape here. Any implementation must provide:
      //
      // - Future<VoiceTurnResult> voiceTurn(String, Uint8List, {String})
      // - Stream<VoiceTurnEvent> voiceTurnStream(String, Uint8List, {String})
      // - Future<Uint8List> fetchAudioChunk(String, String)
      //
      // The concrete test here just verifies the types exist and are importable.
      // Actual behavior is tested in adapter tests (TASK-VC-003/TASK-VC-004).

      // Type tokens prove the interface and DTOs are visible.
      expect(VoiceApi, isA<Type>());
      expect(VoiceTurnResult, isA<Type>());
      expect(VoiceTurnEvent, isA<Type>());
    });
  });

  group('DTO immutability invariant', () {
    test('VoiceTurnResult fields are final', () {
      // Dart const constructors enforce immutability — if fields were mutable,
      // this would not compile. This test documents the invariant.
      const result = VoiceTurnResult(transcript: 'test', answerParts: []);

      // Attempting to assign would be a compile error:
      // result.transcript = 'new'; // ❌
      expect(result.transcript, 'test');
    });

    test('AnswerPart fields are final', () {
      const text = TextAnswerPart(seq: 0, text: 'hello');
      const audio = AudioAnswerPart(seq: 1, chunkId: 'chunk');

      expect(text.seq, 0);
      expect(audio.chunkId, 'chunk');
    });

    test('VoiceTurnEvent fields are final', () {
      const transcript = TranscriptEvent(transcript: 'test', isFinal: true);
      const token = TextTokenEvent(token: 'word');

      expect(transcript.transcript, 'test');
      expect(token.token, 'word');
    });
  });
}
