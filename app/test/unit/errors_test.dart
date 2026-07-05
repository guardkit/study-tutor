// Wave-1 unit tests: the typed errors carry the contract's exact
// `error_type` strings (API-session-cross-device.md §9, closed set).
// p2-wave-1 adds the client-local TransportError group — the one member of
// the sealed hierarchy outside the §9 wire set (phase-2 scope §3.2).
import 'package:flutter_test/flutter_test.dart';
import 'package:study_tutor_app/domain/errors.dart';

void main() {
  group('contract §9 error_type strings, verbatim', () {
    test('SessionNotFoundError', () {
      expect(const SessionNotFoundError().errorType, 'SessionNotFoundError');
    });

    test('SessionEnded', () {
      expect(const SessionEnded().errorType, 'SessionEnded');
    });

    test('SessionForbidden', () {
      expect(const SessionForbidden().errorType, 'SessionForbidden');
    });

    test('Unauthenticated', () {
      expect(const Unauthenticated().errorType, 'Unauthenticated');
    });
  });

  group('error mechanics', () {
    test('all four are catchable as SessionApiException', () {
      const errors = <SessionApiException>[
        SessionNotFoundError(),
        SessionEnded(),
        SessionForbidden(),
        Unauthenticated(),
      ];
      for (final e in errors) {
        expect(e, isA<Exception>());
      }
    });

    test('toString carries errorType for debug logs', () {
      expect(const SessionEnded().toString(), startsWith('SessionEnded'));
    });

    test('message is carried through', () {
      expect(const SessionForbidden('nope').message, 'nope');
    });
  });

  group('client-local TransportError (phase-2 scope §3.2)', () {
    test('label is TransportError — a client-side tag, not a §9 wire string',
        () {
      expect(const TransportError().errorType, 'TransportError');
    });

    test('catchable as SessionApiException like the wire errors, so call '
        'sites handle one sealed hierarchy', () {
      expect(const TransportError(), isA<SessionApiException>());
    });

    test('message is carried through', () {
      expect(const TransportError('socket died').message, 'socket died');
    });
  });
}
